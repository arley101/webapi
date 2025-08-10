import requests, json, base64, logging
from typing import Dict, Any, Optional, List  # ✅ Any disponible
from datetime import datetime, timedelta
import hashlib, time, os
from urllib.parse import urljoin, quote
from app.core.auth_manager import token_manager
from app.core.config import settings  # ✅ IMPORT FALTANTE AGREGADO

# Configurar logging
logger = logging.getLogger(__name__)

# Cache para sesiones de WordPress
_wp_sessions = {}
_wp_cache = {}

def _get_wp_credentials(params: Dict[str, Any]) -> Dict[str, str]:
    """Obtiene credenciales de WordPress desde parámetros o variables de entorno."""
    return {
        'site_url': params.get('site_url') or getattr(settings, 'WP_SITE_URL', ''),
        'username': params.get('username') or getattr(settings, 'WP_USERNAME', '') or getattr(settings, 'WP_JWT_USERNAME', ''),
        'password': params.get('password') or getattr(settings, 'WP_PASSWORD', '') or getattr(settings, 'WP_JWT_PASSWORD', ''),
        'app_password': params.get('app_password') or getattr(settings, 'WP_APP_PASSWORD', ''),
        'consumer_key': params.get('consumer_key') or getattr(settings, 'WC_CONSUMER_KEY', ''),
        'consumer_secret': params.get('consumer_secret') or getattr(settings, 'WC_CONSUMER_SECRET', ''),
        'auth_mode': params.get('auth_mode') or getattr(settings, 'WP_AUTH_MODE', 'jwt')
    }

def _handle_wp_api_error(error: Exception, action_name: str, site_url: str = "") -> Dict[str, Any]:
    """Maneja errores de WordPress API de forma centralizada."""
    error_message = f"Error en {action_name}"
    if site_url:
        error_message += f" para sitio {site_url}"
    error_message += f": {str(error)}"
    
    logger.error(error_message)
    
    return {
        "status": "error",
        "error": error_message,
        "action": action_name,
        "site_url": site_url,
        "timestamp": datetime.now().isoformat()
    }

def _validate_wp_credentials(credentials: Dict[str, str]) -> bool:
    """Valida que las credenciales de WordPress estén completas."""
    # Para JWT, solo necesitamos site_url ya que las credenciales vienen de settings
    site_url = credentials.get('site_url')
    if not site_url:
        return False
    
    auth_mode = credentials.get('auth_mode', 'jwt')
    
    if auth_mode == 'jwt':
        # JWT funciona con settings, solo verificar que tengamos la URL
        return bool(site_url)
    elif auth_mode == 'app_password':
        return bool(credentials.get('app_password') and credentials.get('username'))
    elif auth_mode == 'woocommerce':
        return bool(credentials.get('consumer_key') and credentials.get('consumer_secret'))
    else:
        # Para 'auto', JWT siempre está disponible si tenemos site_url
        return bool(site_url)

def _get_wp_auth_headers(credentials: Dict[str, str], auth_type: str = 'auto') -> Dict[str, str]:
    """Sistema inteligente de autenticación WordPress"""
    
    # Si es automático, usar el gestor centralizado
    if auth_type == 'auto':
        try:
            auth_data = token_manager.get_wordpress_auth(
                site_url=credentials.get('site_url'),
                auth_mode=credentials.get('auth_mode')
            )
            logger.info(f"Usando autenticación automática: {auth_data['type']}")
            return auth_data.get('headers', {})
        except Exception as e:
            logger.warning(f"Autenticación automática falló: {str(e)}, intentando fallbacks...")
    
    # Fallbacks manuales (mantener compatibilidad)
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'User-Agent': 'EliteDynamics-WordPress-Client/1.2.0'
    }
    
    # JWT manual
    if auth_type == 'jwt' or (auth_type == 'auto' and not headers.get('Authorization')):
        try:
            jwt_token = token_manager.get_wordpress_jwt_token(credentials.get('site_url'))
            headers['Authorization'] = f'Bearer {jwt_token}'
            logger.info("Usando JWT manual como fallback")
            return headers
        except Exception as jwt_error:
            logger.warning(f"JWT manual falló: {str(jwt_error)}")
    
    # Application Password fallback
    if credentials.get('app_password') and credentials.get('username'):
        auth_string = f"{credentials['username']}:{credentials['app_password']}"
        encoded_auth = base64.b64encode(auth_string.encode()).decode()
        headers['Authorization'] = f'Basic {encoded_auth}'
        logger.info("Usando Application Password como fallback")
    
    # Basic Auth último recurso
    elif credentials.get('username') and credentials.get('password'):
        auth_string = f"{credentials['username']}:{credentials['password']}"
        encoded_auth = base64.b64encode(auth_string.encode()).decode()
        headers['Authorization'] = f'Basic {encoded_auth}'
        logger.info("Usando Basic Auth como último recurso")
    
    return headers

