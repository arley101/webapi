# app/actions/correo_actions.py
import logging
from typing import Dict, Any
from app.shared.helpers.http_client import AuthenticatedHttpClient
from app.core.config import settings

logger = logging.getLogger(__name__)
BASE_URL = "https://graph.microsoft.com/v1.0"

def _get_user_url_segment(params: Dict[str, Any]) -> str:
    """Helper para construir el segmento de URL del usuario (/me o /users/{id})."""
    user_id = params.get("user_id", "me")
    return f"/users/{user_id}"

async def list_messages(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    user_segment = _get_user_url_segment(params)
    folder_id = params.get("folder_id")
    url = f"{BASE_URL}{user_segment}/mailFolders/{folder_id}/messages" if folder_id else f"{BASE_URL}{user_segment}/messages"
    
    query_params = {
        "$select": params.get("select"),
        "$filter": params.get("filter"),
        "$top": params.get("top", 25)
    }
    query_params = {k: v for k, v in query_params.items() if v is not None}
    
    response = await client.get(url, params=query_params)
    return response.json()

async def get_message(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    user_segment = _get_user_url_segment(params)
    message_id = params.get("message_id")
    if not message_id:
        return {"status": "error", "message": "Se requiere 'message_id'."}
    
    url = f"{BASE_URL}{user_segment}/messages/{message_id}"
    response = await client.get(url)
    return response.json()

async def send_message(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    user_segment = _get_user_url_segment(params)
    save_to_sent_items = params.get("save_to_sent_items", "true") # API espera un string
    
    message_payload = {
        "message": {
            "subject": params.get("subject"),
            "body": {
                "contentType": params.get("body_type", "HTML"),
                "content": params.get("body_content")
            },
            "toRecipients": params.get("to_recipients"),
            "ccRecipients": params.get("cc_recipients"),
            "bccRecipients": params.get("bcc_recipients")
        },
        "saveToSentItems": str(save_to_sent_items).lower()
    }
    
    url = f"{BASE_URL}{user_segment}/sendMail"
    response = await client.post(url, json=message_payload)
    if 200 <= response.status_code < 300:
        return {"status": "success", "message": "Solicitud de envío de correo aceptada.", "http_status": response.status_code}
    return response.json()

async def reply_message(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    user_segment = _get_user_url_segment(params)
    message_id = params.get("message_id")
    if not message_id:
        return {"status": "error", "message": "Se requiere 'message_id'."}
        
    reply_payload = {"comment": params.get("comment")}
    
    url = f"{BASE_URL}{user_segment}/messages/{message_id}/reply"
    response = await client.post(url, json=reply_payload)
    if 200 <= response.status_code < 300:
        return {"status": "success", "message": "Respuesta enviada.", "http_status": response.status_code}
    return response.json()

async def forward_message(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    user_segment = _get_user_url_segment(params)
    message_id = params.get("message_id")
    if not message_id:
        return {"status": "error", "message": "Se requiere 'message_id'."}

    forward_payload = {
        "comment": params.get("comment"),
        "toRecipients": params.get("to_recipients")
    }
    
    url = f"{BASE_URL}{user_segment}/messages/{message_id}/forward"
    response = await client.post(url, json=forward_payload)
    if 200 <= response.status_code < 300:
        return {"status": "success", "message": "Mensaje reenviado.", "http_status": response.status_code}
    return response.json()

async def delete_message(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    user_segment = _get_user_url_segment(params)
    message_id = params.get("message_id")
    if not message_id:
        return {"status": "error", "message": "Se requiere 'message_id'."}
        
    url = f"{BASE_URL}{user_segment}/messages/{message_id}"
    response = await client.delete(url)
    if 200 <= response.status_code < 300:
        return {"status": "success", "message": "Mensaje eliminado.", "http_status": response.status_code}
    return response.json()

async def move_message(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    user_segment = _get_user_url_segment(params)
    message_id = params.get("message_id")
    destination_id = params.get("destination_id")
    if not message_id or not destination_id:
        return {"status": "error", "message": "Se requieren 'message_id' y 'destination_id'."}

    move_payload = {"destinationId": destination_id}
    url = f"{BASE_URL}{user_segment}/messages/{message_id}/move"
    response = await client.post(url, json=move_payload)
    return response.json()

async def list_folders(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    user_segment = _get_user_url_segment(params)
    url = f"{BASE_URL}{user_segment}/mailFolders"
    response = await client.get(url)
    return response.json()

async def create_folder(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    user_segment = _get_user_url_segment(params)
    folder_name = params.get("displayName")
    if not folder_name:
        return {"status": "error", "message": "Se requiere 'displayName' para la nueva carpeta."}

    url = f"{BASE_URL}{user_segment}/mailFolders"
    response = await client.post(url, json={"displayName": folder_name})
    return response.json()

async def search_messages(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    user_segment = _get_user_url_segment(params)
    query = params.get("q")
    if not query:
        return {"status": "error", "message": "Se requiere parámetro de búsqueda 'q'."}
    
    url = f"{BASE_URL}{user_segment}/messages"
    response = await client.get(url, params={"$search": query})
    return response.json()