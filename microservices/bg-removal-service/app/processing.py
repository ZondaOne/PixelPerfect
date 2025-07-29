import os
import time
import threading
import gc
import io
import requests
import numpy as np
from PIL import Image
import onnxruntime as ort
import cv2

from app.cloudinary_service import CloudinaryService

# Exception for processing errors
class ImageProcessingError(Exception):
    pass

# Configuration\ n# URL to download ONNX model (U2-Net small) from rembg GitHub releases
MODEL_URL = os.getenv(
    "ONNX_MODEL_URL",
    "https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2netp.onnx"
)
# Local path to save the downloaded model
MODEL_PATH = os.getenv("ONNX_MODEL_PATH", "models/u2netp.onnx")

MAX_IMAGE_DIMENSION = 500
MAX_THUMBNAIL_DIMENSION = 400
PNG_COMPRESSION = 9
MAX_CONCURRENT_JOBS = 1
_active_jobs = set()
_jobs_lock = threading.Lock()
MODEL_SESSION = None


def download_model():
    """Download the ONNX model from remote URL if not present locally."""
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    try:
        resp = requests.get(MODEL_URL, stream=True, timeout=30)
        resp.raise_for_status()
        with open(MODEL_PATH, 'wb') as f:
            for chunk in resp.iter_content(8192):
                f.write(chunk)
    except Exception as e:
        raise ImageProcessingError(f"Failed to download ONNX model: {e}")


def load_model():
    """Load ONNX model with minimal memory footprint, auto-downloading if missing."""
    global MODEL_SESSION
    if MODEL_SESSION is None:
        # Ensure model file exists
        if not os.path.isfile(MODEL_PATH):
            download_model()

        sess_opts = ort.SessionOptions()
        sess_opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_EXTENDED
        # Disable memory pattern for tighter footprint
        sess_opts.enable_mem_pattern = False
        # Enable CPU arena for efficient allocations
        sess_opts.enable_cpu_mem_arena = True

        MODEL_SESSION = ort.InferenceSession(MODEL_PATH, sess_opts, providers=["CPUExecutionProvider"])
    return MODEL_SESSION


def emergency_cleanup():
    try:
        cv2.destroyAllWindows()
    except:
        pass
    gc.collect()


def optimize_image(img: Image.Image) -> np.ndarray:
    """Resize and convert PIL image to RGB numpy array."""
    w, h = img.size
    scale = min(1.0, MAX_IMAGE_DIMENSION / max(w, h))
    if scale < 1.0:
        img = img.resize((int(w*scale), int(h*scale)), Image.Resampling.LANCZOS)
    if img.mode != 'RGB':
        img = img.convert('RGB')
    arr = np.array(img, dtype=np.float32)
    arr = arr.transpose(2, 0, 1) / 255.0  # CHW, normalized
    return arr


def predict_mask_onnx(img_arr: np.ndarray) -> np.ndarray:
    """Run ONNX model to get a segmentation mask."""
    session = load_model()
    input_name = session.get_inputs()[0].name
    _, H, W = img_arr.shape
    target_size = 320
    img_resized = cv2.resize(img_arr.transpose(1,2,0), (target_size, target_size))
    inp = np.expand_dims(img_resized.transpose(2,0,1).astype(np.float32), 0)
    outputs = session.run(None, {input_name: inp})
    mask = outputs[0][0,0,:,:]
    mask = cv2.resize(mask, (W, H))
    # Normalize & threshold
    mask = (mask - mask.min())/(mask.max() - mask.min() + 1e-8)
    mask = (mask * 255).astype(np.uint8)
    _, binary = cv2.threshold(mask, 128, 255, cv2.THRESH_BINARY)
    return binary


def composite_foreground(img_rgb: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Combine RGB image and binary mask to RGBA output with smooth alpha."""
    h, w = mask.shape
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    rgba[:, :, :3] = (img_rgb.transpose(1,2,0) * 255).astype(np.uint8)
    # Smooth edges for better blending
    mask_blur = cv2.GaussianBlur(mask, (5,5), 0)
    rgba[:, :, 3] = mask_blur
    return rgba

async def perform_background_removal(job_id: str, image_url: str, config: dict):
    with _jobs_lock:
        if len(_active_jobs) >= MAX_CONCURRENT_JOBS:
            raise ImageProcessingError("Max concurrent jobs reached")
        if job_id in _active_jobs:
            raise ImageProcessingError(f"Job {job_id} already active")
        _active_jobs.add(job_id)

    try:
        input_bytes = CloudinaryService.download_image_from_url(image_url)
        img = Image.open(io.BytesIO(input_bytes))
        img.load()
        del input_bytes

        img_arr = optimize_image(img)

        start = time.perf_counter()
        mask = predict_mask_onnx(img_arr)
        duration = time.perf_counter() - start

        output_arr = composite_foreground(img_arr, mask)

        out_img = Image.fromarray(output_arr, 'RGBA')
        thumb = out_img.copy()
        thumb.thumbnail((MAX_THUMBNAIL_DIMENSION, MAX_THUMBNAIL_DIMENSION), Image.Resampling.LANCZOS)

        buf = io.BytesIO()
        out_img.save(buf, format='PNG', optimize=True, compress_level=PNG_COMPRESSION)
        final_bytes = buf.getvalue()

        tbuf = io.BytesIO()
        thumb.save(tbuf, format='PNG', optimize=True, compress_level=PNG_COMPRESSION)
        thumb_bytes = tbuf.getvalue()

        proc_url, proc_id = CloudinaryService.upload_processed_image(final_bytes, job_id, 'onnx_bg_removed')
        thumb_url, thumb_id = CloudinaryService.upload_thumbnail(thumb_bytes, job_id)

        info = {
            "model_path": MODEL_PATH,
            "processing_time_s": round(duration, 3),
            "thumbnail_url": thumb_url,
            "full_quality_public_id": proc_id,
            "thumbnail_public_id": thumb_id,
            "job_id": job_id,
            "timestamp": time.time()
        }
        return proc_url, info
    except Exception as e:
        raise ImageProcessingError(f"ONNX background removal failed: {e}")
    finally:
        with _jobs_lock:
            _active_jobs.discard(job_id)
        emergency_cleanup()


def force_reset_system():
    global _active_jobs
    with _jobs_lock:
        _active_jobs.clear()
    emergency_cleanup()
