from fastapi import FastAPI
import os
import dspy
from typing import Optional
from ..models.UserInputRequest import UserInputRequest, GetMessagesRequest, MessageRequest
from ..models import ABTestConfig, ModuleABConfig, ABVariant, EnquiryReplyRequest
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


@app.post("/api/message")
def receive_message(request: MessageRequest):
    """Receive a message with optional user and session identifiers."""
    # Generate session_id if not provided
    session_id = request.session_id or str(uuid.uuid4())
    user_id = request.user_id or str(uuid.uuid4())

    log = logger.bind(
        user_id=user_id,
        session_id=session_id,
        endpoint="/api/message"
    )
    log.info("Message received", message_length=len(request.message))

    # Get previous conversation
    previous_conversation = memory_manager.get_memory(session_id)
    log.debug("Retrieved conversation history", message_count=len(previous_conversation.messages))

    # Determine AB test configuration for this user
    ab_config = get_ab_test_config(user_id, session_id)
    if ab_config:
        log.info("AB test active", ab_config=ab_config)

    @observe()
    def process_message(message: str, ab_config: Optional[ABTestConfig] = None):
        """Process message through the conversation orchestrator."""
        orchestrator = ConversationOrchestrator(ab_config=ab_config)

        prediction = orchestrator(
            user_message=message,
            previous_conversation=previous_conversation,
            page_context=None
        )

        # Log AB test metadata to Langfuse
        if ab_config and ab_config.is_any_variant_active():
            langfuse.update_current_trace(
                user_id=user_id,
                session_id=session_id,
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
                user_id=user_id,
                session_id=session_id,
            )

        return prediction.answer

    response_content = process_message(message=request.message, ab_config=ab_config)
    log.debug("Orchestrator response generated", response_length=len(response_content))

    # Create new messages in dspy.History format
    user_message = {"role": "user", "content": request.message}
    assistant_message = {"role": "assistant", "content": response_content}

    # Update conversation history with dspy.History
    new_messages = previous_conversation.messages + [user_message, assistant_message]
    new_conversation = dspy.History(messages=new_messages)
    memory_manager.update_memory(session_id, new_conversation)

    log.info("Message processed successfully")
    return {
        "status": "success",
        "message": response_content,
        "user_id": user_id,
        "session_id": session_id
    }


@app.post("/api/enquiry-reply")
def handle_enquiry_reply(request: EnquiryReplyRequest):
    """
    API endpoint to receive merchant replies to booking enquiries.

    This endpoint:
    1. Validates the enquiry exists
    2. Uses the MerchantReplyAnalyzer to format the reply
    3. Updates the enquiry status in database
    4. Sends notification to the user
    5. Updates conversation history if session exists

    Args:
        request: EnquiryReplyRequest with enquiry_id, reply_message, reply_channel

    Returns:
        Dictionary with status and message

    Errors:
        - Enquiry not found
        - Database errors
        - Notification failures (logged but not returned as error)
    """
    from config.database import DatabaseConnectionPool
    from ..llm.modules.MerchantReplyAnalyzer import MerchantReplyAnalyzer
    from ..services.notification import NotificationService

    log = logger.bind(
        enquiry_id=request.enquiry_id,
        reply_channel=request.reply_channel,
        endpoint="/api/enquiry-reply"
    )
    log.info("Enquiry reply received")

    try:
        # Step 1: Get enquiry details from database
        pool = DatabaseConnectionPool()
        connection = pool.get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                be.id, be.session_id, be.user_message, be.contact_email, be.contact_phone, be.event_id,
                COALESCE(
                    JSON_UNQUOTE(JSON_EXTRACT(e.name, '$.en')),
                    JSON_UNQUOTE(JSON_EXTRACT(o.name, '$.en'))
                ) as event_name
            FROM booking_enquiries be
            LEFT JOIN events e ON be.event_id = e.id
            INNER JOIN organizers o ON be.organizer_id = o.id
            WHERE be.id = %s
        """, (request.enquiry_id,))

        enquiry = cursor.fetchone()

        if not enquiry:
            log.warning("Enquiry not found")
            return {"status": "error", "message": "Enquiry not found"}

        log.debug("Enquiry details retrieved", event_name=enquiry['event_name'])

        # Step 2: Use MerchantReplyAnalyzer to format the reply
        @observe(name="merchant_reply_formatting")
        def analyze_and_format_reply(user_enquiry: str, merchant_reply: str, event_name: str):
            """Use LLM to format merchant reply into user-friendly message."""
            analyzer = MerchantReplyAnalyzer()
            result = analyzer(
                user_enquiry=user_enquiry,
                merchant_reply=merchant_reply,
                event_name=event_name
            )
            return result.formatted_response

        formatted_message = analyze_and_format_reply(
            enquiry['user_message'],
            request.reply_message,
            enquiry['event_name']
        )

        log.debug("Reply formatted by analyzer", formatted_length=len(formatted_message))

        # Step 3: Store reply in database
        cursor.execute("""
            INSERT INTO enquiry_replies (enquiry_id, reply_from, reply_message, reply_channel)
            VALUES (%s, 'merchant', %s, %s)
        """, (request.enquiry_id, request.reply_message, request.reply_channel))

        # Step 4: Update enquiry status to 'replied'
        cursor.execute("""
            UPDATE booking_enquiries SET status = 'replied' WHERE id = %s
        """, (request.enquiry_id,))

        connection.commit()

        log.info("Reply stored in database")

        # Step 5: Send notification to user
        notification_service = NotificationService()
        notification_result = notification_service.send_reply_to_user(
            enquiry_id=request.enquiry_id,
            event_name=enquiry['event_name'],
            merchant_reply=formatted_message,
            user_email=enquiry['contact_email'],
            user_phone=enquiry.get('contact_phone')
        )

        if notification_result['success']:
            log.info("User notification sent", channel=notification_result['channel'])
        else:
            log.warning("User notification failed", error=notification_result['message'])

        # Step 6: Add reply to conversation history if session exists
        if enquiry['session_id']:
            try:
                conversation = memory_manager.get_memory(enquiry['session_id'])
                assistant_message = {"role": "assistant", "content": formatted_message}
                new_messages = conversation.messages + [assistant_message]
                new_conversation = dspy.History(messages=new_messages)
                memory_manager.update_memory(enquiry['session_id'], new_conversation)

                log.debug("Conversation history updated", session_id=enquiry['session_id'])
            except Exception as e:
                log.warning("Failed to update conversation history", error=str(e))
                # Non-critical error, don't fail the request

        log.info("Enquiry reply processed successfully")
        return {"status": "success", "message": "Reply delivered to user"}

    except Exception as e:
        log.error("Error processing enquiry reply", error=str(e))
        return {"status": "error", "message": str(e)}

    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()
