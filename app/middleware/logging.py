# app/middleware/logging.py
"""
Enhanced logging middleware for enterprise-level observability.
"""

import time
import json
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive logging middleware that captures:
    - Request/response details
    - Performance metrics
    - Error tracking
    - User context
    """
    
    def __init__(
        self,
        app,
        log_requests: bool = True,
        log_responses: bool = True,
        log_request_body: bool = False,  # Disabled by default for security
        max_body_size: int = 1024  # Max body size to log
    ):
        super().__init__(app)
        self.log_requests = log_requests
        self.log_responses = log_responses
        self.log_request_body = log_request_body
        self.max_body_size = max_body_size
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # Get correlation ID from security middleware
        correlation_id = getattr(request.state, 'correlation_id', 'unknown')
        
        # Log request details
        if self.log_requests:
            await self._log_request(request, correlation_id)
        
        # Process request
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Log response details
        if self.log_responses:
            self._log_response(request, response, process_time, correlation_id)
        
        return response
    
    async def _log_request(self, request: Request, correlation_id: str):
        """Log incoming request details."""
        request_data = {
            "event": "http_request",
            "correlation_id": correlation_id,
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "headers": dict(request.headers),
            "client_ip": self._get_client_ip(request),
            "user_agent": request.headers.get("User-Agent", ""),
            "timestamp": time.time()
        }
        
        # Log request body if enabled (be careful with sensitive data)
        if self.log_request_body and request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if body and len(body) <= self.max_body_size:
                    # Try to parse as JSON, otherwise log as string
                    try:
                        request_data["body"] = json.loads(body.decode('utf-8'))
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        request_data["body"] = body.decode('utf-8', errors='ignore')[:self.max_body_size]
            except Exception as e:
                logger.warning(f"Failed to read request body: {e}")
        
        logger.info(f"HTTP Request: {json.dumps(request_data, default=str)}")
    
    def _log_response(self, request: Request, response: Response, process_time: float, correlation_id: str):
        """Log response details."""
        response_data = {
            "event": "http_response",
            "correlation_id": correlation_id,
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "status_code": response.status_code,
            "processing_time_ms": round(process_time * 1000, 2),
            "response_headers": dict(response.headers),
            "timestamp": time.time()
        }
        
        # Determine log level based on status code
        if response.status_code >= 500:
            logger.error(f"HTTP Response: {json.dumps(response_data, default=str)}")
        elif response.status_code >= 400:
            logger.warning(f"HTTP Response: {json.dumps(response_data, default=str)}")
        else:
            logger.info(f"HTTP Response: {json.dumps(response_data, default=str)}")
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP considering proxies."""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.client.host if request.client else "unknown"


class StructuredLogger:
    """
    Utility class for structured logging throughout the application.
    """
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
    
    def log_business_event(self, event_type: str, data: dict, correlation_id: str = None):
        """Log business events with structured format."""
        log_data = {
            "event_type": "business_event",
            "event": event_type,
            "data": data,
            "timestamp": time.time()
        }
        
        if correlation_id:
            log_data["correlation_id"] = correlation_id
        
        self.logger.info(json.dumps(log_data, default=str))
    
    def log_api_call(self, service: str, endpoint: str, status: str, duration: float, correlation_id: str = None):
        """Log external API calls."""
        log_data = {
            "event_type": "external_api_call",
            "service": service,
            "endpoint": endpoint,
            "status": status,
            "duration_ms": round(duration * 1000, 2),
            "timestamp": time.time()
        }
        
        if correlation_id:
            log_data["correlation_id"] = correlation_id
        
        if status == "success":
            self.logger.info(json.dumps(log_data, default=str))
        else:
            self.logger.error(json.dumps(log_data, default=str))
    
    def log_error(self, error: Exception, context: dict = None, correlation_id: str = None):
        """Log errors with structured format."""
        log_data = {
            "event_type": "error",
            "error_type": type(error).__name__,
            "error_message": str(error),
            "timestamp": time.time()
        }
        
        if context:
            log_data["context"] = context
        
        if correlation_id:
            log_data["correlation_id"] = correlation_id
        
        self.logger.error(json.dumps(log_data, default=str), exc_info=True)