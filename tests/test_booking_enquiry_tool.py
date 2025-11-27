"""
Tests for BookingEnquiry DSPy Tool

Following TDD approach - these tests are written before implementation.
Tests cover:
- Successful enquiry creation
- Database interactions
- Notification sending
- Error handling
- Edge cases
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from app.llm.tools.BookingEnquiry import _create_booking_enquiry, BookingEnquiry


class TestCreateBookingEnquiry:
    """Test the private _create_booking_enquiry function."""

    @patch('app.llm.tools.BookingEnquiry.get_db_connection')
    @patch('app.llm.tools.BookingEnquiry.NotificationService')
    def test_successful_enquiry_creation(self, mock_notification_service, mock_db_connection):
        """Test successful booking enquiry creation and notification."""
        # Arrange
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_db_connection.return_value.__enter__.return_value = mock_connection
        mock_connection.cursor.return_value = mock_cursor

        # Mock database query result - event and organizer exist
        mock_cursor.fetchone.return_value = {
            'organizer_id': 1,
            'merchant_email': 'merchant@example.com',
            'merchant_phone': '+852 1234 5678',
            'event_name': 'Amazing Concert'
        }
        mock_cursor.lastrowid = 123  # Enquiry ID

        # Mock notification service
        mock_service_instance = Mock()
        mock_notification_service.return_value = mock_service_instance
        mock_service_instance.send_enquiry_to_merchant.return_value = {
            'success': True,
            'message': 'Notification sent',
            'channel': 'log'
        }

        # Act
        result = _create_booking_enquiry(
            event_id=1,
            user_message="I want to book 50 tickets for my company",
            contact_email="user@example.com",
            contact_phone="+852 9876 5432",
            enquiry_type="group_booking"
        )

        # Assert
        assert result['status'] == 'success'
        assert 'enquiry_id' in result
        assert result['enquiry_id'] == '123'
        assert '#123' in result['message']
        assert '24-48 hours' in result['message']

        # Verify database calls
        mock_cursor.execute.assert_any_call(
            pytest.approx("""
                SELECT
                    e.organizer_id,
                    o.contact_email as merchant_email,
                    o.contact_phone as merchant_phone,
                    JSON_UNQUOTE(JSON_EXTRACT(e.name, '$.en')) as event_name
                FROM events e
                INNER JOIN organizers o ON e.organizer_id = o.id
                WHERE e.id = %s AND e.event_status = 'published'
            """, rel=None),
            (1,)
        )

        # Verify INSERT was called
        insert_calls = [call for call in mock_cursor.execute.call_args_list
                       if 'INSERT INTO booking_enquiries' in str(call)]
        assert len(insert_calls) > 0

        # Verify notification was sent
        mock_service_instance.send_enquiry_to_merchant.assert_called_once()
        call_args = mock_service_instance.send_enquiry_to_merchant.call_args[1]
        assert call_args['enquiry_id'] == 123
        assert call_args['event_name'] == 'Amazing Concert'
        assert call_args['user_message'] == "I want to book 50 tickets for my company"
        assert call_args['user_email'] == "user@example.com"
        assert call_args['merchant_email'] == 'merchant@example.com'

    @patch('app.llm.tools.BookingEnquiry.get_db_connection')
    def test_event_not_found(self, mock_db_connection):
        """Test error handling when event doesn't exist."""
        # Arrange
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_db_connection.return_value.__enter__.return_value = mock_connection
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None  # Event not found

        # Act
        result = _create_booking_enquiry(
            event_id=999,
            user_message="Test message",
            contact_email="user@example.com"
        )

        # Assert
        assert result['status'] == 'error'
        assert 'not found' in result['message'].lower()

    @patch('app.llm.tools.BookingEnquiry.get_db_connection')
    def test_merchant_email_missing(self, mock_db_connection):
        """Test error handling when merchant contact info is missing."""
        # Arrange
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_db_connection.return_value.__enter__.return_value = mock_connection
        mock_connection.cursor.return_value = mock_cursor

        # Event exists but no merchant email
        mock_cursor.fetchone.return_value = {
            'organizer_id': 1,
            'merchant_email': None,
            'merchant_phone': None,
            'event_name': 'Test Event'
        }

        # Act
        result = _create_booking_enquiry(
            event_id=1,
            user_message="Test message",
            contact_email="user@example.com"
        )

        # Assert
        assert result['status'] == 'error'
        assert 'contact information not available' in result['message'].lower()

    @patch('app.llm.tools.BookingEnquiry.get_db_connection')
    @patch('app.llm.tools.BookingEnquiry.NotificationService')
    def test_notification_failure(self, mock_notification_service, mock_db_connection):
        """Test handling when notification sending fails."""
        # Arrange
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_db_connection.return_value.__enter__.return_value = mock_connection
        mock_connection.cursor.return_value = mock_cursor

        mock_cursor.fetchone.return_value = {
            'organizer_id': 1,
            'merchant_email': 'merchant@example.com',
            'merchant_phone': None,
            'event_name': 'Test Event'
        }
        mock_cursor.lastrowid = 456

        # Notification fails
        mock_service_instance = Mock()
        mock_notification_service.return_value = mock_service_instance
        mock_service_instance.send_enquiry_to_merchant.return_value = {
            'success': False,
            'message': 'SMTP error',
            'channel': 'email'
        }

        # Act
        result = _create_booking_enquiry(
            event_id=1,
            user_message="Test",
            contact_email="user@example.com"
        )

        # Assert
        assert result['status'] == 'error'
        assert 'failed to send' in result['message'].lower()

        # Status should NOT be updated to 'sent'
        update_calls = [call for call in mock_cursor.execute.call_args_list
                       if 'UPDATE' in str(call) and 'sent' in str(call)]
        assert len(update_calls) == 0

    @patch('app.llm.tools.BookingEnquiry.get_db_connection')
    def test_database_exception_handling(self, mock_db_connection):
        """Test graceful handling of database exceptions."""
        # Arrange
        mock_db_connection.return_value.__enter__.side_effect = Exception("DB connection failed")

        # Act
        result = _create_booking_enquiry(
            event_id=1,
            user_message="Test",
            contact_email="user@example.com"
        )

        # Assert
        assert result['status'] == 'error'
        assert 'error occurred' in result['message'].lower()
        assert 'support' in result['message'].lower()

    @patch('app.llm.tools.BookingEnquiry.get_db_connection')
    @patch('app.llm.tools.BookingEnquiry.NotificationService')
    def test_optional_phone_parameter(self, mock_notification_service, mock_db_connection):
        """Test that phone number is optional."""
        # Arrange
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_db_connection.return_value.__enter__.return_value = mock_connection
        mock_connection.cursor.return_value = mock_cursor

        mock_cursor.fetchone.return_value = {
            'organizer_id': 1,
            'merchant_email': 'merchant@example.com',
            'merchant_phone': None,
            'event_name': 'Test Event'
        }
        mock_cursor.lastrowid = 789

        mock_service_instance = Mock()
        mock_notification_service.return_value = mock_service_instance
        mock_service_instance.send_enquiry_to_merchant.return_value = {'success': True}

        # Act - no phone provided
        result = _create_booking_enquiry(
            event_id=1,
            user_message="Test",
            contact_email="user@example.com"
        )

        # Assert
        assert result['status'] == 'success'

    def test_enquiry_types(self):
        """Test that all valid enquiry types are accepted."""
        valid_types = ['custom_booking', 'group_booking', 'special_request', 'restaurant_reservation']

        for enquiry_type in valid_types:
            # Should not raise exception
            assert enquiry_type in ['custom_booking', 'group_booking', 'special_request', 'restaurant_reservation']

    @patch('app.llm.tools.BookingEnquiry.get_db_connection')
    @patch('app.llm.tools.BookingEnquiry.NotificationService')
    def test_merchant_based_enquiry(self, mock_notification_service, mock_db_connection):
        """Test merchant-based enquiry (new mode for restaurants)."""
        # Arrange
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_db_connection.return_value.__enter__.return_value = mock_connection
        mock_connection.cursor.return_value = mock_cursor

        # Mock merchant query result
        mock_cursor.fetchone.return_value = {
            'organizer_id': 5,
            'merchant_email': 'restaurant@example.com',
            'merchant_phone': '+852 2345 6789',
            'merchant_name': 'ABC Restaurant',
            'event_name': 'General Enquiry'
        }
        mock_cursor.lastrowid = 999

        # Mock notification service
        mock_service_instance = Mock()
        mock_notification_service.return_value = mock_service_instance
        mock_service_instance.send_enquiry_to_merchant.return_value = {
            'success': True,
            'message': 'Notification sent',
            'channel': 'log'
        }

        # Act
        result = _create_booking_enquiry(
            user_message="I want to reserve a table for 20 people",
            contact_email="customer@example.com",
            merchant_name="ABC Restaurant",
            contact_phone="+852 9999 8888",
            enquiry_type="restaurant_reservation"
        )

        # Assert
        assert result['status'] == 'success'
        assert 'enquiry_id' in result
        assert result['enquiry_id'] == '999'
        assert 'ABC Restaurant' in result['message']

        # Verify merchant search query was executed
        merchant_query_calls = [call for call in mock_cursor.execute.call_args_list
                               if 'FROM organizers o' in str(call) and 'WHERE JSON_UNQUOTE' in str(call)]
        assert len(merchant_query_calls) > 0

        # Verify INSERT was called with NULL event_id
        insert_calls = [call for call in mock_cursor.execute.call_args_list
                       if 'INSERT INTO booking_enquiries' in str(call)]
        assert len(insert_calls) > 0

        # Verify notification was sent with merchant name
        mock_service_instance.send_enquiry_to_merchant.assert_called_once()
        call_args = mock_service_instance.send_enquiry_to_merchant.call_args[1]
        assert call_args['event_name'] == 'ABC Restaurant'  # Display name should be merchant name

    @patch('app.llm.tools.BookingEnquiry.get_db_connection')
    def test_merchant_not_found(self, mock_db_connection):
        """Test error when merchant name doesn't exist."""
        # Arrange
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_db_connection.return_value.__enter__.return_value = mock_connection
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None  # Merchant not found

        # Act
        result = _create_booking_enquiry(
            user_message="Test message",
            contact_email="user@example.com",
            merchant_name="NonExistent Restaurant"
        )

        # Assert
        assert result['status'] == 'error'
        assert 'not found' in result['message'].lower()
        assert 'NonExistent Restaurant' in result['message']

    def test_missing_both_event_and_merchant(self):
        """Test error when neither event_id nor merchant_name is provided."""
        # Act
        result = _create_booking_enquiry(
            user_message="Test",
            contact_email="user@example.com"
        )

        # Assert
        assert result['status'] == 'error'
        assert 'event ID or merchant name' in result['message']

    def test_both_event_and_merchant_provided(self):
        """Test error when both event_id and merchant_name are provided."""
        # Act
        result = _create_booking_enquiry(
            user_message="Test",
            contact_email="user@example.com",
            event_id=1,
            merchant_name="ABC Restaurant"
        )

        # Assert
        assert result['status'] == 'error'
        assert 'either event_id OR merchant_name' in result['message']


class TestBookingEnquiryDSPyTool:
    """Test the DSPy Tool wrapper."""

    def test_tool_exists(self):
        """Test that BookingEnquiry tool is properly created."""
        assert BookingEnquiry is not None
        assert hasattr(BookingEnquiry, 'func')
        assert hasattr(BookingEnquiry, 'name')
        assert hasattr(BookingEnquiry, 'desc')

    def test_tool_name(self):
        """Test tool has correct name."""
        assert BookingEnquiry.name == "booking_enquiry"

    def test_tool_description(self):
        """Test tool has meaningful description for ReAct agent."""
        desc = BookingEnquiry.desc
        assert len(desc) > 50  # Should be detailed
        assert 'merchant' in desc.lower() or 'organizer' in desc.lower()
        assert 'enquiry' in desc.lower()

    def test_tool_function_reference(self):
        """Test tool references the correct implementation function."""
        assert BookingEnquiry.func == _create_booking_enquiry
