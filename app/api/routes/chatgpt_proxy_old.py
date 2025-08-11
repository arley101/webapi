# app/api/routes/chatgpt_proxy.py
"""
Endpoint especial para ChatGPT - Interface simplificada
Este endpoint recibe consultas en lenguaje natural y las convierte automáticamente
"""

import logging
from datetime import datetime
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from typing import Any, Dict, Optional
import json
import re

from app.core.action_mapper import ACTION_MAP
from app.core.auth_manager import get_auth_client
from app.actions import gemini_actions
from app.memory.simple_memory import simple_memory_manager as memory_manager

logger = logging.getLogger(__name__)
router = APIRouter()

# Mapeo inteligente de queries naturales a acciones
NATURAL_LANGUAGE_MAP = {
    # YouTube
    "subir video": "youtube_upload_video",
    "upload video": "youtube_upload_video", 
    "crear playlist": "youtube_create_playlist",
    "analytics youtube": "youtube_get_channel_analytics",
    "videos del canal": "youtube_list_channel_videos",
    "información canal": "youtube_get_channel_info",
    
    # SharePoint
    "crear lista": "sp_create_list",
    "subir documento": "sp_upload_document",
    "buscar archivos": "sp_search_list_items",
    "información sitio": "sp_get_site_info",
    
    # Email
    "enviar email": "email_send_message",
    "buscar emails": "email_search_messages",
    "leer emails": "email_list_messages",
    
    # Calendar
    "crear evento": "calendar_create_event",
    "eventos hoy": "calendar_list_events",
    "buscar reuniones": "calendar_find_meeting_times",
    
    # OneDrive
    "subir archivo": "onedrive_upload_file",
    "buscar archivos": "onedrive_search_items",
    "crear carpeta": "onedrive_create_folder",
    
    # Notion
    "crear página": "notion_create_page",
    "buscar notion": "notion_search_general",
    "crear base datos": "notion_create_database",
    
    # Google Ads
    "campañas google": "googleads_get_campaigns",
    "crear campaña": "googleads_create_campaign",
    "performance campaña": "googleads_get_campaign_performance",
    
    # Meta Ads
    "campañas facebook": "metaads_list_campaigns",
    "insights facebook": "metaads_get_insights",
    "crear campaña facebook": "metaads_create_campaign",
    
    # HubSpot
    "contactos hubspot": "hubspot_get_contacts",
    "crear contacto": "hubspot_create_contact",
    "deals hubspot": "hubspot_get_deals",
    
    # Teams
    "equipos": "teams_list_joined_teams",
    "enviar mensaje teams": "teams_send_channel_message",
    "crear chat": "teams_create_chat",
    
    # WordPress
    "crear post": "wordpress_create_post",
    "posts wordpress": "wordpress_get_posts",
    "crear página web": "wordpress_create_page",
    
    # Generales
    "listar acciones": "list_all_actions",
    "ayuda": "get_help",
    "estado sistema": "get_system_status"
}

