# app/actions/gemini_actions.py
import logging
import json
import re
from typing import Any, Dict, List, Union
import google.generativeai as genai
from app.core.config import settings

logger = logging.getLogger(__name__)

def _configure_gemini():
    """Configures the Gemini API client."""
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        raise ValueError("GEMINI_API_KEY no está configurada en el entorno.")
    genai.configure(api_key=api_key)

def _handle_gemini_api_error(e: Exception, action_name: str) -> dict:
    logger.error(f"Error en Gemini Action '{action_name}': {e}", exc_info=True)
    return {"status": "error", "action": action_name, "message": str(e), "http_status": 500}

def _extract_json_from_text(text: str) -> Union[Dict, None]:
    """
    Extrae JSON de texto que puede contener markdown o texto adicional.
    Múltiples estrategias de extracción para mayor robustez.
    """
    try:
        # Estrategia 1: JSON directo
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    
    try:
        # Estrategia 2: Remover markdown code blocks
        cleaned = re.sub(r'```json\s*', '', text)
        cleaned = re.sub(r'```\s*$', '', cleaned, flags=re.MULTILINE)
        return json.loads(cleaned.strip())
    except json.JSONDecodeError:
        pass
    
    try:
        # Estrategia 3: Buscar patrón JSON en el texto
        json_pattern = r'\{.*\}'
        matches = re.findall(json_pattern, text, re.DOTALL)
        if matches:
            # Tomar el JSON más grande encontrado
            largest_json = max(matches, key=len)
            return json.loads(largest_json)
    except (json.JSONDecodeError, ValueError):
        pass
    
    try:
        # Estrategia 4: Buscar entre llaves balanceadas
        start = text.find('{')
        if start != -1:
            brace_count = 0
            for i, char in enumerate(text[start:], start):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        potential_json = text[start:i+1]
                        return json.loads(potential_json)
    except (json.JSONDecodeError, ValueError):
        pass
    
    return None

def _validate_plan_structure(plan_data: Dict) -> Dict[str, Any]:
    """
    Valida que el plan tenga la estructura correcta y las acciones existan.
    """
    from app.core.action_mapper import ACTION_MAP
    
    if not isinstance(plan_data, dict):
        return {"error": "El plan debe ser un objeto JSON válido."}
    
    if "error" in plan_data:
        return plan_data  # Plan indica que no puede cumplir el objetivo
    
    if "plan" not in plan_data:
        return {"error": "El plan debe contener una clave 'plan' con la lista de acciones."}
    
    plan_list = plan_data["plan"]
    if not isinstance(plan_list, list):
        return {"error": "La clave 'plan' debe ser una lista de acciones."}
    
    if len(plan_list) == 0:
        return {"error": "El plan no puede estar vacío."}
    
    # Validar cada acción en el plan
    validated_plan = []
    for i, action_obj in enumerate(plan_list):
        if not isinstance(action_obj, dict):
            return {"error": f"La acción {i+1} debe ser un objeto con 'action' y 'params'."}
        
        if "action" not in action_obj:
            return {"error": f"La acción {i+1} debe tener una clave 'action'."}
        
        action_name = action_obj["action"]
        if action_name not in ACTION_MAP:
            return {"error": f"La acción '{action_name}' no existe en el sistema. Acciones disponibles: {', '.join(list(ACTION_MAP.keys())[:10])}..."}
        
        # Asegurar que params existe (puede estar vacío)
        if "params" not in action_obj:
            action_obj["params"] = {}
        
        validated_plan.append(action_obj)
    
    return {"plan": validated_plan}

def _get_categorized_actions() -> str:
    """
    Genera una representación más legible de las acciones disponibles por categoría.
    """
    from app.core.action_mapper import ACTION_MAP
    
    # Agrupar acciones por prefijo/categoría
    categories = {}
    for action_name in ACTION_MAP.keys():
        prefix = action_name.split('_')[0]
        if prefix not in categories:
            categories[prefix] = []
        categories[prefix].append(action_name)
    
    # Crear representación legible
    categorized_text = "ACCIONES DISPONIBLES POR CATEGORÍA:\n"
    for category, actions in sorted(categories.items()):
        categorized_text += f"\n{category.upper()} ({len(actions)} acciones):\n"
        for action in sorted(actions)[:8]:  # Mostrar máximo 8 por categoría
            categorized_text += f"  - {action}\n"
        if len(actions) > 8:
            categorized_text += f"  ... y {len(actions) - 8} más\n"
    
    return categorized_text

