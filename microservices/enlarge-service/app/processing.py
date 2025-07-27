import logging
import os
import cv2
import numpy as np

from typing import Dict, Tuple, Any, Literal
from PIL import Image, ImageFilter
import torch
from diffusers import StableDiffusionInpaintPipeline, DPMSolverMultistepScheduler
import gc

from app.cloudinary_service import CloudinaryService
from app.config import MODELS_DIR
from app.local_image_processing import LocalImageProcessor

logger = logging.getLogger(__name__)

class ImageProcessingError(Exception):
    """Custom exception for image processing errors."""
    pass

AspectRatio = Literal["portrait", "landscape", "square"]

class MVPGenerativeFillProcessor:
    """MVP Ultra ligero - Solo Stable Diffusion con configuración mejorada para outpainting horizontal y vertical"""

    def __init__(self):
        self.device = "cpu"
        self.max_resolution = 640  # Resolución conservadora (ya es múltiplo de 8)
        self.model_loaded = False
        
        # Initialize pipeline first
        try:
            # Replace "your-model-name" with the actual model you want to use
            self.pipeline = StableDiffusionInpaintPipeline.from_pretrained(
                "runwayml/stable-diffusion-inpainting",  # or your preferred model
                torch_dtype=torch.float32,  # Use float32 for CPU
                device_map="cpu"
            )
            
            # Now you can safely configure the scheduler
            self.pipeline.scheduler = DPMSolverMultistepScheduler.from_config(
                self.pipeline.scheduler.config
            )
            
            self.model_loaded = True
            
        except Exception as e:
            print(f"Error loading pipeline: {e}")
            self.pipeline = None
            self.model_loaded = False
       
        self.base_prompts = {
    "landscape": (
        "only grass field, only green lawn, only outdoor ground, "
        "no people, no objects, no buildings, just grass surface, "
        "simple natural ground, empty field, minimal scene"
    ),
    
    "portrait": (
        "only background extension, only ground surface, only grass, "
        "no people, no additional objects, no crowd, "
        "simple outdoor background, clean environment"
    ),
    
    "square": (
        "only background extension, only grass surface, only outdoor field, "
        "no people, no objects, no spectators, no crowd, "
        "simple clean background, minimal natural scene"
        
    )
}

        self.negative_prompt = (
    "people, humans, persons, men, women, children, crowd, spectators, "
    "audience, photographers, multiple objects, cars, vehicles, "
    "buildings, complex scene, busy environment, detailed background"
)



        logger.info(f"Device: {self.device}")
        if torch.cuda.is_available():
            vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            logger.info(f"VRAM: {vram_gb:.1f} GB")

    def _clear_memory(self):
        """Limpieza agresiva de memoria CUDA"""
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
        gc.collect()

    def _load_model(self) -> bool:
        """Cargar solo un modelo ultra liviano"""
        if self.model_loaded:
            return True

        try:
            logger.info("Loading ultra-light SD 1.5 inpainting model...")
            self._clear_memory()

            # Usar el modelo más liviano posible
            self.pipeline = StableDiffusionInpaintPipeline.from_pretrained(
                "runwayml/stable-diffusion-inpainting",
                torch_dtype=torch.float16,  # Half precision para ahorrar VRAM
                safety_checker=None,
                requires_safety_checker=False,
                cache_dir=MODELS_DIR,
                low_cpu_mem_usage=True,
                variant="fp16"
            ).to(self.device)

            # Optimizaciones extremas para RTX 2050
            self.pipeline.enable_attention_slicing("max")
            self.pipeline.enable_sequential_cpu_offload()
            self.pipeline.enable_model_cpu_offload()
            self.pipeline.enable_vae_slicing()

            # Intentar usar xformers si está disponible
            try:
                self.pipeline.enable_xformers_memory_efficient_attention()
                logger.info("XFormers enabled for memory efficiency")
            except Exception:
                logger.info("XFormers not available, using default attention")

            self.model_loaded = True
            logger.info("Model loaded successfully!")
            return True

        except Exception as e:
            logger.error(f"Model loading failed: {e}")
            self._clear_memory()
            return False

    def _round_to_multiple_of_8(self, value: int) -> int:
        """Redondear a múltiplo de 8 (requerido por Stable Diffusion)"""
        return ((value + 7) // 8) * 8

    def _calculate_target_dimensions(self, width: int, height: int, aspect: AspectRatio) -> Tuple[int, int]:
        """Calcular dimensiones objetivo para agrandar la imagen según el aspect ratio deseado"""
        max_size = self.max_resolution
        
        # Factor de agrandamiento - siempre expandir al menos un 30-50%
        expansion_factor = 1.4  # Agranda la imagen un 40%
        
        if aspect == "square":
            # Para square, crear un cuadrado más grande que la imagen original
            base_size = max(width, height) * expansion_factor
            target_w = target_h = int(base_size)
            
            # Si excede el límite, escalar manteniendo proporción cuadrada
            if target_w > max_size:
                target_w = target_h = max_size
                
        elif aspect == "portrait":
            # Portrait (3:4 ratio) - crear imagen más grande en formato portrait
            desired_ratio = 3/4  # width/height
            
            # Expandir basándose en la dimensión mayor actual
            base_dimension = max(width, height) * expansion_factor
            
            # Calcular dimensiones para portrait manteniendo el ratio
            target_h = int(base_dimension)
            target_w = int(target_h * desired_ratio)
            
            # Asegurar que sea más grande que la imagen original
            if target_w < width * 1.2:
                target_w = int(width * 1.3)
                target_h = int(target_w / desired_ratio)
            if target_h < height * 1.2:
                target_h = int(height * 1.3)
                target_w = int(target_h * desired_ratio)
            
            # Aplicar límite de resolución
            if target_h > max_size:
                scale = max_size / target_h
                target_w = int(target_w * scale)
                target_h = int(target_h * scale)
                
        elif aspect == "landscape":
            # Landscape (4:3 ratio) - crear imagen más grande en formato landscape
            desired_ratio = 4/3  # width/height
            
            # Expandir basándose en la dimensión mayor actual
            base_dimension = max(width, height) * expansion_factor
            
            # Calcular dimensiones para landscape manteniendo el ratio
            target_w = int(base_dimension)
            target_h = int(target_w / desired_ratio)
            
            # Asegurar que sea más grande que la imagen original
            if target_w < width * 1.2:
                target_w = int(width * 1.3)
                target_h = int(target_w / desired_ratio)
            if target_h < height * 1.2:
                target_h = int(height * 1.3)
                target_w = int(target_h * desired_ratio)
            
            # Aplicar límite de resolución
            if target_w > max_size:
                scale = max_size / target_w
                target_w = int(target_w * scale)
                target_h = int(target_h * scale)
        else:
            # Fallback: simplemente agranda manteniendo proporción original
            scale_factor = expansion_factor
            target_w = int(width * scale_factor)
            target_h = int(height * scale_factor)
            
            if target_w > max_size or target_h > max_size:
                scale = min(max_size / target_w, max_size / target_h)
                target_w = int(target_w * scale)
                target_h = int(target_h * scale)
            
        # CRÍTICO: Asegurar que sean múltiplos de 8
        target_w = self._round_to_multiple_of_8(target_w)
        target_h = self._round_to_multiple_of_8(target_h)
        
        return target_w, target_h

    def _analyze_image_content(self, image: np.ndarray) -> str:
        """Analizar el contenido de la imagen para generar un prompt más específico"""
        # Análisis básico de colores dominantes
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Calcular colores promedio en diferentes regiones
        h, w = image_rgb.shape[:2]
        
        # Región superior (cielo potencial)
        top_region = image_rgb[:h//3, :]
        top_avg = np.mean(top_region, axis=(0, 1))
        
        # Región inferior (suelo potencial)
        bottom_region = image_rgb[2*h//3:, :]
        bottom_avg = np.mean(bottom_region, axis=(0, 1))
        
        # Determinar tipo de escena basado en colores
        content_hints = []
        
        # Si la parte superior es azulada, probablemente hay cielo
        if top_avg[2] > top_avg[0] and top_avg[2] > top_avg[1]:  # Más azul
            content_hints.append("blue sky")
        elif top_avg[0] > 200 and top_avg[1] > 200 and top_avg[2] > 200:  # Muy claro
            content_hints.append("bright sky")
        
        # Si la parte inferior es verdosa/marrón, probablemente hay tierra/vegetación
        if bottom_avg[1] > bottom_avg[2]:  # Más verde que azul
            content_hints.append("natural ground with vegetation")
        elif bottom_avg[0] > bottom_avg[1] and bottom_avg[0] > bottom_avg[2]:  # Más rojo/marrón
            content_hints.append("earth tones ground")
        
        return ", ".join(content_hints) if content_hints else "natural environment"

    def _create_canvas_and_mask(self, image: np.ndarray, target_w: int, target_h: int, aspect: AspectRatio) -> Tuple[Image.Image, Image.Image, Tuple[int, int, int, int]]:
        """Crear canvas y máscara optimizada para expansión según aspect ratio
        
        Returns:
            canvas: Canvas con imagen y fondo
            mask: Máscara para inpainting
            original_bounds: (x_offset, y_offset, width, height) de la imagen original en el canvas
        """
        original_h, original_w = image.shape[:2]
    
        # VERIFICAR que las dimensiones objetivo sean múltiplos de 8
        assert target_w % 8 == 0 and target_h % 8 == 0, f"Target dimensions must be divisible by 8, got {target_w}x{target_h}"
    
        # Convertir imagen original a PIL RGB
        if len(image.shape) == 3:
            original_pil = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        else:
            original_pil = Image.fromarray(image)

        # Si la imagen original es más grande que el target, escalamos
        if original_w > target_w or original_h > target_h:
            scale = min(target_w / original_w, target_h / original_h)
            new_w = int(original_w * scale)
            new_h = int(original_h * scale)
            original_pil = original_pil.resize((new_w, new_h), Image.Resampling.LANCZOS)
        else:
            new_w, new_h = original_w, original_h

        # CREAR CANVAS CON CONTENIDO INTELIGENTE EN LUGAR DE GRADIENTE
        canvas = Image.new('RGB', (target_w, target_h))
        
        # Posicionamiento según aspect ratio
        if aspect == "portrait":
            x_offset = (target_w - new_w) // 2
            y_offset = int((target_h - new_h) * 0.6)  # Más hacia abajo
        elif aspect == "landscape":
            x_offset = (target_w - new_w) // 2
            y_offset = (target_h - new_h) // 2
        else:  # square
            x_offset = (target_w - new_w) // 2
            y_offset = (target_h - new_h) // 2

        # Asegurar offsets válidos
        x_offset = max(0, min(x_offset, target_w - new_w))
        y_offset = max(0, min(y_offset, target_h - new_h))

        # CREAR FONDO INTELIGENTE basado en los bordes de la imagen original
        canvas_array = np.array(canvas)
        original_array = np.array(original_pil)
        
        # Extender los bordes de la imagen original para crear un fondo más natural
        # Usar los píxeles del borde para crear un fondo extendido
        
        # Borde superior
        if y_offset > 0:
            top_edge = original_array[0:min(10, new_h//4), :]  # Tomar los primeros píxeles
            top_avg_color = np.mean(top_edge, axis=(0, 1)).astype(np.uint8)
            canvas_array[0:y_offset, :] = top_avg_color
        
        # Borde inferior
        if y_offset + new_h < target_h:
            bottom_edge = original_array[max(0, new_h-10):new_h, :]  # Tomar los últimos píxeles
            bottom_avg_color = np.mean(bottom_edge, axis=(0, 1)).astype(np.uint8)
            canvas_array[y_offset + new_h:target_h, :] = bottom_avg_color
        
        # Borde izquierdo
        if x_offset > 0:
            left_edge = original_array[:, 0:min(10, new_w//4)]
            left_avg_color = np.mean(left_edge, axis=(0, 1)).astype(np.uint8)
            canvas_array[:, 0:x_offset] = left_avg_color
        
        # Borde derecho
        if x_offset + new_w < target_w:
            right_edge = original_array[:, max(0, new_w-10):new_w]
            right_avg_color = np.mean(right_edge, axis=(0, 1)).astype(np.uint8)
            canvas_array[:, x_offset + new_w:target_w] = right_avg_color
    
        canvas = Image.fromarray(canvas_array)

        # Pegar la imagen original
        canvas.paste(original_pil, (x_offset, y_offset))

        # CREAR MÁSCARA MÁS AGRESIVA Y CLARA
        mask_array = np.zeros((target_h, target_w), dtype=np.uint8)

        # Marcar todas las áreas que NO son la imagen original como áreas a generar
        # Área superior
        if y_offset > 0:
            mask_array[0:y_offset, :] = 255
        
        # Área inferior
        if y_offset + new_h < target_h:
            mask_array[y_offset + new_h:target_h, :] = 255
        
        # Área izquierda
        if x_offset > 0:
            mask_array[:, 0:x_offset] = 255
        
        # Área derecha
        if x_offset + new_w < target_w:
            mask_array[:, x_offset + new_w:target_w] = 255

        # ZONA DE TRANSICIÓN MÁS AMPLIA para mejor blending
        transition_size = min(15, min(new_w, new_h) // 6)
        
        if transition_size > 2:
            # Crear gradiente de transición en los bordes de la imagen original
            for i in range(transition_size):
                alpha = int(255 * (i + 1) / transition_size)
                
                # Transición superior
                if y_offset > 0 and (y_offset + new_h - 1 - i) >= y_offset:
                    row = y_offset + new_h - 1 - i
                    if row < target_h:
                        mask_array[row, x_offset:x_offset + new_w] = alpha
                
                # Transición inferior
                if y_offset + new_h < target_h and (y_offset + i) < target_h:
                    row = y_offset + i
                    mask_array[row, x_offset:x_offset + new_w] = alpha
                
                # Transición izquierda
                if x_offset > 0 and (x_offset + new_w - 1 - i) >= x_offset:
                    col = x_offset + new_w - 1 - i
                    if col < target_w:
                        mask_array[y_offset:y_offset + new_h, col] = alpha
                
                # Transición derecha
                if x_offset + new_w < target_w and (x_offset + i) < target_w:
                    col = x_offset + i
                    mask_array[y_offset:y_offset + new_h, col] = alpha

        mask = Image.fromarray(mask_array)
        
        # APLICAR BLUR A LA MÁSCARA para transiciones más suaves
        mask = mask.filter(ImageFilter.GaussianBlur(radius=1.5))

        # Guardar los bounds de la imagen original para la superposición posterior
        original_bounds = (x_offset, y_offset, new_w, new_h)

        logger.info(f"Canvas created: {canvas.width}x{canvas.height}")
        logger.info(f"Original placed at ({x_offset},{y_offset}) with size {new_w}x{new_h}")
        
        # Verificar que la máscara tiene áreas a generar
        mask_array_final = np.array(mask)
        generate_pixels = np.sum(mask_array_final > 128)
        logger.info(f"Pixels to generate: {generate_pixels} ({generate_pixels/(target_w*target_h)*100:.1f}%)")
        
        return canvas, mask, original_bounds

    def _generate_fill(self, canvas: Image.Image, mask: Image.Image, aspect: AspectRatio, original_image: np.ndarray) -> Image.Image:
        """Generar el fill usando prompt específico para el aspecto y contenido de la imagen"""
        try:
            self._clear_memory()

            canvas_w, canvas_h = canvas.width, canvas.height
            
            # Analizar contenido de la imagen original para prompt más específico
            content_description = self._analyze_image_content(original_image)
            
            # Combinar prompt base con análisis de contenido
            base_prompt = self.base_prompts.get(aspect, self.base_prompts["square"])
            enhanced_prompt = f"{base_prompt}, {content_description}"
            
            logger.info(f"Generating with enhanced prompt for {aspect}")
            logger.info(f"Content analysis: {content_description}")
            logger.info(f"Canvas dimensions: {canvas_w}x{canvas_h}")

            # CONFIGURACIÓN OPTIMIZADA para generative fill efectivo
            result = self.pipeline(
            prompt=enhanced_prompt,
            negative_prompt=self.negative_prompt,
            image=canvas,
            mask_image=mask,
            num_inference_steps=30,        # Más pasos
            guidance_scale=12,              # Intermedio - ni muy alto ni muy bajo
            strength=0.99,                  # Intermedio - suficiente para generar
            eta=0.0,
            height=canvas_h,
            width=canvas_w,
            
        ).images[0]

            logger.info("Fill generation completed")
            return result

        except Exception as e:
            logger.error(f"Fill generation failed: {e}")
            raise
        finally:
            self._clear_memory()

    def _create_blended_overlay(self, original_image: np.ndarray, ai_generated: Image.Image, 
                              original_bounds: Tuple[int, int, int, int], 
                              blend_margin: int = 10) -> np.ndarray:
        """
        Superpone la imagen original sobre el resultado de IA con blending suave en los bordes
        
        Args:
            original_image: Imagen original en formato numpy (BGR)
            ai_generated: Imagen generada por IA en formato PIL (RGB)
            original_bounds: (x_offset, y_offset, width, height) de donde estaba la imagen original
            blend_margin: Margen en píxeles para el blending suave
        
        Returns:
            Imagen final con la original superpuesta sobre el fondo generado
        """
        x_offset, y_offset, orig_w, orig_h = original_bounds
        
        # Convertir AI generated a numpy BGR
        ai_array = np.array(ai_generated)
        ai_bgr = cv2.cvtColor(ai_array, cv2.COLOR_RGB2BGR)
        
        # Escalar la imagen original al tamaño que tenía en el canvas
        original_h, original_w = original_image.shape[:2]
        if (orig_w, orig_h) != (original_w, original_h):
            original_resized = cv2.resize(original_image, (orig_w, orig_h), interpolation=cv2.INTER_LANCZOS4)
        else:
            original_resized = original_image.copy()
        
        # Crear resultado base con la imagen de IA
        result = ai_bgr.copy()
        
        # Si no hay margen de blending, simplemente pegar la imagen original encima
        if blend_margin <= 0:
            result[y_offset:y_offset+orig_h, x_offset:x_offset+orig_w] = original_resized
            logger.info("Original image overlaid without blending")
            return result
        
        # Crear máscara de blending suave
        mask = np.ones((orig_h, orig_w), dtype=np.float32)
        
        # Aplicar gradiente suave en los bordes
        for i in range(blend_margin):
            alpha = i / blend_margin
            
            # Borde superior
            if i < orig_h:
                mask[i, :] = alpha
            
            # Borde inferior
            if orig_h - 1 - i >= 0:
                mask[orig_h - 1 - i, :] = np.minimum(mask[orig_h - 1 - i, :], alpha)
            
            # Borde izquierdo
            if i < orig_w:
                mask[:, i] = np.minimum(mask[:, i], alpha)
            
            # Borde derecho
            if orig_w - 1 - i >= 0:
                mask[:, orig_w - 1 - i] = np.minimum(mask[:, orig_w - 1 - i], alpha)
        
        # Aplicar blur suave a la máscara para transiciones más naturales
        mask = cv2.GaussianBlur(mask, (5, 5), 0)
        
        # Expandir la máscara a 3 canales
        mask_3ch = np.stack([mask, mask, mask], axis=2)
        
        # Extraer la región de la imagen de IA donde va la original
        ai_region = result[y_offset:y_offset+orig_h, x_offset:x_offset+orig_w].astype(np.float32)
        original_float = original_resized.astype(np.float32)
        
        # Realizar el blending: resultado = original * mask + ai * (1 - mask)
        blended_region = (original_float * mask_3ch + ai_region * (1 - mask_3ch)).astype(np.uint8)
        
        # Colocar la región blended en el resultado final
        result[y_offset:y_offset+orig_h, x_offset:x_offset+orig_w] = blended_region
        
        logger.info(f"Original image overlaid with {blend_margin}px soft blending")
        return result

    def _resize_input_if_larger(self, image: np.ndarray, target_w: int, target_h: int) -> np.ndarray:
            """
            Redimensiona la imagen de entrada si es más grande que el tamaño objetivo
            manteniendo la proporción y asegurando que no exceda las dimensiones objetivo.
            
            Args:
                image: Imagen de entrada en formato numpy (BGR)
                target_w: Ancho objetivo
                target_h: Alto objetivo
                
            Returns:
                Imagen redimensionada si era necesario, o la original si ya era del tamaño correcto
            """
            original_h, original_w = image.shape[:2]
            
            # Si la imagen es más pequeña o igual al objetivo, no hacer nada
            if original_w <= target_w and original_h <= target_h:
                logger.info(f"Input image {original_w}x{original_h} fits within target {target_w}x{target_h}, no resizing needed")
                return image
            
            # Calcular factor de escala para que quepa dentro del target manteniendo proporción
            scale_w = target_w / original_w
            scale_h = target_h / original_h
            scale = min(scale_w, scale_h)  # Usar el menor para que quepa completamente
            
            # Calcular nuevas dimensiones
            new_w = int(original_w * scale)
            new_h = int(original_h * scale)
            
            # Asegurar que sean múltiplos de 8 (requerido por Stable Diffusion)
            new_w = self._round_to_multiple_of_8(new_w)
            new_h = self._round_to_multiple_of_8(new_h)
            
            # Redimensionar usando interpolación de alta calidad
            resized_image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
            
            logger.info(f"Input image resized from {original_w}x{original_h} to {new_w}x{new_h} (scale: {scale:.3f})")
            
            return resized_image



    def process(self, input_image: np.ndarray, target_aspect: AspectRatio, 
                preserve_original: bool = True, blend_margin: int = 10) -> np.ndarray:
        """
        Función principal de procesamiento - siempre agranda la imagen
        
        Args:
            input_image: Imagen de entrada
            target_aspect: Aspecto deseado (portrait, landscape, square)
            preserve_original: Si True, superpone la imagen original sobre el resultado
            blend_margin: Margen en píxeles para el blending suave (0 = sin blending)
        """
        try:
            # Cargar modelo
            if not self._load_model():
                raise RuntimeError("Failed to load the inpainting model")

            h, w = input_image.shape[:2]
            logger.info(f"Processing image: {w}x{h} -> {target_aspect} (enlarging)")

            # Calcular dimensiones objetivo (siempre más grandes)
            target_w, target_h = self._calculate_target_dimensions(w, h, target_aspect)
            logger.info(f"Target dimensions: {target_w}x{target_h} (expansion factor: {target_w/w:.1f}x{target_h/h:.1f})")

            input_image = self._resize_input_if_larger(input_image, target_w, target_h)
        
        # Actualizar dimensiones después del posible redimensionado
            h, w = input_image.shape[:2]
            
            # Verificar que efectivamente sea un agrandamiento
            if target_w <= w and target_h <= h:
                # Si por alguna razón no se agrandó, forzar agrandamiento mínimo
                logger.warning("Target dimensions not larger than original, forcing enlargement")
                scale_factor = 1.3
                target_w = self._round_to_multiple_of_8(int(w * scale_factor))
                target_h = self._round_to_multiple_of_8(int(h * scale_factor))
                logger.info(f"Forced target dimensions: {target_w}x{target_h}")

            # Crear canvas y máscara para agrandamiento
            canvas, mask, original_bounds = self._create_canvas_and_mask(input_image, target_w, target_h, target_aspect)

            # Generar el fill con prompt específico
            result_pil = self._generate_fill(canvas, mask, target_aspect, input_image)

            # Si preserve_original está habilitado, superponer la imagen original
            if preserve_original:
                logger.info("Overlaying original image to preserve quality")
                result_bgr = self._create_blended_overlay(
                    input_image, result_pil, original_bounds, blend_margin
                )
            else:
                # Convertir de vuelta a numpy array (BGR para OpenCV) sin superposición
                result_array = np.array(result_pil)
                result_bgr = cv2.cvtColor(result_array, cv2.COLOR_RGB2BGR)

            logger.info(f"Processing completed successfully - enlarged from {w}x{h} to {target_w}x{target_h}")
            if preserve_original:
                logger.info("Original image preserved with quality overlay")
            
            return result_bgr

        except Exception as e:
            logger.error(f"Processing failed: {e}")
            raise
        finally:
            self._clear_memory()


# Función principal mejorada
async def perform_image_enlargement(
    job_id: str,
    image_url: str,
    config: Dict[str, Any]
) -> Tuple[str, Dict[str, Any]]:
    """Función principal del MVP con mejoras de expansión horizontal y vertical"""

    processor = None
    try:
        # Crear directorio de modelos
        os.makedirs(MODELS_DIR, exist_ok=True)

        # Descargar imagen
        logger.info(f"Downloading image for job {job_id}")
        image_bytes = CloudinaryService.download_image_from_url(image_url)

        # Decodificar imagen
        nparr = np.frombuffer(image_bytes, np.uint8)
        input_image = cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)

        if input_image is None:
            raise ValueError("Failed to decode image")

        # Configuración
        aspect_ratio = config.get('aspectRatio', 'square')
        if aspect_ratio not in ("portrait", "landscape", "square"):
            logger.warning(f"Invalid aspectRatio '{aspect_ratio}' received; defaulting to 'square'")
            aspect_ratio = "square"

        # NUEVAS OPCIONES DE CONFIGURACIÓN
        preserve_original = config.get('preserveOriginal', True)  # Por defecto True
        blend_margin = config.get('blendMargin', 8)  # Margen de blending por defecto

        # Crear procesador mejorado
        logger.info("Initializing enhanced MVP Generative Fill processor")
        processor = MVPGenerativeFillProcessor()

        # Procesar imagen con nuevas opciones
        output_image = processor.process(
            input_image, 
            aspect_ratio, 
            preserve_original=preserve_original,
            blend_margin=blend_margin
        )

        # Codificar resultado
        encode_params = [cv2.IMWRITE_PNG_COMPRESSION, 6]
        is_success, buffer = cv2.imencode('.png', output_image, encode_params)

        if not is_success:
            raise RuntimeError("Failed to encode output image")

        output_bytes = buffer.tobytes()

        # Crear thumbnail
        h, w = output_image.shape[:2]
        thumb_scale = min(300 / w, 300 / h, 1.0)

        if thumb_scale < 1.0:
            new_w = int(w * thumb_scale)
            new_h = int(h * thumb_scale)
            thumbnail = cv2.resize(output_image, (new_w, new_h), interpolation=cv2.INTER_AREA)
        else:
            thumbnail = output_image.copy()

        is_success, thumb_buffer = cv2.imencode('.png', thumbnail)
        if not is_success:
            raise RuntimeError("Failed to encode thumbnail")

        thumbnail_bytes = thumb_buffer.tobytes()

        logger.info(f"🖼️ Generating thumbnail locally for {job_id}")
        # Create thumbnail locally for better quality control
        thumbnail_bytes = LocalImageProcessor.create_thumbnail(output_bytes)
        
        # Optimize premium image
        optimized_premium_bytes = LocalImageProcessor.optimize_premium_image(output_bytes)
        
        logger.info(f"☁️ Uploading premium optimized image to Cloudinary for {job_id}")
        processed_url, processed_public_id = CloudinaryService.upload_processed_image(
            optimized_premium_bytes, job_id, "generative_fill"
        )
        
        logger.info(f"☁️ Uploading thumbnail to Cloudinary for {job_id}")
        thumbnail_url, thumbnail_public_id = CloudinaryService.upload_thumbnail(
            thumbnail_bytes, job_id
        )

        # Información del procesamiento
        original_h, original_w = input_image.shape[:2]
        output_h, output_w = output_image.shape[:2]

        processing_info = {
            "processing_type": "image_enlargement_with_generative_fill",
            "model": "stable-diffusion-inpainting",
            "prompt_used": processor.base_prompts.get(aspect_ratio, "natural landscape"),
            "aspect_ratio": aspect_ratio,
            "original_size": f"{original_w}x{original_h}",
            "output_size": f"{output_w}x{output_h}",
            "expansion_factor": f"{output_w/original_w:.1f}x{output_h/original_h:.1f}",
            "preserve_original": preserve_original,
            "blend_margin": blend_margin if preserve_original else None,
            "full_quality_public_id": processed_public_id,
            "thumbnail_public_id": thumbnail_public_id,
            "thumbnail_url": thumbnail_url,
            "local_thumbnail_generated": True,
            "thumbnail_size_bytes": len(thumbnail_bytes),
            "premium_size_bytes": len(optimized_premium_bytes),
            "mode": "hybrid_secure_integration",
            "device_used": processor.device,
            "improvements": "intelligent_content_analysis_enhanced_masking_and_original_overlay"
        }

        logger.info(f"Job {job_id} completed successfully with enhanced generative fill and original overlay")
        return processed_url, processing_info

    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}")
        raise ImageProcessingError(f"Enhanced generative fill processing failed: {e}")

    finally:
        # Limpieza global
        if processor is not None:
            processor._clear_memory()