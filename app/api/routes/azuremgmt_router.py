# Archivo generado automáticamente
from fastapi import APIRouter, Depends, Body, HTTPException, status, Response
from typing import Dict, Any, Optional
from app.actions import azuremgmt_actions
from app.dependencies import get_authenticated_http_client
from app.shared.helpers.http_client import AuthenticatedHttpClient

router = APIRouter(prefix="/azuremgmt", tags=["Azuremgmt"])

# Endpoint para: azure_list_resource_groups
@router.post("/azure_list_resource_groups")
def azure_list_resource_groups(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = azuremgmt_actions.list_resource_groups(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

# Endpoint para: azure_list_resources_in_rg
@router.post("/azure_list_resources_in_rg")
def azure_list_resources_in_rg(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = azuremgmt_actions.list_resources_in_rg(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

# Endpoint para: azure_get_resource
@router.post("/azure_get_resource")
def azure_get_resource(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = azuremgmt_actions.get_resource(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

# Endpoint para: azure_create_deployment
@router.post("/azure_create_deployment")
def azure_create_deployment(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = azuremgmt_actions.create_deployment(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

# Endpoint para: azure_list_functions
@router.post("/azure_list_functions")
def azure_list_functions(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = azuremgmt_actions.list_functions(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

# Endpoint para: azure_get_function_status
@router.post("/azure_get_function_status")
def azure_get_function_status(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = azuremgmt_actions.get_function_status(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

# Endpoint para: azure_restart_function_app
@router.post("/azure_restart_function_app")
def azure_restart_function_app(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = azuremgmt_actions.restart_function_app(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

# Endpoint para: azure_list_logic_apps
@router.post("/azure_list_logic_apps")
def azure_list_logic_apps(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = azuremgmt_actions.list_logic_apps(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

# Endpoint para: azure_trigger_logic_app
@router.post("/azure_trigger_logic_app")
def azure_trigger_logic_app(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = azuremgmt_actions.trigger_logic_app(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

# Endpoint para: azure_get_logic_app_run_history
@router.post("/azure_get_logic_app_run_history")
def azure_get_logic_app_run_history(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = azuremgmt_actions.get_logic_app_run_history(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

