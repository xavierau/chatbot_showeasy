"""
Notification Service Module

Provides notification functionality using the Strategy Pattern.
Supports multiple channels (log, email, WhatsApp) with pluggable implementations.

Usage:
    from app.services.notification import NotificationService

    service = NotificationService()  # Auto-detects channel from env
    result = service.send_enquiry_to_merchant(
        enquiry_id=123,
        event_name="Concert",
        user_message="I want to book 50 tickets",
        user_email="user@example.com",
        merchant_email="merchant@example.com"
    )

Environment Configuration:
    NOTIFICATION_CHANNEL=log  # 'log', 'email', 'whatsapp'
    NOTIFICATION_LOG_PATH=logs/notifications.log  # For log channel
"""

from .notification_interface import (
    NotificationChannel,
    EnquiryNotification,
    ReplyNotification
)
from .log_channel import LogNotificationChannel
from .email_channel import EmailNotificationChannel
from .notification_service import NotificationService

__all__ = [
    "NotificationService",
    "NotificationChannel",
    "LogNotificationChannel",
    "EmailNotificationChannel",
    "EnquiryNotification",
    "ReplyNotification"
]
