"""
Image processing module for background removal with Cloudinary integration.
Uses a single ultra-lightweight model (u2netp) for optimized memory usage.
"""

import logging
import time
import traceback
from typing import Dict, Tuple, Any, Set
import io
import threading
import gc
from PIL import Image
from rembg import remove, new_session

from app.cloudinary_service import CloudinaryService

logger = logging.getLogger(__name__)

class ImageProcessingError(Exception):
    """Specific error for image processing failures."""

# Use only u2netp model
MODEL_NAME = "u2netp"

_sessions_cache: Dict[str, Any] = {}
_active_jobs: Set[str] = set()
_jobs_lock = threading.Lock()

def clear_sessions_cache():
    logger.info("🧹 Clearing rembg sessions cache")
    for session in list(_sessions_cache.values()):
        try:
            del session
        except Exception:
            pass
    _sessions_cache.clear()
    gc.collect()
    logger.info("🧹 Sessions cache cleared and memory freed")

def clear_active_jobs():
    global _active_jobs
    with _jobs_lock:
        logger.info("🧹 Clearing active jobs list")
        _active_jobs.clear()

def get_session():
    if MODEL_NAME not in _sessions_cache:
        logger.info(f"🔧 Creating new session for model: {MODEL_NAME}")
        try:
            _sessions_cache[MODEL_NAME] = new_session(MODEL_NAME)
            logger.info(f"✅ Session created successfully for model: {MODEL_NAME}")
        except Exception as e:
            logger.error(f"❌ Failed to create session for {MODEL_NAME}: {e}")
            raise ImageProcessingError(f"Failed to create rembg session: {e}")
    else:
        logger.debug(f"♻️ Reusing existing session for model: {MODEL_NAME}")
    return _sessions_cache[MODEL_NAME]

def optimize_image_for_processing(image: Image.Image, max_size: int = 800) -> Image.Image:
    width, height = image.size
    if max(width, height) <= max_size:
        return image
    if width > height:
        new_width = max_size
        new_height = int((height * max_size) / width)
    else:
        new_height = max_size
        new_width = int((width * max_size) / height)
    resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
    logger.info(f"🔄 Image optimized from {width}x{height} to {new_width}x{new_height}")
    return resized

async def perform_background_removal(
    job_id: str,
    image_url: str,
    config: Dict[str, Any]
) -> Tuple[str, Dict[str, Any]]:
    
    logger.info(f"🔍 JOB STARTED: {job_id}")
    logger.info(f"🔗 URL: {image_url}")
    
    with _jobs_lock:
        if job_id in _active_jobs:
            error_msg = f"🚫 Job {job_id} is already being processed, ignoring duplicate"
            logger.warning(error_msg)
            raise ImageProcessingError(error_msg)
        _active_jobs.add(job_id)
        logger.info(f"📝 Job {job_id} added to active list. Total active jobs: {len(_active_jobs)}")

    max_image_size = config.get("max_image_size", 400)

    try:
        logger.info(f"🚀 Starting job {job_id} with URL: {image_url}")
        input_image_bytes = CloudinaryService.download_image_from_url(image_url)
        input_image = Image.open(io.BytesIO(input_image_bytes)).convert("RGB")
        optimized_image = optimize_image_for_processing(input_image, max_image_size)
        del input_image
        gc.collect()
        
        optimized_buffer = io.BytesIO()
        optimized_image.save(optimized_buffer, format="PNG", optimize=True)
        optimized_bytes = optimized_buffer.getvalue()

        session = get_session()

        start_time = time.perf_counter()
        logger.info(f"🎨 Removing background for {job_id} using model {MODEL_NAME}")
        output_bytes = remove(optimized_bytes, session=session)
        elapsed = time.perf_counter() - start_time

        del optimized_image, optimized_bytes
        gc.collect()

        output_image = Image.open(io.BytesIO(output_bytes)).convert("RGBA")
        thumbnail = output_image.copy()
        thumbnail.thumbnail((300, 200), Image.Resampling.LANCZOS)

        thumbnail_buffer = io.BytesIO()
        thumbnail.save(thumbnail_buffer, format="PNG", optimize=True, quality=60)
        thumbnail_bytes = thumbnail_buffer.getvalue()

        processed_url, processed_public_id = CloudinaryService.upload_processed_image(
            output_bytes, job_id, "bg_removed"
        )
        thumbnail_url, thumbnail_public_id = CloudinaryService.upload_thumbnail(
            thumbnail_bytes, job_id
        )

        del output_image, thumbnail
        gc.collect()

        logger.info(f"✅ Job {job_id} completed successfully")
        logger.info(f"🔗 Full quality URL: {processed_url}")
        logger.info(f"🔗 Thumbnail URL: {thumbnail_url}")

        processing_info = {
            "model_version": MODEL_NAME,
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
        with _jobs_lock:
            _active_jobs.discard(job_id)
            logger.info(f"🗑️ Job {job_id} removed from active list. Remaining jobs: {len(_active_jobs)}")
        # Limpiar memoria al final para no acumular caché y liberar referencias
        clear_active_jobs()
        clear_sessions_cache()
        gc.collect()

def get_system_status() -> Dict[str, Any]:
    with _jobs_lock:
        return {
            "active_jobs_count": len(_active_jobs),
            "active_jobs": list(_active_jobs),
            "cached_models": list(_sessions_cache.keys()),
            "cached_sessions_count": len(_sessions_cache),
            "model_in_use": MODEL_NAME,
            "memory_optimization_enabled": True,
            "ocr_disabled": True,
            "max_expected_ram_usage_mb": 250,
            "timestamp": time.time()
        }

def force_reset_system():
    logger.warning("🚨 FORCED SYSTEM RESET")
    clear_active_jobs()
    clear_sessions_cache()
    gc.collect()
    logger.warning("🚨 System completely reset and memory freed")
