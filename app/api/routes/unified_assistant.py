# app/api/routes/unified_assistant.py
"""
🚀 ROUTER UNIFICADO PARA ASISTENTE INTELIGENTE INDEPENDIENTE
Sistema completo sin restricciones que funciona como backup del Custom GPT.
Incluye interfaz web, micrófono, síntesis de voz y toma de decisiones autónomas.

✅ SIN RESTRICCIONES: No limitado por políticas de OpenAI
✅ TOMA DECISIONES: Puede ejecutar cualquier acción sin confirmación
✅ INTERFAZ WEB: Navegador con micrófono y síntesis de voz
✅ MEMORIA INTELIGENTE: Aprendizaje y contexto persistente
✅ LENGUAJE NATURAL: Comprende español conversacional
"""

import logging
from datetime import datetime
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import JSONResponse, HTMLResponse
from typing import Any, Dict, Optional, List
import json
import re
import os
import asyncio

from app.core.action_mapper import ACTION_MAP
from app.core.auth_manager import get_current_user, AuthenticatedUser, get_auth_client
from app.memory.intelligent_assistant import IntelligentAssistant
from app.memory.simple_memory import simple_memory_manager as memory_manager
from app.workflows.auto_workflow import AutoWorkflowManager

logger = logging.getLogger(__name__)
router = APIRouter()

# Instanciar el asistente inteligente
intelligent_assistant = IntelligentAssistant()
workflow_manager = AutoWorkflowManager()

# Configuración del asistente independiente
ASSISTANT_CONFIG = {
    "name": "Elite Assistant",
    "personality": "proactive_intelligent",
    "decision_making": "autonomous",  # Puede tomar decisiones sin confirmación
    "restrictions": "none",  # Sin restricciones de OpenAI
    "voice_enabled": True,
    "memory_enabled": True,
    "learning_enabled": True
}

# Mapeo extendido de lenguaje natural con patrones conversacionales
CONVERSATION_PATTERNS = {
    # Saludos y activación
    r"(hola|buenos días|buenas tardes|hey|oye)": "greeting",
    r"(ayuda|ayúdame|necesito ayuda|qué puedes hacer)": "help",
    r"(cómo estás|cómo te encuentras|qué tal)": "status_check",
    
    # Comandos de email
    r"(envía|enviar|manda|mandar).*(email|correo|mensaje)": "send_email",
    r"(revisa|revisar|lee|leer|consulta|consultar).*(email|correo|mensaje)": "check_email",
    r"(responde|responder|contesta|contestar).*(email|correo)": "reply_email",
    
    # Comandos de calendario
    r"(programa|programar|agenda|agendar|crea|crear).*(reunión|cita|evento)": "schedule_meeting",
    r"(qué tengo|qué hay|agenda|calendario).*(hoy|mañana|semana)": "check_calendar",
    r"(cancela|cancelar|elimina|eliminar).*(reunión|cita|evento)": "cancel_meeting",
    
    # Comandos de análisis
    r"(analiza|analizar|revisa|revisar|evalúa|evaluar).*(métricas|datos|resultados)": "analyze_metrics",
    r"(reporta|reportar|resume|resumir|informe)": "generate_report",
    r"(compara|comparar|contrasta|contrastar)": "compare_data",
    
    # Comandos de automatización
    r"(ejecuta|ejecutar|corre|correr|inicia|iniciar).*(workflow|flujo|proceso)": "execute_workflow",
    r"(backup|respaldo|copia|guarda|guardar).*(todo|completo|datos)": "backup_data",
    r"(sincroniza|sincronizar|actualiza|actualizar)": "sync_data",
    
    # Comandos de memoria e IA
    r"(aprende|aprender|recuerda|recordar|guarda|guardar).*(esto|información|dato)": "learn_from_input",
    r"(qué has aprendido|qué sabes|qué recuerdas)": "show_learned_data",
    r"(sugiere|sugerir|recomienda|recomendar|propone|proponer)": "get_suggestions",
    r"(optimiza|optimizar|mejora|mejorar)": "optimize_workflow",
    
    # Comandos de marketing
    r"(crea|crear|diseña|diseñar).*(campaña|anuncio|publicidad)": "create_campaign",
    r"(publica|publicar|comparte|compartir).*(redes|social|facebook|twitter|linkedin)": "social_post",
    r"(métricas|estadísticas|rendimiento).*(marketing|campaña|anuncios)": "marketing_metrics",
    
    # Comandos de archivos
    r"(sube|subir|carga|cargar).*(archivo|documento|imagen)": "upload_file",
    r"(busca|buscar|encuentra|encontrar).*(archivo|documento)": "search_files",
    r"(comparte|compartir|envía|enviar).*(archivo|documento|enlace)": "share_file",
    
    # Comandos de decisión
    r"(decide|decidir|elige|elegir|selecciona|seleccionar)": "make_decision",
    r"(qué me recomiendas|qué debo hacer|qué sugieres)": "get_recommendation",
    r"(toma la decisión|hazlo|procede|continúa)": "autonomous_action"
}

