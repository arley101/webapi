import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import google.generativeai as genai
from app.core.config import settings

logger = logging.getLogger(__name__)

# Configurar Gemini
genai.configure(api_key=settings.GEMINI_API_KEY)

# Actualizar el modelo a usar
GEMINI_MODEL = "gemini-1.5-flash"  # Cambiar de gemini-pro a gemini-1.5-flash

def analyze_conversation_context(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Versión mejorada con capacidad de decisión autónoma"""
    try:
        conversation_data = params.get("conversation_data", {})
        
        # Detectar el tipo de análisis requerido
        task_type = conversation_data.get('task', 'general_analysis')
        
        # Prompts especializados según la tarea
        specialized_prompts = {
            'analyze_and_decide_storage': """
            Eres un experto en arquitectura de información. Analiza el contenido y decide:
            1. La mejor plataforma de almacenamiento principal
            2. Plataformas secundarias para redundancia o acceso
            3. Metadata relevante a agregar
            4. Acciones adicionales necesarias (resúmenes, notificaciones, etc.)
            5. Tags inteligentes para clasificación
            
            Considera:
            - SharePoint: Mejor para documentos estructurados, listas, registros
            - OneDrive: Ideal para multimedia (videos, imágenes, audio)
            - Notion: Perfecto para bases de datos, dashboards, wikis
            - Teams: Para notificaciones y colaboración
            
            Responde SOLO en formato JSON válido.
            """,
            
            'optimize_workflow': """
            Eres un experto en optimización de procesos. Analiza el workflow y:
            1. Identifica pasos que pueden ejecutarse en paralelo
            2. Detecta redundancias o pasos innecesarios
            3. Sugiere pasos adicionales que faltan
            4. Propón el orden óptimo de ejecución
            5. Identifica puntos de falla potenciales
            
            Responde con un plan de ejecución optimizado en JSON.
            """,
            
            'extract_search_terms': """
            Extrae 3-5 términos de búsqueda clave del contenido.
            Prioriza:
            1. Nombres de productos o servicios
            2. Tecnologías mencionadas
            3. Problemas o necesidades
            4. Competidores o alternativas
            
            Responde con los términos separados por espacios.
            """,
            
            'general_analysis': """
            Analiza el contexto completo y proporciona:
            1. Resumen ejecutivo
            2. Puntos clave identificados
            3. Acciones recomendadas
            4. Riesgos o consideraciones
            5. Siguiente mejor paso
            """
        }
        
        # Seleccionar el prompt adecuado
        system_prompt = specialized_prompts.get(task_type, specialized_prompts['general_analysis'])
        
        # Agregar contexto adicional si está disponible
        if 'instructions' in conversation_data:
            system_prompt += f"\n\nInstrucciones adicionales:\n{conversation_data['instructions']}"
        
        # Construir el mensaje para Gemini
        user_message = json.dumps(conversation_data, ensure_ascii=False)
        
        # Llamar a Gemini
        response = client.post(
            f"{settings.GEMINI_API_URL}/models/gemini-pro:generateContent",
            headers={
                "Content-Type": "application/json",
            },
            params={
                "key": settings.GEMINI_API_KEY
            },
            json={
                "contents": [{
                    "parts": [{
                        "text": f"{system_prompt}\n\nDatos a analizar:\n{user_message}"
                    }]
                }],
                "generationConfig": {
                    "temperature": 0.3,  # Más determinista para decisiones
                    "topK": 40,
                    "topP": 0.95,
                    "maxOutputTokens": 2048,
                }
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            generated_text = result['candidates'][0]['content']['parts'][0]['text']
            
            # Intentar parsear como JSON si es posible
            parsed_response = generated_text
            try:
                parsed_response = json.loads(generated_text)
            except:
                # Si no es JSON válido, intentar extraer JSON del texto
                import re
                json_match = re.search(r'\{.*\}', generated_text, re.DOTALL)
                if json_match:
                    try:
                        parsed_response = json.loads(json_match.group())
                    except:
                        pass
            
            return {
                "success": True,
                "data": {
                    "response": parsed_response,
                    "raw_response": generated_text,
                    "task_type": task_type,
                    "model": "gemini-pro"
                }
            }
        else:
            return {
                "success": False,
                "error": f"Gemini API error: {response.status_code}",
                "details": response.text
            }
            
    except Exception as e:
        logger.error(f"Error in analyze_conversation_context: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

def generate_response_suggestions(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Genera sugerencias de respuesta basadas en el contexto
    """
    try:
        query = params.get("query", "")
        context = params.get("context", "")
        
        prompt = f"""
        Genera 3 sugerencias de respuesta para esta situación:
        
        Query: {query}
        Contexto: {context}
        
        Formato: Lista de sugerencias profesionales y útiles
        """
        
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)
        
        suggestions = response.text.split('\n')
        suggestions = [s.strip() for s in suggestions if s.strip()]
        
        return {
            "success": True,
            "data": {
                "suggestions": suggestions[:3],
                "generated_at": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error generating suggestions: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

def extract_key_information(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extrae información clave de un texto o conversación
    """
    try:
        text = params.get("text", params.get("query", ""))
        
        prompt = f"""
        Extrae la información clave de este texto:
        
        {text}
        
        Identifica:
        - Entidades mencionadas (personas, empresas, lugares)
        - Fechas y tiempos
        - Acciones solicitadas
        - Datos numéricos importantes
        """
        
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)
        
        return {
            "success": True,
            "data": {
                "extracted_info": response.text,
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error extracting information: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

def summarize_conversation(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Resume una conversación o texto largo
    """
    try:
        conversation = params.get("conversation", params.get("text", ""))
        
        prompt = f"""
        Resume esta conversación/texto de manera concisa:
        
        {conversation}
        
        Incluye:
        - Puntos principales
        - Decisiones tomadas
        - Acciones pendientes
        """
        
        model = genai.GenerativeModel(GEMINI_MODEL)  # Usar el modelo actualizado
        response = model.generate_content(prompt)
        
        return {
            "success": True,
            "data": {
                "summary": response.text,
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error summarizing: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

def classify_message_intent(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Clasifica la intención de un mensaje
    """
    try:
        message = params.get("message", params.get("query", ""))
        
        prompt = f"""
        Clasifica la intención de este mensaje:
        
        "{message}"
        
        Categorías posibles:
        - solicitud_información
        - ejecutar_acción
        - crear_contenido
        - modificar_existente
        - eliminar_contenido
        - consulta_estado
        - otro
        
        Responde con la categoría y un confidence score (0-1)
        """
        
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)
        
        return {
            "success": True,
            "data": {
                "intent": response.text.strip(),
                "message": message,
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error classifying intent: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

def generate_execution_plan(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Genera un plan de ejecución optimizado para workflows"""
    
    # Usar analyze_conversation_context con task específico
    return analyze_conversation_context(client, {
        "conversation_data": {
            **params.get("conversation_data", {}),
            "task": "optimize_workflow"
        }
    })

# Función adicional detectada en el proxy
gemini_suggest_action = generate_response_suggestions  # Alias para compatibilidad