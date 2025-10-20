"""
MembershipInfo Tool - Provides information about membership benefits and features.

This tool handles all membership-related queries including:
- Membership benefits and features
- Pricing and plans
- Upgrade options
- Discounts and savings
"""
import dspy
import os
from typing import Dict


def _get_membership_info(query_type: str = "general") -> Dict[str, str]:
    """
    Retrieves membership information based on query type.

    Args:
        query_type: Type of membership query - 'general', 'benefits', 'pricing', 'upgrade'

    Returns:
        Dictionary with membership information
    """
    event_platform_base_url = os.getenv("EVENT_PLATFORM_BASE_URL", "https://showeasy.ai")

    # This would typically query a database or CMS
    # For now, returning structured information

    membership_data = {
        "general": """ShowEasy Premium Membership provides exclusive benefits for event enthusiasts.
        Members enjoy 20% off all ticket purchases, early access to ticket sales, exclusive member-only events,
        priority customer support, and free ticket cancellations up to 24 hours before events.""",

        "benefits": """Premium Membership Benefits:
        - 20% discount on all ticket purchases
        - Early access to tickets (48 hours before general sale)
        - Exclusive access to member-only events
        - Priority customer support (24/7 dedicated line)
        - Free ticket cancellations (up to 24 hours before event)
        - Monthly event recommendations tailored to your interests
        - Special member pricing on VIP upgrades""",

        "pricing": """Membership Plans:
        - Monthly Plan: $9.99/month (cancel anytime)
        - Annual Plan: $99/year (save $20, 2 months free)
        - Premium Plus: $199/year (includes all benefits + guaranteed tickets for sold-out events)

        The membership pays for itself after purchasing just 3-4 tickets!""",

        "upgrade": f"""Upgrade to Premium Membership today!
        Visit your account settings or go to {event_platform_base_url}/membership to upgrade.
        Current members can upgrade to Premium Plus at any time and receive prorated credits.
        New members get their first month at 50% off!"""
    }

    return {"info": membership_data.get(query_type, membership_data["general"])}


# Create DSPy Tool for membership information
MembershipInfo = dspy.Tool(
    func=_get_membership_info,
    name="membership_info",
    desc="""Get information about ShowEasy Premium Membership benefits, pricing, and upgrade options.

Parameters:
- query_type: Type of information needed - 'general', 'benefits', 'pricing', or 'upgrade'

Use this tool when users ask about:
- Membership benefits or features
- How much membership costs
- How to upgrade to premium
- Discounts available to members
- What they get with membership"""
)
