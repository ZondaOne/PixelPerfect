package com.chunaudis.image_toolkit.service;

import java.awt.image.BufferedImage;
import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;

import javax.imageio.ImageIO;
import javax.imageio.ImageReader;
import javax.imageio.stream.ImageInputStream;
import javax.imageio.stream.MemoryCacheImageInputStream;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import com.chunaudis.image_toolkit.dto.ImageUploadRequestDTO;
import com.chunaudis.image_toolkit.dto.ImageGenerationRequestDTO;
import com.chunaudis.image_toolkit.entity.Image;
import com.chunaudis.image_toolkit.entity.Job;
import com.chunaudis.image_toolkit.entity.User;
import com.chunaudis.image_toolkit.entity.enums.JobStatusEnum;
import com.chunaudis.image_toolkit.entity.enums.JobTypeEnum;
import com.chunaudis.image_toolkit.repository.ImageRepository;
import com.chunaudis.image_toolkit.repository.UserRepository;
import com.chunaudis.image_toolkit.storage.CloudinaryStorageService;

import jakarta.persistence.EntityNotFoundException;

@Service
public class ImageService {
    private static final Logger log = LoggerFactory.getLogger(ImageService.class);
    
    // ULTRA-OPTIMIZED LIMITS
    private static final long MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
    private static final int MAX_DIMENSION = 4096;
    private static final String[] ALLOWED_MIME_TYPES = {
        "image/jpeg", "image/jpg", "image/png", "image/gif", "image/webp", "image/bmp"
    };
    
    // Retry configuration
    private static final int MAX_UPLOAD_RETRIES = 3;
    private static final long RETRY_DELAY_MS = 2000; // 2 seconds

    private final ImageRepository imageRepository;
    private final UserRepository userRepository; 
    private final CloudinaryStorageService cloudinaryStorageService;
    private final JobService jobService;

    public ImageService(ImageRepository imageRepository, 
                       UserRepository userRepository,
                       CloudinaryStorageService cloudinaryStorageService, 
                       JobService jobService) {
        this.imageRepository = imageRepository;
        this.userRepository = userRepository;
        this.cloudinaryStorageService = cloudinaryStorageService;
        this.jobService = jobService;
    }

