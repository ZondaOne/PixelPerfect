package com.chunaudis.image_toolkit.storage;

import com.cloudinary.Cloudinary;
import com.cloudinary.utils.ObjectUtils;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;
import java.util.HashMap;


import java.io.IOException;
import java.util.Map;
import java.util.UUID;

@Service
@Slf4j
public class CloudinaryStorageService {

    @Autowired
    private Cloudinary cloudinary;

    /**
     * Upload original image to Cloudinary
     */
    public String uploadOriginalImage(MultipartFile file, UUID userId, UUID imageId) {
        try {
            String publicId = String.format("originals/%s/%s_original", userId, imageId);
            
            Map uploadResult = cloudinary.uploader().upload(file.getBytes(), 
                ObjectUtils.asMap(
                    "public_id", publicId,
                    "folder", "pixelperfect",
                    "resource_type", "image",
                    "overwrite", true,
                    // Add tags for management
                    "tags", ObjectUtils.asArray(new String[]{"original", "user_" + userId})
                ));
            
            String imageUrl = (String) uploadResult.get("secure_url");
            log.info("Uploaded original image to Cloudinary: {}", imageUrl);
            return imageUrl;
            
        } catch (IOException e) {
            log.error("Failed to upload original image to Cloudinary", e);
            throw new RuntimeException("Failed to upload original image", e);
        }
    }

    /**
     * Upload processed image to Cloudinary
     */
    public String uploadProcessedImage(byte[] imageBytes, UUID jobId, String suffix, boolean isPremium) {
        try {
            String publicId = String.format("processed/%s_%s", jobId, suffix);
            String tag = isPremium ? "premium" : "free";
            
            Map uploadResult = cloudinary.uploader().upload(imageBytes, 
                ObjectUtils.asMap(
                    "public_id", publicId,
                    "folder", "pixelperfect",
                    "resource_type", "image",
                    "overwrite", true,
                    "tags", ObjectUtils.asArray(new String[]{"processed", tag, "job_" + jobId})
                ));
            
            String imageUrl = (String) uploadResult.get("secure_url");
            log.info("Uploaded processed image to Cloudinary: {}", imageUrl);
            return imageUrl;
            
        } catch (IOException e) {
            log.error("Failed to upload processed image to Cloudinary", e);
            throw new RuntimeException("Failed to upload processed image", e);
        }
    }

    /**
     * Delete image from Cloudinary by public ID
     */
    public void deleteImage(String publicId) {
        try {
            Map result = cloudinary.uploader().destroy(publicId, ObjectUtils.emptyMap());
            log.info("Deleted image from Cloudinary: {} - Result: {}", publicId, result.get("result"));
        } catch (IOException e) {
            log.error("Failed to delete image from Cloudinary: {}", publicId, e);
        }
    }

    /**
     * Extract public ID from Cloudinary URL
     */
    public String extractPublicId(String cloudinaryUrl) {
        if (cloudinaryUrl == null || !cloudinaryUrl.contains("cloudinary.com")) {
            return null;
        }
        
        try {
            // Extract the public ID from URL like:
            // https://res.cloudinary.com/cloud_name/image/upload/v1234567890/pixelperfect/path/image_id.jpg
            String[] parts = cloudinaryUrl.split("/");
            String fileName = parts[parts.length - 1];
            String path = parts[parts.length - 2];
            
            // Remove file extension and version
            String publicId = fileName.replaceFirst("\\.[^.]+$", "");
            
            // Construct full public ID including folder
            return "pixelperfect/" + path + "/" + publicId;
        } catch (Exception e) {
            log.error("Failed to extract public ID from URL: {}", cloudinaryUrl, e);
            return null;
        }
    }

    /**
     * Delete images by tag (for batch operations)
     */
    public void deleteImagesByTag(String tag) {
        try {
            Map result = cloudinary.api().deleteResourcesByTag(tag, ObjectUtils.emptyMap());
            log.info("Deleted images with tag '{}': {}", tag, result);
        } catch (Exception e) {
            log.error("Failed to delete images by tag: {}", tag, e);
        }
    }

    /**
     * Get image info from Cloudinary
     */
    public Map getImageInfo(String publicId) {
        try {
            return cloudinary.api().resource(publicId, ObjectUtils.emptyMap());
        } catch (Exception e) {
            log.error("Failed to get image info for: {}", publicId, e);
            return null;
        }
    }

    // Agregar a CloudinaryStorageService.java
public String uploadOriginalImageFromBytes(byte[] fileData, String originalFilename, String contentType, 
        UUID userId, UUID imageId) throws Exception {
    
    Map<String, Object> params = new HashMap<>();
    params.put("folder", "users/" + userId + "/originals");
    params.put("public_id", imageId.toString());
    params.put("resource_type", "image");
    params.put("format", extractFormatFromContentType(contentType));
    
    // Upload from byte array
    Map<String, Object> result = cloudinary.uploader().upload(fileData, params);
    
    return (String) result.get("secure_url");
}

private String extractFormatFromContentType(String contentType) {
    if (contentType != null && contentType.startsWith("image/")) {
        return contentType.substring(6); // Remove "image/" prefix
    }
    return "auto";
}
}