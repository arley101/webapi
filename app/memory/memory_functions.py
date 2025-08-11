# app/memory/memory_functions.py
"""
Funciones de memoria independientes para evitar importaciones circulares
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from .simple_memory import save_memory as simple_save, get_memory_history as simple_get, search_memory as simple_search, export_memory_summary as simple_export

logger = logging.getLogger(__name__)

async def save_memory(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """Función para ACTION_MAP - guardar memoria"""
    try:
        session_id = params.get("session_id", f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        interaction_data = params.get("data", params)
        user_id = params.get("user_id")
        
        result = simple_save(session_id, interaction_data, user_id)
        return result
    except Exception as e:
        logger.error(f"Error guardando memoria: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

async def get_memory_history(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """Función para ACTION_MAP - obtener historial de memoria"""
    try:
        session_id = params.get("session_id", f"session_{datetime.now().strftime('%Y%m%d')}")
        limit = params.get("limit", 50)
        
        result = simple_get(session_id, limit)
        return result
    except Exception as e:
        logger.error(f"Error obteniendo historial: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

async def search_memory(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """Función para ACTION_MAP - buscar en memoria"""
    try:
        query = params.get("query", "")
        session_id = params.get("session_id")
        limit = params.get("limit", 20)
        
        result = simple_search(query, session_id, limit)
        return result
    except Exception as e:
        logger.error(f"Error buscando en memoria: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

def export_memory_summary(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """Función para ACTION_MAP - exportar resumen de memoria"""
    try:
        session_id = params.get("session_id", f"session_{datetime.now().strftime('%Y%m%d')}")
        format_type = params.get("format", "json")
        
        result = simple_export(session_id, format_type)
        return result
    except Exception as e:
        logger.error(f"Error exportando resumen: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }
