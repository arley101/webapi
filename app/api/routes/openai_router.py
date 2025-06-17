# Archivo generado automáticamente por refactor_maestro.py
from fastapi import APIRouter, Depends, Body, HTTPException
from typing import Dict, Any, Optional
from app.actions import openai_actions
from app.dependencies import get_authenticated_http_client
from app.shared.helpers.http_client import AuthenticatedHttpClient

router = APIRouter(prefix="/openai", tags=["Openai"])

# Endpoint para: openai_chat_completion
@router.post("/chat_completion", status_code=200)
async def openai_chat_completion(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para openai_chat_completion."""
    try:
        result = await openai_actions.chat_completion(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: openai_completion
@router.post("/completion", status_code=200)
async def openai_completion(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para openai_completion."""
    try:
        result = await openai_actions.completion(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: openai_get_embedding
@router.get("/get_embedding", status_code=200)
async def openai_get_embedding(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para openai_get_embedding."""
    try:
        result = await openai_actions.get_embedding(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: openai_list_models
@router.get("/list_models", status_code=200)
async def openai_list_models(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para openai_list_models."""
    try:
        result = await openai_actions.list_models(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

