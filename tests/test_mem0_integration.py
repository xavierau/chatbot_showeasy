"""
Tests for Mem0 Long-Term Memory Integration.

This module tests the integration of Mem0 as a long-term memory and
personalization engine into the ConversationOrchestrator.

Test Categories:
- Mem0Service unit tests
- ConversationOrchestrator integration tests with Mem0
- Graceful degradation when Mem0 unavailable
"""

import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

import pytest
from unittest.mock import Mock, MagicMock, patch
from dataclasses import dataclass
from typing import Optional, Dict, Any

# Import the modules under test
from app.services.mem0.service import Mem0Service, MemoryResult
from app.llm.modules.ConversationOrchestrator import ConversationOrchestrator
from app.models import ConversationMessage, ABTestConfig


class TestMemoryResult:
    """Test suite for MemoryResult dataclass."""

    def test_success_result(self):
        """Test creating a successful MemoryResult."""
        result = MemoryResult(
            success=True,
            data={"results": [{"memory": "User likes jazz"}]},
            message="Retrieved 1 memories"
        )
        assert result.success is True
        assert result.data is not None
        assert result.error is None

    def test_failure_result(self):
        """Test creating a failed MemoryResult."""
        result = MemoryResult(
            success=False,
            error="Connection timeout",
            message="Failed to retrieve memories"
        )
        assert result.success is False
        assert result.error == "Connection timeout"

    def test_to_dict(self):
        """Test converting MemoryResult to dictionary."""
        result = MemoryResult(
            success=True,
            data={"test": "data"},
            message="Test message"
        )
        result_dict = result.to_dict()
        assert result_dict["success"] is True
        assert result_dict["data"] == {"test": "data"}
        assert result_dict["message"] == "Test message"
        assert result_dict["error"] is None


class TestMem0Service:
    """Test suite for Mem0Service."""

    @pytest.fixture
    def mock_memory_client(self):
        """Create a mock Memory client."""
        return MagicMock()

    @pytest.fixture
    def mem0_service(self, mock_memory_client):
        """Create Mem0Service with mocked Memory client."""
        return Mem0Service(memory=mock_memory_client)

    def test_add_conversation(self, mem0_service, mock_memory_client):
        """Test adding a conversation turn to memory."""
        mock_memory_client.add.return_value = {
            "results": [{"id": "mem_123", "memory": "User prefers jazz concerts"}]
        }

        result = mem0_service.add_conversation(
            user_message="I love jazz concerts",
            assistant_message="Great! I'll remember that.",
            user_id="user123",
            session_id="session456"
        )

        assert result.success is True
        mock_memory_client.add.assert_called_once()

    def test_search_memories(self, mem0_service, mock_memory_client):
        """Test searching for memories."""
        mock_memory_client.search.return_value = {
            "results": [
                {"memory": "User prefers jazz concerts", "score": 0.95},
                {"memory": "Usually books 2 tickets", "score": 0.88}
            ]
        }

        result = mem0_service.search(
            query="music preferences",
            user_id="user123",
            limit=5
        )

        assert result.success is True
        assert len(result.data["results"]) == 2
        mock_memory_client.search.assert_called_once()

    def test_get_user_context_with_query(self, mem0_service, mock_memory_client):
        """Test retrieving user context with semantic search."""
        mock_memory_client.search.return_value = {
            "results": [
                {"memory": "User prefers jazz concerts"},
                {"memory": "Usually attends with spouse"}
            ]
        }

        context = mem0_service.get_user_context(
            user_id="user123",
            query="What kind of events do they like?",
            limit=5
        )

        assert "User Context:" in context
        assert "jazz concerts" in context
        assert "spouse" in context

    def test_get_user_context_empty(self, mem0_service, mock_memory_client):
        """Test retrieving user context when no memories exist."""
        mock_memory_client.search.return_value = {"results": []}

        context = mem0_service.get_user_context(
            user_id="new_user",
            query="preferences"
        )

        assert context == ""

    def test_add_memory_error_handling(self, mem0_service, mock_memory_client):
        """Test error handling when adding memory fails."""
        mock_memory_client.add.side_effect = Exception("API Error")

        result = mem0_service.add(
            messages="Test message",
            user_id="user123"
        )

        assert result.success is False
        assert "API Error" in result.error

    def test_search_error_handling(self, mem0_service, mock_memory_client):
        """Test error handling when search fails."""
        mock_memory_client.search.side_effect = Exception("Search failed")

        result = mem0_service.search(
            query="test",
            user_id="user123"
        )

        assert result.success is False
        assert "Search failed" in result.error


