"""
Memory-optimized image processing module for upscaling with Real-ESRGAN integration.
Designed to use <512MB RAM with faster processing.
"""

import logging
import os
import cv2
import numpy as np
from typing import Dict, Tuple, Any, Optional
import urllib.request
from pathlib import Path
from realesrgan import RealESRGANer
from basicsr.archs.rrdbnet_arch import RRDBNet
import torch
import gc
from app.cloudinary_service import CloudinaryService
from app.config import MODELS_DIR
from app.local_image_processing import LocalImageProcessor

logger = logging.getLogger(__name__)

# Global model cache - only one model at a time
_current_model = None
_current_model_name = None

# Check GPU availability once
CUDA_AVAILABLE = torch.cuda.is_available()
if CUDA_AVAILABLE:
    logger.info(f"GPU available: {torch.cuda.get_device_name(0)}")
else:
    logger.info("Using CPU for processing")

class OptimizedUpscalingProcessor:
    """Memory-efficient upscaling processor that loads models on-demand."""
    
    MODEL_CONFIGS = {
        'free': {
            'url': 'https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth',
            'scale': 2,
            'filename': 'RealESRGAN_x2plus.pth',
            'blocks': 23
        },
        'premium': {
            'url': 'https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth',
            'scale': 4,
            'filename': 'RealESRGAN_x4plus.pth',
            'blocks': 23
        }
    }
    
    def __init__(self):
        """Initialize without loading any models to save memory."""
        os.makedirs(MODELS_DIR, exist_ok=True)
        self._ensure_models_downloaded()
    
    def _ensure_models_downloaded(self):
        """Pre-download models if needed, but don't load them."""
        for model_key, config in self.MODEL_CONFIGS.items():
            model_path = os.path.join(MODELS_DIR, config['filename'])
            if not os.path.exists(model_path):
                logger.info(f"Downloading {model_key} model...")
                try:
                    urllib.request.urlretrieve(config['url'], model_path)
                    logger.info(f"Downloaded {config['filename']}")
                except Exception as e:
                    logger.error(f"Failed to download {model_key}: {e}")
                    raise RuntimeError(f"Model download failed: {e}")
    
    def _load_model_on_demand(self, model_type: str) -> RealESRGANer:
        """Load model only when needed and cache it globally."""
        global _current_model, _current_model_name
        
        if _current_model_name == model_type and _current_model is not None:
            return _current_model
        
        # Clear previous model to free memory
        if _current_model is not None:
            del _current_model
            _current_model = None
            gc.collect()
            if CUDA_AVAILABLE:
                torch.cuda.empty_cache()
        
        config = self.MODEL_CONFIGS[model_type]
        model_path = os.path.join(MODELS_DIR, config['filename'])
        
        logger.info(f"Loading {model_type} model...")
        
        # Create lightweight model
        model = RRDBNet(
            num_in_ch=3, 
            num_out_ch=3, 
            num_feat=64, 
            num_block=config['blocks'], 
            num_grow_ch=32, 
            scale=config['scale']
        )
        
        # Use half precision on GPU to save memory
        use_half = CUDA_AVAILABLE
        gpu_id = 0 if CUDA_AVAILABLE else None
        
        upsampler = RealESRGANer(
            scale=config['scale'],
            model_path=model_path,
            dni_weight=None,
            model=model,
            tile=512,  # Use tiling to reduce memory usage
            tile_pad=10,
            pre_pad=0,
            half=use_half,
            gpu_id=gpu_id
        )
        
        _current_model = upsampler
        _current_model_name = model_type
        
        logger.info(f"Model {model_type} loaded successfully")
        return upsampler
    
    def process_image(self, image_data: bytes, is_premium: bool = False) -> Tuple[bytes, Dict[str, Any]]:
        """Process image with memory optimization."""
        model_type = 'premium' if is_premium else 'free'
        
        # Load model on demand
        upsampler = self._load_model_on_demand(model_type)
        
        # Decode image efficiently - CAMBIAR ESTA LÍNEA
        nparr = np.frombuffer(image_data, np.uint8)
        input_image = cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)  # ← CAMBIO AQUÍ
        
        if input_image is None:
            raise ValueError("Failed to decode input image")
        
        # AGREGAR ESTAS LÍNEAS AQUÍ ↓
        has_alpha = len(input_image.shape) == 3 and input_image.shape[2] == 4
        alpha_channel = None
        
        if has_alpha:
            # Separar RGB y Alpha
            alpha_channel = input_image[:, :, 3]
            input_rgb = input_image[:, :, :3]
            logger.info("Image has transparency - preserving alpha channel")
        else:
            input_rgb = input_image
        # HASTA AQUÍ ↑
        
        original_shape = input_rgb.shape[:2]  # ← CAMBIAR input_image por input_rgb
        
        # Resize if image is too large to prevent memory issues
        max_dimension = 2048 if is_premium else 1024
        h, w = original_shape
        if max(h, w) > max_dimension:
            scale_factor = max_dimension / max(h, w)
            new_h, new_w = int(h * scale_factor), int(w * scale_factor)
            input_rgb = cv2.resize(input_rgb, (new_w, new_h), interpolation=cv2.INTER_AREA)
            # También resize del alpha si existe
            if has_alpha and alpha_channel is not None:
                alpha_channel = cv2.resize(alpha_channel, (new_w, new_h), interpolation=cv2.INTER_AREA)
            logger.info(f"Resized input from {w}x{h} to {new_w}x{new_h}")
        
        # Process with upsampler - CAMBIAR ESTA LÍNEA
        try:
            output_image, _ = upsampler.enhance(input_rgb, outscale=None)  # ← CAMBIO AQUÍ
        except Exception as e:
            logger.error(f"Enhancement failed: {e}")
            raise RuntimeError(f"Upscaling failed: {e}")
        
        # AGREGAR DESPUÉS DEL ENHANCEMENT:
        if has_alpha and alpha_channel is not None:
            # Redimensionar canal alpha al tamaño de salida
            scale_factor = output_image.shape[0] / alpha_channel.shape[0]
            new_alpha_size = (int(alpha_channel.shape[1] * scale_factor), 
                            int(alpha_channel.shape[0] * scale_factor))
            alpha_upscaled = cv2.resize(alpha_channel, new_alpha_size, interpolation=cv2.INTER_CUBIC)
            
            # Combinar RGB + Alpha
            output_image = cv2.merge([output_image[:,:,0], output_image[:,:,1], 
                                    output_image[:,:,2], alpha_upscaled])
            logger.info("Alpha channel restored to upscaled image")
        
        # Convert and encode efficiently
        if output_image.dtype != np.uint8:
            output_image = np.clip(output_image, 0, 255).astype(np.uint8)
        
        # CAMBIAR ESTAS LÍNEAS:
        # Use PNG to preserve transparency
        encode_params = [cv2.IMWRITE_PNG_COMPRESSION, 6]
        success, buffer = cv2.imencode('.png', output_image, encode_params)
        
        if not success:
            raise RuntimeError("Failed to encode output image")
        
        output_bytes = buffer.tobytes()
        
        # Calculate processing info
        output_shape = output_image.shape[:2]
        scale_factor = output_shape[1] / original_shape[1]
        
        processing_info = {
            "model_used": f"RealESRGAN_x{self.MODEL_CONFIGS[model_type]['scale']}plus",
            "quality_level": model_type,
            "scale_factor": round(scale_factor, 2),
            "original_size": f"{original_shape[1]}x{original_shape[0]}",
            "output_size": f"{output_shape[1]}x{output_shape[0]}",
            "is_premium": is_premium,
            "memory_optimized": True
        }
        
        # Clean up
        del input_image, output_image, nparr, buffer
        gc.collect()
        
        return output_bytes, processing_info


