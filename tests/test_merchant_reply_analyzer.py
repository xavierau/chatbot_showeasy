"""
Tests for MerchantReplyAnalyzer DSPy Module

Following TDD approach - tests written before implementation.
Tests cover:
- Signature validation
- LLM-powered reply formatting
- Context preservation
- Edge cases (rude replies, unclear replies, etc.)
"""

import pytest
import dspy
from unittest.mock import Mock, patch
from app.llm.modules.MerchantReplyAnalyzer import (
    MerchantReplySignature,
    MerchantReplyAnalyzer
)


class TestMerchantReplySignature:
    """Test the DSPy signature for merchant reply analysis."""

    def test_signature_exists(self):
        """Test that signature is properly defined."""
        assert MerchantReplySignature is not None
        assert issubclass(MerchantReplySignature, dspy.Signature)

    def test_signature_has_required_fields(self):
        """Test signature has all required input/output fields."""
        # Get fields from signature
        fields = MerchantReplySignature.model_fields

        # Check input fields
        assert 'user_enquiry' in fields
        assert 'merchant_reply' in fields
        assert 'event_name' in fields

        # Check output field
        assert 'formatted_response' in fields

    def test_signature_field_types(self):
        """Test that fields have correct types."""
        fields = MerchantReplySignature.model_fields

        # All fields should be strings
        assert fields['user_enquiry'].annotation == str
        assert fields['merchant_reply'].annotation == str
        assert fields['event_name'].annotation == str
        assert fields['formatted_response'].annotation == str

    def test_signature_has_docstring(self):
        """Test signature has meaningful docstring for LLM."""
        assert MerchantReplySignature.__doc__ is not None
        assert len(MerchantReplySignature.__doc__) > 50
        assert 'merchant' in MerchantReplySignature.__doc__.lower()


class TestMerchantReplyAnalyzer:
    """Test the MerchantReplyAnalyzer DSPy module."""

    def test_module_exists(self):
        """Test that module can be instantiated."""
        analyzer = MerchantReplyAnalyzer()
        assert analyzer is not None
        assert isinstance(analyzer, dspy.Module)

    @pytest.mark.skip(reason="Requires configured LLM - integration test")
    def test_forward_with_positive_reply(self):
        """Test formatting a positive merchant reply."""
        analyzer = MerchantReplyAnalyzer()

        result = analyzer(
            user_enquiry="I want to book 50 tickets for my company event",
            merchant_reply="Yes, we can accommodate 50 people. We offer a 15% group discount. Please call us at 1234-5678 to finalize.",
            event_name="Amazing Concert"
        )

        assert result.formatted_response is not None
        assert len(result.formatted_response) > 50
        # Should include key information
        assert '50' in result.formatted_response or 'fifty' in result.formatted_response.lower()
        assert 'discount' in result.formatted_response.lower() or '15%' in result.formatted_response

    @pytest.mark.skip(reason="Requires configured LLM - integration test")
    def test_forward_with_negative_reply(self):
        """Test formatting a rejection from merchant."""
        analyzer = MerchantReplyAnalyzer()

        result = analyzer(
            user_enquiry="Can I get tickets for free?",
            merchant_reply="No, all tickets must be purchased at full price.",
            event_name="Concert XYZ"
        )

        assert result.formatted_response is not None
        # Should be polite even if merchant was direct
        assert 'unfortunately' in result.formatted_response.lower() or 'apologize' in result.formatted_response.lower()

    @pytest.mark.skip(reason="Requires configured LLM - integration test")
    def test_forward_preserves_contact_info(self):
        """Test that important contact information is preserved."""
        analyzer = MerchantReplyAnalyzer()

        result = analyzer(
            user_enquiry="How can I contact you?",
            merchant_reply="Please email us at contact@event.com or call +852-1234-5678",
            event_name="Test Event"
        )

        assert result.formatted_response is not None
        # Contact info should be preserved
        assert 'contact@event.com' in result.formatted_response
        assert '1234-5678' in result.formatted_response or '+852-1234-5678' in result.formatted_response

    @pytest.mark.skip(reason="Requires configured LLM - integration test")
    def test_forward_with_unclear_merchant_reply(self):
        """Test handling of unclear or poorly formatted merchant replies."""
        analyzer = MerchantReplyAnalyzer()

        result = analyzer(
            user_enquiry="Do you have group discounts?",
            merchant_reply="maybe depends call office",  # Poorly formatted
            event_name="Event ABC"
        )

        assert result.formatted_response is not None
        # Should improve clarity
        assert len(result.formatted_response) > len("maybe depends call office")

    def test_module_has_predict_method(self):
        """Test that module inherits predict method from ChainOfThought."""
        analyzer = MerchantReplyAnalyzer()
        assert hasattr(analyzer, 'predict')
        assert callable(analyzer.predict)

    def test_module_has_forward_method(self):
        """Test that module has forward method."""
        analyzer = MerchantReplyAnalyzer()
        assert hasattr(analyzer, 'forward')
        assert callable(analyzer.forward)

    @patch('dspy.ChainOfThought')
    def test_module_uses_chain_of_thought(self, mock_cot):
        """Test that module uses ChainOfThought internally."""
        # This tests the structure, not the actual LLM call
        mock_cot_instance = Mock()
        mock_cot.return_value = mock_cot_instance

        analyzer = MerchantReplyAnalyzer()

        # Verify ChainOfThought was initialized with signature
        mock_cot.assert_called_once()
        call_args = mock_cot.call_args
        assert call_args[0][0] == MerchantReplySignature

    def test_callable_with_kwargs(self):
        """Test that analyzer can be called with keyword arguments."""
        analyzer = MerchantReplyAnalyzer()

        # Should not raise exception (though will fail without LLM configured)
        try:
            analyzer(
                user_enquiry="Test enquiry",
                merchant_reply="Test reply",
                event_name="Test Event"
            )
        except Exception as e:
            # Expected to fail without LLM, but should accept the parameters
            assert 'user_enquiry' not in str(e)
            assert 'merchant_reply' not in str(e)
            assert 'event_name' not in str(e)


class TestMerchantReplyAnalyzerEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_inputs(self):
        """Test behavior with empty string inputs."""
        analyzer = MerchantReplyAnalyzer()

        # Should not crash with empty strings
        try:
            result = analyzer(
                user_enquiry="",
                merchant_reply="",
                event_name=""
            )
        except Exception as e:
            # If it fails, should be due to LLM config, not input validation
            assert 'empty' not in str(e).lower()

    def test_very_long_inputs(self):
        """Test behavior with very long inputs."""
        analyzer = MerchantReplyAnalyzer()

        long_text = "This is a very long message. " * 100  # 500+ characters

        # Should handle long inputs
        try:
            result = analyzer(
                user_enquiry=long_text,
                merchant_reply=long_text,
                event_name="Event"
            )
        except Exception as e:
            # Should not fail due to length
            assert 'length' not in str(e).lower()
            assert 'too long' not in str(e).lower()

    def test_special_characters_in_input(self):
        """Test handling of special characters."""
        analyzer = MerchantReplyAnalyzer()

        special_text = "Test with émojis 😊 and spëcial ćhars <>&\"'"

        try:
            result = analyzer(
                user_enquiry=special_text,
                merchant_reply=special_text,
                event_name=special_text
            )
        except UnicodeError:
            pytest.fail("Should handle special characters without UnicodeError")
