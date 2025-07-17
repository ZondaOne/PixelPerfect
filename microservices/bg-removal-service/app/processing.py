"""
Image processing module for background removal with Cloudinary integration.
Implements full-quality and low-quality thumbnail generation.
Uses enhanced OCR optimized for signature detection (white background with dark line).
OPTIMIZED: Uses memory-efficient rembg models (max 400MB RAM usage).
FIXED: Job tracking and duplicate prevention system.
"""

import logging
import time
import traceback
from typing import Dict, Tuple, Any, Set
import io
import threading
import gc
from PIL import Image, ImageFilter
from rembg import remove, new_session
import pytesseract
import numpy as np

from app.cloudinary_service import CloudinaryService

logger = logging.getLogger(__name__)

class ImageProcessingError(Exception):
    """Specific error for image processing failures."""

# Memory-efficient model configurations
# silueta model: ~250MB RAM, good for general use
# u2netp model: ~150MB RAM, lightweight version of u2net
MEMORY_EFFICIENT_MODELS = {
    "general": "u2netp",           # Reduced from silueta (250MB) to u2netp (150MB) = 100MB saving
    "signature": "isnet-general-use",  # Even lighter model for signatures = 30MB saving
    "fallback": "u2netp"           # Consistent fallback
}

# Cache for sessions by model to avoid creating new session for each image
_sessions_cache: Dict[str, Any] = {}

# Set to track active jobs and prevent duplicates
_active_jobs: Set[str] = set()
_jobs_lock = threading.Lock()

def clear_sessions_cache():
    """
    Clear rembg sessions cache to free memory.
    Useful when restarting application or changing configurations.
    """
    global _sessions_cache
    logger.info("🧹 Clearing rembg sessions cache")
    
    # Explicitly delete sessions to free GPU/CPU memory
    for model_name, session in _sessions_cache.items():
        try:
            del session
        except:
            pass
    
    _sessions_cache.clear()
    
    # Force garbage collection to free memory immediately
    gc.collect()
    logger.info("🧹 Sessions cache cleared and memory freed")

def clear_active_jobs():
    """
    Clear active jobs set.
    Useful when restarting application or in case of critical errors.
    """
    global _active_jobs
    with _jobs_lock:
        logger.info("🧹 Clearing active jobs list")
        _active_jobs.clear()

def get_active_jobs_count() -> int:
    """Returns the number of jobs currently being processed."""
    with _jobs_lock:
        return len(_active_jobs)

def get_session_for_model(model_name: str):
    """
    Get a reusable rembg session for the given model,
    caching to avoid creating multiple sessions.
    Uses memory-efficient models to stay under 400MB RAM.
    """
    if model_name not in _sessions_cache:
        logger.info(f"🔧 Creating new session for memory-efficient model: {model_name}")
        try:
            _sessions_cache[model_name] = new_session(model_name)
            logger.info(f"✅ Session created successfully for model: {model_name}")
        except Exception as e:
            logger.error(f"❌ Failed to create session for {model_name}: {e}")
            # Fallback to most lightweight model
            fallback_model = MEMORY_EFFICIENT_MODELS["fallback"]
            logger.info(f"🔄 Using fallback model: {fallback_model}")
            _sessions_cache[model_name] = new_session(fallback_model)
    else:
        logger.debug(f"♻️ Reusing existing session for model: {model_name}")
    
    return _sessions_cache[model_name]

def optimize_image_for_processing(image: Image.Image, max_size: int = 1024) -> Image.Image:
    """
    Optimize image size to reduce memory usage during processing.
    Maintains aspect ratio while reducing dimensions if needed.
    """
    width, height = image.size
    
    # If image is already small enough, return as-is
    if max(width, height) <= max_size:
        return image
    
    # Calculate new dimensions maintaining aspect ratio
    if width > height:
        new_width = max_size
        new_height = int((height * max_size) / width)
    else:
        new_height = max_size
        new_width = int((width * max_size) / height)
    
    # Resize with high-quality resampling
    resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
    logger.info(f"🔄 Image optimized from {width}x{height} to {new_width}x{new_height}")
    
    return resized

