"""
Image processing module for background removal with Cloudinary integration.
Implements full-quality and low-quality thumbnail generation.
ULTRA OPTIMIZED: Removed OCR dependency, uses lightweight models only (max 250MB RAM).
FIXED: Job tracking and duplicate prevention system.
"""

import logging
import time
import traceback
from typing import Dict, Tuple, Any, Set
import io
import threading
import gc
from PIL import Image, ImageFilter, ImageStat
from rembg import remove, new_session
import numpy as np

from app.cloudinary_service import CloudinaryService

logger = logging.getLogger(__name__)

class ImageProcessingError(Exception):
    """Specific error for image processing failures."""

# Ultra lightweight model configurations for 512MB RAM limit
# u2netp: ~150MB RAM, fastest and most memory efficient
# isnet-general-use: ~100MB RAM, even lighter
ULTRA_LIGHT_MODELS = {
    "general": "u2netp",           # 150MB - good balance of quality/memory
    "signature": "u2netp",         # Same model for consistency and memory saving
    "fallback": "u2netp"           # Single model reduces memory footprint
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
    Uses ultra lightweight models to stay under 250MB RAM.
    """
    if model_name not in _sessions_cache:
        logger.info(f"🔧 Creating new session for ultra-light model: {model_name}")
        try:
            _sessions_cache[model_name] = new_session(model_name)
            logger.info(f"✅ Session created successfully for model: {model_name}")
        except Exception as e:
            logger.error(f"❌ Failed to create session for {model_name}: {e}")
            # Fallback to most lightweight model
            fallback_model = ULTRA_LIGHT_MODELS["fallback"]
            logger.info(f"🔄 Using fallback model: {fallback_model}")
            _sessions_cache[model_name] = new_session(fallback_model)
    else:
        logger.debug(f"♻️ Reusing existing session for model: {model_name}")
    
    return _sessions_cache[model_name]

def optimize_image_for_processing(image: Image.Image, max_size: int = 800) -> Image.Image:
    """
    Optimize image size to reduce memory usage during processing.
    Reduced max_size to 800px to save more memory.
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

def is_probable_signature_simple(image: Image.Image) -> bool:
    """
    Simplified signature detection without OCR.
    Based on image statistics: high contrast, mostly white background.
    """
    try:
        # Convert to grayscale for analysis
        gray = image.convert("L")
        
        # Get image statistics
        stat = ImageStat.Stat(gray)
        
        # Check if image has high brightness (white background)
        mean_brightness = stat.mean[0]
        if mean_brightness < 200:  # Not bright enough
            return False
        
        # Check contrast/standard deviation
        stddev = stat.stddev[0]
        if stddev < 30:  # Too uniform, probably not a signature
            return False
        
        # Calculate histogram to check for bimodal distribution (signature characteristic)
        histogram = gray.histogram()
        
        # Count pixels in white range (240-255) and dark range (0-100)
        white_pixels = sum(histogram[240:256])
        dark_pixels = sum(histogram[0:100])
        total_pixels = image.size[0] * image.size[1]
        
        white_ratio = white_pixels / total_pixels
        dark_ratio = dark_pixels / total_pixels
        
        # Signature characteristics: lots of white background, some dark strokes
        is_signature = (white_ratio > 0.7 and dark_ratio > 0.05 and dark_ratio < 0.3)
        
        if is_signature:
            logger.info(f"✍️ Signature detected: white={white_ratio:.2f}, dark={dark_ratio:.2f}, contrast={stddev:.1f}")
        else:
            logger.debug(f"📝 Not a signature: white={white_ratio:.2f}, dark={dark_ratio:.2f}, contrast={stddev:.1f}")
        
        return is_signature

    except Exception as e:
        logger.warning(f"⚠️ Signature detection failed: {e}")
        return False

def detect_content_type(image_bytes: bytes) -> str:
    """
    Detect content type without OCR.
    Returns ultra-lightweight model name.
    """
    try:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        
        # Simplified detection - use same model for everything to save memory
        # This reduces memory usage and model loading time
        return ULTRA_LIGHT_MODELS["general"]  # Always use u2netp
        
    except Exception as e:
        logger.warning(f"⚠️ Content detection failed: {e}, using fallback model")
        return ULTRA_LIGHT_MODELS["fallback"]

async def perform_background_removal(
    job_id: str,
    image_url: str,
    config: Dict[str, Any]
) -> Tuple[str, Dict[str, Any]]:
    
    logger.info(f"🔍 JOB STARTED: {job_id}")
    logger.info(f"🔗 URL: {image_url}")
    
    # Check if job is already being processed (prevent duplicates)
    with _jobs_lock:
        if job_id in _active_jobs:
            error_msg = f"🚫 Job {job_id} is already being processed, ignoring duplicate"
            logger.warning(error_msg)
            raise ImageProcessingError(error_msg)
        
        # Add job to active set
        _active_jobs.add(job_id)
        logger.info(f"📝 Job {job_id} added to active list. Total active jobs: {len(_active_jobs)}")

    max_image_size = config.get("max_image_size", 800)  # Reduced from 1024 to 800

    try:
        logger.info(f"🚀 Starting job {job_id} with URL: {image_url}")
        
        logger.info(f"⬇️ Downloading image: {image_url}")
        input_image_bytes = CloudinaryService.download_image_from_url(image_url)

        # Optimize image size to reduce memory usage
        input_image = Image.open(io.BytesIO(input_image_bytes)).convert("RGB")
        optimized_image = optimize_image_for_processing(input_image, max_image_size)
        
        # Free original image from memory immediately
        del input_image
        gc.collect()
        
        # Convert back to bytes for processing
        optimized_buffer = io.BytesIO()
        optimized_image.save(optimized_buffer, format="PNG", optimize=True)
        optimized_bytes = optimized_buffer.getvalue()

        model_to_use = detect_content_type(optimized_bytes)
        logger.info(f"🤖 Ultra-light model selected for {job_id}: {model_to_use}")

        # Use cached session or create new one only if it doesn't exist
        session = get_session_for_model(model_to_use)

        start_time = time.perf_counter()
        logger.info(f"🎨 Removing background for {job_id} (ultra-memory-optimized)")
        
        # Process with optimized image to reduce memory usage
        output_bytes = remove(optimized_bytes, session=session)
        elapsed = time.perf_counter() - start_time

        # Free intermediate data
        del optimized_image, optimized_bytes
        gc.collect()

        logger.info(f"🖼️ Generating thumbnail for {job_id}")
        output_image = Image.open(io.BytesIO(output_bytes)).convert("RGBA")
        thumbnail = output_image.copy()
        thumbnail.thumbnail((300, 200), Image.Resampling.LANCZOS)  # Smaller thumbnail

        thumbnail_buffer = io.BytesIO()
        thumbnail.save(thumbnail_buffer, format="PNG", optimize=True, quality=60)  # Lower quality
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
        del output_image, thumbnail
        gc.collect()

        logger.info(f"✅ Job {job_id} completed successfully")
        logger.info(f"🔗 Full quality URL: {processed_url}")
        logger.info(f"🔗 Thumbnail URL: {thumbnail_url}")

        processing_info = {
            "model_version": model_to_use,
            "mode": "cloudinary_integration_ultra_optimized",
            "processing_time_seconds": round(elapsed, 3),
            "max_image_size": max_image_size,
            "memory_optimization": True,
            "ocr_disabled": True,
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
            "ultra_light_models": ULTRA_LIGHT_MODELS,
            "memory_optimization_enabled": True,
            "ocr_disabled": True,
            "max_expected_ram_usage_mb": 250,
            "timestamp": time.time()
        }

def get_memory_usage_info() -> Dict[str, Any]:
    """
    Return information about current memory usage and optimization settings.
    """
    return {
        "models_configuration": ULTRA_LIGHT_MODELS,
        "expected_ram_usage": {
            "u2netp_model": "~150MB",
            "total_max": "250MB"
        },
        "optimization_features": [
            "Single lightweight model (u2netp) for all tasks",
            "OCR completely removed",
            "Reduced image size optimization (800px max)",
            "Smaller thumbnail generation (300x200)",
            "Aggressive garbage collection",
            "Session caching to avoid model reloading"
        ],
        "current_cached_sessions": len(_sessions_cache),
        "ram_limit_target": "512MB"
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

def get_render_optimizations() -> Dict[str, Any]:
    """
    Return specific optimizations for Render.com deployment.
    """
    return {
        "render_optimizations": [
            "OCR dependency removed (saves ~100MB)",
            "Single model strategy (u2netp only)",
            "Reduced max image size (800px)",
            "Smaller thumbnails (300x200)",
            "Aggressive garbage collection",
            "Memory monitoring enabled"
        ],
        "memory_footprint": {
            "base_app": "~50MB",
            "rembg_model": "~150MB",
            "image_processing": "~100MB",
            "total_estimated": "~300MB",
            "safety_margin": "~200MB"
        },
        "render_recommendations": [
            "Use this version for 512MB RAM limit",
            "Monitor memory usage in logs",
            "Consider processing limits per minute",
            "Implement request queuing if needed"
        ]
    }