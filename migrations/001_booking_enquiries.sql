-- Migration: Booking Enquiries System
-- Created: 2025-11-14
-- Description: Creates tables for booking enquiry management with merchant communication

-- Create booking_enquiries table
CREATE TABLE IF NOT EXISTS booking_enquiries (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NULL COMMENT 'Optional user ID if user is logged in',
    session_id VARCHAR(255) NOT NULL COMMENT 'Chat session ID for conversation tracking',
    event_id BIGINT NOT NULL COMMENT 'Event being enquired about',
    organizer_id BIGINT NOT NULL COMMENT 'Event organizer/merchant ID',
    enquiry_type VARCHAR(50) NOT NULL DEFAULT 'custom_booking' COMMENT 'Type: custom_booking, group_booking, special_request',
    user_message TEXT NOT NULL COMMENT 'User enquiry message',
    contact_email VARCHAR(255) NOT NULL COMMENT 'User contact email',
    contact_phone VARCHAR(50) NULL COMMENT 'Optional user contact phone',
    status VARCHAR(50) NOT NULL DEFAULT 'pending' COMMENT 'Status: pending, sent, replied, completed, cancelled',
    merchant_email VARCHAR(255) NOT NULL COMMENT 'Merchant contact email from organizers table',
    merchant_phone VARCHAR(50) NULL COMMENT 'Merchant contact phone from organizers table',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Indexes for performance
    INDEX idx_user_session (user_id, session_id),
    INDEX idx_organizer (organizer_id),
    INDEX idx_event (event_id),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at),

    -- Foreign key constraints (optional - depends on existing schema)
    -- FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
    -- FOREIGN KEY (organizer_id) REFERENCES organizers(id) ON DELETE CASCADE

    CONSTRAINT chk_enquiry_type CHECK (enquiry_type IN ('custom_booking', 'group_booking', 'special_request')),
    CONSTRAINT chk_status CHECK (status IN ('pending', 'sent', 'replied', 'completed', 'cancelled'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Tracks booking enquiries sent to event organizers/merchants';

-- Create enquiry_replies table
CREATE TABLE IF NOT EXISTS enquiry_replies (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    enquiry_id BIGINT NOT NULL COMMENT 'Reference to booking_enquiries.id',
    reply_from VARCHAR(50) NOT NULL COMMENT 'Source: merchant, user, system',
    reply_message TEXT NOT NULL COMMENT 'Reply content',
    reply_channel VARCHAR(50) NOT NULL DEFAULT 'api' COMMENT 'Channel: email, whatsapp, api',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Indexes
    INDEX idx_enquiry_id (enquiry_id),
    INDEX idx_created_at (created_at),
    INDEX idx_reply_from (reply_from),

    -- Foreign key
    FOREIGN KEY (enquiry_id) REFERENCES booking_enquiries(id) ON DELETE CASCADE,

    CONSTRAINT chk_reply_from CHECK (reply_from IN ('merchant', 'user', 'system')),
    CONSTRAINT chk_reply_channel CHECK (reply_channel IN ('email', 'whatsapp', 'api'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Stores all replies to booking enquiries for audit trail';

-- Sample queries for reference:

-- Get all enquiries for a specific event with replies count
-- SELECT
--     be.id, be.enquiry_type, be.status, be.contact_email, be.created_at,
--     COUNT(er.id) as reply_count
-- FROM booking_enquiries be
-- LEFT JOIN enquiry_replies er ON be.id = er.enquiry_id
-- WHERE be.event_id = ?
-- GROUP BY be.id
-- ORDER BY be.created_at DESC;

-- Get full enquiry thread
-- SELECT
--     be.id as enquiry_id,
--     be.user_message,
--     be.status,
--     er.reply_from,
--     er.reply_message,
--     er.reply_channel,
--     er.created_at
-- FROM booking_enquiries be
-- LEFT JOIN enquiry_replies er ON be.id = er.enquiry_id
-- WHERE be.id = ?
-- ORDER BY er.created_at ASC;
