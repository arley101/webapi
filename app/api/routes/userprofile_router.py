# Archivo generado automáticamente por refactor_maestro.py
from fastapi import APIRouter, Depends, Body, HTTPException
from typing import Dict, Any, Optional
from app.actions import userprofile_actions
from app.dependencies import get_authenticated_http_client
from app.shared.helpers.http_client import AuthenticatedHttpClient

router = APIRouter(prefix="/userprofile", tags=["Userprofile"])

# Endpoint para: profile_get_my_profile
@router.get("/profile_get_my_profile", status_code=200)
async def profile_get_my_profile(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para profile_get_my_profile."""
    try:
        result = await userprofile_actions.profile_get_my_profile(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: profile_get_my_manager
@router.get("/profile_get_my_manager", status_code=200)
async def profile_get_my_manager(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para profile_get_my_manager."""
    try:
        result = await userprofile_actions.profile_get_my_manager(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: profile_get_my_direct_reports
@router.get("/profile_get_my_direct_reports", status_code=200)
async def profile_get_my_direct_reports(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para profile_get_my_direct_reports."""
    try:
        result = await userprofile_actions.profile_get_my_direct_reports(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: profile_get_my_photo
@router.get("/profile_get_my_photo", status_code=200)
async def profile_get_my_photo(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para profile_get_my_photo."""
    try:
        result = await userprofile_actions.profile_get_my_photo(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: profile_update_my_profile
@router.patch("/profile_update_my_profile", status_code=200)
async def profile_update_my_profile(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para profile_update_my_profile."""
    try:
        result = await userprofile_actions.profile_update_my_profile(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

