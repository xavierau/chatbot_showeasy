import dspy
from ...models import ConversationMessage, Intent
from typing import Optional


class UserMessageIntentSignature(dspy.Signature):
    """Determine the user's intent from their message."""

    user_message: str = dspy.InputField(desc="The user's message.")
    previous_conversation: Optional[dspy.History] = dspy.InputField(
        desc="A list of previous messages in the conversation. This is optional field",
    )
    intent:Intent = dspy.OutputField(desc="The user's intent.")
