# app/actions/intelligent_assistant_actions.py
"""
Acciones del Asistente de IA Inteligente
Funcionalidades expuestas como API endpoints:
- Análisis de patrones de usuario
- Procesamiento de feedback  
- Memoria conversacional
- Gestión inteligente de archivos
- Sugerencias personalizadas
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json

from app.core.auth_manager import AuthenticatedUser
from app.memory.intelligent_assistant import intelligent_assistant
from app.memory.learning_engine import learning_engine
from app.memory.conversational_memory import conversational_memory
from app.memory.intelligent_file_manager import intelligent_file_manager

logger = logging.getLogger(__name__)

async def start_intelligent_session(auth_user: AuthenticatedUser, params: Dict[str, Any]) -> Dict[str, Any]:
    """Inicia una sesión inteligente del asistente con contexto histórico"""
    try:
        user_id = params.get("user_id", auth_user.user_id)
        initial_context = params.get("context", {})
        
        # Analizar patrones del usuario
        logger.info(f"Analizando patrones para usuario: {user_id}")
        pattern_analysis = await intelligent_assistant.analyze_user_patterns(user_id)
        
        # Iniciar sesión conversacional
        session_id = await conversational_memory.start_conversation_session(
            user_id, initial_context
        )
        
        # Obtener sugerencias personalizadas
        suggestions = await learning_engine.get_personalized_suggestions(
            user_id, initial_context
        )
        
        return {
            "success": True,
            "session_id": session_id,
            "user_analysis": pattern_analysis.get("user_profile", {}),
            "personalized_suggestions": suggestions,
            "message": f"Sesión inteligente iniciada con análisis de {pattern_analysis.get('user_profile', {}).get('total_interactions', 0)} interacciones históricas"
        }
        
    except Exception as e:
        logger.error(f"Error iniciando sesión inteligente: {e}")
        return {"success": False, "error": str(e)}

async def process_intelligent_query(auth_user: AuthenticatedUser, params: Dict[str, Any]) -> Dict[str, Any]:
    """Procesa una consulta con inteligencia contextual"""
    try:
        session_id = params.get("session_id", "")
        user_message = params.get("message", "")
        action_executed = params.get("action_executed", "")
        assistant_response = params.get("assistant_response", "")
        context = params.get("context", {})
        
        if not session_id or not user_message:
            return {"success": False, "error": "session_id y message son requeridos"}
        
        # Obtener contexto conversacional actual
        conversation_context = await conversational_memory.get_conversation_context(session_id)
        
        # Añadir turno a la conversación
        turn_result = await conversational_memory.add_conversation_turn(
            session_id, user_message, assistant_response, action_executed, context
        )
        
        # Obtener sugerencias actualizadas basadas en el contexto
        user_id = conversation_context.get("context", {}).get("user_id", auth_user.user_id)
        updated_suggestions = await learning_engine.get_personalized_suggestions(
            user_id, {
                "current_message": user_message,
                "session_context": conversation_context.get("context", {}),
                "action_requested": action_executed
            }
        )
        
        return {
            "success": True,
            "turn_id": turn_result.get("turn_id"),
            "conversation_context": conversation_context.get("context", {}),
            "updated_suggestions": updated_suggestions,
            "sentiment_analysis": turn_result.get("sentiment"),
            "importance_score": turn_result.get("importance_score"),
            "message": "Consulta procesada con contexto inteligente"
        }
        
    except Exception as e:
        logger.error(f"Error procesando consulta inteligente: {e}")
        return {"success": False, "error": str(e)}

async def submit_user_feedback(auth_user: AuthenticatedUser, params: Dict[str, Any]) -> Dict[str, Any]:
    """Permite al usuario enviar feedback para mejorar el asistente"""
    try:
        feedback_data = {
            "user_id": params.get("user_id", auth_user.user_id),
            "interaction_id": params.get("interaction_id", ""),
            "type": params.get("feedback_type", "general"),  # positive, negative, suggestion, correction
            "rating": params.get("rating"),  # 1-5
            "comment": params.get("comment", ""),
            "context": params.get("context", {})
        }
        
        # Procesar feedback
        feedback_result = await learning_engine.process_user_feedback(feedback_data)
        
        return {
            "success": feedback_result["success"],
            "feedback_id": feedback_result.get("feedback_id"),
            "learning_improvements": {
                "patterns_updated": feedback_result.get("learning_patterns_updated", 0),
                "improvements_generated": feedback_result.get("improvements_generated", 0)
            },
            "message": feedback_result.get("message", "Feedback procesado")
        }
        
    except Exception as e:
        logger.error(f"Error procesando feedback: {e}")
        return {"success": False, "error": str(e)}

async def get_user_intelligence_profile(auth_user: AuthenticatedUser, params: Dict[str, Any]) -> Dict[str, Any]:
    """Obtiene el perfil de inteligencia del usuario"""
    try:
        user_id = params.get("user_id", auth_user.user_id)
        
        # Analizar patrones actualizados
        pattern_analysis = await intelligent_assistant.analyze_user_patterns(user_id)
        
        if not pattern_analysis.get("success"):
            return {"success": False, "error": "No se pudo obtener perfil de usuario"}
        
        profile = pattern_analysis["user_profile"]
        
        # Enriquecer con sugerencias personalizadas
        suggestions = await learning_engine.get_personalized_suggestions(
            user_id, {"profile_request": True}
        )
        
        return {
            "success": True,
            "user_profile": {
                "basic_info": {
                    "user_id": profile["user_id"],
                    "total_interactions": profile["total_interactions"],
                    "confidence_score": profile["confidence_score"],
                    "last_analysis": profile["last_analysis"]
                },
                "behavioral_patterns": {
                    "most_used_actions": dict(profile["patterns"]["most_used_actions"].most_common(5)),
                    "preferred_categories": dict(profile["preferences"]["preferred_platforms"].most_common(3)),
                    "peak_hours": profile["patterns"].get("time_patterns", {}),
                    "success_rate": profile["patterns"].get("success_rates", {})
                },
                "preferences": {
                    "platforms": dict(profile["preferences"]["preferred_platforms"].most_common(3)),
                    "content_types": dict(profile["preferences"]["content_types"].most_common(3)),
                    "frequent_keywords": dict(profile["preferences"]["frequent_keywords"].most_common(10))
                },
                "trends": profile["usage_trends"],
                "insights": profile["insights"],
                "personalized_suggestions": suggestions
            }
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo perfil de inteligencia: {e}")
        return {"success": False, "error": str(e)}

async def end_intelligent_session(auth_user: AuthenticatedUser, params: Dict[str, Any]) -> Dict[str, Any]:
    """Finaliza una sesión inteligente con evaluación"""
    try:
        session_id = params.get("session_id", "")
        satisfaction_score = params.get("satisfaction_score")  # 1-5
        final_feedback = params.get("feedback", "")
        
        if not session_id:
            return {"success": False, "error": "session_id es requerido"}
        
        # Finalizar sesión conversacional
        session_result = await conversational_memory.end_conversation_session(
            session_id, satisfaction_score
        )
        
        # Procesar feedback final si se proporciona
        if final_feedback or satisfaction_score:
            feedback_data = {
                "user_id": auth_user.user_id,
                "interaction_id": session_id,
                "type": "session_evaluation",
                "rating": satisfaction_score,
                "comment": final_feedback,
                "context": {"session_end": True}
            }
            
            await learning_engine.process_user_feedback(feedback_data)
        
        return {
            "success": session_result["success"],
            "session_summary": session_result.get("session_summary", ""),
            "session_stats": {
                "total_turns": session_result.get("total_turns", 0),
                "resolution_status": session_result.get("resolution_status", ""),
                "satisfaction_score": satisfaction_score
            },
            "message": "Sesión inteligente finalizada con aprendizaje actualizado"
        }
        
    except Exception as e:
        logger.error(f"Error finalizando sesión inteligente: {e}")
        return {"success": False, "error": str(e)}

async def upload_file_intelligently(auth_user: AuthenticatedUser, params: Dict[str, Any]) -> Dict[str, Any]:
    """Sube y procesa un archivo con análisis e IA"""
    try:
        file_data = params.get("file_content", "")  # Base64 encoded
        file_name = params.get("file_name", "")
        session_id = params.get("session_id", "")
        source = params.get("source", "upload")
        additional_context = params.get("context", {})
        
        if not file_data or not file_name:
            return {"success": False, "error": "file_content y file_name son requeridos"}
        
        # Decodificar archivo si está en base64
        import base64
        try:
            decoded_file = base64.b64decode(file_data)
        except:
            # Asumir que ya está decodificado
            decoded_file = file_data.encode('utf-8') if isinstance(file_data, str) else file_data
        
        # Procesar archivo inteligentemente
        processing_result = await intelligent_file_manager.process_file_automatically(
            decoded_file, file_name, auth_user.user_id, session_id, source, additional_context
        )
        
        response = {
            "success": processing_result.success,
            "file_id": processing_result.file_metadata.file_id if processing_result.file_metadata else None,
            "storage_locations": processing_result.storage_paths,
            "error": processing_result.error_message
        }
        
        if processing_result.success and processing_result.file_metadata:
            response["file_metadata"] = {
                "original_name": processing_result.file_metadata.original_name,
                "file_type": processing_result.file_metadata.file_type,
                "size_mb": round(processing_result.file_metadata.size_bytes / 1024 / 1024, 2),
                "classification": processing_result.file_metadata.classification,
                "ai_analysis": processing_result.file_metadata.ai_analysis
            }
            
            response["message"] = f"Archivo procesado y guardado en {len(processing_result.storage_paths)} ubicaciones"
        
        return response
        
    except Exception as e:
        logger.error(f"Error subiendo archivo inteligentemente: {e}")
        return {"success": False, "error": str(e)}

async def search_files_intelligently(auth_user: AuthenticatedUser, params: Dict[str, Any]) -> Dict[str, Any]:
    """Busca archivos usando IA y análisis semántico"""
    try:
        search_query = params.get("query", "")
        filters = params.get("filters", {})
        user_id = params.get("user_id", auth_user.user_id)
        
        if not search_query:
            return {"success": False, "error": "query es requerido"}
        
        # Realizar búsqueda inteligente
        search_result = await intelligent_file_manager.search_files_intelligently(
            user_id, search_query, filters
        )
        
        return search_result
        
    except Exception as e:
        logger.error(f"Error en búsqueda inteligente: {e}")
        return {"success": False, "error": str(e)}

async def get_conversation_history(auth_user: AuthenticatedUser, params: Dict[str, Any]) -> Dict[str, Any]:
    """Obtiene el historial de conversaciones del usuario"""
    try:
        user_id = params.get("user_id", auth_user.user_id)
        days_back = params.get("days_back", 30)
        limit = params.get("limit", 10)
        
        # Usar el sistema de memoria persistente para obtener historial
        from app.memory.persistent_memory import PersistentMemoryManager
        memory_manager = PersistentMemoryManager()
        
        # Obtener historial
        history_result = await memory_manager.search_interactions(
            query=f"user_id:{user_id}",
            limit=limit,
            user_id=user_id
        )
        
        if not history_result.get("success"):
            return {"success": False, "error": "No se pudo obtener historial"}
        
        conversations = history_result.get("data", [])
        
        # Organizar por sesiones
        sessions = {}
        for conv in conversations:
            session_id = conv.get("session_id", "unknown")
            if session_id not in sessions:
                sessions[session_id] = {
                    "session_id": session_id,
                    "start_time": conv.get("timestamp"),
                    "interactions": []
                }
            sessions[session_id]["interactions"].append(conv)
        
        # Convertir a lista y ordenar
        session_list = list(sessions.values())
        session_list.sort(key=lambda x: x.get("start_time", ""), reverse=True)
        
        return {
            "success": True,
            "total_sessions": len(session_list),
            "sessions": session_list[:limit],
            "user_id": user_id
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo historial de conversaciones: {e}")
        return {"success": False, "error": str(e)}

async def analyze_user_behavior_patterns(auth_user: AuthenticatedUser, params: Dict[str, Any]) -> Dict[str, Any]:
    """Analiza patrones de comportamiento detallados del usuario"""
    try:
        user_id = params.get("user_id", auth_user.user_id)
        analysis_type = params.get("analysis_type", "comprehensive")  # comprehensive, trends, preferences
        
        # Obtener análisis completo
        pattern_analysis = await intelligent_assistant.analyze_user_patterns(user_id)
        
        if not pattern_analysis.get("success"):
            return {"success": False, "error": "No se pudo analizar patrones"}
        
        profile = pattern_analysis["user_profile"]
        
        analysis_result = {
            "user_id": user_id,
            "analysis_timestamp": datetime.now().isoformat(),
            "confidence_score": profile["confidence_score"]
        }
        
        if analysis_type in ["comprehensive", "trends"]:
            analysis_result["temporal_patterns"] = {
                "most_active_hours": profile["patterns"].get("time_patterns", {}),
                "usage_trends": profile["usage_trends"],
                "session_patterns": {
                    "average_length": profile["patterns"].get("session_lengths", []),
                    "most_productive_days": profile["usage_trends"].get("most_productive_days", [])
                }
            }
        
        if analysis_type in ["comprehensive", "preferences"]:
            analysis_result["behavioral_preferences"] = {
                "platform_preferences": dict(profile["preferences"]["preferred_platforms"]),
                "content_preferences": dict(profile["preferences"]["content_types"]),
                "interaction_style": profile["preferences"].get("complexity_level", "medium"),
                "common_workflows": profile.get("common_workflows", [])
            }
        
        if analysis_type == "comprehensive":
            analysis_result["success_metrics"] = {
                "action_success_rates": profile["patterns"].get("success_rates", {}),
                "most_successful_actions": dict(profile["patterns"]["most_used_actions"].most_common(5)),
                "improvement_areas": profile.get("insights", [])
            }
        
        return {
            "success": True,
            "analysis": analysis_result,
            "recommendations": await learning_engine.get_personalized_suggestions(
                user_id, {"analysis_type": analysis_type}
            )
        }
        
    except Exception as e:
        logger.error(f"Error analizando patrones de comportamiento: {e}")
        return {"success": False, "error": str(e)}

async def get_learning_insights(auth_user: AuthenticatedUser, params: Dict[str, Any]) -> Dict[str, Any]:
    """Obtiene insights del motor de aprendizaje"""
    try:
        user_id = params.get("user_id", auth_user.user_id)
        
        # Obtener patrones de aprendizaje del usuario
        user_patterns = [
            pattern for pattern in learning_engine.learning_patterns.values()
            if user_id in pattern.pattern_id
        ]
        
        # Obtener reglas de adaptación
        adaptation_rules = learning_engine.adaptation_rules.get(user_id, {})
        
        # Estadísticas de feedback
        user_feedback = [
            feedback for feedback in learning_engine.feedback_history
            if feedback.user_id == user_id
        ]
        
        feedback_stats = {
            "total_feedback": len(user_feedback),
            "feedback_types": {},
            "average_rating": 0,
            "recent_feedback": []
        }
        
        if user_feedback:
            # Contar tipos de feedback
            for feedback in user_feedback:
                feedback_stats["feedback_types"][feedback.feedback_type] = \
                    feedback_stats["feedback_types"].get(feedback.feedback_type, 0) + 1
            
            # Calcular rating promedio
            ratings = [f.rating for f in user_feedback if f.rating]
            if ratings:
                feedback_stats["average_rating"] = sum(ratings) / len(ratings)
            
            # Feedback reciente
            recent = sorted(user_feedback, key=lambda x: x.timestamp, reverse=True)[:5]
            feedback_stats["recent_feedback"] = [
                {
                    "type": f.feedback_type,
                    "rating": f.rating,
                    "comment": f.comment,
                    "timestamp": f.timestamp.isoformat()
                }
                for f in recent
            ]
        
        return {
            "success": True,
            "learning_insights": {
                "identified_patterns": [
                    {
                        "pattern_type": p.pattern_type,
                        "description": p.description,
                        "confidence": p.confidence,
                        "occurrences": p.occurrences,
                        "impact_score": p.impact_score
                    }
                    for p in user_patterns
                ],
                "adaptation_rules": adaptation_rules,
                "feedback_statistics": feedback_stats,
                "learning_status": {
                    "total_patterns": len(user_patterns),
                    "high_confidence_patterns": len([p for p in user_patterns if p.confidence > 0.8]),
                    "adaptation_level": adaptation_rules.get("response_style", "standard")
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo insights de aprendizaje: {e}")
        return {"success": False, "error": str(e)}
