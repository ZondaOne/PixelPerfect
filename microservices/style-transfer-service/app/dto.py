"""
Data Transfer Objects (DTOs) for the SDXL style transfer service.
Defines Pydantic models for incoming and outgoing data validation.
"""

from enum import Enum
from typing import Dict, Optional, Any, List
from pydantic import BaseModel, Field, validator

class JobType(str, Enum):
    """Job types supported by the image processing system."""
    BG_REMOVAL = "BG_REMOVAL"
    UPSCALE = "UPSCALE"
    ENLARGE = "ENLARGE"

class JobStatus(str, Enum):
    """Status values for job processing."""
    RECEIVED = "RECEIVED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"

class StyleType(str, Enum):
    """Available art styles for SDXL image style transfer."""
    # Cartoon & Animation
    THREE_D_CHIBI = "3D_Chibi"
    AMERICAN_CARTOON = "American_Cartoon"
    GHIBLI = "Ghibli"
    ANIME = "Anime"
    DISNEY = "Disney"
    PIXAR = "Pixar"
    
    # Traditional Art
    CHINESE_INK = "Chinese_Ink"
    OIL_PAINTING = "Oil_Painting"
    WATERCOLOR = "Watercolor"
    ACRYLIC_PAINTING = "Acrylic_Painting"
    CHARCOAL_DRAWING = "Charcoal_Drawing"
    
    # Famous Artists
    VAN_GOGH = "Van_Gogh"
    PICASSO = "Picasso"
    MONET = "Monet"
    DA_VINCI = "Da_Vinci"
    WARHOL = "Warhol"
    BANKSY = "Banksy"
    
    # Modern Styles
    POP_ART = "Pop_Art"
    STREET_ART = "Street_Art"
    GRAFFITI = "Graffiti"
    COMIC_BOOK = "Comic_Book"
    MANGA = "Manga"
    CONCEPT_ART = "Concept_Art"
    
    # Digital Art
    PIXEL = "Pixel"
    VECTOR = "Vector"
    LOW_POLY = "Low_Poly"
    CYBERPUNK = "Cyberpunk"
    SYNTHWAVE = "Synthwave"
    NEON = "Neon"
    
    # Textures & Materials
    CLAY_TOY = "Clay_Toy"
    FABRIC = "Fabric"
    PAPER_CUTTING = "Paper_Cutting"
    ORIGAMI = "Origami"
    LEGO = "LEGO"
    GLASS_ART = "Glass_Art"
    
    # Artistic Movements
    IMPRESSIONIST = "Impressionist"
    CUBIST = "Cubist"
    SURREAL = "Surreal"
    ABSTRACT = "Abstract"
    MINIMALIST = "Minimalist"
    ART_NOUVEAU = "Art_Nouveau"

class StyleQuality(str, Enum):
    """Quality levels for style transfer."""
    FREE = "FREE"  # Standard quality, 768px, 20 steps
    PREMIUM = "PREMIUM"  # Higher quality, 1024px, 35 steps

class JobMessageDTO(BaseModel):
    """
    DTO for job messages received from RabbitMQ.
    Represents the structure of messages sent by the Spring Boot backend.
    """
    jobId: str
    originalImageId: str
    imageStoragePath: str
    jobType: JobType
    jobConfig: Optional[Dict[str, Any]] = Field(default_factory=dict)

class JobStatusUpdateRequestDTO(BaseModel):
    """
    DTO for sending job status updates back to the Spring Boot backend.
    """
    status: JobStatus
    processedStoragePath: Optional[str] = None
    processingParams: Optional[Dict[str, Any]] = None
    errorMessage: Optional[str] = None

    class Config:
        use_enum_values = True

