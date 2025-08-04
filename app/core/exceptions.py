# app/core/exceptions.py
"""
Centralized exception handling for enterprise-level error management.
"""

from typing import Any, Dict, Optional, Union
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
import traceback

logger = logging.getLogger(__name__)


class EliteDynamicsException(Exception):
    """Base exception class for EliteDynamics API."""
    
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = "INTERNAL_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(EliteDynamicsException):
    """Exception for validation errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=422,
            error_code="VALIDATION_ERROR",
            details=details
        )


class AuthenticationError(EliteDynamicsException):
    """Exception for authentication errors."""
    
    def __init__(self, message: str = "Authentication required", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=401,
            error_code="AUTHENTICATION_ERROR",
            details=details
        )


class AuthorizationError(EliteDynamicsException):
    """Exception for authorization errors."""
    
    def __init__(self, message: str = "Insufficient permissions", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=403,
            error_code="AUTHORIZATION_ERROR",
            details=details
        )


class NotFoundError(EliteDynamicsException):
    """Exception for resource not found errors."""
    
    def __init__(self, message: str = "Resource not found", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=404,
            error_code="NOT_FOUND_ERROR",
            details=details
        )


class ExternalServiceError(EliteDynamicsException):
    """Exception for external service integration errors."""
    
    def __init__(
        self,
        service_name: str,
        message: str,
        original_error: Optional[Exception] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.service_name = service_name
        self.original_error = original_error
        
        error_details = details or {}
        error_details.update({
            "service": service_name,
            "original_error": str(original_error) if original_error else None
        })
        
        super().__init__(
            message=f"External service error ({service_name}): {message}",
            status_code=502,
            error_code="EXTERNAL_SERVICE_ERROR",
            details=error_details
        )


class RateLimitError(EliteDynamicsException):
    """Exception for rate limiting errors."""
    
    def __init__(self, message: str = "Rate limit exceeded", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=429,
            error_code="RATE_LIMIT_ERROR",
            details=details
        )


class BusinessLogicError(EliteDynamicsException):
    """Exception for business logic errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=400,
            error_code="BUSINESS_LOGIC_ERROR",
            details=details
        )


async def elite_dynamics_exception_handler(request: Request, exc: EliteDynamicsException) -> JSONResponse:
    """Handle custom EliteDynamics exceptions."""
    
    correlation_id = getattr(request.state, 'correlation_id', 'unknown')
    
    # Log the exception
    logger.error(
        f"EliteDynamics Exception: {exc.error_code} - {exc.message} "
        f"- Correlation ID: {correlation_id}",
        extra={
            "correlation_id": correlation_id,
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "details": exc.details
        }
    )
    
    response_content = {
        "error": exc.error_code,
        "message": exc.message,
        "correlation_id": correlation_id,
        "details": exc.details
    }
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response_content
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle general unexpected exceptions."""
    
    correlation_id = getattr(request.state, 'correlation_id', 'unknown')
    
    # Log the full exception with traceback
    logger.error(
        f"Unhandled exception: {type(exc).__name__} - {str(exc)} "
        f"- Correlation ID: {correlation_id}",
        exc_info=True,
        extra={
            "correlation_id": correlation_id,
            "exception_type": type(exc).__name__,
            "traceback": traceback.format_exc()
        }
    )
    
    response_content = {
        "error": "INTERNAL_SERVER_ERROR",
        "message": "An unexpected error occurred",
        "correlation_id": correlation_id,
        "details": {}
    }
    
    return JSONResponse(
        status_code=500,
        content=response_content
    )


async def http_exception_handler_custom(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions with correlation ID."""
    
    correlation_id = getattr(request.state, 'correlation_id', 'unknown')
    
    # Log HTTP exceptions
    logger.warning(
        f"HTTP Exception: {exc.status_code} - {exc.detail} "
        f"- Correlation ID: {correlation_id}",
        extra={
            "correlation_id": correlation_id,
            "status_code": exc.status_code,
            "detail": exc.detail
        }
    )
    
    response_content = {
        "error": f"HTTP_{exc.status_code}",
        "message": exc.detail,
        "correlation_id": correlation_id,
        "details": {}
    }
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response_content
    )


async def validation_exception_handler_custom(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle request validation errors with correlation ID."""
    
    correlation_id = getattr(request.state, 'correlation_id', 'unknown')
    
    # Extract validation errors
    validation_errors = []
    for error in exc.errors():
        validation_errors.append({
            "field": " -> ".join(str(x) for x in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    
    # Log validation errors
    logger.warning(
        f"Validation Error: {len(validation_errors)} field(s) failed validation "
        f"- Correlation ID: {correlation_id}",
        extra={
            "correlation_id": correlation_id,
            "validation_errors": validation_errors
        }
    )
    
    response_content = {
        "error": "VALIDATION_ERROR",
        "message": "Request validation failed",
        "correlation_id": correlation_id,
        "details": {
            "validation_errors": validation_errors
        }
    }
    
    return JSONResponse(
        status_code=422,
        content=response_content
    )


def register_exception_handlers(app):
    """Register all exception handlers with the FastAPI app."""
    
    # Custom exception handlers
    app.add_exception_handler(EliteDynamicsException, elite_dynamics_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler_custom)
    app.add_exception_handler(RequestValidationError, validation_exception_handler_custom)
    app.add_exception_handler(Exception, general_exception_handler)
    
    logger.info("Exception handlers registered successfully")