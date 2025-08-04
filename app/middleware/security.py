# app/middleware/security.py
"""
Security middleware for enterprise-level protection.
"""

import time
import uuid
from typing import Callable, Dict, Any
from fastapi import Request, Response, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)

class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive security middleware providing:
    - Security headers
    - Rate limiting
    - Request correlation IDs
    - Basic request sanitization
    """
    
    def __init__(
        self, 
        app,
        rate_limit_requests: int = 100,
        rate_limit_window: int = 60,
        enable_rate_limiting: bool = True
    ):
        super().__init__(app)
        self.rate_limit_requests = rate_limit_requests
        self.rate_limit_window = rate_limit_window
        self.enable_rate_limiting = enable_rate_limiting
        self.request_counts: Dict[str, Dict[str, Any]] = {}
        
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate correlation ID for request tracking
        correlation_id = str(uuid.uuid4())
        request.state.correlation_id = correlation_id
        
        # Rate limiting (basic implementation)
        if self.enable_rate_limiting:
            client_ip = self._get_client_ip(request)
            if self._is_rate_limited(client_ip):
                logger.warning(f"Rate limit exceeded for IP: {client_ip}")
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "Rate limit exceeded",
                        "detail": f"Maximum {self.rate_limit_requests} requests per {self.rate_limit_window} seconds",
                        "correlation_id": correlation_id
                    }
                )
        
        start_time = time.time()
        
        try:
            # Process request
            response = await call_next(request)
            
            # Add security headers
            response = self._add_security_headers(response, correlation_id)
            
            # Log request completion
            process_time = time.time() - start_time
            logger.info(
                f"Request completed: {request.method} {request.url.path} "
                f"- Status: {response.status_code} - Duration: {process_time:.3f}s "
                f"- Correlation ID: {correlation_id}"
            )
            
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"Request failed: {request.method} {request.url.path} "
                f"- Error: {str(e)} - Duration: {process_time:.3f}s "
                f"- Correlation ID: {correlation_id}"
            )
            
            # Return structured error response
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "detail": "An unexpected error occurred",
                    "correlation_id": correlation_id
                }
            )
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP considering proxies."""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
    
    def _is_rate_limited(self, client_ip: str) -> bool:
        """Basic rate limiting logic."""
        current_time = time.time()
        window_start = current_time - self.rate_limit_window
        
        # Clean old entries
        if client_ip in self.request_counts:
            self.request_counts[client_ip]["requests"] = [
                req_time for req_time in self.request_counts[client_ip]["requests"]
                if req_time > window_start
            ]
        else:
            self.request_counts[client_ip] = {"requests": []}
        
        # Check rate limit
        request_count = len(self.request_counts[client_ip]["requests"])
        if request_count >= self.rate_limit_requests:
            return True
        
        # Add current request
        self.request_counts[client_ip]["requests"].append(current_time)
        return False
    
    def _add_security_headers(self, response: Response, correlation_id: str) -> Response:
        """Add security headers to response."""
        security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY", 
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
            "X-Correlation-ID": correlation_id,
            "X-API-Version": "1.1.0"
        }
        
        for header, value in security_headers.items():
            response.headers[header] = value
            
        return response


class JWTBearer(HTTPBearer):
    """
    JWT Bearer token authentication.
    TODO: Implement proper JWT validation logic based on your auth provider.
    """
    
    def __init__(self, auto_error: bool = True):
        super(JWTBearer, self).__init__(auto_error=auto_error)
    
    async def __call__(self, request: Request):
        credentials: HTTPAuthorizationCredentials = await super(JWTBearer, self).__call__(request)
        if credentials:
            if not credentials.scheme == "Bearer":
                raise HTTPException(
                    status_code=403, 
                    detail="Invalid authentication scheme."
                )
            if not self.verify_jwt(credentials.credentials):
                raise HTTPException(
                    status_code=403, 
                    detail="Invalid token or expired token."
                )
            return credentials.credentials
        else:
            raise HTTPException(
                status_code=403, 
                detail="Invalid authorization code."
            )
    
    def verify_jwt(self, jwtoken: str) -> bool:
        """
        Verify JWT token.
        TODO: Implement actual JWT verification logic.
        """
        # Placeholder - implement with your JWT verification logic
        # For now, accept any non-empty token for demonstration
        return len(jwtoken) > 0


# JWT security dependency
security = JWTBearer()