async def perform_upscaling(
    job_id: str,
    image_url: str,
    config: Dict[str, Any]
) -> Tuple[str, Dict[str, Any]]:
    """
    Perform optimized image upscaling using Real-ESRGAN.
    
    Args:
        job_id: Unique job identifier
        image_url: Cloudinary URL of the original image
        config: Processing configuration with 'quality' key
        
    Returns:
        Tuple of (processed_image_url, processing_info)
    """
    logger.info(f"Processing upscaling job {job_id}")
    
    try:
        # Get quality level
        quality = config.get('quality', 'FREE').upper()
        is_premium = quality == 'PREMIUM'
        
        # Download image efficiently
        logger.info(f"Downloading image from Cloudinary")
        input_image_bytes = CloudinaryService.download_image_from_url(image_url)
        
        # Process with optimized processor
        processor = OptimizedUpscalingProcessor()
        output_bytes, processing_info = processor.process_image(input_image_bytes, is_premium)
        
        # Create thumbnail efficiently
        logger.info(f"Creating thumbnail for {job_id}")
        thumbnail_bytes = LocalImageProcessor.create_thumbnail(output_bytes)
        
        # Optimize for upload
        if is_premium:
            optimized_bytes = LocalImageProcessor.optimize_premium_image(output_bytes)
        else:
            optimized_bytes = output_bytes
        
        # Upload to Cloudinary
        logger.info(f"Uploading to Cloudinary for {job_id}")
        processed_url, processed_public_id = CloudinaryService.upload_processed_image(
            optimized_bytes, job_id, "upscaled"
        )
        
        thumbnail_url, thumbnail_public_id = CloudinaryService.upload_thumbnail(
            thumbnail_bytes, job_id
        )
        
        # Update processing info
        processing_info.update({
            "full_quality_public_id": processed_public_id,
            "thumbnail_public_id": thumbnail_public_id,
            "thumbnail_url": thumbnail_url,
            "local_thumbnail_generated": True,
            "thumbnail_size_bytes": len(thumbnail_bytes),
            "premium_size_bytes": len(optimized_bytes),
            "mode": "memory_optimized"
        })
        
        logger.info(f"✅ Successfully processed job {job_id}")
        logger.info(f"🔗 URL: {processed_url}")
        
        # Final cleanup
        del input_image_bytes, output_bytes, thumbnail_bytes, optimized_bytes
        gc.collect()
        if CUDA_AVAILABLE:
            torch.cuda.empty_cache()
        
        return processed_url, processing_info
        
    except Exception as e:
        logger.error(f"Upscaling failed for job {job_id}: {e}")
        # Force cleanup on error
        gc.collect()
        if CUDA_AVAILABLE:
            torch.cuda.empty_cache()
        raise RuntimeError(f"Upscaling failed: {e}")


def cleanup_models():
    """Manually cleanup models to free memory."""
    global _current_model, _current_model_name
    
    if _current_model is not None:
        del _current_model
        _current_model = None
        _current_model_name = None
        gc.collect()
        if CUDA_AVAILABLE:
            torch.cuda.empty_cache()
        logger.info("Models cleaned up successfully")


def get_memory_usage() -> Dict[str, Any]:
    """Get current memory usage statistics."""
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    
    stats = {
        "rss_mb": memory_info.rss / 1024 / 1024,
        "vms_mb": memory_info.vms / 1024 / 1024,
        "model_loaded": _current_model_name,
    }
    
    if CUDA_AVAILABLE:
        stats["gpu_memory_mb"] = torch.cuda.memory_allocated() / 1024 / 1024
        stats["gpu_memory_cached_mb"] = torch.cuda.memory_reserved() / 1024 / 1024
    
    return stats