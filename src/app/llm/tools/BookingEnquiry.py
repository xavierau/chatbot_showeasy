"""
BookingEnquiry DSPy Tool

Allows users to send booking enquiries to event organizers/merchants.
Following the established pattern: private implementation function + DSPy Tool wrapper.

This tool:
1. Retrieves merchant contact information from the database
2. Creates an enquiry record in the database
3. Sends notification to the merchant via the configured channel
4. Returns confirmation to the user

Design Patterns:
- Tool Pattern: Private function + DSPy Tool wrapper
- Context Manager: Database connection management
- Dependency Injection: NotificationService
"""

import dspy
import logging
from typing import Dict, Optional
from contextlib import contextmanager
from config.database import DatabaseConnectionPool
from app.services.notification import NotificationService

# Configure logger for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Valid enquiry types - must match database constraint chk_enquiry_type
VALID_ENQUIRY_TYPES = {'ticket_booking', 'custom_booking', 'group_booking', 'special_request'}


def _infer_enquiry_type(
    user_message: str,
    event_id: Optional[int] = None,
    merchant_name: Optional[str] = None,
    provided_type: Optional[str] = None
) -> str:
    """
    Smart inference of enquiry type based on context.

    Inference Rules (in priority order):
    1. Always analyze message content for special indicators (group, wheelchair, etc.)
    2. If special indicators found → use inferred type (overrides provided_type)
    3. If no special indicators and provided_type is valid → use provided_type
    4. Otherwise, use mode-based default:
       - event_id provided → 'ticket_booking'
       - merchant_name provided → 'custom_booking'

    This ensures that when agent passes default 'custom_booking' but event_id is provided,
    we correctly infer 'ticket_booking' unless there are special indicators.

    Args:
        user_message: User's enquiry message
        event_id: Event ID if provided (event-based enquiry)
        merchant_name: Merchant name if provided (merchant-based enquiry)
        provided_type: Provided enquiry type (may be default, not explicit)

    Returns:
        Inferred enquiry type (one of VALID_ENQUIRY_TYPES)
    """

    # Convert message to lowercase for pattern matching
    msg_lower = user_message.lower()

    # Group booking indicators
    group_indicators = [
        'group', '團體', '公司', 'corporate', 'company',
        'school', '學校', 'organization', '機構',
        '20', '30', '40', '50', '100',  # Large numbers
        'bulk', 'wholesale', '批量'
    ]

    # Special request indicators
    special_indicators = [
        'wheelchair', '輪椅', 'accessibility', '無障礙',
        'special need', '特殊需求', 'disability', '殘障',
        'private', '私人', 'vip', 'exclusive', '專屬',
        'customiz', '定制', '客製'
    ]

    # Priority 1: Check for group booking indicators (overrides everything)
    if any(indicator in msg_lower for indicator in group_indicators):
        logger.debug(f"[EnquiryTypeInference] Group indicator detected → group_booking (overrides provided_type)")
        return 'group_booking'

    # Priority 2: Check for special request indicators (overrides everything)
    if any(indicator in msg_lower for indicator in special_indicators):
        logger.debug(f"[EnquiryTypeInference] Special request indicator detected → special_request (overrides provided_type)")
        return 'special_request'

    # Priority 3: No special indicators found - determine based on mode
    # If event_id is provided, it's an event-based enquiry → ticket_booking
    # If merchant_name is provided, it's a merchant-based enquiry → custom_booking
    # The provided_type is ignored when mode clearly indicates the type
    if event_id:
        # Event-based: user has identified specific event → standard ticket booking
        logger.debug(f"[EnquiryTypeInference] Event-based enquiry (event_id={event_id}) → ticket_booking")
        return 'ticket_booking'
    elif merchant_name:
        # Merchant-based: general merchant contact → custom booking
        logger.debug(f"[EnquiryTypeInference] Merchant-based enquiry (merchant_name={merchant_name}) → custom_booking")
        return 'custom_booking'
    elif provided_type and provided_type in VALID_ENQUIRY_TYPES:
        # Fallback: use provided type if valid (shouldn't reach here in normal flow)
        logger.debug(f"[EnquiryTypeInference] Using provided_type as fallback: {provided_type}")
        return provided_type
    else:
        # Final fallback: custom_booking
        logger.warning(f"[EnquiryTypeInference] No mode detected, defaulting to custom_booking")
        return 'custom_booking'


