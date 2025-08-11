"""
Helpers para interactuar con servicios de Azure como KeyVault para obtener credenciales.
"""
import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

# Logging
logger = logging.getLogger(__name__)

# Cache para credenciales
_credential_cache = {}
_credential_expiry = {}

def get_azure_credential(service_name: str) -> Optional[Dict[str, Any]]:
    """
    Obtiene credenciales desde Azure KeyVault o App Configuration.
    
    Args:
        service_name: Nombre del servicio (youtube, google_ads, etc.)
        
    Returns:
        Dict con credenciales o None si no se encuentran
    """
    # Verificar caché primero
    if service_name in _credential_cache:
        if datetime.now() < _credential_expiry.get(service_name, datetime.min):
            logger.debug(f"Usando credenciales cacheadas para {service_name}")
            return _credential_cache[service_name]
    
    # Comprobar si estamos en Azure
    is_azure = os.environ.get('WEBSITE_SITE_NAME') is not None
    
    if is_azure:
        try:
            # Opción 1: Azure KeyVault (requiere azure-keyvault-secrets)
            credential = _get_from_keyvault(service_name)
            if credential:
                _cache_credential(service_name, credential)
                return credential
                
            # Opción 2: Azure App Configuration (requiere azure-appconfiguration)
            credential = _get_from_app_config(service_name)
            if credential:
                _cache_credential(service_name, credential)
                return credential
                
            # Opción 3: Variables de entorno de App Service (último recurso)
            credential = _get_from_app_service_settings(service_name)
            if credential:
                _cache_credential(service_name, credential)
                return credential
                
        except ImportError:
            logger.warning("Bibliotecas de Azure no instaladas. Instala azure-keyvault-secrets y/o azure-appconfiguration")
            return None
        except Exception as e:
            logger.error(f"Error accediendo a credenciales de Azure para {service_name}: {e}")
            return None
    else:
        logger.debug(f"No estamos en Azure, no se pueden obtener credenciales para {service_name}")
        return None

def _cache_credential(service_name: str, credential: Dict[str, Any], ttl_minutes: int = 50) -> None:
    """Guarda credencial en caché con TTL."""
    _credential_cache[service_name] = credential
    _credential_expiry[service_name] = datetime.now() + timedelta(minutes=ttl_minutes)

def _get_from_keyvault(service_name: str) -> Optional[Dict[str, Any]]:
    """Obtiene credenciales desde Azure KeyVault."""
    try:
        from azure.identity import DefaultAzureCredential
        from azure.keyvault.secrets import SecretClient
        
        # Obtener URL del Key Vault de la configuración
        vault_url = os.environ.get('AZURE_KEYVAULT_URL')
        if not vault_url:
            logger.warning("AZURE_KEYVAULT_URL no configurada")
            return None
            
        # Autenticarse con la identidad asignada
        credential = DefaultAzureCredential()
        client = SecretClient(vault_url=vault_url, credential=credential)
        
        # Buscar credenciales para el servicio
        secret_name = f"{service_name.upper()}-CREDENTIALS"
        secret = client.get_secret(secret_name)
        
        if secret and secret.value:
            import json
            try:
                # Intentar decodificar como JSON
                return json.loads(secret.value)
            except json.JSONDecodeError:
                # Formato alternativo de credenciales
                logger.warning(f"Credencial para {service_name} no es JSON válido")
                return {"access_token": secret.value}
        
        return None
    except ImportError:
        logger.warning("azure-keyvault-secrets no está instalado")
        return None
    except Exception as e:
        logger.error(f"Error accediendo a KeyVault: {e}")
        return None

def _get_from_app_config(service_name: str) -> Optional[Dict[str, Any]]:
    """Obtiene credenciales desde Azure App Configuration."""
    # Implementación similar a KeyVault pero con App Configuration
    return None  # Implementar según necesidad

def _get_from_app_service_settings(service_name: str) -> Optional[Dict[str, Any]]:
    """Obtiene credenciales desde variables de entorno de App Service."""
    prefix = service_name.upper()
    
    # Buscar ACCESS_TOKEN, CLIENT_ID, etc.
    access_token = os.environ.get(f'{prefix}_ACCESS_TOKEN')
    if access_token:
        return {
            "access_token": access_token,
            "client_id": os.environ.get(f'{prefix}_CLIENT_ID', ''),
            "client_secret": os.environ.get(f'{prefix}_CLIENT_SECRET', ''),
            "refresh_token": os.environ.get(f'{prefix}_REFRESH_TOKEN', '')
        }
    
    return None
