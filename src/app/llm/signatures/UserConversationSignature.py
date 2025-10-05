import dspy
from app.models import ConversationMessage, Intent


class UserConversationSignature(dspy.Signature):
    """Generate a response to the user's message based on the conversation history and user's intent."""

    user_message: str = dspy.InputField(desc="The user's current message.")
    previous_conversation: dspy.History = dspy.InputField(
        desc="The previous messages in the conversation."
    )
    user_intent: Intent = dspy.InputField(desc="The user's determined intent.")

    response_message: str = dspy.OutputField(desc="The chatbot's response to the user.")
