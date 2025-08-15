# app/api/routes/intelligent_assistant_router.py
"""
Router del Asistente de IA Inteligente
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
router = APIRouter(tags=["Intelligent AI Assistant"])  # Sin prefix aquí, se agrega en main.py

@router.post("/session/start")
async def start_intelligent_session(
    request_data: Dict[str, Any],
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    🚀 Inicia una sesión inteligente del asistente con análisis de patrones
    
    Body:
    - user_id (opcional): ID del usuario
    - context (opcional): Contexto inicial de la sesión
    
    Returns:
    - session_id: ID de la nueva sesión
    - user_analysis: Análisis de patrones del usuario
    - personalized_suggestions: Sugerencias personalizadas
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

@router.post("/session/process-query")
async def process_intelligent_query(
    request_data: Dict[str, Any],
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    🧠 Procesa una consulta con inteligencia contextual
    
    Body:
    - session_id: ID de la sesión activa
    - message: Mensaje del usuario
    - action_executed (opcional): Acción ejecutada
    - assistant_response (opcional): Respuesta del asistente
    - context (opcional): Contexto adicional
    
    Returns:
    - turn_id: ID del turno de conversación
    - conversation_context: Contexto conversacional actualizado
    - updated_suggestions: Sugerencias actualizadas
    """
    try:
        action_func = get_action("process_intelligent_query")
        if not action_func:
            raise HTTPException(status_code=500, detail="Acción no encontrada")
        
        result = await action_func(current_user, request_data)
        
        if result.get("success"):
            return create_success_response(
                data=result,
                message="Consulta procesada con contexto inteligente"
            )
        else:
            return create_error_response(
                error=result.get("error", "Error procesando consulta"),
                status_code=400
            )
            
    except Exception as e:
        logger.error(f"Error en process_intelligent_query: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/feedback/submit")
