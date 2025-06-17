# Archivo generado automáticamente por refactor_maestro.py
from fastapi import APIRouter, Depends, Body, HTTPException
from typing import Dict, Any, Optional
from app.actions import forms_actions
from app.dependencies import get_authenticated_http_client
from app.shared.helpers.http_client import AuthenticatedHttpClient

router = APIRouter(prefix="/forms", tags=["Forms"])

# Endpoint para: forms_list_forms
@router.get("/list_forms", status_code=200)
async def forms_list_forms(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para forms_list_forms."""
    try:
        result = await forms_actions.list_forms(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: forms_get_form
@router.get("/get_form", status_code=200)
async def forms_get_form(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para forms_get_form."""
    try:
        result = await forms_actions.get_form(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: forms_get_form_responses
@router.get("/get_form_responses", status_code=200)
async def forms_get_form_responses(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para forms_get_form_responses."""
    try:
        result = await forms_actions.get_form_responses(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

