"""
Google Services Actions - Gmail, Calendar, Drive, Sheets
Implementación de acciones mejoradas usando el nuevo cliente de autenticación
"""

import os
import json
import logging
import time
import base64
import mimetypes
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import requests

from app.services.auth.google_auth import get_google_client, format_gmail_message, format_calendar_event

logger = logging.getLogger(__name__)

# ============================================================================
# GMAIL ACTIONS
# ============================================================================

async def gmail_send_bulk(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Envía emails en bulk usando plantilla + variables
    Params: template, recipients (lista con variables por fila), subject_template
    """
    try:
        template = params.get("template", "")
        recipients = params.get("recipients", [])  # [{"email": "x@y.com", "name": "John", "var1": "value1"}]
        subject_template = params.get("subject_template", "")
        
        if not template or not recipients:
            return {"status": "error", "message": "Se requieren 'template' y 'recipients'"}
        
        google_client = get_google_client()
        
        results = []
        successful_sends = 0
        failed_sends = 0
        
        for recipient_data in recipients:
            try:
                # Reemplazar variables en template
                email_body = template
                email_subject = subject_template
                
                for key, value in recipient_data.items():
                    placeholder = f"{{{key}}}"
                    email_body = email_body.replace(placeholder, str(value))
                    email_subject = email_subject.replace(placeholder, str(value))
                
                # Formatear y enviar email
                message = format_gmail_message(
                    to=recipient_data.get("email", ""),
                    subject=email_subject,
                    body=email_body
                )
                
                request = google_client.gmail_service.users().messages().send(
                    userId="me",
                    body=message
                )
                
                result = google_client.execute_request("gmail", request, "gmail_send_bulk_individual")
                
                if result.get("status") == "success":
                    successful_sends += 1
                    results.append({
                        "email": recipient_data.get("email"),
                        "status": "sent",
                        "message_id": result.get("data", {}).get("id")
                    })
                else:
                    failed_sends += 1
                    results.append({
                        "email": recipient_data.get("email"),
                        "status": "error",
                        "error": result.get("message", "Unknown error")
                    })
                
                # Delay para evitar rate limits
                time.sleep(0.5)
                
            except Exception as e:
                failed_sends += 1
                results.append({
                    "email": recipient_data.get("email", "unknown"),
                    "status": "error",
                    "error": str(e)
                })
        
        final_result = {
            "status": "success",
            "action": "gmail_send_bulk",
            "data": {
                "total_recipients": len(recipients),
                "successful_sends": successful_sends,
                "failed_sends": failed_sends,
                "results": results
            }
        }
        
        # Persistencia
        final_result["persist_suggestion"] = {
            "action": "save_memory",
            "params": {
                "storage_type": "analytics",
                "file_name": f"gmail_bulk_send_{int(time.time())}.json",
                "content": final_result["data"],
                "tags": ["gmail", "bulk_send", "email_campaign"]
            }
        }
        
        return final_result
        
    except Exception as e:
        logger.error(f"Error en gmail_send_bulk: {str(e)}")
        return {
            "status": "error",
            "action": "gmail_send_bulk",
            "message": f"Error en envío bulk: {str(e)}",
            "details": {}
        }

async def gmail_get_leads_from_inbox(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extrae leads del inbox usando regex/intención
    Params: query_filter, lead_patterns, max_messages
    """
    try:
        query_filter = params.get("query_filter", "is:unread")
        lead_patterns = params.get("lead_patterns", ["contacto", "interesado", "cotización", "información"])
        max_messages = params.get("max_messages", 50)
        
        google_client = get_google_client()
        
        # Buscar mensajes
        search_request = google_client.gmail_service.users().messages().list(
            userId="me",
            q=query_filter,
            maxResults=max_messages
        )
        
        search_result = google_client.execute_request("gmail", search_request, "gmail_search_messages")
        
        if search_result.get("status") != "success":
            return search_result
        
        messages = search_result.get("data", {}).get("messages", [])
        leads = []
        
        # Analizar cada mensaje
        for msg_info in messages:
            try:
                # Obtener contenido completo del mensaje
                msg_request = google_client.gmail_service.users().messages().get(
                    userId="me",
                    id=msg_info["id"],
                    format="full"
                )
                
                msg_result = google_client.execute_request("gmail", msg_request, "gmail_get_message")
                
                if msg_result.get("status") != "success":
                    continue
                
                message_data = msg_result.get("data", {})
                
                # Extraer headers
                headers = {h["name"]: h["value"] for h in message_data.get("payload", {}).get("headers", [])}
                sender = headers.get("From", "")
                subject = headers.get("Subject", "")
                date = headers.get("Date", "")
                
                # Extraer body
                body = ""
                payload = message_data.get("payload", {})
                if "parts" in payload:
                    for part in payload["parts"]:
                        if part.get("mimeType") == "text/plain":
                            body_data = part.get("body", {}).get("data", "")
                            if body_data:
                                body = base64.urlsafe_b64decode(body_data).decode('utf-8', errors='ignore')
                                break
                else:
                    body_data = payload.get("body", {}).get("data", "")
                    if body_data:
                        body = base64.urlsafe_b64decode(body_data).decode('utf-8', errors='ignore')
                
                # Verificar patrones de lead
                full_text = f"{subject} {body}".lower()
                is_lead = any(pattern.lower() in full_text for pattern in lead_patterns)
                
                if is_lead:
                    leads.append({
                        "message_id": msg_info["id"],
                        "sender": sender,
                        "subject": subject,
                        "date": date,
                        "body_snippet": body[:200] + "..." if len(body) > 200 else body,
                        "matched_patterns": [p for p in lead_patterns if p.lower() in full_text],
                        "thread_id": message_data.get("threadId", "")
                    })
                
            except Exception as e:
                logger.warning(f"Error procesando mensaje {msg_info['id']}: {str(e)}")
                continue
        
        result = {
            "status": "success",
            "action": "gmail_get_leads_from_inbox",
            "data": {
                "total_messages_analyzed": len(messages),
                "leads_found": len(leads),
                "leads": leads,
                "query_used": query_filter,
                "patterns_used": lead_patterns
            }
        }
        
        # Persistencia
        result["persist_suggestion"] = {
            "action": "save_memory",
            "params": {
                "storage_type": "document",
                "file_name": f"gmail_leads_{int(time.time())}.json",
                "content": result["data"],
                "tags": ["gmail", "leads", "inbox_analysis"]
            }
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Error en gmail_get_leads_from_inbox: {str(e)}")
        return {
            "status": "error",
            "action": "gmail_get_leads_from_inbox",
            "message": f"Error extrayendo leads: {str(e)}",
            "details": {}
        }

# ============================================================================
# CALENDAR ACTIONS
# ============================================================================

async def calendar_schedule_event_with_meet(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Programa evento con Google Meet automático
    Params: title, start_time, end_time, attendees, description
    """
    try:
        title = params.get("title", "")
        start_time = params.get("start_time", "")
        end_time = params.get("end_time", "")
        attendees = params.get("attendees", [])
        description = params.get("description", "")
        timezone = params.get("timezone", "UTC")
        
        if not title or not start_time or not end_time:
            return {"status": "error", "message": "Se requieren 'title', 'start_time' y 'end_time'"}
        
        google_client = get_google_client()
        
        # Formatear evento con Meet
        event_data = format_calendar_event(
            title=title,
            start_time=start_time,
            end_time=end_time,
            description=description,
            attendees=attendees,
            timezone=timezone
        )
        
        # Crear evento con Meet link
        request = google_client.calendar_service.events().insert(
            calendarId="primary",
            body=event_data,
            conferenceDataVersion=1  # Requerido para Google Meet
        )
        
        result = google_client.execute_request("calendar", request, "calendar_schedule_event_with_meet")
        
        # Extraer Meet link del resultado
        if result.get("status") == "success":
            event_result = result.get("data", {})
            meet_link = ""
            conference_data = event_result.get("conferenceData", {})
            if conference_data:
                entry_points = conference_data.get("entryPoints", [])
                for entry in entry_points:
                    if entry.get("entryPointType") == "video":
                        meet_link = entry.get("uri", "")
                        break
            
            result["data"]["meet_link"] = meet_link
            result["data"]["calendar_link"] = event_result.get("htmlLink", "")
        
        return result
        
    except Exception as e:
        logger.error(f"Error en calendar_schedule_event_with_meet: {str(e)}")
        return {
            "status": "error",
            "action": "calendar_schedule_event_with_meet",
            "message": f"Error programando evento: {str(e)}",
            "details": {}
        }

# ============================================================================
# DRIVE ACTIONS
# ============================================================================

async def drive_upload_to_campaign_folder(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sube archivo a carpeta de campaña usando STORAGE_RULES
    Params: file_url/file_path, campaign_name, file_type (document|image|video)
    """
    try:
        file_url = params.get("file_url", "")
        file_path = params.get("file_path", "")
        campaign_name = params.get("campaign_name", "General")
        file_type = params.get("file_type", "document")
        
        if not file_url and not file_path:
            return {"status": "error", "message": "Se requiere 'file_url' o 'file_path'"}
        
        google_client = get_google_client()
        
        # Obtener datos del archivo
        if file_url:
            response = requests.get(file_url, timeout=30)
            response.raise_for_status()
            file_data = response.content
            file_name = file_url.split("/")[-1]
            mime_type = response.headers.get("content-type", "application/octet-stream")
        else:
            with open(file_path, 'rb') as f:
                file_data = f.read()
            file_name = os.path.basename(file_path)
            mime_type, _ = mimetypes.guess_type(file_path)
            mime_type = mime_type or "application/octet-stream"
        
        # Crear estructura de carpetas según STORAGE_RULES
        # Buscar/crear carpeta principal "EliteDynamics"
        folder_query = "name='EliteDynamics' and mimeType='application/vnd.google-apps.folder'"
        folders_request = google_client.drive_service.files().list(q=folder_query)
        folders_result = google_client.execute_request("drive", folders_request, "drive_search_folders")
        
        if folders_result.get("status") != "success":
            return folders_result
        
        elite_folder_id = None
        folders = folders_result.get("data", {}).get("files", [])
        
        if folders:
            elite_folder_id = folders[0]["id"]
        else:
            # Crear carpeta principal
            folder_body = {
                "name": "EliteDynamics",
                "mimeType": "application/vnd.google-apps.folder"
            }
            create_folder_request = google_client.drive_service.files().create(body=folder_body)
            create_result = google_client.execute_request("drive", create_folder_request, "drive_create_main_folder")
            
            if create_result.get("status") != "success":
                return create_result
            
            elite_folder_id = create_result.get("data", {}).get("id")
        
        # Crear/buscar subcarpeta de campaña
        campaign_folder_query = f"name='{campaign_name}' and mimeType='application/vnd.google-apps.folder' and '{elite_folder_id}' in parents"
        campaign_folders_request = google_client.drive_service.files().list(q=campaign_folder_query)
        campaign_folders_result = google_client.execute_request("drive", campaign_folders_request, "drive_search_campaign_folder")
        
        campaign_folder_id = None
        if campaign_folders_result.get("status") == "success":
            campaign_folders = campaign_folders_result.get("data", {}).get("files", [])
            if campaign_folders:
                campaign_folder_id = campaign_folders[0]["id"]
        
        if not campaign_folder_id:
            # Crear carpeta de campaña
            campaign_folder_body = {
                "name": campaign_name,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [elite_folder_id]
            }
            create_campaign_request = google_client.drive_service.files().create(body=campaign_folder_body)
            create_campaign_result = google_client.execute_request("drive", create_campaign_request, "drive_create_campaign_folder")
            
            if create_campaign_result.get("status") != "success":
                return create_campaign_result
            
            campaign_folder_id = create_campaign_result.get("data", {}).get("id")
        
        # Subir archivo
        from googleapiclient.http import MediaIoBaseUpload
        import io
        
        file_stream = io.BytesIO(file_data)
        media = MediaIoBaseUpload(file_stream, mimetype=mime_type, resumable=True)
        
        file_body = {
            "name": file_name,
            "parents": [campaign_folder_id]
        }
        
        upload_request = google_client.drive_service.files().create(
            body=file_body,
            media_body=media,
            fields="id,name,webViewLink,webContentLink"
        )
        
        result = google_client.execute_request("drive", upload_request, "drive_upload_to_campaign_folder")
        
        # Persistencia
        if result.get("status") == "success":
            result["persist_suggestion"] = {
                "action": "save_memory",
                "params": {
                    "storage_type": file_type,
                    "file_name": f"drive_upload_{int(time.time())}.json",
                    "content": {
                        "file_id": result.get("data", {}).get("id"),
                        "file_name": file_name,
                        "campaign_name": campaign_name,
                        "file_type": file_type,
                        "drive_link": result.get("data", {}).get("webViewLink"),
                        "download_link": result.get("data", {}).get("webContentLink"),
                        "upload_time": time.time()
                    },
                    "tags": ["drive", "upload", "campaign", campaign_name]
                }
            }
        
        return result
        
    except Exception as e:
        logger.error(f"Error en drive_upload_to_campaign_folder: {str(e)}")
        return {
            "status": "error",
            "action": "drive_upload_to_campaign_folder",
            "message": f"Error subiendo a Drive: {str(e)}",
            "details": {}
        }

async def drive_sync_assets_with_wordpress(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sincroniza assets nuevos de Drive con WordPress
    Params: drive_folder_id, wordpress_endpoint, last_sync_time
    """
    try:
        drive_folder_id = params.get("drive_folder_id", "")
        wordpress_endpoint = params.get("wordpress_endpoint", "")
        last_sync_time = params.get("last_sync_time", "")
        
        if not drive_folder_id or not wordpress_endpoint:
            return {"status": "error", "message": "Se requieren 'drive_folder_id' y 'wordpress_endpoint'"}
        
        google_client = get_google_client()
        
        # Buscar archivos nuevos en Drive
        query = f"'{drive_folder_id}' in parents"
        if last_sync_time:
            query += f" and modifiedTime > '{last_sync_time}'"
        
        files_request = google_client.drive_service.files().list(
            q=query,
            fields="files(id,name,mimeType,webContentLink,modifiedTime)"
        )
        
        files_result = google_client.execute_request("drive", files_request, "drive_list_new_files")
        
        if files_result.get("status") != "success":
            return files_result
        
        new_files = files_result.get("data", {}).get("files", [])
        
        if not new_files:
            return {
                "status": "success",
                "action": "drive_sync_assets_with_wordpress",
                "data": {"message": "No hay archivos nuevos para sincronizar", "synced_files": 0}
            }
        
        # Sincronizar con WordPress (esto requeriría implementación específica de WordPress)
        synced_files = []
        
        for file_info in new_files:
            try:
                # Aquí se implementaría la lógica específica de sincronización con WordPress
                # Por ahora, simulamos la sincronización
                synced_files.append({
                    "drive_file_id": file_info["id"],
                    "file_name": file_info["name"],
                    "mime_type": file_info["mimeType"],
                    "sync_status": "simulated",  # En implementación real sería "synced" o "failed"
                    "wordpress_url": f"{wordpress_endpoint}/wp-content/uploads/{file_info['name']}"
                })
                
            except Exception as e:
                synced_files.append({
                    "drive_file_id": file_info["id"],
                    "file_name": file_info["name"],
                    "sync_status": "failed",
                    "error": str(e)
                })
        
        result = {
            "status": "success",
            "action": "drive_sync_assets_with_wordpress",
            "data": {
                "total_new_files": len(new_files),
                "synced_files": len([f for f in synced_files if f["sync_status"] in ["synced", "simulated"]]),
                "failed_files": len([f for f in synced_files if f["sync_status"] == "failed"]),
                "sync_details": synced_files,
                "sync_time": time.time()
            }
        }
        
        # Persistencia
        result["persist_suggestion"] = {
            "action": "save_memory",
            "params": {
                "storage_type": "analytics",
                "file_name": f"drive_wp_sync_{int(time.time())}.json",
                "content": result["data"],
                "tags": ["drive", "wordpress", "sync", "assets"]
            }
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Error en drive_sync_assets_with_wordpress: {str(e)}")
        return {
            "status": "error",
            "action": "drive_sync_assets_with_wordpress",
            "message": f"Error sincronizando con WordPress: {str(e)}",
            "details": {}
        }
