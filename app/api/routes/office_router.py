# Archivo generado automáticamente por refactor_maestro.py
from fastapi import APIRouter, Depends, Body, HTTPException
from typing import Dict, Any, Optional
from app.actions import office_actions
from app.dependencies import get_authenticated_http_client
from app.shared.helpers.http_client import AuthenticatedHttpClient

router = APIRouter(prefix="/office", tags=["Office"])

# Endpoint para: office_crear_documento_word
@router.post("/crear_documento_word", status_code=200)
async def office_crear_documento_word(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para office_crear_documento_word."""
    try:
        result = await office_actions.crear_documento_word(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: office_reemplazar_contenido_word
@router.post("/reemplazar_contenido_word", status_code=200)
async def office_reemplazar_contenido_word(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para office_reemplazar_contenido_word."""
    try:
        result = await office_actions.reemplazar_contenido_word(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: office_obtener_documento_word_binario
@router.get("/obtener_documento_word_binario", status_code=200)
async def office_obtener_documento_word_binario(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para office_obtener_documento_word_binario."""
    try:
        result = await office_actions.obtener_documento_word_binario(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: office_crear_libro_excel
@router.post("/crear_libro_excel", status_code=200)
async def office_crear_libro_excel(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para office_crear_libro_excel."""
    try:
        result = await office_actions.crear_libro_excel(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: office_leer_celda_excel
@router.post("/leer_celda_excel", status_code=200)
async def office_leer_celda_excel(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para office_leer_celda_excel."""
    try:
        result = await office_actions.leer_celda_excel(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: office_escribir_celda_excel
@router.post("/escribir_celda_excel", status_code=200)
async def office_escribir_celda_excel(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para office_escribir_celda_excel."""
    try:
        result = await office_actions.escribir_celda_excel(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: office_crear_tabla_excel
@router.post("/crear_tabla_excel", status_code=200)
async def office_crear_tabla_excel(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para office_crear_tabla_excel."""
    try:
        result = await office_actions.crear_tabla_excel(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: office_agregar_filas_tabla_excel
@router.post("/agregar_filas_tabla_excel", status_code=200)
async def office_agregar_filas_tabla_excel(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para office_agregar_filas_tabla_excel."""
    try:
        result = await office_actions.agregar_filas_tabla_excel(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

