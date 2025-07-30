import os
import time
import threading
import gc
import io
import requests
import numpy as np
import asyncio
import concurrent.futures
from PIL import Image, ImageFilter, ImageEnhance
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

# Balanced optimization for Render free tier - quality vs speed
MAX_IMAGE_DIMENSION = 200   # Better quality, still manageable
THUMBNAIL_DIMENSION = 180   # Better thumbnails
JPEG_QUALITY = 80          # Better quality output
MAX_CONCURRENT_JOBS = 1    # Only one job at a time
CHUNK_SIZE = 2048          # Smaller download chunks
TIMEOUT = 15               # Shorter timeouts

# Global variables
_active_jobs = set()
_jobs_lock = threading.Lock()
_session = None
_model_cache = {}

async def run_sync_in_thread(func, *args, **kwargs):
    """Execute sync function in separate thread"""
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        return await loop.run_in_executor(executor, func, *args, **kwargs)

def download_model_fast(url: str, path: str):
    """Fast model download with aggressive optimization"""
    if os.path.exists(path):
        return
        
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        print("Downloading model (optimized)...")
        start = time.perf_counter()
        
        # Use session with connection pooling
        session = requests.Session()
        session.headers.update({'User-Agent': 'ImageProcessor/1.0'})
        
        resp = session.get(url, stream=True, timeout=TIMEOUT)
        resp.raise_for_status()
        
        with open(path, 'wb') as f:
            for chunk in resp.iter_content(CHUNK_SIZE):
                if chunk:
                    f.write(chunk)
        
        duration = time.perf_counter() - start
        size_mb = os.path.getsize(path) // 1024 // 1024
        print(f"Model downloaded in {duration:.1f}s ({size_mb}MB)")
        
    except Exception as e:
        if os.path.exists(path):
            os.remove(path)
        raise ImageProcessingError(f"Download failed: {e}")

def get_session_optimized() -> ort.InferenceSession:
    """Get ultra-optimized ONNX session for Render free tier"""
    global _session
    
    if _session is None:
        download_model_fast(FREE_MODEL_URL, FREE_MODEL_PATH)
        
        # Extreme memory optimization for 512MB RAM
        opts = ort.SessionOptions()
        opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_DISABLE_ALL  # Disable optimizations that use RAM
        opts.enable_mem_pattern = False
        opts.enable_cpu_mem_arena = False  # Critical for low RAM
        opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        opts.inter_op_num_threads = 1  # Single thread
        opts.intra_op_num_threads = 1  # Single thread
        
        # Minimal providers for speed
        providers = [('CPUExecutionProvider', {
            'arena_extend_strategy': 'kSameAsRequested',
            'enable_cpu_mem_arena': False,
            'use_arena': False
        })]
        
        _session = ort.InferenceSession(FREE_MODEL_PATH, opts, providers)
        print("ONNX session created with extreme optimization")
    
    return _session

def upscale_adaptive_chunks(img_arr: np.ndarray) -> np.ndarray:
    """Adaptive chunking based on image size and available memory"""
    session = get_session_optimized()
    h, w, c = img_arr.shape
    total_pixels = h * w
    
    # Small images: process directly (up to 100x100)
    if total_pixels <= 10000:
        return upscale_direct(img_arr, session)
    
    # Medium images: split in 2x2 (100x100 to 200x200)
    elif total_pixels <= 40000:
        return upscale_in_chunks(img_arr, session, 2, 2)
    
    # Large images: split in 3x3 (200x200+)
    else:
        return upscale_in_chunks(img_arr, session, 3, 3)

