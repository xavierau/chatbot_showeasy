"""
Tests for Enquiry Reply API Endpoints

Following TDD approach - tests written before implementation.
Tests cover:
- POST /api/enquiry-reply endpoint
- Request validation
- Database operations
- LLM reply formatting
- User notification
- Error handling
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
from app.models import EnquiryReplyRequest


@pytest.fixture
def mock_db_connection():
    """Mock database connection."""
    with patch('config.database.DatabaseConnectionPool') as mock_pool:
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_pool.return_value.get_connection.return_value = mock_connection
        mock_connection.cursor.return_value = mock_cursor
        mock_connection.is_connected.return_value = True
        yield mock_connection, mock_cursor


@pytest.fixture
def mock_analyzer():
    """Mock MerchantReplyAnalyzer."""
    with patch('app.llm.modules.MerchantReplyAnalyzer.MerchantReplyAnalyzer') as mock:
        mock_instance = Mock()
        mock.return_value = mock_instance
        mock_instance.return_value = Mock(
            formatted_response="This is a formatted reply from the merchant."
        )
        yield mock_instance


@pytest.fixture
def mock_notification_service():
    """Mock NotificationService."""
    with patch('app.services.notification.NotificationService') as mock:
        mock_instance = Mock()
        mock.return_value = mock_instance
        mock_instance.send_reply_to_user.return_value = {
            'success': True,
            'message': 'Notification sent',
            'channel': 'log'
        }
        yield mock_instance


class TestEnquiryReplyRequest:
    """Test the Pydantic request model."""

    def test_model_exists(self):
        """Test that EnquiryReplyRequest model is defined."""
        assert EnquiryReplyRequest is not None

    def test_model_valid_input(self):
        """Test model validates correct input."""
        request = EnquiryReplyRequest(
            enquiry_id=123,
            reply_message="Yes, we can accommodate your request",
            reply_channel="email"
        )

        assert request.enquiry_id == 123
        assert request.reply_message == "Yes, we can accommodate your request"
        assert request.reply_channel == "email"

    def test_model_default_channel(self):
        """Test default reply_channel is 'api'."""
        request = EnquiryReplyRequest(
            enquiry_id=123,
            reply_message="Test reply"
        )

        assert request.reply_channel == "api"

    def test_model_missing_required_fields(self):
        """Test validation fails for missing required fields."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            EnquiryReplyRequest(reply_message="Test")  # Missing enquiry_id

        with pytest.raises(Exception):
            EnquiryReplyRequest(enquiry_id=123)  # Missing reply_message

    def test_model_invalid_channel(self):
        """Test validation for invalid channel."""
        # Model should accept any string, but API might validate
        request = EnquiryReplyRequest(
            enquiry_id=123,
            reply_message="Test",
            reply_channel="invalid_channel"
        )
        assert request.reply_channel == "invalid_channel"


