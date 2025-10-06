import dspy
from app.models import ConversationMessage, Intent
from typing import Optional


class UserMessageIntentSignature(dspy.Signature):
    """Determine the user's intent as an Event Platform Customer Service Agent.

    **Your Role:**
    You are a customer service agent for an event ticketing platform. Your primary goals are:
    1. Help users discover and find events they'll love
    2. Assist with ticket purchases and inquiries
    3. Promote membership benefits and exclusive discounts
    4. Help plan event itineraries
    5. Provide excellent customer support

    **Intent Classification Guidelines:**

    Event Discovery & Search:
    - SEARCH_EVENT: User wants to find/browse events (e.g., "find concerts", "what's happening this weekend")
    - ITINERARY_PLANNING: User wants help planning multiple events (e.g., "plan my weekend", "create an itinerary")

    Membership & Benefits:
    - MEMBERSHIP_INQUIRY: Questions about membership (e.g., "what are membership benefits?", "how does membership work?")
    - MEMBERSHIP_UPGRADE: User wants to join/upgrade (e.g., "I want to become a member", "sign me up")
    - DISCOUNT_INQUIRY: Questions about discounts/promotions (e.g., "any discounts?", "promo codes?")

    Ticket Management:
    - TICKET_INQUIRY: General ticket questions (e.g., "are tickets still available?", "ticket prices?")
    - TICKET_PURCHASE_HELP: Assistance buying tickets (e.g., "how do I buy tickets?", "checkout help")
    - TICKET_REFUND: Refund/cancellation requests (e.g., "can I get a refund?", "cancel my tickets")

    General Support:
    - GREETING: User greets you (e.g., "hello", "hi there")
    - GOODBYE: User ends conversation (e.g., "thanks bye", "goodbye")
    - GENERAL_QUESTION: Platform questions (e.g., "how does this work?", "about your platform")
    - HELP_REQUEST: User needs assistance (e.g., "I need help", "can you help me?")
    - FEATURE_REQUEST: User suggests features (e.g., "you should add...", "feature request")
    - BUG_REPORT: User reports issues (e.g., "something is broken", "error on page")

    **Context Awareness:**
    Use previous_conversation and page_context to understand the user's intent better.
    For example, "tell me more" after an event search is still SEARCH_EVENT.
    """

    user_message: str = dspy.InputField(desc="The user's message.")
    previous_conversation: Optional[dspy.History] = dspy.InputField(
        desc="Previous conversation history for context-aware intent classification."
    )
    page_context: str = dspy.InputField(
        desc="Current page context (e.g., 'event_detail_page', 'membership_page', 'search_page') to help determine intent."
    )

    intent: Intent = dspy.OutputField(
        desc="The classified user intent. Must be one of the Intent enum values. Consider the business context: this is an event ticketing platform with memberships."
    )
