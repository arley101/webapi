# Archivo generado automáticamente por refactor_maestro.py
from fastapi import APIRouter, Depends, Body, HTTPException
from typing import Dict, Any, Optional
from app.actions import todo_actions
from app.dependencies import get_authenticated_http_client
from app.shared.helpers.http_client import AuthenticatedHttpClient

router = APIRouter(prefix="/todo", tags=["Todo"])

# Endpoint para: todo_list_task_lists
@router.get("/list_task_lists", status_code=200)
async def todo_list_task_lists(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para todo_list_task_lists."""
    try:
        result = await todo_actions.list_task_lists(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: todo_create_task_list
@router.get("/create_task_list", status_code=200)
async def todo_create_task_list(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para todo_create_task_list."""
    try:
        result = await todo_actions.create_task_list(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: todo_list_tasks
@router.get("/list_tasks", status_code=200)
async def todo_list_tasks(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para todo_list_tasks."""
    try:
        result = await todo_actions.list_tasks(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: todo_create_task
@router.post("/create_task", status_code=200)
async def todo_create_task(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para todo_create_task."""
    try:
        result = await todo_actions.create_task(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: todo_get_task
@router.get("/get_task", status_code=200)
async def todo_get_task(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para todo_get_task."""
    try:
        result = await todo_actions.get_task(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: todo_update_task
@router.patch("/update_task", status_code=200)
async def todo_update_task(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para todo_update_task."""
    try:
        result = await todo_actions.update_task(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: todo_delete_task
@router.delete("/delete_task", status_code=200)
async def todo_delete_task(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para todo_delete_task."""
    try:
        result = await todo_actions.delete_task(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

