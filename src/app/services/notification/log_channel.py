"""
Log Notification Channel - Test Implementation

This is a concrete implementation of NotificationChannel that logs notifications
to a file instead of sending actual emails or messages. Perfect for testing
and development without requiring external service configuration.

Design Pattern: Strategy Pattern (Concrete Strategy)
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict
from .notification_interface import (
    NotificationChannel,
    EnquiryNotification,
    ReplyNotification
)

# Configure logger for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class LogNotificationChannel(NotificationChannel):
    """
    Notification channel that writes to a log file.

    This implementation is useful for:
    - Local development without email service
    - Testing notification logic
    - Debugging notification content
    - CI/CD environments

    Log Format: JSON Lines (one JSON object per line)
    """

    def __init__(self, log_path: str = "logs/notifications.log"):
        """
        Initialize the log notification channel.

        Args:
            log_path: Path to log file (default: logs/notifications.log)
        """
        logger.debug(f"[LogNotificationChannel] Initializing with log_path={log_path}")
        self.log_path = log_path
        self._ensure_log_directory()
        logger.debug(f"[LogNotificationChannel] Initialization complete")

    def _ensure_log_directory(self):
        """Create log directory if it doesn't exist."""
        log_dir = Path(self.log_path).parent
        logger.debug(f"[LogNotificationChannel] Ensuring log directory exists: {log_dir}")
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"[LogNotificationChannel] Log directory ready: {log_dir}")
        except Exception as e:
            logger.error(f"[LogNotificationChannel] Failed to create log directory: {e}", exc_info=True)
            raise

    def _write_log(self, log_entry: Dict) -> bool:
        """
        Write a log entry to the notification log file.

        Args:
            log_entry: Dictionary to write as JSON

        Returns:
            Boolean indicating success
        """
        logger.debug(f"[LogNotificationChannel] Writing log entry to {self.log_path}")
        try:
            # Check if file is writable before attempting
            log_dir = Path(self.log_path).parent
            if not os.access(log_dir, os.W_OK):
                logger.error(f"[LogNotificationChannel] Log directory not writable: {log_dir}")
                return False

            with open(self.log_path, 'a', encoding='utf-8') as f:
                json.dump(log_entry, f, ensure_ascii=False)
                f.write('\n')
            logger.info(f"[LogNotificationChannel] Log entry written successfully to {self.log_path}")
            return True
        except PermissionError as e:
            logger.error(f"[LogNotificationChannel] Permission denied writing to {self.log_path}: {e}", exc_info=True)
            return False
        except OSError as e:
            logger.error(f"[LogNotificationChannel] OS error writing to {self.log_path}: {e}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"[LogNotificationChannel] Unexpected error writing log: {type(e).__name__}: {e}", exc_info=True)
            return False

    def send_enquiry_to_merchant(self, notification: EnquiryNotification) -> Dict[str, any]:
        """
        Log the enquiry notification instead of sending email/SMS.

        Creates a structured log entry with all enquiry details in JSON format.
        """
        logger.info(f"[LogNotificationChannel] send_enquiry_to_merchant called for enquiry_id={notification.enquiry_id}")
        logger.info(f"[LogNotificationChannel] Writing to log_path={self.log_path}")
        logger.debug(f"[LogNotificationChannel] Notification details: event_name={notification.event_name}, merchant_email={notification.merchant_email}")

        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": "enquiry_to_merchant",
            "channel": "log",
            "enquiry_id": notification.enquiry_id,
            "event_name": notification.event_name,
            "merchant": {
                "email": notification.merchant_email,
                "phone": notification.merchant_phone
            },
            "user": {
                "email": notification.user_email,
                "phone": notification.user_phone,
                "message": notification.user_message
            },
            "reply_url": notification.reply_url,
            "formatted_message": self._format_enquiry_message(notification)
        }

        logger.info(f"[LogNotificationChannel] Log entry created, writing to file...")
        success = self._write_log(log_entry)

        result = {
            "success": success,
            "message": f"Enquiry logged to {self.log_path}" if success else "Failed to log enquiry",
            "channel": "log",
            "log_path": self.log_path if success else None
        }
        logger.info(f"[LogNotificationChannel] Returning result: success={success}")
        if not success:
            logger.error(f"[LogNotificationChannel] Failed to write log entry to {self.log_path}")
        return result

    def send_reply_to_user(self, notification: ReplyNotification) -> Dict[str, any]:
        """
        Log the reply notification instead of sending to user.

        Creates a structured log entry with the merchant's reply.
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": "reply_to_user",
            "channel": "log",
            "enquiry_id": notification.enquiry_id,
            "event_name": notification.event_name,
            "user": {
                "email": notification.user_email,
                "phone": notification.user_phone
            },
            "merchant_reply": notification.merchant_reply,
            "formatted_message": self._format_reply_message(notification)
        }

        success = self._write_log(log_entry)

        return {
            "success": success,
            "message": f"Reply logged to {self.log_path}" if success else "Failed to log reply",
            "channel": "log",
            "log_path": self.log_path if success else None
        }

    def get_channel_name(self) -> str:
        """Return channel identifier."""
        return "log"

    def is_available(self) -> bool:
        """
        Check if log file is writable.

        Returns:
            True if log directory exists and is writable
        """
        logger.debug(f"[LogNotificationChannel] Checking availability for log_path={self.log_path}")
        try:
            self._ensure_log_directory()
            log_dir = Path(self.log_path).parent
            is_writable = os.access(log_dir, os.W_OK)
            logger.debug(f"[LogNotificationChannel] Log directory {log_dir} writable: {is_writable}")
            return is_writable
        except Exception as e:
            logger.error(f"[LogNotificationChannel] Availability check failed: {e}", exc_info=True)
            return False

    def _format_enquiry_message(self, notification: EnquiryNotification) -> str:
        """
        Format enquiry as human-readable message (simulates email body).

        This shows what the actual email would look like when implemented.
        """
        return f"""
================================================================================
NEW BOOKING ENQUIRY #{notification.enquiry_id}
================================================================================

Event: {notification.event_name}

From: {notification.user_email}
{f'Phone: {notification.user_phone}' if notification.user_phone else ''}

Message:
{notification.user_message}

--------------------------------------------------------------------------------
To reply to this enquiry, visit:
{notification.reply_url}

Or reply directly to this email.
--------------------------------------------------------------------------------
Sent by ShowEasy.ai Booking System
        """.strip()

    def _format_reply_message(self, notification: ReplyNotification) -> str:
        """
        Format reply as human-readable message (simulates email to user).
        """
        return f"""
================================================================================
REPLY TO YOUR BOOKING ENQUIRY #{notification.enquiry_id}
================================================================================

Event: {notification.event_name}

The event organizer has responded to your enquiry:

{notification.merchant_reply}

--------------------------------------------------------------------------------
If you have additional questions, feel free to continue the conversation!
--------------------------------------------------------------------------------
ShowEasy.ai - Your Event Platform
        """.strip()
