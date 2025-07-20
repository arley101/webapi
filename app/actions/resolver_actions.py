# app/actions/resolver_actions.py
import logging
import json
from typing import Dict, Any, Optional

from app.shared.helpers.http_client import AuthenticatedHttpClient
from app.actions import (
    googleads_actions, 
    planner_actions, 
    teams_actions, 
    notion_actions
)

logger = logging.getLogger(__name__)

RESOLVER_MAP = {
    "google_campaign": googleads_actions.googleads_get_campaign_by_name,
    "planner_plan": planner_actions.planner_get_plan_by_name,
    "teams_team": teams_actions.teams_get_team_by_name,
    "notion_database": notion_actions.notion_find_database_by_name,
}

def _handle_resolver_error(message: str, http_status: int = 500, details: Any = None) -> Dict[str, Any]:
    logger.error(f"Resolver Error: {message} | Details: {details}")
    return {"status": "error", "action": "resolve_resource", "message": message, "http_status": http_status, "details": details}

def resolve_resource(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "resolve_resource"
    object_type = params.get("object_type")
    search_params = params.get("search_params")
    memory_db_id = params.get("memory_db_id")

    if not all([object_type, search_params, memory_db_id]):
        return _handle_resolver_error("Se requieren 'object_type', 'search_params' y 'memory_db_id'.", 400)

    resolver_function = RESOLVER_MAP.get(object_type)
    if not resolver_function:
        return _handle_resolver_error(f"Tipo de objeto '{object_type}' no es soportado.", 400)

    search_key_name = next(iter(search_params))
    search_value = search_params[search_key_name]
    cache_key = f"{object_type}:{search_key_name}:{search_value}"
    
    # 1. Buscar en la memoria de Notion
    try:
        query_payload = {"filter": {"property": "CacheKey", "title": {"equals": cache_key}}}
        query_params = {"database_id": memory_db_id, "query_payload": query_payload, **params}
        cached_response = notion_actions.notion_query_database(client, query_params)

        if cached_response.get("status") == "success" and cached_response.get("data", {}).get("results"):
            page = cached_response["data"]["results"][0]
            value_str = page["properties"]["FullObject"]["rich_text"][0]["text"]["content"]
            logger.info(f"Recurso encontrado en caché de Notion para '{cache_key}'.")
            return {"status": "success", "data": json.loads(value_str), "source": "notion_cache"}
    except Exception as e:
        logger.warning(f"No se pudo leer la caché de Notion para '{cache_key}': {e}. Se buscará en tiempo real.")

    # 2. Buscar en tiempo real
    live_search_params = {**params, **search_params}
    live_response = resolver_function(client, live_search_params)
    
    if live_response.get("status") != "success":
        return live_response

    live_data = live_response.get("data")
    resource_id = live_data.get("id") or live_data.get("resourceName")

    # 3. Guardar en Notion
    try:
        properties = {
            "CacheKey": {"title": [{"text": {"content": cache_key}}]},
            "FullObject": {"rich_text": [{"text": {"content": json.dumps(live_data, indent=2)}}]},
            "ResourceType": {"select": {"name": object_type}},
            "ResourceName": {"rich_text": [{"text": {"content": search_value}}]},
            "ResourceID": {"rich_text": [{"text": {"content": str(resource_id)}}]}
        }
        create_params = {"database_id": memory_db_id, "properties_payload": properties, **params}
        notion_actions.notion_create_page_in_database(client, create_params)
        logger.info(f"Nuevo recurso para '{cache_key}' guardado en la caché de Notion.")
    except Exception as e:
        logger.warning(f"No se pudo guardar el resultado de '{cache_key}' en la caché de Notion: {e}")

    return {"status": "success", "data": live_data, "source": "live_api"}