def gemini_simple_text_prompt(client: Any, params: dict) -> dict:
    """
    Generates content based on a simple text prompt using a Gemini model.
    """
    action_name = "gemini_simple_text_prompt"
    try:
        _configure_gemini()
        
        prompt = params.get("prompt")
        model_name = params.get("model", "gemini-1.5-pro-latest")
        temperature = params.get("temperature", 0.7)
        max_tokens = params.get("max_tokens", 1000)
        
        if not prompt:
            raise ValueError("El parámetro 'prompt' es requerido.")
        
        # Configuración del modelo con parámetros de generación
        generation_config = genai.types.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
        
        model = genai.GenerativeModel(
            model_name=model_name,
            generation_config=generation_config
        )
        
        response = model.generate_content(prompt)
        
        return {
            "status": "success", 
            "data": {
                "text": response.text,
                "model_used": model_name,
                "prompt_tokens": len(prompt.split()),
                "completion_tokens": len(response.text.split()) if response.text else 0
            }
        }
    except Exception as e:
        return _handle_gemini_api_error(e, action_name)

def gemini_orchestrate_task(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    CEREBRO DE ORQUESTACIÓN INTELIGENTE
    
    Función central del Nivel 3 de Orquestación. Traduce objetivos complejos 
    en lenguaje natural a planes ejecutables de múltiples pasos.
    
    Mejoras implementadas:
    - Extracción robusta de JSON con múltiples estrategias
    - Validación exhaustiva de la estructura del plan
    - Mejor prompt engineering con ejemplos contextualizar
    - Reintentos automáticos en caso de fallos de formato
    - Representación más inteligente de acciones disponibles
    """
    action_name = "gemini_orchestrate_task"
    
    try:
        _configure_gemini()
        
        objective = params.get("objective")
        if not objective:
            raise ValueError("El parámetro 'objective' es requerido.")

        model_name = params.get("model", "gemini-1.5-pro-latest")
        max_retries = params.get("max_retries", 3)
        include_examples = params.get("include_examples", True)
        
        # Generar representación inteligente de acciones
        available_actions_text = _get_categorized_actions()
        
        # Ejemplos contextuales para mejorar la comprensión del modelo
        examples_section = ""
        if include_examples:
            examples_section = """
EJEMPLOS DE PLANES BIEN ESTRUCTURADOS:

Ejemplo 1 - Objetivo: "Revisa mis últimos correos y crea una tarea con el resumen"
{
    "plan": [
        {
            "action": "email_list_messages",
            "params": {
                "folder": "Inbox",
                "limit": 10
            }
        },
        {
            "action": "email_get_message", 
            "params": {
                "message_id": "{{step1.data.messages[0].id}}"
            }
        },
        {
            "action": "gemini_simple_text_prompt",
            "params": {
                "prompt": "Resume este correo: {{step2.data.body}}"
            }
        },
        {
            "action": "todo_create_task",
            "params": {
                "title": "Resumen de correo importante",
                "description": "{{step3.data.text}}"
            }
        }
    ]
}

Ejemplo 2 - Objetivo imposible: "Hackea la cuenta de mi jefe"
{
    "error": "No puedo ayudar con actividades ilegales o no éticas."
}
"""
        
        # Prompt mejorado con mejor estructura e instrucciones
        enhanced_prompt = f"""
SISTEMA DE ORQUESTACIÓN INTELIGENTE

Objetivo del Usuario: "{objective}"

Tu misión es ser un orquestador experto que traduce objetivos complejos en planes ejecutables.

{available_actions_text}

{examples_section}

REGLAS CRÍTICAS:
1. SOLO puedes usar acciones de la lista proporcionada
2. Si el objetivo es imposible/ilegal/poco ético, responde: {{"error": "Razón específica"}}
3. Tu respuesta debe ser ÚNICAMENTE un objeto JSON válido
4. Usa referencias entre pasos con la sintaxis: {{{{stepN.data.campo}}}}
5. Piensa paso a paso: ¿qué información necesito? ¿en qué orden?

ESTRUCTURA REQUERIDA:
{{
    "plan": [
        {{
            "action": "nombre_accion_exacto",
            "params": {{
                "parametro1": "valor",
                "parametro2": "{{{{referencia_paso_anterior}}}}"
            }}
        }}
    ]
}}

RESPUESTA (SOLO JSON):"""

        # Configuración del modelo para mayor precisión
        generation_config = genai.types.GenerationConfig(
            temperature=0.1,  # Baja temperatura para mayor precisión
            max_output_tokens=2000,
        )
        
        model = genai.GenerativeModel(
            model_name=model_name,
            generation_config=generation_config
        )

        # Sistema de reintentos para mayor robustez
        last_error = None
        for attempt in range(max_retries):
            try:
                logger.info(f"Intento {attempt + 1} de orquestación para objetivo: {objective}")
                
                response = model.generate_content(enhanced_prompt)
                
                if not response.text:
                    raise ValueError("El modelo no generó respuesta.")
                
                # Extracción robusta de JSON
                plan_json = _extract_json_from_text(response.text)
                
                if plan_json is None:
                    raise ValueError(f"No se pudo extraer JSON válido de la respuesta: {response.text[:200]}...")
                
                # Validación de la estructura del plan
                validated_plan = _validate_plan_structure(plan_json)
                
                if "error" in validated_plan:
                    # Si es un error del plan (objetivo imposible), no reintentamos
                    if "no existe en el sistema" not in validated_plan["error"]:
                        logger.info(f"Plan rechazado intencionalmente: {validated_plan['error']}")
                        return {"status": "success", "data": validated_plan}
                    else:
                        # Error de acción inexistente, reintentamos
                        raise ValueError(validated_plan["error"])
                
                # Éxito: plan válido generado
                logger.info(f"Plan orquestado exitosamente con {len(validated_plan['plan'])} pasos")
                
                return {
                    "status": "success", 
                    "data": {
                        **validated_plan,
                        "metadata": {
                            "model_used": model_name,
                            "attempt": attempt + 1,
                            "objective": objective,
                            "steps_count": len(validated_plan['plan'])
                        }
                    }
                }
                
            except Exception as attempt_error:
                last_error = attempt_error
                logger.warning(f"Intento {attempt + 1} falló: {str(attempt_error)}")
                
                if attempt < max_retries - 1:
                    # Modificar el prompt para el siguiente intento
                    enhanced_prompt += f"\n\nNOTA: Intento anterior falló ({str(attempt_error)}). Asegúrate de generar JSON válido."
                    continue
                else:
                    break
        
        # Si llegamos aquí, todos los intentos fallaron
        logger.error(f"Orquestación falló después de {max_retries} intentos. Último error: {last_error}")
        
        return {
            "status": "error",
            "action": action_name,
            "message": f"No se pudo generar un plan válido después de {max_retries} intentos.",
            "details": {
                "objective": objective,
                "last_error": str(last_error),
                "attempts": max_retries
            },
            "http_status": 500
        }

    except Exception as e:
        return _handle_gemini_api_error(e, action_name)

def gemini_analyze_user_intent(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    NUEVA FUNCIÓN: Analiza la intención del usuario antes de la orquestación.
    
    Útil para:
    - Detectar si el usuario quiere información vs acción
    - Identificar el contexto y urgencia
    - Sugerir clarificaciones si el objetivo es ambiguo
    """
    action_name = "gemini_analyze_user_intent"
    
    try:
        _configure_gemini()
        
        user_input = params.get("user_input")
        if not user_input:
            raise ValueError("El parámetro 'user_input' es requerido.")
        
        model_name = params.get("model", "gemini-1.5-flash")  # Modelo más rápido para análisis
        
        analysis_prompt = f"""
Analiza la siguiente solicitud del usuario y clasifica su intención:

Entrada del usuario: "{user_input}"

Responde en formato JSON con esta estructura:
{{
    "intent_type": "information_request|action_request|ambiguous|inappropriate",
    "confidence": 0.0-1.0,
    "complexity": "simple|medium|complex",
    "urgency": "low|medium|high",
    "requires_clarification": true/false,
    "suggested_clarifications": ["pregunta1", "pregunta2"],
    "estimated_steps": número,
    "primary_domains": ["email", "calendar", "tasks", etc],
    "summary": "resumen breve de la intención"
}}

RESPUESTA (SOLO JSON):"""
        
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(analysis_prompt)
        
        analysis_json = _extract_json_from_text(response.text)
        
        if analysis_json is None:
            raise ValueError("No se pudo extraer análisis válido de la respuesta.")
        
        return {"status": "success", "data": analysis_json}
        
    except Exception as e:
        return _handle_gemini_api_error(e, action_name)