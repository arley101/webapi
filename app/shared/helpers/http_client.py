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
        if not self.default_graph_scope or not isinstance(self.default_graph_scope, list) or not self.default_graph_scope[0]:
            logger.warning("GRAPH_API_DEFAULT_SCOPE no está configurado correctamente en settings.")
            
        self.session.headers.update({
            'User-Agent': f'{settings.APP_NAME}/{settings.APP_VERSION}',
            'Accept': 'application/json'
        })
        logger.info(f"AuthenticatedHttpClient inicializado. Default Timeout: {self.default_timeout}s, Default Graph Scope: {self.default_graph_scope}")

    def _get_access_token(self, scope: List[str]) -> Optional[str]:
        if not scope or not isinstance(scope, list) or not all(isinstance(s, str) for s in scope):
            logger.error("Se requiere un scope válido para obtener el token. Scope recibido: %s", scope)
            return None
        try:
            token_result = self.credential.get_token(*scope)
            return token_result.token
        except (CredentialUnavailableError, ClientAuthenticationError) as e:
            logger.error(f"Error de credencial/autenticación de Azure al obtener token para {scope}: {e}.")
            return None
        except Exception as e: 
            logger.exception(f"Error inesperado al obtener token para {scope}: {e}") 
            return None

    def request(self, method: str, url: str, scope: List[str], **kwargs: Any) -> requests.Response:
        access_token = self._get_access_token(scope)
        if not access_token:
            raise ValueError(f"No se pudo obtener el token de acceso para el scope {scope}.")

        request_headers = kwargs.pop('headers', {}).copy()
        request_headers['Authorization'] = f'Bearer {access_token}'

        if 'json' in kwargs or ('data' in kwargs and isinstance(kwargs['data'], (dict, list))):
            if 'Content-Type' not in request_headers:
                request_headers['Content-Type'] = 'application/json'
        
        timeout = kwargs.pop('timeout', self.default_timeout)
        if 'json_data' in kwargs and 'json' not in kwargs:
             kwargs['json'] = kwargs.pop('json_data')
        
        try:
            response = self.session.request(method=method, url=url, headers=request_headers, timeout=timeout, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as http_err:
            raise 
        except requests.exceptions.RequestException as req_err: 
            raise 
        except Exception as e: 
            raise

    def get(self, url: str, scope: Optional[List[str]] = None, **kwargs: Any) -> Union[Dict[str, Any], str, bytes]:
        current_scope_to_use = scope or self.default_graph_scope
        if not current_scope_to_use:
            raise ValueError("No se pudo determinar el scope para la solicitud GET.")
            
        access_token = self._get_access_token(current_scope_to_use)
        if not access_token:
            raise ValueError(f"No se pudo obtener token para el scope {current_scope_to_use}.")

        request_headers = self.session.headers.copy()
        request_headers['Authorization'] = f'Bearer {access_token}'
        if 'headers' in kwargs: request_headers.update(kwargs.pop('headers'))
        
        timeout_to_use = kwargs.pop('timeout', self.default_timeout)
        stream_response = kwargs.pop('stream', False)

        try:
            response = self.session.get(url, headers=request_headers, timeout=timeout_to_use, stream=stream_response, **kwargs)
            response.raise_for_status()
            if stream_response:
                return response.content
            try:
                return response.json()
            except requests.exceptions.JSONDecodeError:
                return response.text
        except requests.exceptions.HTTPError as http_err:
            raise
        except requests.exceptions.RequestException as req_err:
            raise
        except Exception as e:
            raise

    def post(self, url: str, scope: List[str], **kwargs: Any) -> requests.Response:
        return self.request('POST', url, scope, **kwargs)

    def put(self, url: str, scope: List[str], **kwargs: Any) -> requests.Response:
        return self.request('PUT', url, scope, **kwargs)

    def delete(self, url: str, scope: List[str], **kwargs: Any) -> requests.Response: 
        return self.request('DELETE', url, scope, **kwargs)

    def patch(self, url: str, scope: List[str], **kwargs: Any) -> requests.Response:
        return self.request('PATCH', url, scope, **kwargs)