class UnifiedAssistantProcessor:
    """Procesador principal del asistente unificado"""
    
    def __init__(self):
        self.session_memory = {}
        self.context_history = []
    
    async def process_natural_language(self, query: str, user_id: str = "default") -> Dict[str, Any]:
        """
        Procesa lenguaje natural sin restricciones y toma decisiones autónomas
        """
        try:
            # Normalizar query
            query = query.strip().lower()
            
            # Guardar en contexto
            self.context_history.append({
                "timestamp": datetime.now().isoformat(),
                "query": query,
                "user_id": user_id
            })
            
            # Mantener solo últimos 10 mensajes en contexto
            if len(self.context_history) > 10:
                self.context_history = self.context_history[-10:]
            
            # 1. Detectar patrón conversacional
            intent = self._detect_intent(query)
            
            # 2. Extraer parámetros del contexto
            params = self._extract_parameters(query, intent)
            
            # 3. Analizar contexto histórico
            context = await self._analyze_context(user_id)
            
            # 4. Tomar decisión autónoma o sugerir acción
            decision = await self._make_autonomous_decision(intent, params, context, query)
            
            # 5. Ejecutar acción si está autorizada
            if decision.get("execute_immediately", False):
                result = await self._execute_action(decision["action"], decision["params"])
                decision["execution_result"] = result
            
            # 6. Aprender de la interacción
            await self._learn_from_interaction(query, intent, decision, user_id)
            
            return {
                "status": "success",
                "response": decision["response"],
                "intent": intent,
                "action": decision.get("action"),
                "params": decision.get("params", {}),
                "executed": decision.get("execute_immediately", False),
                "execution_result": decision.get("execution_result"),
                "suggestions": decision.get("suggestions", []),
                "context_used": context,
                "assistant_personality": ASSISTANT_CONFIG["personality"],
                "restrictions": ASSISTANT_CONFIG["restrictions"],
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error procesando lenguaje natural: {e}")
            return {
                "status": "error",
                "message": f"Error procesando consulta: {str(e)}",
                "query": query,
                "timestamp": datetime.now().isoformat()
            }
    
    def _detect_intent(self, query: str) -> str:
        """Detecta la intención basada en patrones conversacionales"""
        for pattern, intent in CONVERSATION_PATTERNS.items():
            if re.search(pattern, query, re.IGNORECASE):
                return intent
        
        # Si no encuentra patrón específico, buscar en acciones disponibles
        for natural_phrase, action in self._get_action_mappings().items():
            if natural_phrase in query:
                return f"action_{action}"
        
        return "general_query"
    
    def _extract_parameters(self, query: str, intent: str) -> Dict[str, Any]:
        """Extrae parámetros del lenguaje natural"""
        params = {}
        
        # Extraer emails
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, query)
        if emails:
            params["email"] = emails[0] if len(emails) == 1 else emails
        
        # Extraer fechas comunes
        if re.search(r'\b(hoy|today)\b', query, re.IGNORECASE):
            params["date"] = datetime.now().strftime("%Y-%m-%d")
        elif re.search(r'\b(mañana|tomorrow)\b', query, re.IGNORECASE):
            params["date"] = (datetime.now().replace(day=datetime.now().day + 1)).strftime("%Y-%m-%d")
        
        # Extraer horas
        time_pattern = r'\b(\d{1,2}):(\d{2})\b|\b(\d{1,2})\s*(am|pm|hrs|h)\b'
        times = re.findall(time_pattern, query, re.IGNORECASE)
        if times:
            params["time"] = times[0]
        
        # Extraer nombres y asuntos entre comillas
        quoted_pattern = r'"([^"]+)"'
        quoted_texts = re.findall(quoted_pattern, query)
        if quoted_texts:
            if intent.startswith("send_email"):
                params["subject"] = quoted_texts[0] if len(quoted_texts) > 0 else ""
                params["body"] = quoted_texts[1] if len(quoted_texts) > 1 else ""
            elif intent.startswith("schedule"):
                params["title"] = quoted_texts[0]
        
        return params
    
    async def _analyze_context(self, user_id: str) -> Dict[str, Any]:
        """Analiza el contexto del usuario para tomar mejores decisiones"""
        try:
            # Obtener patrones del usuario desde la IA inteligente
            patterns = await intelligent_assistant.analyze_user_patterns(user_id)
            
            # Obtener historial reciente
            recent_history = self.context_history[-5:] if self.context_history else []
            
            # Analizar tendencias
            return {
                "user_patterns": patterns,
                "recent_history": recent_history,
                "frequent_actions": patterns.get("most_used_actions", {}),
                "time_preferences": patterns.get("time_patterns", {}),
                "context_score": len(recent_history) * 0.2  # Peso del contexto
            }
        except Exception as e:
            logger.warning(f"Error analizando contexto: {e}")
            return {"context_available": False}
    
    async def _make_autonomous_decision(self, intent: str, params: Dict, context: Dict, original_query: str) -> Dict[str, Any]:
        """Toma decisiones autónomas sin restricciones"""
        try:
            # Configuración de decisiones por tipo de intent
            decision_config = {
                "greeting": {
                    "response": f"¡Hola! Soy {ASSISTANT_CONFIG['name']}, tu asistente personal inteligente. ¿En qué puedo ayudarte hoy?",
                    "execute_immediately": False,
                    "suggestions": ["Ver agenda del día", "Revisar emails pendientes", "Analizar métricas recientes"]
                },
                "help": {
                    "response": "Puedo ayudarte con emails, calendario, análisis de datos, marketing, automatizaciones y mucho más. Simplemente dime qué necesitas en lenguaje natural.",
                    "execute_immediately": False,
                    "suggestions": ["Mostrar todas las categorías", "Ver acciones populares", "Comenzar con un ejemplo"]
                },
                "send_email": {
                    "response": "Perfecto, voy a enviar ese email por ti.",
                    "action": "enviar_correo_outlook",
                    "execute_immediately": True,  # Ejecuta automáticamente
                    "params": params
                },
                "check_email": {
                    "response": "Revisando tus emails ahora mismo...",
                    "action": "leer_correos_outlook",
                    "execute_immediately": True,
                    "params": {"limit": 10}
                },
                "schedule_meeting": {
                    "response": "Programando la reunión en tu calendario...",
                    "action": "calendario_crear_evento",
                    "execute_immediately": True,
                    "params": params
                },
                "execute_workflow": {
                    "response": "Ejecutando el workflow solicitado...",
                    "action": "execute_workflow",
                    "execute_immediately": True,
                    "params": self._determine_workflow_params(original_query, params)
                },
                "analyze_metrics": {
                    "response": "Analizando tus métricas y generando insights...",
                    "action": "analyze_all_metrics",
                    "execute_immediately": True,
                    "params": {"period": "last_week", "include_suggestions": True}
                },
                "get_suggestions": {
                    "response": "Basándome en tus patrones, aquí tienes mis recomendaciones...",
                    "execute_immediately": False,
                    "suggestions": await self._generate_intelligent_suggestions(context)
                },
                "autonomous_action": {
                    "response": "Entendido, procediendo con la acción más apropiada según el contexto...",
                    "execute_immediately": True,
                    "action": await self._determine_best_action(context, original_query),
                    "params": params
                }
            }
            
            # Obtener configuración de decisión o usar default
            decision = decision_config.get(intent, {
                "response": "Entiendo tu consulta. Déjame procesar eso para ti...",
                "execute_immediately": False,
                "suggestions": ["¿Puedes ser más específico?", "¿Te refieres a alguna acción en particular?"]
            })
            
            # Añadir contexto inteligente a la respuesta
            if context.get("user_patterns"):
                decision["response"] += f" (Basado en tus patrones de uso habituales)"
            
            return decision
            
        except Exception as e:
            logger.error(f"Error tomando decisión autónoma: {e}")
            return {
                "response": "Hubo un problema procesando tu solicitud, pero puedo intentar otra aproximación.",
                "execute_immediately": False,
                "error": str(e)
            }
    
    async def _execute_action(self, action: str, params: Dict) -> Dict[str, Any]:
        """Ejecuta acción sin restricciones"""
        try:
            if action not in ACTION_MAP:
                return {"status": "error", "message": f"Acción '{action}' no encontrada"}
            
            auth_client = get_auth_client()
            action_function = ACTION_MAP[action]
            
            # Ejecutar función
            if asyncio.iscoroutinefunction(action_function):
                result = await action_function(auth_client, params)
            else:
                result = action_function(auth_client, params)
            
            return {
                "status": "success",
                "action_executed": action,
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error ejecutando acción {action}: {e}")
            return {
                "status": "error", 
                "message": f"Error ejecutando acción: {str(e)}",
                "action": action
            }
    
    async def _learn_from_interaction(self, query: str, intent: str, decision: Dict, user_id: str):
        """Aprende de la interacción para mejorar futuras respuestas"""
        try:
            # Guardar interacción en memoria inteligente
            interaction_data = {
                "user_id": user_id,
                "query": query,
                "intent": intent,
                "decision": decision,
                "timestamp": datetime.now().isoformat(),
                "success": decision.get("execution_result", {}).get("status") == "success"
            }
            
            # Guardar en memoria simple y persistente
            session_id = f"unified_assistant_{user_id}_{datetime.now().strftime('%Y%m%d')}"
            memory_manager.save_interaction(session_id, interaction_data)
            
            # Entrenar IA inteligente
            await intelligent_assistant.learn_from_interaction(user_id, interaction_data)
            
        except Exception as e:
            logger.warning(f"Error aprendiendo de interacción: {e}")
    
    def _get_action_mappings(self) -> Dict[str, str]:
        """Obtiene mapeo de frases naturales a acciones"""
        return {
            "enviar email": "enviar_correo_outlook",
            "leer correos": "leer_correos_outlook",
            "crear evento": "calendario_crear_evento",
            "listar eventos": "calendario_listar_eventos",
            "subir archivo": "subir_archivo_onedrive",
            "crear campaña": "metaads_create_campaign",
            "analizar métricas": "google_ads_get_campaign_performance",
            "backup completo": "execute_workflow",
            "listar workflows": "list_workflows"
        }
    
    def _determine_workflow_params(self, query: str, params: Dict) -> Dict[str, Any]:
        """Determina parámetros de workflow basado en la consulta"""
        workflow_params = params.copy()
        
        if "backup" in query.lower():
            workflow_params["workflow_name"] = "backup_completo"
        elif "marketing" in query.lower():
            workflow_params["workflow_name"] = "sync_marketing"
        elif "contenido" in query.lower() or "content" in query.lower():
            workflow_params["workflow_name"] = "content_creation"
        elif "youtube" in query.lower():
            workflow_params["workflow_name"] = "youtube_pipeline"
        
        return workflow_params
    
    async def _generate_intelligent_suggestions(self, context: Dict) -> List[str]:
        """Genera sugerencias inteligentes basadas en contexto"""
        suggestions = []
        
        try:
            patterns = context.get("user_patterns", {})
            frequent_actions = patterns.get("most_used_actions", {})
            
            if frequent_actions:
                top_actions = list(frequent_actions.keys())[:3]
                suggestions.extend([f"Ejecutar {action}" for action in top_actions])
            
            # Sugerencias basadas en hora del día
            current_hour = datetime.now().hour
            if 8 <= current_hour <= 12:
                suggestions.append("Revisar agenda del día")
                suggestions.append("Procesar emails pendientes")
            elif 13 <= current_hour <= 17:
                suggestions.append("Analizar progreso del día")
                suggestions.append("Preparar reuniones")
            else:
                suggestions.append("Realizar backup de datos")
                suggestions.append("Programar tareas para mañana")
            
            return suggestions[:5]  # Máximo 5 sugerencias
            
        except Exception as e:
            logger.warning(f"Error generando sugerencias: {e}")
            return ["Revisar emails", "Ver calendario", "Analizar métricas"]
    
    async def _determine_best_action(self, context: Dict, query: str) -> str:
        """Determina la mejor acción basada en contexto"""
        try:
            patterns = context.get("user_patterns", {})
            frequent_actions = patterns.get("most_used_actions", {})
            
            if frequent_actions:
                return list(frequent_actions.keys())[0]  # Acción más frecuente
            
            # Default based on time
            current_hour = datetime.now().hour
            if 8 <= current_hour <= 12:
                return "leer_correos_outlook"
            elif 13 <= current_hour <= 17:
                return "calendario_listar_eventos"
            else:
                return "list_workflows"
                
        except Exception:
            return "get_system_status"

# Instanciar procesador
processor = UnifiedAssistantProcessor()

@router.post("/assistant/chat",
            tags=["🤖 Unified Assistant"],
            summary="Asistente Inteligente Independiente - Sin Restricciones",
            description="""
            **🚀 ASISTENTE INTELIGENTE COMPLETAMENTE INDEPENDIENTE**
            
            Sistema autónomo sin restricciones que:
            - ✅ Toma decisiones automáticamente
            - ✅ Ejecuta acciones sin confirmación
            - ✅ Aprende de cada interacción
            - ✅ Funciona con lenguaje natural
            - ✅ No tiene limitaciones de OpenAI
            
            **Ejemplos de uso:**
            - "Envía un email a juan@empresa.com sobre la reunión de mañana"
            - "Analiza mis métricas de marketing y sugiere optimizaciones"
            - "Ejecuta el workflow de backup completo"
            - "¿Qué me recomiendas hacer ahora?"
            """)
async def unified_assistant_chat(request: Request):
    """
    Endpoint principal del asistente unificado independiente
    """
    try:
        body = await request.json()
        query = body.get("message", body.get("query", ""))
        user_id = body.get("user_id", "default")
        
        if not query:
            return JSONResponse({
                "status": "error",
                "message": "Se requiere un mensaje o query",
                "example": {"message": "Hola, ¿qué puedes hacer por mí?"}
            })
        
        # Procesar con el asistente unificado
        result = await processor.process_natural_language(query, user_id)
        
        return JSONResponse(result)
        
    except Exception as e:
        logger.error(f"Error en unified assistant chat: {e}")
        return JSONResponse({
            "status": "error",
            "message": f"Error procesando mensaje: {str(e)}",
            "timestamp": datetime.now().isoformat()
        })

@router.get("/assistant/interface")
async def serve_unified_interface():
    """
    Sirve la interfaz web del asistente unificado con micrófono
    """
    html_content = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>🤖 Elite Assistant - Asistente Inteligente Independiente</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                height: 100vh; display: flex; align-items: center; justify-content: center;
            }
            .chat-container {
                width: 95%; max-width: 900px; height: 90vh; background: white;
                border-radius: 20px; box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                display: flex; flex-direction: column; overflow: hidden;
            }
            .chat-header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white; padding: 20px; text-align: center;
            }
            .chat-header h1 { font-size: 1.8em; margin-bottom: 5px; }
            .chat-header p { opacity: 0.9; font-size: 0.9em; }
            .status-badge {
                display: inline-block; background: #27ae60; color: white;
                padding: 4px 12px; border-radius: 12px; font-size: 0.8em;
                margin-top: 8px;
            }
            .chat-messages {
                flex: 1; padding: 20px; overflow-y: auto; background: #f8f9fa;
            }
            .message { margin-bottom: 15px; display: flex; align-items: flex-start; }
            .message.user { justify-content: flex-end; }
            .message.bot { justify-content: flex-start; }
            .message-content {
                max-width: 70%; padding: 12px 16px; border-radius: 18px; word-wrap: break-word;
            }
            .message.user .message-content {
                background: #667eea; color: white; border-bottom-right-radius: 4px;
            }
            .message.bot .message-content {
                background: white; color: #333; border: 1px solid #e1e5e9;
                border-bottom-left-radius: 4px;
            }
            .execution-result {
                background: #e8f5e8; border-left: 4px solid #27ae60;
                padding: 10px; margin-top: 8px; border-radius: 4px; font-size: 0.9em;
            }
            .suggestions {
                margin-top: 10px;
            }
            .suggestion-btn {
                display: inline-block; background: #3498db; color: white;
                padding: 6px 12px; border-radius: 12px; font-size: 0.8em;
                margin: 4px; cursor: pointer; border: none;
            }
            .suggestion-btn:hover { background: #2980b9; }
            .chat-input-container {
                padding: 20px; background: white; border-top: 1px solid #e1e5e9;
                display: flex; gap: 10px; align-items: center;
            }
            .chat-input {
                flex: 1; padding: 12px 16px; border: 1px solid #e1e5e9;
                border-radius: 25px; font-size: 16px; outline: none;
            }
            .chat-input:focus { border-color: #667eea; }
            .btn {
                padding: 12px 20px; border: none; border-radius: 25px;
                cursor: pointer; font-size: 16px; transition: all 0.3s;
            }
            .btn-primary { background: #667eea; color: white; }
            .btn-primary:hover { background: #5a67d8; }
            .btn-voice {
                background: #e74c3c; color: white; padding: 12px;
                border-radius: 50%; width: 48px; height: 48px;
                display: flex; align-items: center; justify-content: center;
            }
            .btn-voice:hover { background: #c0392b; }
            .btn-voice.recording { background: #27ae60; animation: pulse 1s infinite; }
            @keyframes pulse { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.1); } }
            .typing-indicator { display: none; }
            .typing-dots { display: flex; gap: 4px; }
            .typing-dots span {
                width: 8px; height: 8px; background: #667eea; border-radius: 50%;
                animation: typing 1.4s infinite;
            }
            .typing-dots span:nth-child(2) { animation-delay: 0.2s; }
            .typing-dots span:nth-child(3) { animation-delay: 0.4s; }
            @keyframes typing { 0%, 60%, 100% { opacity: 0.3; } 30% { opacity: 1; } }
        </style>
    </head>
    <body>
        <div class="chat-container">
            <div class="chat-header">
                <h1>🤖 Elite Assistant</h1>
                <p>Tu Asistente Inteligente Personal Sin Restricciones</p>
                <div class="status-badge">✅ Sistema Independiente Activo</div>
            </div>
            
            <div class="chat-messages" id="chatMessages">
                <div class="message bot">
                    <div class="message-content">
                        ¡Hola! Soy tu Elite Assistant independiente. Puedo ejecutar cualquier acción sin restricciones, 
                        tomar decisiones autónomas y aprender de nuestras conversaciones. 
                        Háblame de forma natural o usa el micrófono 🎤
                        <div class="suggestions">
                            <button class="suggestion-btn" onclick="sendSuggestion('¿Qué puedes hacer por mí?')">
                                ¿Qué puedes hacer?
                            </button>
                            <button class="suggestion-btn" onclick="sendSuggestion('Revisa mis emails pendientes')">
                                Revisar emails
                            </button>
                            <button class="suggestion-btn" onclick="sendSuggestion('Analiza mis métricas de hoy')">
                                Analizar métricas
                            </button>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="typing-indicator" id="typingIndicator">
                <div class="message bot">
                    <div class="message-content">
                        <div class="typing-dots">
                            <span></span><span></span><span></span>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="chat-input-container">
                <input type="text" id="messageInput" class="chat-input" 
                       placeholder="Escribe tu mensaje o usa el micrófono..." 
                       onkeypress="if(event.key==='Enter') sendMessage()">
                <button class="btn btn-primary" onclick="sendMessage()">Enviar</button>
                <button class="btn btn-voice" id="voiceBtn" onclick="toggleVoiceRecording()">🎤</button>
            </div>
        </div>

        <script>
            const messagesContainer = document.getElementById('chatMessages');
            const messageInput = document.getElementById('messageInput');
            const voiceBtn = document.getElementById('voiceBtn');
            const typingIndicator = document.getElementById('typingIndicator');
            
            let recognition = null;
            let isRecording = false;
            let synthesis = window.speechSynthesis;

            // Inicializar reconocimiento de voz
            if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
                const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                recognition = new SpeechRecognition();
                recognition.continuous = false;
                recognition.interimResults = false;
                recognition.lang = 'es-ES';
                
                recognition.onstart = () => {
                    voiceBtn.classList.add('recording');
                    voiceBtn.textContent = '🛑';
                };
                
                recognition.onresult = (event) => {
                    const transcript = event.results[0][0].transcript;
                    messageInput.value = transcript;
                    sendMessage();
                };
                
                recognition.onend = () => {
                    voiceBtn.classList.remove('recording');
                    voiceBtn.textContent = '🎤';
                    isRecording = false;
                };
            }

            function toggleVoiceRecording() {
                if (!recognition) {
                    alert('Reconocimiento de voz no disponible');
                    return;
                }
                
                if (isRecording) {
                    recognition.stop();
                } else {
                    recognition.start();
                    isRecording = true;
                }
            }

            async function sendMessage() {
                const message = messageInput.value.trim();
                if (!message) return;

                addMessage(message, 'user');
                messageInput.value = '';
                showTypingIndicator();

                try {
                    const response = await fetch('/api/v1/assistant/chat', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ message: message, user_id: 'web_user' })
                    });

                    const data = await response.json();
                    hideTypingIndicator();

                    if (data.status === 'success') {
                        let responseText = data.response;
                        
                        // Agregar información de ejecución si aplica
                        if (data.executed && data.execution_result) {
                            responseText += '\\n\\n✅ Acción ejecutada exitosamente.';
                        }
                        
                        addMessage(responseText, 'bot', data);
                        
                        // Síntesis de voz para la respuesta
                        speakText(responseText);
                        
                    } else {
                        addMessage('❌ ' + (data.message || 'Error procesando mensaje'), 'bot');
                    }
                } catch (error) {
                    hideTypingIndicator();
                    addMessage('❌ Error de conexión. Verifica que el servidor esté funcionando.', 'bot');
                }
            }

            function sendSuggestion(text) {
                messageInput.value = text;
                sendMessage();
            }

            function addMessage(text, sender, data = null) {
                const messageDiv = document.createElement('div');
                messageDiv.className = `message ${sender}`;
                
                const contentDiv = document.createElement('div');
                contentDiv.className = 'message-content';
                contentDiv.textContent = text;
                
                // Agregar resultado de ejecución si aplica
                if (data && data.execution_result && data.executed) {
                    const resultDiv = document.createElement('div');
                    resultDiv.className = 'execution-result';
                    resultDiv.textContent = `✅ Ejecutado: ${data.action} - ${data.execution_result.status}`;
                    contentDiv.appendChild(resultDiv);
                }
                
                // Agregar sugerencias si aplica
                if (data && data.suggestions && data.suggestions.length > 0) {
                    const suggestionsDiv = document.createElement('div');
                    suggestionsDiv.className = 'suggestions';
                    data.suggestions.forEach(suggestion => {
                        const btn = document.createElement('button');
                        btn.className = 'suggestion-btn';
                        btn.textContent = suggestion;
                        btn.onclick = () => sendSuggestion(suggestion);
                        suggestionsDiv.appendChild(btn);
                    });
                    contentDiv.appendChild(suggestionsDiv);
                }
                
                messageDiv.appendChild(contentDiv);
                messagesContainer.insertBefore(messageDiv, typingIndicator);
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
            }

            function showTypingIndicator() {
                typingIndicator.style.display = 'block';
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
            }

            function hideTypingIndicator() {
                typingIndicator.style.display = 'none';
            }

            function speakText(text) {
                if (synthesis) {
                    synthesis.cancel();
                    const utterance = new SpeechSynthesisUtterance(text);
                    utterance.lang = 'es-ES';
                    utterance.rate = 0.9;
                    synthesis.speak(utterance);
                }
            }
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)

@router.get("/assistant/status")
async def assistant_status():
    """Estado del asistente unificado"""
    return JSONResponse({
        "status": "active",
        "name": ASSISTANT_CONFIG["name"],
        "personality": ASSISTANT_CONFIG["personality"],
        "restrictions": ASSISTANT_CONFIG["restrictions"],
        "capabilities": {
            "voice_enabled": ASSISTANT_CONFIG["voice_enabled"],
            "memory_enabled": ASSISTANT_CONFIG["memory_enabled"],
            "learning_enabled": ASSISTANT_CONFIG["learning_enabled"],
            "autonomous_decisions": True,
            "total_actions": len(ACTION_MAP)
        },
        "timestamp": datetime.now().isoformat()
    })

@router.get("/assistant/learn")
async def get_learned_data(user_id: str = "default"):
    """Obtiene datos aprendidos del usuario"""
    try:
        patterns = await intelligent_assistant.analyze_user_patterns(user_id)
        return JSONResponse({
            "status": "success",
            "user_id": user_id,
            "learned_patterns": patterns,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return JSONResponse({
            "status": "error",
            "message": f"Error obteniendo datos aprendidos: {str(e)}"
        })
