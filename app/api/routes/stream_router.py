# Archivo para el servicio 'stream' generado automáticamente
from fastapi import APIRouter, Depends, Body, Path, Query, HTTPException, status, Response
from typing import Dict, Any, Optional
from app.actions import stream_actions
from app.api.dependencies import get_authenticated_http_client
from app.shared.helpers.http_client import AuthenticatedHttpClient

router = APIRouter(prefix="/stream", tags=["Stream"])

# Endpoint para: stream_get_video_playback_url
@router.post("/get_video_playback_url")
def stream_get_video_playback_url(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para stream_get_video_playback_url"""
    final_params = params or {}
    result = stream_actions.get_video_playback_url(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: stream_listar_videos
@router.post("/listar_videos")
def stream_listar_videos(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para stream_listar_videos"""
    final_params = params or {}
    result = stream_actions.listar_videos(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: stream_obtener_metadatos_video
@router.post("/obtener_metadatos_video")
def stream_obtener_metadatos_video(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para stream_obtener_metadatos_video"""
    final_params = params or {}
    result = stream_actions.obtener_metadatos_video(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: stream_obtener_transcripcion_video
@router.post("/obtener_transcripcion_video")
def stream_obtener_transcripcion_video(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para stream_obtener_transcripcion_video"""
    final_params = params or {}
    result = stream_actions.obtener_transcripcion_video(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

