"""
Unit tests for EmailNotificationChannel

Tests email construction, retry logic, and availability checks
using mocked SMTP connections.
"""

import pytest
from unittest.mock import patch, MagicMock
import smtplib

from app.services.notification import (
    EmailNotificationChannel,
    EnquiryNotification,
    ReplyNotification
)


@pytest.fixture
def email_channel():
    """Create EmailNotificationChannel with test configuration."""
    with patch.dict('os.environ', {
        'MAIL_HOST': 'smtp.gmail.com',
        'MAIL_PORT': '465',
        'MAIL_USERNAME': 'test@example.com',
        'MAIL_PASSWORD': 'test_password',
        'MAIL_FROM_ADDRESS': 'noreply@showeasy.ai',
        'MAIL_FROM_NAME': 'ShowEasy Test'
    }):
        return EmailNotificationChannel()


@pytest.fixture
def enquiry_notification():
    """Create test EnquiryNotification."""
    return EnquiryNotification(
        enquiry_id=123,
        event_name="Test Concert",
        user_message="I want to book 50 tickets for my company event.",
        user_email="user@example.com",
        user_phone="+852 1234 5678",
        merchant_email="merchant@example.com",
        merchant_phone="+852 9876 5432",
        reply_url="http://localhost:3010/api/enquiry-reply?id=123"
    )


@pytest.fixture
def reply_notification():
    """Create test ReplyNotification."""
    return ReplyNotification(
        enquiry_id=123,
        event_name="Test Concert",
        merchant_reply="Yes, we can accommodate 50 people. 15% group discount available.",
        user_email="user@example.com",
        user_phone="+852 1234 5678"
    )


class TestEmailNotificationChannelInit:
    """Tests for EmailNotificationChannel initialization."""

    def test_init_loads_config_from_env(self, email_channel):
        """Should load configuration from environment variables."""
        assert email_channel.host == "smtp.gmail.com"
        assert email_channel.port == 465
        assert email_channel.username == "test@example.com"
        assert email_channel.password == "test_password"
        assert email_channel.from_address == "noreply@showeasy.ai"
        assert email_channel.from_name == "ShowEasy Test"

    def test_init_uses_defaults(self):
        """Should use default values when env vars not set."""
        with patch.dict('os.environ', {}, clear=True):
            channel = EmailNotificationChannel()
            assert channel.host == "smtp.gmail.com"
            assert channel.port == 465
            assert channel.from_name == "ShowEasy.ai"


class TestEmailNotificationChannelAvailability:
    """Tests for is_available() method."""

    def test_is_available_when_all_credentials_present(self, email_channel):
        """Should return True when all required credentials are present."""
        assert email_channel.is_available() is True

    def test_is_not_available_when_missing_username(self):
        """Should return False when username is missing."""
        with patch.dict('os.environ', {
            'MAIL_HOST': 'smtp.gmail.com',
            'MAIL_PORT': '465',
            'MAIL_PASSWORD': 'test_password',
            'MAIL_FROM_ADDRESS': 'noreply@showeasy.ai'
        }, clear=True):
            channel = EmailNotificationChannel()
            assert channel.is_available() is False

    def test_is_not_available_when_missing_password(self):
        """Should return False when password is missing."""
        with patch.dict('os.environ', {
            'MAIL_HOST': 'smtp.gmail.com',
            'MAIL_PORT': '465',
            'MAIL_USERNAME': 'test@example.com',
            'MAIL_FROM_ADDRESS': 'noreply@showeasy.ai'
        }, clear=True):
            channel = EmailNotificationChannel()
            assert channel.is_available() is False


class TestEmailNotificationChannelName:
    """Tests for get_channel_name() method."""

    def test_get_channel_name_returns_email(self, email_channel):
        """Should return 'email' as channel name."""
        assert email_channel.get_channel_name() == "email"


class TestSendEnquiryToMerchant:
    """Tests for send_enquiry_to_merchant() method."""

    @patch('smtplib.SMTP_SSL')
    def test_send_enquiry_success(self, mock_smtp_class, email_channel, enquiry_notification):
        """Should send email successfully and return success result."""
        mock_smtp = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_smtp

        result = email_channel.send_enquiry_to_merchant(enquiry_notification)

        assert result['success'] is True
        assert result['channel'] == 'email'
        assert 'merchant@example.com' in result['message']
        mock_smtp.login.assert_called_once_with('test@example.com', 'test_password')
        mock_smtp.send_message.assert_called_once()

    @patch('smtplib.SMTP_SSL')
    def test_send_enquiry_email_contains_correct_content(self, mock_smtp_class, email_channel, enquiry_notification):
        """Should construct email with correct subject and recipients."""
        mock_smtp = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_smtp

        email_channel.send_enquiry_to_merchant(enquiry_notification)

        sent_message = mock_smtp.send_message.call_args[0][0]
        assert sent_message['To'] == 'merchant@example.com'
        assert 'ShowEasy Test' in sent_message['From']
        assert '#123' in sent_message['Subject']
        assert 'Test Concert' in sent_message['Subject']

    @patch('smtplib.SMTP_SSL')
    def test_send_enquiry_failure_returns_error(self, mock_smtp_class, email_channel, enquiry_notification):
        """Should return error result when SMTP fails."""
        mock_smtp_class.return_value.__enter__.side_effect = smtplib.SMTPException("Connection failed")

        result = email_channel.send_enquiry_to_merchant(enquiry_notification)

        assert result['success'] is False
        assert result['channel'] == 'email'
        assert 'Failed' in result['message']


