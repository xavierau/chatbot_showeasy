"""
TicketInfo Tool - Provides information about tickets, purchases, and refunds.

This tool handles all ticket-related queries including:
- Ticket purchasing process
- Ticket pricing and availability
- Refund and cancellation policies
- Ticket delivery and access
- Member ticket discounts

Source: docs/context/zh-TW/
- 01_platform_overview.md (ticket management section)
- 02_membership_program.md (member discounts)
- 04_customer_service.md (refund policies)
- 05_contact_information.md (support contact)
"""
import dspy
from pathlib import Path
from typing import Dict, Optional
from functools import lru_cache


@lru_cache(maxsize=1)
def _load_ticket_context() -> str:
    """
    Load ticket-related content from the context files.
    Combines platform overview, membership, and customer service information.
    Uses lru_cache to avoid repeated file reads.

    Returns:
        The combined content of the ticket-related context files.
    """
    context_dir = Path(__file__).parent.parent.parent.parent.parent / "docs" / "context" / "zh-TW"

    context_files = [
        "01_platform_overview.md",
        "02_membership_program.md",
        "04_customer_service.md",
        "05_contact_information.md",
    ]

    combined_content = []
    for filename in context_files:
        file_path = context_dir / filename
        if file_path.exists():
            combined_content.append(file_path.read_text(encoding="utf-8"))
        else:
            combined_content.append(f"[Warning: {filename} not found]")

    return "\n\n---\n\n".join(combined_content)


def _get_ticket_info(topic: str = "general", event_context: Optional[str] = None) -> Dict[str, str]:
    """
    Retrieves ticket information from the official context files.

    Args:
        topic: Type of ticket query - 'purchase', 'refund', 'delivery', 'pricing', 'general'
              (Note: topic is kept for backward compatibility but the full
              context is always returned for the LLM to process)
        event_context: Optional context about specific event

    Returns:
        Dictionary with ticket information from docs/context/zh-TW/
    """
    try:
        ticket_content = _load_ticket_context()

        if event_context:
            ticket_content = f"User is asking about: {event_context}\n\n{ticket_content}"

        return {"info": ticket_content}
    except Exception as e:
        return {"info": f"Error loading ticket information: {e}"}


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
