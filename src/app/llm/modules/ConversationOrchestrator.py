import dspy
from ..signatures import (
    UserMessageIntentSignature,
    UserConversationSignature,
    EventSearchSignature,
    SearchQueryAnalysisSignature,
    AgentResponseSignature,
)
from ...models import ConversationMessage, Intent
from ..tools import SearchEvent


class ConversationOrchestrator(dspy.Module):
    def __init__(self):
        super().__init__()
        self.determine_intent = dspy.Predict(UserMessageIntentSignature)
        self.generate_response = dspy.ChainOfThought(UserConversationSignature)
        self.analyze_search_query = dspy.Predict(SearchQueryAnalysisSignature)
        self.agent_response = dspy.Predict(AgentResponseSignature)
        # Pass the tool instance directly, not a call to it.
        self.event_search_agent = dspy.ReAct(EventSearchSignature, tools=[SearchEvent])

    def forward(self, user_message: str, previous_conversation: list[ConversationMessage], page_context: str = "") -> str:
        # First, determine the user's intent.
        intent_prediction = self.determine_intent(
            user_message=user_message, 
            previous_conversation=previous_conversation,
            page_context=page_context
        )
        intent = intent_prediction.intent

        # Based on the intent, either use the ReAct agent for event searches
        # or the standard response generation for other intents.
        if intent == Intent.SEARCH_EVENT:
            # Analyze the user's query for specificity, considering the conversation history.
            query_analysis = self.analyze_search_query(
                user_message=user_message, 
                previous_conversation=previous_conversation,
                page_context=page_context
            )

            if not query_analysis.is_specific:
                # If the query is not specific, return the clarifying question.
                return query_analysis.clarifying_question
            else:
                # If the query is specific, proceed with the event search.
                response_prediction = self.event_search_agent(
                    question=user_message,
                    previous_conversation=previous_conversation,
                    page_context=page_context
                )
                agent_response = self.agent_response(
                    user_input=user_message,
                    agent_answer=response_prediction.answer,
                    agent_reasoning=response_prediction.reasoning,
                    page_context=page_context
                )
                return agent_response.message
        else:
            response_prediction = self.generate_response(
                user_message=user_message,
                previous_conversation=previous_conversation,
                page_context=page_context,
                user_intent=intent,
            )
            return response_prediction.response_message
