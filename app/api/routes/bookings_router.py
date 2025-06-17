# Archivo generado automáticamente por refactor_maestro.py
from fastapi import APIRouter, Depends, Body, HTTPException
from typing import Dict, Any, Optional
from app.actions import bookings_actions
from app.dependencies import get_authenticated_http_client
from app.shared.helpers.http_client import AuthenticatedHttpClient

router = APIRouter(prefix="/bookings", tags=["Bookings"])

# Endpoint para: bookings_list_businesses
@router.get("/list_businesses", status_code=200)
async def bookings_list_businesses(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para bookings_list_businesses."""
    try:
        result = await bookings_actions.list_businesses(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: bookings_get_business
@router.get("/get_business", status_code=200)
async def bookings_get_business(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para bookings_get_business."""
    try:
        result = await bookings_actions.get_business(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: bookings_list_services
@router.get("/list_services", status_code=200)
async def bookings_list_services(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para bookings_list_services."""
    try:
        result = await bookings_actions.list_services(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: bookings_list_staff
@router.get("/list_staff", status_code=200)
async def bookings_list_staff(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para bookings_list_staff."""
    try:
        result = await bookings_actions.list_staff(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: bookings_create_appointment
@router.post("/create_appointment", status_code=200)
async def bookings_create_appointment(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para bookings_create_appointment."""
    try:
        result = await bookings_actions.create_appointment(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: bookings_get_appointment
@router.get("/get_appointment", status_code=200)
async def bookings_get_appointment(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para bookings_get_appointment."""
    try:
        result = await bookings_actions.get_appointment(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: bookings_cancel_appointment
@router.delete("/cancel_appointment", status_code=200)
async def bookings_cancel_appointment(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para bookings_cancel_appointment."""
    try:
        result = await bookings_actions.cancel_appointment(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: bookings_list_appointments
@router.get("/list_appointments", status_code=200)
async def bookings_list_appointments(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para bookings_list_appointments."""
    try:
        result = await bookings_actions.list_appointments(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

