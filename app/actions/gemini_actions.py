# app/actions/gemini_actions.py
import logging
import json
import google.generativeai as genai
from app.core.config import settings
from typing import Any, Dict

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

def gemini_simple_text_prompt(client: Any, params: dict) -> dict:
    """
    Generates content based on a simple text prompt using a Gemini model.
    """
    action_name = "gemini_simple_text_prompt"
    try:
        _configure_gemini()
        
        prompt = params.get("prompt")
        model_name = params.get("model", "gemini-1.5-pro-latest")
        
        if not prompt:
            raise ValueError("El parámetro 'prompt' es requerido.")
            
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        
        return {"status": "success", "data": {"text": response.text}}
    except Exception as e:
        return _handle_gemini_api_error(e, action_name)

def gemini_orchestrate_task(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Takes a high-level objective and generates a structured plan of actions to be executed.
    """
    action_name = "gemini_orchestrate_task"
    # --- INICIO DE LA CORRECCIÓN ---
    # Se importa ACTION_MAP aquí adentro para romper la dependencia circular.
    from app.core.action_mapper import ACTION_MAP
    # --- FIN DE LA CORRECCIÓN ---
    try:
        _configure_gemini()
        
        objective = params.get("objective")
        if not objective:
            raise ValueError("El parámetro 'objective' es requerido.")

        model_name = params.get("model", "gemini-1.5-pro-latest")
        model = genai.GenerativeModel(model_name)

        available_actions = ", ".join(ACTION_MAP.keys())
        
        prompt = f"""
        Objective: "{objective}"

        You are an expert AI orchestrator. Your task is to break down the user's objective into a sequence of precise, executable API actions.
        You must only use the actions available in the provided list. Do not invent actions.

        Available Actions: {available_actions}

        Instructions:
        1. Analyze the objective and determine the logical sequence of actions required to achieve it.
        2. For each action, determine the necessary parameters. You may need to infer parameters from the objective.
        3. Return a SINGLE JSON object containing a "plan" key. The value of "plan" must be a list of action objects.
        4. Each action object in the list must have two keys: "action" (the name of the action) and "params" (an object with the parameters for that action).
        5. If the objective is ambiguous or cannot be fulfilled with the available actions, return an error object: {{"error": "Objective is ambiguous or cannot be fulfilled."}}
        6. Do not include explanations. Only the final JSON object is allowed as output.

        Example:
        Objective: "Find out who my manager is and list their direct reports."
        Expected Output:
        {{
            "plan": [
                {{
                    "action": "profile_get_my_profile",
                    "params": {{
                        "user_id": "me"
                    }}
                }},
                {{
                    "action": "profile_get_my_direct_reports",
                    "params": {{
                        "user_id": "{{step1.data.id}}"
                    }}
                }}
            ]
        }}
        """

        response = model.generate_content(prompt)
        
        cleaned_text = response.text.strip().replace("```json", "").replace("```", "").strip()
        plan_json = json.loads(cleaned_text)

        return {"status": "success", "data": plan_json}

    except Exception as e:
        return _handle_gemini_api_error(e, action_name)