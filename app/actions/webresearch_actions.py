import requests
import json
import time
import hashlib
import logging
from typing import Dict, Any, Optional, List
from urllib.parse import urljoin, urlparse, quote_plus
from datetime import datetime, timedelta
import re
from bs4 import BeautifulSoup
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor
import os

# Configurar logging
logger = logging.getLogger(__name__)

# Cache simple en memoria
_url_cache = {}
_rate_limit_tracker = {}

def _get_headers() -> Dict[str, str]:
    """Obtiene headers estándar para las requests web."""
    return {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9,es;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }

def _handle_web_error(error: Exception, action_name: str, url: str = "") -> Dict[str, Any]:
    """Maneja errores web de forma centralizada."""
    error_message = f"Error en {action_name}"
    if url:
        error_message += f" para URL {url}"
    error_message += f": {str(error)}"
    
    logger.error(error_message)
    
    return {
        "success": False,
        "error": error_message,
        "url": url,
        "timestamp": datetime.now().isoformat()
    }

def _validate_url(url: str) -> bool:
    """Valida que una URL sea válida."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False

def _get_cache_key(url: str, params: Dict[str, Any]) -> str:
    """Genera una clave de caché única para URL y parámetros."""
    cache_data = f"{url}_{json.dumps(params, sort_keys=True)}"
    return hashlib.md5(cache_data.encode()).hexdigest()

def _check_rate_limit(domain: str, max_requests: int = 10, window_seconds: int = 60) -> bool:
    """Verifica si se puede hacer una request considerando rate limiting."""
    now = time.time()
    
    if domain not in _rate_limit_tracker:
        _rate_limit_tracker[domain] = []
    
    # Limpiar requests antiguas
    _rate_limit_tracker[domain] = [
        req_time for req_time in _rate_limit_tracker[domain]
        if now - req_time < window_seconds
    ]
    
    # Verificar límite
    if len(_rate_limit_tracker[domain]) >= max_requests:
        return False
    
    _rate_limit_tracker[domain].append(now)
    return True

def fetch_url(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Obtiene el contenido de una URL con validación, caché y rate limiting
    """
    action_name = "fetch_url"
    
    try:
        url = params.get('url')
        if not url:
            return {
                "success": False,
                "error": "URL es requerida",
                "timestamp": datetime.now().isoformat()
            }
        
        if not _validate_url(url):
            return {
                "success": False,
                "error": "URL inválida",
                "url": url,
                "timestamp": datetime.now().isoformat()
            }
        
        timeout = params.get('timeout', 30)
        use_cache = params.get('use_cache', True)
        cache_ttl = params.get('cache_ttl', 3600)
        
        # Verificar caché
        cache_key = _get_cache_key(url, params)
        if use_cache and cache_key in _url_cache:
            cached_data = _url_cache[cache_key]
            if datetime.now() - cached_data['timestamp'] < timedelta(seconds=cache_ttl):
                cached_data['data']['from_cache'] = True
                return cached_data['data']
        
        # Rate limiting
        domain = urlparse(url).netloc
        if not _check_rate_limit(domain):
            return {
                "success": False,
                "error": "Rate limit excedido para este dominio",
                "url": url,
                "timestamp": datetime.now().isoformat()
            }
        
        headers = _get_headers()
        
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        
        result = {
            "success": True,
            "data": {
                "url": url,
                "status_code": response.status_code,
                "content": response.text,
                "headers": dict(response.headers),
                "encoding": response.encoding,
                "content_length": len(response.content),
                "from_cache": False
            },
            "timestamp": datetime.now().isoformat()
        }
        
        # Guardar en caché
        if use_cache:
            _url_cache[cache_key] = {
                'data': result,
                'timestamp': datetime.now()
            }
        
        return result
        
    except Exception as e:
        return _handle_web_error(e, action_name, params.get('url', ''))

