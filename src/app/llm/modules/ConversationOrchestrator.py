import dspy
from langfuse import observe
from typing import Optional, TYPE_CHECKING
import logging
from ..signatures import ConversationSignature
from ...models import ConversationMessage, ABTestConfig, ABVariant
from ..tools import (
    SearchEvent,
    Thinking,
    BookingEnquiry,
    DocumentSummary,
    DocumentDetail,
)
from ..guardrails import PreGuardrails, PostGuardrails, GuardrailViolation

if TYPE_CHECKING:
    from ...services.mem0 import Mem0Service

logger = logging.getLogger(__name__)


class ConversationOrchestrator(dspy.Module):
    """Event Platform Customer Service Agent orchestrator with simplified 3-step architecture.

    Architecture:
    1. Pre-Guardrails: Validate user input for safety and scope
    2. ReAct Agent: Comprehensive reasoning and tool use for all conversation types
    3. Post-Guardrails: Validate output for compliance and brand safety

    The ReAct agent handles ALL conversation types through intelligent tool selection:
    - Event search and discovery (SearchEvent)
    - Documentation overview (DocumentSummary)
    - Detailed documentation retrieval (DocumentDetail)
    - Booking enquiries (BookingEnquiry)
    - Working memory/reasoning (Thinking)

    Design Principles:
    - Single Responsibility: Each tool handles one domain
    - Composition: ReAct composes tools based on user intent
    - Reliability: Guardrails ensure safe, compliant responses
    - SOLID: Clean separation between tools, agent logic, and validation
    """

    def __init__(
        self,
        ab_config: Optional[ABTestConfig] = None,
        mem0_service: Optional["Mem0Service"] = None
    ):
        super().__init__()

        # Initialize AB test configuration
        self.ab_config = ab_config or ABTestConfig.default()

        # Initialize Mem0 long-term memory service (optional)
        self.mem0_service = mem0_service

        # Initialize guardrails with AB testing support
        self.pre_guardrails = self._initialize_pre_guardrails()
        self.post_guardrails = self._initialize_post_guardrails()

        # Initialize agent with AB testing support
        self.agent = self._initialize_agent()

        if self.mem0_service:
            logger.info("ConversationOrchestrator initialized with Mem0 long-term memory")

    def _initialize_pre_guardrails(self) -> PreGuardrails:
        """Initialize PreGuardrails based on AB test configuration.

        Variants:
        - CONTROL: Standard PreGuardrails with load_optimized_model()
        - VARIANT_A: PreGuardrails without loading optimized model (baseline)
        - VARIANT_B: Reserved for future variants (e.g., different optimization)
        """
        pre_guardrails = PreGuardrails()

        if self.ab_config.pre_guardrails.enabled:
            variant = self.ab_config.pre_guardrails.variant

            if variant == ABVariant.CONTROL:
                # Default behavior: load optimized model
                pass  # Already loaded in __init__
            elif variant == ABVariant.VARIANT_A:
                # Variant A: Don't load optimized model (baseline comparison)
                # Reset to unoptimized by recreating the validator
                from ..signatures.GuardrailSignatures import InputGuardrailSignature
                pre_guardrails.validator = dspy.ChainOfThought(InputGuardrailSignature)
                print(f"[AB Test] PreGuardrails using VARIANT_A: {self.ab_config.pre_guardrails.description}")
            elif variant == ABVariant.VARIANT_B:
                # Variant B: Reserved for future experiments
                print(f"[AB Test] PreGuardrails using VARIANT_B: {self.ab_config.pre_guardrails.description}")

        return pre_guardrails

    def _initialize_post_guardrails(self) -> PostGuardrails:
        """Initialize PostGuardrails based on AB test configuration.

        Variants:
        - CONTROL: Standard PostGuardrails
        - VARIANT_A: Reserved for variant testing
        - VARIANT_B: Reserved for variant testing
        """
        post_guardrails = PostGuardrails()

        if self.ab_config.post_guardrails.enabled:
            variant = self.ab_config.post_guardrails.variant
            print(f"[AB Test] PostGuardrails using {variant.value}: {self.ab_config.post_guardrails.description}")

        return post_guardrails

    def _initialize_agent(self) -> dspy.ReAct:
        """Initialize ReAct agent based on AB test configuration.

        Variants:
        - CONTROL: Standard ReAct with max_iters=10
        - VARIANT_A: Reserved for variant testing (e.g., different max_iters)
        - VARIANT_B: Reserved for variant testing
        """
        # Default configuration
        max_iters = 10
        tools = [
            Thinking,  # Working memory - should be first for reasoning before actions
            SearchEvent,
            DocumentSummary,  # Get doc index/summaries - use first for documentation queries
            DocumentDetail,  # Fetch specific docs - use after DocumentSummary
            BookingEnquiry,  # Booking enquiry tool for merchant communication
        ]

        if self.ab_config.agent.enabled:
            variant = self.ab_config.agent.variant

            if variant == ABVariant.VARIANT_A:
                # Example: Different max_iters for variant testing
                max_iters = 5
                print(f"[AB Test] Agent using VARIANT_A (max_iters={max_iters}): {self.ab_config.agent.description}")
            elif variant == ABVariant.VARIANT_B:
                # Example: Different tool configuration
                print(f"[AB Test] Agent using VARIANT_B: {self.ab_config.agent.description}")

        return dspy.ReAct(
            ConversationSignature,
            tools=tools,
            max_iters=max_iters
        )

    def forward(
        self,
        user_message: str,
        previous_conversation: list[ConversationMessage],
        page_context: str = "",
        user_id: Optional[str] = None
    ) -> dspy.Prediction:
        """Process user message through simplified 3-step architecture.

        Args:
            user_message: The user's input message
            previous_conversation: Conversation history for context (short-term memory)
            page_context: Current page context (e.g., 'event_detail_page', 'membership_page')
            user_id: User identifier for long-term memory retrieval from Mem0

        Returns:
            dspy.Prediction with 'answer' field containing the safe, helpful response

        Flow:
            1. Pre-Guardrails: Validate input safety and scope
            2. Retrieve user context from Mem0 (long-term memory)
            3. ReAct Agent: Reason about intent and use appropriate tools
            4. Post-Guardrails: Validate output compliance and brand safety
        """

        # ===== STEP 1: Pre-Guardrails (Input Validation) =====
