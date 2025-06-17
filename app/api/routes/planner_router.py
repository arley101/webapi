# Archivo generado automáticamente por refactor_maestro.py
from fastapi import APIRouter, Depends, Body, HTTPException
from typing import Dict, Any, Optional
from app.actions import planner_actions
from app.dependencies import get_authenticated_http_client
from app.shared.helpers.http_client import AuthenticatedHttpClient

router = APIRouter(prefix="/planner", tags=["Planner"])

# Endpoint para: planner_list_plans
@router.get("/list_plans", status_code=200)
async def planner_list_plans(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para planner_list_plans."""
    try:
        result = await planner_actions.list_plans(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: planner_get_plan
@router.get("/get_plan", status_code=200)
async def planner_get_plan(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para planner_get_plan."""
    try:
        result = await planner_actions.get_plan(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: planner_list_tasks
@router.get("/list_tasks", status_code=200)
async def planner_list_tasks(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para planner_list_tasks."""
    try:
        result = await planner_actions.list_tasks(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: planner_create_task
@router.post("/create_task", status_code=200)
async def planner_create_task(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para planner_create_task."""
    try:
        result = await planner_actions.create_task(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: planner_get_task
@router.get("/get_task", status_code=200)
async def planner_get_task(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para planner_get_task."""
    try:
        result = await planner_actions.get_task(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: planner_update_task
@router.patch("/update_task", status_code=200)
async def planner_update_task(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para planner_update_task."""
    try:
        result = await planner_actions.update_task(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: planner_delete_task
@router.delete("/delete_task", status_code=200)
async def planner_delete_task(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para planner_delete_task."""
    try:
        result = await planner_actions.delete_task(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: planner_list_buckets
@router.get("/list_buckets", status_code=200)
async def planner_list_buckets(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para planner_list_buckets."""
    try:
        result = await planner_actions.list_buckets(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: planner_create_bucket
@router.post("/create_bucket", status_code=200)
async def planner_create_bucket(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para planner_create_bucket."""
    try:
        result = await planner_actions.create_bucket(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

