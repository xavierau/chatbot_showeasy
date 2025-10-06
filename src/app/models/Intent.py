import enum


class Intent(str, enum.Enum):
    """User intent categories for Event Platform Customer Service Agent.

    Event Discovery & Search:
    - SEARCH_EVENT: User wants to find/discover events
    - ITINERARY_PLANNING: User wants help planning multi-event itinerary

    Membership & Benefits:
    - MEMBERSHIP_INQUIRY: Questions about membership benefits/features
    - MEMBERSHIP_UPGRADE: User wants to upgrade/purchase membership
    - DISCOUNT_INQUIRY: Questions about discounts/promotions

    Ticket Management:
    - TICKET_INQUIRY: General questions about tickets
    - TICKET_PURCHASE_HELP: Assistance with buying tickets
    - TICKET_REFUND: Refund or cancellation requests

    General Support:
    - GREETING: User greets the agent
    - GOODBYE: User ends conversation
    - GENERAL_QUESTION: General platform questions
    - HELP_REQUEST: User needs help/support
    - FEATURE_REQUEST: User suggests new features
    - BUG_REPORT: User reports issues/bugs
    """

    # Event Discovery
    SEARCH_EVENT = "Search Event"
    ITINERARY_PLANNING = "Itinerary Planning"

    # Membership
    MEMBERSHIP_INQUIRY = "Membership Inquiry"
    MEMBERSHIP_UPGRADE = "Membership Upgrade"
    DISCOUNT_INQUIRY = "Discount Inquiry"

    # Tickets
    TICKET_INQUIRY = "Ticket Inquiry"
    TICKET_PURCHASE_HELP = "Ticket Purchase Help"
    TICKET_REFUND = "Ticket Refund"

    # General
    GREETING = "Greeting"
    GOODBYE = "Goodbye"
    GENERAL_QUESTION = "General Question"
    HELP_REQUEST = "Help Request"
    FEATURE_REQUEST = "Feature Request"
    BUG_REPORT = "Bug Report"
