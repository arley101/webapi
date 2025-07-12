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
            logger.error("AuthenticatedHttpClient: Se requiere una instancia de DefaultAzureCredential. Tipo recibido: %s", type(credential).__name__)
            raise TypeError("Se requiere una instancia de DefaultAzureCredential para AuthenticatedHttpClient.")
        
        self.credential = credential
        self.session = requests.Session()
        self.default_timeout = default_timeout if default_timeout is not None else settings.DEFAULT_API_TIMEOUT
        
        self.default_graph_scope: List[str] = settings.GRAPH_API_DEFAULT_SCOPE
        if not self.default_graph_scope or not isinstance(self.default_graph_scope, list) or not self.default_graph_scope[0]:
            logger.warning("GRAPH_API_DEFAULT_SCOPE no está configurado correctamente en settings o está vacío. Esto podría causar problemas para el método get().")

        self.session.headers.update({
            'User-Agent': f'{settings.APP_NAME}/{settings.APP_VERSION}',
            'Accept': 'application/json'
        })
        logger.info(f"AuthenticatedHttpClient inicializado. User-Agent: {settings.APP_NAME}/{settings.APP_VERSION}, Default Timeout: {self.default_timeout}s, Default Graph Scope: {self.default_graph_scope}")

    def _get_access_token(self, scope: List[str]) -> Optional[str]:
        if not scope or not isinstance(scope, list) or not all(isinstance(s, str) for s in scope):
            logger.error("Se requiere un scope válido (lista de strings no vacía) para obtener el token de acceso. Scope recibido: %s", scope)
            return None
        try:
            logger.debug(f"Solicitando token para scope: {scope}")
            token_result = self.credential.get_token(*scope)
            logger.debug(f"Token obtenido exitosamente para scope: {scope}. Expiración (UTC): {token_result.expires_on}")
            return token_result.token
        except (CredentialUnavailableError, ClientAuthenticationError) as e:
            logger.error(f"Error de credencial de Azure al obtener token para {scope}: {e}.")
            return None
        except Exception as e: 
            logger.exception(f"Error inesperado al obtener token para {scope}: {e}") 
            return None

    def request(self, method: str, url: str, scope: List[str], **kwargs: Any) -> requests.Response:
        log_context = f"Request: {method} {url.split('?')[0]}"
        logger.debug(f"{log_context} - Iniciando solicitud con scope: {scope}")

        access_token = self._get_access_token(scope)
        if not access_token:
            logger.error(f"{log_context} - Fallo al obtener token de acceso para scope {scope}.")
            raise ValueError(f"No se pudo obtener el token de acceso para el scope {scope}. Verifique la configuración de credenciales y los logs.")

        request_headers = kwargs.pop('headers', {}).copy()
        request_headers['Authorization'] = f'Bearer {access_token}'

        if 'json' in kwargs or ('data' in kwargs and isinstance(kwargs['data'], (dict, list))):
            if 'Content-Type' not in request_headers:
                request_headers['Content-Type'] = 'application/json'
        
        timeout = kwargs.pop('timeout', self.default_timeout)
        if 'json_data' in kwargs and 'json' not in kwargs :
             kwargs['json'] = kwargs.pop('json_data')

        logger.debug(f"{log_context} - Headers: { {k: (v if k != 'Authorization' else '[TOKEN OMITIDO]') for k,v in request_headers.items()} }, Timeout: {timeout}s")
        
        try:
            response = self.session.request(
                method=method, url=url, headers=request_headers, timeout=timeout, **kwargs
            )
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
                    if error_message_from_api:
                         error_message += f" - API Message: {error_message_from_api}"
                except json.JSONDecodeError: 
                    error_message += f" - Respuesta no JSON: {http_err.response.text[:1000] if http_err.response.text else 'Sin cuerpo de respuesta.'}..."
            
            logger.error(f"{log_context} - {error_message}", exc_info=False)
            raise 
        except requests.exceptions.RequestException as req_err: 
            logger.error(f"{log_context} - Error de conexión/red: {req_err}", exc_info=True)
            raise 
        except Exception as e: 
            logger.exception(f"{log_context} - Error inesperado durante la solicitud: {e}")
            raise

    def get(self, url: str, scope: Optional[List[str]] = None, headers: Optional[Dict[str, str]] = None, params: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Union[Dict[str, Any], str, bytes]:
        """
        Realiza una solicitud GET utilizando la sesión y el token de autenticación.
        Devuelve el objeto de respuesta completo si la solicitud es exitosa, 
        o el contenido binario si es un stream.
        """
        current_scope_to_use = scope or self.default_graph_scope
        if not current_scope_to_use:
            raise ValueError("No se pudo determinar el scope para la solicitud GET.")

        response = self.request('GET', url, current_scope_to_use, headers=headers, params=params, **kwargs)
        
        if kwargs.get('stream'):
            return response.content

        # *** ESTA ES LA LÓGICA RESTAURADA Y CORRECTA ***
        # Ahora, son las funciones de acción las responsables de llamar a .json()
        # lo que hace que este cliente sea compatible con todo tu código.
        try:
            return response.json()
        except requests.exceptions.JSONDecodeError:
            logger.warning(f"Respuesta GET a {url} no es JSON. Devolviendo texto crudo.")
            return response.text

    def post(self, url: str, scope: List[str], **kwargs: Any) -> requests.Response:
        if 'json_data' in kwargs and 'json' not in kwargs:
            kwargs['json'] = kwargs.pop('json_data')
        return self.request('POST', url, scope, **kwargs)

    def put(self, url: str, scope: List[str], **kwargs: Any) -> requests.Response:
        if 'json_data' in kwargs and 'json' not in kwargs:
            kwargs['json'] = kwargs.pop('json_data')
        return self.request('PUT', url, scope, **kwargs)

    def delete(self, url: str, scope: List[str], **kwargs: Any) -> requests.Response: 
        return self.request('DELETE', url, scope, **kwargs)

    def patch(self, url: str, scope: List[str], **kwargs: Any) -> requests.Response:
        if 'json_data' in kwargs and 'json' not in kwargs:
            kwargs['json'] = kwargs.pop('json_data')
        return self.request('PATCH', url, scope, **kwargs)