@contextmanager
def get_db_connection():
    """
    Context manager for database connections.

    Ensures connections are properly closed after use,
    following the existing pattern from SearchEvent.py.

    Yields:
        MySQL connection object
    """
    logger.debug("[BookingEnquiry] Attempting to get database connection...")
    pool = DatabaseConnectionPool()
    connection = pool.get_connection()
    logger.debug("[BookingEnquiry] Database connection obtained successfully")
    try:
        yield connection
    except Exception as e:
        logger.error(f"[BookingEnquiry] Database connection error: {e}", exc_info=True)
        raise
    finally:
        if connection.is_connected():
            connection.close()
            logger.debug("[BookingEnquiry] Database connection closed")


def _create_booking_enquiry(
    user_message: str,
    contact_email: str,
    event_id: Optional[int] = None,
    merchant_name: Optional[str] = None,
    contact_phone: Optional[str] = None,
    enquiry_type: str = "custom_booking",
    session_id: Optional[str] = None
) -> Dict[str, str]:
    """
    Create a booking enquiry and send it to the merchant.

    This function supports TWO modes:
    1. Event-based enquiry: Requires event_id (traditional events)
    2. Merchant-based enquiry: Requires merchant_name (restaurants, general enquiries)

    Following Single Responsibility Principle - this function orchestrates the
    enquiry creation workflow.

    Args:
        user_message: User's booking enquiry message (REQUIRED)
        contact_email: User's contact email for merchant replies (REQUIRED)
        event_id: The event ID to enquire about (Optional - for event-based enquiries)
        merchant_name: Merchant/organizer name (Optional - for direct merchant enquiries)
        contact_phone: User's contact phone (optional)
        enquiry_type: Type of enquiry (auto-inferred if not provided):
            - 'ticket_booking': Standard event ticket booking (auto-set when event_id provided)
            - 'group_booking': Large group or corporate bookings (20+ people)
            - 'special_request': Special accommodations (accessibility, VIP, private showings)
            - 'custom_booking': General merchant enquiry (auto-set when merchant_name provided)
        session_id: Session ID for tracking conversation context (optional)

    Returns:
        Dictionary with:
            - status: 'success' or 'error'
            - message: Human-readable message for user
            - enquiry_id: (optional) Enquiry reference number if successful

    Workflow:
        1. Validate parameters (must have either event_id OR merchant_name)
        2. Query database for merchant info (via event or merchant name)
        3. Validate merchant contact is available
        4. Insert enquiry record into database
        5. Send notification to merchant via NotificationService
        6. Update enquiry status to 'sent' if notification succeeds
        7. Return confirmation to user

    Error Handling:
        - Missing parameters → User-friendly error
        - Event/Merchant not found → User-friendly error
        - Merchant contact missing → User-friendly error
        - Notification failure → Error with support contact
        - Database exception → Generic error with support contact
    """
    # Log all input parameters for debugging
    # Using INFO level for key parameters to ensure visibility even without DEBUG mode
    logger.info(f"[BookingEnquiry] === Starting booking enquiry creation ===")
    logger.info(f"[BookingEnquiry] Key params: event_id={event_id}, merchant_name={merchant_name}, enquiry_type={enquiry_type}, contact_email={contact_email}")
    logger.debug(f"[BookingEnquiry] Full input parameters:")
    logger.debug(f"  - user_message: {user_message[:100]}..." if len(user_message) > 100 else f"  - user_message: {user_message}")
    logger.debug(f"  - contact_email: {contact_email}")
    logger.debug(f"  - event_id: {event_id}")
    logger.debug(f"  - merchant_name: {merchant_name}")
    logger.debug(f"  - contact_phone: {contact_phone}")
    logger.debug(f"  - enquiry_type: {enquiry_type}")
    logger.debug(f"  - session_id: {session_id}")

    # Validate parameters: must have either event_id OR merchant_name (not both, not neither)
    if not event_id and not merchant_name:
        logger.warning("[BookingEnquiry] Validation failed: Neither event_id nor merchant_name provided")
        return {
            "status": "error",
            "message": "Please provide either an event ID or merchant name for your enquiry."
        }

    if event_id and merchant_name:
        logger.warning(f"[BookingEnquiry] Validation failed: Both event_id ({event_id}) and merchant_name ({merchant_name}) provided")
        return {
            "status": "error",
            "message": "Please provide either event_id OR merchant_name, not both."
        }

    # Smart inference of enquiry type
    enquiry_type = _infer_enquiry_type(
        user_message=user_message,
        event_id=event_id,
        merchant_name=merchant_name,
        provided_type=enquiry_type
    )

    mode = 'event-based' if event_id else 'merchant-based'
    logger.info(f"[BookingEnquiry] Parameter validation passed. Mode: {mode}, enquiry_type: {enquiry_type}")

    try:
        with get_db_connection() as connection:
            cursor = connection.cursor(dictionary=True)

            # Step 1: Get merchant/organizer info
            logger.debug("[BookingEnquiry] Step 1: Querying merchant/organizer info...")
            if event_id:
                # Mode 1: Event-based enquiry (existing behavior)
                query = """
                    SELECT
                        e.organizer_id,
                        o.contact_email as merchant_email,
                        o.contact_phone as merchant_phone,
                        JSON_UNQUOTE(JSON_EXTRACT(e.name, '$.en')) as event_name,
                        JSON_UNQUOTE(JSON_EXTRACT(o.name, '$.en')) as merchant_name
                    FROM events e
                    INNER JOIN organizers o ON e.organizer_id = o.id
                    WHERE e.id = %s AND e.event_status = 'published'
                """
                logger.debug(f"[BookingEnquiry] Executing event-based query for event_id={event_id}")
                cursor.execute(query, (event_id,))
            else:
                # Mode 2: Merchant-based enquiry (new behavior for restaurants)
                query = """
                    SELECT
                        o.id as organizer_id,
                        o.contact_email as merchant_email,
                        o.contact_phone as merchant_phone,
                        JSON_UNQUOTE(JSON_EXTRACT(o.name, '$.en')) as merchant_name,
                        'General Enquiry' as event_name
                    FROM organizers o
                    WHERE JSON_UNQUOTE(JSON_EXTRACT(o.name, '$.en')) LIKE %s
                       OR JSON_UNQUOTE(JSON_EXTRACT(o.name, '$.zh_tw')) LIKE %s
                    LIMIT 1
                """
                logger.debug(f"[BookingEnquiry] Executing merchant-based query for merchant_name={merchant_name}")
                cursor.execute(query, (f"%{merchant_name}%", f"%{merchant_name}%"))

            merchant_data = cursor.fetchone()
            logger.info(f"[BookingEnquiry] Step 1 result: merchant_data={'found' if merchant_data else 'NOT FOUND'}")
            logger.debug(f"[BookingEnquiry] Full query result: {merchant_data}")

            if not merchant_data:
                if event_id:
                    logger.warning(f"[BookingEnquiry] Event not found for event_id={event_id}")
                    return {
                        "status": "error",
                        "message": "Event not found or not available for booking enquiries. Please check the event ID and try again."
                    }
                else:
                    logger.warning(f"[BookingEnquiry] Merchant not found for merchant_name={merchant_name}")
                    return {
                        "status": "error",
                        "message": f"Merchant '{merchant_name}' not found. Please check the spelling or contact support at info@showeasy.ai"
                    }

            if not merchant_data.get('merchant_email'):
                logger.warning(f"[BookingEnquiry] Merchant found but no email: organizer_id={merchant_data.get('organizer_id')}")
                return {
                    "status": "error",
                    "message": "Merchant contact information not available. Please contact support at info@showeasy.ai"
                }

            logger.info(f"[BookingEnquiry] Merchant found: organizer_id={merchant_data.get('organizer_id')}, email={merchant_data.get('merchant_email')}")

            # Step 2: Create enquiry record
            logger.info("[BookingEnquiry] Step 2: Creating enquiry record in database...")
            insert_params = (
                event_id,  # NULL for merchant-based enquiries
                merchant_data['organizer_id'],
                session_id,  # Optional - may be NULL if not provided
                enquiry_type,
                user_message,
                contact_email,
                contact_phone,
                merchant_data['merchant_email'],
                merchant_data['merchant_phone']
            )
            logger.debug(f"[BookingEnquiry] INSERT params: event_id={event_id}, organizer_id={merchant_data['organizer_id']}, session_id={session_id}, enquiry_type={enquiry_type}")

            cursor.execute("""
                INSERT INTO booking_enquiries
                (event_id, organizer_id, session_id, enquiry_type, user_message, contact_email,
                 contact_phone, merchant_email, merchant_phone, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending')
            """, insert_params)

            connection.commit()
            enquiry_id = cursor.lastrowid
            logger.info(f"[BookingEnquiry] Enquiry record created successfully: enquiry_id={enquiry_id}")

            # Step 3: Send notification to merchant
            logger.info("[BookingEnquiry] Step 3: Sending notification to merchant...")
            notification_service = NotificationService()
            display_name = merchant_data['event_name'] if event_id else merchant_data['merchant_name']
            logger.debug(f"[BookingEnquiry] NotificationService initialized, channel: {notification_service.get_current_channel()}")

            logger.debug(f"[BookingEnquiry] Calling send_enquiry_to_merchant with:")
            logger.debug(f"  - enquiry_id: {enquiry_id}")
            logger.debug(f"  - event_name: {display_name}")
            logger.debug(f"  - user_email: {contact_email}")
            logger.debug(f"  - merchant_email: {merchant_data['merchant_email']}")

            send_result = notification_service.send_enquiry_to_merchant(
                enquiry_id=enquiry_id,
                event_name=display_name,
                user_message=user_message,
                user_email=contact_email,
                user_phone=contact_phone,
                merchant_email=merchant_data['merchant_email'],
                merchant_phone=merchant_data.get('merchant_phone')
            )

            logger.info(f"[BookingEnquiry] Step 3 result: notification success={send_result.get('success')}, channel={send_result.get('channel')}")
            logger.debug(f"[BookingEnquiry] Full notification result: {send_result}")

            if send_result['success']:
                # Step 4: Update status to 'sent'
                logger.debug("[BookingEnquiry] Step 4: Updating enquiry status to 'sent'...")
                cursor.execute("""
                    UPDATE booking_enquiries SET status = 'sent' WHERE id = %s
                """, (enquiry_id,))
                connection.commit()
                logger.info(f"[BookingEnquiry] Enquiry status updated to 'sent' for enquiry_id={enquiry_id}")

                merchant_name_display = merchant_data.get('merchant_name', 'the merchant')
                success_result = {
                    "status": "success",
                    "message": f"Your enquiry has been sent to {merchant_name_display}. Reference: #{enquiry_id}. They will respond within 24-48 hours via email.",
                    "enquiry_id": str(enquiry_id)
                }
                logger.info(f"[BookingEnquiry] === Booking enquiry completed successfully: enquiry_id={enquiry_id} ===")
                return success_result
            else:
                logger.error(f"[BookingEnquiry] Notification send failed: {send_result}")
                return {
                    "status": "error",
                    "message": "Failed to send enquiry. Please try again or contact support at info@showeasy.ai"
                }

    except Exception as e:
        # Log the error with full stack trace for debugging
        logger.error(f"[BookingEnquiry] Exception creating booking enquiry: {e}", exc_info=True)
        logger.error(f"[BookingEnquiry] Exception type: {type(e).__name__}")
        logger.error(f"[BookingEnquiry] Exception args: {e.args}")

        return {
            "status": "error",
            "message": "An error occurred while processing your enquiry. Please contact support at info@showeasy.ai"
        }


