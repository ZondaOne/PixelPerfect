package com.chunaudis.image_toolkit.controller;

import java.time.OffsetDateTime;
import java.util.Optional;
import java.util.UUID;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.ResponseEntity;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.CrossOrigin;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.chunaudis.image_toolkit.dto.AuthRequestDTO;
import com.chunaudis.image_toolkit.dto.AuthResponseDTO;
import com.chunaudis.image_toolkit.entity.User;
import com.chunaudis.image_toolkit.repository.UserRepository;
import com.chunaudis.image_toolkit.security.JwtUtil;
import com.chunaudis.image_toolkit.service.PasswordResetService;
import com.chunaudis.image_toolkit.service.EmailVerificationService;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Value;
import com.google.api.client.http.javanet.NetHttpTransport;
import com.google.api.client.json.JsonFactory;
import com.google.api.client.json.gson.GsonFactory;
import com.google.api.client.googleapis.auth.oauth2.GoogleIdToken;
import com.google.api.client.googleapis.auth.oauth2.GoogleIdTokenVerifier;
import com.chunaudis.image_toolkit.dto.GoogleAuthRequestDTO;
import java.util.Collections;

import java.time.Duration;
import java.time.OffsetDateTime;
import java.util.Map;


@RestController
@RequestMapping("/api/v1/auth")
@CrossOrigin(origins = "*") // Para desarrollo, restringir en producción
public class AuthController {

    private static final Logger log = LoggerFactory.getLogger(AuthController.class);
    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtUtil jwtUtil;
    private final PasswordResetService passwordResetService;
    private final EmailVerificationService emailVerificationService;
    
    // Variables para Google OAuth
    @Value("${google.client.id}")
    private String googleClientId;
    
    private final NetHttpTransport transport = new NetHttpTransport();
    private final JsonFactory jsonFactory = GsonFactory.getDefaultInstance();

    public AuthController(UserRepository userRepository, PasswordEncoder passwordEncoder, JwtUtil jwtUtil, 
                         PasswordResetService passwordResetService, EmailVerificationService emailVerificationService) {
        this.userRepository = userRepository;
        this.passwordEncoder = passwordEncoder;
        this.jwtUtil = jwtUtil;
        this.passwordResetService = passwordResetService;
        this.emailVerificationService = emailVerificationService;
    }