async def submit_user_feedback(
    request_data: Dict[str, Any],
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    📝 Permite al usuario enviar feedback para mejorar el asistente
    
    Body:
    - interaction_id: ID de la interacción
    - feedback_type: Tipo de feedback (positive, negative, suggestion, correction)
    - rating (opcional): Calificación 1-5
    - comment (opcional): Comentario adicional
    - context (opcional): Contexto del feedback
    
    Returns:
    - feedback_id: ID del feedback procesado
    - learning_improvements: Mejoras en el aprendizaje
    """
    try:
        action_func = get_action("submit_user_feedback")
        if not action_func:
            raise HTTPException(status_code=500, detail="Acción no encontrada")
        
        result = await action_func(current_user, request_data)
        
        if result.get("success"):
            return create_success_response(
                data=result,
                message="Feedback procesado y aprendizaje actualizado"
            )
        else:
            return create_error_response(
                error=result.get("error", "Error procesando feedback"),
                status_code=400
            )
            
    except Exception as e:
        logger.error(f"Error en submit_user_feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/profile/intelligence")
async def get_user_intelligence_profile(
    user_id: Optional[str] = None,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    👤 Obtiene el perfil de inteligencia del usuario
    
    Query Parameters:
    - user_id (opcional): ID del usuario
    
    Returns:
    - user_profile: Perfil completo del usuario
    - learning_insights: Insights de aprendizaje
    - interaction_patterns: Patrones de interacción
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

@router.post("/chat")
async def intelligent_chat(
    request_data: Dict[str, Any],
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    💬 Chat inteligente con contexto y aprendizaje
    
    Body:
    - message: Mensaje del usuario
    - session_id: ID de la sesión
    - context (opcional): Contexto adicional
    
    Returns:
    - response: Respuesta del asistente
    - context_updates: Actualizaciones de contexto
    - suggestions: Sugerencias inteligentes
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
    
    Body:
    - user_id: ID del usuario
    - feedback: Feedback del usuario
    - context: Contexto del feedback
    
    Returns:
    - learning_update: Actualización del aprendizaje
    - improved_suggestions: Sugerencias mejoradas
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
    
    Body:
    - user_id: ID del usuario
    - action: Tipo de análisis
    
    Returns:
    - patterns: Patrones identificados
    - insights: Insights del análisis
    - recommendations: Recomendaciones
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
    
    Returns:
    - user_profile: Perfil completo del usuario con patrones y preferencias
    """
    try:
        action_func = get_action("get_user_intelligence_profile")
        if not action_func:
            raise HTTPException(status_code=500, detail="Acción no encontrada")
        
        request_data = {"user_id": user_id} if user_id else {}
        result = await action_func(current_user, request_data)
        
        if result.get("success"):
            return create_success_response(
                data=result,
                message="Perfil de inteligencia obtenido exitosamente"
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
    
    Body:
    - session_id: ID de la sesión a finalizar
    - satisfaction_score (opcional): Puntuación de satisfacción 1-5
    - feedback (opcional): Comentario final
    
    Returns:
    - session_summary: Resumen de la sesión
    - session_stats: Estadísticas de la sesión
    """
    try:
        action_func = get_action("end_intelligent_session")
        if not action_func:
            raise HTTPException(status_code=500, detail="Acción no encontrada")
        
        result = await action_func(current_user, request_data)
        
        if result.get("success"):
            return create_success_response(
                data=result,
                message="Sesión finalizada con aprendizaje actualizado"
            )
        else:
            return create_error_response(
                error=result.get("error", "Error finalizando sesión"),
                status_code=400
            )
            
    except Exception as e:
        logger.error(f"Error en end_intelligent_session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/files/upload")
async def upload_file_intelligently(
    request_data: Dict[str, Any],
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    📁 Sube y procesa un archivo con análisis e IA
    
    Body:
    - file_content: Contenido del archivo (base64)
    - file_name: Nombre del archivo
    - session_id (opcional): ID de la sesión
    - source (opcional): Origen del archivo
    - context (opcional): Contexto adicional
    
    Returns:
    - file_id: ID del archivo procesado
    - storage_locations: Ubicaciones donde se guardó
    - file_metadata: Metadatos del archivo
    """
    try:
        action_func = get_action("upload_file_intelligently")
        if not action_func:
            raise HTTPException(status_code=500, detail="Acción no encontrada")
        
        result = await action_func(current_user, request_data)
        
        if result.get("success"):
            return create_success_response(
                data=result,
                message="Archivo procesado y guardado inteligentemente"
            )
        else:
            return create_error_response(
                error=result.get("error", "Error procesando archivo"),
                status_code=400
            )
            
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
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    🔍 Busca archivos usando IA y análisis semántico
    
    Query Parameters:
    - query: Consulta de búsqueda
    - file_type (opcional): Tipo de archivo a buscar
    - category (opcional): Categoría de archivo
    - date_from (opcional): Fecha desde (ISO format)
    - date_to (opcional): Fecha hasta (ISO format)
    
    Returns:
    - files: Lista de archivos encontrados con relevancia
    """
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
        
        request_data = {
            "query": query,
            "filters": filters
        }
        
        result = await action_func(current_user, request_data)
        
        if result.get("success"):
            return create_success_response(
                data=result,
                message="Búsqueda inteligente completada"
            )
        else:
            return create_error_response(
                error=result.get("error", "Error en búsqueda"),
                status_code=400
            )
            
    except Exception as e:
        logger.error(f"Error en search_files_intelligently: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/conversations")
async def get_conversation_history(
    user_id: Optional[str] = None,
    days_back: int = 30,
    limit: int = 10,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    📚 Obtiene el historial de conversaciones del usuario
    
    Query Parameters:
    - user_id (opcional): ID del usuario
    - days_back: Días hacia atrás (default: 30)
    - limit: Límite de resultados (default: 10)
    
    Returns:
    - sessions: Lista de sesiones de conversación
    """
    try:
        action_func = get_action("get_conversation_history")
        if not action_func:
            raise HTTPException(status_code=500, detail="Acción no encontrada")
        
        request_data = {
            "user_id": user_id,
            "days_back": days_back,
            "limit": limit
        }
        
        result = await action_func(current_user, request_data)
        
        if result.get("success"):
            return create_success_response(
                data=result,
                message="Historial de conversaciones obtenido"
            )
        else:
            return create_error_response(
                error=result.get("error", "Error obteniendo historial"),
                status_code=400
            )
            
    except Exception as e:
        logger.error(f"Error en get_conversation_history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/behavior-patterns")
async def analyze_user_behavior_patterns(
    user_id: Optional[str] = None,
    analysis_type: str = "comprehensive",
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    📊 Analiza patrones de comportamiento detallados del usuario
    
    Query Parameters:
    - user_id (opcional): ID del usuario
    - analysis_type: Tipo de análisis (comprehensive, trends, preferences)
    
    Returns:
    - analysis: Análisis detallado de patrones
    - recommendations: Recomendaciones personalizadas
    """
    try:
        action_func = get_action("analyze_user_behavior_patterns")
        if not action_func:
            raise HTTPException(status_code=500, detail="Acción no encontrada")
        
        request_data = {
            "user_id": user_id,
            "analysis_type": analysis_type
        }
        
        result = await action_func(current_user, request_data)
        
        if result.get("success"):
            return create_success_response(
                data=result,
                message="Análisis de patrones completado"
            )
        else:
            return create_error_response(
                error=result.get("error", "Error analizando patrones"),
                status_code=400
            )
            
    except Exception as e:
        logger.error(f"Error en analyze_user_behavior_patterns: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/learning/insights")
async def get_learning_insights(
    user_id: Optional[str] = None,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    🧠 Obtiene insights del motor de aprendizaje
    
    Query Parameters:
    - user_id (opcional): ID del usuario
    
    Returns:
    - learning_insights: Insights del sistema de aprendizaje
    """
    try:
        action_func = get_action("get_learning_insights")
        if not action_func:
            raise HTTPException(status_code=500, detail="Acción no encontrada")
        
        request_data = {"user_id": user_id} if user_id else {}
        result = await action_func(current_user, request_data)
        
        if result.get("success"):
            return create_success_response(
                data=result,
                message="Insights de aprendizaje obtenidos"
            )
        else:
            return create_error_response(
                error=result.get("error", "Error obteniendo insights"),
                status_code=400
            )
            
    except Exception as e:
        logger.error(f"Error en get_learning_insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def get_intelligent_assistant_status():
    """
    ⚡ Estado del sistema de asistente inteligente
    
    Returns:
    - system_status: Estado de todos los módulos
    """
    try:
        status = {
            "intelligent_assistant": "active",
            "learning_engine": "active", 
            "conversational_memory": "active",
            "file_manager": "active",
            "total_actions": 10,
            "last_update": "2025-08-13T19:45:00Z",
            "version": "1.0.0"
        }
        
        return create_success_response(
            data=status,
            message="Sistema de asistente inteligente operativo"
        )
        
    except Exception as e:
        logger.error(f"Error en get_intelligent_assistant_status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