class TestConversationOrchestratorWithMem0:
    """Test suite for ConversationOrchestrator with Mem0 integration."""

    @pytest.fixture
    def mock_mem0_service(self):
        """Create a mock Mem0Service."""
        mock = MagicMock(spec=Mem0Service)
        mock.get_user_context.return_value = (
            "User Context:\n"
            "- Prefers jazz concerts\n"
            "- Usually books 2 tickets"
        )
        return mock

    def test_orchestrator_initializes_with_mem0(self, mock_mem0_service):
        """Test that orchestrator can be initialized with Mem0 service."""
        orchestrator = ConversationOrchestrator(
            mem0_service=mock_mem0_service
        )
        assert orchestrator.mem0_service is mock_mem0_service

    def test_orchestrator_initializes_without_mem0(self):
        """Test that orchestrator works without Mem0 service."""
        orchestrator = ConversationOrchestrator(mem0_service=None)
        assert orchestrator.mem0_service is None

    def test_get_user_context_with_mem0(self, mock_mem0_service):
        """Test that _get_user_context retrieves from Mem0."""
        orchestrator = ConversationOrchestrator(
            mem0_service=mock_mem0_service
        )

        context = orchestrator._get_user_context(
            user_id="user123",
            user_message="Find me jazz concerts"
        )

        assert "jazz concerts" in context
        mock_mem0_service.get_user_context.assert_called_once_with(
            user_id="user123",
            query="Find me jazz concerts",
            limit=5
        )

    def test_get_user_context_without_mem0(self):
        """Test that _get_user_context returns empty without Mem0."""
        orchestrator = ConversationOrchestrator(mem0_service=None)

        context = orchestrator._get_user_context(
            user_id="user123",
            user_message="Find me concerts"
        )

        assert context == ""

    def test_get_user_context_without_user_id(self, mock_mem0_service):
        """Test that _get_user_context returns empty without user_id."""
        orchestrator = ConversationOrchestrator(
            mem0_service=mock_mem0_service
        )

        context = orchestrator._get_user_context(
            user_id=None,
            user_message="Find me concerts"
        )

        assert context == ""
        mock_mem0_service.get_user_context.assert_not_called()

    def test_get_user_context_handles_mem0_error(self, mock_mem0_service):
        """Test graceful degradation when Mem0 throws error."""
        mock_mem0_service.get_user_context.side_effect = Exception("Connection failed")
        orchestrator = ConversationOrchestrator(
            mem0_service=mock_mem0_service
        )

        context = orchestrator._get_user_context(
            user_id="user123",
            user_message="Find me concerts"
        )

        # Should return empty string, not raise exception
        assert context == ""


class TestMem0ServiceCategories:
    """Test suite for ShowEasy-specific memory categories."""

    def test_showeasy_categories_loaded(self):
        """Test that ShowEasy categories are loaded."""
        from app.services.mem0.categories import SHOWEASY_CATEGORIES
        assert len(SHOWEASY_CATEGORIES) > 0
        # Check key categories exist
        category_names = [list(cat.keys())[0] for cat in SHOWEASY_CATEGORIES]
        assert "event_preferences" in category_names
        assert "booking_patterns" in category_names
        assert "membership_preferences" in category_names

    def test_showeasy_instructions_loaded(self):
        """Test that ShowEasy instructions are loaded."""
        from app.services.mem0.categories import SHOWEASY_INSTRUCTIONS
        assert len(SHOWEASY_INSTRUCTIONS) > 0
        # Check key instructions
        assert "event preferences" in SHOWEASY_INSTRUCTIONS.lower()
        assert "do not extract" in SHOWEASY_INSTRUCTIONS.lower()

    def test_get_categories_for_use_case(self):
        """Test getting categories for different use cases."""
        from app.services.mem0.categories import get_categories_for_use_case

        default = get_categories_for_use_case("default")
        minimal = get_categories_for_use_case("minimal")
        personalization = get_categories_for_use_case("personalization")

        assert len(default) > len(minimal)
        assert len(personalization) > len(minimal)


class TestAPIEndpointMem0Integration:
    """Test suite for API endpoint integration with Mem0."""

    @pytest.fixture
    def mock_mem0_service(self):
        """Create a mock Mem0Service for API tests."""
        mock = MagicMock(spec=Mem0Service)
        mock.get_user_context.return_value = ""
        mock.add_conversation.return_value = MemoryResult(
            success=True,
            data={"results": []},
            message="Memory added"
        )
        return mock

    def test_get_mem0_service_disabled(self):
        """Test that get_mem0_service returns None when disabled."""
        with patch.dict('os.environ', {'MEM0_ENABLED': 'false'}):
            from app.api.main import get_mem0_service
            # Reset the cached service
            import app.api.main as api_main
            api_main._mem0_service = None

            result = get_mem0_service()
            assert result is None

    def test_mem0_service_initialization_failure_graceful(self):
        """Test graceful handling when Mem0 fails to initialize."""
        with patch('app.services.mem0.Mem0Service', side_effect=Exception("Init failed")):
            with patch.dict('os.environ', {'MEM0_ENABLED': 'true'}):
                from app.api.main import get_mem0_service
                import app.api.main as api_main
                api_main._mem0_service = None

                # Should not raise, should return None
                result = get_mem0_service()
                assert result is None


class TestConversationSignatureWithUserContext:
    """Test suite for ConversationSignature with user_context field."""

    def test_signature_has_user_context_field(self):
        """Test that ConversationSignature includes user_context."""
        from app.llm.signatures import ConversationSignature

        # DSPy signatures define fields as class-level attributes via model_fields
        # Check that user_context is in the signature's fields
        assert 'user_context' in ConversationSignature.model_fields

    def test_signature_user_context_has_default(self):
        """Test that user_context has a default empty string."""
        from app.llm.signatures import ConversationSignature

        # Check that user_context field exists and has the correct configuration
        user_context_field = ConversationSignature.model_fields.get('user_context')
        assert user_context_field is not None
        # The field should have a default value of empty string
        assert user_context_field.default == ""


# Integration test that requires actual LLM (marked for manual/CI run)
@pytest.mark.skip(reason="Requires LLM configuration - run manually")
class TestMem0IntegrationE2E:
    """End-to-end tests for Mem0 integration (requires configured LLM)."""

    def test_full_conversation_with_memory(self):
        """Test a full conversation flow with memory persistence."""
        from config import configure_llm
        configure_llm()

        # This would require actual Mem0 setup
        # Left as a template for E2E testing
        pass
