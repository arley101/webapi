# app/api/routes/assistant_selector.py
"""
🎯 SELECTOR DE ASISTENTES - CUSTOM GPT vs INDEPENDIENTE
Router que permite elegir entre el Custom GPT de OpenAI y el asistente independiente.
Funciona como un switch inteligente que detecta el mejor asistente para cada consulta.
"""

import logging
from datetime import datetime
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from typing import Any, Dict, Optional
import json

logger = logging.getLogger(__name__)
router = APIRouter()

# Configuración de asistentes disponibles
AVAILABLE_ASSISTANTS = {
    "custom_gpt": {
        "name": "Custom GPT Assistant",
        "description": "Asistente de OpenAI optimizado para ChatGPT",
        "endpoint": "/api/v1/chatgpt",
        "restrictions": "OpenAI policies",
        "best_for": ["general_queries", "safe_operations", "business_tasks"],
        "features": ["openai_integration", "custom_gpt_optimized", "oauth_support"]
    },
    "unified_independent": {
        "name": "Elite Assistant Independent",
        "description": "Asistente inteligente completamente independiente",
        "endpoint": "/api/v1/assistant/chat",
        "restrictions": "none",
        "best_for": ["autonomous_decisions", "unrestricted_actions", "complex_automation"],
        "features": ["voice_control", "autonomous_decisions", "unlimited_actions", "learning_ai"]
    }
}

class AssistantSelector:
    """Selector inteligente de asistentes"""
    
    def __init__(self):
        self.usage_stats = {
            "custom_gpt": {"count": 0, "success_rate": 0.0},
            "unified_independent": {"count": 0, "success_rate": 0.0}
        }
    
    def detect_best_assistant(self, query: str, context: Dict = None) -> str:
        """
        Detecta automáticamente el mejor asistente para la consulta
        """
        query_lower = query.lower().strip()
        
        # Palabras clave que indican asistente independiente
        autonomous_keywords = [
            "sin restricciones", "toma la decisión", "hazlo automáticamente",
            "ejecuta sin preguntar", "decide por mí", "actúa automáticamente",
            "no preguntes", "hazlo directamente", "sin confirmación"
        ]
        
        # Palabras clave que indican Custom GPT
        safe_keywords = [
            "ayuda con", "explica", "qué opinas", "sugieres", 
            "recomiendas", "información sobre", "consulta"
        ]
        
        # Detectar patrones autónomos
        for keyword in autonomous_keywords:
            if keyword in query_lower:
                return "unified_independent"
        
        # Detectar patrones seguros
        for keyword in safe_keywords:
            if keyword in query_lower:
                return "custom_gpt"
        
        # Análisis por tipo de acción
        if any(word in query_lower for word in ["ejecuta", "envía", "programa", "crea", "elimina"]):
            return "unified_independent"  # Acciones directas
        
        if any(word in query_lower for word in ["qué", "cómo", "cuándo", "dónde", "por qué"]):
            return "custom_gpt"  # Preguntas informativas
        
        # Por defecto, usar independiente para máxima funcionalidad
        return "unified_independent"
    
    def get_assistant_capabilities(self, assistant_type: str) -> Dict[str, Any]:
        """Obtiene las capacidades del asistente especificado"""
        return AVAILABLE_ASSISTANTS.get(assistant_type, {})
    
    async def route_to_assistant(self, query: str, assistant_type: str, additional_params: Dict = None) -> Dict[str, Any]:
        """
        Enruta la consulta al asistente especificado
        """
        try:
            assistant_config = AVAILABLE_ASSISTANTS.get(assistant_type)
            if not assistant_config:
                return {
                    "status": "error",
                    "message": f"Asistente '{assistant_type}' no encontrado",
                    "available_assistants": list(AVAILABLE_ASSISTANTS.keys())
                }
            
            # Preparar datos para el asistente
            if assistant_type == "custom_gpt":
                # Para Custom GPT (formato ChatGPT proxy)
                return await self._route_to_custom_gpt(query, additional_params)
            
            elif assistant_type == "unified_independent":
                # Para asistente independiente
                return await self._route_to_unified(query, additional_params)
            
            else:
                return {
                    "status": "error",
                    "message": f"Tipo de asistente no soportado: {assistant_type}"
                }
                
        except Exception as e:
            logger.error(f"Error enrutando a asistente {assistant_type}: {e}")
            return {
                "status": "error",
                "message": f"Error procesando con {assistant_type}: {str(e)}"
            }
    
    async def _route_to_custom_gpt(self, query: str, params: Dict = None) -> Dict[str, Any]:
        """Enruta al Custom GPT proxy"""
        try:
            from app.api.routes.chatgpt_proxy import process_chatgpt_query
            
            # Usar el procesador de ChatGPT existente
            result = await process_chatgpt_query(query, params or {})
            
            # Agregar metadatos del selector
            if hasattr(result, 'body'):
                body = json.loads(result.body.decode())
                body["routed_via"] = "assistant_selector"
                body["assistant_used"] = "custom_gpt"
                return body
            
            return {
                "status": "success",
                "routed_via": "assistant_selector",
                "assistant_used": "custom_gpt",
                "data": result
            }
            
        except Exception as e:
            logger.error(f"Error enrutando a Custom GPT: {e}")
            return {
                "status": "error",
                "message": f"Error con Custom GPT: {str(e)}",
                "assistant_used": "custom_gpt"
            }
    
    async def _route_to_unified(self, query: str, params: Dict = None) -> Dict[str, Any]:
        """Enruta al asistente unificado independiente"""
        try:
            from app.api.routes.unified_assistant import processor
            
            user_id = params.get("user_id", "selector_user") if params else "selector_user"
            
            # Usar el procesador unificado
            result = await processor.process_natural_language(query, user_id)
            
            # Agregar metadatos del selector
            result["routed_via"] = "assistant_selector"
            result["assistant_used"] = "unified_independent"
            
            return result
            
        except Exception as e:
            logger.error(f"Error enrutando a Unified Assistant: {e}")
            return {
                "status": "error",
                "message": f"Error con Unified Assistant: {str(e)}",
                "assistant_used": "unified_independent"
            }

