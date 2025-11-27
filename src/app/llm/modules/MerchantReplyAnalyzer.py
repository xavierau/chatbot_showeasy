"""
MerchantReplyAnalyzer DSPy Module

Uses LLM to analyze and reformat merchant replies into user-friendly messages.

This module:
1. Takes raw merchant reply + context (user enquiry, event name)
2. Uses ChainOfThought reasoning to understand the reply
3. Reformats it into a clear, friendly message for the user
4. Preserves important details (contact info, pricing, conditions)

Design Pattern: DSPy Module with Signature-based I/O
Following: Clean Architecture, Single Responsibility Principle
"""

import dspy
from langfuse import observe


class MerchantReplySignature(dspy.Signature):
    """
    Analyze and reformat a merchant's reply to a booking enquiry into a user-friendly message.

    You are helping format a merchant's response to make it clear and friendly for the user.
    The merchant may have written a brief, informal, or technical response. Your job is to:

    1. Preserve ALL important information (prices, dates, contact details, conditions)
    2. Make the tone friendly and professional
    3. Structure the information clearly with proper formatting
    4. Add helpful context if the merchant's reply was unclear
    5. Maintain accuracy - do not add information not in the merchant's reply

    Guidelines:
    - If merchant says "yes/no", expand with context
    - If merchant provides contact info, format it clearly
    - If merchant was rude or unprofessional, make it polite but honest
    - If merchant's reply is unclear, acknowledge and suggest next steps
    - Always maintain a helpful, customer-service tone
    """

    user_enquiry: str = dspy.InputField(
        desc="The original enquiry message from the user"
    )
    merchant_reply: str = dspy.InputField(
        desc="The raw reply from the merchant/event organizer"
    )
    event_name: str = dspy.InputField(
        desc="The name of the event this enquiry is about"
    )
    formatted_response: str = dspy.OutputField(
        desc="A clear, friendly, well-formatted message to send to the user. "
             "Must preserve all important details from merchant's reply. "
             "Should be structured with proper paragraphs and formatting."
    )


class MerchantReplyAnalyzer(dspy.Module):
    """
    DSPy module that analyzes and reformats merchant replies.

    Uses ChainOfThought to reason about the best way to present
    the merchant's reply to the user.

    Usage:
        analyzer = MerchantReplyAnalyzer()
        result = analyzer(
            user_enquiry="Can I book 50 tickets?",
            merchant_reply="Yes 15% discount call 1234",
            event_name="Concert XYZ"
        )
        print(result.formatted_response)
    """

    def __init__(self):
        """
        Initialize the analyzer with ChainOfThought reasoning.

        ChainOfThought allows the LLM to think step-by-step about
        how to best reformat the message.
        """
        super().__init__()
        self.predict = dspy.ChainOfThought(MerchantReplySignature)

    @observe(name="merchant_reply_analyzer")
    def forward(self, user_enquiry: str, merchant_reply: str, event_name: str):
        """
        Analyze and reformat the merchant's reply.

        Args:
            user_enquiry: Original user's enquiry message
            merchant_reply: Raw merchant reply (may be informal or unclear)
            event_name: Name of the event

        Returns:
            Prediction with formatted_response field containing
            the user-friendly message

        Example:
            Input:
                user_enquiry: "Do you have group discounts?"
                merchant_reply: "yes 10% for 20+ ppl"
                event_name: "Broadway Musical"

            Output:
                formatted_response: "Great news! The event organizer for
                Broadway Musical offers a 10% group discount for groups of
                20 or more people. ..."
        """
        return self.predict(
            user_enquiry=user_enquiry,
            merchant_reply=merchant_reply,
            event_name=event_name
        )