def upscale_in_chunks(img_arr: np.ndarray, session, rows: int, cols: int) -> np.ndarray:
    """Process image in NxM chunks with proper edge handling"""
    h, w, c = img_arr.shape
    
    # Calculate chunk sizes with overlap to avoid seams
    chunk_h = h // rows
    chunk_w = w // cols
    overlap = 4  # Small overlap to blend edges
    
    # Pre-allocate output
    output = np.zeros((h * 4, w * 4, c), dtype=np.uint8)
    
    print(f"Processing in {rows}x{cols} chunks ({chunk_h}x{chunk_w} each)...")
    
    for i in range(rows):
        for j in range(cols):
            print(f"Processing chunk {i*cols + j + 1}/{rows*cols}...")
            
            # Calculate chunk boundaries with overlap
            y_start = max(0, i * chunk_h - overlap)
            y_end = min(h, (i + 1) * chunk_h + overlap)
            x_start = max(0, j * chunk_w - overlap)
            x_end = min(w, (j + 1) * chunk_w + overlap)
            
            # Extract chunk
            chunk = img_arr[y_start:y_end, x_start:x_end]
            
            # Process chunk
            processed_chunk = upscale_direct(chunk, session)
            
            # Calculate output position (accounting for overlap removal)
            out_y_start = i * chunk_h * 4
            out_y_end = out_y_start + (y_end - y_start - 2*overlap) * 4
            out_x_start = j * chunk_w * 4  
            out_x_end = out_x_start + (x_end - x_start - 2*overlap) * 4
            
            # Remove overlap from processed chunk
            crop_top = overlap * 4 if i > 0 else 0
            crop_bottom = processed_chunk.shape[0] - overlap * 4 if i < rows - 1 else processed_chunk.shape[0]
            crop_left = overlap * 4 if j > 0 else 0
            crop_right = processed_chunk.shape[1] - overlap * 4 if j < cols - 1 else processed_chunk.shape[1]
            
            cropped_chunk = processed_chunk[crop_top:crop_bottom, crop_left:crop_right]
            
            # Place in output
            actual_h, actual_w = cropped_chunk.shape[:2]
            output[out_y_start:out_y_start + actual_h, out_x_start:out_x_start + actual_w] = cropped_chunk
            
            # Aggressive cleanup after each chunk
            del processed_chunk, cropped_chunk, chunk
            gc.collect()
    
    return output

def upscale_direct(img_arr: np.ndarray, session) -> np.ndarray:
    """Direct upscaling with immediate cleanup"""
    # Normalize in-place
    input_tensor = img_arr.astype(np.float32)
    input_tensor /= 255.0
    input_tensor = input_tensor.transpose(2, 0, 1)[None, ...]
    
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

def smart_resize_for_quality(img: Image.Image) -> Image.Image:
    """Smart resize balancing quality and performance"""
    w, h = img.size
    pixels = w * h
    
    # Don't resize small images - keep original quality
    if pixels <= 10000:  # 100x100
        print(f"Small image ({w}x{h}) - keeping original size")
        return img
    
    # Only resize if necessary for memory management
    if max(w, h) > MAX_IMAGE_DIMENSION:
        scale = MAX_IMAGE_DIMENSION / max(w, h)
        new_w = max(32, int(w * scale))  # Minimum 32px for decent quality
        new_h = max(32, int(h * scale))
        
        # Use high-quality LANCZOS for better results
        resized = img.resize((new_w, new_h), Image.LANCZOS)
        print(f"Quality-balanced resize: {w}x{h} -> {new_w}x{new_h}")
        return resized
    
    return img

def enhance_thumbnail_quality(img: Image.Image) -> Image.Image:
    """Better thumbnail enhancement balancing speed and quality"""
    # Apply both contrast and sharpness for better results
    contrast_enhancer = ImageEnhance.Contrast(img)
    contrast_enhanced = contrast_enhancer.enhance(1.15)
    
    sharpness_enhancer = ImageEnhance.Sharpness(contrast_enhanced)
    final_enhanced = sharpness_enhancer.enhance(1.1)
    
    return final_enhanced

def save_image_balanced(img, is_thumbnail=False):
    """Balanced image saving - better quality while maintaining speed"""
    buf = io.BytesIO()
    
    if img.mode == 'RGBA':
        # PNG with moderate compression for better quality
        img.save(buf, format='PNG', optimize=True, compress_level=6)
    else:
        # JPEG with better quality
        quality = 90 if is_thumbnail else JPEG_QUALITY
        img.save(buf, format='JPEG', quality=quality, optimize=True, progressive=False)
    
    result = buf.getvalue()
    buf.close()
    return result

