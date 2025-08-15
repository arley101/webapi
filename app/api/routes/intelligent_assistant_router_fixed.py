"""
Router del Asistente de IA Inteligente (Fixed)
Versión copiada desde el backup para reemplazar el placeholder vacío.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional
import logging

from app.core.auth_manager import get_current_user, AuthenticatedUser
from app.core.action_mapper import get_action
from app.shared.constants import SUCCESS_RESPONSE, ERROR_RESPONSE
from app.shared.helpers.response_helpers import create_success_response, create_error_response

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Intelligent AI Assistant"])  # Sin prefix aquí, se agrega en main.py


@router.post("/session/start")
async def start_intelligent_session(
    request_data: Dict[str, Any],
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    try:
        action_func = get_action("start_intelligent_session")
        if not action_func:
            raise HTTPException(status_code=500, detail="Acción no encontrada")
        result = await action_func(current_user, request_data)
        if result.get("success"):
            return create_success_response(data=result, message="Sesión inteligente iniciada exitosamente")
        else:
            return create_error_response(error=result.get("error", "Error iniciando sesión"), status_code=400)
    except Exception as e:
        logger.error(f"Error en start_intelligent_session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/session/process-query")
async def process_intelligent_query(
    request_data: Dict[str, Any],
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    try:
        action_func = get_action("process_intelligent_query")
        if not action_func:
            raise HTTPException(status_code=500, detail="Acción no encontrada")
        result = await action_func(current_user, request_data)
        if result.get("success"):
            return create_success_response(data=result, message="Consulta procesada con contexto inteligente")
        else:
            return create_error_response(error=result.get("error", "Error procesando consulta"), status_code=400)
    except Exception as e:
        logger.error(f"Error en process_intelligent_query: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/feedback/submit")
async def submit_user_feedback(
    request_data: Dict[str, Any],
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    try:
        action_func = get_action("submit_user_feedback")
        if not action_func:
            raise HTTPException(status_code=500, detail="Acción no encontrada")
        result = await action_func(current_user, request_data)
        if result.get("success"):
            return create_success_response(data=result, message="Feedback procesado y aprendizaje actualizado")
        else:
            return create_error_response(error=result.get("error", "Error procesando feedback"), status_code=400)
    except Exception as e:
        logger.error(f"Error en submit_user_feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/profile/intelligence")
async def get_user_intelligence_profile(
    user_id: Optional[str] = None, current_user: AuthenticatedUser = Depends(get_current_user)
):
    try:
        action_func = get_action("get_user_intelligence_profile")
        if not action_func:
            raise HTTPException(status_code=500, detail="Acción no encontrada")
        request_data = {"user_id": user_id} if user_id else {}
        result = await action_func(current_user, request_data)
        if result.get("success"):
            return create_success_response(data=result, message="Perfil de inteligencia obtenido exitosamente")
        else:
            return create_error_response(error=result.get("error", "Error obteniendo perfil"), status_code=400)
    except Exception as e:
        logger.error(f"Error en get_user_intelligence_profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/session/end")
async def end_intelligent_session(
    request_data: Dict[str, Any], current_user: AuthenticatedUser = Depends(get_current_user)
):
    try:
        action_func = get_action("end_intelligent_session")
        if not action_func:
            raise HTTPException(status_code=500, detail="Acción no encontrada")
        result = await action_func(current_user, request_data)
        if result.get("success"):
            return create_success_response(data=result, message="Sesión finalizada con aprendizaje actualizado")
        else:
            return create_error_response(error=result.get("error", "Error finalizando sesión"), status_code=400)
    except Exception as e:
        logger.error(f"Error en end_intelligent_session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/files/upload")
async def upload_file_intelligently(
    request_data: Dict[str, Any], current_user: AuthenticatedUser = Depends(get_current_user)
):
    try:
        action_func = get_action("upload_file_intelligently")
        if not action_func:
            raise HTTPException(status_code=500, detail="Acción no encontrada")
        result = await action_func(current_user, request_data)
        if result.get("success"):
            return create_success_response(data=result, message="Archivo procesado y guardado inteligentemente")
        else:
            return create_error_response(error=result.get("error", "Error procesando archivo"), status_code=400)
    except Exception as e:
        logger.error(f"Error en upload_file_intelligently: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files/search")
async def search_files_intelligently(
    query: str,
    file_type: Optional[str] = None,
    category: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    try:
        action_func = get_action("search_files_intelligently")
        if not action_func:
            raise HTTPException(status_code=500, detail="Acción no encontrada")
        filters = {}
        if file_type:
            filters["file_type"] = file_type
        if category:
            filters["category"] = category
        if date_from:
            filters["date_from"] = date_from
        if date_to:
            filters["date_to"] = date_to

        request_data = {"query": query, "filters": filters}
        result = await action_func(current_user, request_data)
        if result.get("success"):
            return create_success_response(data=result, message="Búsqueda inteligente completada")
        else:
            return create_error_response(error=result.get("error", "Error en búsqueda"), status_code=400)
    except Exception as e:
        logger.error(f"Error en search_files_intelligently: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/conversations")
async def get_conversation_history(
    user_id: Optional[str] = None,
    days_back: int = 30,
    limit: int = 10,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    try:
        action_func = get_action("get_conversation_history")
        if not action_func:
            raise HTTPException(status_code=500, detail="Acción no encontrada")
        request_data = {"user_id": user_id, "days_back": days_back, "limit": limit}
        result = await action_func(current_user, request_data)
        if result.get("success"):
            return create_success_response(data=result, message="Historial de conversaciones obtenido")
        else:
            return create_error_response(error=result.get("error", "Error obteniendo historial"), status_code=400)
    except Exception as e:
        logger.error(f"Error en get_conversation_history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/behavior-patterns")
async def analyze_user_behavior_patterns(
    user_id: Optional[str] = None, analysis_type: str = "comprehensive", current_user: AuthenticatedUser = Depends(get_current_user)
):
    try:
        action_func = get_action("analyze_user_behavior_patterns")
        if not action_func:
            raise HTTPException(status_code=500, detail="Acción no encontrada")
        request_data = {"user_id": user_id, "analysis_type": analysis_type}
        result = await action_func(current_user, request_data)
        if result.get("success"):
            return create_success_response(data=result, message="Análisis de patrones completado")
        else:
            return create_error_response(error=result.get("error", "Error analizando patrones"), status_code=400)
    except Exception as e:
        logger.error(f"Error en analyze_user_behavior_patterns: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/learning/insights")
async def get_learning_insights(user_id: Optional[str] = None, current_user: AuthenticatedUser = Depends(get_current_user)):
    try:
        action_func = get_action("get_learning_insights")
        if not action_func:
            raise HTTPException(status_code=500, detail="Acción no encontrada")
        request_data = {"user_id": user_id} if user_id else {}
        result = await action_func(current_user, request_data)
        if result.get("success"):
            return create_success_response(data=result, message="Insights de aprendizaje obtenidos")
        else:
            return create_error_response(error=result.get("error", "Error obteniendo insights"), status_code=400)
    except Exception as e:
        logger.error(f"Error en get_learning_insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_intelligent_assistant_status():
    try:
        status = {
            "intelligent_assistant": "active",
            "learning_engine": "active",
            "conversational_memory": "active",
            "file_manager": "active",
            "total_actions": 10,
            "last_update": "2025-08-13T19:45:00Z",
            "version": "1.0.0",
        }
        return create_success_response(data=status, message="Sistema de asistente inteligente operativo")
    except Exception as e:
        logger.error(f"Error en get_intelligent_assistant_status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
