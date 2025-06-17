# Archivo generado automáticamente por refactor_maestro.py
from fastapi import APIRouter, Depends, Body, HTTPException
from typing import Dict, Any, Optional
from app.actions import users_actions
from app.dependencies import get_authenticated_http_client
from app.shared.helpers.http_client import AuthenticatedHttpClient

router = APIRouter(prefix="/users", tags=["Users"])

# Endpoint para: user_list_users
@router.get("/user_list_users", status_code=200)
async def user_list_users(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para user_list_users."""
    try:
        result = await users_actions.list_users(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: user_get_user
@router.get("/user_get_user", status_code=200)
async def user_get_user(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para user_get_user."""
    try:
        result = await users_actions.get_user(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: user_create_user
@router.post("/user_create_user", status_code=200)
async def user_create_user(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para user_create_user."""
    try:
        result = await users_actions.create_user(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: user_update_user
@router.patch("/user_update_user", status_code=200)
async def user_update_user(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para user_update_user."""
    try:
        result = await users_actions.update_user(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: user_delete_user
@router.delete("/user_delete_user", status_code=200)
async def user_delete_user(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para user_delete_user."""
    try:
        result = await users_actions.delete_user(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: user_list_groups
@router.get("/user_list_groups", status_code=200)
async def user_list_groups(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para user_list_groups."""
    try:
        result = await users_actions.list_groups(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: user_get_group
@router.get("/user_get_group", status_code=200)
async def user_get_group(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para user_get_group."""
    try:
        result = await users_actions.get_group(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: user_list_group_members
@router.get("/user_list_group_members", status_code=200)
async def user_list_group_members(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para user_list_group_members."""
    try:
        result = await users_actions.list_group_members(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: user_add_group_member
@router.post("/user_add_group_member", status_code=200)
async def user_add_group_member(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para user_add_group_member."""
    try:
        result = await users_actions.add_group_member(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: user_remove_group_member
@router.patch("/user_remove_group_member", status_code=200)
async def user_remove_group_member(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para user_remove_group_member."""
    try:
        result = await users_actions.remove_group_member(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: user_check_group_membership
@router.get("/user_check_group_membership", status_code=200)
async def user_check_group_membership(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para user_check_group_membership."""
    try:
        result = await users_actions.check_group_membership(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

