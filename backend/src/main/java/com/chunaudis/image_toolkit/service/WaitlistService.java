package com.chunaudis.image_toolkit.service;

import com.chunaudis.image_toolkit.entity.WaitlistEntry;
import com.chunaudis.image_toolkit.repository.WaitlistRepository;
import org.springframework.stereotype.Service;

@Service
public class WaitlistService {
    private final WaitlistRepository waitlistRepository;

    public WaitlistService(WaitlistRepository waitlistRepository) {
        this.waitlistRepository = waitlistRepository;
    }

    public WaitlistEntry addEmail(String email) {
        if (waitlistRepository.existsByEmail(email)) {
            throw new IllegalArgumentException("Email already in waitlist");
        }

        WaitlistEntry entry = new WaitlistEntry();
        entry.setEmail(email);
        return waitlistRepository.save(entry);
    }
}
