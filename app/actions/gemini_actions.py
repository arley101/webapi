# app/actions/gemini_actions.py
import logging
import google.generativeai as genai
from app.core.config import settings
from typing import Any

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

# Aquí se podrían añadir acciones más complejas en el futuro,
# como 'gemini_execute_complex_task' que analice el prompt
# y llame a otras acciones del backend.