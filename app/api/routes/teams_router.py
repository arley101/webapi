# Archivo para el servicio 'teams' generado automáticamente
from fastapi import APIRouter, Depends, Body, Path, Query, HTTPException, status, Response
from typing import Dict, Any, Optional
from app.actions import teams_actions
from app.api.dependencies import get_authenticated_http_client
from app.shared.helpers.http_client import AuthenticatedHttpClient

router = APIRouter(prefix="/teams", tags=["Teams"])

# Endpoint para: teams_list_joined_teams
@router.post("/list_joined_teams")
def teams_list_joined_teams(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para teams_list_joined_teams"""
    final_params = params or {}
    result = teams_actions.list_joined_teams(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: teams_get_team
@router.post("/get_team")
def teams_get_team(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para teams_get_team"""
    final_params = params or {}
    result = teams_actions.get_team(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: teams_list_channels
@router.post("/list_channels")
def teams_list_channels(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para teams_list_channels"""
    final_params = params or {}
    result = teams_actions.list_channels(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: teams_get_channel
@router.post("/get_channel")
def teams_get_channel(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para teams_get_channel"""
    final_params = params or {}
    result = teams_actions.get_channel(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: teams_send_channel_message
@router.post("/send_channel_message")
def teams_send_channel_message(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para teams_send_channel_message"""
    final_params = params or {}
    result = teams_actions.send_channel_message(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: teams_list_channel_messages
@router.post("/list_channel_messages")
def teams_list_channel_messages(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para teams_list_channel_messages"""
    final_params = params or {}
    result = teams_actions.list_channel_messages(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: teams_reply_to_message
@router.post("/reply_to_message")
def teams_reply_to_message(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para teams_reply_to_message"""
    final_params = params or {}
    result = teams_actions.reply_to_message(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: teams_send_chat_message
@router.post("/send_chat_message")
def teams_send_chat_message(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para teams_send_chat_message"""
    final_params = params or {}
    result = teams_actions.send_chat_message(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: teams_list_chats
@router.post("/list_chats")
def teams_list_chats(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para teams_list_chats"""
    final_params = params or {}
    result = teams_actions.list_chats(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: teams_get_chat
@router.post("/get_chat")
def teams_get_chat(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para teams_get_chat"""
    final_params = params or {}
    result = teams_actions.get_chat(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: teams_create_chat
@router.post("/create_chat")
def teams_create_chat(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para teams_create_chat"""
    final_params = params or {}
    result = teams_actions.create_chat(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: teams_list_chat_messages
@router.post("/list_chat_messages")
def teams_list_chat_messages(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para teams_list_chat_messages"""
    final_params = params or {}
    result = teams_actions.list_chat_messages(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: teams_schedule_meeting
@router.post("/schedule_meeting")
def teams_schedule_meeting(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para teams_schedule_meeting"""
    final_params = params or {}
    result = teams_actions.schedule_meeting(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: teams_get_meeting_details
@router.post("/get_meeting_details")
def teams_get_meeting_details(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para teams_get_meeting_details"""
    final_params = params or {}
    result = teams_actions.get_meeting_details(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: teams_list_members
@router.post("/list_members")
def teams_list_members(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para teams_list_members"""
    final_params = params or {}
    result = teams_actions.list_members(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

