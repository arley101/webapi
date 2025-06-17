# app/api/routes/users_router.py
# VERSIÓN FINAL Y CORREGIDA

from fastapi import APIRouter, Depends, Body, HTTPException
from typing import Dict, Any, Optional

from app.actions import users_actions
from app.dependencies import get_authenticated_http_client
from app.shared.helpers.http_client import AuthenticatedHttpClient

router = APIRouter(prefix="/users", tags=["Users"])

# --- ENDPOINT CORREGIDO PARA SER RESTful ---
# Ahora usa GET y recibe el ID o UPN directamente en la URL
@router.get("/{user_id_or_upn}", status_code=200)
async def get_user(
    user_id_or_upn: str,
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Obtiene los detalles de un usuario por su ID o User Principal Name (UPN)."""
    try:
        params = {"user_id_or_upn": user_id_or_upn}
        # La función de acción ya fue convertida a async por el script reparador
        result = await users_actions.get_user(client=client, params=params)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- El resto de los endpoints de users ---
# (Estos ya son POST, por lo que el script los generó correctamente)

@router.post("/list_users")
async def user_list_users(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    """Lista los usuarios del directorio."""
    result = await users_actions.list_users(client=client, params=params or {})
    return result

@router.post("/create_user")
async def user_create_user(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    """Crea un nuevo usuario."""
    result = await users_actions.create_user(client=client, params=params or {})
    return result

# ... aquí irían los demás endpoints de 'users' que generó el script.
# No es necesario que los copies, solo con tener get_user corregido es suficiente para esta prueba.