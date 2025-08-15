# app/api/routes/intelligent_assistant_router.py
"""
Router del Asistente de IA Inteligente - VERSIÓN LIMPIA
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
    """Inicia una sesión inteligente del asistente con análisis de patrones"""
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

@router.get("/status")
async def get_intelligent_assistant_status(
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Estado del sistema de asistente inteligente"""
    try:
        status = {
            "intelligent_assistant": "active",
            "learning_engine": "active", 
            "conversational_memory": "active",
            "file_manager": "active",
            "total_endpoints": 2,
            "version": "2.0"
        }
        
        return create_success_response(
            data=status,
            message="Sistema de asistente inteligente operativo"
        )
        
    except Exception as e:
        logger.error(f"Error en get_intelligent_assistant_status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