async def process_chatgpt_query(query: str, params: dict) -> JSONResponse:
    """
    Función auxiliar para procesar queries de ChatGPT
    """
    try:
        logger.info(f"ChatGPT Query recibido: {query}")
        
        # Buscar acción correspondiente
        action_name = None
        
        # 1. Buscar coincidencia exacta en el mapa de lenguaje natural
        for phrase, action in NATURAL_LANGUAGE_MAP.items():
            if phrase in query:
                action_name = action
                break
        
        # 2. Si no encuentra, buscar palabras clave en las acciones disponibles
        if not action_name:
            query_words = query.split()
            best_match = None
            max_matches = 0
            
            for action in ACTION_MAP.keys():
                matches = sum(1 for word in query_words if word in action.lower())
                if matches > max_matches:
                    max_matches = matches
                    best_match = action
            
            if max_matches > 0:
                action_name = best_match
        
        # 3. Casos especiales para comandos de sistema
        if not action_name:
            if "listar" in query or "mostrar" in query:
                if "acciones" in query:
                    return JSONResponse({
                        "status": "success",
                        "data": {
                            "total_actions": len(ACTION_MAP),
                            "available_actions": list(ACTION_MAP.keys())[:20],
                            "natural_commands": list(NATURAL_LANGUAGE_MAP.keys())
                        },
                        "message": f"Sistema tiene {len(ACTION_MAP)} acciones disponibles",
                        "chatgpt_friendly": True
                    })
                elif "workflow" in query:
                    # Ejecutar list_workflows
                    action_name = "list_workflows"
                
            elif "ayuda" in query or "help" in query:
                return JSONResponse({
                    "status": "success", 
                    "data": {
                        "message": "Sistema ChatGPT Proxy para Elite Dynamics",
                        "examples": [
                            "listar workflows",
                            "ejecutar workflow backup_completo",
                            "guardar memoria",
                            "subir video youtube",
                            "crear campaña facebook"
                        ]
                    },
                    "chatgpt_friendly": True
                })
        
        # 4. Si aún no encuentra acción, dar sugerencias
        if not action_name:
            return JSONResponse({
                "status": "error",
                "message": f"No se pudo interpretar: '{query}'",
                "suggestions": [
                    "listar workflows",
                    "ejecutar workflow [nombre]", 
                    "guardar memoria",
                    "mostrar acciones"
                ],
                "chatgpt_friendly": True
            })
        
        # 5. Ejecutar la acción encontrada
        if action_name not in ACTION_MAP:
            return JSONResponse({
                "status": "error",
                "message": f"Acción '{action_name}' no encontrada en el sistema",
                "chatgpt_friendly": True
            })
        
        try:
            auth_client = get_auth_client()
            action_function = ACTION_MAP[action_name]
            
            logger.info(f"Ejecutando acción: {action_name} con parámetros: {params}")
            result = action_function(auth_client, params)
            
            # 🧠 GUARDAR AUTOMÁTICAMENTE EN MEMORIA PERSISTENTE
            try:
                session_id = f"chatgpt_session_{datetime.now().strftime('%Y%m%d')}"
                memory_manager.save_interaction(session_id, {
                    "category": "chatgpt_queries",
                    "query": query,
                    "action": action_name,
                    "params": params,
                    "result": result,
                    "success": result.get("status") != "error" if isinstance(result, dict) else True
                })
            except Exception as mem_error:
                logger.warning(f"Error guardando en memoria persistente: {mem_error}")
            
            # Asegurar formato de respuesta consistente
            if isinstance(result, dict):
                if result.get("status") != "error":
                    result["query_original"] = query
                    result["action_executed"] = action_name
                    result["chatgpt_friendly"] = True
                    result["session_id"] = session_id
                
                return JSONResponse(result)
            else:
                return JSONResponse({
                    "status": "success",
                    "data": result,
                    "query_original": query,
                    "action_executed": action_name,
                    "chatgpt_friendly": True,
                    "session_id": session_id
                })
        
        except Exception as e:
            logger.error(f"Error ejecutando acción {action_name}: {e}")
            return JSONResponse({
                "status": "error",
                "message": f"Error ejecutando '{action_name}': {str(e)}",
                "action_attempted": action_name,
                "chatgpt_friendly": True
            })
    
    except Exception as e:
        logger.error(f"Error general en proceso ChatGPT: {e}")
        return JSONResponse({
            "status": "error",
            "message": f"Error procesando query: {str(e)}",
            "chatgpt_friendly": True
        })

@router.get("/chatgpt")
async def chatgpt_proxy_get(query: str):
    """
    Endpoint GET para ChatGPT - Consultas rápidas via URL params
    """
    try:
        query = query.lower().strip()
        
        if not query:
            return JSONResponse({
                "status": "error",
                "message": "Se requiere un parámetro 'query'",
                "example": "GET /api/v1/chatgpt?query=listar workflows"
            })
        
        # Procesar query igual que el POST
        result = await process_chatgpt_query(query, {})
        return result
        
    except Exception as e:
        logger.error(f"Error en ChatGPT GET proxy: {e}")
        return JSONResponse({
            "status": "error",
            "message": f"Error procesando query: {str(e)}",
            "chatgpt_friendly": True
        })

