# app/api/routes/intelligent_assistant_router.py
"""
Router del Asistente de IA Inteligente - VERSIÓN COMPLETA
Endpoints específicos para las funcionalidades avanzadas del asistente
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional, List
import logging

from app.core.auth_manager import get_current_user, AuthenticatedUser
from app.core.action_mapper import get_action
from app.shared.constants import SUCCESS_RESPONSE, ERROR_RESPONSE
from app.shared.helpers.response_helpers import create_success_response, create_error_response

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Intelligent AI Assistant"])

@router.post("/session/start")
async def start_intelligent_session(
    request_data: Dict[str, Any],
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    🚀 Inicia una sesión inteligente del asistente con análisis de patrones
    """
    try:
        action_func = get_action("start_intelligent_session")
        if not action_func:
            raise HTTPException(status_code=500, detail="Acción no encontrada")
        
        result = await action_func(current_user, request_data)
        
        if result.get("success"):
            return create_success_response(
                data=result,
                message="Sesión inteligente iniciada exitosamente"
            )
        else:
            return create_error_response(
                error=result.get("error", "Error iniciando sesión"),
                status_code=400
            )
            
    except Exception as e:
        logger.error(f"Error en start_intelligent_session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat")
async def intelligent_chat(
    request_data: Dict[str, Any],
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    💬 Chat inteligente con contexto y aprendizaje
    """
    try:
        action_func = get_action("process_intelligent_query")
        if not action_func:
            raise HTTPException(status_code=500, detail="Acción no encontrada")
        
        result = await action_func(current_user, request_data)
        
        if result.get("success"):
            return create_success_response(
                data=result,
                message="Chat procesado con inteligencia"
            )
        else:
            return create_error_response(
                error=result.get("error", "Error en chat"),
                status_code=400
            )
            
    except Exception as e:
        logger.error(f"Error en intelligent_chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/learn")
async def learn_from_feedback(
    request_data: Dict[str, Any],
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    🧠 Aprendizaje del sistema basado en feedback
    """
    try:
        action_func = get_action("submit_user_feedback")
        if not action_func:
            raise HTTPException(status_code=500, detail="Acción no encontrada")
        
        result = await action_func(current_user, request_data)
        
        if result.get("success"):
            return create_success_response(
                data=result,
                message="Aprendizaje actualizado"
            )
        else:
            return create_error_response(
                error=result.get("error", "Error en aprendizaje"),
                status_code=400
            )
            
    except Exception as e:
        logger.error(f"Error en learn_from_feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze")
async def analyze_patterns(
    request_data: Dict[str, Any],
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    📊 Análisis de patrones de usuario
    """
    try:
        action_func = get_action("analyze_user_behavior_patterns")
        if not action_func:
            raise HTTPException(status_code=500, detail="Acción no encontrada")
        
        result = await action_func(current_user, request_data)
        
        if result.get("success"):
            return create_success_response(
                data=result,
                message="Análisis completado"
            )
        else:
            return create_error_response(
                error=result.get("error", "Error en análisis"),
                status_code=400
            )
            
    except Exception as e:
        logger.error(f"Error en analyze_patterns: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/profile/intelligence")
async def get_user_intelligence_profile(
    user_id: Optional[str] = None,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    👤 Obtiene el perfil de inteligencia del usuario
    """
    try:
        params = {"user_id": user_id or current_user.user_id}
        action_func = get_action("get_user_intelligence_profile")
        if not action_func:
            raise HTTPException(status_code=500, detail="Acción no encontrada")
        
        result = await action_func(current_user, params)
        
        if result.get("success"):
            return create_success_response(
                data=result,
                message="Perfil de inteligencia obtenido"
            )
        else:
            return create_error_response(
                error=result.get("error", "Error obteniendo perfil"),
                status_code=400
            )
            
    except Exception as e:
        logger.error(f"Error en get_user_intelligence_profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/session/end")
async def end_intelligent_session(
    request_data: Dict[str, Any],
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    🏁 Finaliza una sesión inteligente con evaluación
    """
    try:
        action_func = get_action("end_intelligent_session")
        if not action_func:
            raise HTTPException(status_code=500, detail="Acción no encontrada")
        
        result = await action_func(current_user, request_data)
        
        if result.get("success"):
            return create_success_response(
                data=result,
                message="Sesión finalizada exitosamente"
            )
        else:
            return create_error_response(
                error=result.get("error", "Error finalizando sesión"),
                status_code=400
            )
            
    except Exception as e:
        logger.error(f"Error en end_intelligent_session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def intelligent_assistant_health():
    """
    ❤️ Health check del asistente inteligente
    """
    try:
        return {
            "status": "healthy",
            "service": "intelligent_assistant",
            "endpoints": [
                "/session/start",
                "/chat", 
                "/learn",
                "/analyze",
                "/profile/intelligence",
                "/session/end"
            ],
            "features": [
                "Memoria persistente",
                "Análisis de patrones",
                "Aprendizaje automático",
                "Sugerencias personalizadas"
            ]
        }
    except Exception as e:
        logger.error(f"Error en health check: {e}")
        raise HTTPException(status_code=500, detail=str(e))