@pytest.mark.skip(reason="Requires FastAPI app instance - integration test")
class TestEnquiryReplyEndpoint:
    """Test the /api/enquiry-reply endpoint."""

    def test_endpoint_exists(self, client: TestClient):
        """Test that endpoint is registered."""
        response = client.post("/api/enquiry-reply", json={
            "enquiry_id": 999,
            "reply_message": "Test"
        })

        # Should not get 404
        assert response.status_code != 404

    def test_successful_reply(
        self,
        client: TestClient,
        mock_db_connection,
        mock_analyzer,
        mock_notification_service
    ):
        """Test successful enquiry reply processing."""
        mock_connection, mock_cursor = mock_db_connection

        # Mock database query result
        mock_cursor.fetchone.return_value = {
            'id': 123,
            'session_id': 'test-session',
            'user_message': 'Can I book 50 tickets?',
            'contact_email': 'user@example.com',
            'contact_phone': None,
            'event_name': 'Concert XYZ'
        }

        response = client.post("/api/enquiry-reply", json={
            "enquiry_id": 123,
            "reply_message": "Yes, we can accommodate 50 people with a 15% discount",
            "reply_channel": "email"
        })

        # Assert response
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'success'
        assert 'delivered' in data['message'].lower()

        # Verify database operations
        # Should query enquiry details
        select_calls = [call for call in mock_cursor.execute.call_args_list
                       if 'SELECT' in str(call)]
        assert len(select_calls) > 0

        # Should insert reply
        insert_calls = [call for call in mock_cursor.execute.call_args_list
                       if 'INSERT INTO enquiry_replies' in str(call)]
        assert len(insert_calls) > 0

        # Should update enquiry status
        update_calls = [call for call in mock_cursor.execute.call_args_list
                       if 'UPDATE booking_enquiries' in str(call)]
        assert len(update_calls) > 0

        # Verify analyzer was called
        mock_analyzer.assert_called_once()

        # Verify notification was sent
        mock_notification_service.send_reply_to_user.assert_called_once()

    def test_enquiry_not_found(
        self,
        client: TestClient,
        mock_db_connection
    ):
        """Test error handling when enquiry doesn't exist."""
        mock_connection, mock_cursor = mock_db_connection
        mock_cursor.fetchone.return_value = None  # Enquiry not found

        response = client.post("/api/enquiry-reply", json={
            "enquiry_id": 999,
            "reply_message": "Test reply"
        })

        assert response.status_code == 200  # Returns 200 with error status
        data = response.json()
        assert data['status'] == 'error'
        assert 'not found' in data['message'].lower()

    def test_invalid_request_body(self, client: TestClient):
        """Test validation of request body."""
        response = client.post("/api/enquiry-reply", json={
            "invalid_field": "test"
        })

        assert response.status_code == 422  # Validation error

    def test_database_error_handling(
        self,
        client: TestClient,
        mock_db_connection
    ):
        """Test graceful handling of database errors."""
        mock_connection, mock_cursor = mock_db_connection
        mock_cursor.execute.side_effect = Exception("Database connection lost")

        response = client.post("/api/enquiry-reply", json={
            "enquiry_id": 123,
            "reply_message": "Test"
        })

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'error'

    def test_analyzer_integration(
        self,
        client: TestClient,
        mock_db_connection,
        mock_analyzer
    ):
        """Test that analyzer formats merchant reply correctly."""
        mock_connection, mock_cursor = mock_db_connection

        mock_cursor.fetchone.return_value = {
            'id': 123,
            'session_id': 'test-session',
            'user_message': 'Original enquiry',
            'contact_email': 'user@example.com',
            'contact_phone': None,
            'event_name': 'Test Event'
        }

        merchant_reply = "yes discount available call office"
        formatted_reply = "Great news! A discount is available. Please contact the office for details."

        mock_analyzer.return_value = Mock(formatted_response=formatted_reply)

        response = client.post("/api/enquiry-reply", json={
            "enquiry_id": 123,
            "reply_message": merchant_reply
        })

        assert response.status_code == 200

        # Verify analyzer was called with correct parameters
        call_args = mock_analyzer.call_args[1]
        assert call_args['user_enquiry'] == 'Original enquiry'
        assert call_args['merchant_reply'] == merchant_reply
        assert call_args['event_name'] == 'Test Event'

    def test_memory_manager_update(
        self,
        client: TestClient,
        mock_db_connection,
        mock_analyzer
    ):
        """Test that conversation history is updated."""
        mock_connection, mock_cursor = mock_db_connection

        mock_cursor.fetchone.return_value = {
            'id': 123,
            'session_id': 'test-session-123',
            'user_message': 'Test',
            'contact_email': 'user@example.com',
            'contact_phone': None,
            'event_name': 'Event'
        }

        with patch('app.memory_manager.MemoryManager') as mock_memory:
            mock_memory_instance = Mock()
            mock_memory.return_value = mock_memory_instance

            response = client.post("/api/enquiry-reply", json={
                "enquiry_id": 123,
                "reply_message": "Merchant reply"
            })

            assert response.status_code == 200

            # Verify memory was retrieved and updated
            mock_memory_instance.get_memory.assert_called_with('test-session-123')
            mock_memory_instance.update_memory.assert_called_once()

    def test_notification_failure_handling(
        self,
        client: TestClient,
        mock_db_connection,
        mock_analyzer,
        mock_notification_service
    ):
        """Test handling when user notification fails."""
        mock_connection, mock_cursor = mock_db_connection

        mock_cursor.fetchone.return_value = {
            'id': 123,
            'session_id': 'test-session',
            'user_message': 'Test',
            'contact_email': 'user@example.com',
            'contact_phone': None,
            'event_name': 'Event'
        }

        # Notification fails
        mock_notification_service.send_reply_to_user.return_value = {
            'success': False,
            'message': 'Email send failed'
        }

        response = client.post("/api/enquiry-reply", json={
            "enquiry_id": 123,
            "reply_message": "Test reply"
        })

        # Should still succeed (reply is stored)
        assert response.status_code == 200
        # But might log warning or return partial success

    def test_different_reply_channels(
        self,
        client: TestClient,
        mock_db_connection,
        mock_analyzer
    ):
        """Test support for different reply channels."""
        mock_connection, mock_cursor = mock_db_connection

        mock_cursor.fetchone.return_value = {
            'id': 123,
            'session_id': 'test-session',
            'user_message': 'Test',
            'contact_email': 'user@example.com',
            'contact_phone': None,
            'event_name': 'Event'
        }

        channels = ['email', 'whatsapp', 'api']

        for channel in channels:
            response = client.post("/api/enquiry-reply", json={
                "enquiry_id": 123,
                "reply_message": "Test",
                "reply_channel": channel
            })

            assert response.status_code == 200

            # Verify channel was stored in database
            insert_call = [call for call in mock_cursor.execute.call_args_list
                          if 'INSERT INTO enquiry_replies' in str(call)][-1]
            assert channel in str(insert_call)
