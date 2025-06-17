# Archivo generado automáticamente por refactor_maestro.py
from fastapi import APIRouter, Depends, Body, HTTPException
from typing import Dict, Any, Optional
from app.actions import powerbi_actions
from app.dependencies import get_authenticated_http_client
from app.shared.helpers.http_client import AuthenticatedHttpClient

router = APIRouter(prefix="/powerbi", tags=["Powerbi"])

# Endpoint para: powerbi_list_reports
@router.get("/list_reports", status_code=200)
async def powerbi_list_reports(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para powerbi_list_reports."""
    try:
        result = await powerbi_actions.list_reports(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: powerbi_export_report
@router.get("/export_report", status_code=200)
async def powerbi_export_report(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para powerbi_export_report."""
    try:
        result = await powerbi_actions.export_report(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: powerbi_list_dashboards
@router.get("/list_dashboards", status_code=200)
async def powerbi_list_dashboards(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para powerbi_list_dashboards."""
    try:
        result = await powerbi_actions.list_dashboards(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: powerbi_list_datasets
@router.get("/list_datasets", status_code=200)
async def powerbi_list_datasets(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para powerbi_list_datasets."""
    try:
        result = await powerbi_actions.list_datasets(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: powerbi_refresh_dataset
@router.post("/refresh_dataset", status_code=200)
async def powerbi_refresh_dataset(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para powerbi_refresh_dataset."""
    try:
        result = await powerbi_actions.refresh_dataset(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

