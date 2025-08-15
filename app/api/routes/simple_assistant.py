# app/api/routes/simple_assistant.py
"""
Endpoint ULTRA SIMPLE para OpenAI Custom GPT
Solo texto plano - Sin parámetros complicados - Sin errores de formato
"""
import logging
import json
import re
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from datetime import datetime

# Importar lo esencial
from app.core.action_mapper import get_all_actions
from app.shared.helpers.http_client import AuthenticatedHttpClient
from azure.identity import DefaultAzureCredential

logger = logging.getLogger(__name__)
router = APIRouter()

# Mapeo inteligente de comandos a acciones
COMMAND_MAPPINGS = {
    # CORREOS
    r"(lee|muestra|obtén|ver|revisar|consultar).*(correo|email|mail)": {
        "action": "email_list_messages",
        "extract_params": ["email", "cantidad", "mailbox"]
    },
    r"(envía|manda|enviar).*(correo|email|mail)": {
        "action": "email_send_message", 
        "extract_params": ["destinatario", "asunto", "mensaje", "mailbox"]
    },
    
    # CALENDARIO
    r"(crea|crear|programa|agendar).*(reunión|cita|evento|meeting)": {
        "action": "calendario_create_event",
        "extract_params": ["titulo", "fecha", "hora", "participantes"]
    },
    r"(lista|muestra|ver).*(reunión|cita|evento|calendar)": {
        "action": "calendario_list_events",
        "extract_params": ["fecha", "calendario"]
    },
    
    # RUNWAY AI
    r"(genera|crear|hacer).*(video|runway)": {
        "action": "runway_generate_video",
        "extract_params": ["prompt", "duration"]
    },
    r"(estado|status|verificar).*(runway|video)": {
        "action": "runway_get_video_status",
        "extract_params": ["task_id"]
    },
    
    # SHAREPOINT
    r"(subir|upload|cargar).*(archivo|documento|file).*sharepoint": {
        "action": "sharepoint_upload_file",
        "extract_params": ["archivo", "ruta"]
    },
    r"(buscar|encontrar|search).*sharepoint": {
        "action": "sharepoint_search_content",
        "extract_params": ["query", "sitio"]
    },
    
    # TEAMS
    r"(envía|manda|enviar).*(mensaje|teams)": {
        "action": "teams_send_message",
        "extract_params": ["usuario", "mensaje", "canal"]
    },
    
    # GENERAL - CATCH ALL
    r".*": {
        "action": "intelligent_chat",
        "extract_params": ["query"]
    }
}

def extract_email_from_text(text: str) -> Optional[str]:
    """Extrae email del texto usando regex"""
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    matches = re.findall(email_pattern, text)
    return matches[0] if matches else None

def extract_number_from_text(text: str) -> Optional[int]:
    """Extrae números del texto"""
    numbers = re.findall(r'\d+', text)
    return int(numbers[0]) if numbers else None

def smart_parameter_extraction(text: str, action: str) -> Dict[str, Any]:
    """Extrae parámetros inteligentemente del texto natural"""
    params = {}
    text_lower = text.lower()
    
    # Para acciones de email
    if "email" in action:
        # Extraer mailbox/email
        email = extract_email_from_text(text)
        if email:
            params["mailbox"] = email
        
        # Extraer cantidad
        cantidad = extract_number_from_text(text)
        if cantidad:
            params["top_per_page"] = min(cantidad, 20)  # Máximo 20
            
        # Folder por defecto
        params["folder_id"] = "Inbox"
    
    # Para acciones de calendario
    elif "calendario" in action:
        # Extraer fechas básicas
        if "mañana" in text_lower:
            from datetime import datetime, timedelta
            tomorrow = datetime.now() + timedelta(days=1)
            params["start_date"] = tomorrow.strftime("%Y-%m-%d")
        elif "hoy" in text_lower:
            params["start_date"] = datetime.now().strftime("%Y-%m-%d")
            
        # Extraer horarios básicos
        time_match = re.search(r'(\d{1,2}):?(\d{0,2})\s*(am|pm|AM|PM)?', text)
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2)) if time_match.group(2) else 0
            am_pm = time_match.group(3)
            
            if am_pm and am_pm.lower() == 'pm' and hour < 12:
                hour += 12
            elif am_pm and am_pm.lower() == 'am' and hour == 12:
                hour = 0
                
            params["start_time"] = f"{hour:02d}:{minute:02d}"
    
    # Para acciones de Runway
    elif "runway" in action:
        # Extraer prompt después de ciertas palabras clave
        prompt_markers = ["prompt", "descripción", "genera", "crear", "video de", "video con"]
        for marker in prompt_markers:
            if marker in text_lower:
                start_idx = text_lower.find(marker) + len(marker)
                prompt = text[start_idx:].strip()
                if prompt:
                    params["prompt"] = prompt.strip('"\'')
                    break
        
        # Duración por defecto
        if "duration" not in params:
            duration = extract_number_from_text(text)
            params["duration"] = duration if duration and duration <= 30 else 5
    
    # Parámetros generales siempre útiles
    params["query"] = text  # Siempre incluir el texto original
    
    return params

