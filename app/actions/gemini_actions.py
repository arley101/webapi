# app/actions/gemini_actions.py
import logging
import json
import re
from typing import Any, Dict, List, Union
import google.generativeai as genai
from app.core.config import settings

logger = logging.getLogger(__name__)

def _configure_gemini():
    """Configura el cliente de la API de Gemini."""
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        raise ValueError("GEMINI_API_KEY no está configurada en el entorno.")
    genai.configure(api_key=api_key)

def _handle_gemini_api_error(e: Exception, action_name: str) -> dict:
    logger.error(f"Error en la acción de Gemini '{action_name}': {e}", exc_info=True)
    return {"status": "error", "action": action_name, "message": str(e), "http_status": 500}

def _extract_json_from_text(text: str) -> Union[Dict, None]:
    """
    Extrae JSON de texto que puede contener markdown o texto adicional.
    """
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    try:
        cleaned = re.sub(r'```json\s*', '', text)
        cleaned = re.sub(r'```\s*$', '', cleaned, flags=re.MULTILINE)
        return json.loads(cleaned.strip())
    except json.JSONDecodeError:
        pass

    try:
        json_pattern = r'\{.*\}'
        matches = re.findall(json_pattern, text, re.DOTALL)
        if matches:
            largest_json = max(matches, key=len)
            return json.loads(largest_json)
    except (json.JSONDecodeError, ValueError):
        pass

    try:
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
    """Valida estructura del plan."""
    from app.core.action_mapper import ACTION_MAP
    
    if not isinstance(plan_data, dict):
        return {"error": "El plan debe ser un objeto JSON válido."}
    
    if "error" in plan_data:
        return plan_data
    
    if "plan" not in plan_data:
        return {"error": "El plan debe contener una clave 'plan'."}
    
    plan_list = plan_data["plan"]
    if not isinstance(plan_list, list):
        return {"error": "La clave 'plan' debe ser una lista."}
    
    if len(plan_list) == 0:
        return {"error": "El plan no puede estar vacío."}
    
    validated_plan = []
    for i, action_obj in enumerate(plan_list):
        if not isinstance(action_obj, dict):
            return {"error": f"La acción {i+1} debe ser un objeto."}
        
        if "action" not in action_obj:
            return {"error": f"La acción {i+1} debe tener una clave 'action'."}
        
        action_name = action_obj["action"]
        if action_name not in ACTION_MAP:
            return {"error": f"La acción '{action_name}' no existe."}
        
        if "params" not in action_obj:
            action_obj["params"] = {}
        
        validated_plan.append(action_obj)
    
    return {"plan": validated_plan}

def _get_categorized_actions() -> str:
    """Genera representación de acciones por categoría."""
    from app.core.action_mapper import ACTION_MAP
    
    categories = {}
    for action_name in ACTION_MAP.keys():
        prefix = action_name.split('_')[0]
        if prefix not in categories:
            categories[prefix] = []
        categories[prefix].append(action_name)
    
    categorized_text = "ACCIONES DISPONIBLES POR CATEGORÍA:\n"
    for category, actions in sorted(categories.items()):
        categorized_text += f"\n{category.upper()} ({len(actions)} acciones):\n"
        for action in sorted(actions)[:8]:
            categorized_text += f"  - {action}\n"
        if len(actions) > 8:
            categorized_text += f"  ... y {len(actions) - 8} más\n"
    
    return categorized_text

def gemini_simple_text_prompt(client: Any, params: dict) -> dict:
    """Genera contenido con prompt simple."""
    action_name = "gemini_simple_text_prompt"
    
    try:
        _configure_gemini()
        
        prompt = params.get("prompt")
        model_name = params.get("model", "gemini-1.5-pro-latest")
        temperature = params.get("temperature", 0.7)
        max_tokens = params.get("max_tokens", 1000)
        
        if not prompt:
            raise ValueError("El parámetro 'prompt' es requerido.")
        
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
    """Cerebro de orquestación inteligente."""
    action_name = "gemini_orchestrate_task"
    
    try:
        _configure_gemini()
        
        objective = params.get("objective")
        if not objective:
            raise ValueError("El parámetro 'objective' es requerido.")
        
        model_name = params.get("model", "gemini-1.5-pro-latest")
        max_retries = params.get("max_retries", 3)
        
        available_actions_text = _get_categorized_actions()
        
        enhanced_prompt = f"""
SISTEMA DE ORQUESTACIÓN INTELIGENTE

Objetivo: "{objective}"

{available_actions_text}

REGLAS:
1. SOLO usar acciones de la lista
2. Si imposible/ilegal: {{"error": "razón"}}
3. Respuesta: SOLO JSON válido
4. Referencias: {{{{stepN.data.campo}}}}

ESTRUCTURA:
{{
  "plan": [
    {{
      "action": "nombre_accion_exacto",
      "params": {{"param": "valor"}}
    }}
  ]
}}

RESPUESTA (SOLO JSON):"""
        
        generation_config = genai.types.GenerationConfig(
            temperature=0.1,
            max_output_tokens=2000,
        )
        
        model = genai.GenerativeModel(
            model_name=model_name,
            generation_config=generation_config
        )
        
        last_error = None
        for attempt in range(max_retries):
            try:
                response = model.generate_content(enhanced_prompt)
                
                if not response.text:
                    raise ValueError("El modelo no generó respuesta.")
                
                plan_json = _extract_json_from_text(response.text)
                if plan_json is None:
                    raise ValueError("No se pudo extraer JSON válido.")
                
                validated_plan = _validate_plan_structure(plan_json)
                if "error" in validated_plan:
                    if "no existe" not in validated_plan["error"]:
                        return {"status": "success", "data": validated_plan}
                    else:
                        raise ValueError(validated_plan["error"])
                
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
                if attempt < max_retries - 1:
                    continue
                else:
                    break
        
        return {
            "status": "error",
            "action": action_name,
            "message": f"No se pudo generar plan después de {max_retries} intentos.",
            "details": {
                "objective": objective,
                "last_error": str(last_error),
                "attempts": max_retries
            },
            "http_status": 500
        }
        
    except Exception as e:
        return _handle_gemini_api_error(e, action_name)

def gemini_suggest_action(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Sugiere mejor acción para consulta en lenguaje natural."""
    action_name = "gemini_suggest_action"
    
    try:
        _configure_gemini()
        
        query = params.get("query")
        if not query:
            raise ValueError("El parámetro 'query' es requerido.")
        
        model_name = params.get("model", "gemini-1.5-flash")
        available_actions_text = _get_categorized_actions()
        
        suggestion_prompt = f"""
Consulta: "{query}"

{available_actions_text}

Analiza y sugiere la mejor acción.

RESPUESTA (SOLO JSON):
{{
    "suggested_action": "nombre_exacto",
    "confidence": 0.95,
    "suggested_params": {{"param": "valor"}},
    "explanation": "Por qué es la mejor",
    "alternative_actions": ["alt1", "alt2"]
}}

Si no hay acción apropiada:
{{
    "error": "No hay acciones para esta consulta",
    "suggestion": "Reformula tu consulta"
}}"""
        
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(suggestion_prompt)
        
        suggestion_json = _extract_json_from_text(response.text)
        
        if suggestion_json is None:
            return {
                "status": "error",
                "action": action_name,
                "message": "No se pudo extraer sugerencia válida.",
                "raw_response": response.text[:200] + "..." if len(response.text) > 200 else response.text
            }
        
        return {
            "status": "success",
            "action": action_name,
            "data": suggestion_json
        }
        
    except Exception as e:
        return _handle_gemini_api_error(e, action_name)