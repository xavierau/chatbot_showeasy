"""
EnquiryResponseFormatter DSPy Module

Uses LLM to generate personalized user messages for booking enquiry responses.
Supports confirm, decline, and custom reply scenarios.

Design Pattern: DSPy Module with Signature-based I/O
Following: Clean Architecture, Single Responsibility Principle
"""

import dspy
from langfuse import observe
from enum import Enum


class ResponseType(str, Enum):
    """Types of merchant responses to booking enquiries."""
    CONFIRM = "confirm"
    DECLINE = "decline"
    CUSTOM = "custom"


class ConfirmationResponseSignature(dspy.Signature):
    """
    Generate a friendly confirmation message for a booking enquiry.

    The merchant has confirmed the booking request. Generate a warm, professional
    message that:
    1. Celebrates the good news with the user
    2. References the specific event and their original request
    3. Provides clear next steps if any
    4. Maintains ShowEasy's friendly brand voice
    5. Keeps it concise but complete
    """

    user_enquiry: str = dspy.InputField(
        desc="The original enquiry message from the user"
    )
    event_name: str = dspy.InputField(
        desc="The name of the event this enquiry is about"
    )
    formatted_response: str = dspy.OutputField(
        desc="A warm, celebratory message confirming the booking. "
             "Should reference the event and original request. "
             "Include suggestion to check email for details or contact organizer."
    )


class DeclineResponseSignature(dspy.Signature):
    """
    Generate a sympathetic decline message for a booking enquiry.

    The merchant has declined the booking request. Generate a message that:
    1. Delivers the news gently and professionally
    2. Includes the merchant's reason/message if provided
    3. Suggests alternatives (other events, different dates, contact organizer)
    4. Maintains a helpful, positive tone despite the negative news
    5. Encourages the user to continue using ShowEasy
    """

    user_enquiry: str = dspy.InputField(
        desc="The original enquiry message from the user"
    )
    event_name: str = dspy.InputField(
        desc="The name of the event this enquiry is about"
    )
    merchant_reason: str = dspy.InputField(
        desc="The merchant's reason for declining (may be empty or brief)"
    )
    formatted_response: str = dspy.OutputField(
        desc="A sympathetic but professional message explaining the decline. "
             "Should include the merchant's reason if provided, suggest alternatives, "
             "and encourage the user to explore other options on ShowEasy."
    )


class EnquiryResponseFormatter(dspy.Module):
    """
    DSPy module that generates personalized user messages for booking responses.

    Supports three response types:
    - CONFIRM: Celebratory message when merchant confirms booking
    - DECLINE: Sympathetic message with merchant's reason when declined
    - CUSTOM: General reply formatting (delegates to MerchantReplyAnalyzer)

    Usage:
        formatter = EnquiryResponseFormatter()

        # For confirmation
        result = formatter.format_confirmation(
            user_enquiry="I want to book 50 tickets",
            event_name="Concert XYZ"
        )

        # For decline with reason
        result = formatter.format_decline(
            user_enquiry="I want to book 50 tickets",
            event_name="Concert XYZ",
            merchant_reason="Sold out"
        )
    """

    def __init__(self):
        """Initialize with ChainOfThought for nuanced responses."""
        super().__init__()
        self.confirm_predictor = dspy.ChainOfThought(ConfirmationResponseSignature)
        self.decline_predictor = dspy.ChainOfThought(DeclineResponseSignature)

    @observe(name="enquiry_confirmation_formatter")
    def format_confirmation(self, user_enquiry: str, event_name: str) -> str:
        """
        Generate a confirmation message for the user.

        Args:
            user_enquiry: Original user's enquiry message
            event_name: Name of the event

        Returns:
            Formatted confirmation message string
        """
        result = self.confirm_predictor(
            user_enquiry=user_enquiry,
            event_name=event_name
        )
        return result.formatted_response

    @observe(name="enquiry_decline_formatter")
    def format_decline(self, user_enquiry: str, event_name: str, merchant_reason: str = "") -> str:
        """
        Generate a decline message for the user.

        Args:
            user_enquiry: Original user's enquiry message
            event_name: Name of the event
            merchant_reason: Merchant's reason for declining (optional)

        Returns:
            Formatted decline message string
        """
        result = self.decline_predictor(
            user_enquiry=user_enquiry,
            event_name=event_name,
            merchant_reason=merchant_reason or "No specific reason provided"
        )
        return result.formatted_response
