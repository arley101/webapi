# app/api/routes/facade_routes.py
import logging
from fastapi import APIRouter, Depends, HTTPException, Body, Response
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List, Union

from app.core.action_mapper import ACTION_MAP
from app.dependencies import get_authenticated_http_client
from app.shared.helpers.http_client import AuthenticatedHttpClient

logger = logging.getLogger(__name__)
router = APIRouter()

# =================================================================
# MODELOS DE DATOS (PYDANTIC) PARA LOS PARÁMETROS DE LA FACHADA
# =================================================================

# --- Modelos para Correo ---
class EmailSendMessageParams(BaseModel):
    mailbox: str = Field(..., description="UPN del buzón remitente.")
    to_recipients: List[Dict] = Field(..., description="Lista de destinatarios. Ej: [{'emailAddress': {'address': 'user@example.com'}}]")
    subject: str = Field(..., description="Asunto del correo.")
    body_content: str = Field(..., description="Cuerpo del correo.")
    body_type: str = Field("HTML", description="Tipo de contenido del cuerpo (HTML o TEXT).")

class EmailListMessagesParams(BaseModel):
    mailbox: str = Field(..., description="UPN del buzón a consultar.")
    folder_id: Optional[str] = Field(None, description="ID de la carpeta. Por defecto, la bandeja de entrada.")
    max_items_total: int = Field(25, description="Número máximo de mensajes a devolver.")
    
class EmailGetDeleteParams(BaseModel):
    mailbox: str = Field(..., description="UPN del buzón.")
    message_id: str = Field(..., description="ID del mensaje a obtener o eliminar.")

# --- Modelos para Calendario ---
class CalendarListEventsParams(BaseModel):
    mailbox: str = Field(..., description="UPN del usuario cuyo calendario se va a consultar.")
    start_datetime: str = Field(..., description="Fecha y hora de inicio en formato ISO 8601 (ej: '2025-06-20T10:00:00Z').")
    end_datetime: str = Field(..., description="Fecha y hora de fin en formato ISO 8601.")

class CalendarCreateEventParams(BaseModel):
    mailbox: str = Field(..., description="UPN del buzón donde se creará el evento.")
    event_payload: Dict[str, Any] = Field(..., description="Objeto completo del evento con subject, start, end, attendees, etc.")

class CalendarGetDeleteParams(BaseModel):
    mailbox: str = Field(..., description="UPN del buzón.")
    event_id: str = Field(..., description="ID del evento a obtener o eliminar.")

# --- Modelos para OneDrive ---
class OneDriveListItemsParams(BaseModel):
    user_id: str = Field(..., description="ID o UPN del usuario de OneDrive.")
    ruta: str = Field("/", description="Ruta de la carpeta a listar. Default: raíz.")
    max_items_total: int = 50

class OneDriveFileParams(BaseModel):
    user_id: str = Field(..., description="ID o UPN del usuario de OneDrive.")
    item_id_or_path: str = Field(..., description="ID o ruta completa del archivo/carpeta.")
    
class OneDriveUploadParams(BaseModel):
    user_id: str
    nombre_archivo: str
    ruta_destino_relativa: str = "/"
    contenido_bytes: str = Field(..., description="Contenido del archivo codificado en Base64.", format="byte")

# --- Modelos para SharePoint ---
class SharePointListItemsParams(BaseModel):
    site_identifier: str = Field(..., description="ID o nombre del sitio de SharePoint.")
    lista_id_o_nombre: str = Field(..., description="ID o nombre de la lista.")
    max_items_total: int = 50

class SharePointGetItemParams(BaseModel):
    site_identifier: str
    lista_id_o_nombre: str
    item_id: str

class SharePointAddItemParams(BaseModel):
    site_identifier: str
    lista_id_o_nombre: str
    datos_campos: Dict[str, Any] = Field(..., description="Diccionario con los campos y valores del nuevo item.")

class SharePointFileParams(BaseModel):
    site_identifier: str
    drive_id_or_name: Optional[str] = Field(None, description="Nombre o ID de la biblioteca de documentos. Default: 'Documents'.")
    item_id_or_path: str

# =================================================================
# RUTAS DE LA FACHADA
# =================================================================

