from fastapi import FastAPI
import os
import dspy
from typing import Optional
from ..models.UserInputRequest import UserInputRequest, GetMessagesRequest
from ..models import ABTestConfig, ModuleABConfig, ABVariant
from ..llm.modules.ConversationOrchestrator import ConversationOrchestrator
from ..memory_manager import MemoryManager, FileMemoryService
from ..middleware.logging_middleware import LoggingMiddleware
from config import configure_llm, configure_logging
from ..utils.web_scraper import get_page_content
import json
import uuid
import re
import structlog
from langfuse import observe, get_client

configure_llm()
configure_logging()

langfuse = get_client()
app = FastAPI()
app.add_middleware(LoggingMiddleware)

logger = structlog.get_logger(__name__)

# Instantiate Memory Service and Manager
file_memory_service = FileMemoryService()
memory_manager = MemoryManager(memory_service=file_memory_service)


def get_ab_test_config(user_id: str, session_id: str) -> Optional[ABTestConfig]:
    """Determine AB test configuration based on user_id for consistent variant assignment.

    Uses hash-based bucketing to ensure:
    - Same user always gets same variant (consistency)
    - Even distribution across variants
    - Reproducible results

    Args:
        user_id: User identifier for consistent bucketing
        session_id: Session identifier (for logging)

    Returns:
        ABTestConfig or None for control group

    Example configurations:
        # 50/50 split: control vs optimized pre-guardrails
        # 33/33/33 split: control vs variant_a vs variant_b for agent testing

    Environment Variables:
        AB_TEST_ENABLED: Set to "true" to enable AB testing (default: false)
        AB_TEST_MODULE: Which module to test (pre_guardrails, post_guardrails, agent)
        AB_TEST_VARIANT_A_RATIO: Percentage for variant A (default: 33)
        AB_TEST_VARIANT_B_RATIO: Percentage for variant B (default: 33)
    """
    # Check if AB testing is enabled
    if os.getenv("AB_TEST_ENABLED", "false").lower() != "true":
        return None

    # Determine which module to test
    module_to_test = os.getenv("AB_TEST_MODULE", "pre_guardrails")
    variant_a_ratio = int(os.getenv("AB_TEST_VARIANT_A_RATIO", "33"))
    variant_b_ratio = int(os.getenv("AB_TEST_VARIANT_B_RATIO", "33"))

    # Hash user_id for consistent bucketing (0-99)
    import hashlib
    hash_val = int(hashlib.md5(user_id.encode()).hexdigest(), 16) % 100

    # Determine variant based on hash
    if hash_val < variant_a_ratio:
        variant = ABVariant.VARIANT_A
    elif hash_val < variant_a_ratio + variant_b_ratio:
        variant = ABVariant.VARIANT_B
    else:
        variant = ABVariant.CONTROL

    # Create config based on module being tested
    if module_to_test == "pre_guardrails":
        return ABTestConfig(
            pre_guardrails=ModuleABConfig(
                enabled=True,
                variant=variant,
                description=f"Pre-guardrails {variant.value} testing"
            )
        )
    elif module_to_test == "post_guardrails":
        return ABTestConfig(
            post_guardrails=ModuleABConfig(
                enabled=True,
                variant=variant,
                description=f"Post-guardrails {variant.value} testing"
            )
        )
    elif module_to_test == "agent":
        return ABTestConfig(
            agent=ModuleABConfig(
                enabled=True,
                variant=variant,
                description=f"Agent {variant.value} testing"
            )
        )

    return None


@app.get("/")
def read_root():
    return {"message": "Hello World"}

@app.post('/chat')
def chat(request: UserInputRequest):

    log = logger.bind(
        session_id=request.session_id,
        user_id=request.user_id,
        endpoint="/chat"
    )

    log.info("Chat request started", current_url=request.current_url)

    # Get previous conversation
    previous_conversation = memory_manager.get_memory(request.session_id)
    log.debug("Retrieved conversation history", message_count=len(previous_conversation.messages))

    # Determine AB test configuration for this user
    ab_config = get_ab_test_config(request.user_id, request.session_id)
    if ab_config:
        log.info("AB test active", ab_config=ab_config)

    @observe()
    def wrapper_function(message:str, content:str, ab_config: Optional[ABTestConfig] = None):
        """Wrapper function with AB testing support.

        Args:
            ab_config: Optional AB testing configuration for nested modules.
                      If None, uses default configuration (all control).

        Example AB test configurations:
            # Test optimized vs baseline pre-guardrails
            ab_config = ABTestConfig(
                pre_guardrails=ModuleABConfig(
                    enabled=True,
                    variant=ABVariant.VARIANT_A,
                    description="Baseline pre-guardrails without optimization"
                )
            )

            # Test different agent max_iters
            ab_config = ABTestConfig(
                agent=ModuleABConfig(
                    enabled=True,
                    variant=ABVariant.VARIANT_A,
                    description="Agent with max_iters=5 for faster responses"
                )
            )
        """
        orchestrator = ConversationOrchestrator(ab_config=ab_config)

        # Get response from orchestrator
        prediction = orchestrator(user_message=message,
                                  previous_conversation=previous_conversation,
                                  page_context=content)

        # Log AB test metadata to Langfuse
        if ab_config and ab_config.is_any_variant_active():
            langfuse.update_current_trace(
                user_id=request.user_id,
                session_id=request.session_id,
                metadata={
                    "ab_test": {
                        "pre_guardrails": {
                            "enabled": ab_config.pre_guardrails.enabled,
                            "variant": ab_config.pre_guardrails.variant.value,
                            "description": ab_config.pre_guardrails.description
                        },
                        "post_guardrails": {
                            "enabled": ab_config.post_guardrails.enabled,
                            "variant": ab_config.post_guardrails.variant.value,
                            "description": ab_config.post_guardrails.description
                        },
                        "agent": {
                            "enabled": ab_config.agent.enabled,
                            "variant": ab_config.agent.variant.value,
                            "description": ab_config.agent.description
                        }
                    }
                }
            )
        else:
            langfuse.update_current_trace(
                user_id=request.user_id,
                session_id=request.session_id,
            )

        return prediction.answer

    response_content = wrapper_function(
         message=request.user_input,
         content=request.page_content,
         ab_config=ab_config)

    log.debug("Orchestrator response generated", response_length=len(response_content))

    # Create new messages in dspy.History format
    user_message = {"role": "user", "content": request.user_input}
    assistant_message = {"role": "assistant", "content": response_content}

    # Update conversation history with dspy.History
    new_messages = previous_conversation.messages + [user_message, assistant_message]
    new_conversation = dspy.History(messages=new_messages)
    memory_manager.update_memory(request.session_id, new_conversation)

    log.info("Chat request completed successfully")
    return {"message": response_content}
    
@app.post("/chat/messages")
def get_messages(request: GetMessagesRequest):
    log = logger.bind(session_id=request.session_id, endpoint="/chat/messages")
    log.info("Retrieving messages")

    history = memory_manager.get_memory(request.session_id)

    # Add UUID to each message dict
    messages_array = []
    for msg in history.messages:
        msg_dict = dict(msg)
        msg_dict['id'] = str(uuid.uuid4())
        messages_array.append(msg_dict)

    log.info("Messages retrieved successfully", message_count=len(messages_array))
    return {"messages": messages_array}

@app.get("/health")
def get_health():
    return {"status": "ok"}