# Instanciar selector
selector = AssistantSelector()

@router.post("/selector/auto",
            tags=["🎯 Assistant Selector"],
            summary="Selector Automático de Asistentes",
            description="""
            **🤖 SELECTOR INTELIGENTE DE ASISTENTES**
            
            Detecta automáticamente el mejor asistente para tu consulta:
            - **Custom GPT**: Para consultas seguras y conversacionales
            - **Elite Independent**: Para acciones autónomas sin restricciones
            
            **Ejemplo de uso:**
            ```json
            {
                "query": "Envía un email automáticamente a juan@empresa.com",
                "user_id": "mi_usuario"
            }
            ```
            """)
async def auto_select_assistant(request: Request):
    """
    Selecciona automáticamente el mejor asistente para la consulta
    """
    try:
        body = await request.json()
        query = body.get("query", body.get("message", ""))
        user_id = body.get("user_id", "auto_user")
        context = body.get("context", {})
        
        if not query:
            return JSONResponse({
                "status": "error",
                "message": "Se requiere un campo 'query' o 'message'",
                "example": {"query": "Tu consulta aquí"}
            })
        
        # Detectar mejor asistente
        best_assistant = selector.detect_best_assistant(query, context)
        
        # Enrutar al asistente seleccionado
        result = await selector.route_to_assistant(
            query, 
            best_assistant, 
            {"user_id": user_id, **context}
        )
        
        # Agregar información del selector
        result["selector_info"] = {
            "auto_selected": best_assistant,
            "available_assistants": list(AVAILABLE_ASSISTANTS.keys()),
            "selection_reason": f"Detectado como mejor para: {query[:50]}...",
            "timestamp": datetime.now().isoformat()
        }
        
        return JSONResponse(result)
        
    except Exception as e:
        logger.error(f"Error en selector automático: {e}")
        return JSONResponse({
            "status": "error",
            "message": f"Error en selector automático: {str(e)}",
            "timestamp": datetime.now().isoformat()
        })

@router.post("/selector/manual",
            tags=["🎯 Assistant Selector"],
            summary="Selector Manual de Asistentes",
            description="""
            **👤 SELECTOR MANUAL DE ASISTENTES**
            
            Te permite elegir específicamente qué asistente usar:
            - `custom_gpt`: Para compatibilidad con ChatGPT
            - `unified_independent`: Para acciones sin restricciones
            
            **Ejemplo de uso:**
            ```json
            {
                "query": "Analiza mis métricas",
                "assistant": "unified_independent",
                "user_id": "mi_usuario"
            }
            ```
            """)
