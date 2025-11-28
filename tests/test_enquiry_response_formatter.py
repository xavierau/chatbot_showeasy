"""
Unit tests for EnquiryResponseFormatter DSPy Module

Tests the LLM-powered message formatting for confirm/decline scenarios.
Uses mocked DSPy predictions to test the module structure without actual LLM calls.

Note: Uses sys.path manipulation to import directly from the module file
to avoid mysql.connector dependency in the modules __init__.py
"""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock

# Add src to path for direct imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


@pytest.fixture(autouse=True)
def mock_langfuse():
    """Mock langfuse observe decorator to avoid import issues."""
    with patch('langfuse.observe', lambda **kwargs: lambda f: f):
        yield


class TestEnquiryResponseFormatterStructure:
    """Tests for EnquiryResponseFormatter module structure."""

    def test_response_type_enum_values(self):
        """Should have correct enum values for response types."""
        # Import directly from file to avoid __init__.py chain
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "EnquiryResponseFormatter",
            os.path.join(os.path.dirname(__file__), '..', 'src', 'app', 'llm', 'modules', 'EnquiryResponseFormatter.py')
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        ResponseType = module.ResponseType
        assert ResponseType.CONFIRM.value == "confirm"
        assert ResponseType.DECLINE.value == "decline"
        assert ResponseType.CUSTOM.value == "custom"


class TestEnquiryResponseFormatterInit:
    """Tests for EnquiryResponseFormatter initialization."""

    def test_init_creates_predictors(self):
        """Should initialize with confirm and decline predictors."""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "EnquiryResponseFormatter",
            os.path.join(os.path.dirname(__file__), '..', 'src', 'app', 'llm', 'modules', 'EnquiryResponseFormatter.py')
        )
        module = importlib.util.module_from_spec(spec)

        with patch('dspy.ChainOfThought') as mock_cot:
            spec.loader.exec_module(module)
            EnquiryResponseFormatter = module.EnquiryResponseFormatter

            formatter = EnquiryResponseFormatter()

            # Should create two ChainOfThought predictors
            assert mock_cot.call_count == 2
            assert hasattr(formatter, 'confirm_predictor')
            assert hasattr(formatter, 'decline_predictor')


class TestFormatConfirmation:
    """Tests for format_confirmation method."""

    def test_format_confirmation_returns_formatted_response(self):
        """Should return the formatted_response from prediction."""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "EnquiryResponseFormatter",
            os.path.join(os.path.dirname(__file__), '..', 'src', 'app', 'llm', 'modules', 'EnquiryResponseFormatter.py')
        )
        module = importlib.util.module_from_spec(spec)

        expected_response = "Great news! Your booking has been confirmed."
        mock_result = MagicMock()
        mock_result.formatted_response = expected_response

        with patch('dspy.ChainOfThought') as mock_cot:
            mock_cot.return_value = MagicMock(return_value=mock_result)
            spec.loader.exec_module(module)
            EnquiryResponseFormatter = module.EnquiryResponseFormatter

            formatter = EnquiryResponseFormatter()
            result = formatter.format_confirmation("test enquiry", "test event")

            assert result == expected_response


class TestFormatDecline:
    """Tests for format_decline method."""

    def test_format_decline_returns_formatted_response(self):
        """Should return the formatted_response from prediction."""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "EnquiryResponseFormatter",
            os.path.join(os.path.dirname(__file__), '..', 'src', 'app', 'llm', 'modules', 'EnquiryResponseFormatter.py')
        )
        module = importlib.util.module_from_spec(spec)

        expected_response = "We regret to inform you that the booking cannot be accommodated."
        mock_result = MagicMock()
        mock_result.formatted_response = expected_response

        with patch('dspy.ChainOfThought') as mock_cot:
            mock_cot.return_value = MagicMock(return_value=mock_result)
            spec.loader.exec_module(module)
            EnquiryResponseFormatter = module.EnquiryResponseFormatter

            formatter = EnquiryResponseFormatter()
            result = formatter.format_decline(
                user_enquiry="I want to book 50 tickets",
                event_name="Test Event",
                merchant_reason="Fully booked"
            )

            assert result == expected_response

    def test_format_decline_with_empty_reason(self):
        """Should handle empty merchant reason gracefully."""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "EnquiryResponseFormatter",
            os.path.join(os.path.dirname(__file__), '..', 'src', 'app', 'llm', 'modules', 'EnquiryResponseFormatter.py')
        )
        module = importlib.util.module_from_spec(spec)

        mock_result = MagicMock()
        mock_result.formatted_response = "Unfortunately, your request could not be accommodated."

        with patch('dspy.ChainOfThought') as mock_cot:
            mock_cot.return_value = MagicMock(return_value=mock_result)
            spec.loader.exec_module(module)
            EnquiryResponseFormatter = module.EnquiryResponseFormatter

            formatter = EnquiryResponseFormatter()
            result = formatter.format_decline(
                user_enquiry="I want to book tickets",
                event_name="Test Event",
                merchant_reason=""  # Empty reason
            )

            # Should still work and return a response
            assert result == "Unfortunately, your request could not be accommodated."


class TestSignatureDescriptions:
    """Tests for signature field descriptions."""

    def test_confirmation_signature_has_required_fields(self):
        """Should have user_enquiry, event_name inputs and formatted_response output."""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "EnquiryResponseFormatter",
            os.path.join(os.path.dirname(__file__), '..', 'src', 'app', 'llm', 'modules', 'EnquiryResponseFormatter.py')
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        ConfirmationResponseSignature = module.ConfirmationResponseSignature

        # DSPy Signatures store fields in model_fields (Pydantic-style)
        fields = ConfirmationResponseSignature.model_fields
        assert 'user_enquiry' in fields
        assert 'event_name' in fields
        assert 'formatted_response' in fields

    def test_decline_signature_has_required_fields(self):
        """Should have user_enquiry, event_name, merchant_reason inputs and formatted_response output."""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "EnquiryResponseFormatter",
            os.path.join(os.path.dirname(__file__), '..', 'src', 'app', 'llm', 'modules', 'EnquiryResponseFormatter.py')
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        DeclineResponseSignature = module.DeclineResponseSignature

        fields = DeclineResponseSignature.model_fields
        assert 'user_enquiry' in fields
        assert 'event_name' in fields
        assert 'merchant_reason' in fields
        assert 'formatted_response' in fields
