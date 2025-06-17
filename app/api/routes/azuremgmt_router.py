# Archivo generado automáticamente por refactor_maestro.py
from fastapi import APIRouter, Depends, Body, HTTPException
from typing import Dict, Any, Optional
from app.actions import azuremgmt_actions
from app.dependencies import get_authenticated_http_client
from app.shared.helpers.http_client import AuthenticatedHttpClient

router = APIRouter(prefix="/azuremgmt", tags=["Azuremgmt"])

# Endpoint para: azure_list_resource_groups
@router.get("/azure_list_resource_groups", status_code=200)
async def azure_list_resource_groups(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para azure_list_resource_groups."""
    try:
        result = await azuremgmt_actions.list_resource_groups(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: azure_list_resources_in_rg
@router.get("/azure_list_resources_in_rg", status_code=200)
async def azure_list_resources_in_rg(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para azure_list_resources_in_rg."""
    try:
        result = await azuremgmt_actions.list_resources_in_rg(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: azure_get_resource
@router.get("/azure_get_resource", status_code=200)
async def azure_get_resource(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para azure_get_resource."""
    try:
        result = await azuremgmt_actions.get_resource(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: azure_create_deployment
@router.post("/azure_create_deployment", status_code=200)
async def azure_create_deployment(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para azure_create_deployment."""
    try:
        result = await azuremgmt_actions.create_deployment(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: azure_list_functions
@router.get("/azure_list_functions", status_code=200)
async def azure_list_functions(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para azure_list_functions."""
    try:
        result = await azuremgmt_actions.list_functions(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: azure_get_function_status
@router.get("/azure_get_function_status", status_code=200)
async def azure_get_function_status(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para azure_get_function_status."""
    try:
        result = await azuremgmt_actions.get_function_status(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: azure_restart_function_app
@router.patch("/azure_restart_function_app", status_code=200)
async def azure_restart_function_app(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para azure_restart_function_app."""
    try:
        result = await azuremgmt_actions.restart_function_app(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: azure_list_logic_apps
@router.get("/azure_list_logic_apps", status_code=200)
async def azure_list_logic_apps(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para azure_list_logic_apps."""
    try:
        result = await azuremgmt_actions.list_logic_apps(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: azure_trigger_logic_app
@router.post("/azure_trigger_logic_app", status_code=200)
async def azure_trigger_logic_app(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para azure_trigger_logic_app."""
    try:
        result = await azuremgmt_actions.trigger_logic_app(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: azure_get_logic_app_run_history
@router.get("/azure_get_logic_app_run_history", status_code=200)
async def azure_get_logic_app_run_history(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para azure_get_logic_app_run_history."""
    try:
        result = await azuremgmt_actions.get_logic_app_run_history(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