async def perform_upscaling(job_id: str, image_url: str, config: dict):
    """Ultra-optimized upscaling for Render free tier (1 CPU, 512MB RAM)"""
    with _jobs_lock:
        if len(_active_jobs) >= MAX_CONCURRENT_JOBS:
            raise ImageProcessingError("Max concurrent jobs reached")
        if job_id in _active_jobs:
            raise ImageProcessingError(f"Job {job_id} already active")
        _active_jobs.add(job_id)

    try:
        print(f"Starting ultra-optimized job {job_id}")
        total_start = time.perf_counter()
        
        # Aggressive cleanup at start
        gc.collect()
        
        # Fast download
        print("Downloading image...")
        download_start = time.perf_counter()
        input_bytes = CloudinaryService.download_image_from_url(image_url)
        img = Image.open(io.BytesIO(input_bytes))
        original_size = img.size
        download_time = time.perf_counter() - download_start
        print(f"Downloaded {original_size} in {download_time:.1f}s")
        
        # Clear input bytes immediately
        del input_bytes
        gc.collect()
        
        # Handle transparency efficiently
        has_alpha = img.mode in ('RGBA', 'LA', 'P')
        alpha_channel = None
        
        if has_alpha:
            if img.mode == 'P':
                img = img.convert('RGBA')
            alpha_channel = img.split()[-1]
            img_rgb = img.convert('RGB')
            del img
            img = img_rgb
        else:
            img = img.convert('RGB')
        
        gc.collect()
        
        # Smart resize balancing quality and performance
        img = smart_resize_for_quality(img)
        print(f"Processing size: {img.size}")
        
        # Adaptive upscaling based on image size
        print("Starting adaptive upscale...")
        upscale_start = time.perf_counter()
        
        img_arr = np.array(img)
        del img
        gc.collect()
        
        # Use adaptive chunking strategy
        output_arr = upscale_adaptive_chunks(img_arr)
        
        upscale_time = time.perf_counter() - upscale_start
        print(f"Upscale completed in {upscale_time:.1f}s")
        
        del img_arr
        gc.collect()
        
        # Convert to PIL
        output_img = Image.fromarray(output_arr, 'RGB')
        final_size = output_img.size
        del output_arr
        gc.collect()
        
        # Handle alpha channel if needed
        if has_alpha and alpha_channel is not None:
            alpha_resized = alpha_channel.resize(final_size, Image.LANCZOS)  # Better quality
            output_rgba = Image.merge('RGBA', (*output_img.split(), alpha_resized))
            del output_img, alpha_resized, alpha_channel
            output_img = output_rgba
            gc.collect()
        
        # Create thumbnail with better quality
        print("Creating quality thumbnail...")
        thumb_start = time.perf_counter()
        
        thumb = output_img.copy()
        thumb.thumbnail((THUMBNAIL_DIMENSION, THUMBNAIL_DIMENSION), Image.LANCZOS)
        thumb = enhance_thumbnail_quality(thumb)
        
        thumb_bytes = save_image_balanced(thumb, is_thumbnail=True)
        del thumb
        gc.collect()
        
        thumb_time = time.perf_counter() - thumb_start
        print(f"Thumbnail created in {thumb_time:.1f}s")
        
        # Start async uploads
        print("Starting uploads...")
        upload_start = time.perf_counter()
        
        # Upload thumbnail
        thumb_upload_task = run_sync_in_thread(CloudinaryService.upload_thumbnail, thumb_bytes, job_id)
        
        # Prepare main image with better quality
        final_bytes = save_image_balanced(output_img, is_thumbnail=False)
        del output_img
        gc.collect()
        
        # Wait for thumbnail upload
        thumb_url, thumb_id = await thumb_upload_task
        del thumb_bytes
        
        # Upload main image
        proc_url, proc_id = await run_sync_in_thread(
            CloudinaryService.upload_processed_image,
            final_bytes, 
            job_id, 
            'onnx_speed_optimized'
        )
        del final_bytes
        gc.collect()
        
        upload_time = time.perf_counter() - upload_start
        total_time = time.perf_counter() - total_start
        
        print(f"Uploads completed in {upload_time:.1f}s")
        print(f"Total job time: {total_time:.1f}s")
        
        # Results with timing breakdown
        scale_factor = final_size[0] / original_size[0]
        
        info = {
            "model_used": "ONNX_Quality_Balanced_Render",
            "processing_time_s": round(upscale_time, 1),
            "total_time_s": round(total_time, 1),
            "download_time_s": round(download_time, 1),
            "thumbnail_time_s": round(thumb_time, 1),
            "upload_time_s": round(upload_time, 1),
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
            "max_dimension_used": MAX_IMAGE_DIMENSION,
            "optimization_level": "quality_balanced"
        }
        
        print(f"Job {job_id} completed successfully in {total_time:.1f}s!")
        return proc_url, info
        
    except Exception as e:
        print(f"Error in job {job_id}: {str(e)}")
        raise ImageProcessingError(f"Processing failed: {e}")
    finally:
        with _jobs_lock:
            _active_jobs.discard(job_id)
        # Final cleanup
        gc.collect()

def force_reset_system():
    """Reset system and clear all memory"""
    global _active_jobs, _session, _model_cache
    
    with _jobs_lock:
        _active_jobs.clear()
    
    if _session:
        del _session
        _session = None
    
    _model_cache.clear()
    
    # Triple garbage collection for Render free tier
    gc.collect()
    gc.collect()
    gc.collect()
    print("System reset for Render free tier")

def get_memory_usage():
    """Memory info optimized for Render monitoring"""
    return {
        "model_loaded": _session is not None,
        "active_jobs": len(_active_jobs),
        "max_dimension": MAX_IMAGE_DIMENSION,
        "thumbnail_dimension": THUMBNAIL_DIMENSION,
        "jpeg_quality": JPEG_QUALITY,
        "optimization_target": "render_free_tier_512mb",
        "concurrent_limit": MAX_CONCURRENT_JOBS
    }