# app/actions/wordpress_actions.py
import logging
import requests
import mimetypes
import json
from typing import Dict, Any, Optional, List, TypedDict, Literal, Union

from app.core.config import settings

logger = logging.getLogger(__name__)

# --- CONSTANTES Y TIPOS ---

# Definición de tipos
class WordPressResponse(TypedDict):
    status: str
    data: Dict[str, Any]
    message: Optional[str]
    http_status: Optional[int]
    details: Optional[Any]

class WooCommerceProduct(TypedDict):
    id: int
    name: str
    regular_price: str
    sale_price: Optional[str]
    status: Literal['draft', 'pending', 'private', 'publish']

# Constantes
WP_POST_STATUS = {
    'PUBLISH': 'publish',
    'DRAFT': 'draft',
    'PRIVATE': 'private',
    'PENDING': 'pending',
    'FUTURE': 'future'
}

WC_ORDER_STATUS = {
    'PENDING': 'pending',
    'PROCESSING': 'processing',
    'ON_HOLD': 'on-hold',
    'COMPLETED': 'completed',
    'CANCELLED': 'cancelled',
    'REFUNDED': 'refunded',
    'FAILED': 'failed'
}

ALLOWED_MIME_TYPES = {
    'IMAGE': ['image/jpeg', 'image/png', 'image/gif', 'image/webp'],
    'DOCUMENT': ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
}

WC_ERRORS = {
    'PRODUCT_NOT_FOUND': 'product_not_found',
    'INVALID_PRICE': 'invalid_price',
    'INVALID_STATUS': 'invalid_status',
    'ORDER_NOT_FOUND': 'order_not_found'
}

# --- HELPERS DE CONEXIÓN Y ERRORES PARA REST API ---

_jwt_token_cache: Optional[str] = None

def _get_wp_jwt_token(params: Dict[str, Any]) -> str:
    """Obtiene y cachea un token JWT para la sesión actual."""
    global _jwt_token_cache
    if _jwt_token_cache:
        logger.debug("Usando token JWT de WordPress cacheado para la solicitud.")
        return _jwt_token_cache

    wp_url = params.get("wp_url")
    username = params.get("wp_jwt_user")
    password = params.get("wp_jwt_pass")

    if not all([wp_url, username, password]):
        raise ValueError("Se requieren 'wp_url', 'wp_jwt_user' y 'wp_jwt_pass' para la autenticación JWT.")

    token_url = f"{wp_url.rstrip('/')}/wp-json/jwt-auth/v1/token"
    logger.info(f"Solicitando nuevo token JWT de WordPress desde: {token_url}")

    try:
        response = requests.post(
            token_url,
            json={"username": username, "password": password},
            timeout=settings.DEFAULT_API_TIMEOUT
        )
        response.raise_for_status()
        token_data = response.json()
        token = token_data.get("token")
        if not token:
            raise ValueError("La respuesta de autenticación JWT no contiene un token.")

        _jwt_token_cache = token
        logger.info("Nuevo token JWT de WordPress obtenido y cacheado exitosamente.")
        return token
    except requests.exceptions.HTTPError as http_err:
        error_body = http_err.response.text
        logger.error(f"Error de autenticación JWT ({http_err.response.status_code}): {error_body}")
        raise ValueError(f"Fallo la autenticación con WordPress (JWT). Verifique las credenciales y que el plugin JWT esté activo. Detalle: {error_body}") from http_err
    except Exception as e:
        logger.error(f"Error inesperado al obtener token JWT: {e}", exc_info=True)
        raise

