# app/actions/wordpress_actions.py
import logging
import requests
import mimetypes
from typing import Dict, Any, Optional, Union, List, TypedDict, Literal

from wordpress_xmlrpc import Client, WordPressPost
from wordpress_xmlrpc.methods import posts, media, comments, users
from wordpress_xmlrpc.compat import xmlrpc_client
from woocommerce import API as WooCommerceAPI

from app.core.config import settings

logger = logging.getLogger(__name__)

# --- HELPERS DE CONEXIÓN Y ERRORES ---

# Definición de tipos
class WordPressResponse(TypedDict):
    status: str
    data: Dict[str, Any]
    message: Optional[str]
    http_status: Optional[int]
    details: Optional[Any]

def _get_wp_client(params: Dict[str, Any]) -> Client:
    """Crea un cliente para la API XML-RPC de WordPress."""
    url = params.get("wp_url")
    username = params.get("wp_username")
    password = params.get("wp_password")
    if not all([url, username, password]):
        raise ValueError("Se requieren 'wp_url', 'wp_username' y 'wp_password' para las acciones de WordPress.")
    # Asegurarse de que la URL apunta al archivo xmlrpc.php
    if not url.endswith('xmlrpc.php'):
        url = url.rstrip('/') + '/xmlrpc.php'
    return Client(url, username, password)

def _get_woocommerce_api(params: Dict[str, Any]) -> WooCommerceAPI:
    """Crea un cliente para la API REST de WooCommerce."""
    url = params.get("wp_url")
    consumer_key = params.get("wc_consumer_key")
    consumer_secret = params.get("wc_consumer_secret")
    if not all([url, consumer_key, consumer_secret]):
        raise ValueError("Se requieren 'wp_url', 'wc_consumer_key' y 'wc_consumer_secret' para las acciones de WooCommerce.")
    
    return WooCommerceAPI(
        url=url,
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        version="wc/v3",
        timeout=settings.DEFAULT_API_TIMEOUT
    )

def _handle_wp_api_error(e: Exception, action_name: str) -> Dict[str, Any]:
    """Maneja errores de las APIs de WordPress y WooCommerce."""
    logger.error(f"Error en WordPress/WooCommerce Action '{action_name}': {type(e).__name__} - {e}", exc_info=True)
    status_code = 500
    message = str(e)
    
    if isinstance(e, xmlrpc_client.Fault):
        status_code = 400 # Generalmente un error de cliente
        message = f"Error XML-RPC {e.faultCode}: {e.faultString}"
    elif isinstance(e, requests.exceptions.HTTPError) and e.response is not None:
        status_code = e.response.status_code
        try:
            error_data = e.response.json()
            message = error_data.get("message", e.response.text)
        except Exception:
            message = e.response.text

    return {"status": "error", "action": action_name, "message": message, "http_status": status_code, "details": str(e)}

def _handle_wc_specific_error(response: requests.Response, action_name: str) -> WordPressResponse:
    """
    Maneja errores específicos de WooCommerce con mensajes más descriptivos.
    """
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

# --- ACCIONES DE WORDPRESS ---

class WooCommerceProduct(TypedDict):
    id: int
    name: str
    regular_price: str
    sale_price: Optional[str]
    status: Literal['draft', 'pending', 'private', 'publish']

WP_POST_STATUS = {
    'PUBLISH': 'publish',
    'DRAFT': 'draft',
    'PRIVATE': 'private',
    'PENDING': 'pending',
    'FUTURE': 'future'
}