async def _call_action(action_name: str, client: AuthenticatedHttpClient, params: Dict[str, Any]):
    """Helper interno para llamar a la lógica original."""
    action_function = ACTION_MAP.get(action_name)
    if not action_function:
        raise HTTPException(status_code=500, detail=f"Acción interna '{action_name}' no encontrada en ACTION_MAP.")
    
    logger.info(f"Fachada llamando a la acción interna: '{action_name}'")
    result = action_function(client, params)
    
    # Manejar diferentes tipos de resultados devueltos por las acciones
    if isinstance(result, bytes):
        return Response(content=result, media_type="application/octet-stream")
    if isinstance(result, str): # Para casos como exportación a CSV
        return Response(content=result, media_type="text/plain")
    if isinstance(result, dict) and result.get("status") == "error":
        status_code = result.get("http_status", 500)
        raise HTTPException(status_code=status_code, detail=result)
        
    return result

# --- Rutas para Correo ---
@router.post("/correo/enviar", summary="Enviar un correo")
async def facade_send_email(params: EmailSendMessageParams, client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)):
    return await _call_action("email_send_message", client, params.model_dump())

@router.post("/correo/listar", summary="Listar correos de una carpeta")
async def facade_list_messages(params: EmailListMessagesParams, client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)):
    return await _call_action("email_list_messages", client, params.model_dump())

@router.post("/correo/obtener", summary="Obtener un correo por su ID")
async def facade_get_message(params: EmailGetDeleteParams, client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)):
    return await _call_action("email_get_message", client, params.model_dump())

@router.post("/correo/eliminar", summary="Eliminar un correo por su ID")
async def facade_delete_message(params: EmailGetDeleteParams, client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)):
    return await _call_action("email_delete_message", client, params.model_dump())

# --- Rutas para Calendario ---
@router.post("/calendario/listar_eventos", summary="Listar eventos de un calendario")
async def facade_list_events(params: CalendarListEventsParams, client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)):
    return await _call_action("calendar_list_events", client, params.model_dump())

@router.post("/calendario/crear_evento", summary="Crear un nuevo evento")
async def facade_create_event(params: CalendarCreateEventParams, client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)):
    return await _call_action("calendar_create_event", client, params.model_dump())

@router.post("/calendario/obtener_evento", summary="Obtener un evento por su ID")
async def facade_get_event(params: CalendarGetDeleteParams, client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)):
    return await _call_action("calendar_get_event", client, params.model_dump())

@router.post("/calendario/eliminar_evento", summary="Eliminar un evento por su ID")
async def facade_delete_event(params: CalendarGetDeleteParams, client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)):
    return await _call_action("calendar_delete_event", client, params.model_dump())

# --- Rutas para OneDrive ---
@router.post("/onedrive/listar_archivos", summary="Listar archivos en una carpeta de OneDrive")
async def facade_list_onedrive_items(params: OneDriveListItemsParams, client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)):
    return await _call_action("onedrive_list_items", client, params.model_dump())

@router.post("/onedrive/descargar_archivo", summary="Descargar un archivo de OneDrive")
async def facade_download_onedrive_file(params: OneDriveFileParams, client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)):
    return await _call_action("onedrive_download_file", client, params.model_dump())

@router.post("/onedrive/eliminar_archivo", summary="Eliminar un archivo de OneDrive")
async def facade_delete_onedrive_item(params: OneDriveFileParams, client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)):
    return await _call_action("onedrive_delete_item", client, params.model_dump())

# --- Rutas para SharePoint ---
@router.post("/sharepoint/listar_items_lista", summary="Listar items de una lista de SharePoint")
async def facade_sp_list_items(params: SharePointListItemsParams, client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)):
    return await _call_action("sp_list_list_items", client, params.model_dump())

@router.post("/sharepoint/agregar_item_lista", summary="Agregar un item a una lista de SharePoint")
async def facade_sp_add_item(params: SharePointAddItemParams, client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)):
    return await _call_action("sp_add_list_item", client, params.model_dump())

@router.post("/sharepoint/descargar_documento", summary="Descargar un documento de SharePoint")
async def facade_sp_download_doc(params: SharePointFileParams, client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)):
    return await _call_action("sp_download_document", client, params.model_dump())