class StyleTransferConfigDTO(BaseModel):
    """
    DTO for SDXL style transfer configuration parameters.
    Validates the job configuration for style transfer operations.
    """
    style: StyleType = Field(description="Target art style")
    quality: StyleQuality = Field(default=StyleQuality.FREE, description="Quality level for style transfer")
    prompt: Optional[str] = Field(default=None, max_length=500, description="Optional text prompt to guide the style transfer")
    strength: float = Field(default=0.7, ge=0.1, le=1.0, description="Style transfer strength (0.1-1.0)")
    
    # Advanced parameters (optional)
    guidance_scale: Optional[float] = Field(default=None, ge=1.0, le=15.0, description="Guidance scale override")
    inference_steps: Optional[int] = Field(default=None, ge=10, le=50, description="Inference steps override")
    seed: Optional[int] = Field(default=42, ge=0, le=2**32-1, description="Random seed for reproducibility")
    negative_prompt: Optional[str] = Field(default=None, max_length=300, description="Custom negative prompt")
    
    @validator('prompt')
    def validate_prompt(cls, v):
        if v is not None:
            # Remove any potentially problematic content
            forbidden_words = ['nsfw', 'nude', 'naked', 'explicit']
            if any(word in v.lower() for word in forbidden_words):
                raise ValueError("Prompt contains inappropriate content")
        return v
    
    @validator('strength')
    def validate_strength_by_quality(cls, v, values):
        quality = values.get('quality', StyleQuality.FREE)
        if quality == StyleQuality.PREMIUM and v > 0.8:
            # Cap premium strength to prevent over-processing
            return 0.8
        elif quality == StyleQuality.FREE and v < 0.3:
            # Ensure minimum strength for free tier
            return 0.3
        return v
    
    def get_display_style(self) -> str:
        """Get user-friendly style name."""
        return self.style.value.replace("_", " ")
    
    def get_effective_parameters(self) -> Dict[str, Any]:
        """Get the effective parameters after validation and defaults."""
        from app.config import DEFAULT_CONFIG
        
        quality_config = DEFAULT_CONFIG[f"{self.quality.value.lower()}_quality"]
        
        return {
            "style": self.style.value,
            "quality": self.quality.value,
            "strength": self.strength,
            "guidance_scale": self.guidance_scale or quality_config["guidance_scale"],
            "inference_steps": self.inference_steps or quality_config["inference_steps"],
            "max_resolution": quality_config["max_resolution"],
            "seed": self.seed,
            "custom_prompt": self.prompt,
            "custom_negative_prompt": self.negative_prompt
        }

class StyleInfo(BaseModel):
    """Information about a specific art style."""
    name: str
    display_name: str
    category: str
    description: str
    example_prompt: Optional[str] = None
    difficulty: str = Field(default="medium")  # easy, medium, hard
    recommended_strength: tuple[float, float] = Field(default=(0.5, 0.8))

class ProcessingResultDTO(BaseModel):
    """
    DTO for processing results returned by the style transfer function.
    """
    processedImageUrl: str
    thumbnailUrl: str
    originalSize: str
    outputSize: str
    style: str
    styleDisplayName: str
    prompt: Optional[str]
    negativePrompt: Optional[str]
    strength: float
    qualityLevel: str
    inferenceSteps: int
    guidanceScale: float
    processingTimeSeconds: float
    isPremium: bool
    seed: int
    deviceUsed: str
    modelVersion: str

class SystemStatusDTO(BaseModel):
    """System status information."""
    activeJobsCount: int
    activeJobs: List[str]
    pipelineLoaded: bool
    availableStyles: List[str]
    device: str
    modelConfig: Dict[str, Any]
    modelsDirectory: str
    memoryInfo: Dict[str, Any]
    timestamp: float

