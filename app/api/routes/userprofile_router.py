# Archivo para el servicio 'userprofile' generado automáticamente
from fastapi import APIRouter, Depends, Body, Path, Query, HTTPException, status, Response
from typing import Dict, Any, Optional
from app.actions import userprofile_actions
from app.api.dependencies import get_authenticated_http_client
from app.shared.helpers.http_client import AuthenticatedHttpClient

router = APIRouter(prefix="/userprofile", tags=["Userprofile"])

# Endpoint para: profile_get_my_profile
@router.post("/profile_get_my_profile")
def profile_get_my_profile(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para profile_get_my_profile"""
    final_params = params or {}
    result = userprofile_actions.profile_get_my_profile(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: profile_get_my_manager
@router.post("/profile_get_my_manager")
def profile_get_my_manager(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para profile_get_my_manager"""
    final_params = params or {}
    result = userprofile_actions.profile_get_my_manager(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: profile_get_my_direct_reports
@router.post("/profile_get_my_direct_reports")
def profile_get_my_direct_reports(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para profile_get_my_direct_reports"""
    final_params = params or {}
    result = userprofile_actions.profile_get_my_direct_reports(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: profile_get_my_photo
@router.post("/profile_get_my_photo")
def profile_get_my_photo(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para profile_get_my_photo"""
    final_params = params or {}
    result = userprofile_actions.profile_get_my_photo(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: profile_update_my_profile
@router.post("/profile_update_my_profile")
def profile_update_my_profile(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para profile_update_my_profile"""
    final_params = params or {}
    result = userprofile_actions.profile_update_my_profile(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

