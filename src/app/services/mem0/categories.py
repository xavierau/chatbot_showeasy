"""
Custom Categories and Instructions for ShowEasy Chatbot Memory

This module defines domain-specific memory categories and extraction instructions
for the ShowEasy.ai event platform chatbot. These configurations help Mem0
organize and categorize user memories effectively.

Design Principles:
- Categories are specific to the event/ticketing domain
- Instructions guide what information to extract and what to ignore
- Categories enable efficient memory retrieval for personalization

Note: Transactional data (booking history, membership info) is NOT stored in memory.
These are fetched in real-time from the database via tools (TicketInfo, MembershipInfo)
to ensure accuracy and freshness. Memory stores preferences and behavioral patterns only.
"""

from typing import List, Dict

# Custom categories for ShowEasy chatbot domain
SHOWEASY_CATEGORIES: List[Dict[str, str]] = [
    {
        "event_preferences": (
            "User's event preferences including favorite genres (concerts, theatre, dance, "
            "exhibitions), preferred venues, seating preferences, and event formats "
            "(live, virtual, hybrid)"
        )
    },
    {
        "booking_patterns": (
            "User's booking behavior patterns and preferences (NOT actual booking records). "
            "Examples: prefers early bird tickets, usually books in groups, likes front-row seats. "
            "Note: Actual booking history is fetched from DB via TicketInfo tool."
        )
    },
    {
        "membership_preferences": (
            "User's expressed interests and preferences related to membership (NOT actual membership data). "
            "Examples: interested in upgrading, wants more discounts, prefers premium benefits. "
            "Note: Actual membership tier/points are fetched from DB via MembershipInfo tool."
        )
    },
    {
        "personal_preferences": (
            "General preferences like preferred contact method, language, accessibility needs, "
            "dietary requirements for events with catering, and notification preferences"
        )
    },
    {
        "location_preferences": (
            "Preferred event locations, venues, areas in Hong Kong, willingness to travel, "
            "and transportation preferences"
        )
    },
    {
        "budget_preferences": (
            "Typical spending range, price sensitivity, interest in discounts/promotions, "
            "and preferred payment methods"
        )
    },
    {
        "companion_info": (
            "Information about who the user typically attends events with: family members, "
            "friends, colleagues, group sizes, and any special requirements for companions"
        )
    },
    {
        "feedback_history": (
            "User feedback on past events, satisfaction levels, complaints, "
            "and suggestions they've shared"
        )
    },
]

# Custom instructions for memory extraction
SHOWEASY_INSTRUCTIONS: str = """
You are extracting memories for a Hong Kong performing arts event platform chatbot.

IMPORTANT: This memory system stores PREFERENCES and PATTERNS only.
Transactional data (actual bookings, membership tiers, points, order history)
is fetched in real-time from the database via dedicated tools.

EXTRACT the following information:
- Event preferences (genres, artists, venues, seating)
- Booking behavior patterns (NOT actual booking records)
- Membership preferences and interests (NOT actual tier/points data)
- Personal preferences (accessibility, dietary, language)
- Location and travel preferences
- Budget and spending patterns
- Information about companions or groups
- Feedback and satisfaction indicators
- Contact preferences
- Special requests and requirements

DO NOT EXTRACT (fetched from DB instead):
- Actual booking records or order history
- Membership tier levels or point balances
- Transaction amounts or payment details
- Ticket numbers or confirmation codes

EXCLUDE the following:
- General greetings and pleasantries
- Filler words and casual conversation
- Temporary information (weather comments, time of day)
- Off-topic discussions unrelated to events
- System messages or error acknowledgments
- Sensitive personal information (full addresses, ID numbers, financial details)

PRIORITIZE:
- Long-term preferences over one-time requests
- Explicit statements over implied preferences
- Recent preferences over outdated ones
- Specific details over vague mentions

FORMAT:
- Extract concise, factual statements
- Preserve context when relevant
- Use clear, searchable language
"""

# Alternative category sets for different use cases
# Note: Minimal set focuses on preferences only; transactional data comes from DB
MINIMAL_CATEGORIES: List[Dict[str, str]] = [
    {"preferences": "User preferences for events, venues, and experiences"},
    {"patterns": "Behavioral patterns from past interactions (not actual records)"},
    {"profile": "Personal information and contact preferences"},
]

# Category set focused on personalization
PERSONALIZATION_CATEGORIES: List[Dict[str, str]] = [
    {
        "likes": (
            "Things the user enjoys: favorite genres, artists, venues, "
            "event types, and positive experiences"
        )
    },
    {
        "dislikes": (
            "Things the user avoids: genres they don't enjoy, venues they dislike, "
            "negative experiences, and explicit preferences to avoid"
        )
    },
    {
        "constraints": (
            "User limitations: budget constraints, accessibility needs, "
            "time restrictions, location limitations, and group requirements"
        )
    },
    {
        "goals": (
            "User objectives: upcoming events they're interested in, "
            "experiences they want to have, membership goals"
        )
    },
]


def get_categories_for_use_case(use_case: str = "default") -> List[Dict[str, str]]:
    """
    Get appropriate categories based on the use case.

    Args:
        use_case: One of 'default', 'minimal', 'personalization'

    Returns:
        List of category definitions
    """
    categories_map = {
        "default": SHOWEASY_CATEGORIES,
        "minimal": MINIMAL_CATEGORIES,
        "personalization": PERSONALIZATION_CATEGORIES,
    }
    return categories_map.get(use_case, SHOWEASY_CATEGORIES)