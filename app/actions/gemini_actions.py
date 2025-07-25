import google.generativeai as genai
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

# Configurar logging
logger = logging.getLogger(__name__)

def _handle_gemini_api_error(error: Exception, action_name: str) -> Dict[str, Any]:
    """Maneja errores de la API de Gemini de forma centralizada."""
    error_message = f"Error en {action_name}: {str(error)}"
    logger.error(error_message)
    
    return {
        "success": False,
        "error": error_message,
        "timestamp": datetime.now().isoformat()
    }

def _validate_gemini_response(response: Any, action_name: str) -> bool:
    """Valida que la respuesta de Gemini sea válida."""
    try:
        if not response or not hasattr(response, 'text'):
            logger.warning(f"Respuesta vacía o inválida en {action_name}")
            return False
        
        if not response.text or response.text.strip() == "":
            logger.warning(f"Texto de respuesta vacío en {action_name}")
            return False
            
        return True
    except Exception as e:
        logger.error(f"Error validando respuesta en {action_name}: {str(e)}")
        return False

def analyze_conversation_context(conversation_data: Dict[str, Any]) -> Dict[str, Any]:
    """Analiza el contexto de una conversación usando Gemini."""
    action_name = "analyze_conversation_context"
    
    try:
        if not conversation_data:
            return {
                "success": False,
                "error": "Datos de conversación requeridos",
                "timestamp": datetime.now().isoformat()
            }
        
        model = genai.GenerativeModel('gemini-pro')
        
        prompt = f"""
        Analiza el siguiente contexto de conversación y proporciona insights:
        
        Datos de conversación: {json.dumps(conversation_data, indent=2)}
        
        Por favor, proporciona tu análisis en formato JSON con las siguientes claves:
        - sentiment: sentimiento general (positive, negative, neutral)
        - key_topics: lista de temas principales
        - urgency_level: nivel de urgencia (low, medium, high)
        - suggested_actions: acciones recomendadas
        - confidence_score: puntuación de confianza (0-100)
        """
        
        response = model.generate_content(prompt)
        
        if not _validate_gemini_response(response, action_name):
            return _handle_gemini_api_error(
                Exception("Respuesta inválida de Gemini"), 
                action_name
            )
        
        try:
            analysis_json = json.loads(response.text)
        except json.JSONDecodeError:
            analysis_json = {
                "sentiment": "neutral",
                "key_topics": ["general"],
                "urgency_level": "medium",
                "suggested_actions": ["follow_up"],
                "confidence_score": 50,
                "raw_response": response.text
            }
        
        return {
            "success": True,
            "data": analysis_json,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return _handle_gemini_api_error(e, action_name)

def generate_response_suggestions(context: str, user_message: str) -> Dict[str, Any]:
    """Genera sugerencias de respuesta basadas en el contexto."""
    action_name = "generate_response_suggestions"
    
    try:
        if not context or not user_message:
            return {
                "success": False,
                "error": "Contexto y mensaje de usuario requeridos",
                "timestamp": datetime.now().isoformat()
            }
        
        model = genai.GenerativeModel('gemini-pro')
        
        prompt = f"""
        Basándote en el siguiente contexto y mensaje del usuario, genera 3 sugerencias de respuesta profesionales:
        
        Contexto: {context}
        Mensaje del usuario: {user_message}
        
        Proporciona las sugerencias en formato JSON con esta estructura:
        {{
            "suggestions": [
                {{
                    "text": "texto de la sugerencia",
                    "tone": "professional/friendly/formal",
                    "priority": "high/medium/low"
                }}
            ]
        }}
        """
        
        response = model.generate_content(prompt)
        
        if not _validate_gemini_response(response, action_name):
            return _handle_gemini_api_error(
                Exception("Respuesta inválida de Gemini"), 
                action_name
            )
        
        try:
            suggestion_json = json.loads(response.text)
        except json.JSONDecodeError:
            suggestion_json = {
                "suggestions": [
                    {
                        "text": "Gracias por tu mensaje. Te ayudaré con tu consulta.",
                        "tone": "professional",
                        "priority": "medium"
                    }
                ]
            }
        
        return {
            "success": True,
            "data": suggestion_json,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return _handle_gemini_api_error(e, action_name)

def extract_key_information(text: str, extraction_type: str = "general") -> Dict[str, Any]:
    """Extrae información clave de un texto usando Gemini."""
    action_name = "extract_key_information"
    
    try:
        if not text:
            return {
                "success": False,
                "error": "Texto requerido para extracción",
                "timestamp": datetime.now().isoformat()
            }
        
        model = genai.GenerativeModel('gemini-pro')
        
        extraction_prompts = {
            "general": "Extrae información clave general",
            "contact": "Extrae información de contacto (nombres, emails, teléfonos)",
            "business": "Extrae información comercial (productos, servicios, precios)",
            "technical": "Extrae información técnica (especificaciones, requisitos)"
        }
        
        prompt_instruction = extraction_prompts.get(extraction_type, extraction_prompts["general"])
        
        prompt = f"""
        {prompt_instruction} del siguiente texto:
        
        Texto: {text}
        
        Proporciona la información extraída en formato JSON con claves descriptivas.
        """
        
        response = model.generate_content(prompt)
        
        if not _validate_gemini_response(response, action_name):
            return _handle_gemini_api_error(
                Exception("Respuesta inválida de Gemini"), 
                action_name
            )
        
        try:
            extracted_info = json.loads(response.text)
        except json.JSONDecodeError:
            extracted_info = {
                "extraction_type": extraction_type,
                "raw_response": response.text,
                "confidence": "low"
            }
        
        return {
            "success": True,
            "data": extracted_info,
            "extraction_type": extraction_type,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return _handle_gemini_api_error(e, action_name)

def summarize_conversation(messages: List[Dict[str, Any]], max_length: int = 500) -> Dict[str, Any]:
    """Crea un resumen de una conversación."""
    action_name = "summarize_conversation"
    
    try:
        if not messages:
            return {
                "success": False,
                "error": "Lista de mensajes requerida",
                "timestamp": datetime.now().isoformat()
            }
        
        model = genai.GenerativeModel('gemini-pro')
        
        conversation_text = "\n".join([
            f"{msg.get('sender', 'Unknown')}: {msg.get('content', '')}"
            for msg in messages
        ])
        
        prompt = f"""
        Crea un resumen conciso de la siguiente conversación (máximo {max_length} caracteres):
        
        Conversación:
        {conversation_text}
        
        El resumen debe incluir:
        - Puntos principales discutidos
        - Decisiones tomadas
        - Acciones pendientes
        
        Formato JSON:
        {{
            "summary": "resumen de la conversación",
            "key_points": ["punto1", "punto2"],
            "action_items": ["acción1", "acción2"],
            "participants": ["participante1", "participante2"]
        }}
        """
        
        response = model.generate_content(prompt)
        
        if not _validate_gemini_response(response, action_name):
            return _handle_gemini_api_error(
                Exception("Respuesta inválida de Gemini"), 
                action_name
            )
        
        try:
            summary_json = json.loads(response.text)
        except json.JSONDecodeError:
            summary_json = {
                "summary": "Resumen no disponible",
                "key_points": [],
                "action_items": [],
                "participants": []
            }
        
        return {
            "success": True,
            "data": summary_json,
            "message_count": len(messages),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return _handle_gemini_api_error(e, action_name)

def classify_message_intent(message: str) -> Dict[str, Any]:
    """Clasifica la intención de un mensaje."""
    action_name = "classify_message_intent"
    
    try:
        if not message:
            return {
                "success": False,
                "error": "Mensaje requerido para clasificación",
                "timestamp": datetime.now().isoformat()
            }
        
        model = genai.GenerativeModel('gemini-pro')
        
        prompt = f"""
        Clasifica la intención del siguiente mensaje:
        
        Mensaje: {message}
        
        Proporciona la clasificación en formato JSON:
        {{
            "primary_intent": "question/request/complaint/compliment/information",
            "confidence": 0.0-1.0,
            "categories": ["category1", "category2"],
            "urgency": "low/medium/high",
            "requires_response": true/false
        }}
        """
        
        response = model.generate_content(prompt)
        
        if not _validate_gemini_response(response, action_name):
            return _handle_gemini_api_error(
                Exception("Respuesta inválida de Gemini"), 
                action_name
            )
        
        try:
            classification_json = json.loads(response.text)
        except json.JSONDecodeError:
            classification_json = {
                "primary_intent": "information",
                "confidence": 0.5,
                "categories": ["general"],
                "urgency": "medium",
                "requires_response": True
            }
        
        return {
            "success": True,
            "data": classification_json,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return _handle_gemini_api_error(e, action_name)