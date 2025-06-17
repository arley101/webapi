# Archivo generado automáticamente por refactor_maestro.py
from fastapi import APIRouter, Depends, Body, HTTPException
from typing import Dict, Any, Optional
from app.actions import notion_actions
from app.dependencies import get_authenticated_http_client
from app.shared.helpers.http_client import AuthenticatedHttpClient

router = APIRouter(prefix="/notion", tags=["Notion"])

# Endpoint para: notion_search_general
@router.get("/search_general", status_code=200)
async def notion_search_general(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para notion_search_general."""
    try:
        result = await notion_actions.notion_search_general(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: notion_get_database
@router.get("/get_database", status_code=200)
async def notion_get_database(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para notion_get_database."""
    try:
        result = await notion_actions.notion_get_database(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: notion_query_database
@router.post("/query_database", status_code=200)
async def notion_query_database(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para notion_query_database."""
    try:
        result = await notion_actions.notion_query_database(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: notion_retrieve_page
@router.post("/retrieve_page", status_code=200)
async def notion_retrieve_page(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para notion_retrieve_page."""
    try:
        result = await notion_actions.notion_retrieve_page(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: notion_create_page
@router.post("/create_page", status_code=200)
async def notion_create_page(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para notion_create_page."""
    try:
        result = await notion_actions.notion_create_page(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: notion_update_page
@router.patch("/update_page", status_code=200)
async def notion_update_page(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para notion_update_page."""
    try:
        result = await notion_actions.notion_update_page(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: notion_delete_block
@router.delete("/delete_block", status_code=200)
async def notion_delete_block(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para notion_delete_block."""
    try:
        result = await notion_actions.notion_delete_block(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