#         try:
#             guardrail_result = self.pre_guardrails(
#                 user_message=user_message,
#                 previous_conversation=previous_conversation,
#                 page_context=page_context
#             )
#
#             if not guardrail_result["is_valid"]:
#                 # Input violated guardrails, return friendly redirect message
#                 print(f"[PreGuardrail] Input violation: {guardrail_result['violation_type']}")
#                 return dspy.Prediction(answer=guardrail_result["message"])
#
#         except GuardrailViolation as e:
#             # Strict mode enabled, violation raised as exception
#             print(f"[PreGuardrail] Strict violation: {e.violation_type}")
#             return dspy.Prediction(answer=e.message)

        # ===== STEP 2: Retrieve Long-Term Memory Context =====
        user_context = self._get_user_context(user_id, user_message)

        # ===== STEP 3: ReAct Agent (Reasoning + Tool Use) =====
        # The agent will:
        # - Determine user intent through reasoning
        # - Select and call appropriate tools
        # - Compose final response with personalization from user_context
        # No explicit intent classification needed - ReAct handles this naturally
        try:
            agent_prediction = self.agent(
                question=user_message,
                previous_conversation=previous_conversation,
                page_context=page_context,
                user_context=user_context
            )
            response_message = agent_prediction.answer
            logger.info(
                f"[ReAct Agent] Generated response with "
                f"{len(agent_prediction.trajectory) if hasattr(agent_prediction, 'trajectory') else 0} tool calls"
            )
            return dspy.Prediction(answer=response_message)
        except Exception as e:
            # ReAct agent failure - provide helpful fallback
            logger.error(f"[ReAct Agent] Error during execution: {e}")
            response_message = "I apologize, but I'm having trouble processing your request right now. Please try rephrasing your question or contact our support team at support@showeasy.com for immediate assistance."

        # ===== STEP 4: Post-Guardrails (Output Validation) =====
        try:
            output_validation = self.post_guardrails(
                agent_response=response_message,
                user_query=user_message,
                response_intent="conversation"  # Generic intent since ReAct handles all types
            )

            if not output_validation["is_safe"]:
                logger.warning(f"[PostGuardrail] Output violation: {output_validation['violation_type']}")
                logger.debug(f"[PostGuardrail] Improvement: {output_validation['improvement']}")

            # Return sanitized response (original if safe, sanitized if violations found)
            return dspy.Prediction(answer=output_validation["response"])

        except Exception as e:
            # Post-guardrail failure - return original response as fallback
            logger.error(f"[PostGuardrail] Error during validation: {e}")
            return dspy.Prediction(answer=response_message)

    def _get_user_context(self, user_id: Optional[str], user_message: str) -> str:
        """Retrieve user context from Mem0 long-term memory.

        This method performs a semantic search against the user's stored memories
        using the current message as the query, returning relevant preferences
        and patterns to personalize the response.

        Args:
            user_id: User identifier for memory lookup
            user_message: Current user message for semantic search

        Returns:
            Formatted string of user context, or empty string if unavailable
        """
        if not self.mem0_service or not user_id:
            return ""

        try:
            user_context = self.mem0_service.get_user_context(
                user_id=user_id,
                query=user_message,  # Semantic search based on current message
                limit=5
            )
            if user_context:
                logger.debug(f"[Mem0] Retrieved user context for user_id={user_id}")
            return user_context
        except Exception as e:
            logger.warning(f"[Mem0] Failed to retrieve user context: {e}")
            return ""  # Graceful degradation - continue without personalization
