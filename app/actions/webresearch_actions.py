import os
import re
import json
import time
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse, quote_plus
import requests
from bs4 import BeautifulSoup

# Cache simple en memoria
_url_cache = {}
_last_request_time = 0
REQUEST_DELAY = 1  # Delay entre requests en segundos

def _get_headers() -> Dict[str, str]:
    """Retorna headers comunes para requests web."""
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }

def _rate_limit():
    """Implementa rate limiting básico."""
    global _last_request_time
    current_time = time.time()
    time_since_last = current_time - _last_request_time
    
    if time_since_last < REQUEST_DELAY:
        time.sleep(REQUEST_DELAY - time_since_last)
    
    _last_request_time = time.time()

def _get_cached_result(cache_key: str) -> Optional[Dict[str, Any]]:
    """Obtiene resultado del cache si existe y no ha expirado."""
    if cache_key in _url_cache:
        cached = _url_cache[cache_key]
        # Cache válido por 1 hora
        if time.time() - cached['timestamp'] < 3600:
            return cached['data']
        else:
            del _url_cache[cache_key]
    return None

def _cache_result(cache_key: str, data: Dict[str, Any]):
    """Guarda resultado en cache."""
    _url_cache[cache_key] = {
        'data': data,
        'timestamp': time.time()
    }

def _handle_web_error(error: Exception, action_name: str) -> Dict[str, Any]:
    """Maneja errores de forma consistente."""
    return {
        "success": False,
        "error": str(error),
        "action": action_name,
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

def fetch_url(client, params: Dict[str, Any]) -> Dict[str, Any]:
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
                "error": "URL no válida",
                "timestamp": datetime.now().isoformat()
            }
        
        use_cache = params.get('use_cache', True)
        cache_key = _get_cache_key(url, params)
        
        # Verificar cache
        if use_cache:
            cached_result = _get_cached_result(cache_key)
            if cached_result:
                return cached_result
        
        # Rate limiting
        _rate_limit()
        
        headers = _get_headers()
        timeout = params.get('timeout', 30)
        
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        
        result = {
            "success": True,
            "url": url,
            "status_code": response.status_code,
            "content": response.text,
            "headers": dict(response.headers),
            "encoding": response.encoding,
            "timestamp": datetime.now().isoformat()
        }
        
        # Guardar en cache
        if use_cache:
            _cache_result(cache_key, result)
        
        return result
        
    except requests.exceptions.RequestException as e:
        return _handle_web_error(e, action_name)
    except Exception as e:
        return _handle_web_error(e, action_name)

def search_web(client, params: Dict[str, Any]) -> Dict[str, Any]:
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
                    'title': title_elem.get_text().strip(),
                    'url': title_elem.get('href', ''),
                    'snippet': snippet_elem.get_text().strip() if snippet_elem else ''
                })
        
        return {
            "success": True,
            "query": query,
            "results": results,
            "count": len(results),
            "search_engine": "duckduckgo",
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
        
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            'key': api_key,
            'cx': search_engine_id,
            'q': query,
            'num': min(max_results, 10)  # Google permite máximo 10 por request
        }
        
        response = requests.get(url, params=params, timeout=30)
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
            "query": query,
            "results": results,
            "count": len(results),
            "search_engine": "google",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return _handle_web_error(e, "search_google_custom")

