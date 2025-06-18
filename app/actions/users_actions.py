# app/actions/users_actions.py (Versión Original Restaurada)

from app.shared.helpers.http_client import AuthenticatedHttpClient
import logging

logger = logging.getLogger(__name__)
BASE_URL = "https://graph.microsoft.com/v1.0"

async def list_users(client: AuthenticatedHttpClient, params: dict):
    query_params = {
        "$filter": params.get("filter"),
        "$select": params.get("select"),
        "$top": params.get("top", 100)
    }
    query_params = {k: v for k, v in query_params.items() if v is not None}
    url = f"{BASE_URL}/users"
    response = client.get(url, params=query_params)
    return response.json()

async def get_user(client: AuthenticatedHttpClient, params: dict):
    user_id = params.get("user_id") or params.get("user_principal_name")
    if not user_id:
        return {"status": "error", "message": "Se requiere 'user_id' o 'user_principal_name'.", "http_status": 400}
    select_fields = params.get("select")
    url = f"{BASE_URL}/users/{user_id}"
    query_params = {"$select": select_fields} if select_fields else None
    response = client.get(url, params=query_params)
    return response.json()

async def create_user(client: AuthenticatedHttpClient, params: dict):
    required_fields = ["accountEnabled", "displayName", "mailNickname", "userPrincipalName", "passwordProfile"]
    if not all(field in params for field in required_fields):
        return {"status": "error", "message": "Faltan campos requeridos para crear el usuario.", "http_status": 400}
    url = f"{BASE_URL}/users"
    response = client.post(url, json=params)
    return response.json()

async def update_user(client: AuthenticatedHttpClient, params: dict):
    user_id = params.get("user_id") or params.get("user_principal_name")
    if not user_id:
        return {"status": "error", "message": "Se requiere 'user_id' o 'user_principal_name' para actualizar.", "http_status": 400}
    update_payload = {k: v for k, v in params.items() if k not in ["user_id", "user_principal_name"]}
    if not update_payload:
        return {"status": "error", "message": "No se proporcionaron campos para actualizar.", "http_status": 400}
    url = f"{BASE_URL}/users/{user_id}"
    response = client.patch(url, json=update_payload)
    if response.status_code == 204:
        return {"status": "success", "message": f"Usuario {user_id} actualizado correctamente."}
    return response.json()

async def delete_user(client: AuthenticatedHttpClient, params: dict):
    user_id = params.get("user_id") or params.get("user_principal_name")
    if not user_id:
        return {"status": "error", "message": "Se requiere 'user_id' o 'user_principal_name' para eliminar.", "http_status": 400}
    url = f"{BASE_URL}/users/{user_id}"
    response = client.delete(url)
    if response.status_code == 204:
        return {"status": "success", "message": f"Usuario {user_id} eliminado correctamente."}
    return response.json()

async def list_groups(client: AuthenticatedHttpClient, params: dict):
    query_params = {
        "$filter": params.get("filter"),
        "$select": params.get("select"),
        "$top": params.get("top", 100)
    }
    query_params = {k: v for k, v in query_params.items() if v is not None}
    url = f"{BASE_URL}/groups"
    response = client.get(url, params=query_params)
    return response.json()

async def get_group(client: AuthenticatedHttpClient, params: dict):
    group_id = params.get("group_id")
    if not group_id:
        return {"status": "error", "message": "Se requiere 'group_id'.", "http_status": 400}
    select_fields = params.get("select")
    url = f"{BASE_URL}/groups/{group_id}"
    query_params = {"$select": select_fields} if select_fields else None
    response = client.get(url, params=query_params)
    return response.json()

async def list_group_members(client: AuthenticatedHttpClient, params: dict):
    group_id = params.get("group_id")
    if not group_id:
        return {"status": "error", "message": "Se requiere 'group_id'.", "http_status": 400}
    url = f"{BASE_URL}/groups/{group_id}/members"
    response = client.get(url)
    return response.json()

async def add_group_member(client: AuthenticatedHttpClient, params: dict):
    group_id = params.get("group_id")
    user_id = params.get("user_id")
    if not group_id or not user_id:
        return {"status": "error", "message": "Se requieren 'group_id' y 'user_id'.", "http_status": 400}
    url = f"{BASE_URL}/groups/{group_id}/members/$ref"
    payload = {
        "@odata.id": f"{BASE_URL}/directoryObjects/{user_id}"
    }
    response = client.post(url, json=payload)
    if response.status_code == 204:
        return {"status": "success", "message": f"Usuario {user_id} añadido al grupo {group_id}."}
    return response.json()

async def remove_group_member(client: AuthenticatedHttpClient, params: dict):
    group_id = params.get("group_id")
    member_id = params.get("member_id")
    if not group_id or not member_id:
        return {"status": "error", "message": "Se requieren 'group_id' y 'member_id'.", "http_status": 400}
    url = f"{BASE_URL}/groups/{group_id}/members/{member_id}/$ref"
    response = client.delete(url)
    if response.status_code == 204:
        return {"status": "success", "message": f"Miembro {member_id} eliminado del grupo {group_id}."}
    return response.json()

async def check_group_membership(client: AuthenticatedHttpClient, params: dict):
    user_id = params.get("user_id", "me")
    group_ids = params.get("group_ids")
    if not group_ids:
        return {"status": "error", "message": "Se requiere una lista de 'group_ids'.", "http_status": 400}
    url = f"{BASE_URL}/users/{user_id}/checkMemberGroups"
    payload = {"groupIds": group_ids}
    response = client.post(url, json=payload)
    return response.json()