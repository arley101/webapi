# Archivo para el servicio 'youtube_ads' generado automáticamente
from fastapi import APIRouter, Depends, Body, Path, Query, HTTPException, status, Response
from typing import Dict, Any, Optional
from app.actions import youtube_ads_actions
from app.api.dependencies import get_authenticated_http_client
from app.shared.helpers.http_client import AuthenticatedHttpClient

router = APIRouter(prefix="/youtube_ads", tags=["Youtube_ads"])

# Endpoint para: youtube_get_channel_stats
@router.post("/youtube_get_channel_stats")
def youtube_get_channel_stats(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para youtube_get_channel_stats"""
    final_params = params or {}
    result = youtube_ads_actions.youtube_get_channel_stats(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

