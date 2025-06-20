# app/actions/openai_actions.py
import logging
import requests # Para requests.exceptions.HTTPError
import json # Para el helper de error
from typing import Dict, List, Optional, Any, Union

# Importar la configuración y el cliente HTTP autenticado
from app.core.config import settings
from app.shared.helpers.http_client import AuthenticatedHttpClient

logger = logging.getLogger(__name__)

# Helper para manejo de errores de Azure OpenAI API
def _handle_openai_api_error(e: Exception, action_name: str, params_for_log: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    log_message = f"Error en Azure OpenAI Action '{action_name}'"
    safe_params = {} # Inicializar
    if params_for_log:
        # Omitir campos sensibles como mensajes, prompts, input
        sensitive_keys = ['messages', 'prompt', 'input', 'payload']
        safe_params = {k: (v if k not in sensitive_keys else f"[{type(v).__name__} OMITIDO]") for k, v in params_for_log.items()}
        log_message += f" con params: {safe_params}"
    
    logger.error(f"{log_message}: {type(e).__name__} - {str(e)}", exc_info=True)
    
    details_str = str(e)
    status_code_int = 500
    api_error_code = None # Azure OpenAI puede tener su propia estructura de error

    if isinstance(e, requests.exceptions.HTTPError) and e.response is not None:
        status_code_int = e.response.status_code
        try:
            error_data = e.response.json()
            # La estructura del error de Azure OpenAI puede variar.
            # Comúnmente, hay un objeto 'error' con 'code' y 'message'.
            error_info = error_data.get("error", error_data) # Tomar error_data si 'error' no existe
            details_str = error_info.get("message", e.response.text)
            api_error_code = error_info.get("code")
        except json.JSONDecodeError: 
            details_str = e.response.text[:500] if e.response.text else "No response body"
            
    return {
        "status": "error", 
        "action": action_name,
        "message": f"Error en {action_name}: {details_str}", 
        "details": str(e) if not isinstance(e, requests.exceptions.HTTPError) else details_str,
        "http_status": status_code_int,
        "azure_openai_error_code": api_error_code 
    }

# Validar configuración esencial al cargar el módulo
def _check_openai_config(action_name_for_log: str) -> bool:
    # El validador en config.py ya construye OPENAI_API_DEFAULT_SCOPE si el endpoint existe.
    if not settings.AZURE_OPENAI_RESOURCE_ENDPOINT:
        logger.critical(f"CRÍTICO ({action_name_for_log}): Configuración 'AZURE_OPENAI_RESOURCE_ENDPOINT' no definida. Las acciones de OpenAI no funcionarán.")
        return False
    if not settings.AZURE_OPENAI_API_VERSION: 
        logger.critical(f"CRÍTICO ({action_name_for_log}): Configuración 'AZURE_OPENAI_API_VERSION' no definida. Las acciones de OpenAI no funcionarán.")
        return False
    if not settings.OPENAI_API_DEFAULT_SCOPE: 
        logger.critical(f"CRÍTICO ({action_name_for_log}): Scope 'OPENAI_API_DEFAULT_SCOPE' no pudo ser construido, probablemente falta AZURE_OPENAI_RESOURCE_ENDPOINT.")
        return False
    return True

# ---- FUNCIONES DE ACCIÓN PARA AZURE OPENAI ----

def chat_completion(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "openai_chat_completion"
    # Loggear params de forma segura, omitiendo 'messages'
    log_params = {k:v for k,v in params.items() if k != 'messages'}
    if 'messages' in params: log_params['messages_count'] = len(params['messages']) if isinstance(params['messages'], list) else 'Invalid'
    logger.info(f"Ejecutando {action_name} con params: %s", log_params)

    if not _check_openai_config(action_name):
        return {"status": "error", "action": action_name, "message": "Configuración de Azure OpenAI incompleta en el servidor.", "http_status": 500}

    deployment_id: Optional[str] = params.get("deployment_id") # Nombre del despliegue del modelo (ej. gpt-35-turbo)
    messages: Optional[List[Dict[str, str]]] = params.get("messages")

    if not deployment_id:
        return {"status": "error", "action": action_name, "message": "Parámetro 'deployment_id' (nombre del despliegue del modelo OpenAI) es requerido.", "http_status": 400}
    if not messages or not isinstance(messages, list) or not all(isinstance(m, dict) and 'role' in m and 'content' in m for m in messages):
        return {"status": "error", "action": action_name, "message": "Parámetro 'messages' (lista de objetos {'role': '...', 'content': '...'}) es requerido y debe tener formato válido.", "http_status": 400}

    if params.get("stream", False): # Streaming no es manejado por este backend directamente, el cliente debería manejarlo.
        logger.warning(f"{action_name}: Solicitud de Chat Completion para despliegue '{deployment_id}' con stream=true. "
                       "Esta acción no soporta streaming directamente y procederá de forma síncrona. "
                       "El cliente es responsable de manejar respuestas de stream si la API de Azure lo permite para este endpoint.")

    base_url = str(settings.AZURE_OPENAI_RESOURCE_ENDPOINT).rstrip('/')
    url = f"{base_url}/openai/deployments/{deployment_id}/chat/completions?api-version={settings.AZURE_OPENAI_API_VERSION}"

    # Construir el payload, incluyendo solo parámetros permitidos por la API de Azure OpenAI
    payload: Dict[str, Any] = {"messages": messages}
    # Lista de parámetros comunes para ChatCompletion, basada en la documentación de Azure OpenAI.
    # Ampliar según sea necesario.
    allowed_api_params = [
        "temperature", "max_tokens", "top_p", "frequency_penalty", "presence_penalty", 
        "stop", "logit_bias", "user", "n", "logprobs", "top_logprobs", 
        "response_format", "seed", "tools", "tool_choice", "stream" # Aunque stream no se maneje, se pasa a la API.
    ]
    for param_key, value in params.items():
        if param_key in allowed_api_params and value is not None: # Solo añadir si el valor no es None
            payload[param_key] = value

    logger.info(f"{action_name}: Enviando petición de Chat Completion a Azure OpenAI, despliegue '{deployment_id}'. Mensajes: {len(messages)}. Payload keys: {list(payload.keys())}")
    
    # El scope para Azure OpenAI se construye en config.py
    openai_scope = settings.OPENAI_API_DEFAULT_SCOPE
    if not openai_scope: # Doble chequeo por si acaso
         return {"status": "error", "action": action_name, "message": "Scope de Azure OpenAI no configurado.", "http_status": 500}

    try:
        # AuthenticatedHttpClient maneja la adición del token y Content-Type para json_data
        response = client.post(
            url=url,
            scope=openai_scope, 
            json_data=payload, # Pasa el payload como json_data
            timeout=params.get("timeout", settings.DEFAULT_API_TIMEOUT) # Permitir timeout por param
        )
        response_data = response.json()
        return {"status": "success", "data": response_data}
    except Exception as e:
        return _handle_openai_api_error(e, action_name, params)

def get_embedding(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "openai_get_embedding"
    log_params = {k:v for k,v in params.items() if k != 'input'}
    if 'input' in params: log_params['input_type'] = type(params['input']).__name__
    logger.info(f"Ejecutando {action_name} con params: %s", log_params)

    if not _check_openai_config(action_name):
        return {"status": "error", "action": action_name, "message": "Configuración de Azure OpenAI incompleta en el servidor.", "http_status": 500}

    deployment_id: Optional[str] = params.get("deployment_id") # Nombre del despliegue del modelo de embeddings
    input_data: Optional[Union[str, List[str]]] = params.get("input")
    user_param: Optional[str] = params.get("user") # Opcional, para seguimiento
    input_type_param: Optional[str] = params.get("input_type") # Opcional: 'query', 'document'

    if not deployment_id:
        return {"status": "error", "action": action_name, "message": "Parámetro 'deployment_id' (nombre del despliegue del modelo Embeddings) es requerido.", "http_status": 400}
    if not input_data: # Puede ser string o lista de strings, no puede ser None o vacío
        return {"status": "error", "action": action_name, "message": "Parámetro 'input' (string o lista de strings) es requerido y no puede estar vacío.", "http_status": 400}

    base_url = str(settings.AZURE_OPENAI_RESOURCE_ENDPOINT).rstrip('/')
    url = f"{base_url}/openai/deployments/{deployment_id}/embeddings?api-version={settings.AZURE_OPENAI_API_VERSION}"

    payload: Dict[str, Any] = {"input": input_data}
    if user_param: payload["user"] = user_param
    if input_type_param: payload["input_type"] = input_type_param
    # Otros parámetros como 'dimensions' pueden ser añadidos si la API los soporta.
    if params.get("dimensions") is not None and isinstance(params["dimensions"], int):
        payload["dimensions"] = params["dimensions"]


    log_input_type_desc = "lista de strings" if isinstance(input_data, list) else "string"
    logger.info(f"{action_name}: Generando Embeddings con Azure OpenAI, despliegue '{deployment_id}' para entrada tipo '{log_input_type_desc}'. Payload keys: {list(payload.keys())}")
    
    openai_scope = settings.OPENAI_API_DEFAULT_SCOPE
    if not openai_scope:
         return {"status": "error", "action": action_name, "message": "Scope de Azure OpenAI no configurado.", "http_status": 500}

    try:
        response = client.post(
            url=url,
            scope=openai_scope,
            json_data=payload,
            timeout=params.get("timeout", settings.DEFAULT_API_TIMEOUT)
        )
        response_data = response.json()
        return {"status": "success", "data": response_data}
    except Exception as e:
        return _handle_openai_api_error(e, action_name, params)

def completion(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    # Esta es para modelos de completion más antiguos (no chat).
    params = params or {}
    action_name = "openai_completion"
    log_params = {k:v for k,v in params.items() if k != 'prompt'}
    if 'prompt' in params: log_params['prompt_provided'] = True
    logger.info(f"Ejecutando {action_name} con params: %s", log_params)

    if not _check_openai_config(action_name):
        return {"status": "error", "action": action_name, "message": "Configuración de Azure OpenAI incompleta en el servidor.", "http_status": 500}

    deployment_id: Optional[str] = params.get("deployment_id") # Nombre del despliegue del modelo (ej. text-davinci-003)
    prompt: Optional[Union[str, List[str]]] = params.get("prompt")

    if not deployment_id:
        return {"status": "error", "action": action_name, "message": "Parámetro 'deployment_id' (del modelo de completion) es requerido.", "http_status": 400}
    if not prompt: # Puede ser string o lista de strings
        return {"status": "error", "action": action_name, "message": "Parámetro 'prompt' (string o lista de strings) es requerido.", "http_status": 400}

    base_url = str(settings.AZURE_OPENAI_RESOURCE_ENDPOINT).rstrip('/')
    url = f"{base_url}/openai/deployments/{deployment_id}/completions?api-version={settings.AZURE_OPENAI_API_VERSION}"

    payload: Dict[str, Any] = {"prompt": prompt}
    # Parámetros comunes para Completions API
    allowed_api_params = [
        "max_tokens", "temperature", "top_p", "frequency_penalty", "presence_penalty", 
        "stop", "logit_bias", "user", "n", "logprobs", "echo", "best_of", "stream"
    ]
    for param_key, value in params.items():
        if param_key in allowed_api_params and value is not None:
            payload[param_key] = value

    logger.info(f"{action_name}: Enviando petición de Completion a Azure OpenAI, despliegue '{deployment_id}'. Payload keys: {list(payload.keys())}")
    
    openai_scope = settings.OPENAI_API_DEFAULT_SCOPE
    if not openai_scope:
         return {"status": "error", "action": action_name, "message": "Scope de Azure OpenAI no configurado.", "http_status": 500}

    try:
        response = client.post(
            url=url,
            scope=openai_scope,
            json_data=payload,
            timeout=params.get("timeout", settings.DEFAULT_API_TIMEOUT)
        )
        response_data = response.json()
        return {"status": "success", "data": response_data}
    except Exception as e:
        return _handle_openai_api_error(e, action_name, params)

def list_models(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    # Esta acción lista los modelos disponibles en el recurso Azure OpenAI, no los despliegues.
    params = params or {}
    action_name = "openai_list_models"
    logger.info(f"Ejecutando {action_name} con params: %s", params)

    # Para listar modelos, solo se necesita el endpoint y la api-version.
    # _check_openai_config valida esto.
    if not _check_openai_config(action_name):
         return {"status": "error", "action": action_name, "message": "Configuración de Azure OpenAI incompleta para listar modelos (endpoint, api-version o scope).", "http_status": 500}

    base_url = str(settings.AZURE_OPENAI_RESOURCE_ENDPOINT).rstrip('/')
    # El endpoint para listar modelos es /openai/models (sin /deployments/)
    url = f"{base_url}/openai/models?api-version={settings.AZURE_OPENAI_API_VERSION}"

    logger.info(f"{action_name}: Listando modelos disponibles en el recurso Azure OpenAI: {settings.AZURE_OPENAI_RESOURCE_ENDPOINT}")
    
    openai_scope = settings.OPENAI_API_DEFAULT_SCOPE
    if not openai_scope: # Aunque /models puede no requerir un token de recurso específico, el cliente lo intenta obtener.
         return {"status": "error", "action": action_name, "message": "Scope de Azure OpenAI no configurado.", "http_status": 500}
    
    try:
        # Esta llamada es GET
        response = client.get(
            url=url,
            scope=openai_scope, 
            timeout=params.get("timeout", settings.DEFAULT_API_TIMEOUT)
        )
        response_data = response.json()
        # La respuesta de /models tiene un campo "data" que es una lista de modelos.
        return {"status": "success", "data": response_data.get("data", [])}
    except Exception as e:
        return _handle_openai_api_error(e, action_name, params)

# --- FIN DEL MÓDULO actions/openai_actions.py ---