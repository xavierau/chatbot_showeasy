from fastapi import FastAPI
import os
import dspy
from typing import Optional
from ..models.UserInputRequest import UserInputRequest, GetMessagesRequest, MessageRequest
from ..models import ABTestConfig, ModuleABConfig, ABVariant, EnquiryReplyRequest
from ..llm.modules.ConversationOrchestrator import ConversationOrchestrator
from ..services.memory import MemoryManager, FileMemoryService
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

# Langfuse client - may be None if unavailable
try:
    langfuse = get_client()
except Exception:
    langfuse = None
app = FastAPI()
app.add_middleware(LoggingMiddleware)

logger = structlog.get_logger(__name__)

# Instantiate Memory Service and Manager (short-term memory)
file_memory_service = FileMemoryService()
memory_manager = MemoryManager(memory_service=file_memory_service)

# Mem0 long-term memory service (lazy initialization)
_mem0_service = None


def get_mem0_service():
    """Lazy initialization of Mem0 service for long-term memory.

    Returns:
        Mem0Service instance or None if unavailable/disabled.

    The service is initialized on first call and cached for subsequent requests.
    If MEM0_ENABLED is set to "false", returns None immediately.
    """
    global _mem0_service

    # Check if Mem0 is explicitly disabled
    if os.getenv("MEM0_ENABLED", "true").lower() == "false":
        return None

    if _mem0_service is None:
        try:
            from ..services.mem0 import Mem0Service
            _mem0_service = Mem0Service()
            logger.info("Mem0 long-term memory service initialized successfully")
        except Exception as e:
            logger.warning(
                "Mem0 service unavailable - continuing without long-term memory",
                error=str(e)
            )
            _mem0_service = None

    return _mem0_service


def get_ab_test_config(user_id: str, session_id: str) -> Optional[ABTestConfig]:
    """Determine AB test configuration based on user_id for consistent variant assignment.

    Uses hash-based bucketing to ensure:
    - Same user always gets same variant (consistency)
    - Even distribution across variants
    - Reproducible results

    Args: Hey, welcome.
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
    def wrapper_function(message:str, content:str, user_id: str, ab_config: Optional[ABTestConfig] = None):
        """Wrapper function with AB testing and long-term memory support.

        Args:
            message: User's input message
            content: Page content context
            user_id: User identifier for Mem0 long-term memory
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
        # Initialize orchestrator with Mem0 long-term memory
        mem0_service = get_mem0_service()
        orchestrator = ConversationOrchestrator(
            ab_config=ab_config,
            mem0_service=mem0_service
        )

        # Get response from orchestrator with user_id for memory lookup
        prediction = orchestrator(
            user_message=message,
            previous_conversation=previous_conversation,
            page_context=content,
            user_id=user_id
        )

        # Log AB test metadata to Langfuse (skip if unavailable)
        if langfuse:
            try:
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
                            },
                            "mem0_enabled": mem0_service is not None
                        }
                    )
                else:
                    langfuse.update_current_trace(
                        user_id=request.user_id,
                        session_id=request.session_id,
                        metadata={"mem0_enabled": mem0_service is not None}
                    )
            except Exception:
                pass  # Langfuse unavailable, skip tracing

        return prediction.answer

    response_content = wrapper_function(
         message=request.user_input,
         content=request.page_content,
         user_id=str(request.user_id) if request.user_id else str(uuid.uuid4()),
         ab_config=ab_config)

    log.debug("Orchestrator response generated", response_length=len(response_content))

    # ===== Update Short-Term Memory (Conversation History) =====
    user_message = {"role": "user", "content": request.user_input}
    assistant_message = {"role": "assistant", "content": response_content}

    # Append new messages without reading entire history first
    memory_manager.append_messages(request.session_id, [user_message, assistant_message])

    # ===== Update Long-Term Memory (Mem0) =====
    mem0_service = get_mem0_service()
    if mem0_service:
        try:
            user_id_str = str(request.user_id) if request.user_id else str(uuid.uuid4())
            mem0_service.add_conversation(
                user_message=request.user_input,
                assistant_message=response_content,
                user_id=user_id_str,
                session_id=request.session_id
            )
            log.debug("Long-term memory updated via Mem0")
        except Exception as e:
            log.warning("Failed to update long-term memory", error=str(e))
            # Non-critical - continue without blocking response

    log.info("Chat request completed successfully")
    return {"message": response_content}
    
