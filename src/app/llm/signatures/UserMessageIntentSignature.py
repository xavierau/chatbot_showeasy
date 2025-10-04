import dspy
from ...models import ConversationMessage, Intent


class UserMessageIntentSignature(dspy.Signature):
    """Determine the user's intent from their message."""

    user_message: str = dspy.InputField(desc="The user's message.")
    previous_conversation: list[ConversationMessage] = dspy.InputField(
        desc="A list of previous messages in the conversation."
    )
    intent: Intent = dspy.OutputField(
        desc=f"The user's intent. One of {[e.value for e in Intent]}."
    )
