# Archivo generado automáticamente por refactor_maestro.py
from fastapi import APIRouter, Depends, Body, HTTPException
from typing import Dict, Any, Optional
from app.actions import teams_actions
from app.dependencies import get_authenticated_http_client
from app.shared.helpers.http_client import AuthenticatedHttpClient

router = APIRouter(prefix="/teams", tags=["Teams"])

# Endpoint para: teams_list_joined_teams
@router.get("/list_joined_teams", status_code=200)
async def teams_list_joined_teams(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para teams_list_joined_teams."""
    try:
        result = await teams_actions.list_joined_teams(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: teams_get_team
@router.get("/get_team", status_code=200)
async def teams_get_team(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para teams_get_team."""
    try:
        result = await teams_actions.get_team(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: teams_list_channels
@router.get("/list_channels", status_code=200)
async def teams_list_channels(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para teams_list_channels."""
    try:
        result = await teams_actions.list_channels(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: teams_get_channel
@router.get("/get_channel", status_code=200)
async def teams_get_channel(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para teams_get_channel."""
    try:
        result = await teams_actions.get_channel(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: teams_send_channel_message
@router.post("/send_channel_message", status_code=200)
async def teams_send_channel_message(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para teams_send_channel_message."""
    try:
        result = await teams_actions.send_channel_message(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: teams_list_channel_messages
@router.get("/list_channel_messages", status_code=200)
async def teams_list_channel_messages(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para teams_list_channel_messages."""
    try:
        result = await teams_actions.list_channel_messages(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: teams_reply_to_message
@router.post("/reply_to_message", status_code=200)
async def teams_reply_to_message(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para teams_reply_to_message."""
    try:
        result = await teams_actions.reply_to_message(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: teams_send_chat_message
@router.post("/send_chat_message", status_code=200)
async def teams_send_chat_message(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para teams_send_chat_message."""
    try:
        result = await teams_actions.send_chat_message(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: teams_list_chats
@router.get("/list_chats", status_code=200)
async def teams_list_chats(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para teams_list_chats."""
    try:
        result = await teams_actions.list_chats(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: teams_get_chat
@router.get("/get_chat", status_code=200)
async def teams_get_chat(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para teams_get_chat."""
    try:
        result = await teams_actions.get_chat(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: teams_create_chat
@router.post("/create_chat", status_code=200)
async def teams_create_chat(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para teams_create_chat."""
    try:
        result = await teams_actions.create_chat(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: teams_list_chat_messages
@router.get("/list_chat_messages", status_code=200)
async def teams_list_chat_messages(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para teams_list_chat_messages."""
    try:
        result = await teams_actions.list_chat_messages(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: teams_schedule_meeting
@router.post("/schedule_meeting", status_code=200)
async def teams_schedule_meeting(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para teams_schedule_meeting."""
    try:
        result = await teams_actions.schedule_meeting(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: teams_get_meeting_details
@router.get("/get_meeting_details", status_code=200)
async def teams_get_meeting_details(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para teams_get_meeting_details."""
    try:
        result = await teams_actions.get_meeting_details(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: teams_list_members
@router.get("/list_members", status_code=200)
async def teams_list_members(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para teams_list_members."""
    try:
        result = await teams_actions.list_members(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

