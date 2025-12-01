"""
Tests for DocumentSummary and DocumentDetail tools.
"""
import pytest
from app.llm.tools.DocumentSummary import _get_document_summary, DocumentSummary
from app.llm.tools.DocumentDetail import _get_document_detail, DocumentDetail


class TestDocumentSummary:
    """Test DocumentSummary tool."""

    def test_returns_summaries(self):
        """Should return summaries from all documents."""
        result = _get_document_summary()

        assert "summaries" in result
        assert isinstance(result["summaries"], str)
        assert len(result["summaries"]) > 0

    def test_includes_all_documents(self):
        """Should include references to all 9 main documents."""
        result = _get_document_summary()
        summaries = result["summaries"]

        # Check for document IDs
        assert "[01]" in summaries
        assert "[02]" in summaries
        assert "[03]" in summaries
        assert "[04]" in summaries
        assert "[05]" in summaries
        assert "[06]" in summaries
        assert "[07]" in summaries
        assert "[08]" in summaries
        assert "[09]" in summaries

    def test_caching_works(self):
        """Should cache results to avoid repeated file reads."""
        result1 = _get_document_summary()
        result2 = _get_document_summary()

        # Should be identical strings (cached)
        assert result1["summaries"] == result2["summaries"]


class TestDocumentDetail:
    """Test DocumentDetail tool."""

    def test_fetch_single_document(self):
        """Should fetch a single document by ID."""
        result = _get_document_detail(doc_ids="01")

        assert "content" in result
        assert "fetched_docs" in result
        assert result["fetched_docs"] == ["01"]
        assert len(result["content"]) > 0
        assert "[01]" in result["content"]

    def test_fetch_multiple_documents(self):
        """Should fetch multiple documents."""
        result = _get_document_detail(doc_ids=["01", "02"])

        assert "content" in result
        assert "fetched_docs" in result
        assert result["fetched_docs"] == ["01", "02"]
        assert "[01]" in result["content"]
        assert "[02]" in result["content"]

    def test_invalid_doc_id(self):
        """Should handle invalid doc IDs gracefully."""
        result = _get_document_detail(doc_ids="99")

        assert "Error" in result["content"]
        assert "Invalid document IDs" in result["content"]
        assert result["fetched_docs"] == []

    def test_mixed_valid_invalid_ids(self):
        """Should reject request if any ID is invalid."""
        result = _get_document_detail(doc_ids=["01", "99"])

        assert "Error" in result["content"]
        assert result["fetched_docs"] == []

    def test_caching_works(self):
        """Should cache individual documents."""
        # First call loads from file
        result1 = _get_document_detail(doc_ids="01")

        # Second call should use cache
        result2 = _get_document_detail(doc_ids="01")

        assert result1["content"] == result2["content"]


class TestDSPyToolWrappers:
    """Test DSPy tool wrappers."""

    def test_document_summary_tool_exists(self):
        """DocumentSummary should be a valid DSPy tool."""
        assert hasattr(DocumentSummary, 'func')
        assert hasattr(DocumentSummary, 'name')
        assert hasattr(DocumentSummary, 'desc')
        assert DocumentSummary.name == "document_summary"

    def test_document_detail_tool_exists(self):
        """DocumentDetail should be a valid DSPy tool."""
        assert hasattr(DocumentDetail, 'func')
        assert hasattr(DocumentDetail, 'name')
        assert hasattr(DocumentDetail, 'desc')
        assert DocumentDetail.name == "document_detail"