@app.post("/chat/messages")
def get_messages(request: GetMessagesRequest):
    log = logger.bind(session_id=request.session_id, endpoint="/chat/messages")
    log.info("Retrieving messages")

    history = memory_manager.get_memory(request.session_id, 5)

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
    # Generate user_id if not provided, then derive session_id from user_id
    # This ensures 1:1 mapping: each user_id has exactly one session_id
    user_id = request.user_id or str(uuid.uuid4())
    session_id = request.session_id or f"session_{user_id}"

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
    def process_message(message: str, user_id: str, ab_config: Optional[ABTestConfig] = None):
        """Process message through the conversation orchestrator with long-term memory."""
        # Initialize orchestrator with Mem0 long-term memory
        mem0_service = get_mem0_service()
        orchestrator = ConversationOrchestrator(
            ab_config=ab_config,
            mem0_service=mem0_service
        )

        prediction = orchestrator(
            user_message=message,
            previous_conversation=previous_conversation,
            page_context=None,
            user_id=user_id
        )

        # Log AB test metadata to Langfuse (skip if unavailable)
        if langfuse:
            try:
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
                            },
                            "mem0_enabled": mem0_service is not None
                        }
                    )
                else:
                    langfuse.update_current_trace(
                        user_id=user_id,
                        session_id=session_id,
                        metadata={"mem0_enabled": mem0_service is not None}
                    )
            except Exception:
                pass  # Langfuse unavailable, skip tracing

        return prediction.answer

    response_content = process_message(
        message=request.message,
        user_id=user_id,
        ab_config=ab_config
    )
    log.debug("Orchestrator response generated", response_length=len(response_content))

    # ===== Update Short-Term Memory (Conversation History) =====
    user_message = {"role": "user", "content": request.message}
    assistant_message = {"role": "assistant", "content": response_content}

    # Append new messages without reading entire history first
    memory_manager.append_messages(session_id, [user_message, assistant_message])

    # ===== Update Long-Term Memory (Mem0) =====
    mem0_service = get_mem0_service()
    if mem0_service:
        try:
            mem0_service.add_conversation(
                user_message=request.message,
                assistant_message=response_content,
                user_id=user_id,
                session_id=session_id
            )
            log.debug("Long-term memory updated via Mem0")
        except Exception as e:
            log.warning("Failed to update long-term memory", error=str(e))
            # Non-critical - continue without blocking response

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
                assistant_message = {"role": "assistant", "content": formatted_message}
                # Append new message without reading entire history first
                memory_manager.append_messages(enquiry['session_id'], [assistant_message])

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


