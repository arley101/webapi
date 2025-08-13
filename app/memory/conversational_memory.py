# app/memory/conversational_memory.py
"""
Sistema de Memoria Conversacional Persistente
Funcionalidades:
- Memoria entre sesiones
- Contexto conversacional inteligente
- Conexión de información histórica
- Resumen automático de conversaciones largas
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import json
import hashlib
from dataclasses import dataclass, asdict
from collections import defaultdict

from app.core.auth_manager import get_auth_client
from app.actions import sharepoint_actions, notion_actions, gemini_actions
from .persistent_memory import PersistentMemoryManager

logger = logging.getLogger(__name__)

@dataclass
class ConversationTurn:
    """Un turno en la conversación"""
    turn_id: str
    session_id: str
    user_id: str
    timestamp: datetime
    user_message: str
    assistant_response: str
    action_executed: Optional[str]
    context: Dict[str, Any]
    sentiment: Optional[str]
    importance_score: float

@dataclass
class ConversationSession:
    """Una sesión completa de conversación"""
    session_id: str
    user_id: str
    start_time: datetime
    end_time: Optional[datetime]
    turns: List[ConversationTurn]
    summary: Optional[str]
    topics: List[str]
    resolution_status: str  # 'completed', 'pending', 'escalated'
    satisfaction_score: Optional[float]

class ConversationalMemory:
    """Sistema de memoria conversacional que mantiene contexto entre sesiones"""
    
    def __init__(self):
        self.persistent_memory = PersistentMemoryManager()
        self.active_sessions = {}  # Cache de sesiones activas
        self.conversation_history = {}  # Cache de historial por usuario
        
        # Configuración
        self.config = {
            "max_turns_per_session": 100,
            "session_timeout_minutes": 30,
            "max_context_tokens": 4000,
            "summary_trigger_turns": 20,
            "importance_threshold": 0.7,
            "max_sessions_cache": 50
        }
    
    async def start_conversation_session(self, user_id: str, initial_context: Dict[str, Any] = None) -> str:
        """Inicia una nueva sesión de conversación"""
        try:
            session_id = f"conv_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Obtener contexto histórico relevante
            historical_context = await self._get_relevant_historical_context(user_id, initial_context)
            
            # Crear nueva sesión
            session = ConversationSession(
                session_id=session_id,
                user_id=user_id,
                start_time=datetime.now(),
                end_time=None,
                turns=[],
                summary=None,
                topics=[],
                resolution_status="pending",
                satisfaction_score=None
            )
            
            # Guardar en cache
            self.active_sessions[session_id] = session
            
            # Inicializar memoria conversacional
            await self._initialize_session_memory(session, historical_context)
            
            logger.info(f"Nueva sesión iniciada: {session_id} para usuario {user_id}")
            
            return session_id
            
        except Exception as e:
            logger.error(f"Error iniciando sesión de conversación: {e}")
            raise
    
    async def add_conversation_turn(self, session_id: str, user_message: str, 
                                  assistant_response: str, action_executed: str = None,
                                  context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Añade un turno a la conversación actual"""
        try:
            session = self.active_sessions.get(session_id)
            if not session:
                return {"success": False, "error": "Sesión no encontrada"}
            
            # Crear turno
            turn_id = f"turn_{len(session.turns) + 1}"
            
            # Analizar sentimiento y importancia
            sentiment = await self._analyze_sentiment(user_message)
            importance_score = await self._calculate_importance_score(
                user_message, assistant_response, context or {}
            )
            
            turn = ConversationTurn(
                turn_id=turn_id,
                session_id=session_id,
                user_id=session.user_id,
                timestamp=datetime.now(),
                user_message=user_message,
                assistant_response=assistant_response,
                action_executed=action_executed,
                context=context or {},
                sentiment=sentiment,
                importance_score=importance_score
            )
            
            # Añadir a la sesión
            session.turns.append(turn)
            
            # Actualizar temas
            await self._update_session_topics(session, user_message)
            
            # Verificar si necesita resumen
            if len(session.turns) >= self.config["summary_trigger_turns"]:
                await self._create_session_summary(session)
            
            # Guardar persistentemente
            await self._save_conversation_turn(turn)
            
            # Verificar límites de contexto
            await self._manage_context_limits(session)
            
            return {
                "success": True,
                "turn_id": turn_id,
                "importance_score": importance_score,
                "sentiment": sentiment,
                "session_turns": len(session.turns)
            }
            
        except Exception as e:
            logger.error(f"Error añadiendo turno de conversación: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_conversation_context(self, session_id: str, max_turns: int = 10) -> Dict[str, Any]:
        """Obtiene el contexto actual de la conversación"""
        try:
            session = self.active_sessions.get(session_id)
            if not session:
                return {"success": False, "error": "Sesión no encontrada"}
            
            # Obtener últimos turnos
            recent_turns = session.turns[-max_turns:] if session.turns else []
            
            # Construir contexto
            context = {
                "session_id": session_id,
                "user_id": session.user_id,
                "session_start": session.start_time.isoformat(),
                "total_turns": len(session.turns),
                "current_topics": session.topics,
                "resolution_status": session.resolution_status,
                "recent_turns": []
            }
            
            # Añadir turnos recientes
            for turn in recent_turns:
                context["recent_turns"].append({
                    "turn_id": turn.turn_id,
                    "timestamp": turn.timestamp.isoformat(),
                    "user_message": turn.user_message,
                    "assistant_response": turn.assistant_response,
                    "action_executed": turn.action_executed,
                    "sentiment": turn.sentiment,
                    "importance_score": turn.importance_score
                })
            
            # Añadir resumen si existe
            if session.summary:
                context["session_summary"] = session.summary
            
            # Obtener contexto histórico relevante
            historical_context = await self._get_relevant_historical_context(
                session.user_id, {"current_topics": session.topics}
            )
            context["historical_context"] = historical_context
            
            return {"success": True, "context": context}
            
        except Exception as e:
            logger.error(f"Error obteniendo contexto de conversación: {e}")
            return {"success": False, "error": str(e)}
    
    async def end_conversation_session(self, session_id: str, 
                                      satisfaction_score: float = None) -> Dict[str, Any]:
        """Finaliza una sesión de conversación"""
        try:
            session = self.active_sessions.get(session_id)
            if not session:
                return {"success": False, "error": "Sesión no encontrada"}
            
            # Actualizar sesión
            session.end_time = datetime.now()
            session.satisfaction_score = satisfaction_score
            
            # Determinar estado de resolución
            if satisfaction_score and satisfaction_score >= 4.0:
                session.resolution_status = "completed"
            elif satisfaction_score and satisfaction_score <= 2.0:
                session.resolution_status = "escalated"
            else:
                session.resolution_status = "completed"
            
            # Crear resumen final si no existe
            if not session.summary:
                await self._create_session_summary(session)
            
            # Guardar sesión completa
            await self._save_complete_session(session)
            
            # Actualizar memoria persistente
            await self._update_persistent_memory(session)
            
            # Remover del cache activo
            del self.active_sessions[session_id]
            
            # Añadir al historial
            if session.user_id not in self.conversation_history:
                self.conversation_history[session.user_id] = []
            self.conversation_history[session.user_id].append(session)
            
            # Limitar historial en cache
            if len(self.conversation_history[session.user_id]) > self.config["max_sessions_cache"]:
                self.conversation_history[session.user_id] = \
                    self.conversation_history[session.user_id][-self.config["max_sessions_cache"]:]
            
            return {
                "success": True,
                "session_summary": session.summary,
                "total_turns": len(session.turns),
                "resolution_status": session.resolution_status,
                "satisfaction_score": satisfaction_score
            }
            
        except Exception as e:
            logger.error(f"Error finalizando sesión de conversación: {e}")
            return {"success": False, "error": str(e)}
    
    async def _get_relevant_historical_context(self, user_id: str, 
                                              current_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Obtiene contexto histórico relevante para el usuario"""
        try:
            # Obtener historial del usuario desde SharePoint
            auth_client = get_auth_client()
            
            search_result = await sharepoint_actions.search_list_items(auth_client, {
                "list_name": "Elite_Conversation_History",
                "search_query": f"user_id:{user_id}",
                "filter": f"end_time ge '{(datetime.now() - timedelta(days=30)).isoformat()}'",
                "top": 10,
                "order_by": "end_time desc"
            })
            
            if not search_result.get("success"):
                return {"sessions": [], "topics": [], "patterns": []}
            
            historical_sessions = search_result.get("data", [])
            
            # Extraer información relevante
            historical_topics = []
            common_patterns = []
            successful_resolutions = []
            
            for session_data in historical_sessions:
                try:
                    session_info = json.loads(session_data.get("session_data", "{}"))
                    
                    # Temas históricos
                    if session_info.get("topics"):
                        historical_topics.extend(session_info["topics"])
                    
                    # Patrones de resolución exitosa
                    if session_info.get("resolution_status") == "completed":
                        successful_resolutions.append({
                            "topics": session_info.get("topics", []),
                            "actions_used": session_info.get("actions_used", []),
                            "satisfaction": session_info.get("satisfaction_score", 0)
                        })
                    
                except Exception as e:
                    logger.warning(f"Error procesando sesión histórica: {e}")
                    continue
            
            # Encontrar temas relacionados con el contexto actual
            relevant_topics = []
            if current_context and current_context.get("current_topics"):
                current_topics = set(current_context["current_topics"])
                for topic in historical_topics:
                    if any(ct.lower() in topic.lower() for ct in current_topics):
                        relevant_topics.append(topic)
            
            return {
                "historical_sessions": len(historical_sessions),
                "topics": list(set(historical_topics)),
                "relevant_topics": list(set(relevant_topics)),
                "successful_patterns": successful_resolutions,
                "last_interaction": historical_sessions[0].get("end_time") if historical_sessions else None
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo contexto histórico: {e}")
            return {"sessions": [], "topics": [], "patterns": []}
    
    async def _analyze_sentiment(self, message: str) -> str:
        """Analiza el sentimiento del mensaje"""
        try:
            if not message or len(message) < 5:
                return "neutral"
            
            # Análisis básico por palabras clave
            positive_keywords = ["gracias", "excelente", "perfecto", "genial", "bueno", "correcto"]
            negative_keywords = ["error", "mal", "problema", "fallo", "incorrecto", "no funciona"]
            
            message_lower = message.lower()
            
            positive_count = sum(1 for word in positive_keywords if word in message_lower)
            negative_count = sum(1 for word in negative_keywords if word in message_lower)
            
            if positive_count > negative_count:
                return "positive"
            elif negative_count > positive_count:
                return "negative"
            else:
                return "neutral"
                
        except Exception as e:
            logger.error(f"Error analizando sentimiento: {e}")
            return "neutral"
    
    async def _calculate_importance_score(self, user_message: str, 
                                        assistant_response: str, context: Dict) -> float:
        """Calcula la importancia de un turno de conversación"""
        try:
            score = 0.5  # Base score
            
            # Factores que aumentan importancia
            if any(word in user_message.lower() for word in ["problema", "error", "urgent", "importante"]):
                score += 0.3
            
            if any(word in user_message.lower() for word in ["configurar", "setup", "crear", "implementar"]):
                score += 0.2
            
            if context.get("action_executed"):
                score += 0.2
            
            if len(user_message) > 100:  # Mensajes largos suelen ser más importantes
                score += 0.1
            
            if any(word in assistant_response.lower() for word in ["completado", "éxito", "finalizado"]):
                score += 0.1
            
            # Factores que disminuyen importancia
            if any(word in user_message.lower() for word in ["hola", "gracias", "ok", "bien"]) and len(user_message) < 20:
                score -= 0.2
            
            return min(max(score, 0.0), 1.0)
            
        except Exception as e:
            logger.error(f"Error calculando importancia: {e}")
            return 0.5
    
    async def _update_session_topics(self, session: ConversationSession, message: str) -> None:
        """Actualiza los temas de la sesión basado en el mensaje"""
        try:
            # Extraer temas usando análisis básico
            topics_keywords = {
                "sharepoint": ["sharepoint", "sharepoint online", "listas", "sitios"],
                "teams": ["teams", "microsoft teams", "reuniones", "chat"],
                "onedrive": ["onedrive", "archivos", "sincronización", "almacenamiento"],
                "email": ["email", "correo", "outlook", "enviar"],
                "calendar": ["calendario", "cita", "evento", "reunión"],
                "automation": ["automatizar", "flujo", "workflow", "power automate"],
                "reports": ["reporte", "informe", "análisis", "datos"],
                "integration": ["integración", "api", "conectar", "sincronizar"]
            }
            
            message_lower = message.lower()
            new_topics = []
            
            for topic, keywords in topics_keywords.items():
                if any(keyword in message_lower for keyword in keywords):
                    if topic not in session.topics:
                        new_topics.append(topic)
                        session.topics.append(topic)
            
            # Limitar número de temas
            if len(session.topics) > 10:
                session.topics = session.topics[-10:]
                
        except Exception as e:
            logger.error(f"Error actualizando temas: {e}")
    
    async def _create_session_summary(self, session: ConversationSession) -> None:
        """Crea un resumen de la sesión usando IA"""
        try:
            if not session.turns:
                return
            
            # Preparar contexto para el resumen
            conversation_text = []
            for turn in session.turns[-20:]:  # Últimos 20 turnos
                conversation_text.append(f"Usuario: {turn.user_message}")
                conversation_text.append(f"Asistente: {turn.assistant_response}")
            
            conversation_str = "\n".join(conversation_text)
            
            # Usar Gemini para crear resumen
            auth_client = get_auth_client()
            
            summary_prompt = f"""
            Crea un resumen conciso de esta conversación entre un usuario y un asistente de IA.
            Incluye:
            1. Objetivo principal del usuario
            2. Acciones realizadas
            3. Resultados obtenidos
            4. Estado de resolución
            
            Conversación:
            {conversation_str}
            
            Resumen (máximo 200 palabras):
            """
            
            summary_result = await gemini_actions.analyze_conversation(auth_client, {
                "conversation_data": summary_prompt,
                "analysis_type": "session_summary"
            })
            
            if summary_result.get("success"):
                session.summary = summary_result.get("data", {}).get("summary", "Resumen no disponible")
            else:
                # Resumen básico si falla IA
                session.summary = f"Conversación con {len(session.turns)} turnos sobre: {', '.join(session.topics[:3])}"
                
        except Exception as e:
            logger.error(f"Error creando resumen de sesión: {e}")
            session.summary = f"Conversación con {len(session.turns)} turnos"
    
    async def _save_conversation_turn(self, turn: ConversationTurn) -> None:
        """Guarda un turno de conversación"""
        try:
            auth_client = get_auth_client()
            
            turn_data = {
                "list_name": "Elite_Conversation_Turns",
                "item_data": {
                    "turn_id": turn.turn_id,
                    "session_id": turn.session_id,
                    "user_id": turn.user_id,
                    "timestamp": turn.timestamp.isoformat(),
                    "user_message": turn.user_message,
                    "assistant_response": turn.assistant_response,
                    "action_executed": turn.action_executed or "",
                    "context": json.dumps(turn.context),
                    "sentiment": turn.sentiment or "",
                    "importance_score": turn.importance_score
                }
            }
            
            await sharepoint_actions.create_list_item(auth_client, turn_data)
            
        except Exception as e:
            logger.error(f"Error guardando turno de conversación: {e}")
    
    async def _save_complete_session(self, session: ConversationSession) -> None:
        """Guarda una sesión completa de conversación"""
        try:
            auth_client = get_auth_client()
            
            # Datos principales de la sesión
            session_data = {
                "list_name": "Elite_Conversation_History",
                "item_data": {
                    "session_id": session.session_id,
                    "user_id": session.user_id,
                    "start_time": session.start_time.isoformat(),
                    "end_time": session.end_time.isoformat() if session.end_time else "",
                    "total_turns": len(session.turns),
                    "summary": session.summary or "",
                    "topics": json.dumps(session.topics),
                    "resolution_status": session.resolution_status,
                    "satisfaction_score": session.satisfaction_score or 0,
                    "session_data": json.dumps(asdict(session), default=str)
                }
            }
            
            await sharepoint_actions.create_list_item(auth_client, session_data)
            
            # También guardar en Notion para análisis
            notion_data = {
                "database_name": "Elite Conversation Sessions",
                "properties": {
                    "Session ID": session.session_id,
                    "User ID": session.user_id,
                    "Start Time": session.start_time.isoformat(),
                    "Duration": str(session.end_time - session.start_time) if session.end_time else "Ongoing",
                    "Total Turns": len(session.turns),
                    "Topics": ", ".join(session.topics),
                    "Resolution": session.resolution_status,
                    "Satisfaction": session.satisfaction_score or 0,
                    "Summary": session.summary or "No summary available"
                }
            }
            
            await notion_actions.create_page(auth_client, notion_data)
            
        except Exception as e:
            logger.error(f"Error guardando sesión completa: {e}")
    
    async def _manage_context_limits(self, session: ConversationSession) -> None:
        """Gestiona los límites de contexto de la sesión"""
        if len(session.turns) > self.config["max_turns_per_session"]:
            # Crear resumen de turnos antiguos y removerlos
            old_turns = session.turns[:-50]  # Mantener últimos 50
            
            if old_turns:
                await self._archive_old_turns(session.session_id, old_turns)
                session.turns = session.turns[-50:]
    
    async def _archive_old_turns(self, session_id: str, old_turns: List[ConversationTurn]) -> None:
        """Archiva turnos antiguos en almacenamiento persistente"""
        try:
            auth_client = get_auth_client()
            
            archive_data = {
                "list_name": "Elite_Conversation_Archive",
                "item_data": {
                    "session_id": session_id,
                    "archived_at": datetime.now().isoformat(),
                    "turns_count": len(old_turns),
                    "archived_turns": json.dumps([asdict(turn) for turn in old_turns], default=str)
                }
            }
            
            await sharepoint_actions.create_list_item(auth_client, archive_data)
            
        except Exception as e:
            logger.error(f"Error archivando turnos antiguos: {e}")
    
    async def _initialize_session_memory(self, session: ConversationSession, 
                                       historical_context: Dict[str, Any]) -> None:
        """Inicializa la memoria de la sesión con contexto histórico"""
        try:
            # Guardar contexto inicial en Notion para referencia
            auth_client = get_auth_client()
            
            context_data = {
                "database_name": "Elite Session Context",
                "properties": {
                    "Session ID": session.session_id,
                    "User ID": session.user_id,
                    "Initialized At": session.start_time.isoformat(),
                    "Historical Sessions": historical_context.get("historical_sessions", 0),
                    "Relevant Topics": ", ".join(historical_context.get("relevant_topics", [])),
                    "Context Data": json.dumps(historical_context, indent=2)
                }
            }
            
            await notion_actions.create_page(auth_client, context_data)
            
        except Exception as e:
            logger.error(f"Error inicializando memoria de sesión: {e}")
    
    async def _update_persistent_memory(self, session: ConversationSession) -> None:
        """Actualiza la memoria persistente con información de la sesión"""
        try:
            # Extraer información importante para memoria persistente
            important_turns = [turn for turn in session.turns if turn.importance_score > 0.7]
            
            for turn in important_turns:
                memory_data = {
                    "session_id": session.session_id,
                    "user_id": session.user_id,
                    "action": turn.action_executed or "conversation",
                    "query": turn.user_message,
                    "result": turn.assistant_response,
                    "context": turn.context,
                    "importance": turn.importance_score,
                    "timestamp": turn.timestamp.isoformat()
                }
                
                await self.persistent_memory.save_interaction(
                    session.session_id, memory_data, session.user_id
                )
                
        except Exception as e:
            logger.error(f"Error actualizando memoria persistente: {e}")

# Instancia global de memoria conversacional
conversational_memory = ConversationalMemory()
