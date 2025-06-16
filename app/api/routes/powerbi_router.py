# Archivo para el servicio 'powerbi' generado automáticamente
from fastapi import APIRouter, Depends, Body, Path, Query, HTTPException, status, Response
from typing import Dict, Any, Optional
from app.actions import powerbi_actions
from app.api.dependencies import get_authenticated_http_client
from app.shared.helpers.http_client import AuthenticatedHttpClient

router = APIRouter(prefix="/powerbi", tags=["Powerbi"])

# Endpoint para: powerbi_list_reports
@router.post("/list_reports")
def powerbi_list_reports(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para powerbi_list_reports"""
    final_params = params or {}
    result = powerbi_actions.list_reports(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: powerbi_export_report
@router.post("/export_report")
def powerbi_export_report(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para powerbi_export_report"""
    final_params = params or {}
    result = powerbi_actions.export_report(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: powerbi_list_dashboards
@router.post("/list_dashboards")
def powerbi_list_dashboards(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para powerbi_list_dashboards"""
    final_params = params or {}
    result = powerbi_actions.list_dashboards(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: powerbi_list_datasets
@router.post("/list_datasets")
def powerbi_list_datasets(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para powerbi_list_datasets"""
    final_params = params or {}
    result = powerbi_actions.list_datasets(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: powerbi_refresh_dataset
@router.post("/refresh_dataset")
def powerbi_refresh_dataset(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para powerbi_refresh_dataset"""
    final_params = params or {}
    result = powerbi_actions.refresh_dataset(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

