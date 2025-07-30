import os
import time
import threading
import gc
import io
import requests
import numpy as np
import asyncio
import concurrent.futures
from PIL import Image, ImageFilter
import onnxruntime as ort

from app.cloudinary_service import CloudinaryService

class ImageProcessingError(Exception):
    pass

# Model URLs and paths
FREE_MODEL_URL = os.getenv(
    "FREE_UPSCALE_MODEL_URL",
    "https://huggingface.co/spaces/Wuvin/Unique3D/resolve/main/ckpt/realesrgan-x4.onnx"
)

FREE_MODEL_PATH = os.getenv("FREE_UPSCALE_MODEL_PATH", "models/realesrgan_free.onnx")

# ULTRA conservative settings optimized for 1 CPU + 512MB RAM
MAX_IMAGE_DIMENSION = 150  # Más pequeño para velocidad
THUMBNAIL_DIMENSION = 200  # Reducido para menos memoria
JPEG_QUALITY = 75  # Menos calidad = más velocidad
MAX_CONCURRENT_JOBS = 1

_active_jobs = set()
_jobs_lock = threading.Lock()
_session = None

async def run_sync_in_thread(func, *args, **kwargs):
    """Ejecutar función síncrona en thread separado para no bloquear"""
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        return await loop.run_in_executor(executor, func, *args, **kwargs)

def download_model(url: str, path: str):
    """Download ONNX model if not exists"""
    if os.path.exists(path):
        return
        
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        print("Downloading model...")
        resp = requests.get(url, stream=True, timeout=30)
        resp.raise_for_status()
        with open(path, 'wb') as f:
            for chunk in resp.iter_content(4096):  # Smaller chunks
                if chunk:
                    f.write(chunk)
        print(f"Model downloaded ({os.path.getsize(path)//1024//1024}MB)")
    except Exception as e:
        if os.path.exists(path):
            os.remove(path)
        raise ImageProcessingError(f"Download failed: {e}")

def get_session() -> ort.InferenceSession:
    """Get memory-optimized ONNX session"""
    global _session
    
    if _session is None:
        download_model(FREE_MODEL_URL, FREE_MODEL_PATH)
        
        # Ultra memory-conservative settings
        opts = ort.SessionOptions()
        opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_DISABLE_ALL
        opts.enable_mem_pattern = False
        opts.enable_cpu_mem_arena = False
        opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        
        # Limit memory usage
        providers = [
            ('CPUExecutionProvider', {
                'arena_extend_strategy': 'kSameAsRequested',
                'enable_cpu_mem_arena': False
            })
        ]
        
        _session = ort.InferenceSession(FREE_MODEL_PATH, opts, providers)
    
    return _session

def upscale_simple(img_arr: np.ndarray) -> np.ndarray:
    """Memory-optimized upscaling with immediate cleanup"""
    session = get_session()
    
    # Normalize in-place to save memory
    input_tensor = img_arr.astype(np.float32)
    input_tensor /= 255.0
    input_tensor = input_tensor.transpose(2, 0, 1)[None, ...]
    
    # Clear original array immediately
    del img_arr
    gc.collect()
    
    # Process
    input_name = session.get_inputs()[0].name
    output = session.run(None, {input_name: input_tensor})[0]
    
    # Clear input immediately
    del input_tensor
    gc.collect()
    
    # Convert back
    output = output[0].transpose(1, 2, 0)
    output = np.clip(output * 255.0, 0, 255).astype(np.uint8)
    
    return output

def enhance_thumbnail(img: Image.Image) -> Image.Image:
    """Memory-efficient thumbnail enhancement"""
    # Apply subtle sharpening in-place
    enhanced = img.filter(ImageFilter.UnsharpMask(radius=1, percent=110, threshold=3))
    return enhanced

def process_alpha_channel(alpha_channel, target_size):
    """Process alpha channel separately to control memory"""
    if alpha_channel is None:
        return None
    alpha_resized = alpha_channel.resize(target_size, Image.LANCZOS)
    del alpha_channel  # Clean up original
    gc.collect()
    return alpha_resized

def save_image_fast(img, is_thumbnail=False):
    """Guardar imagen priorizando velocidad sobre calidad"""
    buf = io.BytesIO()
    
    if img.mode == 'RGBA':
        # PNG más rápido con menos compresión
        compress_level = 1 if is_thumbnail else 3  # Mínima compresión
        img.save(buf, format='PNG', optimize=False, compress_level=compress_level)
    else:
        # JPEG más rápido
        quality = 90 if is_thumbnail else JPEG_QUALITY
        img.save(buf, format='JPEG', quality=quality, optimize=False)
    
    result = buf.getvalue()
    buf.close()
    return result