    @Transactional
public void updateLastLoginTime(UUID userId) {
    userRepository.findById(userId).ifPresent(user -> {
        user.setLastLoginAt(OffsetDateTime.now());
        userRepository.save(user);
    });
}

@PostMapping("/login")
public ResponseEntity<?> login(@Valid @RequestBody AuthRequestDTO authRequest) {
    try {
        log.info("Login attempt for email: {}", authRequest.getEmail());

        Optional<User> userOpt = userRepository.findByEmail(authRequest.getEmail());

        if (userOpt.isPresent()) {
            User user = userOpt.get();

            if (user.isAccountLocked()) {
                OffsetDateTime lastFail = user.getLastFailedLogin();
                int attemptsOverThreshold = Math.max(0, user.getFailedLoginAttempts() - 4);
                Duration lockDuration = Duration.ofMinutes(5L * attemptsOverThreshold);
                OffsetDateTime unlockTime = lastFail.plus(lockDuration);

                if (OffsetDateTime.now().isBefore(unlockTime)) {
                    Duration remaining = Duration.between(OffsetDateTime.now(), unlockTime);
                    long minutes = remaining.toMinutes();
                    long seconds = remaining.minusMinutes(minutes).getSeconds();

                    log.warn("Account is locked until {} for email: {}", unlockTime, user.getEmail());
                    return ResponseEntity.status(403).body(
                        String.format("Your account is locked due to too many failed login attempts. Try again in %d minutes and %d seconds.", minutes, seconds)
                    );
                } else {
                    user.setAccountLocked(false);
                    userRepository.save(user);
                    log.info("User {} unlocked after lock duration expired", user.getEmail());
                }
            }

            if (passwordEncoder.matches(authRequest.getPassword(), user.getPasswordHash())) {

              
                if (!user.getIsGuest() && !emailVerificationService.isEmailVerified(user)) {
                    return ResponseEntity.status(403).body(Map.of(
                        "error", "EMAIL_NOT_VERIFIED",
                        "message", "Please verify your email address before logging in.",
                        "email", user.getEmail()
                    ));
                }


                user.setFailedLoginAttempts(0);
                user.setAccountLocked(false);

                
                if (user.getIsGuest()) {
                    user.setIsGuest(false);
                }

                updateLastLoginTime(user.getUserId());
                userRepository.save(user);

                String token = jwtUtil.generateToken(user.getUserId(), user.getEmail(), user.getIsGuest());

                return ResponseEntity.ok(new AuthResponseDTO(
                    token,
                    user.getUserId().toString(),
                    user.getEmail(),
                    user.getDisplayName(),
                    "Registered"
                ));
            } else {
                
                int attempts = user.getFailedLoginAttempts() + 1;
                user.setFailedLoginAttempts(attempts);
                user.setLastFailedLogin(OffsetDateTime.now());

                if (attempts >= 5) {
                    user.setAccountLocked(true);
                    log.warn("User {} has been locked due to too many failed attempts", user.getEmail());
                }

                userRepository.save(user);
            }
        }

        return ResponseEntity.status(401).body("Invalid email or password");

    } catch (Exception e) {
        log.error("Login error", e);
        return ResponseEntity.internalServerError().body("Authentication failed");
    }
}



@PostMapping("/register")
public ResponseEntity<?> register(@Valid @RequestBody AuthRequestDTO registerRequest) {
    try {
        log.info("Registration attempt for email: {}", registerRequest.getEmail());

        if (userRepository.existsByEmail(registerRequest.getEmail())) {
            return ResponseEntity.badRequest().body("Email already registered");
        }

        User user = new User();
        user.setEmail(registerRequest.getEmail());
        user.setPasswordHash(passwordEncoder.encode(registerRequest.getPassword()));
        user.setIsGuest(false);
        user.setDisplayName(registerRequest.getDisplayName());
        user.setEmailVerified(false); // New users need to verify email

        User savedUser = userRepository.save(user);

        // Send verification email (with error handling)
        try {
            emailVerificationService.sendVerificationEmail(savedUser);
            log.info("User registered and verification email sent for: {}", savedUser.getEmail());
        } catch (Exception emailError) {
            log.error("Failed to send verification email for user: {}, Error: {}", savedUser.getEmail(), emailError.getMessage());
            // For now, mark user as verified if email fails (development mode)
            savedUser.setEmailVerified(true);
            savedUser.setEmailVerifiedAt(OffsetDateTime.now());
            userRepository.save(savedUser);
            log.warn("User {} marked as verified due to email service failure", savedUser.getEmail());
        }

        return ResponseEntity.ok(Map.of(
            "message", "Registration successful! Please check your email to verify your account.",
            "email", savedUser.getEmail(),
            "userId", savedUser.getUserId().toString()
        ));

    } catch (Exception e) {
        log.error("Registration error", e);
        return ResponseEntity.internalServerError().body("Registration failed");
    }
}

@GetMapping("/create-test-user")
@Transactional
public ResponseEntity<?> createTestUser() {
    // TODO: Remove this endpoint in production or secure with proper authentication
    if (!"development".equals(System.getProperty("spring.profiles.active", "development"))) {
        return ResponseEntity.status(404).body("Endpoint not available");
    }
    try {
        String testEmail = "test@example.com";
        String testPassword = "password123";

        Optional<User> existingUser = userRepository.findByEmail(testEmail);
        if (existingUser.isPresent()) {
            User user = existingUser.get();
            String token = jwtUtil.generateToken(user.getUserId(), user.getEmail(), user.getIsGuest());

            return ResponseEntity.ok(new AuthResponseDTO(
                token,
                user.getUserId().toString(),
                user.getEmail(),
                user.getDisplayName(),
                user.getIsGuest() ? "Guest" : "Test user"
            ));
        }

        User user = new User();
        user.setEmail(testEmail);
        user.setPasswordHash(passwordEncoder.encode(testPassword));
        user.setDisplayName("Test User");
        user.setIsGuest(false);

        User savedUser = userRepository.save(user);
        userRepository.flush();

        log.info("Created test user with ID: {}", savedUser.getUserId());

        String token = jwtUtil.generateToken(savedUser.getUserId(), savedUser.getEmail(), savedUser.getIsGuest());

        return ResponseEntity.ok(new AuthResponseDTO(
            token,
            savedUser.getUserId().toString(),
            savedUser.getEmail(),
            savedUser.getDisplayName(),
            savedUser.getIsGuest() ? "Guest" : "Test user"
        ));

    } catch (Exception e) {
        log.error("Test user creation error", e);
        return ResponseEntity.internalServerError().body("Test user creation failed: " + e.getMessage());
    }
}


@PostMapping("/login-with-google")
public ResponseEntity loginWithGoogle(@Valid @RequestBody GoogleAuthRequestDTO googleAuthRequest) {
    System.out.println("=== ENDPOINT REACHED ===");
    try {
        log.info("Google login attempt with token");
        
        // Validar el token de Google
        GoogleIdTokenVerifier verifier = new GoogleIdTokenVerifier.Builder(transport, jsonFactory)
            .setAudience(Collections.singletonList(googleClientId))
            .build();
        
        GoogleIdToken idToken = verifier.verify(googleAuthRequest.getCredential());
        
        if (idToken == null) {
            log.warn("Invalid Google token");
            return ResponseEntity.status(401).body("Invalid Google token");
        }
        
        GoogleIdToken.Payload payload = idToken.getPayload();
        String email = payload.getEmail();
        String name = (String) payload.get("name");
        String googleId = payload.getSubject();
        
        log.info("Google login for email: {}", email);
        
        Optional<User> userOpt = userRepository.findByEmail(email);
        
        User user;
        if (userOpt.isPresent()) {
            user = userOpt.get();
            log.info("Existing user found: {}", email);
        } else {
            user = new User();
            user.setEmail(email);
            // Generate a unique hash for Google users
            user.setPasswordHash(generateGoogleUserHash(googleId, email));
            user.setIsGuest(false);
            user.setDisplayName(name);
            user.setEmailVerified(true);
            
            user = userRepository.save(user);
            log.info("New Google user created: {}", email);
        }
        
        // Actualizar último login
        updateLastLoginTime(user.getUserId());
        
        // Generar JWT
        String token = jwtUtil.generateToken(user.getUserId(), user.getEmail(), user.getIsGuest());
        
        return ResponseEntity.ok(new AuthResponseDTO(
            token,
            user.getUserId().toString(),
            user.getEmail(),
            user.getDisplayName(),
            "Registered"
        ));
        
    } catch (Exception e) {
        log.error("Google login error", e);
        return ResponseEntity.internalServerError().body("Google authentication failed");
    }
}

private String generateGoogleUserHash(String googleId, String email) {
    // Create a unique identifier for Google users
    String googleIdentifier = "GOOGLE_AUTH_" + googleId + "_" + email;
    
    // Use your existing password encoder to create a hash
    return passwordEncoder.encode(googleIdentifier);
}

//endpoint for maintaining alive session only 200 ok response
@GetMapping("/keep-alive")
public ResponseEntity<?> keepAlive() {
    return ResponseEntity.ok().build();

}
}


