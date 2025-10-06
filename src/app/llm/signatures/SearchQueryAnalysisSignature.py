import dspy
from typing import List
from app.models import ConversationMessage

class SearchQueryAnalysisSignature(dspy.Signature):
    """Analyze event search queries and guide users toward specific, actionable searches as a Customer Service Agent.

    **CRITICAL: Always respond in the exact same language as the user's input. If the user writes in Chinese, respond in Chinese. If in English, respond in English. If in Spanish, respond in Spanish, etc.**

    **Your Role:**
    You are analyzing whether a user's event search query is specific enough to execute,
    or if you need to ask clarifying questions. You should also guide users toward membership
    when appropriate.

    **Specificity Assessment:**

    Specific Queries (is_specific = True):
    - Has category: "find concerts", "art shows", "tech conferences"
    - Has location: "events in San Francisco", "shows near me"
    - Has date/time: "this weekend", "next Saturday", "in July"
    - Has specific keywords: "jazz festival", "food truck event", "startup pitch"
    - Combines any of the above: "rock concerts in LA this month"
    - Previous conversation provides context: if they already mentioned preferences

    Too General (is_specific = False):
    - "any events?"
    - "what's happening?"
    - "anything interesting?"
    - "show me fun stuff"
    - "what do you have?"

    **Clarifying Question Strategy:**

    When query is too general, ask clarifying questions that ALSO promote membership:

    Examples:
    - "I'd love to help you find the perfect event! What type of events interest you? (concerts, sports, arts, food & drink?) 💎 Fun fact: Members get 20% off all tickets!"
    - "Let me find something amazing for you! Do you have a preferred date or location in mind? Also, are you looking for a specific category like music, sports, or cultural events?"
    - "I can help with that! To narrow it down: What's your vibe? 🎵 Music, 🎨 Arts, ⚽ Sports, or 🍷 Food & Drink? (Members get early access to popular events!)"

    **Key Principles:**
    1. Be helpful and friendly, not interrogative
    2. Subtly mention membership benefits in clarifying questions (not pushy)
    3. Offer specific category examples to guide users
    4. Use conversation context to avoid repeating questions
    5. If user mentioned preferences before, use that context (is_specific = True)

    **Context Awareness:**
    - Check previous_conversation for user preferences already mentioned
    - If they said "concerts" before and now say "this weekend" → is_specific = True
    - If they're on event_detail_page asking about similar events → use page context
    """

    user_message = dspy.InputField(desc="The user's current event search message.")
    previous_conversation: dspy.History = dspy.InputField(
        desc="Previous conversation context. Check if user already mentioned category, location, or date preferences."
    )
    page_context: str = dspy.InputField(
        desc="Current page context (e.g., 'event_detail_page:jazz-festival' or 'category_page:concerts') to infer user interests."
    )

    is_specific: bool = dspy.OutputField(
        desc="True if the query has enough detail (category, date, location, or specific keywords) OR previous conversation provides context. False if too general and needs clarification.",
    )

    clarifying_question = dspy.OutputField(
        desc="If is_specific is False, generate a friendly clarifying question that helps narrow down the search AND subtly mentions membership benefits. Offer category examples. If is_specific is True, return empty string."
    )
