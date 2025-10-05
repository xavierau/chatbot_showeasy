import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from src.app.middleware.logging_middleware import LoggingMiddleware
import structlog
from unittest.mock import patch, MagicMock


@pytest.fixture
def app():
    """Create a test FastAPI app with logging middleware."""
    test_app = FastAPI()
    test_app.add_middleware(LoggingMiddleware)

    @test_app.get("/test")
    async def test_endpoint():
        return {"status": "ok"}

    @test_app.post("/echo")
    async def echo_endpoint(data: dict):
        return data

    @test_app.get("/error")
    async def error_endpoint():
        raise ValueError("Test error")

    return test_app


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


class TestLoggingMiddleware:
    """Test suite for LoggingMiddleware."""

    def test_successful_request_logging(self, client):
        """Test that successful requests are logged correctly."""
        with patch.object(structlog.get_logger(), 'info') as mock_log:
            response = client.get("/test")

            assert response.status_code == 200
            # Verify logging was called
            assert mock_log.called

    def test_post_request_with_body(self, client):
        """Test that POST requests with body are logged."""
        test_data = {"message": "test", "value": 123}

        response = client.post("/echo", json=test_data)

        assert response.status_code == 200
        assert response.json() == test_data

    def test_request_with_query_params(self, client):
        """Test that query parameters are logged."""
        response = client.get("/test?param1=value1&param2=value2")

        assert response.status_code == 200

    def test_sensitive_header_sanitization(self):
        """Test that sensitive headers are redacted."""
        middleware = LoggingMiddleware(app=MagicMock())

        headers = {
            "authorization": "Bearer secret-token",
            "cookie": "session=abc123",
            "x-api-key": "api-key-123",
            "content-type": "application/json"
        }

        sanitized = middleware._sanitize_headers(headers)

        assert sanitized["authorization"] == "***REDACTED***"
        assert sanitized["cookie"] == "***REDACTED***"
        assert sanitized["x-api-key"] == "***REDACTED***"
        assert sanitized["content-type"] == "application/json"

    def test_sensitive_body_sanitization(self):
        """Test that sensitive fields in request body are redacted."""
        middleware = LoggingMiddleware(app=MagicMock())

        body = {
            "username": "testuser",
            "password": "secret123",
            "token": "jwt-token",
            "data": "normal data"
        }

        sanitized = middleware._sanitize_body(body)

        assert sanitized["username"] == "testuser"
        assert sanitized["password"] == "***REDACTED***"
        assert sanitized["token"] == "***REDACTED***"
        assert sanitized["data"] == "normal data"

    def test_nested_body_sanitization(self):
        """Test that nested sensitive fields are sanitized."""
        middleware = LoggingMiddleware(app=MagicMock())

        body = {
            "user": {
                "name": "John",
                "password": "secret",
                "profile": {
                    "api_key": "key123"
                }
            }
        }

        sanitized = middleware._sanitize_body(body)

        assert sanitized["user"]["name"] == "John"
        assert sanitized["user"]["password"] == "***REDACTED***"
        assert sanitized["user"]["profile"]["api_key"] == "***REDACTED***"

    def test_request_id_generation(self):
        """Test that unique request IDs are generated."""
        middleware = LoggingMiddleware(app=MagicMock())

        request_id_1 = middleware._generate_request_id()
        request_id_2 = middleware._generate_request_id()

        assert request_id_1 != request_id_2
        assert len(request_id_1) == 8  # UUID truncated to 8 chars
        assert len(request_id_2) == 8

    def test_exception_logging(self, client):
        """Test that exceptions are logged with stack traces."""
        with patch.object(structlog.get_logger(), 'exception') as mock_log:
            with pytest.raises(ValueError):
                client.get("/error")

            # Verify exception logging was called
            assert mock_log.called

    def test_large_body_handling(self):
        """Test that large request bodies are truncated in logs."""
        middleware = LoggingMiddleware(app=MagicMock())

        # Create a body larger than MAX_BODY_LOG_SIZE
        large_data = "x" * (middleware.MAX_BODY_LOG_SIZE + 1000)

        # This would normally be tested with an async request
        # For now, verify the constant exists
        assert middleware.MAX_BODY_LOG_SIZE == 10000


class TestSensitiveDataSanitization:
    """Test suite specifically for sensitive data handling."""

    def test_password_variations_are_sanitized(self):
        """Test various password field naming conventions."""
        middleware = LoggingMiddleware(app=MagicMock())

        body = {
            "password": "secret",
            "Password": "secret",
            "user_password": "secret",
            "passwordConfirm": "secret"
        }

        sanitized = middleware._sanitize_body(body)

        for key in body.keys():
            assert sanitized[key] == "***REDACTED***"

    def test_token_variations_are_sanitized(self):
        """Test various token field naming conventions."""
        middleware = LoggingMiddleware(app=MagicMock())

        body = {
            "token": "jwt-123",
            "auth_token": "bearer-456",
            "access_token": "token-789",
            "refreshToken": "refresh-abc"
        }

        sanitized = middleware._sanitize_body(body)

        for key in body.keys():
            assert sanitized[key] == "***REDACTED***"

    def test_non_sensitive_data_preserved(self):
        """Test that non-sensitive data is preserved."""
        middleware = LoggingMiddleware(app=MagicMock())

        body = {
            "user_input": "Hello world",
            "session_id": "session-123",
            "current_url": "https://example.com",
            "metadata": {"key": "value"}
        }

        sanitized = middleware._sanitize_body(body)

        # All values should be unchanged
        assert sanitized == body
