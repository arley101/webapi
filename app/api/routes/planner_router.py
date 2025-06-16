# Archivo generado automáticamente
from fastapi import APIRouter, Depends, Body, HTTPException, status, Response
from typing import Dict, Any, Optional
from app.actions import planner_actions
from app.dependencies import get_authenticated_http_client
from app.shared.helpers.http_client import AuthenticatedHttpClient

router = APIRouter(prefix="/planner", tags=["Planner"])

# Endpoint para: planner_list_plans
@router.post("/list_plans")
def planner_list_plans(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = planner_actions.list_plans(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

# Endpoint para: planner_get_plan
@router.post("/get_plan")
def planner_get_plan(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = planner_actions.get_plan(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

# Endpoint para: planner_list_tasks
@router.post("/list_tasks")
def planner_list_tasks(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = planner_actions.list_tasks(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

# Endpoint para: planner_create_task
@router.post("/create_task")
def planner_create_task(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = planner_actions.create_task(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

# Endpoint para: planner_get_task
@router.post("/get_task")
def planner_get_task(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = planner_actions.get_task(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

# Endpoint para: planner_update_task
@router.post("/update_task")
def planner_update_task(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = planner_actions.update_task(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

# Endpoint para: planner_delete_task
@router.post("/delete_task")
def planner_delete_task(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = planner_actions.delete_task(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

# Endpoint para: planner_list_buckets
@router.post("/list_buckets")
def planner_list_buckets(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = planner_actions.list_buckets(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

# Endpoint para: planner_create_bucket
@router.post("/create_bucket")
def planner_create_bucket(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = planner_actions.create_bucket(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