@router.post("/chatgpt")
async def chatgpt_proxy(request: Request):
    """
    Endpoint POST para ChatGPT - Consultas con cuerpo JSON
    """
    try:
        body = await request.json()
        
        # Extraer query del cuerpo de la solicitud
        query = body.get("query", "").lower().strip()
        params = body.get("params", {})
        
        if not query:
            return JSONResponse({
                "status": "error",
                "message": "Se requiere un 'query' en el cuerpo de la solicitud",
                "example": {
                    "query": "subir video a youtube",
                    "params": {"file_path": "/ruta/video.mp4", "title": "Mi Video"}
                },
                "chatgpt_friendly": True
            })
        
        # Procesar query usando la función auxiliar
        result = await process_chatgpt_query(query, params)
        return result
        
    except Exception as e:
        logger.error(f"Error en ChatGPT POST proxy: {e}")
        return JSONResponse({
            "status": "error",
            "message": f"Error procesando query: {str(e)}",
            "chatgpt_friendly": True
        })
        
        # Buscar acción correspondiente
        action_name = None
        
        # 1. Buscar coincidencia exacta en el mapa de lenguaje natural
        for phrase, action in NATURAL_LANGUAGE_MAP.items():
            if phrase in query:
                action_name = action
                break
        
        # 2. Si no encuentra, buscar palabras clave en las acciones disponibles
        if not action_name:
            query_words = query.split()
            best_match = None
            max_matches = 0
            
            for action in ACTION_MAP.keys():
                matches = sum(1 for word in query_words if word in action.lower())
                if matches > max_matches:
                    max_matches = matches
                    best_match = action
            
            if max_matches > 0:
                action_name = best_match
        
        # 3. Casos especiales
        if not action_name:
            if "listar" in query or "mostrar" in query:
                if "acciones" in query:
                    return JSONResponse({
                        "status": "success",
                        "data": {
                            "total_actions": len(ACTION_MAP),
                            "available_actions": list(ACTION_MAP.keys())[:20],
                            "natural_commands": list(NATURAL_LANGUAGE_MAP.keys())
                        },
                        "message": f"Sistema tiene {len(ACTION_MAP)} acciones disponibles"
                    })
            
            elif "ayuda" in query or "help" in query:
                return JSONResponse({
                    "status": "success",
                    "data": {
                        "commands": NATURAL_LANGUAGE_MAP,
                        "total_actions": len(ACTION_MAP),
                        "example_usage": {
                            "query": "subir video a youtube",
                            "params": {"file_path": "/ruta/video.mp4", "title": "Mi Video"}
                        }
                    },
                    "message": "Lista de comandos disponibles en lenguaje natural"
                })
            
            # Si no encuentra nada, usar Gemini para interpretar
            try:
                auth_client = get_auth_client()
                gemini_result = gemini_actions.analyze_conversation_context(auth_client, {
                    "conversation_data": {
                        "request": query,
                        "available_actions": list(ACTION_MAP.keys()),
                        "context": "find_best_action"
                    }
                })
                
                if gemini_result.get("success") and gemini_result.get("data", {}).get("suggested_action"):
                    action_name = gemini_result["data"]["suggested_action"]
                    logger.info(f"Gemini sugirió acción: {action_name}")
            except Exception as e:
                logger.warning(f"Error usando Gemini para interpretar query: {e}")
        
        if not action_name:
            return JSONResponse({
                "status": "error",
                "message": f"No se pudo interpretar el query: '{query}'",
                "suggestions": [
                    "Intenta con comandos como: 'subir video', 'crear lista', 'enviar email'",
                    "O usa nombres específicos de acciones como: 'youtube_upload_video'",
                    "Envía 'ayuda' para ver todos los comandos disponibles"
                ],
                "available_commands": list(NATURAL_LANGUAGE_MAP.keys())[:10]
            })
        
        # Verificar que la acción existe
        if action_name not in ACTION_MAP:
            return JSONResponse({
                "status": "error",
                "message": f"Acción '{action_name}' no encontrada en el sistema",
                "total_actions": len(ACTION_MAP)
            })
        
        # Ejecutar la acción
        try:
            auth_client = get_auth_client()
            action_function = ACTION_MAP[action_name]
            
            logger.info(f"Ejecutando acción: {action_name} con parámetros: {params}")
            result = action_function(auth_client, params)
            
            # 🧠 GUARDAR AUTOMÁTICAMENTE EN MEMORIA PERSISTENTE
            try:
                session_id = f"chatgpt_session_{datetime.now().strftime('%Y%m%d')}"
                memory_manager.save_interaction(session_id, {
                    "category": "chatgpt_queries",
                    "query": query,
                    "action": action_name,
                    "params": params,
                    "result": result,
                    "success": result.get("status") != "error" if isinstance(result, dict) else True
                })
            except Exception as mem_error:
                logger.warning(f"Error guardando en memoria persistente: {mem_error}")
            
            # Asegurar formato de respuesta consistente
            if isinstance(result, dict):
                if result.get("status") != "error":
                    result["query_original"] = query
                    result["action_executed"] = action_name
                    result["chatgpt_friendly"] = True
                    result["session_id"] = session_id
                
                return JSONResponse(result)
            else:
                return JSONResponse({
                    "status": "success",
                    "data": result,
                    "query_original": query,
                    "action_executed": action_name,
                    "chatgpt_friendly": True,
                    "session_id": session_id
                })
        
        except Exception as e:
            logger.error(f"Error ejecutando acción {action_name}: {e}")
            return JSONResponse({
                "status": "error",
                "message": f"Error ejecutando acción: {str(e)}",
                "action_attempted": action_name,
                "query_original": query
            })
    
    except Exception as e:
        logger.error(f"Error en chatgpt_proxy: {e}")
        return JSONResponse({
            "status": "error",
            "message": f"Error procesando solicitud: {str(e)}"
        })

