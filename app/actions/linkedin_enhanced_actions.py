"""
LinkedIn Actions - Enhanced
Acciones mejoradas para LinkedIn con automatización profesional
"""

import os
import json
import time
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from app.shared.helpers.http_client import AuthenticatedHttpClient

logger = logging.getLogger(__name__)

# ============================================================================
# LINKEDIN PROFESSIONAL ACTIONS
# ============================================================================

async def linkedin_post_update(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Publica una actualización en LinkedIn
    
    Parámetros:
    - content: Contenido del post
    - media_urls: URLs de imágenes/videos - opcional
    - visibility: Visibilidad ("PUBLIC", "CONNECTIONS") - opcional
    - company_page_id: ID de página de empresa - opcional
    """
    try:
        content = params.get("content")
        if not content:
            return {
                "status": "error",
                "message": "Parámetro 'content' es requerido"
            }
        
        # Configurar LinkedIn API
        import requests
        
        access_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
        if not access_token:
            return {
                "status": "error",
                "message": "Token de acceso de LinkedIn no configurado"
            }
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0"
        }
        
        # Obtener el perfil del usuario para el URN
        profile_url = "https://api.linkedin.com/v2/people/~"
        profile_response = requests.get(profile_url, headers=headers)
        profile_response.raise_for_status()
        profile_data = profile_response.json()
        person_urn = f"urn:li:person:{profile_data['id']}"
        
        # Configurar el post
        visibility = params.get("visibility", "PUBLIC")
        company_page_id = params.get("company_page_id")
        
        if company_page_id:
            author_urn = f"urn:li:organization:{company_page_id}"
        else:
            author_urn = person_urn
        
        post_data = {
            "author": author_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": content
                    },
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": visibility
            }
        }
        
        # Agregar media si se proporciona
        media_urls = params.get("media_urls", [])
        if media_urls:
            # Para posts con media necesitaríamos subir primero
            post_data["specificContent"]["com.linkedin.ugc.ShareContent"]["shareMediaCategory"] = "IMAGE"
            # Aquí iría la lógica de upload de media
        
        # Publicar el post
        post_url = "https://api.linkedin.com/v2/ugcPosts"
        response = requests.post(post_url, headers=headers, json=post_data)
        response.raise_for_status()
        
        post_result = response.json()
        
        result = {
            "status": "success",
            "post": {
                "id": post_result.get("id"),
                "author": author_urn,
                "content": content,
                "visibility": visibility,
                "created_at": post_result.get("created", {}).get("time"),
                "activity_url": f"https://www.linkedin.com/feed/update/{post_result.get('id', '').replace('urn:li:ugcPost:', '')}"
            }
        }
        
        # Persistir post publicado
        await _persist_linkedin_post(client, result["post"], "published")
        
        return result
        
    except Exception as e:
        logger.error(f"Error posting LinkedIn update: {str(e)}")
        return {
            "status": "error",
            "message": f"Error al publicar en LinkedIn: {str(e)}"
        }

async def linkedin_schedule_post(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Programa una publicación en LinkedIn
    
    Parámetros:
    - content: Contenido del post
    - scheduled_time: Fecha y hora programada (ISO 8601)
    - visibility: Visibilidad del post - opcional
    - company_page_id: ID de página de empresa - opcional
    """
    try:
        content = params.get("content")
        scheduled_time = params.get("scheduled_time")
        
        if not all([content, scheduled_time]):
            return {
                "status": "error",
                "message": "Parámetros 'content' y 'scheduled_time' son requeridos"
            }
        
        # Validar fecha futura
        from datetime import datetime, timezone
        try:
            schedule_dt = datetime.fromisoformat(scheduled_time.replace('Z', '+00:00'))
            if schedule_dt <= datetime.now(timezone.utc):
                return {
                    "status": "error",
                    "message": "La fecha programada debe ser futura"
                }
        except ValueError:
            return {
                "status": "error",
                "message": "Formato de fecha inválido. Use ISO 8601"
            }
        
        # LinkedIn API no soporta programación nativa, usar sistema interno
        scheduled_post = {
            "id": f"linkedin_scheduled_{int(time.time())}",
            "content": content,
            "scheduled_time": scheduled_time,
            "visibility": params.get("visibility", "PUBLIC"),
            "company_page_id": params.get("company_page_id"),
            "status": "scheduled",
            "created_at": datetime.now().isoformat(),
            "platform": "linkedin"
        }
        
        # Persistir post programado usando STORAGE_RULES
        await _persist_scheduled_post(client, scheduled_post, "scheduled")
        
        result = {
            "status": "success",
            "scheduled_post": scheduled_post,
            "message": f"Post programado para {scheduled_time}"
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Error scheduling LinkedIn post: {str(e)}")
        return {
            "status": "error",
            "message": f"Error al programar post: {str(e)}"
        }

async def linkedin_get_engagement_metrics(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Obtiene métricas de engagement de LinkedIn
    
    Parámetros:
    - post_ids: Lista de IDs de posts - opcional
    - date_range: Rango de fechas {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}
    - company_page_id: ID de página de empresa - opcional
    """
    try:
        # Configurar LinkedIn API
        import requests
        
        access_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
        if not access_token:
            return {
                "status": "error",
                "message": "Token de acceso de LinkedIn no configurado"
            }
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0"
        }
        
        post_ids = params.get("post_ids", [])
        date_range = params.get("date_range", {})
        company_page_id = params.get("company_page_id")
        
        engagement_data = []
        
        if post_ids:
            # Obtener métricas de posts específicos
            for post_id in post_ids:
                try:
                    # Obtener estadísticas del post
                    stats_url = f"https://api.linkedin.com/v2/socialActions/{post_id}"
                    response = requests.get(stats_url, headers=headers)
                    response.raise_for_status()
                    
                    stats = response.json()
                    
                    engagement_data.append({
                        "post_id": post_id,
                        "likes": stats.get("likesSummary", {}).get("totalFirstLevelShares", 0),
                        "comments": stats.get("commentsSummary", {}).get("totalFirstLevelComments", 0),
                        "shares": stats.get("sharesSummary", {}).get("totalShares", 0),
                        "impressions": stats.get("impressions", 0),
                        "clicks": stats.get("clicks", 0)
                    })
                    
                except Exception as e:
                    logger.error(f"Error getting stats for post {post_id}: {str(e)}")
                    engagement_data.append({
                        "post_id": post_id,
                        "error": str(e)
                    })
        
        else:
            # Obtener métricas generales de la cuenta
            if company_page_id:
                # Métricas de página de empresa
                metrics_url = f"https://api.linkedin.com/v2/organizationalEntityShareStatistics"
                params_query = f"q=organizationalEntity&organizationalEntity=urn:li:organization:{company_page_id}"
            else:
                # Métricas de perfil personal
                metrics_url = "https://api.linkedin.com/v2/shares"
                params_query = "q=owners&owners=urn:li:person:~"
            
            # Agregar filtro de fechas si se proporciona
            if date_range.get("start"):
                start_timestamp = int(datetime.fromisoformat(date_range["start"]).timestamp() * 1000)
                end_timestamp = int(datetime.fromisoformat(date_range.get("end", datetime.now().strftime("%Y-%m-%d"))).timestamp() * 1000)
                params_query += f"&timeRange.start={start_timestamp}&timeRange.end={end_timestamp}"
            
            full_url = f"{metrics_url}?{params_query}"
            response = requests.get(full_url, headers=headers)
            response.raise_for_status()
            
            metrics_result = response.json()
            
            # Procesar métricas
            total_metrics = {
                "total_posts": len(metrics_result.get("elements", [])),
                "total_likes": 0,
                "total_comments": 0,
                "total_shares": 0,
                "total_impressions": 0,
                "average_engagement": 0
            }
            
            for element in metrics_result.get("elements", []):
                total_metrics["total_likes"] += element.get("totalShareStatistics", {}).get("likeCount", 0)
                total_metrics["total_comments"] += element.get("totalShareStatistics", {}).get("commentCount", 0)
                total_metrics["total_shares"] += element.get("totalShareStatistics", {}).get("shareCount", 0)
                total_metrics["total_impressions"] += element.get("totalShareStatistics", {}).get("impressionCount", 0)
            
            if total_metrics["total_posts"] > 0:
                total_engagement = total_metrics["total_likes"] + total_metrics["total_comments"] + total_metrics["total_shares"]
                total_metrics["average_engagement"] = round(total_engagement / total_metrics["total_posts"], 2)
            
            engagement_data = [total_metrics]
        
        result = {
            "status": "success",
            "metrics_count": len(engagement_data),
            "date_range": date_range,
            "engagement_data": engagement_data
        }
        
        # Persistir métricas
        await _persist_engagement_metrics(client, engagement_data, "engagement_metrics")
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting LinkedIn engagement metrics: {str(e)}")
        return {
            "status": "error",
            "message": f"Error al obtener métricas: {str(e)}"
        }

async def linkedin_send_connection_requests(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Envía solicitudes de conexión en LinkedIn
    
    Parámetros:
    - profile_urls: Lista de URLs de perfiles de LinkedIn
    - message: Mensaje personalizado - opcional
    - max_requests: Máximo número de solicitudes a enviar - opcional (default: 10)
    """
    try:
        profile_urls = params.get("profile_urls", [])
        message = params.get("message", "")
        max_requests = params.get("max_requests", 10)
        
        if not profile_urls:
            return {
                "status": "error",
                "message": "Parámetro 'profile_urls' es requerido"
            }
        
        # Configurar LinkedIn API
        import requests
        
        access_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
        if not access_token:
            return {
                "status": "error",
                "message": "Token de acceso de LinkedIn no configurado"
            }
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0"
        }
        
        connection_results = []
        sent_count = 0
        
        for profile_url in profile_urls[:max_requests]:
            try:
                # Extraer ID del perfil de la URL
                if "/in/" in profile_url:
                    profile_id = profile_url.split("/in/")[1].split("/")[0]
                else:
                    connection_results.append({
                        "profile_url": profile_url,
                        "status": "error",
                        "message": "URL de perfil inválida"
                    })
                    continue
                
                # Buscar el perfil para obtener el URN
                search_url = f"https://api.linkedin.com/v2/people/(publicProfileUrl={profile_url})"
                search_response = requests.get(search_url, headers=headers)
                
                if search_response.status_code != 200:
                    connection_results.append({
                        "profile_url": profile_url,
                        "status": "error",
                        "message": "No se pudo encontrar el perfil"
                    })
                    continue
                
                profile_data = search_response.json()
                invitee_urn = f"urn:li:person:{profile_data['id']}"
                
                # Preparar solicitud de conexión
                invitation_data = {
                    "invitee": invitee_urn,
                    "message": message
                }
                
                # Enviar solicitud de conexión
                invitation_url = "https://api.linkedin.com/v2/invitations"
                response = requests.post(invitation_url, headers=headers, json=invitation_data)
                
                if response.status_code == 201:
                    connection_results.append({
                        "profile_url": profile_url,
                        "profile_id": profile_id,
                        "status": "success",
                        "invitation_id": response.json().get("id"),
                        "sent_at": datetime.now().isoformat()
                    })
                    sent_count += 1
                else:
                    connection_results.append({
                        "profile_url": profile_url,
                        "status": "error",
                        "message": f"Error al enviar solicitud: {response.status_code}"
                    })
                
                # Pausa entre solicitudes para evitar rate limiting
                time.sleep(2)
                
            except Exception as e:
                connection_results.append({
                    "profile_url": profile_url,
                    "status": "error",
                    "message": str(e)
                })
        
        result = {
            "status": "success",
            "total_profiles": len(profile_urls),
            "sent_count": sent_count,
            "error_count": len([r for r in connection_results if r["status"] == "error"]),
            "connection_requests": connection_results
        }
        
        # Persistir solicitudes enviadas
        await _persist_connection_requests(client, connection_results, "connection_requests")
        
        return result
        
    except Exception as e:
        logger.error(f"Error sending LinkedIn connection requests: {str(e)}")
        return {
            "status": "error",
            "message": f"Error al enviar solicitudes: {str(e)}"
        }

async def linkedin_message_new_connections(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Envía mensajes a nuevas conexiones de LinkedIn
    
    Parámetros:
    - message_template: Plantilla del mensaje con variables {name}, {company}
    - connection_ids: Lista de IDs de conexiones - opcional
    - days_back: Días hacia atrás para buscar nuevas conexiones (default: 7)
    - max_messages: Máximo número de mensajes a enviar (default: 20)
    """
    try:
        message_template = params.get("message_template")
        if not message_template:
            return {
                "status": "error",
                "message": "Parámetro 'message_template' es requerido"
            }
        
        connection_ids = params.get("connection_ids", [])
        days_back = params.get("days_back", 7)
        max_messages = params.get("max_messages", 20)
        
        # Configurar LinkedIn API
        import requests
        
        access_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
        if not access_token:
            return {
                "status": "error",
                "message": "Token de acceso de LinkedIn no configurado"
            }
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0"
        }
        
        message_results = []
        sent_count = 0
        
        if not connection_ids:
            # Obtener nuevas conexiones de los últimos días
            connections_url = "https://api.linkedin.com/v2/connections"
            connections_response = requests.get(connections_url, headers=headers)
            connections_response.raise_for_status()
            
            connections_data = connections_response.json()
            
            # Filtrar conexiones recientes
            cutoff_date = datetime.now() - timedelta(days=days_back)
            
            recent_connections = []
            for connection in connections_data.get("elements", []):
                connected_at = connection.get("connectedAt", 0)
                if connected_at and datetime.fromtimestamp(connected_at / 1000) >= cutoff_date:
                    recent_connections.append(connection)
            
            connection_ids = [conn["id"] for conn in recent_connections[:max_messages]]
        
        for connection_id in connection_ids[:max_messages]:
            try:
                # Obtener detalles de la conexión
                profile_url = f"https://api.linkedin.com/v2/people/{connection_id}"
                profile_response = requests.get(profile_url, headers=headers)
                profile_response.raise_for_status()
                
                profile_data = profile_response.json()
                
                # Personalizar mensaje
                name = f"{profile_data.get('firstName', '')} {profile_data.get('lastName', '')}".strip()
                company = ""
                
                # Obtener información de empresa actual
                if profile_data.get("positions"):
                    current_position = profile_data["positions"]["values"][0] if profile_data["positions"]["values"] else {}
                    company = current_position.get("company", {}).get("name", "")
                
                personalized_message = message_template.format(
                    name=name,
                    company=company
                )
                
                # Enviar mensaje
                message_data = {
                    "recipients": [f"urn:li:person:{connection_id}"],
                    "subject": "Conectar y colaborar",
                    "body": personalized_message
                }
                
                message_url = "https://api.linkedin.com/v2/messages"
                response = requests.post(message_url, headers=headers, json=message_data)
                
                if response.status_code == 201:
                    message_results.append({
                        "connection_id": connection_id,
                        "name": name,
                        "company": company,
                        "status": "success",
                        "message_id": response.json().get("id"),
                        "sent_at": datetime.now().isoformat()
                    })
                    sent_count += 1
                else:
                    message_results.append({
                        "connection_id": connection_id,
                        "name": name,
                        "status": "error",
                        "message": f"Error al enviar mensaje: {response.status_code}"
                    })
                
                # Pausa entre mensajes
                time.sleep(3)
                
            except Exception as e:
                message_results.append({
                    "connection_id": connection_id,
                    "status": "error",
                    "message": str(e)
                })
        
        result = {
            "status": "success",
            "total_connections": len(connection_ids),
            "sent_count": sent_count,
            "error_count": len([r for r in message_results if r["status"] == "error"]),
            "messages": message_results
        }
        
        # Persistir mensajes enviados
        await _persist_linkedin_messages(client, message_results, "new_connection_messages")
        
        return result
        
    except Exception as e:
        logger.error(f"Error messaging LinkedIn connections: {str(e)}")
        return {
            "status": "error",
            "message": f"Error al enviar mensajes: {str(e)}"
        }

# ============================================================================
# FUNCIONES AUXILIARES DE PERSISTENCIA
# ============================================================================

async def _persist_linkedin_post(client: AuthenticatedHttpClient, post_data: Dict[str, Any], action: str):
    """Persiste post de LinkedIn usando STORAGE_RULES"""
    try:
        from app.memory.memory_functions import save_memory
        
        await save_memory(client, {
            "storage_type": "document",
            "file_name": f"linkedin_post_{post_data.get('id', int(time.time()))}_{action}.json",
            "content": {
                "action": action,
                "post_data": post_data,
                "timestamp": time.time(),
                "platform": "linkedin"
            },
            "tags": ["linkedin", "post", action]
        })
        
    except Exception as e:
        logger.error(f"Error persisting LinkedIn post: {str(e)}")

async def _persist_scheduled_post(client: AuthenticatedHttpClient, post_data: Dict[str, Any], action: str):
    """Persiste post programado usando STORAGE_RULES"""
    try:
        from app.memory.memory_functions import save_memory
        
        await save_memory(client, {
            "storage_type": "workflow",
            "file_name": f"linkedin_scheduled_{post_data.get('id', int(time.time()))}_{action}.json",
            "content": {
                "action": action,
                "scheduled_post": post_data,
                "timestamp": time.time(),
                "platform": "linkedin"
            },
            "tags": ["linkedin", "scheduled", "post", action]
        })
        
    except Exception as e:
        logger.error(f"Error persisting scheduled post: {str(e)}")

async def _persist_engagement_metrics(client: AuthenticatedHttpClient, metrics_data: List[Dict[str, Any]], action: str):
    """Persiste métricas de engagement usando STORAGE_RULES"""
    try:
        from app.memory.memory_functions import save_memory
        
        await save_memory(client, {
            "storage_type": "analytics",
            "file_name": f"linkedin_engagement_{int(time.time())}_{action}.json",
            "content": {
                "action": action,
                "metrics": metrics_data,
                "timestamp": time.time(),
                "platform": "linkedin"
            },
            "tags": ["linkedin", "engagement", "metrics", action]
        })
        
    except Exception as e:
        logger.error(f"Error persisting engagement metrics: {str(e)}")

async def _persist_connection_requests(client: AuthenticatedHttpClient, requests_data: List[Dict[str, Any]], action: str):
    """Persiste solicitudes de conexión usando STORAGE_RULES"""
    try:
        from app.memory.memory_functions import save_memory
        
        await save_memory(client, {
            "storage_type": "document",
            "file_name": f"linkedin_connections_{int(time.time())}_{action}.json",
            "content": {
                "action": action,
                "connection_requests": requests_data,
                "timestamp": time.time(),
                "platform": "linkedin"
            },
            "tags": ["linkedin", "connections", "requests", action]
        })
        
    except Exception as e:
        logger.error(f"Error persisting connection requests: {str(e)}")

async def _persist_linkedin_messages(client: AuthenticatedHttpClient, messages_data: List[Dict[str, Any]], action: str):
    """Persiste mensajes de LinkedIn usando STORAGE_RULES"""
    try:
        from app.memory.memory_functions import save_memory
        
        await save_memory(client, {
            "storage_type": "document",
            "file_name": f"linkedin_messages_{int(time.time())}_{action}.json",
            "content": {
                "action": action,
                "messages": messages_data,
                "timestamp": time.time(),
                "platform": "linkedin"
            },
            "tags": ["linkedin", "messages", action]
        })
        
    except Exception as e:
        logger.error(f"Error persisting LinkedIn messages: {str(e)}")