def extract_text_from_url(client, params: Dict[str, Any]) -> Dict[str, Any]:
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
        if not fetch_result.get('success'):
            return fetch_result
        
        content = fetch_result.get('content', '')
        text = _extract_text_from_html(content)
        metadata = _extract_metadata(content)
        
        return {
            "success": True,
            "url": url,
            "text": text,
            "metadata": metadata,
            "word_count": len(text.split()),
            "char_count": len(text),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return _handle_web_error(e, action_name)

def check_url_status(client, params: Dict[str, Any]) -> Dict[str, Any]:
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
                "error": "URL no válida",
                "timestamp": datetime.now().isoformat()
            }
        
        headers = _get_headers()
        timeout = params.get('timeout', 10)
        
        response = requests.head(url, headers=headers, timeout=timeout, allow_redirects=True)
        
        return {
            "success": True,
            "url": url,
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "final_url": response.url,
            "is_accessible": 200 <= response.status_code < 400,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return _handle_web_error(e, action_name)

def scrape_website_data(client, params: Dict[str, Any]) -> Dict[str, Any]:
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
        
        # Obtener contenido
        fetch_result = fetch_url(client, params)
        if not fetch_result.get('success'):
            return fetch_result
        
        content = fetch_result.get('content', '')
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
            "url": url,
            "data": extracted_data,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return _handle_web_error(e, action_name)

def batch_url_analysis(client, params: Dict[str, Any]) -> Dict[str, Any]:
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
                return _handle_web_error(e, f"batch_analysis_{url}")
        
        # Procesar URLs secuencialmente para evitar rate limiting
        for url in urls:
            result = analyze_single_url(url)
            results.append(result)
        
        successful_results = [r for r in results if r.get('success')]
        
        return {
            "success": True,
            "analysis_type": analysis_type,
            "total_urls": len(urls),
            "successful": len(successful_results),
            "failed": len(urls) - len(successful_results),
            "results": results,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return _handle_web_error(e, action_name)

def monitor_website_changes(client, params: Dict[str, Any]) -> Dict[str, Any]:
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
        if not current_result.get('success'):
            return current_result
        
        current_content = current_result.get('content', '')
        current_hash = hashlib.md5(current_content.encode()).hexdigest()
        
        # Obtener hash anterior del cache (si existe)
        cache_key = f"monitor_{url}"
        previous_data = _get_cached_result(cache_key)
        
        if previous_data:
            previous_hash = previous_data.get('content_hash')
            has_changed = current_hash != previous_hash
            
            # Análisis básico de cambios
            if has_changed:
                current_text = _extract_text_from_html(current_content)
                previous_text = previous_data.get('text', '')
                
                # Calcular diferencias simples
                current_words = set(current_text.split())
                previous_words = set(previous_text.split())
                
                added_words = current_words - previous_words
                removed_words = previous_words - current_words
                
                change_analysis = {
                    'words_added': len(added_words),
                    'words_removed': len(removed_words),
                    'total_change_percentage': (len(added_words) + len(removed_words)) / max(len(previous_words), 1) * 100
                }
            else:
                change_analysis = {}
        else:
            has_changed = True  # Primera vez monitoreando
            change_analysis = {"note": "Primera vez monitoreando esta URL"}
        
        # Guardar estado actual
        current_text = _extract_text_from_html(current_content)
        monitor_data = {
            'content_hash': current_hash,
            'text': current_text,
            'last_check': datetime.now().isoformat()
        }
        _cache_result(cache_key, monitor_data)
        
        return {
            "success": True,
            "url": url,
            "has_changed": has_changed,
            "current_hash": current_hash,
            "change_analysis": change_analysis,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return _handle_web_error(e, action_name)

def _extract_text_from_html(html: str) -> str:
    """Extrae texto limpio de HTML."""
    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        # Eliminar scripts y estilos
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Obtener texto
        text = soup.get_text()
        
        # Limpiar espacios en blanco
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text
    except Exception:
        return ""

def _extract_metadata(html: str) -> Dict[str, Any]:
    """Extrae metadata de HTML."""
    soup = BeautifulSoup(html, 'html.parser')
    
    metadata = {
        'title': '',
        'description': '',
        'keywords': '',
        'author': '',
        'og_data': {}
    }
    
    try:
        # Título
        title_tag = soup.find('title')
        if title_tag:
            metadata['title'] = title_tag.get_text().strip()
        
        # Meta tags
        for meta in soup.find_all('meta'):
            if meta.get('name') == 'description':
                metadata['description'] = meta.get('content', '')
            elif meta.get('name') == 'keywords':
                metadata['keywords'] = meta.get('content', '')
            elif meta.get('name') == 'author':
                metadata['author'] = meta.get('content', '')
            elif meta.get('property', '').startswith('og:'):
                og_property = meta.get('property')[3:]  # Remove 'og:' prefix
                metadata['og_data'][og_property] = meta.get('content', '')
    except Exception:
        pass
    
    return metadata

def webresearch_search_web(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Realiza búsquedas web específicas para investigación
    
    Args:
        client: Cliente HTTP
        params: Diccionario con parámetros:
            - query: Términos de búsqueda
            - num_results: Número de resultados (default: 5)
            - search_engine: Motor de búsqueda a usar (default: duckduckgo)
    
    Returns:
        Dict con los resultados de la búsqueda
    """
    action_name = "webresearch_search_web"
    
    try:
        query = params.get('query', '')
        num_results = params.get('num_results', 5)
        search_engine = params.get('search_engine', 'duckduckgo')
        
        if not query:
            raise ValueError("El parámetro 'query' es requerido")
        
        # Por ahora implementamos solo DuckDuckGo (no requiere API key)
        if search_engine == 'duckduckgo':
            url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"
            headers = _get_headers()
            
            _rate_limit()
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            
            # Extraer resultados de DuckDuckGo
            for result_div in soup.find_all('div', class_='web-result')[:num_results]:
                title_elem = result_div.find('h2')
                link_elem = result_div.find('a')
                snippet_elem = result_div.find('div', class_='result__snippet')
                
                if title_elem and link_elem:
                    results.append({
                        'title': title_elem.get_text().strip(),
                        'url': link_elem.get('href', ''),
                        'snippet': snippet_elem.get_text().strip() if snippet_elem else ''
                    })
            
            return {
                "success": True,
                "action": action_name,
                "query": query,
                "results": results,
                "count": len(results),
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise ValueError(f"Motor de búsqueda no soportado: {search_engine}")
            
    except Exception as e:
        return _handle_web_error(e, action_name)

def webresearch_scrape_url(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extrae contenido completo de una URL para investigación
    
    Args:
        client: Cliente HTTP
        params: Diccionario con parámetros:
            - url: URL a extraer
            - extract_images: Si extraer URLs de imágenes (default: False)
            - extract_links: Si extraer enlaces (default: False)
    
    Returns:
        Dict con el contenido extraído
    """
    action_name = "webresearch_scrape_url"
    
    try:
        url = params.get('url', '')
        extract_images = params.get('extract_images', False)
        extract_links = params.get('extract_links', False)
        
        if not url:
            raise ValueError("El parámetro 'url' es requerido")
        
        # Verificar cache
        cached_result = _get_cached_result(url)
        if cached_result:
            return cached_result
        
        # Obtener contenido
        fetch_result = fetch_url(client, {'url': url})
        if not fetch_result.get('success'):
            return fetch_result
        
        content = fetch_result.get('content', '')
        soup = BeautifulSoup(content, 'html.parser')
        
        # Extraer texto limpio
        text = _extract_text_from_html(content)
        
        # Extraer metadata
        metadata = _extract_metadata(content)
        
        result = {
            "success": True,
            "action": action_name,
            "url": url,
            "text": text,
            "metadata": metadata,
            "word_count": len(text.split()),
            "timestamp": datetime.now().isoformat()
        }
        
        # Extraer imágenes si se solicita
        if extract_images:
            images = []
            for img in soup.find_all('img'):
                src = img.get('src', '')
                if src:
                    if src.startswith('//'):
                        src = 'https:' + src
                    elif src.startswith('/'):
                        from urllib.parse import urljoin
                        src = urljoin(url, src)
                    
                    images.append({
                        'src': src,
                        'alt': img.get('alt', ''),
                        'title': img.get('title', '')
                    })
            result['images'] = images
        
        # Extraer enlaces si se solicita
        if extract_links:
            links = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                if href.startswith('//'):
                    href = 'https:' + href
                elif href.startswith('/'):
                    from urllib.parse import urljoin
                    href = urljoin(url, href)
                
                links.append({
                    'url': href,
                    'text': link.get_text().strip(),
                    'title': link.get('title', '')
                })
            result['links'] = links
        
        # Guardar en cache
        _cache_result(url, result)
        
        return result
        
    except Exception as e:
        return _handle_web_error(e, action_name)

def webresearch_extract_emails(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extrae direcciones de email de una URL o texto
    
    Args:
        client: Cliente HTTP
        params: Diccionario con parámetros:
            - url: URL de la cual extraer emails (opcional)
            - text: Texto del cual extraer emails (opcional)
    
    Returns:
        Dict con las direcciones de email encontradas
    """
    action_name = "webresearch_extract_emails"
    
    try:
        url = params.get('url')
        text = params.get('text', '')
        
        if not url and not text:
            raise ValueError("Se requiere 'url' o 'text'")
        
        # Si se proporciona URL, obtener el contenido
        if url:
            scrape_result = webresearch_scrape_url(client, {'url': url})
            if not scrape_result.get('success'):
                return scrape_result
            text = scrape_result.get('text', '')
        
        # Patrón regex para emails
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        
        # Eliminar duplicados manteniendo el orden
        unique_emails = list(dict.fromkeys(emails))
        
        return {
            "success": True,
            "action": action_name,
            "emails": unique_emails,
            "count": len(unique_emails),
            "source_url": url if url else "text_input",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return _handle_web_error(e, action_name)

def webresearch_extract_phone_numbers(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extrae números de teléfono de una URL o texto
    
    Args:
        client: Cliente HTTP
        params: Diccionario con parámetros:
            - url: URL de la cual extraer teléfonos (opcional)
            - text: Texto del cual extraer teléfonos (opcional)
    
    Returns:
        Dict con los números de teléfono encontrados
    """
    action_name = "webresearch_extract_phone_numbers"
    
    try:
        url = params.get('url')
        text = params.get('text', '')
        
        if not url and not text:
            raise ValueError("Se requiere 'url' o 'text'")
        
        # Si se proporciona URL, obtener el contenido
        if url:
            scrape_result = webresearch_scrape_url(client, {'url': url})
            if not scrape_result.get('success'):
                return scrape_result
            text = scrape_result.get('text', '')
        
        # Patrones regex para diferentes formatos de teléfono
        phone_patterns = [
            r'\b\d{3}-\d{3}-\d{4}\b',  # 123-456-7890
            r'\b\(\d{3}\)\s*\d{3}-\d{4}\b',  # (123) 456-7890
            r'\b\d{3}\.\d{3}\.\d{4}\b',  # 123.456.7890
            r'\b\d{10}\b',  # 1234567890
            r'\+\d{1,3}\s*\d{3,4}\s*\d{3,4}\s*\d{3,4}',  # +1 123 456 7890
        ]
        
        phone_numbers = []
        for pattern in phone_patterns:
            matches = re.findall(pattern, text)
            phone_numbers.extend(matches)
        
        # Eliminar duplicados manteniendo el orden
        unique_phones = list(dict.fromkeys(phone_numbers))
        
        return {
            "success": True,
            "action": action_name,
            "phone_numbers": unique_phones,
            "count": len(unique_phones),
            "source_url": url if url else "text_input",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return _handle_web_error(e, action_name)