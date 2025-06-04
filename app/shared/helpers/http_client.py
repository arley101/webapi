# app/shared/helpers/http_client.py
import logging
import requests
import json 
from azure.identity import DefaultAzureCredential, CredentialUnavailableError
from azure.core.exceptions import ClientAuthenticationError
from typing import List, Optional, Any, Dict, Union

from app.core.config import settings

logger = logging.getLogger(__name__)

class AuthenticatedHttpClient:
    def __init__(self, credential: DefaultAzureCredential, default_timeout: Optional[int] = None):
        if not isinstance(credential, DefaultAzureCredential):
            logger.error("AuthenticatedHttpClient: Se requiere DefaultAzureCredential. Tipo recibido: %s", type(credential).__name__)
            raise TypeError("Se requiere DefaultAzureCredential para AuthenticatedHttpClient.")
        
        self.credential = credential
        self.session = requests.Session()
        self.default_timeout = default_timeout if default_timeout is not None else settings.DEFAULT_API_TIMEOUT
        self.default_graph_scope: List[str] = settings.GRAPH_API_DEFAULT_SCOPE

        if not self.default_graph_scope or not isinstance(self.default_graph_scope, list) or not self.default_graph_scope[0]:
            logger.warning("GRAPH_API_DEFAULT_SCOPE no configurado correctamente.")
        
        self.session.headers.update({
            'User-Agent': f'{settings.APP_NAME}/{settings.APP_VERSION}',
            'Accept': 'application/json'
        })
        logger.info(f"AuthenticatedHttpClient inicializado. User-Agent: {settings.APP_NAME}/{settings.APP_VERSION}, Timeout: {self.default_timeout}s, Default Graph Scope: {self.default_graph_scope}")

    def _get_access_token(self, scope: List[str]) -> Optional[str]:
        if not scope or not isinstance(scope, list) or not all(isinstance(s, str) for s in scope):
            logger.error("Scope inválido para obtener token: %s", scope)
            return None
        try:
            logger.debug(f"Solicitando token para scope: {scope}")
            token_result = self.credential.get_token(*scope)
            logger.debug(f"Token obtenido para scope: {scope}. Expira (UTC): {token_result.expires_on}")
            return token_result.token
        except CredentialUnavailableError as e:
            logger.error(f"Error de credencial no disponible para {scope}: {e}.")
            return None
        except ClientAuthenticationError as e: 
            logger.error(f"Error de autenticación del cliente para {scope}: {e}.")
            return None
        except Exception as e: 
            logger.exception(f"Error inesperado obteniendo token para {scope}: {e}") 
            return None

    def request(self, method: str, url: str, scope: List[str], **kwargs: Any) -> requests.Response:
        log_context = f"Request: {method} {url.split('?')[0]}"
        logger.debug(f"{log_context} - Iniciando con scope: {scope}")

        access_token = self._get_access_token(scope)
        if not access_token:
            raise ValueError(f"No se pudo obtener token para scope {scope}. Verifique credenciales y logs.")

        request_headers = kwargs.pop('headers', {}).copy()
        request_headers['Authorization'] = f'Bearer {access_token}'

        if 'json' in kwargs or ('data' in kwargs and isinstance(kwargs['data'], (dict, list))):
            if 'Content-Type' not in request_headers:
                request_headers['Content-Type'] = 'application/json'
        
        timeout = kwargs.pop('timeout', self.default_timeout)
        if 'json_data' in kwargs and 'json' not in kwargs : # Manejo de json_data
             kwargs['json'] = kwargs.pop('json_data')

        logger.debug(f"{log_context} - Headers: { {k: (v if k != 'Authorization' else '[TOKEN]') for k,v in request_headers.items()} }, Timeout: {timeout}s")
        
        try:
            response = self.session.request(method=method, url=url, headers=request_headers, timeout=timeout, **kwargs)
            response.raise_for_status() 
            logger.debug(f"{log_context} - Solicitud exitosa (Status: {response.status_code})")
            return response
        except requests.exceptions.HTTPError as http_err:
            error_message = f"Error HTTP en {method} {url}: {http_err.response.status_code if http_err.response is not None else 'N/A'}"
            if http_err.response is not None:
                try:
                    error_details_json = http_err.response.json()
                    error_info = error_details_json.get("error", error_details_json)
                    error_message_from_api = error_info.get("message", str(error_info))
                    if error_message_from_api: error_message += f" - API Message: {error_message_from_api}"
                except json.JSONDecodeError: 
                    error_message += f" - Respuesta no JSON: {http_err.response.text[:1000] if http_err.response.text else 'Sin cuerpo.'}..."
            logger.error(f"{log_context} - {error_message}", exc_info=False) # exc_info=False para no duplicar stack trace si se relanza
            raise 
        except requests.exceptions.RequestException as req_err: 
            logger.error(f"{log_context} - Error de conexión/red: {req_err}", exc_info=True)
            raise 
        except Exception as e: 
            logger.exception(f"{log_context} - Error inesperado: {e}")
            raise

    def get(self, url: str, scope: Optional[List[str]] = None, headers: Optional[Dict[str, str]] = None, params: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Union[Dict[str, Any], str, bytes]:
        log_context = f"GET Request: {url.split('?')[0]}"
        
        current_scope_to_use = scope or self.default_graph_scope
        if not current_scope_to_use:
            raise ValueError("No se pudo determinar el scope para la solicitud GET y no se proporcionó uno.")

        logger.debug(f"{log_context} - Iniciando con scope: {current_scope_to_use}")
        access_token = self._get_access_token(current_scope_to_use)
        if not access_token:
            raise ValueError(f"No se pudo obtener token para scope {current_scope_to_use}.")

        request_headers = self.session.headers.copy()
        request_headers['Authorization'] = f'Bearer {access_token}'
        if headers: request_headers.update(headers)
        
        timeout_to_use = kwargs.pop('timeout', self.default_timeout)
        stream_response = kwargs.pop('stream', False)

        logger.debug(f"{log_context} - Headers: { {k: (v if k != 'Authorization' else '[TOKEN]') for k,v in request_headers.items()} }, Timeout: {timeout_to_use}s, Stream: {stream_response}")

        try:
            response_obj = self.session.get(url, headers=request_headers, params=params, timeout=timeout_to_use, stream=stream_response, **kwargs)
            response_obj.raise_for_status()
            logger.debug(f"{log_context} - Solicitud GET exitosa (Status: {response_obj.status_code})")

            if stream_response: 
                logger.info(f"{log_context} - Respuesta en stream, devolviendo content (bytes).")
                return response_obj.content 
            try:
                return response_obj.json()
            except requests.exceptions.JSONDecodeError:
                logger.warning(f"{log_context} - Respuesta GET no es JSON. Status: {response_obj.status_code}. Devolviendo texto: {response_obj.text[:200]}...")
                return response_obj.text
        except requests.exceptions.HTTPError as http_err:
            error_message = f"Error HTTP en GET {url}: {http_err.response.status_code if http_err.response is not None else 'N/A'}"
            # ... (lógica de error similar a self.request) ...
            if http_err.response is not None:
                try:
                    error_details_json = http_err.response.json(); error_info = error_details_json.get("error", error_details_json)
                    api_msg = error_info.get("message", str(error_info)); error_message += f" - API Message: {api_msg}"
                except: error_message += f" - Respuesta no JSON: {http_err.response.text[:200] if http_err.response.text else ''}..."
            logger.error(f"{log_context} - {error_message}", exc_info=False)
            raise 
        except requests.exceptions.RequestException as req_err:
            logger.error(f"{log_context} - Error de conexión/red GET: {req_err}", exc_info=True); raise
        except Exception as e:
            logger.exception(f"{log_context} - Error inesperado GET: {e}"); raise

    def post(self, url: str, scope: List[str], **kwargs: Any) -> requests.Response:
        if 'json_data' in kwargs and 'json' not in kwargs: kwargs['json'] = kwargs.pop('json_data')
        return self.request('POST', url, scope, **kwargs)

    def put(self, url: str, scope: List[str], **kwargs: Any) -> requests.Response:
        if 'json_data' in kwargs and 'json' not in kwargs: kwargs['json'] = kwargs.pop('json_data')
        return self.request('PUT', url, scope, **kwargs)

    def delete(self, url: str, scope: List[str], **kwargs: Any) -> requests.Response: 
        return self.request('DELETE', url, scope, **kwargs)

    def patch(self, url: str, scope: List[str], **kwargs: Any) -> requests.Response:
        if 'json_data' in kwargs and 'json' not in kwargs: kwargs['json'] = kwargs.pop('json_data')
        return self.request('PATCH', url, scope, **kwargs)