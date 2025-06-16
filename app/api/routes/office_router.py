# Archivo para el servicio 'office' generado automáticamente
from fastapi import APIRouter, Depends, Body, Path, Query, HTTPException, status, Response
from typing import Dict, Any, Optional
from app.actions import office_actions
from app.api.dependencies import get_authenticated_http_client
from app.shared.helpers.http_client import AuthenticatedHttpClient

router = APIRouter(prefix="/office", tags=["Office"])

# Endpoint para: office_crear_documento_word
@router.post("/crear_documento_word")
def office_crear_documento_word(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para office_crear_documento_word"""
    final_params = params or {}
    result = office_actions.crear_documento_word(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: office_reemplazar_contenido_word
@router.post("/reemplazar_contenido_word")
def office_reemplazar_contenido_word(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para office_reemplazar_contenido_word"""
    final_params = params or {}
    result = office_actions.reemplazar_contenido_word(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: office_obtener_documento_word_binario
@router.post("/obtener_documento_word_binario")
def office_obtener_documento_word_binario(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para office_obtener_documento_word_binario"""
    final_params = params or {}
    result = office_actions.obtener_documento_word_binario(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: office_crear_libro_excel
@router.post("/crear_libro_excel")
def office_crear_libro_excel(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para office_crear_libro_excel"""
    final_params = params or {}
    result = office_actions.crear_libro_excel(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: office_leer_celda_excel
@router.post("/leer_celda_excel")
def office_leer_celda_excel(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para office_leer_celda_excel"""
    final_params = params or {}
    result = office_actions.leer_celda_excel(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: office_escribir_celda_excel
@router.post("/escribir_celda_excel")
def office_escribir_celda_excel(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para office_escribir_celda_excel"""
    final_params = params or {}
    result = office_actions.escribir_celda_excel(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: office_crear_tabla_excel
@router.post("/crear_tabla_excel")
def office_crear_tabla_excel(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para office_crear_tabla_excel"""
    final_params = params or {}
    result = office_actions.crear_tabla_excel(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: office_agregar_filas_tabla_excel
@router.post("/agregar_filas_tabla_excel")
def office_agregar_filas_tabla_excel(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para office_agregar_filas_tabla_excel"""
    final_params = params or {}
    result = office_actions.agregar_filas_tabla_excel(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

