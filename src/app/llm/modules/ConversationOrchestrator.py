import dspy
from langfuse import observe
from ..signatures import (
    UserMessageIntentSignature,
    UserConversationSignature,
    EventSearchSignature,
    SearchQueryAnalysisSignature,
    AgentResponseSignature,
)
from ...models import ConversationMessage, Intent
from ..tools import SearchEvent
from ..guardrails import PreGuardrails, PostGuardrails, GuardrailViolation


class ConversationOrchestrator(dspy.Module):
    """Event Platform Customer Service Agent orchestrator with guardrails.

    This orchestrator coordinates the entire conversation flow:
    1. Pre-Guardrails: Validate user input for safety and scope
    2. Intent Classification: Determine what the user wants
    3. Response Generation: Generate appropriate response based on intent
    4. Post-Guardrails: Validate output for compliance and brand safety
    5. Return safe, helpful response to user
    """

    def __init__(self):
        super().__init__()
        # Guardrails
        self.pre_guardrails = PreGuardrails()
        self.post_guardrails = PostGuardrails()

        # Intent and Response Modules
        self.determine_intent = dspy.Predict(UserMessageIntentSignature)
        self.generate_response = dspy.ChainOfThought(UserConversationSignature)
        self.analyze_search_query = dspy.Predict(SearchQueryAnalysisSignature)
        self.agent_response = dspy.Predict(AgentResponseSignature)

        # Event Search Agent (ReAct)
        self.event_search_agent = dspy.ReAct(EventSearchSignature, tools=[SearchEvent])

    def forward(self, user_message: str, previous_conversation: list[ConversationMessage], page_context: str = "") -> str:
        """Process user message through guardrails, intent classification, and response generation.

        Args:
            user_message: The user's input message
            previous_conversation: Conversation history
            page_context: Current page context (e.g., 'event_detail_page', 'membership_page')

        Returns:
            Safe, helpful response from the customer service agent
        """
        # ===== STEP 1: Pre-Guardrails (Input Validation) =====
        try:
            guardrail_result = self.pre_guardrails(
                user_message=user_message,
                previous_conversation=previous_conversation,
                page_context=page_context
            )

            if not guardrail_result["is_valid"]:
                # Input violated guardrails, return friendly redirect message
                print(f"[PreGuardrail] Input violation: {guardrail_result['violation_type']}")
                return guardrail_result["message"]

        except GuardrailViolation as e:
            # Strict mode enabled, violation raised as exception
            print(f"[PreGuardrail] Strict violation: {e.violation_type}")
            return e.message

        # ===== STEP 2: Intent Classification =====
        intent_prediction = self.determine_intent(
            user_message=user_message,
            previous_conversation=previous_conversation,
            page_context=page_context
        )
        intent = intent_prediction.intent
        print(f"[Intent] Classified as: {intent}")

        # ===== STEP 3: Response Generation Based on Intent =====
        response_message = ""

        if intent == Intent.SEARCH_EVENT:
            # Event search flow with query analysis
            query_analysis = self.analyze_search_query(
                user_message=user_message,
                previous_conversation=previous_conversation,
                page_context=page_context
            )

            if not query_analysis.is_specific:
                # Query too general, return clarifying question
                response_message = query_analysis.clarifying_question
            else:
                # Query specific enough, execute search with ReAct agent
                response_prediction = self.event_search_agent(
                    question=user_message,
                    previous_conversation=previous_conversation,
                    page_context=page_context
                )
                # Refine the agent's response for brand voice
                agent_refined = self.agent_response(
                    user_input=user_message,
                    agent_answer=response_prediction.answer,
                    agent_reasoning=response_prediction.reasoning,
                    page_context=page_context
                )
                response_message = agent_refined.message

        else:
            # Non-search intents (membership, tickets, general, etc.)
            response_prediction = self.generate_response(
                user_message=user_message,
                previous_conversation=previous_conversation,
                page_context=page_context,
                user_intent=intent,
            )
            response_message = response_prediction.response_message

        # ===== STEP 4: Post-Guardrails (Output Validation) =====
        try:
            output_validation = self.post_guardrails(
                agent_response=response_message,
                user_query=user_message,
                response_intent=str(intent)
            )

            if not output_validation["is_safe"]:
                print(f"[PostGuardrail] Output violation: {output_validation['violation_type']}")
                print(f"[PostGuardrail] Improvement: {output_validation['improvement']}")

            # Return sanitized response (original if safe, sanitized if violations found)
            return output_validation["response"]

        except Exception as e:
            # Post-guardrail failure - return original response as fallback
            print(f"[PostGuardrail] Error during validation: {e}")
            return response_message
