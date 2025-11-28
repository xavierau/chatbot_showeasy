"""
Notification Service - Facade with Strategy Pattern

This service acts as a facade to the notification system and uses the Strategy
Pattern to support multiple notification channels (email, SMS, WhatsApp, log).

Design Patterns:
- Facade Pattern: Simplifies notification sending for clients
- Strategy Pattern: Allows runtime selection of notification channel
- Singleton-like: Typically instantiated once per application

Following SOLID Principles:
- Single Responsibility: Only handles notification routing
- Open/Closed: Open for extension (new channels), closed for modification
- Dependency Inversion: Depends on NotificationChannel abstraction
"""

import os
import logging
from typing import Dict, Optional
from .notification_interface import (
    NotificationChannel,
    EnquiryNotification,
    ReplyNotification
)
from .log_channel import LogNotificationChannel

# Configure logger for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class NotificationService:
    """
    Facade for sending notifications through different channels.

    This service:
    1. Determines which channel to use based on configuration
    2. Validates channel availability
    3. Delegates to the appropriate channel implementation
    4. Provides fallback behavior if primary channel fails
    """

    def __init__(self, channel: Optional[NotificationChannel] = None):
        """
        Initialize notification service with a specific channel.

        Args:
            channel: Specific NotificationChannel to use, or None to auto-detect
                    from environment variable NOTIFICATION_CHANNEL
        """
        logger.debug("[NotificationService] Initializing...")
        if channel:
            self.channel = channel
            logger.debug(f"[NotificationService] Using provided channel: {channel.get_channel_name()}")
        else:
            self.channel = self._get_channel_from_env()
            logger.debug(f"[NotificationService] Auto-detected channel: {self.channel.get_channel_name()}")

    def _get_channel_from_env(self) -> NotificationChannel:
        """
        Determine notification channel from environment configuration.

        Reads NOTIFICATION_CHANNEL environment variable:
        - 'log': LogNotificationChannel
        - 'email': EmailNotificationChannel (future)
        - 'whatsapp': WhatsAppNotificationChannel (future)

        Returns:
            Configured NotificationChannel instance

        Raises:
            ValueError: If channel type is unknown
        """
        channel_type = os.getenv("NOTIFICATION_CHANNEL", "log").lower()
        log_path = os.getenv("NOTIFICATION_LOG_PATH", "logs/notifications.log")
        logger.debug(f"[NotificationService] Environment config: NOTIFICATION_CHANNEL={channel_type}, NOTIFICATION_LOG_PATH={log_path}")

        if channel_type == "log":
            logger.debug(f"[NotificationService] Creating LogNotificationChannel with path: {log_path}")
            return LogNotificationChannel(log_path=log_path)
        elif channel_type == "email":
            from .email_channel import EmailNotificationChannel
            logger.debug("[NotificationService] Creating EmailNotificationChannel")
            return EmailNotificationChannel()
        # elif channel_type == "whatsapp":
        #     return WhatsAppNotificationChannel()  # Future implementation
        else:
            logger.error(f"[NotificationService] Unknown channel type: {channel_type}")
            raise ValueError(
                f"Unknown notification channel: {channel_type}. "
                f"Supported channels: log, email, whatsapp (future)"
            )

    def send_enquiry_to_merchant(
        self,
        enquiry_id: int,
        event_name: str,
        user_message: str,
        user_email: str,
        merchant_email: str,
        merchant_phone: Optional[str] = None,
        user_phone: Optional[str] = None,
        reply_url: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Send booking enquiry to merchant through configured channel.

        Args:
            enquiry_id: Unique enquiry identifier
            event_name: Name of the event
            user_message: User's enquiry message
            user_email: User's contact email
            merchant_email: Merchant's contact email
            merchant_phone: Optional merchant phone
            user_phone: Optional user phone
            reply_url: Optional URL for merchant to reply

        Returns:
            Dictionary with:
                - success: bool
                - message: str
                - channel: str
        """
        logger.info(f"[NotificationService] send_enquiry_to_merchant called for enquiry_id={enquiry_id}, channel={self.channel.get_channel_name()}")

        # Validate channel availability
        is_available = self.channel.is_available()
        logger.info(f"[NotificationService] Channel '{self.channel.get_channel_name()}' available: {is_available}")

        if not is_available:
            logger.error(f"[NotificationService] Channel '{self.channel.get_channel_name()}' is not available")
            return {
                "success": False,
                "message": f"Notification channel '{self.channel.get_channel_name()}' is not available",
                "channel": self.channel.get_channel_name()
            }

        # Build notification DTO
        built_reply_url = reply_url or self._build_reply_url(enquiry_id)
        logger.debug(f"[NotificationService] Building EnquiryNotification with reply_url={built_reply_url}")

        notification = EnquiryNotification(
            enquiry_id=enquiry_id,
            event_name=event_name,
            user_message=user_message,
            user_email=user_email,
            user_phone=user_phone,
            merchant_email=merchant_email,
            merchant_phone=merchant_phone,
            reply_url=built_reply_url
        )
        logger.debug(f"[NotificationService] EnquiryNotification created: {notification}")

        # Delegate to channel
        logger.info(f"[NotificationService] Delegating to channel.send_enquiry_to_merchant...")
        try:
            result = self.channel.send_enquiry_to_merchant(notification)
            logger.info(f"[NotificationService] Channel result: success={result.get('success')}, message={result.get('message')}")
            logger.debug(f"[NotificationService] Full channel result: {result}")
            return result
        except Exception as e:
            logger.error(f"[NotificationService] Exception in channel.send_enquiry_to_merchant: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"Exception sending notification: {str(e)}",
                "channel": self.channel.get_channel_name()
            }

    def send_reply_to_user(
        self,
        enquiry_id: int,
        event_name: str,
        merchant_reply: str,
        user_email: str,
        user_phone: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Send merchant reply to user through configured channel.

        Args:
            enquiry_id: Unique enquiry identifier
            event_name: Name of the event
            merchant_reply: Formatted merchant reply message
            user_email: User's contact email
            user_phone: Optional user phone

        Returns:
            Dictionary with:
                - success: bool
                - message: str
                - channel: str
        """
        # Validate channel availability
        if not self.channel.is_available():
            return {
                "success": False,
                "message": f"Notification channel '{self.channel.get_channel_name()}' is not available",
                "channel": self.channel.get_channel_name()
            }

        # Build notification DTO
        notification = ReplyNotification(
            enquiry_id=enquiry_id,
            event_name=event_name,
            merchant_reply=merchant_reply,
            user_email=user_email,
            user_phone=user_phone
        )

        # Delegate to channel
        return self.channel.send_reply_to_user(notification)

    def _build_reply_url(self, enquiry_id: int) -> str:
        """
        Build reply URL for merchant.

        In production, this would use the actual API server URL.
        For now, uses localhost or configured base URL.
        """
        base_url = os.getenv("API_BASE_URL", "http://localhost:3010")
        return f"{base_url}/api/enquiry-reply?id={enquiry_id}"

    def get_current_channel(self) -> str:
        """
        Get the name of the currently configured channel.

        Returns:
            Channel name (e.g., 'log', 'email', 'whatsapp')
        """
        return self.channel.get_channel_name()
