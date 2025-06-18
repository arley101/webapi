# app/actions/openai_actions.py
import logging
import requests 
import json 
from typing import Dict, List, Optional, Any, Union

from app.core.config import settings
from app.shared.helpers.http_client import AuthenticatedHttpClient

logger = logging.getLogger(__name__)

def _handle_openai_api_error(e: Exception, action_name: str, params_for_log: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    log_message = f"Error en Azure OpenAI Action '{action_name}'"
    safe_params = {k: (v if k not in ['messages', 'prompt', 'input', 'payload'] else f"[{type(v).__name__} OMITIDO]") for k, v in (params_for_log or {}).items()}
    log_message += f" con params: {safe_params}"
    logger.error(f"{log_message}: {type(e).__name__} - {str(e)}", exc_info=True)
    details_str = str(e); status_code_int = 500; api_error_code = None
    if isinstance(e, requests.exceptions.HTTPError) and e.response is not None:
        status_code_int = e.response.status_code
        try:
            error_data = e.response.json(); error_info = error_data.get("error", error_data)
            details_str = error_info.get("message", e.response.text); api_error_code = error_info.get("code")
        except json.JSONDecodeError: details_str = e.response.text[:500] if e.response.text else "No response body"
    return {"status": "error", "action": action_name, "message": f"Error en {action_name}: {details_str}", 
            "details": str(e) if not isinstance(e, requests.exceptions.HTTPError) else details_str,
            "http_status": status_code_int, "azure_openai_error_code": api_error_code}

def _check_openai_config(action_name_for_log: str) -> bool:
    if not settings.AZURE_OPENAI_RESOURCE_ENDPOINT:
        logger.critical(f"CRÍTICO ({action_name_for_log}): 'AZURE_OPENAI_RESOURCE_ENDPOINT' no definida."); return False
    if not settings.AZURE_OPENAI_API_VERSION: 
        logger.critical(f"CRÍTICO ({action_name_for_log}): 'AZURE_OPENAI_API_VERSION' no definida."); return False
    if not settings.OPENAI_API_DEFAULT_SCOPE: 
        logger.critical(f"CRÍTICO ({action_name_for_log}): 'OPENAI_API_DEFAULT_SCOPE' no construido."); return False
    return True

async async def chat_completion(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; action_name = "openai_chat_completion"
    log_params = {k:v for k,v in params.items() if k != 'messages'}; 
    if 'messages' in params: log_params['messages_count'] = len(params['messages']) if isinstance(params.get('messages'), list) else 'Invalid' # type: ignore
    logger.info(f"Ejecutando {action_name} con params: %s", log_params)
    if not _check_openai_config(action_name): return {"status": "error", "message": "Configuración Azure OpenAI incompleta.", "http_status": 500}
    deployment_id = params.get("deployment_id"); messages = params.get("messages")
    if not deployment_id: return {"status": "error", "message": "'deployment_id' requerido.", "http_status": 400}
    if not messages or not isinstance(messages, list) or not all(isinstance(m, dict) and 'role' in m and 'content' in m for m in messages):
        return {"status": "error", "message": "'messages' (lista de {'role': ..., 'content': ...}) requerido y válido.", "http_status": 400}
    base_url = str(settings.AZURE_OPENAI_RESOURCE_ENDPOINT).rstrip('/')
    url = f"{base_url}/openai/deployments/{deployment_id}/chat/completions?api-version={settings.AZURE_OPENAI_API_VERSION}"
    payload: Dict[str, Any] = {"messages": messages}
    allowed_api_params = ["temperature", "max_tokens", "top_p", "frequency_penalty", "presence_penalty", "stop", "logit_bias", "user", "n", "logprobs", "top_logprobs", "response_format", "seed", "tools", "tool_choice", "stream"]
    for pk, val in params.items():
        if pk in allowed_api_params and val is not None: payload[pk] = val
    try:
        response_obj = await client.post(url=url, scope=settings.OPENAI_API_DEFAULT_SCOPE, json_data=payload, timeout=params.get("timeout", settings.DEFAULT_API_TIMEOUT)) # type: ignore
        return {"status": "success", "data": response_obj.json()} # client.post devuelve requests.Response
    except Exception as e: return _handle_openai_api_error(e, action_name, params)

async async def get_embedding(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; action_name = "openai_get_embedding"
    log_params = {k:v for k,v in params.items() if k != 'input'}; 
    if 'input' in params: log_params['input_type'] = type(params['input']).__name__
    logger.info(f"Ejecutando {action_name} con params: %s", log_params)
    if not _check_openai_config(action_name): return {"status": "error", "message": "Configuración Azure OpenAI incompleta.", "http_status": 500}
    deployment_id = params.get("deployment_id"); input_data = params.get("input")
    if not deployment_id: return {"status": "error", "message": "'deployment_id' (modelo Embeddings) requerido.", "http_status": 400}
    if not input_data: return {"status": "error", "message": "'input' (string o lista) requerido.", "http_status": 400}
    base_url = str(settings.AZURE_OPENAI_RESOURCE_ENDPOINT).rstrip('/')
    url = f"{base_url}/openai/deployments/{deployment_id}/embeddings?api-version={settings.AZURE_OPENAI_API_VERSION}"
    payload: Dict[str, Any] = {"input": input_data}
    if params.get("user"): payload["user"] = params["user"]
    if params.get("input_type"): payload["input_type"] = params["input_type"]
    if params.get("dimensions") is not None and isinstance(params["dimensions"], int): payload["dimensions"] = params["dimensions"]
    try:
        response_obj = await client.post(url=url, scope=settings.OPENAI_API_DEFAULT_SCOPE, json_data=payload, timeout=params.get("timeout", settings.DEFAULT_API_TIMEOUT)) # type: ignore
        return {"status": "success", "data": response_obj.json()}
    except Exception as e: return _handle_openai_api_error(e, action_name, params)

async async def completion(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; action_name = "openai_completion"
    log_params = {k:v for k,v in params.items() if k != 'prompt'}; 
    if 'prompt' in params: log_params['prompt_provided'] = True
    logger.info(f"Ejecutando {action_name} con params: %s", log_params)
    if not _check_openai_config(action_name): return {"status": "error", "message": "Configuración Azure OpenAI incompleta.", "http_status": 500}
    deployment_id = params.get("deployment_id"); prompt = params.get("prompt")
    if not deployment_id: return {"status": "error", "message": "'deployment_id' (modelo completion) requerido.", "http_status": 400}
    if not prompt: return {"status": "error", "message": "'prompt' (string o lista) requerido.", "http_status": 400}
    base_url = str(settings.AZURE_OPENAI_RESOURCE_ENDPOINT).rstrip('/')
    url = f"{base_url}/openai/deployments/{deployment_id}/completions?api-version={settings.AZURE_OPENAI_API_VERSION}"
    payload: Dict[str, Any] = {"prompt": prompt}
    allowed_api_params = ["max_tokens", "temperature", "top_p", "frequency_penalty", "presence_penalty", "stop", "logit_bias", "user", "n", "logprobs", "echo", "best_of", "stream"]
    for pk, val in params.items():
        if pk in allowed_api_params and val is not None: payload[pk] = val
    try:
        response_obj = await client.post(url=url, scope=settings.OPENAI_API_DEFAULT_SCOPE, json_data=payload, timeout=params.get("timeout", settings.DEFAULT_API_TIMEOUT)) # type: ignore
        return {"status": "success", "data": response_obj.json()}
    except Exception as e: return _handle_openai_api_error(e, action_name, params)

async async def list_models(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; action_name = "openai_list_models"
    logger.info(f"Ejecutando {action_name} con params: %s", params)
    if not _check_openai_config(action_name): return {"status": "error", "message": "Configuración Azure OpenAI incompleta.", "http_status": 500}
    base_url = str(settings.AZURE_OPENAI_RESOURCE_ENDPOINT).rstrip('/')
    url = f"{base_url}/openai/models?api-version={settings.AZURE_OPENAI_API_VERSION}"
    try:
        # await client.get() ya devuelve dict o str
        response_data = await client.get(url=url, scope=settings.OPENAI_API_DEFAULT_SCOPE, timeout=params.get("timeout", settings.DEFAULT_API_TIMEOUT)) # type: ignore
        if not isinstance(response_data, dict):
            raise Exception(f"Respuesta inesperada de http_client.get para {action_name}: tipo {type(response_data)}. Contenido: {str(response_data)[:200]}")
        if response_data.get("status") == "error" and "http_status" in response_data: return response_data
        return {"status": "success", "data": response_data.get("data", [])} # La API de /models anida en 'data'
    except Exception as e: return _handle_openai_api_error(e, action_name, params)

# --- FIN DEL MÓDULO actions/openai_actions.py ---