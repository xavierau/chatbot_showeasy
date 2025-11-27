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
from typing import Dict, Optional
from contextlib import contextmanager
from config.database import DatabaseConnectionPool
from app.services.notification import NotificationService


@contextmanager
def get_db_connection():
    """
    Context manager for database connections.

    Ensures connections are properly closed after use,
    following the existing pattern from SearchEvent.py.

    Yields:
        MySQL connection object
    """
    pool = DatabaseConnectionPool()
    connection = pool.get_connection()
    try:
        yield connection
    finally:
        if connection.is_connected():
            connection.close()


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
        enquiry_type: Type of enquiry - one of:
            - 'custom_booking': Custom booking arrangements
            - 'group_booking': Large group or corporate bookings
            - 'special_request': Special accommodations or questions
            - 'restaurant_reservation': Restaurant meal package reservations
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
    # Validate parameters: must have either event_id OR merchant_name (not both, not neither)
    if not event_id and not merchant_name:
        return {
            "status": "error",
            "message": "Please provide either an event ID or merchant name for your enquiry."
        }

    if event_id and merchant_name:
        return {
            "status": "error",
            "message": "Please provide either event_id OR merchant_name, not both."
        }

    try:
        with get_db_connection() as connection:
            cursor = connection.cursor(dictionary=True)

            # Step 1: Get merchant/organizer info
            if event_id:
                # Mode 1: Event-based enquiry (existing behavior)
                cursor.execute("""
                    SELECT
                        e.organizer_id,
                        o.contact_email as merchant_email,
                        o.contact_phone as merchant_phone,
                        JSON_UNQUOTE(JSON_EXTRACT(e.name, '$.en')) as event_name,
                        JSON_UNQUOTE(JSON_EXTRACT(o.name, '$.en')) as merchant_name
                    FROM events e
                    INNER JOIN organizers o ON e.organizer_id = o.id
                    WHERE e.id = %s AND e.event_status = 'published'
                """, (event_id,))
            else:
                # Mode 2: Merchant-based enquiry (new behavior for restaurants)
                cursor.execute("""
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
                """, (f"%{merchant_name}%", f"%{merchant_name}%"))

            merchant_data = cursor.fetchone()

            if not merchant_data:
                if event_id:
                    return {
                        "status": "error",
                        "message": "Event not found or not available for booking enquiries. Please check the event ID and try again."
                    }
                else:
                    return {
                        "status": "error",
                        "message": f"Merchant '{merchant_name}' not found. Please check the spelling or contact support at info@showeasy.ai"
                    }

            if not merchant_data.get('merchant_email'):
                return {
                    "status": "error",
                    "message": "Merchant contact information not available. Please contact support at info@showeasy.ai"
                }

            # Step 2: Create enquiry record
            cursor.execute("""
                INSERT INTO booking_enquiries
                (event_id, organizer_id, session_id, enquiry_type, user_message, contact_email,
                 contact_phone, merchant_email, merchant_phone, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending')
            """, (
                event_id,  # NULL for merchant-based enquiries
                merchant_data['organizer_id'],
                session_id,  # Optional - may be NULL if not provided
                enquiry_type,
                user_message,
                contact_email,
                contact_phone,
                merchant_data['merchant_email'],
                merchant_data['merchant_phone']
            ))

            connection.commit()
            enquiry_id = cursor.lastrowid

            # Step 3: Send notification to merchant
            notification_service = NotificationService()
            display_name = merchant_data['event_name'] if event_id else merchant_data['merchant_name']

            send_result = notification_service.send_enquiry_to_merchant(
                enquiry_id=enquiry_id,
                event_name=display_name,
                user_message=user_message,
                user_email=contact_email,
                user_phone=contact_phone,
                merchant_email=merchant_data['merchant_email'],
                merchant_phone=merchant_data.get('merchant_phone')
            )

            if send_result['success']:
                # Step 4: Update status to 'sent'
                cursor.execute("""
                    UPDATE booking_enquiries SET status = 'sent' WHERE id = %s
                """, (enquiry_id,))
                connection.commit()

                merchant_name_display = merchant_data.get('merchant_name', 'the merchant')
                return {
                    "status": "success",
                    "message": f"Your enquiry has been sent to {merchant_name_display}. Reference: #{enquiry_id}. They will respond within 24-48 hours via email.",
                    "enquiry_id": str(enquiry_id)
                }
            else:
                return {
                    "status": "error",
                    "message": "Failed to send enquiry. Please try again or contact support at info@showeasy.ai"
                }

    except Exception as e:
        # Log the error for debugging (in production, use proper logging)
        print(f"[BookingEnquiry] Error creating booking enquiry: {e}")

        return {
            "status": "error",
            "message": "An error occurred while processing your enquiry. Please contact support at info@showeasy.ai"
        }


# Create DSPy Tool
BookingEnquiry = dspy.Tool(
    func=_create_booking_enquiry,
    name="booking_enquiry",
    desc="""Send a booking enquiry to event organizers/merchants.

This tool supports TWO modes:
1. EVENT-BASED ENQUIRY: For specific events (concerts, shows, performances)
2. MERCHANT-BASED ENQUIRY: For restaurants, meal packages, or general merchant enquiries

Use this tool when users want to:
- Request custom booking arrangements or special packages
- Book large groups, corporate events, or school trips (usually 20+ people)
- Make restaurant reservations or enquire about meal packages
- Ask organizers specific questions before purchasing tickets
- Request customizations, special accommodations, or accessibility support
- Inquire about group discounts or corporate rates
- Ask about private bookings or exclusive access
- Contact a restaurant/merchant directly without a specific event

DO NOT use this tool for:
- General questions about tickets (use TicketInfo instead)
- Standard ticket purchases (users should buy through the platform)
- Questions about membership (use MembershipInfo instead)

Required Parameters (ALWAYS):
- user_message: User's detailed enquiry message
- contact_email: User's email address for merchant to reply

Mode Selection (MUST provide ONE):
- event_id: For event-based enquiries (e.g., concerts, shows)
- merchant_name: For merchant-based enquiries (e.g., restaurants, direct contact)

Optional Parameters:
- contact_phone: User's phone number
- enquiry_type: One of 'custom_booking', 'group_booking', 'special_request', 'restaurant_reservation' (default: 'custom_booking')

Example Scenarios:

EVENT-BASED (use event_id):
- "I want to book 50 tickets for the Jazz Concert" → use event_id from SearchEvent, enquiry_type='group_booking'
- "Can we have a private showing of the Opera?" → use event_id, enquiry_type='special_request'
- "I need wheelchair access for 5 people at the Theater Show" → use event_id, enquiry_type='special_request'

MERCHANT-BASED (use merchant_name):
- "I want to make a reservation at ABC Restaurant" → use merchant_name='ABC Restaurant', enquiry_type='restaurant_reservation'
- "Does XYZ Dining offer meal packages for 20 people?" → use merchant_name='XYZ Dining', enquiry_type='group_booking'
- "I want to contact The Fine Bistro about their special menu" → use merchant_name='The Fine Bistro', enquiry_type='custom_booking'

The tool will:
1. Find the merchant's contact information (via event or merchant name)
2. Create an enquiry record (event_id will be NULL for merchant-based enquiries)
3. Send notification to the merchant
4. Provide the user with a reference number

Return format: Dictionary with status, message, and enquiry_id (if successful)"""
)
