# app/actions/wordpress_actions.py
import logging
import requests
import mimetypes
import json
from typing import Dict, Any, Optional, List

from app.core.config import settings

logger = logging.getLogger(__name__)

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

def _make_wp_rest_request(method: str, endpoint: str, params: Dict[str, Any], json_data: Optional[Dict[str, Any]] = None, query_params: Optional[Dict[str, Any]] = None, extra_headers: Optional[Dict[str, str]] = None) -> Any:
    """Realiza una solicitud autenticada a la REST API de WordPress/WooCommerce."""
    token = _get_wp_jwt_token(params)
    wp_url = params.get("wp_url")
    if not wp_url:
        raise ValueError("El parámetro 'wp_url' es requerido.")

    full_url = f"{wp_url.rstrip('/')}/wp-json/{endpoint}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    if extra_headers:
        headers.update(extra_headers)

    response = requests.request(method, full_url, headers=headers, json=json_data, params=query_params, timeout=settings.DEFAULT_API_TIMEOUT)
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
        response = _make_wp_rest_request("POST", "wp/v2/posts", params, json_data=post_data)
        return {"status": "success", "data": response}
    except Exception as e:
        return _handle_wp_api_error(e, action_name)

def wordpress_get_post_by_slug(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "wordpress_get_post_by_slug"
    try:
        slug = params.get("slug")
        if not slug: raise ValueError("Se requiere 'slug'.")
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
        if not category_name: raise ValueError("Se requiere 'category_name'.")
        # Primero, encontrar el ID de la categoría por su nombre
        cats_resp = _make_wp_rest_request("GET", "wp/v2/categories", params, query_params={"search": category_name})
        if not cats_resp:
            return {"status": "error", "message": f"Categoría '{category_name}' no encontrada.", "http_status": 404}
        category_id = cats_resp[0]['id']
        # Luego, listar los posts de esa categoría
        posts_resp = _make_wp_rest_request("GET", "wp/v2/posts", params, query_params={"categories": category_id})
        return {"status": "success", "data": posts_resp}
    except Exception as e:
        return _handle_wp_api_error(e, action_name)

def wordpress_bulk_update_posts(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    # La REST API no soporta un bulk update nativo para posts de la misma forma que XML-RPC.
    # Se debe iterar y hacer llamadas individuales.
    action_name = "wordpress_bulk_update_posts"
    logger.warning(f"{action_name} se ejecutará como una serie de llamadas individuales a la API REST.")
    try:
        posts_data = params.get("posts", [])
        if not posts_data: raise ValueError("Se requiere una lista de 'posts' para actualizar.")
        results = []
        for post_data in posts_data:
            post_id = post_data.get("id")
            if not post_id: continue
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
    action_name = "wordpress_get_post_revisions"
    try:
        post_id = params.get("post_id")
        if not post_id: raise ValueError("Se requiere 'post_id'.")
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
        if not image_url or not title: raise ValueError("Se requieren 'image_url' y 'title'.")
        
        image_response = requests.get(image_url, timeout=settings.DEFAULT_API_TIMEOUT)
        image_response.raise_for_status()
        image_bytes = image_response.content
        content_type = image_response.headers.get('content-type', mimetypes.guess_type(image_url)[0])
        filename = title + "." + content_type.split('/')[-1]

        headers = {"Content-Disposition": f"attachment; filename={filename}", "Content-Type": content_type}
        response = _make_wp_rest_request("POST", "wp/v2/media", params, json_data=image_bytes, extra_headers=headers)
        return {"status": "success", "data": response}
    except Exception as e:
        return _handle_wp_api_error(e, action_name)

def wordpress_assign_featured_image_to_post(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "wordpress_assign_featured_image_to_post"
    try:
        post_id = params.get("post_id")
        media_id = params.get("media_id")
        if not post_id or not media_id: raise ValueError("Se requieren 'post_id' y 'media_id'.")
        response = _make_wp_rest_request("PUT", f"wp/v2/posts/{post_id}", params, json_data={"featured_media": media_id})
        return {"status": "success", "data": response}
    except Exception as e:
        return _handle_wp_api_error(e, action_name)

# --- ACCIONES DE WORDPRESS (COMENTARIOS) ---

def wordpress_get_comments_for_post(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "wordpress_get_comments_for_post"
    try:
        post_id = params.get("post_id")
        if not post_id: raise ValueError("Se requiere 'post_id'.")
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

# --- ACCIONES DE WOOCOMMERCE ---

def woocommerce_get_product_by_sku(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "woocommerce_get_product_by_sku"
    try:
        sku = params.get("sku")
        if not sku: raise ValueError("Se requiere 'sku'.")
        response = _make_wp_rest_request("GET", "wc/v3/products", params, query_params={"sku": sku})
        if not response:
            return {"status": "error", "message": f"No se encontró producto con SKU '{sku}'.", "http_status": 404}
        return {"status": "success", "data": response[0]}
    except Exception as e:
        return _handle_wp_api_error(e, action_name)

def woocommerce_create_product(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "woocommerce_create_product"
    try:
        product_data = params.get("product_data")
        if not product_data or not product_data.get("name"):
            raise ValueError("Se requiere 'product_data' con al menos un 'name'.")
        response = _make_wp_rest_request("POST", "wc/v3/products", params, json_data=product_data)
        return {"status": "success", "data": response}
    except Exception as e:
        return _handle_wp_api_error(e, action_name)

def woocommerce_bulk_update_prices(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "woocommerce_bulk_update_prices"
    try:
        products_data = params.get("products", [])
        if not products_data: raise ValueError("Se requiere una lista de 'products' para actualizar.")
        update_payload = {"update": []}
        for p in products_data:
            if "id" in p and ("regular_price" in p or "sale_price" in p):
                update_payload["update"].append(p)
        response = _make_wp_rest_request("POST", "wc/v3/products/batch", params, json_data=update_payload)
        return {"status": "success", "data": response}
    except Exception as e:
        return _handle_wp_api_error(e, action_name)

def woocommerce_batch_update_products(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "woocommerce_batch_update_products"
    try:
        batch_data = params.get("batch_data")
        if not batch_data: raise ValueError("Se requiere 'batch_data' (ej. {'update': [...]}).")
        response = _make_wp_rest_request("POST", "wc/v3/products/batch", params, json_data=batch_data)
        return {"status": "success", "data": response}
    except Exception as e:
        return _handle_wp_api_error(e, action_name)

def woocommerce_search_products(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "woocommerce_search_products"
    try:
        search_params = params.get("search_params", {})
        response = _make_wp_rest_request("GET", "wc/v3/products", params, query_params=search_params)
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
        response = _make_wp_rest_request("PUT", f"wc/v3/orders/{order_id}", params, json_data={"status": new_status})
        return {"status": "success", "data": response}
    except Exception as e:
        return _handle_wp_api_error(e, action_name)

def woocommerce_get_customer_orders(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "woocommerce_get_customer_orders"
    try:
        customer_email = params.get("customer_email")
        if not customer_email: raise ValueError("Se requiere 'customer_email'.")
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
