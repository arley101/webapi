# app/actions/webresearch_actions.py
import logging
import requests
import validators
from typing import Dict, Any, Optional
from urllib.parse import urlparse
from datetime import datetime, timedelta
from functools import lru_cache
import time

logger = logging.getLogger(__name__)

# Configuración
DEFAULT_TIMEOUT = 30
DEFAULT_CACHE_TTL = 3600  # 1 hora en segundos
RATE_LIMIT_CALLS = 60  # número máximo de llamadas
RATE_LIMIT_PERIOD = 60  # período en segundos

# Control de rate limiting
last_calls = []

class WebResearchError(Exception):
    """Excepción personalizada para errores de Web Research"""
    pass

def validate_url(url: str) -> bool:
    """Valida que la URL sea válida y utilice HTTP/HTTPS"""
    if not validators.url(url):
        return False
    parsed = urlparse(url)
    return parsed.scheme in ['http', 'https']

def check_rate_limit():
    """Implementa rate limiting"""
    global last_calls
    current_time = time.time()
    
    # Limpia llamadas antiguas
    last_calls = [call_time for call_time in last_calls 
                 if current_time - call_time <= RATE_LIMIT_PERIOD]
    
    if len(last_calls) >= RATE_LIMIT_CALLS:
        raise WebResearchError("Rate limit exceeded. Please try again later.")
    
    last_calls.append(current_time)

@lru_cache(maxsize=100)
def cached_request(url: str, cache_ttl: int) -> Dict[str, Any]:
    """Realiza la petición HTTP con caché"""
    return requests.get(url, headers=get_headers(), timeout=DEFAULT_TIMEOUT).text

def get_headers() -> Dict[str, str]:
    """Retorna headers personalizados para las peticiones"""
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
    }

def fetch_url(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Obtiene el contenido de una URL con validación, caché y rate limiting
    
    Args:
        client: Cliente de la API (no usado en este caso)
        params: Diccionario con parámetros:
            - url: URL a consultar (requerido)
            - timeout: Timeout en segundos (opcional)
            - use_cache: Booleano para usar caché (opcional)
            - cache_ttl: Tiempo de vida del caché en segundos (opcional)
            - proxy: Proxy a utilizar (opcional)
    
    Returns:
        Dict con el resultado de la consulta
    """
    action_name = "fetch_url"
    
    try:
        # Validación de parámetros
        url = params.get("url")
        if not url:
            raise WebResearchError("'url' es un parámetro requerido")
        
        if not validate_url(url):
            raise WebResearchError("URL inválida o no soportada")
            
        # Configuración
        timeout = params.get("timeout", DEFAULT_TIMEOUT)
        use_cache = params.get("use_cache", True)
        cache_ttl = params.get("cache_ttl", DEFAULT_CACHE_TTL)
        proxy = params.get("proxy")
        
        # Rate limiting
        check_rate_limit()
        
        # Configuración de proxy si existe
        proxies = {"http": proxy, "https": proxy} if proxy else None
        
        # Intenta obtener de caché si está habilitado
        if use_cache:
            try:
                content = cached_request(url, cache_ttl)
                return {
                    "status": "success",
                    "data": {
                        "content": content,
                        "from_cache": True,
                        "timestamp": datetime.now().isoformat()
                    }
                }
            except Exception as e:
                logger.warning(f"Cache miss para URL {url}: {str(e)}")
        
        # Realiza la petición HTTP
        response = requests.get(
            url,
            headers=get_headers(),
            timeout=timeout,
            proxies=proxies
        )
        response.raise_for_status()
        
        return {
            "status": "success",
            "data": {
                "content": response.text,
                "from_cache": False,
                "timestamp": datetime.now().isoformat(),
                "headers": dict(response.headers),
                "status_code": response.status_code
            }
        }
        
    except WebResearchError as e:
        logger.error(f"Error de validación en {action_name}: {str(e)}")
        return {"status": "error", "action": action_name, "message": str(e), "http_status": 400}
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error de red en {action_name}: {str(e)}")
        return {"status": "error", "action": action_name, "message": str(e), "http_status": 500}
        
    except Exception as e:
        logger.error(f"Error en {action_name}: {str(e)}", exc_info=True)
        return {"status": "error", "action": action_name, "message": str(e), "http_status": 500}