def is_probable_signature(image: Image.Image, ocr_confidence_threshold=30.0) -> bool:
    """
    Detect signatures in images with white background and dark line using optimized OCR.
    """
    try:
        # Convert to grayscale
        gray = image.convert("L")
        
        # Calculate percentage of light pixels (background)
        np_gray = np.array(gray)
        light_pixels = np_gray > 200  # Almost white pixels
        light_ratio = np.mean(light_pixels)
        
        # If not enough white background, discard as signature
        if light_ratio < 0.85:
            logger.debug(f"📋 Insufficient background: {light_ratio:.2f} < 0.85")
            return False
            
        # Enhanced preprocessing for signatures
        # 1. Slightly sharpen to improve thin lines
        sharpened = gray.filter(ImageFilter.SHARPEN)
        
        # 2. High contrast for dark signatures
        high_contrast = sharpened.point(lambda x: 0 if x < 200 else 255)
        
        # 3. OCR optimized for signatures (special configuration)
        ocr_config = r'--psm 6 --oem 3 -c tessedit_char_whitelist=abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        
        ocr_data = pytesseract.image_to_data(
            high_contrast, 
            lang="eng", 
            output_type=pytesseract.Output.DICT,
            config=ocr_config
        )
        
        # Calculate maximum detected confidence - FIXED TYPE ERROR
        confidences = []
        for conf in ocr_data['conf']:
            try:
                c = float(conf)
                if c > 0:  # Ignore negative or zero values
                    confidences.append(c)
            except (ValueError, TypeError):
                continue
        
        max_conf = max(confidences) if confidences else 0
        
        if max_conf <= ocr_confidence_threshold:
            logger.info(f"✍️ Signature detected: white background ({light_ratio:.2f}), low OCR confidence ({max_conf})")
            return True
            
        logger.debug(f"📝 Not a signature: high OCR confidence ({max_conf})")
        return False

    except Exception as e:
        logger.warning(f"⚠️ Signature detection failed: {e}")
        return False

def detect_signature_or_text(image_bytes: bytes, ocr_confidence_threshold: float = 30.0) -> str:
    """
    Detect if the image is a signature (white background + dark line).
    Returns memory-efficient model name based on content type.
    """
    try:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        if is_probable_signature(image, ocr_confidence_threshold):
            return MEMORY_EFFICIENT_MODELS["signature"]  # u2netp for signatures
        else:
            return MEMORY_EFFICIENT_MODELS["general"]    # silueta for general images

    except Exception as e:
        logger.warning(f"⚠️ OCR detection failed: {e}, using fallback model")
        return MEMORY_EFFICIENT_MODELS["fallback"]