def _make_wp_rest_request(method: str, endpoint: str, params: Dict[str, Any], json_data: Optional[Dict[str, Any]] = None, query_params: Optional[Dict[str, Any]] = None, extra_headers: Optional[Dict[str, str]] = None, data: Optional[bytes] = None) -> Any:
    """Realiza una solicitud autenticada a la REST API de WordPress/WooCommerce."""
    token = _get_wp_jwt_token(params)
    wp_url = params.get("wp_url")
    if not wp_url:
        raise ValueError("El parámetro 'wp_url' es requerido.")

    full_url = f"{wp_url.rstrip('/')}/wp-json/{endpoint}"
    headers = {
        "Authorization": f"Bearer {token}",
    }
    
    # Solo agregar Content-Type si no hay datos binarios
    if not data:
        headers["Content-Type"] = "application/json"
    
    if extra_headers:
        headers.update(extra_headers)

    # Usar data para bytes, json_data para JSON
    request_kwargs = {
        "method": method,
        "url": full_url,
        "headers": headers,
        "params": query_params,
        "timeout": settings.DEFAULT_API_TIMEOUT
    }
    
    if data:
        request_kwargs["data"] = data
    elif json_data:
        request_kwargs["json"] = json_data

    response = requests.request(**request_kwargs)
    response.raise_for_status()

    if response.status_code == 204:
        return {}

    return response.json()

def _handle_wp_api_error(e: Exception, action_name: str) -> Dict[str, Any]:
    """Maneja errores de la API REST de WordPress y WooCommerce."""
    logger.error(f"Error en WordPress/WooCommerce Action '{action_name}': {type(e).__name__} - {e}", exc_info=True)
    status_code = 500
    details = str(e)

    if isinstance(e, requests.exceptions.HTTPError) and e.response is not None:
        status_code = e.response.status_code
        try:
            details = e.response.json()
        except json.JSONDecodeError:
            details = e.response.text

    return {"status": "error", "action": action_name, "message": f"Error en API de WordPress: {str(e)}", "http_status": status_code, "details": details}

def _handle_wc_specific_error(response: requests.Response, action_name: str) -> Dict[str, Any]:
    """Maneja errores específicos de WooCommerce con mensajes más descriptivos."""
    try:
        error_data = response.json()
        error_code = error_data.get('code', '')
        if error_code in WC_ERRORS:
            return {
                "status": "error",
                "message": f"Error de WooCommerce: {error_code}",
                "http_status": response.status_code,
                "details": error_data
            }
        return _handle_wp_api_error(Exception(str(error_data)), action_name)
    except Exception:
        return _handle_wp_api_error(Exception(response.text), action_name)

# --- ACCIONES DE WORDPRESS (CORE) ---

