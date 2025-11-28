"""
Email Notification Channel - SMTP Implementation

This is a concrete implementation of NotificationChannel that sends emails
via SMTP (Gmail) with HTML templates and retry logic.

Design Pattern: Strategy Pattern (Concrete Strategy)
"""

import os
import smtplib
import logging
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict
from .notification_interface import (
    NotificationChannel,
    EnquiryNotification,
    ReplyNotification
)

logger = logging.getLogger(__name__)


class EmailNotificationChannel(NotificationChannel):
    """
    SMTP Email notification channel with HTML templates and retry logic.

    Configuration via environment variables:
    - MAIL_HOST: SMTP server hostname (default: smtp.gmail.com)
    - MAIL_PORT: SMTP port (default: 465 for SSL)
    - MAIL_USERNAME: SMTP authentication username
    - MAIL_PASSWORD: SMTP authentication password
    - MAIL_FROM_ADDRESS: Sender email address
    - MAIL_FROM_NAME: Sender display name (default: ShowEasy.ai)
    """

    def __init__(self):
        """Initialize email channel with configuration from environment."""
        logger.debug("[EmailNotificationChannel] Initializing...")
        self.host = os.getenv("MAIL_HOST", "smtp.gmail.com")
        self.port = int(os.getenv("MAIL_PORT", "465"))
        self.username = os.getenv("MAIL_USERNAME")
        self.password = os.getenv("MAIL_PASSWORD")
        self.from_address = os.getenv("MAIL_FROM_ADDRESS")
        self.from_name = os.getenv("MAIL_FROM_NAME", "ShowEasy.ai")
        self.max_retries = 3
        logger.debug(f"[EmailNotificationChannel] Config: host={self.host}, port={self.port}, from={self.from_address}")

    def send_enquiry_to_merchant(self, notification: EnquiryNotification) -> Dict[str, any]:
        """
        Send booking enquiry email to merchant.

        Args:
            notification: EnquiryNotification with all enquiry details

        Returns:
            Dictionary with success status, message, and channel name
        """
        logger.info(f"[EmailNotificationChannel] Sending enquiry #{notification.enquiry_id} to {notification.merchant_email}")

        subject = f"[ShowEasy] New Booking Enquiry #{notification.enquiry_id} - {notification.event_name}"
        html_body = self._build_enquiry_html(notification)
        plain_body = self._build_enquiry_plain(notification)

        msg = self._create_email(
            to_email=notification.merchant_email,
            subject=subject,
            html_body=html_body,
            plain_body=plain_body
        )

        try:
            self._send_with_retry(msg)
            logger.info(f"[EmailNotificationChannel] Enquiry email sent successfully to {notification.merchant_email}")
            return {
                "success": True,
                "message": f"Enquiry email sent to {notification.merchant_email}",
                "channel": "email"
            }
        except Exception as e:
            logger.error(f"[EmailNotificationChannel] Failed to send enquiry email: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"Failed to send email: {str(e)}",
                "channel": "email"
            }

    def send_reply_to_user(self, notification: ReplyNotification) -> Dict[str, any]:
        """
        Send merchant reply email to user.

        Args:
            notification: ReplyNotification with reply details

        Returns:
            Dictionary with success status, message, and channel name
        """
        logger.info(f"[EmailNotificationChannel] Sending reply for enquiry #{notification.enquiry_id} to {notification.user_email}")

        subject = f"[ShowEasy] Reply to Your Enquiry #{notification.enquiry_id} - {notification.event_name}"
        html_body = self._build_reply_html(notification)
        plain_body = self._build_reply_plain(notification)

        msg = self._create_email(
            to_email=notification.user_email,
            subject=subject,
            html_body=html_body,
            plain_body=plain_body
        )

        try:
            self._send_with_retry(msg)
            logger.info(f"[EmailNotificationChannel] Reply email sent successfully to {notification.user_email}")
            return {
                "success": True,
                "message": f"Reply email sent to {notification.user_email}",
                "channel": "email"
            }
        except Exception as e:
            logger.error(f"[EmailNotificationChannel] Failed to send reply email: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"Failed to send email: {str(e)}",
                "channel": "email"
            }

    def get_channel_name(self) -> str:
        """Return channel identifier."""
        return "email"

    def is_available(self) -> bool:
        """
        Check if SMTP credentials are configured.

        Returns:
            True if all required credentials are present
        """
        available = all([
            self.host,
            self.port,
            self.username,
            self.password,
            self.from_address
        ])
        logger.debug(f"[EmailNotificationChannel] Availability check: {available}")
        return available

    def _create_email(self, to_email: str, subject: str, html_body: str, plain_body: str) -> MIMEMultipart:
        """
        Create multipart email with HTML and plain text versions.

        Args:
            to_email: Recipient email address
            subject: Email subject line
            html_body: HTML version of email body
            plain_body: Plain text version of email body

        Returns:
            MIMEMultipart message ready to send
        """
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{self.from_name} <{self.from_address}>"
        msg["To"] = to_email

        part1 = MIMEText(plain_body, "plain", "utf-8")
        part2 = MIMEText(html_body, "html", "utf-8")

        msg.attach(part1)
        msg.attach(part2)

        return msg

    def _send_with_retry(self, msg: MIMEMultipart) -> None:
        """
        Send email with retry logic and exponential backoff.

        Args:
            msg: Email message to send

        Raises:
            Exception: If all retry attempts fail
        """
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                logger.debug(f"[EmailNotificationChannel] Send attempt {attempt + 1}/{self.max_retries}")
                with smtplib.SMTP_SSL(self.host, self.port) as server:
                    server.login(self.username, self.password)
                    server.send_message(msg)
                logger.debug("[EmailNotificationChannel] Email sent successfully")
                return
            except (smtplib.SMTPException, OSError) as e:
                last_exception = e
                logger.warning(f"[EmailNotificationChannel] Attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    sleep_time = 2 ** attempt
                    logger.debug(f"[EmailNotificationChannel] Retrying in {sleep_time}s...")
                    time.sleep(sleep_time)

        raise last_exception

    def _build_enquiry_html(self, notification: EnquiryNotification) -> str:
        """Build HTML email body for enquiry to merchant."""
        phone_line = f"<p><strong>Phone:</strong> {notification.user_phone}</p>" if notification.user_phone else ""

        # Build action URLs from reply_url base
        base_url = notification.reply_url.rsplit('/', 1)[0]  # Remove last path segment
        confirm_url = f"{base_url}/enquiry-confirm?id={notification.enquiry_id}"
        decline_url = f"{base_url}/enquiry-decline?id={notification.enquiry_id}"

        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
        <h1 style="color: white; margin: 0; font-size: 24px;">ShowEasy.ai</h1>
        <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0 0;">New Booking Enquiry</p>
    </div>

    <div style="background: #f9f9f9; padding: 30px; border: 1px solid #e0e0e0; border-top: none;">
        <div style="background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <h2 style="color: #667eea; margin-top: 0;">Enquiry #{notification.enquiry_id}</h2>

            <div style="margin: 20px 0; padding: 15px; background: #f0f4ff; border-radius: 6px;">
                <p style="margin: 0;"><strong>Event:</strong> {notification.event_name}</p>
            </div>

            <h3 style="color: #333; border-bottom: 2px solid #667eea; padding-bottom: 10px;">Customer Information</h3>
            <p><strong>Email:</strong> <a href="mailto:{notification.user_email}" style="color: #667eea;">{notification.user_email}</a></p>
            {phone_line}

            <h3 style="color: #333; border-bottom: 2px solid #667eea; padding-bottom: 10px;">Message</h3>
            <div style="background: #fff; padding: 15px; border-left: 4px solid #667eea; margin: 15px 0;">
                <p style="margin: 0; white-space: pre-wrap;">{notification.user_message}</p>
            </div>

            <div style="text-align: center; margin-top: 30px;">
                <a href="{confirm_url}" style="display: inline-block; background: #28a745; color: white; padding: 15px 30px; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 0 10px 10px 0;">Confirm Booking</a>
                <a href="{decline_url}" style="display: inline-block; background: #dc3545; color: white; padding: 15px 30px; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 0 0 10px 10px;">Decline</a>
            </div>

            <div style="text-align: center; margin-top: 15px;">
                <a href="{notification.reply_url}" style="color: #667eea; text-decoration: underline; font-size: 14px;">Or send a custom reply</a>
            </div>
        </div>
    </div>

    <div style="text-align: center; padding: 20px; color: #666; font-size: 12px;">
        <p>This email was sent by ShowEasy.ai Booking System</p>
        <p>You can also reply directly to this email</p>
    </div>
</body>
</html>
        """.strip()

    def _build_enquiry_plain(self, notification: EnquiryNotification) -> str:
        """Build plain text email body for enquiry to merchant."""
        phone_line = f"\nPhone: {notification.user_phone}" if notification.user_phone else ""

        # Build action URLs from reply_url base
        base_url = notification.reply_url.rsplit('/', 1)[0]
        confirm_url = f"{base_url}/enquiry-confirm?id={notification.enquiry_id}"
        decline_url = f"{base_url}/enquiry-decline?id={notification.enquiry_id}"

        return f"""
================================================================================
NEW BOOKING ENQUIRY #{notification.enquiry_id}
================================================================================

Event: {notification.event_name}

CUSTOMER INFORMATION
--------------------
Email: {notification.user_email}{phone_line}

MESSAGE
-------
{notification.user_message}

--------------------------------------------------------------------------------
RESPOND TO THIS ENQUIRY:

* Confirm Booking: {confirm_url}
* Decline: {decline_url}
* Send Custom Reply: {notification.reply_url}

Or reply directly to this email.
--------------------------------------------------------------------------------
Sent by ShowEasy.ai Booking System
        """.strip()

    def _build_reply_html(self, notification: ReplyNotification) -> str:
        """Build HTML email body for reply to user."""
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
        <h1 style="color: white; margin: 0; font-size: 24px;">ShowEasy.ai</h1>
        <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0 0;">Response to Your Enquiry</p>
    </div>

    <div style="background: #f9f9f9; padding: 30px; border: 1px solid #e0e0e0; border-top: none;">
        <div style="background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <h2 style="color: #667eea; margin-top: 0;">Enquiry #{notification.enquiry_id}</h2>

            <div style="margin: 20px 0; padding: 15px; background: #f0f4ff; border-radius: 6px;">
                <p style="margin: 0;"><strong>Event:</strong> {notification.event_name}</p>
            </div>

            <h3 style="color: #333; border-bottom: 2px solid #667eea; padding-bottom: 10px;">Event Organizer's Response</h3>
            <div style="background: #fff; padding: 15px; border-left: 4px solid #28a745; margin: 15px 0;">
                <p style="margin: 0; white-space: pre-wrap;">{notification.merchant_reply}</p>
            </div>

            <div style="background: #e8f5e9; padding: 15px; border-radius: 6px; margin-top: 20px;">
                <p style="margin: 0; color: #2e7d32;">If you have additional questions, feel free to continue the conversation through our platform!</p>
            </div>
        </div>
    </div>

    <div style="text-align: center; padding: 20px; color: #666; font-size: 12px;">
        <p>ShowEasy.ai - Your Event Platform</p>
        <p>Thank you for using our service</p>
    </div>
</body>
</html>
        """.strip()

    def _build_reply_plain(self, notification: ReplyNotification) -> str:
        """Build plain text email body for reply to user."""
        return f"""
================================================================================
REPLY TO YOUR BOOKING ENQUIRY #{notification.enquiry_id}
================================================================================

Event: {notification.event_name}

EVENT ORGANIZER'S RESPONSE
--------------------------
{notification.merchant_reply}

--------------------------------------------------------------------------------
If you have additional questions, feel free to continue the conversation!
--------------------------------------------------------------------------------
ShowEasy.ai - Your Event Platform
        """.strip()