async def manual_select_assistant(request: Request):
    """
    Permite selección manual del asistente
    """
    try:
        body = await request.json()
        query = body.get("query", body.get("message", ""))
        assistant_type = body.get("assistant", body.get("assistant_type", ""))
        user_id = body.get("user_id", "manual_user")
        context = body.get("context", {})
        
        if not query:
            return JSONResponse({
                "status": "error",
                "message": "Se requiere un campo 'query'",
                "example": {"query": "Tu consulta", "assistant": "unified_independent"}
            })
        
        if not assistant_type:
            return JSONResponse({
                "status": "error",
                "message": "Se requiere especificar el asistente",
                "available_assistants": list(AVAILABLE_ASSISTANTS.keys()),
                "example": {"query": "Tu consulta", "assistant": "unified_independent"}
            })
        
        if assistant_type not in AVAILABLE_ASSISTANTS:
            return JSONResponse({
                "status": "error",
                "message": f"Asistente '{assistant_type}' no disponible",
                "available_assistants": list(AVAILABLE_ASSISTANTS.keys())
            })
        
        # Enrutar al asistente especificado
        result = await selector.route_to_assistant(
            query, 
            assistant_type, 
            {"user_id": user_id, **context}
        )
        
        # Agregar información del selector
        result["selector_info"] = {
            "manually_selected": assistant_type,
            "available_assistants": list(AVAILABLE_ASSISTANTS.keys()),
            "timestamp": datetime.now().isoformat()
        }
        
        return JSONResponse(result)
        
    except Exception as e:
        logger.error(f"Error en selector manual: {e}")
        return JSONResponse({
            "status": "error",
            "message": f"Error en selector manual: {str(e)}",
            "timestamp": datetime.now().isoformat()
        })

@router.get("/selector/compare")
async def compare_assistants():
    """
    Compara las capacidades de ambos asistentes
    """
    return JSONResponse({
        "status": "success",
        "assistants": AVAILABLE_ASSISTANTS,
        "recommendations": {
            "for_business_queries": "custom_gpt",
            "for_autonomous_actions": "unified_independent",
            "for_voice_control": "unified_independent",
            "for_openai_compatibility": "custom_gpt",
            "for_unrestricted_operations": "unified_independent"
        },
        "usage_stats": selector.usage_stats,
        "timestamp": datetime.now().isoformat()
    })