def wordpress_create_post(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "wordpress_create_post"
    try:
        post_data = {
            "title": params.get("title"),
            "content": params.get("content"),
            "status": params.get("status", "publish"),
        }
        if not post_data["title"] or not post_data["content"]:
            raise ValueError("Se requieren 'title' y 'content'.")
        
        # Agregar categorías y tags si están presentes
        if params.get("categories"):
            post_data["categories"] = params["categories"]
        if params.get("tags"):
            post_data["tags"] = params["tags"]
            
        response = _make_wp_rest_request("POST", "wp/v2/posts", params, json_data=post_data)
        return {"status": "success", "data": response}
    except Exception as e:
        return _handle_wp_api_error(e, action_name)

def wordpress_get_post_by_slug(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "wordpress_get_post_by_slug"
    try:
        slug = params.get("slug")
        if not slug: 
            raise ValueError("Se requiere 'slug'.")
        response = _make_wp_rest_request("GET", "wp/v2/posts", params, query_params={"slug": slug})
        if not response:
            return {"status": "error", "message": f"No se encontró post con slug '{slug}'.", "http_status": 404}
        return {"status": "success", "data": response[0]}
    except Exception as e:
        return _handle_wp_api_error(e, action_name)

def wordpress_update_post_content(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "wordpress_update_post_content"
    try:
        post_id = params.get("post_id")
        new_content = params.get("new_content")
        if not post_id or new_content is None:
            raise ValueError("Se requieren 'post_id' y 'new_content'.")
        response = _make_wp_rest_request("PUT", f"wp/v2/posts/{post_id}", params, json_data={"content": new_content})
        return {"status": "success", "data": response}
    except Exception as e:
        return _handle_wp_api_error(e, action_name)

def wordpress_list_posts_by_category(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "wordpress_list_posts_by_category"
    try:
        category_name = params.get("category_name")
        page = params.get("page", 1)
        per_page = params.get("per_page", 20)
        
        if not category_name: 
            raise ValueError("Se requiere 'category_name'.")
        
        # Primero, encontrar el ID de la categoría por su nombre
        cats_resp = _make_wp_rest_request("GET", "wp/v2/categories", params, query_params={"search": category_name})
        if not cats_resp:
            return {"status": "error", "message": f"Categoría '{category_name}' no encontrada.", "http_status": 404}
        category_id = cats_resp[0]['id']
        
        # Luego, listar los posts de esa categoría con paginación
        query_params = {
            "categories": category_id,
            "page": page,
            "per_page": per_page
        }
        posts_resp = _make_wp_rest_request("GET", "wp/v2/posts", params, query_params=query_params)
        return {"status": "success", "data": posts_resp}
    except Exception as e:
        return _handle_wp_api_error(e, action_name)

def wordpress_bulk_update_posts(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Actualiza múltiples posts en WordPress de forma masiva."""
    action_name = "wordpress_bulk_update_posts"
    logger.warning(f"{action_name} se ejecutará como una serie de llamadas individuales a la API REST.")
    try:
        posts_data = params.get("posts", [])
        if not posts_data: 
            raise ValueError("Se requiere una lista de 'posts' para actualizar.")
        
        results = []
        for post_data in posts_data:
            post_id = post_data.get("id")
            if not post_id: 
                continue
            update_payload = {k: v for k, v in post_data.items() if k != "id"}
            try:
                response = _make_wp_rest_request("PUT", f"wp/v2/posts/{post_id}", params, json_data=update_payload)
                results.append({"id": post_id, "updated": True, "data": response})
            except Exception as e:
                results.append({"id": post_id, "updated": False, "error": str(e)})
        return {"status": "success", "data": results}
    except Exception as e:
        return _handle_wp_api_error(e, action_name)

def wordpress_get_post_revisions(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Obtiene el historial de revisiones de un post."""
    action_name = "wordpress_get_post_revisions"
    try:
        post_id = params.get("post_id")
        if not post_id: 
            raise ValueError("Se requiere 'post_id'.")
        response = _make_wp_rest_request("GET", f"wp/v2/posts/{post_id}/revisions", params)
        return {"status": "success", "data": response}
    except Exception as e:
        return _handle_wp_api_error(e, action_name)

# --- ACCIONES DE WORDPRESS (MEDIA) ---

def wordpress_upload_image_from_url(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "wordpress_upload_image_from_url"
    try:
        image_url = params.get("image_url")
        title = params.get("title")
        if not image_url or not title: 
            raise ValueError("Se requieren 'image_url' y 'title'.")
        
        # Descargar imagen
        image_response = requests.get(image_url, timeout=settings.DEFAULT_API_TIMEOUT)
        image_response.raise_for_status()
        
        # Validar tipo de archivo
        content_type = image_response.headers.get('content-type', mimetypes.guess_type(image_url)[0])
        if content_type not in ALLOWED_MIME_TYPES['IMAGE']:
            raise ValueError(f"Tipo de archivo no permitido: {content_type}")
        
        # Preparar headers para upload
        filename = f"{title}.{content_type.split('/')[-1]}"
        headers = {
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Type": content_type
        }
        
        response = _make_wp_rest_request("POST", "wp/v2/media", params, data=image_response.content, extra_headers=headers)
        return {"status": "success", "data": response}
    except Exception as e:
        return _handle_wp_api_error(e, action_name)

def wordpress_assign_featured_image_to_post(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "wordpress_assign_featured_image_to_post"
    try:
        post_id = params.get("post_id")
        media_id = params.get("media_id")
        if not post_id or not media_id: 
            raise ValueError("Se requieren 'post_id' y 'media_id'.")
        response = _make_wp_rest_request("PUT", f"wp/v2/posts/{post_id}", params, json_data={"featured_media": media_id})
        return {"status": "success", "data": response}
    except Exception as e:
        return _handle_wp_api_error(e, action_name)

# --- ACCIONES DE WORDPRESS (COMENTARIOS) ---

def wordpress_get_comments_for_post(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "wordpress_get_comments_for_post"
    try:
        post_id = params.get("post_id")
        if not post_id: 
            raise ValueError("Se requiere 'post_id'.")
        response = _make_wp_rest_request("GET", "wp/v2/comments", params, query_params={"post": post_id})
        return {"status": "success", "data": response}
    except Exception as e:
        return _handle_wp_api_error(e, action_name)

def wordpress_reply_to_comment(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "wordpress_reply_to_comment"
    try:
        post_id = params.get("post_id")
        parent_comment_id = params.get("parent_comment_id")
        content = params.get("content")
        if not all([post_id, parent_comment_id, content]):
            raise ValueError("Se requieren 'post_id', 'parent_comment_id' y 'content'.")
        
        comment_data = {"post": post_id, "parent": parent_comment_id, "content": content}
        response = _make_wp_rest_request("POST", "wp/v2/comments", params, json_data=comment_data)
        return {"status": "success", "data": response}
    except Exception as e:
        return _handle_wp_api_error(e, action_name)

# --- ACCIONES DE WOOCOMMERCE (PRODUCTOS) ---

def woocommerce_get_product_by_sku(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "woocommerce_get_product_by_sku"
    try:
        sku = params.get("sku")
        if not sku: 
            raise ValueError("Se requiere 'sku'.")
        response = _make_wp_rest_request("GET", "wc/v3/products", params, query_params={"sku": sku})
        if not response:
            return {"status": "error", "message": f"No se encontró producto con SKU '{sku}'.", "http_status": 404}
        return {"status": "success", "data": response[0]}
    except Exception as e:
        return _handle_wp_api_error(e, action_name)

def woocommerce_create_product(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Crea un nuevo producto en WooCommerce."""
    action_name = "woocommerce_create_product"
    try:
        # Validar si se pasa product_data o campos individuales
        if "product_data" in params:
            product_data = params["product_data"]
            if not product_data.get("name"):
                raise ValueError("Se requiere 'name' en product_data.")
        else:
            # Validación de campos requeridos
            if not params.get("name") or not params.get("regular_price"):
                raise ValueError("Se requieren 'name' y 'regular_price'.")
            
            # Validación de precio
            if not isinstance(params.get("regular_price"), (str, float, int)):
                raise ValueError("regular_price debe ser un número válido")
            
            # Validación de status
            if params.get("status") and params.get("status") not in WP_POST_STATUS.values():
                raise ValueError(f"status debe ser uno de: {', '.join(WP_POST_STATUS.values())}")
            
            product_data = {
                "name": params["name"],
                "regular_price": str(params["regular_price"]),
                "description": params.get("description", ""),
                "short_description": params.get("short_description", ""),
                "categories": params.get("categories", []),
                "images": params.get("images", []),
                "status": params.get("status", "publish")
            }
        
        response = _make_wp_rest_request("POST", "wc/v3/products", params, json_data=product_data)
        return {"status": "success", "data": response}
    except Exception as e:
        return _handle_wp_api_error(e, action_name)

def woocommerce_bulk_update_prices(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Actualiza precios de múltiples productos en WooCommerce."""
    action_name = "woocommerce_bulk_update_prices"
    try:
        products_data = params.get("products", [])
        if not products_data: 
            raise ValueError("Se requiere una lista de 'products' para actualizar.")
        
        # Preparar datos para batch update
        update_payload = {"update": []}
        for p in products_data:
            if "id" in p and ("regular_price" in p or "sale_price" in p):
                product_update = {"id": p["id"]}
                if "regular_price" in p:
                    product_update["regular_price"] = str(p["regular_price"])
                if "sale_price" in p:
                    product_update["sale_price"] = str(p["sale_price"])
                update_payload["update"].append(product_update)
        
        response = _make_wp_rest_request("POST", "wc/v3/products/batch", params, json_data=update_payload)
        return {"status": "success", "data": response}
    except Exception as e:
        return _handle_wp_api_error(e, action_name)

def woocommerce_batch_update_products(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Actualiza múltiples productos en una sola llamada a la API."""
    action_name = "woocommerce_batch_update_products"
    try:
        # Permitir tanto batch_data como products
        if "batch_data" in params:
            batch_data = params["batch_data"]
        elif "products" in params:
            products = params["products"]
            if not products:
                raise ValueError("Se requiere lista de productos para actualizar")
            
            batch_data = {
                "update": [
                    {
                        "id": product["id"],
                        **{k:v for k,v in product.items() if k != "id"}
                    }
                    for product in products
                ]
            }
        else:
            raise ValueError("Se requiere 'batch_data' o 'products'.")
        
        response = _make_wp_rest_request("POST", "wc/v3/products/batch", params, json_data=batch_data)
        return {"status": "success", "data": response}
    except Exception as e:
        return _handle_wp_api_error(e, action_name)

def woocommerce_search_products(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Búsqueda avanzada de productos con múltiples filtros."""
    action_name = "woocommerce_search_products"
    try:
        # Permitir tanto search_params como parámetros individuales
        if "search_params" in params:
            search_params = params["search_params"]
        else:
            search_params = {
                "search": params.get("search", ""),
                "category": params.get("category", ""),
                "tag": params.get("tag", ""),
                "status": params.get("status", "publish"),
                "sku": params.get("sku", ""),
                "min_price": params.get("min_price", ""),
                "max_price": params.get("max_price", ""),
                "page": params.get("page", 1),
                "per_page": params.get("per_page", 20)
            }
        
        # Filtrar parámetros vacíos
        clean_params = {k: v for k, v in search_params.items() if v}
        
        response = _make_wp_rest_request("GET", "wc/v3/products", params, query_params=clean_params)
        return {"status": "success", "data": response}
    except Exception as e:
        return _handle_wp_api_error(e, action_name)

# --- ACCIONES DE WOOCOMMERCE (ÓRDENES) ---

def woocommerce_update_order_status(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "woocommerce_update_order_status"
    try:
        order_id = params.get("order_id")
        new_status = params.get("new_status")
        if not order_id or not new_status:
            raise ValueError("Se requieren 'order_id' y 'new_status'.")
        
        # Validar status
        if new_status not in WC_ORDER_STATUS.values():
            raise ValueError(f"new_status debe ser uno de: {', '.join(WC_ORDER_STATUS.values())}")
            
        response = _make_wp_rest_request("PUT", f"wc/v3/orders/{order_id}", params, json_data={"status": new_status})
        return {"status": "success", "data": response}
    except Exception as e:
        return _handle_wp_api_error(e, action_name)

def woocommerce_get_customer_orders(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "woocommerce_get_customer_orders"
    try:
        customer_email = params.get("customer_email")
        if not customer_email: 
            raise ValueError("Se requiere 'customer_email'.")
        
        # Primero, buscar el ID del cliente por email
        customers_resp = _make_wp_rest_request("GET", "wc/v3/customers", params, query_params={"email": customer_email})
        if not customers_resp:
            return {"status": "error", "message": f"Cliente con email '{customer_email}' no encontrado.", "http_status": 404}
        customer_id = customers_resp[0]['id']
        
        # Luego, buscar órdenes por ID de cliente
        orders_resp = _make_wp_rest_request("GET", "wc/v3/orders", params, query_params={"customer": customer_id})
        return {"status": "success", "data": orders_resp}
    except Exception as e:
        return _handle_wp_api_error(e, action_name)