class TestSendReplyToUser:
    """Tests for send_reply_to_user() method."""

    @patch('smtplib.SMTP_SSL')
    def test_send_reply_success(self, mock_smtp_class, email_channel, reply_notification):
        """Should send reply email successfully and return success result."""
        mock_smtp = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_smtp

        result = email_channel.send_reply_to_user(reply_notification)

        assert result['success'] is True
        assert result['channel'] == 'email'
        assert 'user@example.com' in result['message']

    @patch('smtplib.SMTP_SSL')
    def test_send_reply_email_contains_correct_content(self, mock_smtp_class, email_channel, reply_notification):
        """Should construct reply email with correct subject and recipients."""
        mock_smtp = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_smtp

        email_channel.send_reply_to_user(reply_notification)

        sent_message = mock_smtp.send_message.call_args[0][0]
        assert sent_message['To'] == 'user@example.com'
        assert '#123' in sent_message['Subject']
        assert 'Reply' in sent_message['Subject']


class TestRetryLogic:
    """Tests for retry mechanism."""

    @patch('time.sleep')
    @patch('smtplib.SMTP_SSL')
    def test_retry_on_transient_failure(self, mock_smtp_class, mock_sleep, email_channel, enquiry_notification):
        """Should retry on transient SMTP failures with exponential backoff."""
        mock_smtp = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_smtp
        mock_smtp.send_message.side_effect = [
            smtplib.SMTPException("Temporary failure"),
            smtplib.SMTPException("Still failing"),
            None  # Success on third attempt
        ]

        result = email_channel.send_enquiry_to_merchant(enquiry_notification)

        assert result['success'] is True
        assert mock_smtp.send_message.call_count == 3
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(1)  # First backoff: 2^0 = 1
        mock_sleep.assert_any_call(2)  # Second backoff: 2^1 = 2

    @patch('time.sleep')
    @patch('smtplib.SMTP_SSL')
    def test_fail_after_max_retries(self, mock_smtp_class, mock_sleep, email_channel, enquiry_notification):
        """Should fail after exhausting all retry attempts."""
        mock_smtp = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_smtp
        mock_smtp.send_message.side_effect = smtplib.SMTPException("Persistent failure")

        result = email_channel.send_enquiry_to_merchant(enquiry_notification)

        assert result['success'] is False
        assert mock_smtp.send_message.call_count == 3  # max_retries = 3


class TestEmailTemplates:
    """Tests for email template generation."""

    def test_enquiry_html_contains_required_elements(self, email_channel, enquiry_notification):
        """Should generate HTML with all required enquiry information."""
        html = email_channel._build_enquiry_html(enquiry_notification)

        assert 'ShowEasy' in html
        assert '#123' in html
        assert 'Test Concert' in html
        assert 'user@example.com' in html
        assert '+852 1234 5678' in html
        assert '50 tickets' in html
        assert enquiry_notification.reply_url in html

    def test_enquiry_html_contains_confirm_decline_buttons(self, email_channel, enquiry_notification):
        """Should generate HTML with Confirm and Decline action buttons."""
        html = email_channel._build_enquiry_html(enquiry_notification)

        assert 'Confirm Booking' in html
        assert 'Decline' in html
        assert 'enquiry-confirm?id=123' in html
        assert 'enquiry-decline?id=123' in html
        # Should also have custom reply link
        assert 'custom reply' in html.lower()

    def test_enquiry_plain_contains_action_urls(self, email_channel, enquiry_notification):
        """Should generate plain text with all action URLs."""
        plain = email_channel._build_enquiry_plain(enquiry_notification)

        assert 'Confirm Booking' in plain
        assert 'Decline' in plain
        assert 'enquiry-confirm?id=123' in plain
        assert 'enquiry-decline?id=123' in plain
        assert 'Custom Reply' in plain

    def test_enquiry_plain_contains_required_elements(self, email_channel, enquiry_notification):
        """Should generate plain text with all required enquiry information."""
        plain = email_channel._build_enquiry_plain(enquiry_notification)

        assert '#123' in plain
        assert 'Test Concert' in plain
        assert 'user@example.com' in plain
        assert '50 tickets' in plain

    def test_reply_html_contains_required_elements(self, email_channel, reply_notification):
        """Should generate HTML with all required reply information."""
        html = email_channel._build_reply_html(reply_notification)

        assert 'ShowEasy' in html
        assert '#123' in html
        assert 'Test Concert' in html
        assert '15% group discount' in html

    def test_reply_plain_contains_required_elements(self, email_channel, reply_notification):
        """Should generate plain text with all required reply information."""
        plain = email_channel._build_reply_plain(reply_notification)

        assert '#123' in plain
        assert 'Test Concert' in plain
        assert '15% group discount' in plain

    def test_enquiry_without_phone(self, email_channel):
        """Should handle enquiry without phone number gracefully."""
        notification = EnquiryNotification(
            enquiry_id=456,
            event_name="No Phone Event",
            user_message="Test message",
            user_email="user@example.com",
            user_phone=None,
            merchant_email="merchant@example.com",
            merchant_phone=None,
            reply_url="http://example.com"
        )

        html = email_channel._build_enquiry_html(notification)
        plain = email_channel._build_enquiry_plain(notification)

        assert 'Phone:' not in html or 'None' not in html
        assert notification.user_email in html
        assert notification.user_email in plain