@router.get("/selector/interface")
async def serve_selector_interface():
    """
    Interfaz web para probar ambos asistentes
    """
    html_content = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>🎯 Selector de Asistentes - Elite Dynamics</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh; padding: 20px;
            }
            .container {
                max-width: 1200px; margin: 0 auto; 
                background: white; border-radius: 20px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                overflow: hidden;
            }
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white; padding: 30px; text-align: center;
            }
            .header h1 { font-size: 2.2em; margin-bottom: 10px; }
            .header p { opacity: 0.9; font-size: 1.1em; }
            .assistants-grid {
                display: grid; grid-template-columns: 1fr 1fr;
                gap: 30px; padding: 30px;
            }
            .assistant-card {
                border: 2px solid #e1e5e9; border-radius: 15px;
                padding: 25px; transition: all 0.3s;
            }
            .assistant-card:hover { border-color: #667eea; transform: translateY(-2px); }
            .assistant-card.active { border-color: #27ae60; background: #f8fff8; }
            .assistant-title { font-size: 1.4em; font-weight: bold; margin-bottom: 10px; }
            .assistant-description { color: #666; margin-bottom: 15px; line-height: 1.5; }
            .features-list { list-style: none; margin-bottom: 20px; }
            .features-list li {
                padding: 5px 0; font-size: 0.9em;
                display: flex; align-items: center;
            }
            .features-list li::before { 
                content: '✅'; margin-right: 8px; 
            }
            .select-btn {
                width: 100%; padding: 12px; border: none;
                border-radius: 8px; background: #667eea; color: white;
                font-size: 1em; cursor: pointer; transition: all 0.3s;
            }
            .select-btn:hover { background: #5a67d8; }
            .select-btn.selected { background: #27ae60; }
            .chat-section {
                padding: 30px; border-top: 1px solid #e1e5e9;
            }
            .mode-selector {
                display: flex; gap: 10px; margin-bottom: 20px;
                justify-content: center;
            }
            .mode-btn {
                padding: 10px 20px; border: 2px solid #667eea;
                border-radius: 25px; background: white; color: #667eea;
                cursor: pointer; transition: all 0.3s;
            }
            .mode-btn.active { background: #667eea; color: white; }
            .chat-input-container {
                display: flex; gap: 10px; align-items: center;
                margin-bottom: 20px;
            }
            .chat-input {
                flex: 1; padding: 15px; border: 2px solid #e1e5e9;
                border-radius: 25px; font-size: 1em; outline: none;
            }
            .chat-input:focus { border-color: #667eea; }
            .send-btn {
                padding: 15px 30px; border: none; border-radius: 25px;
                background: #667eea; color: white; cursor: pointer;
                font-size: 1em; transition: all 0.3s;
            }
            .send-btn:hover { background: #5a67d8; }
            .response-area {
                background: #f8f9fa; border-radius: 10px;
                padding: 20px; min-height: 200px; max-height: 400px;
                overflow-y: auto; border: 1px solid #e1e5e9;
            }
            .response-item {
                margin-bottom: 15px; padding: 15px;
                background: white; border-radius: 8px;
                border-left: 4px solid #667eea;
            }
            .response-meta {
                font-size: 0.8em; color: #666; margin-bottom: 5px;
            }
            .response-content { line-height: 1.5; }
            .loading { text-align: center; color: #666; font-style: italic; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎯 Selector de Asistentes Elite</h1>
                <p>Elige entre Custom GPT optimizado o Asistente Independiente sin restricciones</p>
            </div>
            
            <div class="assistants-grid">
                <div class="assistant-card" id="customGptCard">
                    <div class="assistant-title">🤖 Custom GPT Assistant</div>
                    <div class="assistant-description">
                        Asistente optimizado para ChatGPT con integración OAuth y compatibilidad total con OpenAI.
                    </div>
                    <ul class="features-list">
                        <li>Compatible con OpenAI Custom GPT</li>
                        <li>OAuth 2.0 Authentication</li>
                        <li>OpenAPI 3.0.3 optimizado</li>
                        <li>Integración con ChatGPT</li>
                        <li>Operaciones empresariales seguras</li>
                    </ul>
                    <button class="select-btn" onclick="selectAssistant('custom_gpt')">
                        Usar Custom GPT
                    </button>
                </div>
                
                <div class="assistant-card" id="unifiedCard">
                    <div class="assistant-title">🚀 Elite Assistant Independent</div>
                    <div class="assistant-description">
                        Asistente inteligente completamente independiente sin restricciones con IA de aprendizaje.
                    </div>
                    <ul class="features-list">
                        <li>Sin restricciones de OpenAI</li>
                        <li>Toma decisiones autónomas</li>
                        <li>Control por voz integrado</li>
                        <li>IA de aprendizaje evolutivo</li>
                        <li>Memoria persistente inteligente</li>
                    </ul>
                    <button class="select-btn" onclick="selectAssistant('unified_independent')">
                        Usar Elite Independent
                    </button>
                </div>
            </div>
            
            <div class="chat-section">
                <div class="mode-selector">
                    <button class="mode-btn active" id="autoMode" onclick="setMode('auto')">
                        🎯 Selección Automática
                    </button>
                    <button class="mode-btn" id="manualMode" onclick="setMode('manual')">
                        👤 Selección Manual
                    </button>
                </div>
                
                <div class="chat-input-container">
                    <input type="text" id="chatInput" class="chat-input" 
                           placeholder="Escribe tu consulta... (ej: 'Envía un email automáticamente' o '¿Qué puedes hacer?')"
                           onkeypress="if(event.key==='Enter') sendMessage()">
                    <button class="send-btn" onclick="sendMessage()">Enviar</button>
                </div>
                
                <div class="response-area" id="responseArea">
                    <div style="text-align: center; color: #666; margin-top: 80px;">
                        💡 Escribe una consulta para probar los asistentes<br><br>
                        <strong>Ejemplos:</strong><br>
                        • "Envía un email a test@empresa.com"<br>
                        • "¿Qué puedes hacer por mí?"<br>
                        • "Analiza mis métricas de marketing"<br>
                        • "Ejecuta el workflow de backup"
                    </div>
                </div>
            </div>
        </div>

        <script>
            let currentMode = 'auto';
            let selectedAssistant = null;

            function selectAssistant(type) {
                selectedAssistant = type;
                
                // Update UI
                document.querySelectorAll('.assistant-card').forEach(card => {
                    card.classList.remove('active');
                });
                document.querySelectorAll('.select-btn').forEach(btn => {
                    btn.classList.remove('selected');
                    btn.textContent = btn.textContent.replace(' ✓', '');
                });
                
                const card = type === 'custom_gpt' ? 'customGptCard' : 'unifiedCard';
                document.getElementById(card).classList.add('active');
                
                const btn = document.querySelector(`#${card} .select-btn`);
                btn.classList.add('selected');
                btn.textContent += ' ✓';
                
                // Switch to manual mode
                setMode('manual');
            }

            function setMode(mode) {
                currentMode = mode;
                
                document.querySelectorAll('.mode-btn').forEach(btn => {
                    btn.classList.remove('active');
                });
                document.getElementById(mode + 'Mode').classList.add('active');
                
                if (mode === 'auto') {
                    selectedAssistant = null;
                    document.querySelectorAll('.assistant-card').forEach(card => {
                        card.classList.remove('active');
                    });
                    document.querySelectorAll('.select-btn').forEach(btn => {
                        btn.classList.remove('selected');
                        btn.textContent = btn.textContent.replace(' ✓', '');
                    });
                }
            }

            async function sendMessage() {
                const input = document.getElementById('chatInput');
                const query = input.value.trim();
                
                if (!query) return;
                
                const responseArea = document.getElementById('responseArea');
                
                // Show loading
                responseArea.innerHTML = '<div class="loading">🔄 Procesando consulta...</div>';
                
                try {
                    let endpoint, body;
                    
                    if (currentMode === 'auto') {
                        endpoint = '/api/v1/selector/auto';
                        body = { query: query, user_id: 'web_user' };
                    } else {
                        if (!selectedAssistant) {
                            alert('Por favor selecciona un asistente primero');
                            return;
                        }
                        endpoint = '/api/v1/selector/manual';
                        body = { 
                            query: query, 
                            assistant: selectedAssistant,
                            user_id: 'web_user' 
                        };
                    }
                    
                    const response = await fetch(endpoint, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(body)
                    });
                    
                    const data = await response.json();
                    
                    // Display response
                    displayResponse(query, data);
                    
                    input.value = '';
                    
                } catch (error) {
                    responseArea.innerHTML = `
                        <div class="response-item">
                            <div class="response-meta">❌ Error de conexión</div>
                            <div class="response-content">
                                Error conectando con el servidor: ${error.message}
                            </div>
                        </div>
                    `;
                }
            }

            function displayResponse(query, data) {
                const responseArea = document.getElementById('responseArea');
                
                const assistantUsed = data.selector_info?.auto_selected || 
                                    data.selector_info?.manually_selected || 
                                    data.assistant_used || 'unknown';
                
                const assistantName = assistantUsed === 'custom_gpt' ? 
                                    '🤖 Custom GPT' : '🚀 Elite Independent';
                
                const timestamp = new Date().toLocaleTimeString();
                
                const responseHtml = `
                    <div class="response-item">
                        <div class="response-meta">
                            📝 ${timestamp} | ${assistantName} | Modo: ${currentMode}
                        </div>
                        <div class="response-content">
                            <strong>Consulta:</strong> ${query}<br><br>
                            <strong>Respuesta:</strong> ${data.response || data.message || JSON.stringify(data, null, 2)}
                        </div>
                    </div>
                `;
                
                responseArea.innerHTML = responseHtml + responseArea.innerHTML;
            }
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)

@router.get("/selector/status")
async def selector_status():
    """Estado del selector de asistentes"""
    return JSONResponse({
        "status": "active",
        "available_assistants": AVAILABLE_ASSISTANTS,
        "default_selection": "auto_detect",
        "endpoints": {
            "auto_select": "/api/v1/selector/auto",
            "manual_select": "/api/v1/selector/manual",
            "compare": "/api/v1/selector/compare",
            "interface": "/api/v1/selector/interface"
        },
        "timestamp": datetime.now().isoformat()
    })