class StyleCatalogDTO(BaseModel):
    """Complete catalog of available styles with metadata."""
    totalStyles: int
    categories: Dict[str, List[StyleInfo]]
    popularStyles: List[str]
    newStyles: List[str]
    
    @classmethod
    def create_catalog(cls) -> "StyleCatalogDTO":
        """Create a complete style catalog with metadata."""
        
        # Define style categories and metadata
        style_metadata = {
            # Cartoon & Animation
            StyleType.THREE_D_CHIBI: StyleInfo(
                name="3D_Chibi", display_name="3D Chibi", category="Cartoon & Animation",
                description="Cute 3D character style with big eyes and rounded features",
                example_prompt="adorable character, big sparkly eyes, soft lighting",
                difficulty="easy", recommended_strength=(0.6, 0.8)
            ),
            StyleType.AMERICAN_CARTOON: StyleInfo(
                name="American_Cartoon", display_name="American Cartoon", category="Cartoon & Animation",
                description="Western animation style with clean lines and vibrant colors",
                example_prompt="animated character, clean cel shading, bright colors",
                difficulty="easy", recommended_strength=(0.5, 0.7)
            ),
            StyleType.GHIBLI: StyleInfo(
                name="Ghibli", display_name="Studio Ghibli", category="Cartoon & Animation",
                description="Magical anime style inspired by Studio Ghibli films",
                example_prompt="magical atmosphere, detailed background, warm lighting",
                difficulty="medium", recommended_strength=(0.6, 0.8)
            ),
            
            # Traditional Art
            StyleType.OIL_PAINTING: StyleInfo(
                name="Oil_Painting", display_name="Oil Painting", category="Traditional Art",
                description="Classical oil painting with thick brushstrokes and rich colors",
                example_prompt="thick brushstrokes, renaissance style, rich textures",
                difficulty="medium", recommended_strength=(0.5, 0.7)
            ),
            StyleType.WATERCOLOR: StyleInfo(
                name="Watercolor", display_name="Watercolor", category="Traditional Art",
                description="Soft watercolor painting with flowing transparent colors",
                example_prompt="soft flowing colors, paper texture, delicate brushwork",
                difficulty="easy", recommended_strength=(0.4, 0.6)
            ),
            
            # Famous Artists
            StyleType.VAN_GOGH: StyleInfo(
                name="Van_Gogh", display_name="Van Gogh", category="Famous Artists",
                description="Post-impressionist style with swirling brushstrokes",
                example_prompt="swirling brushstrokes, vibrant colors, expressive technique",
                difficulty="hard", recommended_strength=(0.6, 0.8)
            ),
            StyleType.PICASSO: StyleInfo(
                name="Picasso", display_name="Picasso", category="Famous Artists",
                description="Cubist style with geometric forms and abstract representation",
                example_prompt="cubist style, geometric shapes, abstract forms",
                difficulty="hard", recommended_strength=(0.7, 0.9)
            ),
            
            # Digital Art
            StyleType.PIXEL: StyleInfo(
                name="Pixel", display_name="Pixel Art", category="Digital Art",
                description="Retro 8-bit pixel art style",
                example_prompt="8-bit graphics, pixelated, retro gaming style",
                difficulty="medium", recommended_strength=(0.7, 0.9)
            ),
            StyleType.CYBERPUNK: StyleInfo(
                name="Cyberpunk", display_name="Cyberpunk", category="Digital Art",
                description="Futuristic cyberpunk aesthetic with neon and technology",
                example_prompt="neon lights, futuristic technology, dark atmosphere",
                difficulty="medium", recommended_strength=(0.5, 0.7)
            )
        }
        
        # Group styles by category
        categories = {}
        for style_info in style_metadata.values():
            category = style_info.category
            if category not in categories:
                categories[category] = []
            categories[category].append(style_info)
        
        # Define popular and new styles
        popular_styles = ["Ghibli", "Van_Gogh", "Oil_Painting", "American_Cartoon", "Pixel"]
        new_styles = ["Cyberpunk", "Synthwave", "Concept_Art", "Glass_Art"]
        
        return cls(
            totalStyles=len(StyleType),
            categories=categories,
            popularStyles=popular_styles,
            newStyles=new_styles
        )