# Create DSPy Tool
BookingEnquiry = dspy.Tool(
    func=_create_booking_enquiry,
    name="booking_enquiry",
    desc="""Send a booking enquiry to event organizers/merchants with SMART TYPE INFERENCE.

This tool supports TWO modes:
1. EVENT-BASED ENQUIRY: For specific events (concerts, shows, performances)
2. MERCHANT-BASED ENQUIRY: For restaurants, meal packages, or general merchant enquiries

SMART TYPE INFERENCE:
The tool automatically determines the correct enquiry_type based on:
- Mode (event_id vs merchant_name)
- User message content (keywords like 'group', 'wheelchair', 'corporate', etc.)
- You DON'T need to specify enquiry_type in most cases - it's auto-inferred!

Enquiry Types (auto-selected):
- 'ticket_booking': Standard event ticket booking (when event_id provided, no special indicators)
- 'group_booking': Large groups (keywords: group, 20+, corporate, school, company)
- 'special_request': Special needs (keywords: wheelchair, accessibility, private, VIP, exclusive)
- 'custom_booking': General merchant enquiry (when merchant_name provided)

Use this tool when users want to:
- Book tickets for a specific event (after SearchEvent provides event_id)
- Book large groups, corporate events, or school trips (20+ people)
- Make restaurant reservations or enquire about meal packages
- Request special accommodations (accessibility, VIP, private showings)
- Ask organizers questions before purchasing
- Contact a merchant directly

DO NOT use this tool for:
- General questions about tickets (use DocumentDetail/DocumentSummary)
- Platform information (use DocumentDetail/DocumentSummary)
- Questions about membership (use DocumentDetail for membership docs)

Required Parameters (ALWAYS):
- user_message: User's detailed enquiry message
- contact_email: User's email address for merchant to reply

Mode Selection (MUST provide ONE):
- event_id: For event-based enquiries (e.g., concerts, shows)
- merchant_name: For merchant-based enquiries (e.g., restaurants, direct contact)

Optional Parameters:
- contact_phone: User's phone number
- enquiry_type: Override auto-inference (rarely needed)

Example Scenarios with AUTO-INFERENCE:

EVENT-BASED (use event_id):
✅ "I want to book tickets for nemo culpa eum"
   → event_id=9 → AUTO: ticket_booking (standard booking)

✅ "I want to book 50 tickets for the Jazz Concert"
   → event_id from SearchEvent → AUTO: group_booking (detected '50')

✅ "Can we have a private showing of the Opera?"
   → event_id → AUTO: special_request (detected 'private')

✅ "I need wheelchair access for 5 people at the Theater Show"
   → event_id → AUTO: special_request (detected 'wheelchair')

MERCHANT-BASED (use merchant_name):
✅ "I want to make a reservation at ABC Restaurant"
   → merchant_name='ABC Restaurant' → AUTO: custom_booking

✅ "Does XYZ Dining offer packages for 30 people?"
   → merchant_name='XYZ Dining' → AUTO: group_booking (detected '30')

The tool will:
1. Infer the correct enquiry_type automatically
2. Find merchant contact information (via event or merchant name)
3. Create an enquiry record with correct type
4. Send notification to the merchant
5. Provide the user with a reference number

Return format: Dictionary with status, message, and enquiry_id (if successful)"""
)
