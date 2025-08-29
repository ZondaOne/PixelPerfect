package com.chunaudis.image_toolkit.controller;
import com.chunaudis.image_toolkit.service.EmailService;
import com.chunaudis.image_toolkit.entity.WaitlistEntry;
import com.chunaudis.image_toolkit.service.WaitlistService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/waitlist")
public class WaitlistController {

    private final WaitlistService waitlistService;
    private final EmailService emailService;

    public WaitlistController(WaitlistService waitlistService, EmailService emailService) {
        this.waitlistService = waitlistService;
        this.emailService = emailService;
    }

    @PostMapping
    public ResponseEntity<?> joinWaitlist(@RequestBody Map<String, String> body) {
        try {
            String email = body.get("email");
            WaitlistEntry entry = waitlistService.addEmail(email);

            
            emailService.sendWaitlistConfirmationEmail(email);

            Map<String, String> response = Map.of(
                "message", "Email added to waitlist",
                "email", email
            );
            return ResponseEntity.ok(response);
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().body(Map.of("error", e.getMessage()));
        }
    }
}

