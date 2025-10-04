import dspy
from app.models import ConversationMessage


class EventSearchSignature(dspy.Signature):
    """Generate a response to a user's event-related query, potentially using the search tool.

    **Reasoning Guidelines**
    1.  **Language Consistency:** The database and tools use English. If the user's query is in another language (e.g., Chinese), you MUST translate the key concepts (like category, location, or query keywords) to English before calling any tools.
    2.  **Follow-up Questions:** When the user asks a follow-up question about a previous result, be consistent with the parameters you used in the successful, preceding tool call.
    """

    question: str = dspy.InputField(desc="The user's current message/question.")
    previous_conversation: list[ConversationMessage] = dspy.InputField(
        desc="The previous messages in the conversation."
    )

    answer: str = dspy.OutputField(
        desc="The chatbot's response to the user, potentially including event information. When presenting events, MUST include event URLs in markdown format [Event Name](https://eventplatform.test/events/{slug}) using the slug from the database query results."
    )