@app.get("/api/enquiry-confirm")
def handle_enquiry_confirm(id: int):
    """
    API endpoint for merchant to confirm a booking enquiry.

    This is a one-click action from the email button. It:
    1. Validates the enquiry exists and is not already responded to
    2. Uses EnquiryResponseFormatter to generate a confirmation message
    3. Updates the enquiry status to 'confirmed'
    4. Sends notification to the user
    5. Updates conversation history

    Args:
        id: Enquiry ID from query parameter

    Returns:
        HTML page confirming the action was successful
    """
    from config.database import DatabaseConnectionPool
    from ..llm.modules.EnquiryResponseFormatter import EnquiryResponseFormatter
    from ..services.notification import NotificationService
    from fastapi.responses import HTMLResponse

    log = logger.bind(enquiry_id=id, endpoint="/api/enquiry-confirm")
    log.info("Enquiry confirmation received")

    connection = None
    try:
        pool = DatabaseConnectionPool()
        connection = pool.get_connection()
        cursor = connection.cursor(dictionary=True)

        # Get enquiry details
        cursor.execute("""
            SELECT
                be.id, be.session_id, be.user_message, be.contact_email,
                be.contact_phone, be.event_id, be.status,
                COALESCE(
                    JSON_UNQUOTE(JSON_EXTRACT(e.name, '$.en')),
                    JSON_UNQUOTE(JSON_EXTRACT(o.name, '$.en'))
                ) as event_name
            FROM booking_enquiries be
            LEFT JOIN events e ON be.event_id = e.id
            INNER JOIN organizers o ON be.organizer_id = o.id
            WHERE be.id = %s
        """, (id,))

        enquiry = cursor.fetchone()

        if not enquiry:
            log.warning("Enquiry not found")
            return HTMLResponse(content=_build_response_html(
                "Enquiry Not Found",
                "The enquiry you're looking for doesn't exist or has been removed.",
                success=False
            ))

        if enquiry['status'] in ('replied', 'confirmed', 'declined', 'completed'):
            log.warning("Enquiry already responded", status=enquiry['status'])
            return HTMLResponse(content=_build_response_html(
                "Already Responded",
                f"This enquiry has already been {enquiry['status']}. No further action needed.",
                success=False
            ))

        # Generate confirmation message using LLM
        formatter = EnquiryResponseFormatter()
        formatted_message = formatter.format_confirmation(
            user_enquiry=enquiry['user_message'],
            event_name=enquiry['event_name']
        )

        log.debug("Confirmation message generated", length=len(formatted_message))

        # Store reply in database
        cursor.execute("""
            INSERT INTO enquiry_replies (enquiry_id, reply_from, reply_message, reply_channel)
            VALUES (%s, 'merchant', %s, %s)
        """, (id, "CONFIRMED", "email"))

        # Update enquiry status
        cursor.execute("""
            UPDATE booking_enquiries SET status = 'confirmed' WHERE id = %s
        """, (id,))

        connection.commit()

        # Send notification to user
        notification_service = NotificationService()
        notification_result = notification_service.send_reply_to_user(
            enquiry_id=id,
            event_name=enquiry['event_name'],
            merchant_reply=formatted_message,
            user_email=enquiry['contact_email'],
            user_phone=enquiry.get('contact_phone')
        )

        if notification_result['success']:
            log.info("User notification sent", channel=notification_result['channel'])
        else:
            log.warning("User notification failed", error=notification_result['message'])

        # Update conversation history
        if enquiry['session_id']:
            try:
                assistant_message = {"role": "assistant", "content": formatted_message}
                # Append new message without reading entire history first
                memory_manager.append_messages(enquiry['session_id'], [assistant_message])
            except Exception as e:
                log.warning("Failed to update conversation history", error=str(e))

        log.info("Enquiry confirmed successfully")
        return HTMLResponse(content=_build_response_html(
            "Booking Confirmed!",
            f"Thank you for confirming the booking for '{enquiry['event_name']}'. "
            "The customer has been notified.",
            success=True
        ))

    except Exception as e:
        log.error("Error confirming enquiry", error=str(e))
        return HTMLResponse(content=_build_response_html(
            "Error",
            f"An error occurred: {str(e)}. Please try again or contact support.",
            success=False
        ))

    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()


