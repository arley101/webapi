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
            raise TypeError("Se requiere una instancia de DefaultAzureCredential para AuthenticatedHttpClient.")
        
        self.credential = credential
        self.session = requests.Session()
        self.default_timeout = default_timeout if default_timeout is not None else settings.DEFAULT_API_TIMEOUT
        self.default_graph_scope: List[str] = settings.GRAPH_API_DEFAULT_SCOPE

        self.session.headers.update({
            'User-Agent': f'{settings.APP_NAME}/{settings.APP_VERSION}',
            'Accept': 'application/json'
        })
        logger.info("AuthenticatedHttpClient inicializado.")

    def _get_access_token(self, scope: List[str]) -> str:
        if not scope or not isinstance(scope, list) or not scope[0]:
            raise ValueError("Se requiere un scope válido para obtener el token.")
        try:
            token_result = self.credential.get_token(*scope)
            return token_result.token
        except (CredentialUnavailableError, ClientAuthenticationError) as e:
            logger.error(f"Error de credencial de Azure al obtener token para {scope}: {e}.")
            raise ConnectionRefusedError(f"No se pudo obtener el token para el scope {scope}. Verifique la configuración de la identidad administrada.") from e
        except Exception as e:
            logger.exception(f"Error inesperado al obtener token para {scope}: {e}")
            raise ConnectionError(f"Error inesperado al obtener token: {e}") from e

    def request(self, method: str, url: str, scope: List[str], **kwargs: Any) -> requests.Response:
        access_token = self._get_access_token(scope)
        
        # *** INICIO DE LA CORRECCIÓN CRÍTICA ***
        # Se inicializa el diccionario de headers copiando los de la sesión.
        request_headers = self.session.headers.copy()
        request_headers['Authorization'] = f'Bearer {access_token}'
        
        # Si se pasan headers adicionales, se fusionan.
        custom_headers = kwargs.pop('headers', None)
        if custom_headers:
            request_headers.update(custom_headers)
        # *** FIN DE LA CORRECCIÓN CRÍTICA ***

        if 'json' in kwargs or 'json_data' in kwargs:
             if 'Content-Type' not in request_headers:
                request_headers['Content-Type'] = 'application/json'
        
        if 'json_data' in kwargs:
            kwargs['json'] = kwargs.pop('json_data')
        
        timeout = kwargs.pop('timeout', self.default_timeout)

        try:
            response = self.session.request(method=method, url=url, headers=request_headers, timeout=timeout, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as http_err:
            logger.error(f"Error HTTP en {method} {url}: {http_err.response.status_code if http_err.response else 'N/A'}", exc_info=True)
            raise
        except requests.exceptions.RequestException as req_err:
            logger.error(f"Error de conexión en {method} {url}: {req_err}", exc_info=True)
            raise

    def get(self, url: str, scope: Optional[List[str]] = None, **kwargs: Any) -> Any:
        scope_to_use = scope or self.default_graph_scope
        if not scope_to_use:
            raise ValueError("No se pudo determinar el scope para la solicitud GET.")
        
        response = self.request('GET', url, scope_to_use, **kwargs)
        
        if kwargs.get('stream'):
            return response.content
        
        try:
            return response.json()
        except json.JSONDecodeError:
            return response.text

    def post(self, url: str, scope: List[str], **kwargs: Any) -> requests.Response:
        return self.request('POST', url, scope, **kwargs)

    def put(self, url: str, scope: List[str], **kwargs: Any) -> requests.Response:
        return self.request('PUT', url, scope, **kwargs)

    def delete(self, url: str, scope: List[str], **kwargs: Any) -> requests.Response: 
        return self.request('DELETE', url, scope, **kwargs)

    def patch(self, url: str, scope: List[str], **kwargs: Any) -> requests.Response:
        return self.request('PATCH', url, scope, **kwargs)