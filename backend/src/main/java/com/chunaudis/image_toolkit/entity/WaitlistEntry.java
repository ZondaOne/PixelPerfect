package com.chunaudis.image_toolkit.entity;

import jakarta.persistence.*;
import lombok.Data;
import java.time.OffsetDateTime;
import java.util.UUID;

@Entity
@Data

public class WaitlistEntry {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(nullable = false, unique = true)
    private String email;

    private OffsetDateTime createdAt;

    @PrePersist
    protected void onCreate() {
        this.createdAt = OffsetDateTime.now();
    }
}