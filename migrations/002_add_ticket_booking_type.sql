-- Migration: Add 'ticket_booking' enquiry type
-- Created: 2025-12-01
-- Description: Adds 'ticket_booking' to valid enquiry types for standard event ticket bookings

-- Drop the existing constraint
ALTER TABLE booking_enquiries DROP CONSTRAINT chk_enquiry_type;

-- Add the new constraint with 'ticket_booking' included
ALTER TABLE booking_enquiries
ADD CONSTRAINT chk_enquiry_type
CHECK (enquiry_type IN ('custom_booking', 'group_booking', 'special_request', 'ticket_booking'));

-- Update comment for clarity
ALTER TABLE booking_enquiries
MODIFY COLUMN enquiry_type VARCHAR(50) NOT NULL DEFAULT 'custom_booking'
COMMENT 'Type: ticket_booking (standard), custom_booking, group_booking, special_request';