async def perform_upscaling(job_id: str, image_url: str, config: dict):
    """Ultra memory-efficient upscaling optimized for 1 CPU"""
    with _jobs_lock:
        if len(_active_jobs) >= MAX_CONCURRENT_JOBS:
            raise ImageProcessingError("Max concurrent jobs reached")
        if job_id in _active_jobs:
            raise ImageProcessingError(f"Job {job_id} already active")
        _active_jobs.add(job_id)

    try:
        print(f"Starting job {job_id} - downloading image...")
        
        # Aggressive garbage collection at start
        gc.collect()
        
        # Download image with smaller buffer
        input_bytes = CloudinaryService.download_image_from_url(image_url)
        img = Image.open(io.BytesIO(input_bytes))
        original_size = img.size
        print(f"Original image size: {original_size}")
        
        # Clear input bytes immediately
        del input_bytes
        gc.collect()
        
        # Handle transparency more efficiently
        has_alpha = img.mode in ('RGBA', 'LA', 'P')
        alpha_channel = None
        
        if has_alpha:
            if img.mode == 'P':
                img = img.convert('RGBA')
            alpha_channel = img.split()[-1]
            # Convert to RGB and clear original immediately
            img_rgb = img.convert('RGB')
            del img
            img = img_rgb
        else:
            img = img.convert('RGB')
        
        gc.collect()
        
        # Resize for speed and memory (even smaller)
        w, h = img.size
        if max(w, h) > MAX_IMAGE_DIMENSION:
            scale = MAX_IMAGE_DIMENSION / max(w, h)
            new_w, new_h = int(w * scale), int(h * scale)
            resized_img = img.resize((new_w, new_h), Image.LANCZOS)
            del img  # Clear original immediately
            img = resized_img
            print(f"Resized to {new_w}x{new_h} for memory efficiency")
        
        gc.collect()
        
        # Fast upscale with immediate cleanup
        print("Starting upscale process...")
        start = time.perf_counter()
        img_arr = np.array(img)
        del img  # Clear PIL image immediately
        gc.collect()
        
        output_arr = upscale_simple(img_arr)  # img_arr is deleted inside function
        duration = time.perf_counter() - start
        print(f"Upscale completed in {duration:.2f}s")
        
        gc.collect()
        
        # Convert to PIL and get size
        output_img = Image.fromarray(output_arr, 'RGB')
        final_size = output_img.size
        del output_arr  # Clear numpy array immediately
        gc.collect()
        
        # Process alpha channel separately if needed
        if has_alpha and alpha_channel is not None:
            alpha_resized = process_alpha_channel(alpha_channel, final_size)
            if alpha_resized:
                output_rgba = Image.merge('RGBA', (*output_img.split(), alpha_resized))
                del output_img, alpha_resized
                output_img = output_rgba
                gc.collect()
        
        # Create and save thumbnail FIRST (smaller memory footprint)
        print("Creating thumbnail...")
        thumb = output_img.copy()
        thumb.thumbnail((THUMBNAIL_DIMENSION, THUMBNAIL_DIMENSION), Image.LANCZOS)
        thumb = enhance_thumbnail(thumb)
        
        # Save thumbnail with fast settings
        thumb_bytes = save_image_fast(thumb, is_thumbnail=True)
        del thumb
        gc.collect()
        
        # Start thumbnail upload asynchronously
        print("Starting thumbnail upload...")
        thumb_upload_task = run_sync_in_thread(CloudinaryService.upload_thumbnail, thumb_bytes, job_id)
        
        # Clear thumbnail bytes and prepare main image while upload happens
        del thumb_bytes
        gc.collect()
        
        # Prepare main image
        print("Preparing main image...")
        final_bytes = save_image_fast(output_img, is_thumbnail=False)
        del output_img
        gc.collect()
        
        # Wait for thumbnail upload to complete
        print("Waiting for thumbnail upload...")
        thumb_url, thumb_id = await thumb_upload_task
        print("Thumbnail uploaded successfully!")
        
        # Start main image upload
        print("Starting main image upload...")
        proc_url, proc_id = await run_sync_in_thread(
            CloudinaryService.upload_processed_image,
            final_bytes, 
            job_id, 
            'onnx_upscaled'
        )
        del final_bytes
        gc.collect()
        
        print("All uploads completed successfully!")
        
        # Results
        scale_factor = final_size[0] / original_size[0]
        
        info = {
            "model_used": "ONNX_Memory_Optimized_1CPU",
            "processing_time_s": round(duration, 2),
            "scale_factor": round(scale_factor, 2),
            "original_size": f"{original_size[0]}x{original_size[1]}",
            "output_size": f"{final_size[0]}x{final_size[1]}",
            "thumbnail_url": thumb_url,
            "thumbnail_size": f"{THUMBNAIL_DIMENSION}x{THUMBNAIL_DIMENSION}",
            "full_quality_public_id": proc_id,
            "thumbnail_public_id": thumb_id,
            "is_premium": False,
            "has_transparency": has_alpha,
            "job_id": job_id,
            "timestamp": time.time(),
            "max_dimension_used": MAX_IMAGE_DIMENSION
        }
        
        print(f"Job {job_id} completed successfully!")
        return proc_url, info
        
    except Exception as e:
        print(f"Error in job {job_id}: {str(e)}")
        raise ImageProcessingError(f"Processing failed: {e}")
    finally:
        with _jobs_lock:
            _active_jobs.discard(job_id)
        # Final aggressive cleanup
        gc.collect()

def force_reset_system():
    """Reset system and clear all memory"""
    global _active_jobs, _session
    
    with _jobs_lock:
        _active_jobs.clear()
    
    if _session:
        del _session
        _session = None
    
    # Aggressive cleanup
    gc.collect()
    gc.collect()  # Double collection
    print("System reset completed")

def get_memory_usage():
    """Simple memory info"""
    return {
        "model_loaded": _session is not None,
        "active_jobs": len(_active_jobs),
        "max_dimension": MAX_IMAGE_DIMENSION,
        "thumbnail_dimension": THUMBNAIL_DIMENSION,
        "jpeg_quality": JPEG_QUALITY
    }