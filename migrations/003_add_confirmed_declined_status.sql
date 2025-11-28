-- Migration 003: Add 'confirmed' and 'declined' status values to booking_enquiries
-- This migration updates the status constraint to support explicit confirm/decline actions
-- from merchants via email buttons.

-- Drop the existing constraint
ALTER TABLE booking_enquiries DROP CONSTRAINT IF EXISTS chk_status;

-- Add the updated constraint with new status values
ALTER TABLE booking_enquiries
ADD CONSTRAINT chk_status CHECK (status IN ('pending', 'sent', 'replied', 'confirmed', 'declined', 'completed', 'cancelled'));

-- Note: Status flow is now:
-- pending -> sent -> confirmed (merchant clicked Confirm)
--                 -> declined (merchant clicked Decline)
--                 -> replied (merchant sent custom reply)
--                 -> completed (enquiry fulfilled)
--                 -> cancelled (enquiry cancelled by user or system)