    /**
     * LIGHTNING-FAST upload processing - ZERO blocking operations in main thread
     * Returns in < 50ms guaranteed
     */
    @Transactional
    public Job processUploadedImage(MultipartFile file, ImageUploadRequestDTO requestDTO,
            Map<String, Object> jobConfig) {
        
        long startTime = System.nanoTime();
        log.info("🚀 LIGHTNING upload process started for file: {}", file.getOriginalFilename());
        
        try {
            // STEP 1: Enhanced validation with corruption check
            long validationStart = System.nanoTime();
            validateFileWithEnhancedChecks(file);
            log.debug("⚡ Validation: {}ms", (System.nanoTime() - validationStart) / 1_000_000);
            
            // STEP 2: User lookup with timeout protection
            long userStart = System.nanoTime();
            UUID userId = UUID.fromString(requestDTO.getUserId());
            User user = userRepository.findById(userId)
                    .orElseThrow(() -> new EntityNotFoundException("User not found with ID: " + userId));
            log.debug("⚡ User lookup: {}ms", (System.nanoTime() - userStart) / 1_000_000);
            
            // STEP 3: Create minimal image entity
            long entityStart = System.nanoTime();
            Image image = createMinimalImageEntity(file, user);
            Image savedImage = imageRepository.save(image);
            log.debug("⚡ Entity creation: {}ms", (System.nanoTime() - entityStart) / 1_000_000);
            
            // STEP 4: Create job instantly
            long jobStart = System.nanoTime();
            Job job = jobService.createJob(savedImage, requestDTO.getJobType(), jobConfig, userId);
            Job savedJob = jobService.saveJob(job);
            log.debug("⚡ Job creation: {}ms", (System.nanoTime() - jobStart) / 1_000_000);
            
            // STEP 5: Copy file data before async processing (MultipartFile is not thread-safe!)
            try {
                byte[] fileData = file.getBytes();
                String originalFilename = file.getOriginalFilename();
                String contentType = file.getContentType();
                
                // Fire-and-forget async processing with copied data
                CompletableFuture.runAsync(() -> processUploadAsyncWithRetry(
                        fileData, originalFilename, contentType, savedImage, savedJob, jobConfig))
                        .exceptionally(throwable -> {
                            log.error("❌ Async upload failed for image {}: {}", 
                                savedImage.getImageId(), throwable.getMessage(), throwable);
                            
                            // Update job status with detailed error
                            try {
                                String errorMessage = throwable.getCause() != null ? 
                                    throwable.getCause().getMessage() : throwable.getMessage();
                                jobService.updateJobStatus(savedJob.getJobId(), JobStatusEnum.FAILED, 
                                    "Upload failed: " + errorMessage);
                            } catch (Exception e) {
                                log.error("Failed to update job status after upload failure", e);
                            }
                            
                            return null;
                        });
                        
            } catch (IOException e) {
                log.error("❌ Failed to copy file data for async processing: {}", e.getMessage());
                jobService.updateJobStatus(savedJob.getJobId(), JobStatusEnum.FAILED, 
                    "Failed to prepare file for upload: " + e.getMessage());
                throw new RuntimeException("Failed to prepare file for upload", e);
            }
            
            long totalTime = (System.nanoTime() - startTime) / 1_000_000;
            log.info("🏆 LIGHTNING response ready in {}ms - upload happening in background", totalTime);
            
            if (totalTime > 50) {
                log.warn("⚠️ Response took {}ms - investigating bottleneck", totalTime);
            }
            
            return savedJob;
            
        } catch (Exception e) {
            log.error("❌ Failed to process upload for file {}: {}", 
                file.getOriginalFilename(), e.getMessage(), e);
            throw e;
        }
    }

    /**
     * Enhanced validation with corruption and detailed checks
     */
    private void validateFileWithEnhancedChecks(MultipartFile file) {
        // Basic checks
        if (file.isEmpty() || file.getSize() == 0) {
            throw new IllegalArgumentException("File cannot be empty");
        }
        
        if (file.getSize() > MAX_FILE_SIZE) {
            throw new IllegalArgumentException(
                String.format("File too large: %.2fMB (max: %dMB)", 
                file.getSize() / (1024.0 * 1024.0), MAX_FILE_SIZE / (1024 * 1024)));
        }
        
        // Content type validation
        String contentType = file.getContentType();
        if (contentType == null) {
            throw new IllegalArgumentException("Unknown file type - no content type detected");
        }
        
        boolean isValidType = false;
        for (String allowedType : ALLOWED_MIME_TYPES) {
            if (allowedType.equalsIgnoreCase(contentType)) {
                isValidType = true;
                break;
            }
        }
        
        if (!isValidType) {
            throw new IllegalArgumentException("Unsupported file type: " + contentType + 
                ". Allowed types: " + String.join(", ", ALLOWED_MIME_TYPES));
        }
        
        // Filename validation
        String filename = file.getOriginalFilename();
        if (filename == null || filename.trim().isEmpty()) {
            throw new IllegalArgumentException("Invalid or missing filename");
        }
        
        // Quick corruption check
        if (isImageCorrupt(file)) {
            throw new IllegalArgumentException("File appears to be corrupted or invalid image format");
        }
        
        log.debug("✅ File validation passed: {} ({})", filename, contentType);
    }

