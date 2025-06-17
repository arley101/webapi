# Archivo generado automáticamente por refactor_maestro.py
from fastapi import APIRouter, Depends, Body, HTTPException
from typing import Dict, Any, Optional
from app.actions import graph_actions
from app.dependencies import get_authenticated_http_client
from app.shared.helpers.http_client import AuthenticatedHttpClient

router = APIRouter(prefix="/graph", tags=["Graph"])

# Endpoint para: graph_generic_get
@router.get("/generic_get", status_code=200)
async def graph_generic_get(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para graph_generic_get."""
    try:
        result = await graph_actions.generic_get(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: graph_generic_post
@router.post("/generic_post", status_code=200)
async def graph_generic_post(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para graph_generic_post."""
    try:
        result = await graph_actions.generic_post(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: graph_generic_get_compat
@router.get("/generic_get_compat", status_code=200)
async def graph_generic_get_compat(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para graph_generic_get_compat."""
    try:
        result = await graph_actions.generic_get_compat(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: graph_generic_post_compat
@router.post("/generic_post_compat", status_code=200)
async def graph_generic_post_compat(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para graph_generic_post_compat."""
    try:
        result = await graph_actions.generic_post_compat(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

