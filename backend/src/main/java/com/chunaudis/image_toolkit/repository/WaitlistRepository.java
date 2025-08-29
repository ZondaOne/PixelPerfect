package com.chunaudis.image_toolkit.repository;

import com.chunaudis.image_toolkit.entity.WaitlistEntry;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.UUID;

@Repository
public interface WaitlistRepository extends JpaRepository<WaitlistEntry, UUID> {
    boolean existsByEmail(String email);
}