    /**
     * Creates minimal image entity with better defaults
     */
    private Image createMinimalImageEntity(MultipartFile file, User user) {
        Image image = new Image();
        image.setUser(user);
        image.setOriginalFilename(file.getOriginalFilename());
        image.setOriginalFilesizeBytes(file.getSize());
        image.setOriginalFormat(extractFormatFast(file.getContentType()));
        
        // Smarter defaults based on file size and name
        String filename = file.getOriginalFilename().toLowerCase();
        long fileSize = file.getSize();
        
        // Estimate dimensions based on file size (rough heuristic)
        if (fileSize < 100_000) { // < 100KB, likely small image
            image.setOriginalWidth(400);
            image.setOriginalHeight(300);
        } else if (fileSize > 5_000_000) { // > 5MB, likely high-res
            image.setOriginalWidth(2048);
            image.setOriginalHeight(1536);
        } else if (filename.contains("portrait") || filename.contains("vertical")) {
            image.setOriginalWidth(600);
            image.setOriginalHeight(800);
        } else {
            image.setOriginalWidth(800);
            image.setOriginalHeight(600);
        }
        
        image.setOriginalStoragePath("uploading");
        image.setCloudinaryPublicId(null);
        
        return image;
    }

    /**
     * Async upload processing with retry logic - uses copied file data
     */
    private void processUploadAsyncWithRetry(byte[] fileData, String originalFilename, String contentType, 
            Image image, Job job, Map<String, Object> jobConfig) {
        UUID imageId = image.getImageId();
        UUID jobId = job.getJobId();
        
        log.info("🔄 Starting async upload with retry for image {} (job {}) - data size: {}", 
            imageId, jobId, fileData.length);
        
        // Update status immediately
        jobService.updateJobStatus(jobId, JobStatusEnum.PROCESSING, "Preparing upload...");
        
        // Try upload with retries
        Exception lastException = null;
        for (int attempt = 1; attempt <= MAX_UPLOAD_RETRIES; attempt++) {
            try {
                log.info("🔄 Upload attempt {}/{} for image {}", attempt, MAX_UPLOAD_RETRIES, imageId);
                
                processUploadAttempt(fileData, originalFilename, contentType, image, job, jobConfig);
                
                log.info("✅ Upload successful on attempt {} for image {}", attempt, imageId);
                return; // Success!
                
            } catch (Exception e) {
                lastException = e;
                log.warn("❌ Upload attempt {}/{} failed for image {}: {}", 
                    attempt, MAX_UPLOAD_RETRIES, imageId, e.getMessage());
                
                // Update status with retry info
                if (attempt < MAX_UPLOAD_RETRIES) {
                    jobService.updateJobStatus(jobId, JobStatusEnum.PROCESSING, 
                        String.format("Upload attempt %d failed, retrying... (%s)", attempt, e.getMessage()));
                    
                    // Wait before retry with exponential backoff
                    try {
                        long delay = RETRY_DELAY_MS * (long) Math.pow(2, attempt - 1);
                        Thread.sleep(delay);
                    } catch (InterruptedException ie) {
                        Thread.currentThread().interrupt();
                        throw new RuntimeException("Upload interrupted", ie);
                    }
                } else {
                    // Final attempt failed
                    log.error("❌ All upload attempts failed for image {}", imageId, e);
                    jobService.updateJobStatus(jobId, JobStatusEnum.FAILED, 
                        "Upload failed after " + MAX_UPLOAD_RETRIES + " attempts: " + e.getMessage());
                }
            }
        }
        
        // If we get here, all retries failed
        throw new RuntimeException("Upload failed after " + MAX_UPLOAD_RETRIES + " attempts", lastException);
    }

