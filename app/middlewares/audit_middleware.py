# app/middlewares/audit_middleware.py
"""
Task 1.3: Middleware for Auditing and Atomic Saving

This middleware intercepts all action calls to provide:
1. Auditing: Log action, parameters, author, timestamp, and result
2. Atomic Saving: Auto-save large responses to OneDrive/SharePoint
3. Error handling and response size management
"""

import json
import logging
import hashlib
import asyncio
from typing import Any, Dict, Optional, Tuple, List
from datetime import datetime
import sys

from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.event_bus import event_bus, EventType
from app.core.state_manager import state_manager

logger = logging.getLogger(__name__)

class AuditMiddleware(BaseHTTPMiddleware):
    """Middleware for auditing actions and managing large responses"""
    
    def __init__(self, app):
        super().__init__(app)
        self.enabled = settings.AUDIT_ENABLED
        self.size_threshold_bytes = int(settings.RESPONSE_SIZE_THRESHOLD_MB * 1024 * 1024)
        self.auto_save_enabled = settings.AUTO_SAVE_LARGE_RESPONSES
        
    async def dispatch(self, request: Request, call_next) -> Response:
        """Main middleware dispatch method"""
        
        if not self._should_audit(request):
            return await call_next(request)
        
        # Extract request information
        request_info = await self._extract_request_info(request)
        start_time = datetime.now()
        
        try:
            # Process the request
            response = await call_next(request)
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Handle the response
            return await self._handle_response(
                request, response, request_info, processing_time, start_time
            )
            
        except Exception as e:
            # Handle errors
            await self._audit_error(request_info, str(e), start_time)
            raise
    
    def _should_audit(self, request: Request) -> bool:
        """Determine if request should be audited"""
        if not self.enabled:
            return False
            
        # Only audit API endpoints, not health checks or docs
        path = request.url.path
        if path in ["/", "/health", "/api/v1/health", "/api/v1/docs", "/api/v1/redoc"]:
            return False
            
        # Only audit dynamic actions endpoint
        if not path.startswith("/api/v1/dynamics"):
            return False
            
        return True
    
    async def _extract_request_info(self, request: Request) -> Dict[str, Any]:
        """Extract relevant information from the request"""
        try:
            # Read request body
            body = await request.body()
            request_data = {}
            
            if body:
                try:
                    request_data = json.loads(body.decode())
                except json.JSONDecodeError:
                    request_data = {"raw_body": body.decode()[:1000]}  # Truncate large bodies
            
            # Extract headers (excluding sensitive ones)
            headers = dict(request.headers)
            sensitive_headers = ["authorization", "x-api-key", "cookie"]
            for header in sensitive_headers:
                if header in headers:
                    headers[header] = "[REDACTED]"
            
            return {
                "method": request.method,
                "url": str(request.url),
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "headers": headers,
                "client_ip": request.client.host if request.client else None,
                "request_data": request_data,
                "user_agent": headers.get("user-agent", ""),
                "action_name": request_data.get("action", "unknown"),
                "action_params": request_data.get("params", {}),
                "mode": request_data.get("mode", "suggestion"),
                "execution_mode": request_data.get("execution", False)
            }
            
        except Exception as e:
            logger.error(f"Error extracting request info: {e}")
            return {
                "method": request.method,
                "path": request.url.path,
                "error": "Failed to extract request info"
            }
    
    async def _handle_response(self, request: Request, response: Response, 
                              request_info: Dict[str, Any], processing_time: float,
                              start_time: datetime) -> Response:
        """Handle the response and perform auditing/saving"""
        
        try:
            # Get response body
            response_body = None
            response_size = 0
            
            if hasattr(response, 'body'):
                response_body = response.body
                response_size = len(response_body) if response_body else 0
            
            # Check if response is too large
            if response_size > self.size_threshold_bytes and self.auto_save_enabled:
                return await self._handle_large_response(
                    request, response, request_info, response_body, processing_time, start_time
                )
            
            # Audit the successful response
            await self._audit_success(
                request_info, response.status_code, response_size, processing_time, start_time
            )
            
            # Emit success event
            await self._emit_action_event(
                request_info, "success", response.status_code, response_size, processing_time
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error handling response: {e}")
            await self._audit_error(request_info, str(e), start_time)
            return response
    
    async def _handle_large_response(self, request: Request, response: Response,
                                    request_info: Dict[str, Any], response_body: bytes,
                                    processing_time: float, start_time: datetime) -> Response:
        """Handle large responses by saving to OneDrive/SharePoint"""
        
        try:
            # Generate file name
            action_name = request_info.get("action_name", "unknown")
            timestamp = start_time.strftime("%Y%m%d_%H%M%S")
            file_name = f"{action_name}_result_{timestamp}.json"
            
            # Save to OneDrive/SharePoint (placeholder for now)
            file_url = await self._save_large_response(file_name, response_body)
            
            if file_url:
                # Create new response with just the URL
                new_response_data = {
                    "success": True,
                    "message": f"Response too large ({len(response_body)} bytes), saved to file",
                    "file_url": file_url,
                    "file_name": file_name,
                    "original_size_bytes": len(response_body),
                    "action": action_name,
                    "timestamp": start_time.isoformat()
                }
                
                # Audit the file save
                await self._audit_file_save(
                    request_info, file_url, len(response_body), processing_time, start_time
                )
                
                # Emit file created event
                await event_bus.emit_file_created(
                    source="audit_middleware",
                    file_id=file_name,
                    file_name=file_name,
                    file_url=file_url,
                    session_id=request_info.get("session_id"),
                    user_id=request_info.get("user_id")
                )
                
                return JSONResponse(
                    content=new_response_data,
                    status_code=200,
                    headers={"X-Large-Response-Saved": "true"}
                )
            else:
                # Failed to save, return original response with warning
                logger.warning(f"Failed to save large response for action {action_name}")
                await self._audit_warning(
                    request_info, "Failed to save large response", start_time
                )
                
                return response
                
        except Exception as e:
            logger.error(f"Error handling large response: {e}")
            await self._audit_error(request_info, f"Large response handling failed: {e}", start_time)
            return response
    
    async def _save_large_response(self, file_name: str, response_body: bytes) -> Optional[str]:
        """Save large response to OneDrive/SharePoint"""
        
        try:
            # For now, simulate saving to OneDrive
            # In a real implementation, this would use the OneDrive API
            
            # Store in state manager temporarily
            await state_manager.set_state(
                f"large_response:{file_name}",
                {
                    "file_name": file_name,
                    "content": response_body.decode('utf-8', errors='ignore')[:10000],  # Truncate for storage
                    "full_size": len(response_body),
                    "saved_at": datetime.now().isoformat()
                },
                ttl_seconds=86400  # 24 hours
            )
            
            # Return a simulated URL
            return f"https://onedrive.sharepoint.com/files/{file_name}"
            
        except Exception as e:
            logger.error(f"Failed to save large response {file_name}: {e}")
            return None
    
    async def _audit_success(self, request_info: Dict[str, Any], status_code: int,
                            response_size: int, processing_time: float, start_time: datetime) -> None:
        """Audit successful request"""
        
        audit_record = {
            "audit_type": "action_success",
            "timestamp": start_time.isoformat(),
            "action_name": request_info.get("action_name"),
            "action_params": request_info.get("action_params"),
            "method": request_info.get("method"),
            "path": request_info.get("path"),
            "status_code": status_code,
            "response_size_bytes": response_size,
            "processing_time_seconds": processing_time,
            "client_ip": request_info.get("client_ip"),
            "user_agent": request_info.get("user_agent"),
            "execution_mode": request_info.get("execution_mode"),
            "mode": request_info.get("mode")
        }
        
        await self._store_audit_record(audit_record)
        logger.info(f"AUDIT SUCCESS: {request_info.get('action_name')} - {status_code} - {processing_time:.3f}s")
    
    async def _audit_error(self, request_info: Dict[str, Any], error: str, start_time: datetime) -> None:
        """Audit failed request"""
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        audit_record = {
            "audit_type": "action_error",
            "timestamp": start_time.isoformat(),
            "action_name": request_info.get("action_name"),
            "action_params": request_info.get("action_params"),
            "method": request_info.get("method"),
            "path": request_info.get("path"),
            "error": error,
            "processing_time_seconds": processing_time,
            "client_ip": request_info.get("client_ip"),
            "user_agent": request_info.get("user_agent"),
            "execution_mode": request_info.get("execution_mode"),
            "mode": request_info.get("mode")
        }
        
        await self._store_audit_record(audit_record)
        logger.error(f"AUDIT ERROR: {request_info.get('action_name')} - {error}")
        
        # Emit error event
        await event_bus.emit_action_failed(
            source="audit_middleware",
            action_name=request_info.get("action_name", "unknown"),
            action_params=request_info.get("action_params", {}),
            error=error
        )
    
    async def _audit_warning(self, request_info: Dict[str, Any], warning: str, start_time: datetime) -> None:
        """Audit warning"""
        
        audit_record = {
            "audit_type": "action_warning",
            "timestamp": start_time.isoformat(),
            "action_name": request_info.get("action_name"),
            "warning": warning,
            "client_ip": request_info.get("client_ip")
        }
        
        await self._store_audit_record(audit_record)
        logger.warning(f"AUDIT WARNING: {request_info.get('action_name')} - {warning}")
    
    async def _audit_file_save(self, request_info: Dict[str, Any], file_url: str,
                              original_size: int, processing_time: float, start_time: datetime) -> None:
        """Audit file save operation"""
        
        audit_record = {
            "audit_type": "large_response_saved",
            "timestamp": start_time.isoformat(),
            "action_name": request_info.get("action_name"),
            "file_url": file_url,
            "original_size_bytes": original_size,
            "processing_time_seconds": processing_time,
            "client_ip": request_info.get("client_ip")
        }
        
        await self._store_audit_record(audit_record)
        logger.info(f"AUDIT FILE SAVE: {request_info.get('action_name')} - {file_url} - {original_size} bytes")
    
    async def _store_audit_record(self, audit_record: Dict[str, Any]) -> None:
        """Store audit record in state manager"""
        
        try:
            # Generate audit ID
            audit_id = f"audit_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
            
            # Store in state manager
            await state_manager.set_state(
                f"audit:{audit_id}",
                audit_record,
                ttl_seconds=2592000  # 30 days
            )
            
        except Exception as e:
            logger.error(f"Failed to store audit record: {e}")
    
    async def _emit_action_event(self, request_info: Dict[str, Any], result_type: str,
                               status_code: int, response_size: int, processing_time: float) -> None:
        """Emit action completion event"""
        
        try:
            if result_type == "success":
                await event_bus.emit_action_completed(
                    source="audit_middleware",
                    action_name=request_info.get("action_name", "unknown"),
                    action_params=request_info.get("action_params", {}),
                    action_result={
                        "status_code": status_code,
                        "response_size_bytes": response_size,
                        "processing_time_seconds": processing_time
                    }
                )
            
        except Exception as e:
            logger.error(f"Failed to emit action event: {e}")


# Utility functions for audit querying

async def get_audit_records(action_name: Optional[str] = None, 
                           limit: int = 100) -> List[Dict[str, Any]]:
    """Get audit records from state manager"""
    
    try:
        # This is a simplified implementation
        # In production, you'd want more sophisticated querying
        records = []
        
        # For now, return empty list as we'd need to implement
        # pattern matching in the state manager
        return records
        
    except Exception as e:
        logger.error(f"Failed to get audit records: {e}")
        return []

async def get_audit_summary(start_date: Optional[datetime] = None,
                           end_date: Optional[datetime] = None) -> Dict[str, Any]:
    """Get audit summary statistics"""
    
    try:
        # This would be implemented with proper analytics
        # For now, return basic structure
        return {
            "total_actions": 0,
            "successful_actions": 0,
            "failed_actions": 0,
            "large_responses_saved": 0,
            "average_processing_time": 0.0,
            "most_used_actions": [],
            "error_rate": 0.0
        }
        
    except Exception as e:
        logger.error(f"Failed to get audit summary: {e}")
        return {}