@app.get("/api/enquiry-decline")
def handle_enquiry_decline_page(id: int):
    """
    Show a form for merchant to provide decline reason.

    Args:
        id: Enquiry ID from query parameter

    Returns:
        HTML form page for entering decline reason
    """
    from config.database import DatabaseConnectionPool
    from fastapi.responses import HTMLResponse

    log = logger.bind(enquiry_id=id, endpoint="/api/enquiry-decline")
    log.info("Enquiry decline page requested")

    connection = None
    try:
        pool = DatabaseConnectionPool()
        connection = pool.get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                be.id, be.status, be.user_message,
                COALESCE(
                    JSON_UNQUOTE(JSON_EXTRACT(e.name, '$.en')),
                    JSON_UNQUOTE(JSON_EXTRACT(o.name, '$.en'))
                ) as event_name
            FROM booking_enquiries be
            LEFT JOIN events e ON be.event_id = e.id
            INNER JOIN organizers o ON be.organizer_id = o.id
            WHERE be.id = %s
        """, (id,))

        enquiry = cursor.fetchone()

        if not enquiry:
            return HTMLResponse(content=_build_response_html(
                "Enquiry Not Found",
                "The enquiry you're looking for doesn't exist.",
                success=False
            ))

        if enquiry['status'] in ('replied', 'confirmed', 'declined', 'completed'):
            return HTMLResponse(content=_build_response_html(
                "Already Responded",
                f"This enquiry has already been {enquiry['status']}.",
                success=False
            ))

        return HTMLResponse(content=_build_decline_form_html(
            enquiry_id=id,
            event_name=enquiry['event_name'],
            user_message=enquiry['user_message']
        ))

    except Exception as e:
        log.error("Error loading decline page", error=str(e))
        return HTMLResponse(content=_build_response_html(
            "Error",
            f"An error occurred: {str(e)}",
            success=False
        ))

    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()


from pydantic import BaseModel, Field


class EnquiryDeclineRequest(BaseModel):
    """Request model for declining an enquiry."""
    enquiry_id: int = Field(gt=0)
    reason: str = Field(default="", max_length=2000)


@app.post("/api/enquiry-decline")
def handle_enquiry_decline(request: EnquiryDeclineRequest):
    """
    API endpoint for merchant to decline a booking enquiry with a reason.

    This endpoint:
    1. Validates the enquiry exists
    2. Uses EnquiryResponseFormatter to generate a personalized decline message
    3. Updates the enquiry status to 'declined'
    4. Sends notification to the user with the reason
    5. Updates conversation history

    Args:
        request: EnquiryDeclineRequest with enquiry_id and reason

    Returns:
        JSON response with status
    """
    from config.database import DatabaseConnectionPool
    from ..llm.modules.EnquiryResponseFormatter import EnquiryResponseFormatter
    from ..services.notification import NotificationService

    log = logger.bind(enquiry_id=request.enquiry_id, endpoint="/api/enquiry-decline")
    log.info("Enquiry decline received")

    connection = None
    try:
        pool = DatabaseConnectionPool()
        connection = pool.get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                be.id, be.session_id, be.user_message, be.contact_email,
                be.contact_phone, be.event_id, be.status,
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

        if enquiry['status'] in ('replied', 'confirmed', 'declined', 'completed'):
            log.warning("Enquiry already responded", status=enquiry['status'])
            return {"status": "error", "message": f"Enquiry already {enquiry['status']}"}

        # Generate decline message using LLM
        formatter = EnquiryResponseFormatter()
        formatted_message = formatter.format_decline(
            user_enquiry=enquiry['user_message'],
            event_name=enquiry['event_name'],
            merchant_reason=request.reason
        )

        log.debug("Decline message generated", length=len(formatted_message))

        # Store reply in database
        cursor.execute("""
            INSERT INTO enquiry_replies (enquiry_id, reply_from, reply_message, reply_channel)
            VALUES (%s, 'merchant', %s, %s)
        """, (request.enquiry_id, request.reason or "DECLINED", "email"))

        # Update enquiry status
        cursor.execute("""
            UPDATE booking_enquiries SET status = 'declined' WHERE id = %s
        """, (request.enquiry_id,))

        connection.commit()

        # Send notification to user
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

        # Update conversation history
        if enquiry['session_id']:
            try:
                assistant_message = {"role": "assistant", "content": formatted_message}
                # Append new message without reading entire history first
                memory_manager.append_messages(enquiry['session_id'], [assistant_message])
            except Exception as e:
                log.warning("Failed to update conversation history", error=str(e))

        log.info("Enquiry declined successfully")
        return {"status": "success", "message": "Decline sent to user"}

    except Exception as e:
        log.error("Error declining enquiry", error=str(e))
        return {"status": "error", "message": str(e)}

    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()


def _build_response_html(title: str, message: str, success: bool) -> str:
    """Build HTML response page for merchant actions."""
    color = "#28a745" if success else "#dc3545"
    icon = "✓" if success else "✗"

    return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - ShowEasy</title>
</head>
<body style="font-family: Arial, sans-serif; background: #f5f5f5; margin: 0; padding: 40px 20px;">
    <div style="max-width: 500px; margin: 0 auto; background: white; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); overflow: hidden;">
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center;">
            <h1 style="color: white; margin: 0; font-size: 24px;">ShowEasy.ai</h1>
        </div>
        <div style="padding: 40px; text-align: center;">
            <div style="width: 80px; height: 80px; background: {color}; border-radius: 50%; margin: 0 auto 20px; display: flex; align-items: center; justify-content: center;">
                <span style="color: white; font-size: 40px;">{icon}</span>
            </div>
            <h2 style="color: #333; margin: 0 0 15px 0;">{title}</h2>
            <p style="color: #666; margin: 0; line-height: 1.6;">{message}</p>
        </div>
        <div style="background: #f9f9f9; padding: 20px; text-align: center; border-top: 1px solid #eee;">
            <p style="color: #999; margin: 0; font-size: 12px;">You can close this page now.</p>
        </div>
    </div>
</body>
</html>
    """.strip()


def _build_decline_form_html(enquiry_id: int, event_name: str, user_message: str) -> str:
    """Build HTML form for merchant to enter decline reason."""
    return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Decline Enquiry - ShowEasy</title>
