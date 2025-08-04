# app/middleware/cors.py
"""
CORS middleware with enterprise-level security configurations.
"""

from typing import List, Union
from fastapi.middleware.cors import CORSMiddleware as FastAPICORSMiddleware

class CORSMiddleware:
    """
    Enhanced CORS configuration for enterprise security.
    """
    
    @staticmethod
    def get_middleware_config(environment: str = "development") -> dict:
        """
        Get CORS configuration based on environment.
        
        Args:
            environment: The deployment environment (development, staging, production)
            
        Returns:
            Dictionary with CORS configuration
        """
        
        if environment == "production":
            return {
                "allow_origins": [
                    "https://elitecosmeticdental.com",
                    "https://app.elitecosmeticdental.com", 
                    "https://admin.elitecosmeticdental.com"
                ],
                "allow_credentials": True,
                "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                "allow_headers": [
                    "Accept",
                    "Accept-Language",
                    "Content-Language",
                    "Content-Type",
                    "Authorization",
                    "X-Requested-With",
                    "X-API-Key",
                    "X-Correlation-ID"
                ],
                "expose_headers": [
                    "X-Correlation-ID",
                    "X-API-Version",
                    "X-Rate-Limit-Remaining",
                    "X-Rate-Limit-Reset"
                ],
                "max_age": 3600  # 1 hour
            }
        
        elif environment == "staging":
            return {
                "allow_origins": [
                    "https://staging.elitecosmeticdental.com",
                    "https://test.elitecosmeticdental.com",
                    "http://localhost:3000",
                    "http://localhost:8080"
                ],
                "allow_credentials": True,
                "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
                "allow_headers": [
                    "Accept",
                    "Accept-Language",
                    "Content-Language",
                    "Content-Type",
                    "Authorization",
                    "X-Requested-With",
                    "X-API-Key",
                    "X-Correlation-ID",
                    "X-Debug"
                ],
                "expose_headers": [
                    "X-Correlation-ID",
                    "X-API-Version",
                    "X-Rate-Limit-Remaining",
                    "X-Rate-Limit-Reset",
                    "X-Debug"
                ],
                "max_age": 3600
            }
        
        else:  # development
            return {
                "allow_origins": ["*"],  # Allow all origins in development
                "allow_credentials": True,
                "allow_methods": ["*"],  # Allow all methods
                "allow_headers": ["*"],  # Allow all headers
                "expose_headers": [
                    "X-Correlation-ID",
                    "X-API-Version",
                    "X-Rate-Limit-Remaining",
                    "X-Rate-Limit-Reset"
                ],
                "max_age": 600  # 10 minutes for faster development
            }
    
    @staticmethod
    def create_cors_middleware(environment: str = "development") -> FastAPICORSMiddleware:
        """
        Create and configure CORS middleware.
        
        Args:
            environment: The deployment environment
            
        Returns:
            Configured FastAPI CORS middleware
        """
        config = CORSMiddleware.get_middleware_config(environment)
        
        return FastAPICORSMiddleware(
            **config
        )