async def perform_background_removal(
    job_id: str,
    image_url: str,
    config: Dict[str, Any]
) -> Tuple[str, Dict[str, Any]]:
    
    # DEBUGGING: Show stack trace to identify where the call comes from
    logger.error("=" * 80)
    logger.error(f"🔍 JOB STARTED: {job_id}")
    logger.error(f"🔗 URL: {image_url}")
    logger.error(f"⚙️ CONFIG: {config}")
    logger.error("📋 CALL STACK TRACE:")
    logger.error("Stack trace:")
    logger.error(traceback.format_exc())
    logger.error("=" * 80)
    
    # Check if job is already being processed (prevent duplicates)
    with _jobs_lock:
        if job_id in _active_jobs:
            error_msg = f"🚫 Job {job_id} is already being processed, ignoring duplicate"
            logger.warning(error_msg)
            raise ImageProcessingError(error_msg)
        
        # Add job to active set
        _active_jobs.add(job_id)
        logger.info(f"📝 Job {job_id} added to active list. Total active jobs: {len(_active_jobs)}")

    ocr_confidence_threshold = config.get("ocr_confidence_threshold", 30.0)
    max_image_size = config.get("max_image_size", 1024)  # New config for memory optimization

    try:
        logger.info(f"🚀 Starting job {job_id} with URL: {image_url}")
        
        logger.info(f"⬇️ Downloading image: {image_url}")
        input_image_bytes = CloudinaryService.download_image_from_url(image_url)

        # Optimize image size to reduce memory usage
        input_image = Image.open(io.BytesIO(input_image_bytes)).convert("RGB")
        optimized_image = optimize_image_for_processing(input_image, max_image_size)
        
        # Convert back to bytes for processing
        optimized_buffer = io.BytesIO()
        optimized_image.save(optimized_buffer, format="PNG", optimize=True)
        optimized_bytes = optimized_buffer.getvalue()

        model_to_use = detect_signature_or_text(optimized_bytes, ocr_confidence_threshold)
        logger.info(f"🤖 Memory-efficient model selected for {job_id}: {model_to_use}")

        # Use cached session or create new one only if it doesn't exist
        session = get_session_for_model(model_to_use)

        start_time = time.perf_counter()
        logger.info(f"🎨 Removing background for {job_id} (memory-optimized)")
        
        # Process with optimized image to reduce memory usage
        output_bytes = remove(optimized_bytes, session=session)
        elapsed = time.perf_counter() - start_time

        logger.info(f"🖼️ Generating thumbnail for {job_id}")
        output_image = Image.open(io.BytesIO(output_bytes)).convert("RGBA")
        thumbnail = output_image.copy()
        thumbnail.thumbnail((400, 300), Image.Resampling.LANCZOS)

        thumbnail_buffer = io.BytesIO()
        thumbnail.save(thumbnail_buffer, format="PNG", optimize=True, quality=70)
        thumbnail_bytes = thumbnail_buffer.getvalue()

        logger.info(f"☁️ Uploading processed image to Cloudinary for {job_id}")
        processed_url, processed_public_id = CloudinaryService.upload_processed_image(
            output_bytes, job_id, "bg_removed"
        )

        logger.info(f"☁️ Uploading thumbnail to Cloudinary for {job_id}")
        thumbnail_url, thumbnail_public_id = CloudinaryService.upload_thumbnail(
            thumbnail_bytes, job_id
        )

        # Force garbage collection to free memory after processing
        del input_image, optimized_image, output_image, thumbnail
        gc.collect()

        logger.info(f"✅ Job {job_id} completed successfully")
        logger.info(f"🔗 Full quality URL: {processed_url}")
        logger.info(f"🔗 Thumbnail URL: {thumbnail_url}")

        processing_info = {
            "model_version": model_to_use,
            "mode": "cloudinary_integration_memory_optimized",
            "processing_time_seconds": round(elapsed, 3),
            "signature_detection_threshold": ocr_confidence_threshold,
            "max_image_size": max_image_size,
            "memory_optimization": True,
            "full_quality_public_id": processed_public_id,
            "thumbnail_public_id": thumbnail_public_id,
            "thumbnail_url": thumbnail_url,
            "job_id": job_id,
            "timestamp": time.time()
        }

        return processed_url, processing_info

    except Exception as e:
        logger.error(f"❌ Error in job {job_id}: {e}")
        logger.error(f"📋 Complete traceback: {traceback.format_exc()}")
        raise ImageProcessingError(f"Error removing background in job {job_id}: {e}")
    
    finally:
        # ALWAYS remove job from active set, regardless of error or success
        with _jobs_lock:
            _active_jobs.discard(job_id)
            logger.info(f"🗑️ Job {job_id} removed from active list. Remaining jobs: {len(_active_jobs)}")
        
        # Force garbage collection to ensure memory is freed
        gc.collect()

def get_system_status() -> Dict[str, Any]:
    """
    Return current processing system status.
    Useful for debugging and monitoring.
    """
    with _jobs_lock:
        return {
            "active_jobs_count": len(_active_jobs),
            "active_jobs": list(_active_jobs),
            "cached_models": list(_sessions_cache.keys()),
            "cached_sessions_count": len(_sessions_cache),
            "memory_efficient_models": MEMORY_EFFICIENT_MODELS,
            "memory_optimization_enabled": True,
            "max_expected_ram_usage_mb": 400,
            "timestamp": time.time()
        }

def get_memory_usage_info() -> Dict[str, Any]:
    """
    Return information about current memory usage and optimization settings.
    """
    return {
        "models_configuration": MEMORY_EFFICIENT_MODELS,
        "expected_ram_usage": {
            "silueta_model": "~250MB",
            "u2netp_model": "~150MB",
            "total_max": "400MB"
        },
        "optimization_features": [
            "Memory-efficient model selection",
            "Image size optimization before processing",
            "Explicit garbage collection after processing",
            "Session caching to avoid model reloading"
        ],
        "current_cached_sessions": len(_sessions_cache)
    }

def force_reset_system():
    """
    Emergency function to completely reset the system.
    USE ONLY IN CASE OF CRITICAL PROBLEMS.
    """
    logger.warning("🚨 FORCED SYSTEM RESET")
    clear_active_jobs()
    clear_sessions_cache()
    
    # Additional memory cleanup
    gc.collect()
    
    logger.warning("🚨 System completely reset and memory freed")

def cleanup_memory():
    """
    Perform aggressive memory cleanup.
    Call this periodically or when memory usage is high.
    """
    logger.info("🧹 Performing memory cleanup")
    
    # Clear sessions cache
    clear_sessions_cache()
    
    # Force garbage collection multiple times
    for _ in range(3):
        gc.collect()
    
    logger.info("🧹 Memory cleanup completed")