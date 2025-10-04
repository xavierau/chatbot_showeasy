import dspy
from typing import List
from app.models import ConversationMessage

class SearchQueryAnalysisSignature(dspy.Signature):
    """
    Analyzes a user's message to determine if it's a specific and actionable request for searching events.
    If the query is too general (e.g., "any interesting events?", "what's fun?"), it identifies it as not specific and generates a clarifying question.
    """

    user_message = dspy.InputField(desc="The user's current message about searching for events.")
    previous_conversation: List[ConversationMessage] = dspy.InputField(desc="The previous turns of the conversation, providing context.")
    
    is_specific: bool = dspy.OutputField(
        desc="A boolean flag. Set to True if the user's message contains specific criteria (like category, date, location, or specific keywords beyond just 'interesting' or 'fun') OR if the current message, in conjunction with the previous conversation, provides enough detail to perform a meaningful search. Set to False if the query is still too general.",
    )
    
    clarifying_question = dspy.OutputField(
        desc="If the query is not specific, generate a friendly question to ask the user for more details (e.g., 'Sounds fun! To help me find the perfect event, could you tell me what kind of events you're interested in, or a preferred date or location?'). If the query is specific, this can be an empty string."
    )
