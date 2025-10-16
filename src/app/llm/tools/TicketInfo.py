"""
TicketInfo Tool - Provides information about tickets, purchases, and refunds.

This tool handles all ticket-related queries including:
- Ticket purchasing process
- Ticket pricing and availability
- Refund and cancellation policies
- Ticket delivery and access
"""
import dspy
from typing import Dict, Optional


def _get_ticket_info(topic: str = "general", event_context: Optional[str] = None) -> Dict[str, str]:
    """
    Retrieves ticket information based on topic.

    Args:
        topic: Type of ticket query - 'purchase', 'refund', 'delivery', 'pricing', 'general'
        event_context: Optional context about specific event

    Returns:
        Dictionary with ticket information
    """

    ticket_info = {
        "purchase": """How to Purchase Tickets:
        1. Browse events and select the event you want to attend
        2. Click 'Get Tickets' and choose your ticket type (General, VIP, etc.)
        3. Select quantity and add to cart
        4. Review your order and proceed to checkout
        5. Complete payment with credit card, debit card, or digital wallet
        6. Receive instant confirmation via email

        Premium members save 20% on all ticket purchases!""",

        "refund": """Ticket Refund Policy:
        - Full refund available up to 7 days before the event
        - 50% refund available 3-7 days before the event
        - No refunds within 72 hours of event start time
        - Premium members: Free cancellations up to 24 hours before event
        - Event cancellations by organizer: Full automatic refund

        To request a refund, visit 'My Tickets' in your account and select 'Request Refund'.""",

        "delivery": """Ticket Delivery & Access:
        - Digital tickets delivered instantly to your email
        - Access tickets via ShowEasy mobile app (recommended)
        - Print-at-home option available for all tickets
        - QR code entry at most venues
        - Add tickets to Apple Wallet or Google Pay

        No physical tickets are mailed. All tickets are digital for instant access.""",

        "pricing": """Ticket Pricing Information:
        - Prices vary by event, seating section, and timing
        - Early bird discounts often available
        - Premium members save 20% on all purchases
        - Group discounts available for 10+ tickets (contact support)
        - Dynamic pricing: Prices may increase as event approaches or tickets sell out

        Check individual event pages for specific pricing.""",

        "general": """Ticket Information:
        All tickets are digital and delivered instantly via email. You can access your tickets through
        our mobile app or print them at home. Refund policies vary by event and timing.
        Premium members enjoy 20% off all tickets and free cancellations up to 24 hours before events.

        For specific questions about purchasing, refunds, or delivery, I can provide more details!"""
    }

    info = ticket_info.get(topic, ticket_info["general"])

    if event_context:
        info = f"For {event_context}:\n\n{info}"

    return {"info": info}


# Create DSPy Tool for ticket information
TicketInfo = dspy.Tool(
    func=_get_ticket_info,
    name="ticket_info",
    desc="""Get information about ticket purchasing, refunds, delivery, and pricing policies.

Parameters:
- topic: Type of information needed - 'purchase', 'refund', 'delivery', 'pricing', or 'general'
- event_context: Optional event name/context for event-specific information

Use this tool when users ask about:
- How to buy tickets
- Refund or cancellation policies
- How tickets are delivered
- Ticket pricing
- General ticket questions"""
)
