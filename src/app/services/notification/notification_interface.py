"""
Notification Channel Interface (Strategy Pattern)

This module defines the abstract interface for notification channels.
Following the Strategy Pattern, concrete implementations (Email, WhatsApp, SMS, Log)
can be swapped at runtime without changing client code.

Design Pattern: Strategy Pattern
Purpose: Allow different notification channels to be plugged in without modifying core logic
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class EnquiryNotification:
    """
    Data class containing all information needed to send an enquiry notification.

    This acts as a Data Transfer Object (DTO) to decouple the notification
    content from the delivery mechanism.
    """
    enquiry_id: int
    event_name: str
    user_message: str
    user_email: str
    user_phone: Optional[str]
    merchant_email: str
    merchant_phone: Optional[str]
    reply_url: str  # URL for merchant to reply


@dataclass
class ReplyNotification:
    """
    Data class for sending reply notifications to users.
    """
    enquiry_id: int
    event_name: str
    merchant_reply: str
    user_email: str
    user_phone: Optional[str]


class NotificationChannel(ABC):
    """
    Abstract base class defining the interface for notification channels.

    All concrete notification implementations must inherit from this class
    and implement the send_enquiry_to_merchant and send_reply_to_user methods.

    This follows the Interface Segregation Principle (ISP) - clients depend
    on abstractions, not concrete implementations.
    """

    @abstractmethod
    def send_enquiry_to_merchant(self, notification: EnquiryNotification) -> Dict[str, any]:
        """
        Send a booking enquiry notification to the merchant.

        Args:
            notification: EnquiryNotification containing all required data

        Returns:
            Dictionary with:
                - success: bool - Whether send was successful
                - message: str - Status or error message
                - channel: str - Channel name (e.g., 'email', 'log')
        """
        pass

    @abstractmethod
    def send_reply_to_user(self, notification: ReplyNotification) -> Dict[str, any]:
        """
        Send a merchant reply notification to the user.

        Args:
            notification: ReplyNotification containing all required data

        Returns:
            Dictionary with:
                - success: bool - Whether send was successful
                - message: str - Status or error message
                - channel: str - Channel name
        """
        pass

    @abstractmethod
    def get_channel_name(self) -> str:
        """
        Return the name of this notification channel.

        Returns:
            String identifier for this channel (e.g., 'email', 'whatsapp', 'log')
        """
        pass

    def is_available(self) -> bool:
        """
        Check if this notification channel is properly configured and available.

        Default implementation returns True. Override in concrete classes to
        perform actual availability checks (e.g., API key validation).

        Returns:
            Boolean indicating if channel is available for use
        """
        return True
