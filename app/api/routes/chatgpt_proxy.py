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
    "listar videos": "youtube_list_videos",
    "descargar video": "youtube_download_video",
    
    # SharePoint
    "crear sitio": "crear_sitio_sharepoint",
    "listar sitios": "listar_sitios_sharepoint",
    "subir archivo": "subir_archivo_sharepoint",
    
    # Teams
    "crear equipo": "crear_equipo_teams",
    "listar equipos": "listar_equipos_teams",
    "enviar mensaje": "enviar_mensaje_teams",
    
    # OneDrive
    "listar archivos": "listar_archivos_onedrive",
    "subir onedrive": "subir_archivo_onedrive",
    "crear carpeta": "crear_carpeta_onedrive",
    
    # Meta/Facebook
    "crear campaña facebook": "metaads_create_campaign",
    "crear campaña meta": "metaads_create_campaign",
    "listar campañas": "listar_campanas_meta",
    
    # Correo
    "enviar correo": "enviar_correo_outlook",
    "leer correos": "leer_correos_outlook",
    "crear contacto": "crear_contacto_outlook",
    
    # Workflows  
    "listar workflows": "list_workflows",
    "ejecutar workflow": "execute_workflow",
    "crear workflow": "create_workflow",
    
    # Memoria
    "guardar memoria": "save_memory",
    "buscar memoria": "search_memory",
    "historial memoria": "get_memory_history",
    
    # Sistema
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
        
        # 3. Casos especiales y extracción de parámetros
        extracted_params = {}
        
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
        
        # 4. Extraer parámetros específicos según la acción
        if action_name == "execute_workflow" or "ejecutar workflow" in query:
            action_name = "execute_workflow"
            # Extraer nombre del workflow
            if "backup_completo" in query:
                extracted_params["workflow_name"] = "backup_completo"
            elif "sync_marketing" in query:
                extracted_params["workflow_name"] = "sync_marketing"
            elif "content_creation" in query:
                extracted_params["workflow_name"] = "content_creation"
            
        elif action_name == "save_memory" or "guardar memoria" in query:
            action_name = "save_memory"
            # Extraer datos para guardar
            memory_data = query.replace("guardar memoria", "").strip()
            if memory_data:
                extracted_params["data"] = {"content": memory_data, "timestamp": datetime.now().isoformat()}
        
        # Combinar parámetros extraídos con los proporcionados
        params.update(extracted_params)
        
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
            
            # Ejecutar la función correctamente según si es async o sync
            import asyncio
            if asyncio.iscoroutinefunction(action_function):
                result = await action_function(auth_client, params)
            else:
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
async def chatgpt_proxy_post(request: Request):
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

@router.get("/chatgpt/help")
async def chatgpt_help():
    """Endpoint de ayuda para ChatGPT"""
    return JSONResponse({
        "status": "success",
        "data": {
            "title": "ChatGPT Proxy - Elite Dynamics API",
            "description": "Convierte consultas en lenguaje natural a acciones de API",
            "endpoint": "/api/v1/chatgpt",
            "methods": ["GET", "POST"],
            "examples": [
                {
                    "query": "listar workflows",
                    "method": "GET",
                    "url": "/api/v1/chatgpt?query=listar workflows"
                },
                {
                    "query": "ejecutar workflow backup_completo",
                    "method": "POST",
                    "body": {"query": "ejecutar workflow backup_completo", "params": {}}
                }
            ],
            "available_commands": list(NATURAL_LANGUAGE_MAP.keys())[:10]
        },
        "chatgpt_friendly": True
    })

@router.get("/chatgpt/actions")
async def chatgpt_actions():
    """Lista todas las acciones disponibles"""
    return JSONResponse({
        "status": "success",
        "data": {
            "total_actions": len(ACTION_MAP),
            "natural_language_commands": len(NATURAL_LANGUAGE_MAP),
            "available_commands": list(NATURAL_LANGUAGE_MAP.keys()),
            "sample_actions": list(ACTION_MAP.keys())[:20]
        },
        "message": f"Sistema tiene {len(ACTION_MAP)} acciones y {len(NATURAL_LANGUAGE_MAP)} comandos en lenguaje natural",
        "chatgpt_friendly": True
    })
