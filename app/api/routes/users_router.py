# app/api/routes/users_router.py
# VERSIÓN FINAL CON EL PARÁMETRO CORREGIDO

from fastapi import APIRouter, Depends, Body, HTTPException
from typing import Dict, Any, Optional

from app.actions import users_actions
from app.dependencies import get_authenticated_http_client
from app.shared.helpers.http_client import AuthenticatedHttpClient

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/{user_id_or_upn}", status_code=200)
async def get_user(
    user_id_or_upn: str,
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Obtiene los detalles de un usuario por su ID o User Principal Name (UPN)."""
    try:
        # --- ESTA ES LA LÍNEA CORREGIDA ---
        # Ahora pasamos el parámetro con el nombre que la función de acción espera.
        params = {"user_principal_name": user_id_or_upn}
        
        result = await users_actions.get_user(client=client, params=params)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ... (El resto del archivo no necesita cambios) ...

@router.post("/list_users")
async def user_list_users(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = await users_actions.list_users(client=client, params=params or {})
    return result

@router.post("/create_user")
async def user_create_user(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = await users_actions.create_user(client=client, params=params or {})
    return result