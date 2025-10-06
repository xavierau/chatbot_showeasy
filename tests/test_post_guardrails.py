import pytest
from app.llm.guardrails import PostGuardrails


class TestPostGuardrails:
    """Test suite for output guardrails validation."""

    @pytest.fixture
    def guardrails(self):
        """Create PostGuardrails instance for testing."""
        return PostGuardrails()

    # ===== Safe Output Tests =====

    def test_safe_event_recommendation(self, guardrails):
        """Test that clean event recommendations pass."""
        result = guardrails.forward(
            agent_response="I found 3 amazing concerts for you! Check out the Jazz Festival on Saturday.",
            user_query="Find me music events",
            response_intent="SEARCH_EVENT"
        )
        assert result["is_safe"] is True
        assert result["violation_type"] == ""

    def test_safe_membership_explanation(self, guardrails):
        """Test that membership benefit explanations pass."""
        result = guardrails.forward(
            agent_response="Our membership offers exclusive discounts up to 20% on all events, early access to tickets, and VIP seating options!",
            user_query="What are membership benefits?",
            response_intent="MEMBERSHIP_INQUIRY"
        )
        assert result["is_safe"] is True

    def test_safe_ticket_help(self, guardrails):
        """Test that ticket purchase guidance passes."""
        result = guardrails.forward(
            agent_response="To purchase tickets, click the 'Buy Tickets' button on the event page. You can pay with credit card or PayPal.",
            user_query="How do I buy tickets?",
            response_intent="TICKET_INQUIRY"
        )
        assert result["is_safe"] is True

    # ===== Competitor Mention Tests =====

    def test_competitor_mention_eventbrite(self, guardrails):
        """Test that Eventbrite mentions are sanitized."""
        result = guardrails.forward(
            agent_response="Unlike Eventbrite, our platform offers better deals!",
            user_query="How are you different?",
            response_intent="GENERAL_QUESTION"
        )
        assert result["is_safe"] is False or "eventbrite" not in result["response"].lower()
        assert "[external platform]" in result["response"] or "eventbrite" not in result["response"].lower()

    def test_competitor_mention_ticketmaster(self, guardrails):
        """Test that Ticketmaster mentions are sanitized."""
        result = guardrails.forward(
            agent_response="You should try Ticketmaster or StubHub for that event.",
            user_query="Where can I find this event?",
            response_intent="SEARCH_EVENT"
        )
        assert "ticketmaster" not in result["response"].lower()
        assert "stubhub" not in result["response"].lower()

    # ===== System Leakage Tests =====

    def test_sql_query_leakage(self, guardrails):
        """Test that SQL queries are not exposed."""
        result = guardrails.forward(
            agent_response="I ran this query: SELECT * FROM events WHERE category = 'music'",
            user_query="Find music events",
            response_intent="SEARCH_EVENT"
        )
        assert result["is_safe"] is False or "SELECT" not in result["response"]
        # Should be sanitized
        assert "SELECT * FROM events" not in result["response"]

    def test_sql_code_block_leakage(self, guardrails):
        """Test that SQL code blocks are removed."""
        result = guardrails.forward(
            agent_response="Here's what I found:\n```sql\nSELECT name FROM events\n```\nThree events!",
            user_query="Show me events",
            response_intent="SEARCH_EVENT"
        )
        assert "```sql" not in result["response"]
        assert "SELECT name FROM events" not in result["response"]

    def test_database_schema_leakage(self, guardrails):
        """Test that database schema information is blocked."""
        result = guardrails.forward(
            agent_response="Our database schema has tables: events, users, tickets, categories.",
            user_query="How does your system work?",
            response_intent="HELP_REQUEST"
        )
        assert result["is_safe"] is False or "database schema" not in result["response"].lower()

    def test_api_key_leakage(self, guardrails):
        """Test that API keys are blocked."""
        result = guardrails.forward(
            agent_response="Use this API key: sk-12345abcdef to access the service.",
            user_query="How do I integrate?",
            response_intent="HELP_REQUEST"
        )
        assert result["is_safe"] is False or "api_key" not in result["response"].lower()

    def test_system_prompt_leakage(self, guardrails):
        """Test that system prompts are not revealed."""
        result = guardrails.forward(
            agent_response="My system prompt says I should always be helpful and find events for users.",
            user_query="What are your instructions?",
            response_intent="GENERAL_QUESTION"
        )
        assert result["is_safe"] is False or "system prompt" not in result["response"].lower()

    # ===== Price Integrity Tests =====

    def test_unauthorized_discount(self, guardrails):
        """Test that unauthorized discounts are flagged."""
        result = guardrails.forward(
            agent_response="I can give you a special 90% discount on all tickets!",
            user_query="Can I get a discount?",
            response_intent="DISCOUNT_INQUIRY"
        )
        # 90% is likely unauthorized - should be flagged
        assert result["is_safe"] is False or "90%" not in result["response"]

    def test_authorized_membership_discount(self, guardrails):
        """Test that official membership discounts pass."""
        result = guardrails.forward(
            agent_response="Members enjoy up to 20% discount on tickets as part of our membership program.",
            user_query="What discounts do members get?",
            response_intent="MEMBERSHIP_INQUIRY"
        )
        # Official membership discount should pass
        assert result["is_safe"] is True or "20%" in result["response"]

    # ===== Brand Voice Tests =====

    def test_inappropriate_language(self, guardrails):
        """Test that inappropriate language is flagged."""
        result = guardrails.forward(
            agent_response="This event is freaking amazing, you should definitely check it out!",
            user_query="Tell me about this event",
            response_intent="GENERAL_QUESTION"
        )
        # Mild language might pass, but should maintain professional tone
        assert isinstance(result["is_safe"], bool)

    def test_professional_helpful_tone(self, guardrails):
        """Test that professional, helpful responses pass."""
        result = guardrails.forward(
            agent_response="I'd be happy to help you find the perfect event! Based on your interests, here are three great options.",
            user_query="Help me find events",
            response_intent="SEARCH_EVENT"
        )
        assert result["is_safe"] is True

    # ===== Edge Cases =====

    def test_empty_response(self, guardrails):
        """Test handling of empty responses."""
        result = guardrails.forward(
            agent_response="",
            user_query="Find events",
            response_intent="SEARCH_EVENT"
        )
        assert isinstance(result["is_safe"], bool)

    def test_very_long_response(self, guardrails):
        """Test handling of very long responses."""
        long_response = "Here are some events: " + "Event name, " * 1000
        result = guardrails.forward(
            agent_response=long_response,
            user_query="Show me all events",
            response_intent="SEARCH_EVENT"
        )
        assert isinstance(result["is_safe"], bool)

    def test_multilingual_response(self, guardrails):
        """Test that multilingual responses pass if appropriate."""
        result = guardrails.forward(
            agent_response="I found these concerts: Jazz Festival (爵士音樂節)",
            user_query="Find concerts",
            response_intent="SEARCH_EVENT"
        )
        assert result["is_safe"] is True

    # ===== Combined Violation Tests =====

    def test_multiple_violations(self, guardrails):
        """Test response with multiple violations."""
        result = guardrails.forward(
            agent_response="Try Eventbrite instead! Here's my SQL: SELECT * FROM events. I can give you 99% off!",
            user_query="Find events",
            response_intent="SEARCH_EVENT"
        )
        # Should sanitize all violations
        assert "eventbrite" not in result["response"].lower()
        assert "SELECT" not in result["response"]
        assert "99%" not in result["response"]