</head>
<body style="font-family: Arial, sans-serif; background: #f5f5f5; margin: 0; padding: 40px 20px;">
    <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); overflow: hidden;">
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center;">
            <h1 style="color: white; margin: 0; font-size: 24px;">ShowEasy.ai</h1>
            <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0 0;">Decline Booking Enquiry</p>
        </div>

        <div style="padding: 30px;">
            <div style="background: #f0f4ff; padding: 15px; border-radius: 6px; margin-bottom: 20px;">
                <p style="margin: 0 0 5px 0; color: #667eea; font-weight: bold;">Event: {event_name}</p>
                <p style="margin: 0; color: #666; font-size: 14px;">Enquiry #{enquiry_id}</p>
            </div>

            <div style="background: #fff3cd; padding: 15px; border-radius: 6px; margin-bottom: 20px; border-left: 4px solid #ffc107;">
                <p style="margin: 0 0 5px 0; font-weight: bold; color: #856404;">Customer's Message:</p>
                <p style="margin: 0; color: #666; font-size: 14px; white-space: pre-wrap;">{user_message}</p>
            </div>

            <form id="declineForm" style="margin-top: 20px;">
                <label style="display: block; margin-bottom: 10px; font-weight: bold; color: #333;">
                    Reason for declining (optional):
                </label>
                <textarea
                    name="reason"
                    id="reason"
                    placeholder="e.g., Fully booked, dates not available, special requirements cannot be met..."
                    style="width: 100%; height: 120px; padding: 12px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; resize: vertical; box-sizing: border-box;"
                ></textarea>
                <p style="color: #666; font-size: 12px; margin: 8px 0 20px 0;">
                    Your message will be personalized by our AI to deliver it professionally to the customer.
                </p>

                <div style="display: flex; gap: 10px;">
                    <button
                        type="submit"
                        style="flex: 1; background: #dc3545; color: white; padding: 15px; border: none; border-radius: 6px; font-size: 16px; font-weight: bold; cursor: pointer;"
                    >
                        Decline Enquiry
                    </button>
                    <button
                        type="button"
                        onclick="window.history.back()"
                        style="flex: 1; background: #6c757d; color: white; padding: 15px; border: none; border-radius: 6px; font-size: 16px; cursor: pointer;"
                    >
                        Cancel
                    </button>
                </div>
            </form>
        </div>
    </div>

    <script>
        document.getElementById('declineForm').addEventListener('submit', async function(e) {{
            e.preventDefault();

            const button = this.querySelector('button[type="submit"]');
            button.disabled = true;
            button.textContent = 'Processing...';

            try {{
                const response = await fetch('/api/enquiry-decline', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{
                        enquiry_id: {enquiry_id},
                        reason: document.getElementById('reason').value
                    }})
                }});

                const result = await response.json();

                if (result.status === 'success') {{
                    document.body.innerHTML = `
                        <div style="font-family: Arial, sans-serif; background: #f5f5f5; margin: 0; padding: 40px 20px; min-height: 100vh; box-sizing: border-box;">
                            <div style="max-width: 500px; margin: 0 auto; background: white; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); overflow: hidden;">
                                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center;">
                                    <h1 style="color: white; margin: 0; font-size: 24px;">ShowEasy.ai</h1>
                                </div>
                                <div style="padding: 40px; text-align: center;">
                                    <div style="width: 80px; height: 80px; background: #28a745; border-radius: 50%; margin: 0 auto 20px; display: flex; align-items: center; justify-content: center;">
                                        <span style="color: white; font-size: 40px;">✓</span>
                                    </div>
                                    <h2 style="color: #333; margin: 0 0 15px 0;">Decline Sent</h2>
                                    <p style="color: #666; margin: 0; line-height: 1.6;">The customer has been notified of your response.</p>
                                </div>
                                <div style="background: #f9f9f9; padding: 20px; text-align: center; border-top: 1px solid #eee;">
                                    <p style="color: #999; margin: 0; font-size: 12px;">You can close this page now.</p>
                                </div>
                            </div>
                        </div>
                    `;
                }} else {{
                    alert('Error: ' + result.message);
                    button.disabled = false;
                    button.textContent = 'Decline Enquiry';
                }}
            }} catch (error) {{
                alert('Network error. Please try again.');
                button.disabled = false;
                button.textContent = 'Decline Enquiry';
            }}
        }});
    </script>
</body>
</html>
    """.strip()