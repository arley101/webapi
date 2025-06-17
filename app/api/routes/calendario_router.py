# Archivo generado automáticamente por refactor_maestro.py
from fastapi import APIRouter, Depends, Body, HTTPException
from typing import Dict, Any, Optional
from app.actions import calendario_actions
from app.dependencies import get_authenticated_http_client
from app.shared.helpers.http_client import AuthenticatedHttpClient

router = APIRouter(prefix="/calendario", tags=["Calendario"])

# Endpoint para: calendar_list_events
@router.get("/calendar_list_events", status_code=200)
async def calendar_list_events(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para calendar_list_events."""
    try:
        result = await calendario_actions.calendar_list_events(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: calendar_create_event
@router.post("/calendar_create_event", status_code=200)
async def calendar_create_event(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para calendar_create_event."""
    try:
        result = await calendario_actions.calendar_create_event(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: calendar_get_event
@router.get("/calendar_get_event", status_code=200)
async def calendar_get_event(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para calendar_get_event."""
    try:
        result = await calendario_actions.get_event(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: calendar_update_event
@router.patch("/calendar_update_event", status_code=200)
async def calendar_update_event(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para calendar_update_event."""
    try:
        result = await calendario_actions.update_event(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: calendar_delete_event
@router.delete("/calendar_delete_event", status_code=200)
async def calendar_delete_event(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para calendar_delete_event."""
    try:
        result = await calendario_actions.delete_event(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: calendar_find_meeting_times
@router.post("/calendar_find_meeting_times", status_code=200)
async def calendar_find_meeting_times(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para calendar_find_meeting_times."""
    try:
        result = await calendario_actions.find_meeting_times(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: calendar_get_schedule
@router.get("/calendar_get_schedule", status_code=200)
async def calendar_get_schedule(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para calendar_get_schedule."""
    try:
        result = await calendario_actions.get_schedule(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