def find_best_action(text: str) -> tuple[str, Dict[str, Any]]:
    """Encuentra la mejor acción basada en el texto usando IA simple"""
    text_lower = text.lower()
    
    for pattern, config in COMMAND_MAPPINGS.items():
        if re.search(pattern, text_lower):
            action = config["action"]
            params = smart_parameter_extraction(text, action)
            
            logger.info(f"Simple Assistant: Matched pattern '{pattern}' -> action '{action}'")
            return action, params
    
    # Fallback - acción por defecto
    return "intelligent_chat", {"query": text}

def format_response_for_human(result: Dict[str, Any], action: str, original_text: str) -> str:
    """Convierte respuesta técnica a texto claro en español"""
    
    if not isinstance(result, dict):
        return f"Resultado: {str(result)}"
    
    # Si hay error, explicarlo claramente
    if result.get("status") == "error":
        error_msg = result.get("message", "Error desconocido")
        return f"❌ No pude completar la tarea: {error_msg}"
    
    # Respuestas específicas por tipo de acción
    if "email" in action:
        if "data" in result and isinstance(result["data"], dict):
            data = result["data"]
            if "value" in data and isinstance(data["value"], list):
                emails = data["value"]
                if emails:
                    response = f"📧 Encontré {len(emails)} correos:\n\n"
                    for i, email in enumerate(emails[:5], 1):  # Máximo 5
                        subject = email.get("subject", "Sin asunto")
                        sender = email.get("sender", {}).get("emailAddress", {}).get("address", "Remitente desconocido")
                        received = email.get("receivedDateTime", "")
                        
                        # Formatear fecha
                        if received:
                            try:
                                from datetime import datetime
                                dt = datetime.fromisoformat(received.replace('Z', '+00:00'))
                                received_formatted = dt.strftime("%d/%m/%Y %H:%M")
                            except:
                                received_formatted = received
                        else:
                            received_formatted = "Fecha desconocida"
                        
                        response += f"{i}. **{subject}**\n"
                        response += f"   De: {sender}\n"
                        response += f"   Fecha: {received_formatted}\n\n"
                    
                    return response
                else:
                    return "📧 No se encontraron correos en tu buzón."
    
    elif "calendario" in action:
        if "data" in result:
            return f"📅 Evento creado/consultado exitosamente."
    
    elif "runway" in action:
        if "data" in result and isinstance(result["data"], dict):
            data = result["data"]
            if "task_id" in data:
                return f"🎬 Video en proceso. ID de tarea: {data['task_id']}"
            elif "status" in data:
                status = data["status"]
                if status == "completed":
                    return "🎬 ¡Video completado exitosamente!"
                elif status == "processing":
                    return "🎬 Video en proceso de generación..."
                else:
                    return f"🎬 Estado del video: {status}"
    
    # Respuesta genérica para otros casos
    if "data" in result:
        data = result["data"]
        if isinstance(data, dict) and "message" in data:
            return data["message"]
        elif isinstance(data, str):
            return data
        else:
            return "✅ Tarea completada exitosamente."
    
    return "✅ Operación realizada correctamente."

