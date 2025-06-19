from fastapi import APIRouter, Depends, Body
from typing import Dict, Any, Optional
from app.actions import correo_actions
from app.dependencies import get_authenticated_http_client
from app.shared.helpers.http_client import AuthenticatedHttpClient

router = APIRouter(prefix="/correo", tags=["Correo"])

@router.post("/list_messages")
async def list_messages_endpoint(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    return await correo_actions.list_messages(client, params or {})

@router.post("/get_message")
async def get_message_endpoint(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    return await correo_actions.get_message(client, params or {})

@router.post("/send_message")
async def send_message_endpoint(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    return await correo_actions.send_message(client, params or {})

@router.post("/reply_message")
async def reply_message_endpoint(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    return await correo_actions.reply_message(client, params or {})

@router.post("/forward_message")
async def forward_message_endpoint(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    return await correo_actions.forward_message(client, params or {})

@router.post("/delete_message")
async def delete_message_endpoint(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    return await correo_actions.delete_message(client, params or {})

@router.post("/move_message")
async def move_message_endpoint(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    return await correo_actions.move_message(client, params or {})

@router.post("/list_folders")
async def list_folders_endpoint(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    return await correo_actions.list_folders(client, params or {})

@router.post("/create_folder")
async def create_folder_endpoint(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    return await correo_actions.create_folder(client, params or {})

@router.post("/search_messages")
async def search_messages_endpoint(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    return await correo_actions.search_messages(client, params or {})