# app/actions/users_actions.py (Tu código original, ahora 100% asíncrono)
import logging
import requests
import json
from typing import Dict, List, Optional, Any, Union
from app.core.config import settings
from app.shared.helpers.http_client import AuthenticatedHttpClient

logger = logging.getLogger(__name__)

def _handle_users_directory_api_error(e: Exception, action_name: str, params_for_log: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    log_message = f"Error en Users/Directory action '{action_name}'"
    safe_params = {k: v for k, v in (params_for_log or {}).items() if k not in ['user_payload', 'update_payload', 'passwordProfile']}
    log_message += f" con params: {safe_params}"
    logger.error(f"{log_message}: {type(e).__name__} - {e}", exc_info=True)
    details_str = str(e); status_code_int = 500; graph_error_code = None
    if isinstance(e, requests.exceptions.HTTPError) and e.response is not None:
        status_code_int = e.response.status_code
        try:
            error_data = e.response.json(); error_info = error_data.get("error", {})
            details_str = error_info.get("message", e.response.text); graph_error_code = error_info.get("code")
        except json.JSONDecodeError: details_str = e.response.text[:500] if e.response.text else "No response body"
    return {"status": "error", "action": action_name, "message": f"Error en {action_name}: {details_str}", "details": str(e), "http_status": status_code_int, "graph_error_code": graph_error_code}

async def _directory_paged_request(client: AuthenticatedHttpClient, url_base: str, params_input: Dict[str, Any], query_api_params_initial: Dict[str, Any], max_items_total: Optional[int], action_name_for_log: str, custom_headers_first_call: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    all_items: List[Dict[str, Any]] = []
    current_url: Optional[str] = url_base
    page_count = 0
    max_pages = getattr(settings, 'MAX_PAGING_PAGES', 20)
    effective_max_items = float('inf') if max_items_total is None else max_items_total
    try:
        while current_url and len(all_items) < effective_max_items and page_count < max_pages:
            page_count += 1
            current_call_params = query_api_params_initial if page_count == 1 and current_url == url_base else None
            current_headers = custom_headers_first_call if page_count == 1 and current_url == url_base else None
            response = await client.get(url=current_url, params=current_call_params, headers=current_headers)
            response.raise_for_status()
            response_data = response.json()
            page_items = response_data.get('value', [])
            for item in page_items:
                if len(all_items) < effective_max_items: all_items.append(item)
                else: break
            current_url = response_data.get('@odata.nextLink')
            if not current_url or len(all_items) >= effective_max_items: break
        return {"status": "success", "data": {"value": all_items, "@odata.count": len(all_items)}, "total_retrieved": len(all_items), "pages_processed": page_count}
    except Exception as e: return _handle_users_directory_api_error(e, action_name_for_log, params_input)

async def list_users(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando list_users: %s", params); action_name = "user_list_users"
    url_base = f"{settings.GRAPH_API_BASE_URL}/users"
    api_query_params: Dict[str, Any] = {}
    api_query_params['$select'] = params.get('select', "id,displayName,userPrincipalName,mail,jobTitle,officeLocation,accountEnabled")
    if params.get('filter'): api_query_params['$filter'] = params['filter']
    if params.get('search'): api_query_params['$search'] = f'"{params["search"]}"'
    if params.get('orderby'): api_query_params['$orderby'] = params['orderby']
    max_graph_top_users = getattr(settings, 'MAX_GRAPH_TOP_VALUE_PAGING_USERS', 999)
    api_query_params['$top'] = min(int(params.get('top_per_page', 25)), max_graph_top_users)
    max_items: Optional[int] = int(params['max_items_total']) if params.get('max_items_total') is not None else None
    custom_headers = {}
    if params.get('search'): api_query_params['$count'] = "true"; custom_headers['ConsistencyLevel'] = 'eventual'
    return await _directory_paged_request(client, url_base, params, api_query_params, max_items, action_name, custom_headers_first_call=custom_headers)

async def get_user(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando get_user: %s", params); action_name = "user_get_user"
    user_id_or_upn: Optional[str] = params.get("user_id") or params.get("user_principal_name")
    if not user_id_or_upn: return {"status": "error", "action":action_name, "message": "Se requiere 'user_id' o 'user_principal_name'.", "http_status": 400}
    url = f"{settings.GRAPH_API_BASE_URL}/users/{user_id_or_upn}"
    api_query_params: Dict[str, Any] = {}
    api_query_params['$select'] = params.get('select', "id,displayName,userPrincipalName,mail,jobTitle,officeLocation,accountEnabled,businessPhones,mobilePhone,department,employeeId,givenName,surname")
    try:
        response = await client.get(url, params=api_query_params if api_query_params.get('$select') else None)
        response.raise_for_status()
        return {"status": "success", "data": response.json()}
    except requests.exceptions.HTTPError as http_err:
        if http_err.response and http_err.response.status_code == 404:
            return {"status": "error", "action":action_name, "message": f"Usuario '{user_id_or_upn}' no encontrado.", "http_status": 404, "details": http_err.response.text if http_err.response else "No response object"}
        return _handle_users_directory_api_error(http_err, action_name, params)
    except Exception as e: return _handle_users_directory_api_error(e, action_name, params)

# ... (El resto de las funciones convertidas a async)
async def create_user(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando create_user (payload omitido del log)"); action_name = "user_create_user"
    user_payload: Optional[Dict[str, Any]] = params.get("user_payload")
    if not user_payload: return {"status": "error", "message": "'user_payload' (dict) requerido.", "http_status": 400}
    url = f"{settings.GRAPH_API_BASE_URL}/users"
    try:
        response = await client.post(url, json=user_payload)
        response.raise_for_status()
        return {"status": "success", "data": response.json(), "message": "Usuario creado."}
    except Exception as e: return _handle_users_directory_api_error(e, action_name, params)

async def update_user(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando update_user (payload omitido del log)"); action_name = "user_update_user"
    user_id_or_upn: Optional[str] = params.get("user_id") or params.get("user_principal_name")
    update_payload: Optional[Dict[str, Any]] = params.get("update_payload")
    if not user_id_or_upn: return {"status": "error", "message": "Se requiere 'user_id' o 'user_principal_name'.", "http_status": 400}
    if not update_payload: return {"status": "error", "message": "'update_payload' (dict no vacío) requerido.", "http_status": 400}
    url = f"{settings.GRAPH_API_BASE_URL}/users/{user_id_or_upn}"
    try:
        response = await client.patch(url, json=update_payload)
        response.raise_for_status()
        return {"status": "success", "message": "Usuario actualizado.", "http_status": 204}
    except Exception as e: return _handle_users_directory_api_error(e, action_name, params)

async def delete_user(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando delete_user: %s", params); action_name = "user_delete_user"
    user_id_or_upn: Optional[str] = params.get("user_id") or params.get("user_principal_name")
    if not user_id_or_upn: return {"status": "error", "message": "Se requiere 'user_id' o 'user_principal_name'.", "http_status": 400}
    url = f"{settings.GRAPH_API_BASE_URL}/users/{user_id_or_upn}"
    try:
        response = await client.delete(url)
        response.raise_for_status()
        return {"status": "success", "message": f"Usuario '{user_id_or_upn}' eliminado.", "http_status": 204}
    except Exception as e: return _handle_users_directory_api_error(e, action_name, params)

async def list_groups(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando list_groups: %s", params); action_name = "user_list_groups"
    url_base = f"{settings.GRAPH_API_BASE_URL}/groups"
    api_query_params: Dict[str, Any] = {}
    api_query_params['$select'] = params.get('select', "id,displayName,description,mailEnabled,securityEnabled")
    if params.get('filter'): api_query_params['$filter'] = params['filter']
    if params.get('search'): api_query_params['$search'] = f'"{params["search"]}"'
    max_top = getattr(settings, 'MAX_GRAPH_TOP_VALUE_PAGING', 100)
    api_query_params['$top'] = min(int(params.get('top_per_page', 25)), max_top)
    max_items: Optional[int] = int(params['max_items_total']) if params.get('max_items_total') is not None else None
    custom_headers = {'ConsistencyLevel': 'eventual'} if params.get('search') else None
    if params.get('search'): api_query_params['$count'] = "true"
    return await _directory_paged_request(client, url_base, params, api_query_params, max_items, action_name, custom_headers_first_call=custom_headers)

async def get_group(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando get_group: %s", params); action_name = "user_get_group"
    group_id: Optional[str] = params.get("group_id")
    if not group_id: return {"status": "error", "message": "Se requiere 'group_id'.", "http_status": 400}
    url = f"{settings.GRAPH_API_BASE_URL}/groups/{group_id}"
    api_query_params: Dict[str, Any] = {'$select': params.get('select')} if params.get('select') else {}
    try:
        response = await client.get(url, params=api_query_params)
        response.raise_for_status()
        return {"status": "success", "data": response.json()}
    except Exception as e: return _handle_users_directory_api_error(e, action_name, params)

async def list_group_members(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando list_group_members: %s", params); action_name = "user_list_group_members"
    group_id: Optional[str] = params.get("group_id")
    if not group_id: return {"status": "error", "message": "Se requiere 'group_id'.", "http_status": 400}
    url_base = f"{settings.GRAPH_API_BASE_URL}/groups/{group_id}/members"
    max_items: Optional[int] = int(params['max_items_total']) if params.get('max_items_total') is not None else None
    return await _directory_paged_request(client, url_base, params, {}, max_items, action_name)

async def add_group_member(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando add_group_member: %s", params); action_name = "user_add_group_member"
    group_id: Optional[str] = params.get("group_id"); member_id: Optional[str] = params.get("member_id")
    if not group_id or not member_id: return {"status": "error", "message": "Se requieren 'group_id' y 'member_id'.", "http_status": 400}
    url = f"{settings.GRAPH_API_BASE_URL}/groups/{group_id}/members/$ref"
    payload = {"@odata.id": f"{settings.GRAPH_API_BASE_URL}/directoryObjects/{member_id}"}
    try:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        return {"status": "success", "message": "Miembro añadido.", "http_status": 204}
    except Exception as e: return _handle_users_directory_api_error(e, action_name, params)

async def remove_group_member(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando remove_group_member: %s", params); action_name = "user_remove_group_member"
    group_id: Optional[str] = params.get("group_id"); member_id: Optional[str] = params.get("member_id")
    if not group_id or not member_id: return {"status": "error", "message": "Se requieren 'group_id' y 'member_id'.", "http_status": 400}
    url = f"{settings.GRAPH_API_BASE_URL}/groups/{group_id}/members/{member_id}/$ref"
    try:
        response = await client.delete(url)
        response.raise_for_status()
        return {"status": "success", "message": "Miembro eliminado.", "http_status": 204}
    except Exception as e: return _handle_users_directory_api_error(e, action_name, params)

async def check_group_membership(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando check_group_membership: %s", params); action_name = "user_check_group_membership"
    user_id: Optional[str] = params.get("user_id")
    group_ids: Optional[List[str]] = params.get("group_ids")
    if not user_id or not group_ids: return {"status": "error", "message": "Se requieren 'user_id' y 'group_ids'.", "http_status": 400}
    url = f"{settings.GRAPH_API_BASE_URL}/users/{user_id}/checkMemberGroups"
    payload = {"groupIds": group_ids}
    try:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        return {"status": "success", "data": response.json()}
    except Exception as e: return _handle_users_directory_api_error(e, action_name, params)