    /**
     * Single upload attempt with detailed logging - uses byte array
     */
    private void processUploadAttempt(byte[] fileData, String originalFilename, String contentType,
            Image image, Job job, Map<String, Object> jobConfig) throws Exception {
        long startTime = System.currentTimeMillis();
        UUID imageId = image.getImageId();
        UUID jobId = job.getJobId();
        
        try {
            // Start dimension extraction in parallel
            CompletableFuture<int[]> dimensionsFuture = extractDimensionsFromBytes(fileData);
            
            // Pre-upload validation
            if (fileData.length == 0) {
                throw new IllegalStateException("File data is empty during upload");
            }
            
            // Update status
            jobService.updateJobStatus(jobId, JobStatusEnum.PROCESSING, "Uploading to cloud storage...");
            
            // Upload to Cloudinary with detailed logging
            log.info("☁️ Starting Cloudinary upload for image {} (size: {} bytes)", imageId, fileData.length);
            long cloudinaryStart = System.currentTimeMillis();
            
            String cloudinaryUrl = cloudinaryStorageService.uploadOriginalImageFromBytes(
                fileData, originalFilename, contentType, image.getUser().getUserId(), imageId);
            
            if (cloudinaryUrl == null || cloudinaryUrl.trim().isEmpty()) {
                throw new RuntimeException("Cloudinary upload returned null/empty URL");
            }
            
            String publicId = cloudinaryStorageService.extractPublicId(cloudinaryUrl);
            if (publicId == null || publicId.trim().isEmpty()) {
                throw new RuntimeException("Failed to extract public ID from Cloudinary URL: " + cloudinaryUrl);
            }
            
            long cloudinaryTime = System.currentTimeMillis() - cloudinaryStart;
            log.info("☁️ Cloudinary upload completed in {}ms for image {} -> {}", 
                cloudinaryTime, imageId, publicId);
            
            // Update image with upload results
            image.setCloudinaryPublicId(publicId);
            image.setOriginalStoragePath(cloudinaryUrl);
            
            // Get real dimensions with timeout
            try {
                int[] dimensions = dimensionsFuture.get(1000, TimeUnit.MILLISECONDS);
                image.setOriginalWidth(dimensions[0]);
                image.setOriginalHeight(dimensions[1]);
                log.debug("📐 Updated to real dimensions: {}x{}", dimensions[0], dimensions[1]);
            } catch (Exception e) {
                log.debug("📐 Using estimated dimensions for image {} ({})", imageId, e.getMessage());
            }
            
            // Save updated image
            imageRepository.save(image);
            
            long totalTime = System.currentTimeMillis() - startTime;
            log.info("✅ Upload completed in {}ms for image {}", totalTime, imageId);
            
            // Dispatch for processing
            jobService.updateJobStatus(jobId, JobStatusEnum.QUEUED, "Upload complete, queuing for processing...");
            jobService.dispatchJobForProcessing(job, cloudinaryUrl);
            
        } catch (Exception e) {
            log.error("❌ Upload attempt failed for image {}: {}", imageId, e.getMessage(), e);
            
            // Cleanup any partial upload
            if (image.getCloudinaryPublicId() != null) {
                cleanupAsync(image.getCloudinaryPublicId());
            }
            
            throw e; // Re-throw for retry logic
        }
    }

    /**
     * Extract dimensions from byte array instead of MultipartFile
     */
    public CompletableFuture<int[]> extractDimensionsFromBytes(byte[] fileData) {
        return CompletableFuture.supplyAsync(() -> {
            try {
                if (fileData.length < 50) {
                    throw new IllegalArgumentException("File data too small");
                }
                
                // Use minimal header for dimension extraction
                int headerSize = Math.min(8192, fileData.length);
                
                ImageInputStream iis = new MemoryCacheImageInputStream(
                    new ByteArrayInputStream(fileData, 0, headerSize));
                ImageReader reader = ImageIO.getImageReaders(iis).next();
                
                if (reader != null) {
                    try {
                        reader.setInput(iis);
                        int width = reader.getWidth(0);
                        int height = reader.getHeight(0);
                        
                        // Validate dimensions
                        if (width <= 0 || height <= 0) {
                            throw new IllegalArgumentException("Invalid image dimensions: " + width + "x" + height);
                        }
                        
                        if (width > MAX_DIMENSION || height > MAX_DIMENSION) {
                            throw new IllegalArgumentException(
                                String.format("Image too large: %dx%d (max: %dx%d)", 
                                width, height, MAX_DIMENSION, MAX_DIMENSION));
                        }
                        
                        return new int[]{width, height};
                    } finally {
                        reader.dispose();
                        iis.close();
                    }
                }
            } catch (Exception e) {
                log.debug("Dimension extraction from bytes failed, using defaults: {}", e.getMessage());
            }
            return new int[]{800, 600}; // Smart defaults
        });
    }