@router.post("/simple")
async def simple_assistant(request: Request):
    """
    Endpoint ULTRA SIMPLE - Solo envía texto, recibe texto claro
    
    Formato de entrada:
    {"mensaje": "lee mis últimos 2 correos de ceo@elitecosmeticdental.com"}
    
    Formato de salida:
    {"respuesta": "Encontré 2 correos recientes..."}
    """
    try:
        # Obtener el cuerpo de la request
        raw_body = await request.body()
        
        try:
            body = json.loads(raw_body.decode('utf-8'))
        except json.JSONDecodeError:
            return JSONResponse(
                status_code=400,
                content={
                    "respuesta": "❌ Error: No pude entender el mensaje. Usa formato: {\"mensaje\": \"tu petición aquí\"}",
                    "timestamp": datetime.now().isoformat()
                }
            )
        
        # Extraer mensaje
        mensaje = ""
        if isinstance(body, dict):
            mensaje = body.get("mensaje") or body.get("message") or body.get("text") or body.get("query")
        
        if not mensaje or not isinstance(mensaje, str) or not mensaje.strip():
            return JSONResponse(
                status_code=400,
                content={
                    "respuesta": "❌ Por favor proporciona un mensaje. Ejemplo: {\"mensaje\": \"lee mis correos\"}",
                    "ejemplos": [
                        "lee mis últimos correos",
                        "crea una reunión mañana a las 2pm", 
                        "genera un video de un gato jugando",
                        "busca documentos en SharePoint"
                    ],
                    "timestamp": datetime.now().isoformat()
                }
            )
        
        logger.info(f"Simple Assistant: Received message: {mensaje}")
        
        # PASO 1: Interpretar mensaje y encontrar acción
        action, params = find_best_action(mensaje)
        
        logger.info(f"Simple Assistant: Interpreted as action '{action}' with params: {params}")
        
        # PASO 2: Verificar que la acción existe
        all_actions = get_all_actions()
        if action not in all_actions:
            return JSONResponse(
                status_code=400,
                content={
                    "respuesta": f"❌ No encontré una acción para '{mensaje}'. Intenta ser más específico.",
                    "sugerencias": [
                        "lee mis correos de ceo@ejemplo.com",
                        "crea una reunión mañana",
                        "genera un video con Runway"
                    ],
                    "timestamp": datetime.now().isoformat()
                }
            )
        
        # PASO 3: Ejecutar acción
        action_function = all_actions[action]
        
        try:
            credential = DefaultAzureCredential()
            auth_client = AuthenticatedHttpClient(credential=credential)
        except Exception as auth_error:
            logger.error(f"Authentication error: {auth_error}")
            return JSONResponse(
                status_code=500,
                content={
                    "respuesta": "❌ Error de autenticación. Intenta de nuevo en unos minutos.",
                    "timestamp": datetime.now().isoformat()
                }
            )
        
        # Ejecutar función
        try:
            logger.info(f"Simple Assistant: Executing {action} with params: {params}")
            result = action_function(auth_client, params)
            
            # PASO 4: Convertir respuesta técnica a texto claro
            human_response = format_response_for_human(result, action, mensaje)
            
            logger.info(f"Simple Assistant: Action completed successfully")
            
            return JSONResponse(
                status_code=200,
                content={
                    "respuesta": human_response,
                    "accion_ejecutada": action,
                    "mensaje_original": mensaje,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as exec_error:
            logger.error(f"Execution error for action '{action}': {exec_error}")
            
            # Error específico para el usuario
            error_msg = str(exec_error)
            if "unauthorized" in error_msg.lower():
                user_msg = "❌ No tengo permisos para acceder a ese recurso. Verifica tus credenciales."
            elif "not found" in error_msg.lower():
                user_msg = "❌ No encontré el recurso solicitado. Verifica que existe."
            elif "timeout" in error_msg.lower():
                user_msg = "❌ La operación tardó demasiado. Intenta de nuevo."
            else:
                user_msg = f"❌ Error al ejecutar la tarea: {error_msg}"
            
            return JSONResponse(
                status_code=500,
                content={
                    "respuesta": user_msg,
                    "accion_intentada": action,
                    "mensaje_original": mensaje,
                    "timestamp": datetime.now().isoformat()
                }
            )
    
    except Exception as general_error:
        logger.error(f"General error in simple_assistant: {general_error}")
        return JSONResponse(
            status_code=500,
            content={
                "respuesta": "❌ Error interno del sistema. Intenta de nuevo en unos minutos.",
                "timestamp": datetime.now().isoformat()
            }
        )

@router.get("/simple/help")
async def simple_help():
    """Ayuda y ejemplos para el endpoint simple"""
    return JSONResponse(
        content={
            "titulo": "Asistente Simple - Guía de Uso",
            "descripcion": "Envía comandos en lenguaje natural y recibe respuestas claras",
            "formato": {
                "entrada": '{"mensaje": "tu petición en lenguaje natural"}',
                "salida": '{"respuesta": "respuesta clara en español"}'
            },
            "ejemplos": {
                "correos": [
                    "lee mis últimos 5 correos",
                    "muestra correos de ceo@elitecosmeticdental.com",
                    "envía correo a juan@empresa.com con asunto Reunión"
                ],
                "calendario": [
                    "crea reunión mañana a las 2pm con el equipo",
                    "agenda cita hoy a las 10am",
                    "muestra mis eventos de hoy"
                ],
                "runway": [
                    "genera video de un perro corriendo en el parque",
                    "crea video con prompt gato jugando",
                    "verifica estado del video task_123"
                ],
                "sharepoint": [
                    "busca documentos sobre proyecto Alpha",
                    "sube archivo contrato.pdf a SharePoint"
                ],
                "teams": [
                    "envía mensaje a @juan en Teams diciendo hola",
                    "manda mensaje al canal general"
                ]
            },
            "ventajas": [
                "Sin parámetros complicados",
                "Lenguaje natural en español", 
                "Respuestas claras y directas",
                "Funciona con todas las 468 acciones"
            ]
        }
    )
