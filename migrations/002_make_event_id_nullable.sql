-- Migration: Make event_id nullable for merchant-based enquiries
-- Date: 2025-11-14
-- Purpose: Support direct merchant enquiries without requiring an event_id
--          This allows restaurant reservations and general merchant contact

USE showeasy;

-- Make event_id nullable
ALTER TABLE booking_enquiries
MODIFY COLUMN event_id BIGINT NULL;

-- Verify the change
DESCRIBE booking_enquiries;
