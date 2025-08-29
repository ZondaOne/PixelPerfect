package com.chunaudis.image_toolkit.service;

import org.springframework.mail.SimpleMailMessage;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.stereotype.Service;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;

@Service
public class EmailService {

    private static final Logger log = LoggerFactory.getLogger(EmailService.class);
    
    private final JavaMailSender mailSender;

    @Value("${spring.mail.username:zondasys@gmail.com}")
    private String mailUsername;

    @Value("${spring.mail.host:NOT_SET}")
    private String mailHost;

    @Value("${spring.mail.port:NOT_SET}")
    private String mailPort;

    public EmailService(JavaMailSender mailSender) {
        this.mailSender = mailSender;
    }

    public void sendPasswordResetEmail(String to, String token) {
        String subject = "Password Reset Request";
        String resetLink = "https://pixelperfect.zonda.one/reset-password?token=" + token;

        String text = "Hello!\n\n"
                    + "You received this email because you requested to reset your password.\n\n"
                    + "Please click the link below or copy and paste it into your browser:\n"
                    + resetLink + "\n\n"
                    + "If you did not request a password reset, please ignore this message.\n\n"
                    + "Best regards,\n"
                    + "The Chunaudis Team";

        SimpleMailMessage message = new SimpleMailMessage();
        message.setFrom(mailUsername); 
        message.setTo(to);
        message.setSubject(subject);
        message.setText(text);

        mailSender.send(message);
    }

    public void sendEmailVerificationEmail(String to, String token) {
        log.info("=== EMAIL VERIFICATION ATTEMPT ===");
        log.info("Recipient: {}", to);
        log.info("Mail Configuration:");
        log.info("  Host: {}", mailHost);
        log.info("  Port: {}", mailPort);
        log.info("  Username: {}", mailUsername);
        log.info("  Password set: {}", mailUsername != null && !mailUsername.equals("NOT_SET") ? "YES" : "NO");
        
        try {
            String subject = "Verify Your Email Address";
            String verificationLink = "https://pixelperfect.zonda.one/verify-email?token=" + token;

            String text = "Hello!\n\n"
                        + "Thank you for signing up with PixelPerfect Image Toolkit!\n\n"
                        + "To complete your registration, please verify your email address by clicking the link below:\n"
                        + verificationLink + "\n\n"
                        + "This link will expire in 24 hours.\n\n"
                        + "If you did not create an account, please ignore this message.\n\n"
                        + "Best regards,\n"
                        + "The Zonda Team";

            SimpleMailMessage message = new SimpleMailMessage();
            message.setFrom(mailUsername);
            message.setTo(to);
            message.setSubject(subject);
            message.setText(text);

            log.info("Attempting to send email...");
            log.info("From: {}", mailUsername);
            log.info("To: {}", to);
            log.info("Subject: {}", subject);

            mailSender.send(message);
            
            log.info("✅ Email sent successfully to {}", to);
            
        } catch (Exception e) {
            log.error("❌ Failed to send email to {}", to);
            log.error("Error type: {}", e.getClass().getSimpleName());
            log.error("Error message: {}", e.getMessage());
            log.error("Full stack trace:", e);
            
            if (e.getMessage() != null) {
                if (e.getMessage().contains("Authentication failed")) {
                    log.error("🔐 AUTHENTICATION ISSUE: Check Gmail credentials and App Password");
                } else if (e.getMessage().contains("Connection")) {
                    log.error("🌐 CONNECTION ISSUE: Check network and SMTP settings");
                } else if (e.getMessage().contains("535")) {
                    log.error("🚫 SMTP AUTH ERROR: Invalid username/password or 2FA not enabled");
                }
            }
            
            throw e;
        }
    }

    public void sendWaitlistConfirmationEmail(String to) {
        log.info("=== WAITLIST CONFIRMATION ATTEMPT ===");
        log.info("Recipient: {}", to);
        log.info("Mail Configuration:");
        log.info("  Host: {}", mailHost);
        log.info("  Port: {}", mailPort);
        log.info("  Username: {}", mailUsername);
        log.info("  Password set: {}", mailUsername != null && !mailUsername.equals("NOT_SET") ? "YES" : "NO");

        try {
            String subject = "You're on the Beta Waitlist!";
            String text = "Hello!\n\n"
                        + "Thank you for joining our beta waitlist!\n"
                        + "We'll notify you as soon as we launch.\n\n"
                        + "Best regards,\n"
                        + "The PixelPerfect AI Team";

            SimpleMailMessage message = new SimpleMailMessage();
            // Usar la misma configuración que los otros métodos
            message.setFrom(mailUsername);
            message.setTo(to);
            message.setSubject(subject);
            message.setText(text);

            log.info("Attempting to send waitlist confirmation email...");
            log.info("From: {}", mailUsername);
            log.info("To: {}", to);
            log.info("Subject: {}", subject);

            mailSender.send(message);

            log.info("✅ Waitlist confirmation email sent successfully to {}", to);

        } catch (Exception e) {
            log.error("❌ Failed to send waitlist email to {}", to);
            log.error("Error type: {}", e.getClass().getSimpleName());
            log.error("Error message: {}", e.getMessage());
            log.error("Full stack trace:", e);

            if (e.getMessage() != null) {
                if (e.getMessage().contains("Authentication failed")) {
                    log.error("🔐 AUTHENTICATION ISSUE: Check Gmail credentials and App Password");
                } else if (e.getMessage().contains("Connection")) {
                    log.error("🌐 CONNECTION ISSUE: Check network and SMTP settings");
                } else if (e.getMessage().contains("535")) {
                    log.error("🚫 SMTP AUTH ERROR: Invalid username/password or 2FA not enabled");
                }
            }

            throw e;
        }
    }
}
