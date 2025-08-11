"""
Gemini AI Actions - Integración con Google Gemini para análisis inteligente
"""
import json
import logging
from typing import Dict, Any, List, Optional
import requests
from datetime import datetime
import re

from app.core.config import settings
# ✅ IMPORTACIÓN DIRECTA DEL RESOLVER PARA EVITAR CIRCULARIDAD
def _get_resolver():
    from app.actions.resolver_actions import Resolver
    return Resolver()

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURACIÓN Y CONSTANTES
# ============================================================================

# URL de la API correcta para Gemini
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1"
GEMINI_MODEL = getattr(settings, "GEMINI_MODEL", "gemini-1.5-flash")  # Permite override desde settings

def _get_gemini_url():
    """Construye la URL correcta para Gemini API"""
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        raise ValueError("GEMINI_API_KEY no configurado")
    
    # Usar v1 en lugar de v1beta
    return f"{GEMINI_API_BASE}/models/{GEMINI_MODEL}:generateContent?key={api_key}"

def _make_gemini_request(prompt: str, system_instruction: Optional[str] = None) -> Dict[str, Any]:
    """Realiza una solicitud a Gemini API con manejo de errores mejorado"""
    try:
        url = _get_gemini_url()
        
        # Construir el payload según la documentación de Gemini
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.7,
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 8192,
            }
        }
        
        # Agregar system instruction si existe
        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [
                    {"text": system_instruction}
                ]
            }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        logger.info(f"Llamando a Gemini API: {GEMINI_MODEL}")
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            
            # Extraer el texto de la respuesta
            if "candidates" in result and len(result["candidates"]) > 0:
                content = result["candidates"][0].get("content", {})
                parts = content.get("parts", [])
                if parts and "text" in parts[0]:
                    return {
                        "success": True,
                        "text": parts[0]["text"],
                        "raw_response": result
                    }
            
            return {
                "success": False,
                "error": "No se pudo extraer respuesta de Gemini",
                "raw_response": result
            }
            
        else:
            content_type = (response.headers.get('content-type') or '').lower()
            error_data = response.json() if 'application/json' in content_type else {}
            logger.error(f"Error de Gemini API: {response.status_code} - {error_data}")
            
            return {
                "success": False,
                "error": error_data.get("error", {}).get("message", f"Error {response.status_code}"),
                "status_code": response.status_code,
                "details": error_data
            }
            
    except requests.exceptions.Timeout:
        logger.error("Timeout al llamar a Gemini API")
        return {
            "success": False,
            "error": "Timeout al contactar Gemini API"
        }
    except Exception as e:
        logger.error(f"Error inesperado en Gemini API: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

# ============================================================================
# FUNCIONES PÚBLICAS
# ============================================================================

def analyze_conversation_context(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analiza el contexto de una conversación y recomienda acciones.
    MEJORADO: Ahora devuelve respuestas ejecutables directamente
    """
    logger.info("🤖 Analizando contexto de conversación con Gemini")
    
    try:
        conversation_data = params.get('conversation_data', {})
        query = conversation_data.get('query', '')
        available_actions = conversation_data.get('available_actions', [])
        context = conversation_data.get('context', {})
        
        # IMPORTANTE: Usar el modelo correcto
        model_name = context.get('model', 'gemini-1.5-flash')
        
        # Construir prompt mejorado para respuestas ejecutables
        prompt = f"""
        Analiza esta solicitud y devuelve ÚNICAMENTE un JSON válido con la acción a ejecutar.
        
        Solicitud del usuario: "{query}"
        
        Contexto:
        - Cliente ID: {context.get('customer_id', '1415018442')}
        - Email: {context.get('mailbox', 'ceo@elitecosmeticdental.com')}
        - Empresa: {context.get('company', 'Elite Cosmetic Dental')}
        
        Acciones disponibles más relevantes:
        - email_list_messages: listar correos (params: mailbox, top)
        - email_send_message: enviar correo (params: to, subject, body)
        - calendar_list_events: listar eventos (params: mailbox, top)
        - search_web: buscar en web (params: query, limit)
        - sp_list_folder_contents: listar archivos SharePoint (params: folder_path, top)
        - onedrive_list_items: listar archivos OneDrive (params: path, top)
        - youtube_get_channel_info: info del canal YouTube (params: ninguno)
        - metaads_list_campaigns: listar campañas Meta (params: account_id)
        - googleads_get_campaigns: listar campañas Google (params: customer_id)
        
        ANALIZA e INTERPRETA la solicitud:
        - Si dice "archivos recientes de OneDrive", usa onedrive_list_items
        - Si dice "correos" o "emails", usa email_list_messages
        - Si dice "buscar" o "información sobre", usa search_web
        - Si menciona "SharePoint" o "documentos", usa sp_list_folder_contents
        - Si menciona "calendario" o "eventos", usa calendar_list_events
        
        IMPORTANTE: Responde SOLO con este JSON:
        {{
            "intent": "descripción de lo que el usuario quiere",
            "confidence": 0.95,
            "recommended_action": "nombre_exacto_de_la_acción",
            "parameters": {{
                "param1": "valor1",
                "param2": "valor2"
            }}
        }}
        
        Si el usuario dice "muéstrame archivos recientes de OneDrive de Arley", debes responder:
        {{"intent": "listar archivos OneDrive", "confidence": 0.95, "recommended_action": "onedrive_list_items", "parameters": {{"path": "/", "top": 20}}}}
        
        Responde SOLO con el JSON, sin texto adicional.
        """
        
        # Verificar si el cliente tiene el modelo correcto configurado
        if not hasattr(client, 'genai') or not client.genai:
            # Si no hay cliente Gemini, usar un análisis basado en patrones
            return _fallback_pattern_analysis(query, available_actions)
        
        # Configurar el modelo
        model = client.genai.GenerativeModel(model_name)
        
        # Generar respuesta
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        logger.info(f"Respuesta cruda de Gemini: {response_text}")
        
        # Intentar parsear el JSON
        try:
            # Limpiar la respuesta si tiene markdown
            if response_text.startswith('```'):
                response_text = response_text.split('```')[1]
                if response_text.startswith('json'):
                    response_text = response_text[4:]
                response_text = response_text.strip()
            
            analysis = json.loads(response_text)
            
            # Validar que tenga los campos necesarios
            if 'recommended_action' not in analysis:
                raise ValueError("Falta recommended_action en la respuesta")
            
            if 'parameters' not in analysis:
                analysis['parameters'] = {}
            
            logger.info(f"✅ Análisis parseado correctamente: {analysis}")
            
            return {
                "success": True,
                "data": {
                    "analysis": analysis,
                    "model_used": model_name
                }
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parseando JSON de Gemini: {e}")
            logger.error(f"Respuesta que causó el error: {response_text}")
            
            # Usar análisis de patrones como fallback
            return _fallback_pattern_analysis(query, available_actions)
        
    except Exception as e:
        logger.error(f"Error en analyze_conversation_context: {str(e)}")
        # Si Gemini falla completamente, usar análisis de patrones
        return _fallback_pattern_analysis(query, available_actions)

def _fallback_pattern_analysis(query: str, available_actions: List[str]) -> Dict[str, Any]:
    """
    Análisis de patrones como fallback cuando Gemini no está disponible
    """
    logger.info("Usando análisis de patrones como fallback")
    
    query_lower = query.lower()
    
    # Mapeo de patrones a acciones
    pattern_map = {
        # OneDrive
        r'onedrive|one drive|archivos.*onedrive': {
            'action': 'onedrive_list_items',
            'params': {'path': '/', 'top': 20},
            'intent': 'listar archivos de OneDrive'
        },
        # Email
        r'correo|email|mensaje|mail': {
            'action': 'email_list_messages',
            'params': {'mailbox': 'ceo@elitecosmeticdental.com', 'top': 10},
            'intent': 'listar correos electrónicos'
        },
        # SharePoint
        r'sharepoint|documento|archivo': {
            'action': 'sp_list_folder_contents',
            'params': {'folder_path': '/', 'top': 20},
            'intent': 'listar documentos de SharePoint'
        },
        # Calendar
        r'calendario|evento|reunión|cita': {
            'action': 'calendar_list_events',
            'params': {'mailbox': 'ceo@elitecosmeticdental.com', 'top': 10},
            'intent': 'listar eventos del calendario'
        },
        # Web search
        r'buscar|búsqueda|información sobre|investigar': {
            'action': 'search_web',
            'params': {'query': query, 'limit': 5},
            'intent': 'buscar información en la web'
        },
        # YouTube
        r'youtube|canal|video': {
            'action': 'youtube_get_channel_info',
            'params': {},
            'intent': 'obtener información del canal de YouTube'
        },
        # Teams
        r'teams|equipo|chat': {
            'action': 'teams_list_joined_teams',
            'params': {'top': 10},
            'intent': 'listar equipos de Teams'
        }
    }
    
    # Buscar coincidencias
    for pattern, config in pattern_map.items():
        if re.search(pattern, query_lower):
            # Extraer números si existen
            numbers = re.findall(r'\d+', query)
            if numbers and 'top' in config['params']:
                config['params']['top'] = int(numbers[0])
            
            return {
                "success": True,
                "data": {
                    "analysis": {
                        "intent": config['intent'],
                        "confidence": 0.85,
                        "recommended_action": config['action'],
                        "parameters": config['params']
                    },
                    "model_used": "pattern_matching"
                }
            }
    
    # Si no hay coincidencia, usar búsqueda web como último recurso
    return {
        "success": True,
        "data": {
            "analysis": {
                "intent": "búsqueda general",
                "confidence": 0.6,
                "recommended_action": "search_web",
                "parameters": {
                    "query": query,
                    "limit": 5
                }
            },
            "model_used": "default_fallback"
        }
    }

# ============================================================================
# FUNCIONES PÚBLICAS (CONTINUACIÓN)
# ============================================================================

def generate_response_suggestions(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Genera sugerencias de respuesta basadas en el contexto"""
    try:
        context = params.get("context", {})
        message = params.get("message", "")
        tone = params.get("tone", "professional")
        
        prompt = f"""Genera 3 sugerencias de respuesta para este mensaje:
"{message}"

Tono deseado: {tone}
Contexto: Comunicación empresarial para Elite Cosmetic Dental

Proporciona respuestas variadas: una breve, una detallada y una con siguiente acción."""

        gemini_response = _make_gemini_request(prompt)
        
        if not gemini_response.get("success"):
            return {
                "success": False,
                "error": gemini_response.get("error", "Error generando sugerencias")
            }
        
        suggestions_text = gemini_response.get("text", "")
        
        # Procesar las sugerencias
        suggestions = []
        lines = suggestions_text.split('\n')
        current_suggestion = ""
        
        for line in lines:
            if line.strip() and (line.startswith('1.') or line.startswith('2.') or line.startswith('3.')):
                if current_suggestion:
                    suggestions.append(current_suggestion.strip())
                current_suggestion = line[2:].strip()
            elif current_suggestion:
                current_suggestion += " " + line.strip()
        
        if current_suggestion:
            suggestions.append(current_suggestion.strip())
        
        result = {
            "success": True,
            "data": {
                "suggestions": suggestions[:3],  # Limitar a 3
                "context": context,
                "tone": tone
            }
        }
        
        # ✅ PERSISTENCIA DE MEMORIA - FUNCIÓN DE GENERACIÓN
        _get_resolver().save_action_result("generate_response_suggestions", params, result)
        
        return result
        
    except Exception as e:
        logger.error(f"Error en generate_response_suggestions: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

def extract_key_information(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Extrae información clave de un texto"""
    try:
        text = params.get("text", "")
        info_types = params.get("info_types", ["dates", "contacts", "actions", "urls"])
        
        prompt = f"""Extrae la siguiente información del texto:
{', '.join(info_types)}

Texto:
"{text}"

Formato de respuesta:
- dates: lista de fechas mencionadas
- contacts: nombres, emails, teléfonos
- actions: acciones requeridas o mencionadas
- urls: enlaces web
- key_points: puntos principales

Responde en formato JSON."""

        gemini_response = _make_gemini_request(prompt)
        
        if not gemini_response.get("success"):
            return {
                "success": False,
                "error": gemini_response.get("error", "Error extrayendo información")
            }
        
        # Procesar respuesta
        response_text = gemini_response.get("text", "")
        
        try:
            # Extraer JSON de la respuesta
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                json_str = response_text[json_start:json_end].strip()
                extracted_info = json.loads(json_str)
            else:
                # Crear estructura básica si no hay JSON
                extracted_info = {
                    "dates": [],
                    "contacts": [],
                    "actions": [],
                    "urls": [],
                    "key_points": [response_text]
                }
        except Exception as e:
            logger.error(f"No se pudo parsear respuesta JSON de Gemini: {e}")
            extracted_info = {
                "raw_extraction": response_text,
                "parse_error": str(e)
            }
        
        result = {
            "success": True,
            "data": {
                "extracted_information": extracted_info,
                "text_length": len(text),
                "info_types_requested": info_types
            }
        }
        
        # ✅ PERSISTENCIA DE MEMORIA - FUNCIÓN DE ANÁLISIS/EXTRACCIÓN
        _get_resolver().save_action_result("extract_key_information", params, result)
        
        return result
        
    except Exception as e:
        logger.error(f"Error en extract_key_information: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

def summarize_conversation(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Resume una conversación o serie de mensajes"""
    try:
        messages = params.get("messages", [])
        summary_type = params.get("summary_type", "executive")
        max_length = params.get("max_length", 500)
        
        # Construir el contexto de la conversación
        conversation_text = "\n".join([
            f"{msg.get('sender', 'Unknown')}: {msg.get('content', '')}"
            for msg in messages
        ])
        
        prompt = f"""Resume esta conversación de manera {summary_type}:

{conversation_text}

Requisitos:
- Máximo {max_length} caracteres
- Incluir puntos clave
- Mencionar decisiones o acciones pendientes
- Tono profesional y ejecutivo"""

        gemini_response = _make_gemini_request(prompt)
        
        if not gemini_response.get("success"):
            return {
                "success": False,
                "error": gemini_response.get("error", "Error generando resumen")
            }
        
        summary = gemini_response.get("text", "")
        
        # Truncar si es necesario
        if len(summary) > max_length:
            summary = summary[:max_length-3] + "..."
        
        result = {
            "success": True,
            "data": {
                "summary": summary,
                "message_count": len(messages),
                "summary_type": summary_type,
                "length": len(summary)
            }
        }
        
        # ✅ PERSISTENCIA DE MEMORIA - FUNCIÓN DE GENERACIÓN
        _get_resolver().save_action_result("summarize_conversation", params, result)
        
        return result
        
    except Exception as e:
        logger.error(f"Error en summarize_conversation: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

def classify_message_intent(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Clasifica la intención de un mensaje"""
    try:
        message = params.get("message", "")
        categories = params.get("categories", [
            "request", "information", "complaint", "confirmation", 
            "question", "action_required", "follow_up"
        ])
        
        prompt = f"""Clasifica este mensaje en una de estas categorías:
{', '.join(categories)}

Mensaje: "{message}"

Proporciona:
1. Categoría principal
2. Confianza (0-100%)
3. Categorías secundarias si aplican
4. Urgencia detectada (baja/media/alta)
5. Sentimiento (positivo/neutral/negativo)"""

        gemini_response = _make_gemini_request(prompt)
        
        if not gemini_response.get("success"):
            return {
                "success": False,
                "error": gemini_response.get("error", "Error clasificando mensaje")
            }
        
        # Procesar respuesta
        response_text = gemini_response.get("text", "")
        
        # Extraer información de la respuesta
        classification = {
            "primary_category": "information",  # default
            "confidence": 70,
            "secondary_categories": [],
            "urgency": "media",
            "sentiment": "neutral"
        }
        
        # Buscar patrones en la respuesta
        lines = response_text.lower().split('\n')
        for line in lines:
            if "categoría principal:" in line or "1." in line:
                for cat in categories:
                    if cat in line:
                        classification["primary_category"] = cat
                        break
            elif "confianza:" in line:
                try:
                    conf = int(''.join(filter(str.isdigit, line)))
                    classification["confidence"] = min(100, max(0, conf))
                except:
                    pass
            elif "urgencia:" in line:
                if "alta" in line:
                    classification["urgency"] = "alta"
                elif "baja" in line:
                    classification["urgency"] = "baja"
            elif "sentimiento:" in line:
                if "positiv" in line:
                    classification["sentiment"] = "positivo"
                elif "negativ" in line:
                    classification["sentiment"] = "negativo"
        
        return {
            "success": True,
            "data": {
                "classification": classification,
                "message_length": len(message),
                "available_categories": categories
            }
        }
        
    except Exception as e:
        logger.error(f"Error en classify_message_intent: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

def generate_execution_plan(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Genera un plan de ejecución detallado para una tarea compleja"""
    try:
        task_description = params.get("task_description", "")
        available_resources = params.get("available_resources", [])
        constraints = params.get("constraints", {})
        
        prompt = f"""Crea un plan de ejecución detallado para esta tarea:
"{task_description}"

Recursos disponibles:
{', '.join(available_resources[:20])}

Restricciones:
- Tiempo: {constraints.get('time', 'No especificado')}
- Presupuesto: {constraints.get('budget', 'No especificado')}
- Prioridad: {constraints.get('priority', 'Normal')}

Genera un plan paso a paso con:
1. Acciones específicas a ejecutar
2. Orden de ejecución
3. Dependencias entre pasos
4. Tiempo estimado
5. Recursos necesarios para cada paso"""

        gemini_response = _make_gemini_request(prompt)
        
        if not gemini_response.get("success"):
            return {
                "success": False,
                "error": gemini_response.get("error", "Error generando plan")
            }
        
        plan_text = gemini_response.get("text", "")
        
        # Estructurar el plan
        plan_steps = []
        current_step = {}
        
        lines = plan_text.split('\n')
        step_number = 0
        
        for line in lines:
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith('-')):
                if current_step:
                    plan_steps.append(current_step)
                step_number += 1
                current_step = {
                    "step": step_number,
                    "description": line.lstrip('0123456789.- '),
                    "details": []
                }
            elif current_step and line:
                current_step["details"].append(line)
        
        if current_step:
            plan_steps.append(current_step)
        
        result = {
            "success": True,
            "data": {
                "execution_plan": {
                    "task": task_description,
                    "total_steps": len(plan_steps),
                    "steps": plan_steps,
                    "constraints": constraints,
                    "generated_at": datetime.now().isoformat()
                }
            }
        }
        
        # ✅ PERSISTENCIA DE MEMORIA - FUNCIÓN DE GENERACIÓN
        _get_resolver().save_action_result("generate_execution_plan", params, result)
        
        return result
        
    except Exception as e:
        logger.error(f"Error en generate_execution_plan: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

# Alias para compatibilidad
gemini_suggest_action = generate_response_suggestions