@router.get("/chatgpt/help")
async def chatgpt_help():
    """Endpoint de ayuda para ChatGPT"""
    return JSONResponse({
        "status": "success",
        "data": {
            "endpoint": "/api/v1/chatgpt",
            "method": "POST",
            "description": "Endpoint simplificado para ChatGPT que acepta consultas en lenguaje natural",
            "example_request": {
                "query": "subir video a youtube",
                "params": {
                    "file_path": "/ruta/al/video.mp4",
                    "title": "Mi Nuevo Video",
                    "description": "Descripción del video"
                }
            },
            "natural_commands": NATURAL_LANGUAGE_MAP,
            "total_actions_available": len(ACTION_MAP),
            "tips": [
                "Usa lenguaje natural: 'subir video', 'crear lista', 'enviar email'",
                "Incluye parámetros en 'params' cuando sea necesario",
                "Envía query 'ayuda' para ver todos los comandos",
                "El sistema puede interpretar automáticamente tus consultas"
            ]
        }
    })

@router.get("/chatgpt/actions")
async def list_actions_for_chatgpt():
    """Lista todas las acciones disponibles de forma amigable para ChatGPT"""
    
    # Organizar acciones por categoría
    categorized_actions = {}
    
    for action_name in ACTION_MAP.keys():
        # Extraer categoría del nombre de la acción
        category = action_name.split('_')[0]
        
        if category not in categorized_actions:
            categorized_actions[category] = []
        
        categorized_actions[category].append(action_name)
    
    return JSONResponse({
        "status": "success",
        "data": {
            "total_actions": len(ACTION_MAP),
            "categories": len(categorized_actions),
            "actions_by_category": categorized_actions,
            "natural_language_commands": NATURAL_LANGUAGE_MAP,
            "usage_tip": "Usa el endpoint POST /api/v1/chatgpt con queries en lenguaje natural"
        },
        "message": f"Sistema con {len(ACTION_MAP)} acciones organizadas en {len(categorized_actions)} categorías"
    })