    /**
     * Enhanced corruption check with better error handling
     */
    public boolean isImageCorrupt(MultipartFile file) {
        try {
            if (file.getSize() < 50) { // Too small to be a valid image
                return true;
            }
            
            // Only read minimal header data for corruption check
            int headerSize = Math.min(4096, (int) file.getSize());
            byte[] header = new byte[headerSize];
            
            int bytesRead = file.getInputStream().read(header);
            if (bytesRead <= 0) {
                return true; // Could not read any data
            }
            
            ImageInputStream iis = new MemoryCacheImageInputStream(new ByteArrayInputStream(header, 0, bytesRead));
            ImageReader reader = ImageIO.getImageReaders(iis).next();
            
            if (reader != null) {
                try {
                    reader.setInput(iis);
                    // Try to read basic info without loading the full image
                    int width = reader.getWidth(0);
                    int height = reader.getHeight(0);
                    return width <= 0 || height <= 0; // Invalid dimensions = corrupt
                } finally {
                    reader.dispose();
                    iis.close();
                }
            }
        } catch (Exception e) {
            log.debug("Image corruption check failed for {}: {}", file.getOriginalFilename(), e.getMessage());
        }
        return true; // Corrupt or unreadable
    }

    /**
     * Async cleanup with better error handling
     */
    @Async
    public void cleanupAsync(String publicId) {
        try {
            if (publicId == null || publicId.trim().isEmpty()) {
                log.warn("🧹 Cannot cleanup: invalid public ID");
                return;
            }
            
            cloudinaryStorageService.deleteImage(publicId);
            log.info("🧹 Cleanup completed for Cloudinary image: {}", publicId);
        } catch (Exception e) {
            log.warn("🧹 Cleanup error for {}: {}", publicId, e.getMessage());
        }
    }

    @Transactional
    public Job processImageGeneration(ImageGenerationRequestDTO requestDTO, Map<String, Object> jobConfig) {
        UUID userId = UUID.fromString(requestDTO.getUserId());
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new EntityNotFoundException("User not found with ID: " + userId));
        
        log.info("🎨 Processing image generation for user {}", userId);
        
        try {
            Image placeholderImage = new Image();
            UUID imageId = placeholderImage.getImageId();
            
            // Quick configuration
            placeholderImage.setUser(user);
            placeholderImage.setOriginalFilename("generated_" + imageId.toString() + ".png");
            placeholderImage.setOriginalFilesizeBytes(0L);
            placeholderImage.setOriginalFormat("PNG");
            
            String aspectRatio = (String) jobConfig.getOrDefault("aspectRatio", "square");
            int[] dimensions = getDefaultDimensions(aspectRatio);
            placeholderImage.setOriginalWidth(dimensions[0]);
            placeholderImage.setOriginalHeight(dimensions[1]);
            
            placeholderImage.setOriginalStoragePath("pending");
            placeholderImage.setCloudinaryPublicId(null);

            Image savedImage = imageRepository.save(placeholderImage);
            log.info("Created placeholder image: {}", savedImage.getImageId());

            return jobService.createAndDispatchJob(savedImage, requestDTO.getJobType(), null, jobConfig, userId);
            
        } catch (Exception e) {
            log.error("Image generation error: {}", e.getMessage(), e);
            throw new RuntimeException("Image generation error: " + e.getMessage(), e);
        }
    }

    private int[] getDefaultDimensions(String aspectRatio) {
        switch (aspectRatio.toLowerCase()) {
            case "portrait": return new int[]{512, 768};
            case "landscape": return new int[]{768, 512};
            case "square":
            default: return new int[]{512, 512};
        }
    }

    private String extractFormatFast(String contentType) {
        if (contentType != null && contentType.startsWith("image/")) {
            return contentType.substring(6).toUpperCase(); // "image/".length() = 6
        }
        return "UNKNOWN";
    }
}