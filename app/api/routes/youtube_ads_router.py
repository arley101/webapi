# Archivo generado automáticamente por refactor_maestro.py
from fastapi import APIRouter, Depends, Body, HTTPException
from typing import Dict, Any, Optional
from app.actions import youtube_ads_actions
from app.dependencies import get_authenticated_http_client
from app.shared.helpers.http_client import AuthenticatedHttpClient

router = APIRouter(prefix="/youtube_ads", tags=["Youtube_ads"])

# Endpoint para: youtube_get_channel_stats
@router.get("/youtube_get_channel_stats", status_code=200)
async def youtube_get_channel_stats(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para youtube_get_channel_stats."""
    try:
        result = await youtube_ads_actions.youtube_get_channel_stats(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

