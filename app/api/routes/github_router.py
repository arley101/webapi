# Archivo generado automáticamente por refactor_maestro.py
from fastapi import APIRouter, Depends, Body, HTTPException
from typing import Dict, Any, Optional
from app.actions import github_actions
from app.dependencies import get_authenticated_http_client
from app.shared.helpers.http_client import AuthenticatedHttpClient

router = APIRouter(prefix="/github", tags=["Github"])

# Endpoint para: github_list_repos
@router.get("/list_repos", status_code=200)
async def github_list_repos(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para github_list_repos."""
    try:
        result = await github_actions.github_list_repos(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: github_create_issue
@router.post("/create_issue", status_code=200)
async def github_create_issue(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para github_create_issue."""
    try:
        result = await github_actions.github_create_issue(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: github_get_repo_details
@router.get("/get_repo_details", status_code=200)
async def github_get_repo_details(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para github_get_repo_details."""
    try:
        result = await github_actions.github_get_repo_details(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