def _make_wp_rest_request(method: str, endpoint: str, params: Dict[str, Any], 
                         data: Optional[Dict[str, Any]] = None, 
                         query_params: Optional[Dict[str, Any]] = None,
                         auth_type: str = 'auto') -> Any:
    """Request WordPress con autenticación automática inteligente"""
    credentials = _get_wp_credentials(params)
    
    # Agregar modo de autenticación a credenciales
    credentials['auth_mode'] = params.get('auth_mode') or 'jwt'
    
    if not _validate_wp_credentials(credentials):
        raise ValueError("Credenciales de WordPress incompletas o inválidas")
    
    site_url = credentials['site_url'].rstrip('/')
    full_url = f"{site_url}/wp-json/wp/v2/{endpoint.lstrip('/')}"
    
    # Sistema inteligente de autenticación
    headers = _get_wp_auth_headers(credentials, auth_type)
    
    # Configurar request
    request_params = {
        'headers': headers,
        'timeout': params.get('timeout', 30),
        'verify': params.get('verify_ssl', True)
    }
    
    # Agregar autenticación WooCommerce si es necesario
    if credentials.get('auth_mode') == 'woocommerce':
        auth_data = token_manager.get_wordpress_auth(site_url, 'woocommerce')
        if 'auth' in auth_data:
            request_params['auth'] = auth_data['auth']
    
    if data:
        request_params['json'] = data
    
    if query_params:
        request_params['params'] = query_params
    
    try:
        logger.info(f"WordPress API Request: {method} {full_url}")
        response = requests.request(method, full_url, **request_params)
        response.raise_for_status()
        
        return response.json() if response.content else {}
        
    except requests.exceptions.HTTPError as e:
        if response.status_code == 401:
            # Fallback automático inteligente
            if auth_type == 'auto':
                logger.warning("Autenticación principal falló, intentando métodos alternativos...")
                # Intentar con app_password si JWT falló
                if credentials.get('app_password'):
                    return _make_wp_rest_request(method, endpoint, {**params, 'auth_mode': 'app_password'}, data, query_params, 'app_password')
                # Último recurso: basic auth
                elif credentials.get('password'):
                    return _make_wp_rest_request(method, endpoint, {**params, 'auth_mode': 'basic'}, data, query_params, 'basic')
            
            raise ValueError(f"Error de autenticación WordPress (401): Verificar credenciales y plugins JWT")
        elif response.status_code == 403:
            raise ValueError(f"Sin permisos para esta operación WordPress (403)")
        elif response.status_code == 404:
            raise ValueError(f"Endpoint no encontrado WordPress (404): {endpoint}")
        else:
            raise ValueError(f"Error HTTP WordPress ({response.status_code}): {str(e)}")
    
    except requests.exceptions.ConnectionError:
        raise ValueError(f"No se puede conectar al sitio WordPress: {site_url}")
    
    except requests.exceptions.Timeout:
        raise ValueError(f"Timeout en la conexión a WordPress después de {request_params['timeout']}s")

