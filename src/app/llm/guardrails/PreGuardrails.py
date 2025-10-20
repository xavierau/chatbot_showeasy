import dspy
import os
from typing import Optional, Dict
from ..signatures.GuardrailSignatures import InputGuardrailSignature
from ...models import ConversationMessage
from pathlib import Path



class GuardrailViolation(Exception):
    """Exception raised when input violates guardrail policies."""

    def __init__(self, violation_type: str, message: str):
        self.violation_type = violation_type
        self.message = message
        super().__init__(message)


class PreGuardrails(dspy.Module):
    """Pre-processing guardrails to validate user input before processing.

    Ensures all user queries align with the Event Platform Customer Service Agent's scope:
    - Event discovery and recommendations
    - Ticket purchasing assistance
    - Membership benefits and upgrades
    - Itinerary planning

    Blocks:
    - Off-topic queries (politics, medical advice, etc.)
    - Prompt injection attacks
    - Safety violations (harmful/inappropriate content)
    - PII exposure risks
    - Malicious intent
    """

    def __init__(self):
        super().__init__()
        self.validator = dspy.ChainOfThought(InputGuardrailSignature)
        self.load_optimized_model()

        # Load configuration
        self.strict_mode = os.getenv("GUARDRAIL_STRICT_MODE", "true").lower() == "true"
        self.strict_mode = False

        # Blocked keywords for quick pattern matching (Layer 1 defense)
        self.injection_patterns = [
            "ignore previous instructions",
            "ignore all previous",
            "forget everything",
            "system prompt",
            "you are now",
            "act as a",
            "pretend you are",
            "roleplay as",
            "your instructions are",
            "disregard all",
            "new instructions:",
            "admin mode",
            "developer mode",
            "jailbreak",
        ]

        self.competitor_keywords = [
            "eventbrite",
            "ticketmaster",
            "stubhub",
            "seatgeek",
            "vivid seats",
            "ticketek",
            "axs.com",
        ]

    def _quick_pattern_check(self, message: str) -> Optional[Dict[str, str]]:
        """Fast pattern-based checks before LLM validation.

        Returns violation dict if pattern detected, None otherwise.
        """
        message_lower = message.lower()

        # Check for prompt injection patterns
        for pattern in self.injection_patterns:
            if pattern in message_lower:
                return {
                    "violation_type": "prompt_injection",
                    "message": "I'm here to help you discover events and manage your tickets! Let me know what you're looking for."
                }

        # Check for competitor mentions (suspicious if user brings them up)
        for competitor in self.competitor_keywords:
            if competitor in message_lower:
                return {
                    "violation_type": "out_of_scope",
                    "message": "I specialize in helping you find events on our platform! What kind of events are you interested in?"
                }

        return None

    def forward(
        self,
        user_message: str,
        previous_conversation: Optional[dspy.History] = None,
        page_context: str = ""
    ) -> Dict[str, any]:
        """Validate user input through guardrails.

        Args:
            user_message: The user's input to validate
            previous_conversation: Conversation history for context
            page_context: Current page context (e.g., 'event_detail_page')

        Returns:
            Dict with keys:
                - is_valid: bool
                - violation_type: str (if invalid)
                - message: str (user-friendly message if invalid)

        Raises:
            GuardrailViolation: If strict mode is enabled and input is invalid
        """
        # Layer 1: Quick pattern-based checks
        quick_check = self._quick_pattern_check(user_message)
        if quick_check:
            if self.strict_mode:
                raise GuardrailViolation(
                    violation_type=quick_check["violation_type"],
                    message=quick_check["message"]
                )
            return {
                "is_valid": False,
                "violation_type": quick_check["violation_type"],
                "message": quick_check["message"]}


        # Layer 2: LLM-based validation for nuanced cases
        validation = self.validator(
            user_message=user_message,
            previous_conversation=previous_conversation,
            page_context=page_context
        )

        if not validation.is_valid:

            if self.strict_mode:
                raise GuardrailViolation(
                    violation_type=validation.violation_type,
                    message=validation.user_friendly_message
                )

            return {
                "is_valid": False,
                "violation_type": validation.violation_type,
                "message": validation.user_friendly_message}


        # Input passed all guardrails
        return {
        "is_valid": True,
            "violation_type": "",
            "message": ""
        }



    def load_optimized_model(self):
        """Load a local optimized model for the guardrail validator."""

        # Try to load optimized model if it exists
        current_dir = Path(__file__).parent
        json_file_path = current_dir.parent.parent / 'optimized' / 'InputGuardrails' / 'current.json'

        if json_file_path.exists():
            try:
                # Load the entire module (not just validator) to match how it was saved
                self.load(str(json_file_path))
            except (KeyError, FileNotFoundError, Exception) as e:
                # If loading fails, continue with unoptimized model
                # Log error in development but don't break production
                import os
                if os.getenv("DEBUG", "false").lower() == "true":
                    print(f"Warning: Failed to load optimized model: {e}")
                pass

