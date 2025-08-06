from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
import json
import time
import uuid
from datetime import datetime
import logging
from app.core.v3.audit_manager import audit_manager
from app.core.v3.event_bus import event_bus
from app.actions import sharepoint_actions
from app.core.config import settings

logger = logging.getLogger(__name__)

class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware que audita todas las requests y maneja respuestas grandes
    """
    
    def __init__(self, app):
        super().__init__(app)
        self.max_response_size = 2 * 1024 * 1024  # 2MB
        
    async def dispatch(self, request: Request, call_next):
        # Generar ID único para la request
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Agregar request_id a los headers para trazabilidad
        request.state.request_id = request_id
        
        # Log inicio solo para endpoints importantes
        if self._should_audit_endpoint(request.url.path):
            await self._log_request_start(request, request_id)
        
        try:
            # Ejecutar request
            response = await call_next(request)
            
            # Calcular duración
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Procesar respuesta si es necesario
            if self._should_process_response(request.url.path):
                response = await self._process_response(
                    request, response, request_id, duration_ms
                )
            
            return response
            
        except Exception as e:
            logger.error(f"Error en request {request_id}: {str(e)}")
            
            # Emitir evento de error
            await event_bus.emit(
                "request.error",
                "audit_middleware",
                {
                    "request_id": request_id,
                    "path": str(request.url.path),
                    "error": str(e)
                }
            )
            
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "error": "Internal server error",
                    "request_id": request_id
                }
            )
    
    def _should_audit_endpoint(self, path: str) -> bool:
        """Determina si el endpoint debe ser auditado"""
        # Auditar solo endpoints importantes
        audit_paths = ["/api/v1/orchestrate", "/api/v1/dynamics", "/api/v1/execute"]
        return any(path.startswith(p) for p in audit_paths)
    
    def _should_process_response(self, path: str) -> bool:
        """Determina si la respuesta debe ser procesada"""
        # No procesar health checks, docs, etc.
        skip_paths = ["/health", "/docs", "/openapi.json", "/favicon.ico"]
        return not any(path.startswith(p) for p in skip_paths)
    
    async def _log_request_start(self, request: Request, request_id: str):
        """Log el inicio de la request"""
        try:
            # Obtener body si existe
            body = None
            if request.method in ["POST", "PUT", "PATCH"]:
                body = await request.body()
                # Resetear el body para que pueda ser leído nuevamente
                request._body = body
                body = body.decode("utf-8") if body else None
            
            # Emitir evento
            await event_bus.emit(
                "request.started",
                "audit_middleware",
                {
                    "request_id": request_id,
                    "method": request.method,
                    "path": str(request.url.path),
                    "query": str(request.url.query),
                    "body_preview": body[:500] if body else None
                }
            )
        except Exception as e:
            logger.error(f"Error logging request start: {e}")
    
    async def _process_response(
        self, 
        request: Request, 
        response: Response, 
        request_id: str,
        duration_ms: int
    ) -> Response:
        """Procesa la respuesta, maneja respuestas grandes"""
        try:
            # Si no es JSON, devolver tal cual
            if not response.headers.get("content-type", "").startswith("application/json"):
                return response
            
            # Leer el body
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            
            # Si es muy grande, guardar en SharePoint
            if len(body) > self.max_response_size:
                logger.info(f"Respuesta grande detectada: {len(body)} bytes")
                
                # Guardar en SharePoint
                file_name = f"large_response_{request_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                
                try:
                    auth_client = get_auth_client()
                    upload_result = await sharepoint_actions.upload_document(auth_client, {
                        "file_content": body,
                        "file_name": file_name,
                        "folder_path": getattr(settings, "SHAREPOINT_ELITE_GENERAL_PATH", "/General"),
                        "content_type": "application/json"
                    })
                    
                    if upload_result.get("status") == "success":
                        # Crear respuesta con referencia
                        new_response = {
                            "status": "success_large_response",
                            "message": f"Respuesta grande guardada automáticamente ({len(body)} bytes)",
                            "data": {
                                "summary": {
                                    "request_id": request_id,
                                    "original_size": len(body),
                                    "saved_to": "SharePoint",
                                    "file_name": file_name
                                },
                                "access": {
                                    "web_url": upload_result["data"].get("webUrl"),
                                    "download_url": upload_result["data"].get("@microsoft.graph.downloadUrl")
                                }
                            },
                            "duration_ms": duration_ms
                        }
                        
                        # Emitir evento
                        await event_bus.emit(
                            "response.large_saved",
                            "audit_middleware",
                            {
                                "request_id": request_id,
                                "size_bytes": len(body),
                                "file_url": upload_result["data"].get("webUrl")
                            }
                        )
                        
                        return JSONResponse(content=new_response)
                    
                except Exception as e:
                    logger.error(f"Error guardando respuesta grande: {e}")
            
            # Si no es grande, devolver normal pero con headers adicionales
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Duration-MS"] = str(duration_ms)
            
            # Recrear la respuesta con el body original
            return Response(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type
            )
            
        except Exception as e:
            logger.error(f"Error procesando respuesta: {e}")
            return response

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware para agregar headers de seguridad
    """
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Agregar headers de seguridad
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response