def search_web(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Realiza búsquedas web usando múltiples motores de búsqueda
    """
    action_name = "search_web"
    
    try:
        query = params.get('query')
        if not query:
            return {
                "success": False,
                "error": "Query de búsqueda es requerida",
                "timestamp": datetime.now().isoformat()
            }
        
        max_results = params.get('max_results', 10)
        search_engine = params.get('search_engine', 'duckduckgo')
        
        if search_engine == 'duckduckgo':
            return _search_duckduckgo(query, max_results)
        elif search_engine == 'google':
            return _search_google_custom(query, max_results)
        else:
            return {
                "success": False,
                "error": f"Motor de búsqueda no soportado: {search_engine}",
                "timestamp": datetime.now().isoformat()
            }
        
    except Exception as e:
        return _handle_web_error(e, action_name)

def _search_duckduckgo(query: str, max_results: int) -> Dict[str, Any]:
    """Búsqueda usando DuckDuckGo."""
    try:
        search_url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"
        headers = _get_headers()
        
        response = requests.get(search_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        for result_div in soup.find_all('div', class_='result')[:max_results]:
            title_elem = result_div.find('a', class_='result__a')
            snippet_elem = result_div.find('a', class_='result__snippet')
            
            if title_elem:
                results.append({
                    'title': title_elem.get_text(strip=True),
                    'url': title_elem.get('href', ''),
                    'snippet': snippet_elem.get_text(strip=True) if snippet_elem else ''
                })
        
        return {
            "success": True,
            "data": {
                "query": query,
                "results": results,
                "total_results": len(results),
                "search_engine": "duckduckgo"
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return _handle_web_error(e, "search_duckduckgo")

def _search_google_custom(query: str, max_results: int) -> Dict[str, Any]:
    """Búsqueda usando Google Custom Search API."""
    try:
        api_key = os.getenv('GOOGLE_SEARCH_API_KEY')
        search_engine_id = os.getenv('GOOGLE_SEARCH_ENGINE_ID')
        
        if not api_key or not search_engine_id:
            return {
                "success": False,
                "error": "API key o Search Engine ID de Google no configurados",
                "timestamp": datetime.now().isoformat()
            }
        
        search_url = f"https://www.googleapis.com/customsearch/v1"
        params = {
            'key': api_key,
            'cx': search_engine_id,
            'q': query,
            'num': min(max_results, 10)
        }
        
        response = requests.get(search_url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        results = []
        
        for item in data.get('items', []):
            results.append({
                'title': item.get('title', ''),
                'url': item.get('link', ''),
                'snippet': item.get('snippet', '')
            })
        
        return {
            "success": True,
            "data": {
                "query": query,
                "results": results,
                "total_results": len(results),
                "search_engine": "google"
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return _handle_web_error(e, "search_google_custom")

def extract_text_from_url(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extrae texto limpio de una URL
    """
    action_name = "extract_text_from_url"
    
    try:
        url = params.get('url')
        if not url:
            return {
                "success": False,
                "error": "URL es requerida",
                "timestamp": datetime.now().isoformat()
            }
        
        # Obtener contenido de la URL
        fetch_result = fetch_url(client, params)
        if not fetch_result['success']:
            return fetch_result
        
        content = fetch_result['data']['content']
        soup = BeautifulSoup(content, 'html.parser')
        
        # Remover scripts y estilos
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Extraer texto
        text = soup.get_text()
        
        # Limpiar texto
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        return {
            "success": True,
            "data": {
                "url": url,
                "text": text,
                "text_length": len(text),
                "word_count": len(text.split())
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return _handle_web_error(e, action_name, params.get('url', ''))

def check_url_status(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verifica el estado de una URL
    """
    action_name = "check_url_status"
    
    try:
        url = params.get('url')
        if not url:
            return {
                "success": False,
                "error": "URL es requerida",
                "timestamp": datetime.now().isoformat()
            }
        
        if not _validate_url(url):
            return {
                "success": False,
                "error": "URL inválida",
                "url": url,
                "timestamp": datetime.now().isoformat()
            }
        
        timeout = params.get('timeout', 30)
        headers = _get_headers()
        
        start_time = time.time()
        response = requests.head(url, headers=headers, timeout=timeout, allow_redirects=True)
        response_time = time.time() - start_time
        
        return {
            "success": True,
            "data": {
                "url": url,
                "status_code": response.status_code,
                "status_text": response.reason,
                "response_time": round(response_time, 3),
                "headers": dict(response.headers),
                "redirected": len(response.history) > 0,
                "final_url": response.url,
                "is_accessible": 200 <= response.status_code < 400
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return _handle_web_error(e, action_name, params.get('url', ''))

def scrape_website_data(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extrae datos específicos de un sitio web usando selectores CSS
    """
    action_name = "scrape_website_data"
    
    try:
        url = params.get('url')
        selectors = params.get('selectors', {})
        
        if not url:
            return {
                "success": False,
                "error": "URL es requerida",
                "timestamp": datetime.now().isoformat()
            }
        
        if not selectors:
            return {
                "success": False,
                "error": "Selectores CSS son requeridos",
                "timestamp": datetime.now().isoformat()
            }
        
        # Obtener contenido
        fetch_result = fetch_url(client, params)
        if not fetch_result['success']:
            return fetch_result
        
        content = fetch_result['data']['content']
        soup = BeautifulSoup(content, 'html.parser')
        
        extracted_data = {}
        
        for key, selector in selectors.items():
            try:
                elements = soup.select(selector)
                if len(elements) == 1:
                    extracted_data[key] = elements[0].get_text(strip=True)
                elif len(elements) > 1:
                    extracted_data[key] = [elem.get_text(strip=True) for elem in elements]
                else:
                    extracted_data[key] = None
            except Exception as e:
                extracted_data[key] = f"Error: {str(e)}"
        
        return {
            "success": True,
            "data": {
                "url": url,
                "extracted_data": extracted_data,
                "selectors_used": selectors
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return _handle_web_error(e, action_name, params.get('url', ''))

def batch_url_analysis(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analiza múltiples URLs en lote
    """
    action_name = "batch_url_analysis"
    
    try:
        urls = params.get('urls', [])
        if not urls:
            return {
                "success": False,
                "error": "Lista de URLs es requerida",
                "timestamp": datetime.now().isoformat()
            }
        
        max_workers = params.get('max_workers', 5)
        analysis_type = params.get('analysis_type', 'status')  # status, content, text
        
        results = []
        
        def analyze_single_url(url):
            try:
                if analysis_type == 'status':
                    return check_url_status(client, {'url': url})
                elif analysis_type == 'content':
                    return fetch_url(client, {'url': url})
                elif analysis_type == 'text':
                    return extract_text_from_url(client, {'url': url})
                else:
                    return {
                        "success": False,
                        "error": f"Tipo de análisis no soportado: {analysis_type}",
                        "url": url
                    }
            except Exception as e:
                return _handle_web_error(e, f"analyze_{analysis_type}", url)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(executor.map(analyze_single_url, urls))
        
        successful_results = [r for r in results if r.get('success', False)]
        failed_results = [r for r in results if not r.get('success', False)]
        
        return {
            "success": True,
            "data": {
                "total_urls": len(urls),
                "successful": len(successful_results),
                "failed": len(failed_results),
                "results": results,
                "analysis_type": analysis_type
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return _handle_web_error(e, action_name)

def monitor_website_changes(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Monitorea cambios en un sitio web
    """
    action_name = "monitor_website_changes"
    
    try:
        url = params.get('url')
        if not url:
            return {
                "success": False,
                "error": "URL es requerida",
                "timestamp": datetime.now().isoformat()
            }
        
        # Obtener contenido actual
        current_result = fetch_url(client, {'url': url, 'use_cache': False})
        if not current_result['success']:
            return current_result
        
        current_content = current_result['data']['content']
        current_hash = hashlib.md5(current_content.encode()).hexdigest()
        
        # Comparar con versión anterior si existe
        cache_key = f"monitor_{hashlib.md5(url.encode()).hexdigest()}"
        previous_data = _url_cache.get(cache_key)
        
        if previous_data:
            previous_hash = previous_data.get('hash')
            has_changed = current_hash != previous_hash
            
            if has_changed:
                # Calcular diferencias básicas
                current_text = BeautifulSoup(current_content, 'html.parser').get_text()
                previous_text = previous_data.get('text', '')
                
                word_diff = len(current_text.split()) - len(previous_text.split())
                char_diff = len(current_text) - len(previous_text)
        else:
            has_changed = True  # Primera vez
            word_diff = 0
            char_diff = 0
        
        # Guardar datos actuales
        _url_cache[cache_key] = {
            'hash': current_hash,
            'text': BeautifulSoup(current_content, 'html.parser').get_text(),
            'timestamp': datetime.now()
        }
        
        return {
            "success": True,
            "data": {
                "url": url,
                "has_changed": has_changed,
                "current_hash": current_hash,
                "word_count_difference": word_diff,
                "character_count_difference": char_diff,
                "last_checked": datetime.now().isoformat()
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return _handle_web_error(e, action_name, params.get('url', ''))