def _make_wc_request(method: str, endpoint: str, params: Dict[str, Any],
                    data: Optional[Dict[str, Any]] = None,
                    query_params: Optional[Dict[str, Any]] = None) -> Any:
    """Request WooCommerce con autenticación automática"""
    try:
        # Usar sistema de autenticación centralizado
        site_url = params.get('site_url') or settings.WP_SITE_URL
        auth_data = token_manager.get_wordpress_auth(site_url, 'woocommerce')
        
        full_url = f"{site_url.rstrip('/')}/wp-json/wc/v3/{endpoint.lstrip('/')}"
        
        request_params = {
            'headers': auth_data['headers'],
            'timeout': params.get('timeout', 30),
            'verify': params.get('verify_ssl', True)
        }
        
        # Agregar autenticación WooCommerce
        if 'auth' in auth_data:
            request_params['auth'] = auth_data['auth']
        
        if data:
            request_params['json'] = data
        
        if query_params:
            request_params['params'] = query_params
        
        logger.info(f"WooCommerce API Request: {method} {full_url}")
        response = requests.request(method, full_url, **request_params)
        response.raise_for_status()
        
        return response.json() if response.content else {}
        
    except Exception as e:
        # Usar el handler de errores existente
        return _handle_wp_api_error(e, "woocommerce_request", params.get('site_url', ''))

# === FUNCIONES PRINCIPALES (MANTIENEN ESTRUCTURA ORIGINAL) ===