ALLOWED_MIME_TYPES = {
    'IMAGE': ['image/jpeg', 'image/png', 'image/gif', 'image/webp'],
    'DOCUMENT': ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
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

WC_ERRORS = {
    'PRODUCT_NOT_FOUND': 'product_not_found',
    'INVALID_PRICE': 'invalid_price',
    'INVALID_STATUS': 'invalid_status',
    'ORDER_NOT_FOUND': 'order_not_found'
}

def wordpress_create_post(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "wordpress_create_post"
    try:
        wp_client = _get_wp_client(params)
        post = WordPressPost()
        post.title = params.get("title")
        post.content = params.get("content")
        if not post.title or not post.content:
            raise ValueError("Se requieren 'title' y 'content'.")

        post.terms_names = {
            'post_tag': params.get("tags", []),
            'category': params.get("categories", [])
        }
        post.post_status = params.get("status", "publish") # publish, draft, private
        
        post_id = wp_client.call(posts.NewPost(post))
        if not post_id:
            raise Exception("La creación del post no devolvió un ID.")
            
        return {"status": "success", "data": {"post_id": post_id, "title": post.title}}
    except Exception as e:
        return _handle_wp_api_error(e, action_name)

def wordpress_get_post_by_slug(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "wordpress_get_post_by_slug"
    try:
        wp_client = _get_wp_client(params)
        slug = params.get("slug")
        if not slug:
            raise ValueError("Se requiere 'slug'.")
        
        # GetPosts puede filtrar por varios criterios, 'post_name' (slug) es uno de ellos.
        post_list = wp_client.call(posts.GetPosts({'post_name': slug}))
        if not post_list:
            return {"status": "error", "message": f"No se encontró post con slug '{slug}'.", "http_status": 404}
        
        p = post_list[0]
        return {"status": "success", "data": {"id": p.id, "title": p.title, "slug": p.slug, "content": p.content}}
    except Exception as e:
        return _handle_wp_api_error(e, action_name)

def wordpress_update_post_content(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "wordpress_update_post_content"
    try:
        wp_client = _get_wp_client(params)
        post_id = params.get("post_id")
        new_content = params.get("new_content")
        if not post_id or new_content is None:
            raise ValueError("Se requieren 'post_id' y 'new_content'.")
        
        post = WordPressPost()
        post.content = new_content
        
        result = wp_client.call(posts.EditPost(post_id, post))
        return {"status": "success", "data": {"updated": result, "post_id": post_id}}
    except Exception as e:
        return _handle_wp_api_error(e, action_name)

def wordpress_list_posts_by_category(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "wordpress_list_posts_by_category"
    try:
        wp_client = _get_wp_client(params)
        category_name = params.get("category_name")
        page = params.get("page", 1)
        per_page = params.get("per_page", 20)
        
        if not category_name:
            raise ValueError("Se requiere 'category_name'.")
            
        post_list = wp_client.call(posts.GetPosts({
            'category': category_name,
            'number': per_page,
            'offset': (page - 1) * per_page
        }))
        
        result_data = [{"id": p.id, "title": p.title, "slug": p.slug} for p in post_list]
        return {"status": "success", "data": result_data}
    except Exception as e:
        return _handle_wp_api_error(e, action_name)

def wordpress_upload_image_from_url(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "wordpress_upload_image_from_url"
    try:
        wp_client = _get_wp_client(params)
        image_url = params.get("image_url")
        title = params.get("title")
        if not image_url or not title:
            raise ValueError("Se requieren 'image_url' y 'title'.")

        response = requests.get(image_url, timeout=settings.DEFAULT_API_TIMEOUT)
        response.raise_for_status()
        
        content_type = response.headers.get('content-type', mimetypes.guess_type(image_url)[0])
        if content_type not in ALLOWED_MIME_TYPES['IMAGE']:
            raise ValueError(f"Tipo de archivo no permitido: {content_type}")
        
        data = {
            'name': title,
            'type': content_type,
            'bits': xmlrpc_client.Binary(response.content)
        }

        upload_response = wp_client.call(media.UploadFile(data))
        return {"status": "success", "data": upload_response}
    except Exception as e:
        return _handle_wp_api_error(e, action_name)

def wordpress_assign_featured_image_to_post(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "wordpress_assign_featured_image_to_post"
    try:
        wp_client = _get_wp_client(params)
        post_id = params.get("post_id")
        media_id = params.get("media_id")
        if not post_id or not media_id:
            raise ValueError("Se requieren 'post_id' y 'media_id'.")
            
        post = WordPressPost()
        post.thumbnail = media_id
        
        result = wp_client.call(posts.EditPost(post_id, post))
        return {"status": "success", "data": {"updated": result, "post_id": post_id}}
    except Exception as e:
        return _handle_wp_api_error(e, action_name)

def wordpress_get_comments_for_post(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "wordpress_get_comments_for_post"
    try:
        wp_client = _get_wp_client(params)
        post_id = params.get("post_id")
        if not post_id:
            raise ValueError("Se requiere 'post_id'.")
        
        comment_list = wp_client.call(comments.GetComments({'post_id': post_id}))
        result_data = [{"id": c.id, "author": c.author, "content": c.content, "date_created": str(c.date_created)} for c in comment_list]
        return {"status": "success", "data": result_data}
    except Exception as e:
        return _handle_wp_api_error(e, action_name)

def wordpress_reply_to_comment(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "wordpress_reply_to_comment"
    try:
        wp_client = _get_wp_client(params)
        post_id = params.get("post_id")
        parent_comment_id = params.get("parent_comment_id")
        content = params.get("content")
        if not all([post_id, parent_comment_id, content]):
            raise ValueError("Se requieren 'post_id', 'parent_comment_id' y 'content'.")

        comment = comments.WordPressComment()
        comment.content = content
        comment.parent = parent_comment_id
        
        comment_id = wp_client.call(comments.NewComment(post_id, comment))
        return {"status": "success", "data": {"comment_id": comment_id}}
    except Exception as e:
        return _handle_wp_api_error(e, action_name)

def wordpress_create_user(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "wordpress_create_user"
    # Esta acción requiere permisos de administrador en WordPress.
    # La librería xmlrpc no tiene un método directo para crear usuarios.
    # Se podría hacer con una llamada XML-RPC personalizada si es necesario,
    # pero es una operación de alto riesgo y no estándar.
    logger.warning(f"La acción '{action_name}' no es soportada de forma estándar por la librería y es de alto riesgo.")
    return {"status": "not_implemented", "message": "La creación de usuarios vía XML-RPC no está implementada de forma estándar."}

def wordpress_bulk_update_posts(client: Any, params: Dict[str, Any]) -> WordPressResponse:
    """
    Actualiza múltiples posts en WordPress de forma masiva.
    
    Args:
        client: Cliente WordPress
        params: Diccionario con lista de posts para actualizar
    """
    action_name = "wordpress_bulk_update_posts"
    try:
        wp_client = _get_wp_client(params)
        posts_data = params.get("posts", [])
        if not posts_data:
            raise ValueError("Se requiere lista de 'posts' para actualizar")
        
        results = []
        for post_data in posts_data:
            post = WordPressPost()
            post_id = post_data.get("id")
            if not post_id:
                continue
                
            for key, value in post_data.items():
                if key != "id":
                    setattr(post, key, value)
            
            success = wp_client.call(posts.EditPost(post_id, post))
            results.append({"id": post_id, "updated": success})
            
        return {"status": "success", "data": results}
    except Exception as e:
        return _handle_wp_api_error(e, action_name)

def wordpress_get_post_revisions(client: Any, params: Dict[str, Any]) -> WordPressResponse:
    """
    Obtiene el historial de revisiones de un post.
    
    Args:
        client: Cliente WordPress
        params: Diccionario con post_id
    """
    action_name = "wordpress_get_post_revisions"
    try:
        wp_client = _get_wp_client(params)
        post_id = params.get("post_id")
        if not post_id:
            raise ValueError("Se requiere 'post_id'")
            
        revisions = wp_client.call(posts.GetRevisions(post_id))
        return {"status": "success", "data": revisions}
    except Exception as e:
        return _handle_wp_api_error(e, action_name)

# --- ACCIONES DE WOOCOMMERCE ---

def woocommerce_get_product_by_sku(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "woocommerce_get_product_by_sku"
    try:
        wc_api = _get_woocommerce_api(params)
        sku = params.get("sku")
        if not sku:
            raise ValueError("Se requiere 'sku'.")
        
        response = wc_api.get("products", params={"sku": sku})
        if response.status_code != 200:
            raise requests.exceptions.HTTPError(response=response)
        
        products = response.json()
        if not products:
             return {"status": "error", "message": f"No se encontró producto con SKU '{sku}'.", "http_status": 404}
        
        return {"status": "success", "data": products[0]}
    except Exception as e:
        return _handle_wp_api_error(e, action_name)

def woocommerce_update_order_status(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "woocommerce_update_order_status"
    try:
        wc_api = _get_woocommerce_api(params)
        order_id = params.get("order_id")
        new_status = params.get("new_status")
        if not order_id or not new_status:
            raise ValueError("Se requieren 'order_id' y 'new_status'.")
            
        payload = {"status": new_status}
        response = wc_api.put(f"orders/{order_id}", payload)
        if response.status_code != 200:
            raise requests.exceptions.HTTPError(response=response)
        
        return {"status": "success", "data": response.json()}
    except Exception as e:
        return _handle_wp_api_error(e, action_name)

def woocommerce_get_customer_orders(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "woocommerce_get_customer_orders"
    try:
        wc_api = _get_woocommerce_api(params)
        customer_email = params.get("customer_email")
        if not customer_email:
            raise ValueError("Se requiere 'customer_email'.")

        # Paso 1: Encontrar el ID del cliente a partir del email
        cust_response = wc_api.get("customers", params={"email": customer_email})
        if cust_response.status_code != 200: raise requests.exceptions.HTTPError(response=cust_response)
        customers = cust_response.json()
        if not customers:
            return {"status": "error", "message": f"No se encontró cliente con email '{customer_email}'.", "http_status": 404}
        customer_id = customers[0]['id']
        
        # Paso 2: Obtener los pedidos para ese ID de cliente
        orders_response = wc_api.get("orders", params={"customer": customer_id})
        if orders_response.status_code != 200: raise requests.exceptions.HTTPError(response=orders_response)
        
        return {"status": "success", "data": orders_response.json()}
    except Exception as e:
        return _handle_wp_api_error(e, action_name)

def woocommerce_create_product(client: Any, params: Dict[str, Any]) -> WordPressResponse:
    """
    Crea un nuevo producto en WooCommerce.
    
    Args:
        client: Cliente WooCommerce
        params: Datos del producto (name, regular_price obligatorios)
    """
    action_name = "woocommerce_create_product"
    try:
        wc_api = _get_woocommerce_api(params)
        required_fields = ["name", "regular_price"]
        if not all(params.get(field) for field in required_fields):
            raise ValueError(f"Se requieren los campos: {', '.join(required_fields)}")
        
        # Validación mejorada de datos
        if not isinstance(params.get("regular_price"), (str, float, int)):
            raise ValueError("regular_price debe ser un número válido")
        
        if params.get("status") not in WP_POST_STATUS.values():
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
        
        response = wc_api.post("products", product_data)
        if response.status_code != 201:
            raise requests.exceptions.HTTPError(response=response)
            
        return {"status": "success", "data": response.json()}
    except Exception as e:
        return _handle_wp_api_error(e, action_name)

def woocommerce_bulk_update_prices(client: Any, params: Dict[str, Any]) -> WordPressResponse:
    """
    Actualiza precios de múltiples productos en WooCommerce.
    
    Args:
        client: Cliente WooCommerce
        params: Lista de productos con IDs y precios
    """
    action_name = "woocommerce_bulk_update_prices"
    try:
        wc_api = _get_woocommerce_api(params)
        products_data = params.get("products", [])
        if not products_data:
            raise ValueError("Se requiere lista de 'products' con IDs y precios")
            
        results = []
        for product in products_data:
            if not all(k in product for k in ["id", "regular_price"]):
                continue
                
            response = wc_api.put(f"products/{product['id']}", {
                "regular_price": str(product["regular_price"]),
                "sale_price": str(product.get("sale_price", ""))
            })
            
            if response.status_code == 200:
                results.append({"id": product["id"], "updated": True})
            else:
                results.append({"id": product["id"], "updated": False})
                
        return {"status": "success", "data": results}
    except Exception as e:
        return _handle_wp_api_error(e, action_name)

def woocommerce_batch_update_products(client: Any, params: Dict[str, Any]) -> WordPressResponse:
    """
    Actualiza múltiples productos en una sola llamada a la API.
    
    Args:
        client: Cliente WooCommerce
        params: Dict con lista de productos para actualizar
    """
    action_name = "woocommerce_batch_update_products"
    try:
        wc_api = _get_woocommerce_api(params)
        products = params.get("products", [])
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
        
        response = wc_api.post("products/batch", batch_data)
        if response.status_code != 200:
            return _handle_wc_specific_error(response, action_name)
            
        return {"status": "success", "data": response.json()}
    except Exception as e:
        return _handle_wp_api_error(e, action_name)

def woocommerce_search_products(client: Any, params: Dict[str, Any]) -> WordPressResponse:
    """
    Búsqueda avanzada de productos con múltiples filtros.
    
    Args:
        client: Cliente WooCommerce
        params: Dict con parámetros de búsqueda
    """
    action_name = "woocommerce_search_products"
    try:
        wc_api = _get_woocommerce_api(params)
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
        
        response = wc_api.get("products", params={k:v for k,v in search_params.items() if v})
        if response.status_code != 200:
            return _handle_wc_specific_error(response, action_name)
            
        return {
            "status": "success", 
            "data": {
                "products": response.json(),
                "total": response.headers.get('X-WP-Total'),
                "total_pages": response.headers.get('X-WP-TotalPages')
            }
        }
    except Exception as e:
        return _handle_wp_api_error(e, action_name)