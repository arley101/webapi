# app/shared/helpers/http_client.py
import logging
import requests
import json 
from azure.identity import DefaultAzureCredential, ClientSecretCredential, CredentialUnavailableError
from azure.core.exceptions import ClientAuthenticationError

from typing import List, Optional, Any, Dict, Union # Añadido Union
import os

# Importar la configuración de la aplicación
from app.core.config import settings

logger = logging.getLogger(__name__)

class AuthenticatedHttpClient:
    """Cliente HTTP con autenticación para múltiples servicios"""
    
    def __init__(self, credential: Optional[Union[DefaultAzureCredential, ClientSecretCredential]] = None):
        """
        Inicializa el cliente con credenciales Azure flexibles
        """
        if credential is None:
            # Intentar usar Managed Identity primero, luego Client Credentials
            try:
                self.credential = DefaultAzureCredential()
                logger.info("✅ Usando DefaultAzureCredential (Managed Identity)")
            except Exception as e:
                logger.warning(f"Managed Identity no disponible: {str(e)}")
                # Fallback a Client Credentials
                self._init_client_credentials()
        elif isinstance(credential, (DefaultAzureCredential, ClientSecretCredential)):
            self.credential = credential
            logger.info(f"✅ Usando credencial proporcionada: {type(credential).__name__}")
        else:
            # Si se pasa otro tipo, intentar Client Credentials
            logger.warning(f"Tipo de credencial no reconocido: {type(credential)}, usando Client Credentials")
            self._init_client_credentials()
        
        self.session = requests.Session()
        self.default_timeout = settings.DEFAULT_API_TIMEOUT
        
        # Establecer el scope por defecto para Graph API al inicializar
        self.default_graph_scope: List[str] = settings.GRAPH_API_DEFAULT_SCOPE
        if not self.default_graph_scope or not isinstance(self.default_graph_scope, list) or not self.default_graph_scope[0]:
            logger.warning("GRAPH_API_DEFAULT_SCOPE no está configurado correctamente en settings o está vacío. Esto podría causar problemas para el método get().")
            # Podrías asignar un fallback más genérico aquí si es absolutamente necesario,
            # pero es mejor que esté bien configurado en settings.py
            # self.default_graph_scope = ["https://graph.microsoft.com/.default"] 

        self.session.headers.update({
            'User-Agent': f'{settings.APP_NAME}/{settings.APP_VERSION}',
            'Accept': 'application/json'
        })
        logger.info(f"AuthenticatedHttpClient inicializado. User-Agent: {settings.APP_NAME}/{settings.APP_VERSION}, Default Timeout: {self.default_timeout}s, Default Graph Scope: {self.default_graph_scope}")

        # Inicializar cliente Gemini si está configurado
        if hasattr(settings, 'GEMINI_API_KEY') and settings.GEMINI_API_KEY:
            try:
                import google.generativeai as genai
                genai.configure(api_key=settings.GEMINI_API_KEY)
                self.genai = genai
                logger.info("✅ Cliente Gemini inicializado")
            except Exception as e:
                logger.warning(f"⚠️ No se pudo inicializar Gemini: {e}")
                self.genai = None
        else:
            self.genai = None

    def _init_client_credentials(self):
        """Inicializa Client Credentials como fallback"""
        tenant_id = os.environ.get('AZURE_TENANT_ID')
        client_id = os.environ.get('AZURE_CLIENT_ID')
        client_secret = os.environ.get('AZURE_CLIENT_SECRET')
        
        if tenant_id and client_id and client_secret:
            self.credential = ClientSecretCredential(
                tenant_id=tenant_id,
                client_id=client_id,
                client_secret=client_secret
            )
            logger.info("✅ Usando ClientSecretCredential como fallback")
        else:
            raise ValueError("No se encontraron credenciales Azure válidas")

    def _get_access_token(self, scope: List[str]) -> Optional[str]:
        if not scope or not isinstance(scope, list) or not all(isinstance(s, str) for s in scope):
            logger.error("Se requiere un scope válido (lista de strings no vacía) para obtener el token de acceso. Scope recibido: %s", scope)
            return None
        try:
            logger.debug(f"Solicitando token para scope: {scope}")
            token_result = self.credential.get_token(*scope)
            logger.debug(f"Token obtenido exitosamente para scope: {scope}. Expiración (UTC): {token_result.expires_on}")
            return token_result.token
        except CredentialUnavailableError as e:
            logger.error(f"Error de credencial de Azure no disponible al obtener token para {scope}: {e}.")
            return None
        except ClientAuthenticationError as e: 
            logger.error(f"Error de autenticación del cliente de Azure al obtener token para {scope}: {e}.")
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
        Permite un scope opcional; si no se provee, usa self.default_graph_scope.
        Intenta devolver JSON, pero recurre a texto o bytes si la decodificación JSON falla o si es una descarga.
        """
        action_name_log = "AuthenticatedHttpClient.get"
        log_context = f"GET Request: {url.split('?')[0]}"
        
        current_scope_to_use = scope
        if not current_scope_to_use:
            if hasattr(self, 'default_graph_scope') and self.default_graph_scope:
                current_scope_to_use = self.default_graph_scope
            else:
                logger.error(f"{log_context} - No se pudo determinar el scope para la solicitud GET y default_graph_scope no está configurado en AuthenticatedHttpClient.")
                raise ValueError("No se pudo determinar el scope para la solicitud GET y no se proporcionó uno, ni se configuró un default_graph_scope.")

        logger.debug(f"{log_context} - Iniciando solicitud GET con scope: {current_scope_to_use}")
        
        access_token = self._get_access_token(current_scope_to_use)
        if not access_token:
            logger.error(f"{log_context} - Fallo al obtener token de acceso para scope {current_scope_to_use}.")
            raise ValueError(f"No se pudo obtener el token de acceso para el scope {current_scope_to_use}.")

        request_headers = self.session.headers.copy() # Empezar con headers de sesión (User-Agent, Accept por defecto)
        request_headers['Authorization'] = f'Bearer {access_token}'
        
        # Los GET no suelen necesitar Content-Type, pero lo respetamos si se pasa en 'headers'
        if headers:
            request_headers.update(headers)
        
        # Eliminar Content-Type si es application/json y no hay cuerpo (práctica común para GET)
        # Aunque self.session.get lo manejará, ser explícito no daña.
        # Si el Accept es application/json, eso es lo que importa para la respuesta.
        # No modificaremos Content-Type aquí a menos que sea problemático.

        timeout_to_use = kwargs.pop('timeout', self.default_timeout)
        stream_response = kwargs.pop('stream', False) # Para manejar descargas de archivos

        logger.debug(f"{log_context} - Headers: { {k: (v if k != 'Authorization' else '[TOKEN OMITIDO]') for k,v in request_headers.items()} }, Timeout: {timeout_to_use}s, Stream: {stream_response}")

        try:
            response = self.session.get(
                url, 
                headers=request_headers, 
                params=params, # Parámetros de query para GET
                timeout=timeout_to_use,
                stream=stream_response, 
                **kwargs
            )
            response.raise_for_status()
            logger.debug(f"{log_context} - Solicitud GET exitosa (Status: {response.status_code})")

            if stream_response: # Si es una descarga de archivo, devolver contenido binario
                logger.info(f"{log_context} - Respuesta en stream, devolviendo content (bytes).")
                return response.content # El router se encargará de Response(content=result...)

            # Intentar devolver JSON, si falla, devolver texto crudo.
            # Esto se alinea con la sugerencia de las instrucciones.
            try:
                return response.json()
            except requests.exceptions.JSONDecodeError:
                logger.warning(f"{log_context} - Respuesta GET no es JSON. Status: {response.status_code}. Devolviendo texto crudo: {response.text[:200]}...")
                return response.text
        except requests.exceptions.HTTPError as http_err:
            # Reutilizar la lógica de error de self.request adaptándola
            error_message = f"Error HTTP en GET {url}: {http_err.response.status_code if http_err.response is not None else 'N/A'}"
            if http_err.response is not None:
                try:
                    error_details_json = http_err.response.json()
                    error_info = error_details_json.get("error", error_details_json)
                    error_message_from_api = error_info.get("message", str(error_info))
                    if error_message_from_api: error_message += f" - API Message: {error_message_from_api}"
                except json.JSONDecodeError:
                    error_message += f" - Respuesta no JSON: {http_err.response.text[:1000] if http_err.response.text else 'Sin cuerpo.'}..."
            logger.error(f"{log_context} - {error_message}", exc_info=False)
            raise # Relanzar para que el router lo maneje
        except requests.exceptions.RequestException as req_err:
            logger.error(f"{log_context} - Error de conexión/red GET: {req_err}", exc_info=True)
            raise
        except Exception as e:
            logger.exception(f"{log_context} - Error inesperado durante solicitud GET: {e}")
            raise

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

# --- FIN DEL MÓDULO helpers/http_client.py ---