def wordpress_create_post(client, params: Dict[str, Any]) -> Dict[str, Any]:
#                         ^^^^^^ ← CORREGIDO: sin Any
    """Crea un nuevo post en WordPress."""
    action_name = "wordpress_create_post"
    
    try:
        credentials = _get_wp_credentials(params)
        
        post_data = {
            'title': params.get('title', 'Nuevo Post'),
            'content': params.get('content', ''),
            'status': params.get('status', 'draft'),
            'excerpt': params.get('excerpt', ''),
            'author': params.get('author_id'),
            'categories': params.get('categories', []),
            'tags': params.get('tags', []),
            'featured_media': params.get('featured_media'),
            'meta': params.get('meta', {}),
            'slug': params.get('slug')
        }
        
        # Filtrar valores None
        post_data = {k: v for k, v in post_data.items() if v is not None}
        
        response = _make_wp_rest_request('POST', 'posts', params, data=post_data)
        
        return {
            "status": "success",
            "data": response,
            "action": action_name,
            "post_id": response.get('id'),
            "site_url": credentials.get('site_url'),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return _handle_wp_api_error(e, action_name, params.get('site_url', ''))

def wordpress_update_post(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """Actualiza un post existente en WordPress."""
    action_name = "wordpress_update_post"
    
    try:
        post_id = params.get('post_id')
        if not post_id:
            raise ValueError("post_id es requerido")
        
        update_data = {}
        updatable_fields = ['title', 'content', 'status', 'excerpt', 'categories', 'tags', 'featured_media', 'meta', 'slug']
        
        for field in updatable_fields:
            if field in params:
                update_data[field] = params[field]
        
        if not update_data:
            raise ValueError("No hay datos para actualizar")
        
        response = _make_wp_rest_request('POST', f'posts/{post_id}', params, data=update_data)
        
        return {
            "status": "success",
            "data": response,
            "action": action_name,
            "post_id": post_id,
            "updated_fields": list(update_data.keys()),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return _handle_wp_api_error(e, action_name, params.get('site_url', ''))

def wordpress_delete_post(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """Elimina un post de WordPress."""
    action_name = "wordpress_delete_post"
    
    try:
        post_id = params.get('post_id')
        if not post_id:
            raise ValueError("post_id es requerido")
        
        force = params.get('force_delete', False)
        query_params = {'force': force} if force else {}
        
        response = _make_wp_rest_request('DELETE', f'posts/{post_id}', params, query_params=query_params)
        
        return {
            "status": "success",
            "data": response,
            "action": action_name,
            "post_id": post_id,
            "force_deleted": force,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return _handle_wp_api_error(e, action_name, params.get('site_url', ''))

def wordpress_get_posts(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """Obtiene posts de WordPress con filtros."""
    action_name = "wordpress_get_posts"
    
    try:
        query_params = {}
        
        # Parámetros de consulta estándar
        filter_params = {
            'per_page': params.get('per_page', 10),
            'page': params.get('page', 1),
            'search': params.get('search'),
            'author': params.get('author_id'),
            'categories': params.get('categories'),
            'tags': params.get('tags'),
            'status': params.get('status', 'publish'),
            'orderby': params.get('orderby', 'date'),
            'order': params.get('order', 'desc'),
            'before': params.get('before'),
            'after': params.get('after')
        }
        
        # Filtrar valores None
        query_params = {k: v for k, v in filter_params.items() if v is not None}
        
        response = _make_wp_rest_request('GET', 'posts', params, query_params=query_params)
        
        return {
            "status": "success",
            "data": response,
            "action": action_name,
            "total_posts": len(response) if isinstance(response, list) else 1,
            "query_params": query_params,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return _handle_wp_api_error(e, action_name, params.get('site_url', ''))

def wordpress_get_post(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """Obtiene un post específico de WordPress."""
    action_name = "wordpress_get_post"
    
    try:
        post_id = params.get('post_id')
        if not post_id:
            raise ValueError("post_id es requerido")
        
        response = _make_wp_rest_request('GET', f'posts/{post_id}', params)
        
        return {
            "status": "success",
            "data": response,
            "action": action_name,
            "post_id": post_id,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return _handle_wp_api_error(e, action_name, params.get('site_url', ''))

def wordpress_create_page(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """Crea una nueva página en WordPress."""
    action_name = "wordpress_create_page"
    
    try:
        page_data = {
            'title': params.get('title', 'Nueva Página'),
            'content': params.get('content', ''),
            'status': params.get('status', 'draft'),
            'excerpt': params.get('excerpt', ''),
            'author': params.get('author_id'),
            'parent': params.get('parent_id'),
            'menu_order': params.get('menu_order', 0),
            'template': params.get('template'),
            'meta': params.get('meta', {}),
            'slug': params.get('slug')
        }
        
        # Filtrar valores None
        page_data = {k: v for k, v in page_data.items() if v is not None}
        
        response = _make_wp_rest_request('POST', 'pages', params, data=page_data)
        
        return {
            "status": "success",
            "data": response,
            "action": action_name,
            "page_id": response.get('id'),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return _handle_wp_api_error(e, action_name, params.get('site_url', ''))

def wordpress_get_pages(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """Obtiene páginas de WordPress."""
    action_name = "wordpress_get_pages"
    
    try:
        query_params = {
            'per_page': params.get('per_page', 10),
            'page': params.get('page', 1),
            'search': params.get('search'),
            'parent': params.get('parent_id'),
            'status': params.get('status', 'publish'),
            'orderby': params.get('orderby', 'menu_order'),
            'order': params.get('order', 'asc')
        }
        
        # Filtrar valores None
        query_params = {k: v for k, v in query_params.items() if v is not None}
        
        response = _make_wp_rest_request('GET', 'pages', params, query_params=query_params)
        
        return {
            "status": "success",
            "data": response,
            "action": action_name,
            "total_pages": len(response) if isinstance(response, list) else 1,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return _handle_wp_api_error(e, action_name, params.get('site_url', ''))

def wordpress_create_user(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """Crea un nuevo usuario en WordPress."""
    action_name = "wordpress_create_user"
    
    try:
        user_data = {
            'username': params.get('username'),
            'email': params.get('email'),
            'password': params.get('password'),
            'name': params.get('name', ''),
            'first_name': params.get('first_name', ''),
            'last_name': params.get('last_name', ''),
            'nickname': params.get('nickname', ''),
            'description': params.get('description', ''),
            'roles': params.get('roles', ['subscriber']),
            'meta': params.get('meta', {})
        }
        
        # Validar campos requeridos
        required_fields = ['username', 'email', 'password']
        for field in required_fields:
            if not user_data.get(field):
                raise ValueError(f"Campo requerido: {field}")
        
        # Filtrar valores None
        user_data = {k: v for k, v in user_data.items() if v is not None}
        
        response = _make_wp_rest_request('POST', 'users', params, data=user_data)
        
        return {
            "status": "success",
            "data": response,
            "action": action_name,
            "user_id": response.get('id'),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return _handle_wp_api_error(e, action_name, params.get('site_url', ''))

def wordpress_get_users(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """Obtiene usuarios de WordPress."""
    action_name = "wordpress_get_users"
    
    try:
        query_params = {
            'per_page': params.get('per_page', 10),
            'page': params.get('page', 1),
            'search': params.get('search'),
            'roles': params.get('roles'),
            'orderby': params.get('orderby', 'name'),
            'order': params.get('order', 'asc')
        }
        
        # Filtrar valores None
        query_params = {k: v for k, v in query_params.items() if v is not None}
        
        response = _make_wp_rest_request('GET', 'users', params, query_params=query_params)
        
        return {
            "status": "success",
            "data": response,
            "action": action_name,
            "total_users": len(response) if isinstance(response, list) else 1,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return _handle_wp_api_error(e, action_name, params.get('site_url', ''))

def wordpress_upload_media(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """Sube un archivo de media a WordPress."""
    action_name = "wordpress_upload_media"
    
    try:
        file_path = params.get('file_path')
        file_data = params.get('file_data')
        filename = params.get('filename')
        
        if not file_path and not file_data:
            raise ValueError("Se requiere file_path o file_data")
        
        credentials = _get_wp_credentials(params)
        site_url = credentials['site_url'].rstrip('/')
        upload_url = f"{site_url}/wp-json/wp/v2/media"
        
        # Usar autenticación moderna
        headers = _get_wp_auth_headers(credentials)
        # Remover Content-Type para multipart/form-data
        headers.pop('Content-Type', None)
        
        if file_path:
            with open(file_path, 'rb') as f:
                files = {'file': (filename or os.path.basename(file_path), f)}
                response = requests.post(upload_url, headers=headers, files=files, timeout=60)
        else:
            files = {'file': (filename or 'upload', file_data)}
            response = requests.post(upload_url, headers=headers, files=files, timeout=60)
        
        response.raise_for_status()
        result = response.json()
        
        return {
            "status": "success",
            "data": result,
            "action": action_name,
            "media_id": result.get('id'),
            "media_url": result.get('source_url'),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return _handle_wp_api_error(e, action_name, params.get('site_url', ''))

def wordpress_get_categories(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """Obtiene categorías de WordPress."""
    action_name = "wordpress_get_categories"
    
    try:
        query_params = {
            'per_page': params.get('per_page', 100),
            'page': params.get('page', 1),
            'search': params.get('search'),
            'parent': params.get('parent_id'),
            'orderby': params.get('orderby', 'name'),
            'order': params.get('order', 'asc'),
            'hide_empty': params.get('hide_empty', False)
        }
        
        # Filtrar valores None
        query_params = {k: v for k, v in query_params.items() if v is not None}
        
        response = _make_wp_rest_request('GET', 'categories', params, query_params=query_params)
        
        return {
            "status": "success",
            "data": response,
            "action": action_name,
            "total_categories": len(response) if isinstance(response, list) else 1,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return _handle_wp_api_error(e, action_name, params.get('site_url', ''))

def wordpress_create_category(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """Crea una nueva categoría en WordPress."""
    action_name = "wordpress_create_category"
    
    try:
        category_data = {
            'name': params.get('name'),
            'description': params.get('description', ''),
            'parent': params.get('parent_id'),
            'slug': params.get('slug')
        }
        
        if not category_data.get('name'):
            raise ValueError("Nombre de categoría es requerido")
        
        # Filtrar valores None
        category_data = {k: v for k, v in category_data.items() if v is not None}
        
        response = _make_wp_rest_request('POST', 'categories', params, data=category_data)
        
        return {
            "status": "success",
            "data": response,
            "action": action_name,
            "category_id": response.get('id'),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return _handle_wp_api_error(e, action_name, params.get('site_url', ''))

def wordpress_get_tags(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """Obtiene tags de WordPress."""
    action_name = "wordpress_get_tags"
    
    try:
        query_params = {
            'per_page': params.get('per_page', 100),
            'page': params.get('page', 1),
            'search': params.get('search'),
            'orderby': params.get('orderby', 'name'),
            'order': params.get('order', 'asc'),
            'hide_empty': params.get('hide_empty', False)
        }
        
        # Filtrar valores None
        query_params = {k: v for k, v in query_params.items() if v is not None}
        
        response = _make_wp_rest_request('GET', 'tags', params, query_params=query_params)
        
        return {
            "status": "success",
            "data": response,
            "action": action_name,
            "total_tags": len(response) if isinstance(response, list) else 1,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return _handle_wp_api_error(e, action_name, params.get('site_url', ''))

def wordpress_backup_content(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """Realiza un backup de contenido de WordPress."""
    action_name = "wordpress_backup_content"
    
    try:
        backup_types = params.get('backup_types', ['posts', 'pages', 'users'])
        backup_data = {}
        
        for backup_type in backup_types:
            if backup_type == 'posts':
                posts_result = wordpress_get_posts(client, {**params, 'per_page': 100})
                if posts_result['status'] == 'success':
                    backup_data['posts'] = posts_result['data']
            
            elif backup_type == 'pages':
                pages_result = wordpress_get_pages(client, {**params, 'per_page': 100})
                if pages_result['status'] == 'success':
                    backup_data['pages'] = pages_result['data']
            
            elif backup_type == 'users':
                users_result = wordpress_get_users(client, {**params, 'per_page': 100})
                if users_result['status'] == 'success':
                    backup_data['users'] = users_result['data']
            
            elif backup_type == 'categories':
                categories_result = wordpress_get_categories(client, {**params, 'per_page': 100})
                if categories_result['status'] == 'success':
                    backup_data['categories'] = categories_result['data']
        
        # Guardar backup en archivo si se especifica
        if params.get('save_to_file'):
            backup_filename = f"wp_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            backup_path = params.get('backup_path', '/tmp/') + backup_filename
            
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
            
            backup_data['backup_file'] = backup_path
        
        return {
            "status": "success",
            "data": backup_data,
            "action": action_name,
            "backup_types": backup_types,
            "total_items": sum(len(v) if isinstance(v, list) else 1 for k, v in backup_data.items() if k != 'backup_file'),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return _handle_wp_api_error(e, action_name, params.get('site_url', ''))

# === FUNCIONES DE WOOCOMMERCE (OPTIMIZADAS) ===

def woocommerce_create_product(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """Crea un nuevo producto en WooCommerce."""
    action_name = "woocommerce_create_product"
    
    try:
        product_data = {
            'name': params.get('name'),
            'type': params.get('type', 'simple'),
            'status': params.get('status', 'publish'),
            'description': params.get('description', ''),
            'short_description': params.get('short_description', ''),
            'sku': params.get('sku'),
            'regular_price': params.get('regular_price'),
            'sale_price': params.get('sale_price'),
            'manage_stock': params.get('manage_stock', False),
            'stock_quantity': params.get('stock_quantity'),
            'categories': params.get('categories', []),
            'tags': params.get('tags', []),
            'images': params.get('images', []),
            'attributes': params.get('attributes', []),
            'weight': params.get('weight'),
            'dimensions': params.get('dimensions', {}),
            'meta_data': params.get('meta_data', [])
        }
        
        if not product_data.get('name'):
            raise ValueError("Nombre del producto es requerido")
        
        # Filtrar valores None
        product_data = {k: v for k, v in product_data.items() if v is not None}
        
        response = _make_wc_request('POST', 'products', params, data=product_data)
        
        return {
            "status": "success",
            "data": response,
            "action": action_name,
            "product_id": response.get('id'),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return _handle_wp_api_error(e, action_name, params.get('site_url', ''))

def woocommerce_get_products(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """Obtiene productos de WooCommerce."""
    action_name = "woocommerce_get_products"
    
    try:
        query_params = {
            'per_page': params.get('per_page', 10),
            'page': params.get('page', 1),
            'search': params.get('search'),
            'category': params.get('category_id'),
            'tag': params.get('tag_id'),
            'type': params.get('type'),
            'status': params.get('status', 'publish'),
            'featured': params.get('featured'),
            'on_sale': params.get('on_sale'),
            'min_price': params.get('min_price'),
            'max_price': params.get('max_price'),
            'orderby': params.get('orderby', 'date'),
            'order': params.get('order', 'desc')
        }
        
        # Filtrar valores None
        query_params = {k: v for k, v in query_params.items() if v is not None}
        
        response = _make_wc_request('GET', 'products', params, query_params=query_params)
        
        return {
            "status": "success",
            "data": response,
            "action": action_name,
            "total_products": len(response) if isinstance(response, list) else 1,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return _handle_wp_api_error(e, action_name, params.get('site_url', ''))

def woocommerce_update_product(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """Actualiza un producto en WooCommerce."""
    action_name = "woocommerce_update_product"
    
    try:
        product_id = params.get('product_id')
        if not product_id:
            raise ValueError("product_id es requerido")
        
        update_data = {}
        updatable_fields = [
            'name', 'description', 'short_description', 'sku', 'regular_price', 
            'sale_price', 'stock_quantity', 'manage_stock', 'status', 'categories',
            'tags', 'images', 'attributes', 'weight', 'dimensions', 'meta_data'
        ]
        
        for field in updatable_fields:
            if field in params:
                update_data[field] = params[field]
        
        if not update_data:
            raise ValueError("No hay datos para actualizar")
        
        response = _make_wc_request('PUT', f'products/{product_id}', params, data=update_data)
        
        return {
            "status": "success",
            "data": response,
            "action": action_name,
            "product_id": product_id,
            "updated_fields": list(update_data.keys()),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return _handle_wp_api_error(e, action_name, params.get('site_url', ''))

def woocommerce_get_orders(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """Obtiene órdenes de WooCommerce."""
    action_name = "woocommerce_get_orders"
    
    try:
        query_params = {
            'per_page': params.get('per_page', 10),
            'page': params.get('page', 1),
            'search': params.get('search'),
            'customer': params.get('customer_id'),
            'status': params.get('status'),
            'after': params.get('after'),
            'before': params.get('before'),
            'orderby': params.get('orderby', 'date'),
            'order': params.get('order', 'desc')
        }
        
        # Filtrar valores None
        query_params = {k: v for k, v in query_params.items() if v is not None}
        
        response = _make_wc_request('GET', 'orders', params, query_params=query_params)
        
        return {
            "status": "success",
            "data": response,
            "action": action_name,
            "total_orders": len(response) if isinstance(response, list) else 1,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return _handle_wp_api_error(e, action_name, params.get('site_url', ''))

def woocommerce_create_order(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """Crea una nueva orden en WooCommerce."""
    action_name = "woocommerce_create_order"
    
    try:
        order_data = {
            'status': params.get('status', 'pending'),
            'customer_id': params.get('customer_id', 0),
            'billing': params.get('billing', {}),
            'shipping': params.get('shipping', {}),
            'line_items': params.get('line_items', []),
            'shipping_lines': params.get('shipping_lines', []),
            'fee_lines': params.get('fee_lines', []),
            'coupon_lines': params.get('coupon_lines', []),
            'payment_method': params.get('payment_method', ''),
            'payment_method_title': params.get('payment_method_title', ''),
            'set_paid': params.get('set_paid', False),
            'meta_data': params.get('meta_data', [])
        }
        
        if not order_data.get('line_items'):
            raise ValueError("line_items es requerido para crear una orden")
        
        # Filtrar valores None y vacíos
        order_data = {k: v for k, v in order_data.items() if v is not None and v != {}}
        
        response = _make_wc_request('POST', 'orders', params, data=order_data)
        
        return {
            "status": "success",
            "data": response,
            "action": action_name,
            "order_id": response.get('id'),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return _handle_wp_api_error(e, action_name, params.get('site_url', ''))

def woocommerce_update_order_status(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """Actualiza el estado de una orden en WooCommerce."""
    action_name = "woocommerce_update_order_status"
    
    try:
        order_id = params.get('order_id')
        status = params.get('status')
        
        if not order_id:
            raise ValueError("order_id es requerido")
        
        if not status:
            raise ValueError("status es requerido")
        
        update_data = {
            'status': status
        }
        
        # Agregar nota si se proporciona
        if params.get('note'):
            update_data['customer_note'] = params['note']
        
        response = _make_wc_request('PUT', f'orders/{order_id}', params, data=update_data)
        
        return {
            "status": "success",
            "data": response,
            "action": action_name,
            "order_id": order_id,
            "new_status": status,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return _handle_wp_api_error(e, action_name, params.get('site_url', ''))

def woocommerce_get_customers(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """Obtiene clientes de WooCommerce."""
    action_name = "woocommerce_get_customers"
    
    try:
        query_params = {
            'per_page': params.get('per_page', 10),
            'page': params.get('page', 1),
            'search': params.get('search'),
            'email': params.get('email'),
            'role': params.get('role'),
            'orderby': params.get('orderby', 'registered_date'),
            'order': params.get('order', 'desc')
        }
        
        # Filtrar valores None
        query_params = {k: v for k, v in query_params.items() if v is not None}
        
        response = _make_wc_request('GET', 'customers', params, query_params=query_params)
        
        return {
            "status": "success",
            "data": response,
            "action": action_name,
            "total_customers": len(response) if isinstance(response, list) else 1,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return _handle_wp_api_error(e, action_name, params.get('site_url', ''))

def woocommerce_create_customer(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """Crea un nuevo cliente en WooCommerce."""
    action_name = "woocommerce_create_customer"
    
    try:
        customer_data = {
            'email': params.get('email'),
            'username': params.get('username'),
            'password': params.get('password'),
            'first_name': params.get('first_name', ''),
            'last_name': params.get('last_name', ''),
            'billing': params.get('billing', {}),
            'shipping': params.get('shipping', {}),
            'meta_data': params.get('meta_data', [])
        }
        
        if not customer_data.get('email'):
            raise ValueError("Email del cliente es requerido")
        
        # Filtrar valores None y vacíos
        customer_data = {k: v for k, v in customer_data.items() if v is not None and v != {}}
        
        response = _make_wc_request('POST', 'customers', params, data=customer_data)
        
        return {
            "status": "success",
            "data": response,
            "action": action_name,
            "customer_id": response.get('id'),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return _handle_wp_api_error(e, action_name, params.get('site_url', ''))

def woocommerce_get_orders_by_customer(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """Obtiene pedidos de un cliente específico."""
    action_name = "woocommerce_get_orders_by_customer"
    
    try:
        customer_id = params.get("customer_id")
        if not customer_id:
            raise ValueError("Se requiere 'customer_id'")
        
        query_params = {
            'customer': customer_id,
            'per_page': params.get('per_page', 10),
            'page': params.get('page', 1),
            'status': params.get('status'),
            'orderby': params.get('orderby', 'date'),
            'order': params.get('order', 'desc')
        }
        
        # Filtrar valores None
        query_params = {k: v for k, v in query_params.items() if v is not None}
        
        response = _make_wc_request('GET', 'orders', params, query_params=query_params)
        
        return {
            "status": "success",
            "data": response,
            "action": action_name,
            "customer_id": customer_id,
            "total_orders": len(response) if isinstance(response, list) else 1,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return _handle_wp_api_error(e, action_name, params.get('site_url', ''))

def woocommerce_get_product_categories(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """Obtiene categorías de productos de WooCommerce."""
    action_name = "woocommerce_get_product_categories"
    
    try:
        query_params = {
            'per_page': params.get('per_page', 100),
            'page': params.get('page', 1),
            'search': params.get('search'),
            'parent': params.get('parent_id'),
            'orderby': params.get('orderby', 'name'),
            'order': params.get('order', 'asc'),
            'hide_empty': params.get('hide_empty', False)
        }
        
        # Filtrar valores None
        query_params = {k: v for k, v in query_params.items() if v is not None}
        
        response = _make_wc_request('GET', 'products/categories', params, query_params=query_params)
        
        return {
            "status": "success",
            "data": response,
            "action": action_name,
            "total_categories": len(response) if isinstance(response, list) else 1,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return _handle_wp_api_error(e, action_name, params.get('site_url', ''))

def woocommerce_get_reports(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """Obtiene reportes de WooCommerce."""
    action_name = "woocommerce_get_reports"
    
    try:
        report_type = params.get('report_type', 'sales')
        
        valid_reports = ['sales', 'top_sellers', 'customers', 'orders']
        if report_type not in valid_reports:
            raise ValueError(f"Tipo de reporte inválido. Debe ser uno de: {valid_reports}")
        
        query_params = {
            'period': params.get('period', 'week'),
            'date_min': params.get('date_min'),
            'date_max': params.get('date_max')
        }
        
        # Filtrar valores None
        query_params = {k: v for k, v in query_params.items() if v is not None}
        
        response = _make_wc_request('GET', f'reports/{report_type}', params, query_params=query_params)
        
        return {
            "status": "success",
            "data": response,
            "action": action_name,
            "report_type": report_type,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return _handle_wp_api_error(e, action_name, params.get('site_url', ''))