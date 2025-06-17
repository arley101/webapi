# Archivo generado automáticamente por refactor_maestro.py
from fastapi import APIRouter, Depends, Body, HTTPException
from typing import Dict, Any, Optional
from app.actions import stream_actions
from app.dependencies import get_authenticated_http_client
from app.shared.helpers.http_client import AuthenticatedHttpClient

router = APIRouter(prefix="/stream", tags=["Stream"])

# Endpoint para: stream_get_video_playback_url
@router.get("/get_video_playback_url", status_code=200)
async def stream_get_video_playback_url(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para stream_get_video_playback_url."""
    try:
        result = await stream_actions.get_video_playback_url(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: stream_listar_videos
@router.get("/listar_videos", status_code=200)
async def stream_listar_videos(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para stream_listar_videos."""
    try:
        result = await stream_actions.listar_videos(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: stream_obtener_metadatos_video
@router.get("/obtener_metadatos_video", status_code=200)
async def stream_obtener_metadatos_video(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para stream_obtener_metadatos_video."""
    try:
        result = await stream_actions.obtener_metadatos_video(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: stream_obtener_transcripcion_video
@router.get("/obtener_transcripcion_video", status_code=200)
async def stream_obtener_transcripcion_video(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para stream_obtener_transcripcion_video."""
    try:
        result = await stream_actions.obtener_transcripcion_video(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

