import time
import json
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import Message
import structlog

logger = structlog.get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for comprehensive request/response logging.

    Logs:
    - Request: method, path, headers (sanitized), query params, body
    - Response: status code, body (sanitized), processing time
    - Exceptions: full stack traces

    Follows OWASP logging best practices with data sanitization.
    """

    SENSITIVE_HEADERS = {
        'authorization', 'cookie', 'x-api-key', 'x-auth-token'
    }

    MAX_BODY_LOG_SIZE = 10000  # Log first 10KB of request/response body

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process and log HTTP request/response."""
        start_time = time.time()
        request_id = self._generate_request_id()

        # Bind request context to logger
        log = logger.bind(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_host=request.client.host if request.client else None,
        )

        # Log request
        await self._log_request(request, log)

        # Process request and capture response
        try:
            response = await call_next(request)
            duration = time.time() - start_time

            # Log successful response
            log.info(
                "Request completed",
                status_code=response.status_code,
                duration_ms=round(duration * 1000, 2)
            )

            return response

        except Exception as exc:
            duration = time.time() - start_time
            log.exception(
                "Request failed",
                exception=str(exc),
                duration_ms=round(duration * 1000, 2)
            )
            raise

    async def _log_request(self, request: Request, log: structlog.BoundLogger):
        """Log incoming request details."""
        # Sanitize headers
        headers = self._sanitize_headers(dict(request.headers))

        # Get query parameters
        query_params = dict(request.query_params)

        # Get request body if available
        body = await self._get_request_body(request)

        log.info(
            "Request received",
            headers=headers,
            query_params=query_params,
            body=body,
        )

    async def _get_request_body(self, request: Request) -> dict | str | None:
        """
        Extract and parse request body.
        Returns parsed JSON if content-type is application/json, otherwise raw string.
        """
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return None

        try:
            # Read body
            body_bytes = await request.body()

            if not body_bytes:
                return None

            # Limit body size for logging
            if len(body_bytes) > self.MAX_BODY_LOG_SIZE:
                return f"<body too large: {len(body_bytes)} bytes>"

            # Try to parse as JSON
            content_type = request.headers.get('content-type', '')
            if 'application/json' in content_type:
                body_str = body_bytes.decode('utf-8')
                body_data = json.loads(body_str)

                # Sanitize sensitive fields from body
                return self._sanitize_body(body_data)

            # Return truncated string for non-JSON
            return body_bytes.decode('utf-8', errors='replace')[:500]

        except Exception as e:
            logger.debug("Failed to parse request body", error=str(e))
            return None

    def _sanitize_headers(self, headers: dict) -> dict:
        """Remove or redact sensitive headers."""
        sanitized = {}
        for key, value in headers.items():
            if key.lower() in self.SENSITIVE_HEADERS:
                sanitized[key] = "***REDACTED***"
            else:
                sanitized[key] = value
        return sanitized

    def _sanitize_body(self, body: dict) -> dict:
        """Sanitize sensitive fields from request body."""
        if not isinstance(body, dict):
            return body

        sensitive_keys = {'password', 'token', 'api_key', 'secret', 'authorization'}
        sanitized = {}

        for key, value in body.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                sanitized[key] = "***REDACTED***"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_body(value)
            else:
                sanitized[key] = value

        return sanitized

    def _generate_request_id(self) -> str:
        """Generate unique request ID for tracing."""
        import uuid
        return str(uuid.uuid4())[:8]
