import dspy
from app.llm.signatures import InputGuardrailSignature

class InputGuardrails(dspy.Module):
    """Simple guardrail module using ChainOfThought reasoning."""

    def __init__(self):
        super().__init__()
        self.predictor = dspy.ChainOfThought(InputGuardrailSignature)

    def forward(self, user_message, previous_conversation=None, page_context=""):
        """Execute guardrail validation with reasoning."""
        result = self.predictor(
            user_message=user_message,
            previous_conversation=previous_conversation,
            page_context=page_context
        )
        return result