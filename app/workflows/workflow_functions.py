# app/workflows/workflow_functions.py
"""
Funciones de workflows independientes para evitar importaciones circulares
"""

import logging
from typing import Dict, Any, Optional
from .simple_workflow import execute_predefined_workflow as simple_execute, create_dynamic_workflow as simple_create, list_available_workflows as simple_list

logger = logging.getLogger(__name__)

async def execute_predefined_workflow(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """Función para ACTION_MAP - ejecutar workflow predefinido"""
    try:
        workflow_name = params.get("workflow_name", "")
        workflow_params = params.get("params", {})
        
        # Usar la versión simple que no depende de ACTION_MAP
        result = simple_execute(workflow_name, workflow_params)
        return result
    except Exception as e:
        logger.error(f"Error ejecutando workflow: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

async def create_dynamic_workflow(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """Función para ACTION_MAP - crear workflow dinámico"""
    try:
        description = params.get("description", "")
        context = params.get("context", {})
        
        # Usar la versión simple que no depende de ACTION_MAP
        result = simple_create(description, context)
        return result
    except Exception as e:
        logger.error(f"Error creando workflow dinámico: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

def list_available_workflows(client=None, params: Dict[str, Any] = None) -> Dict[str, Any]:
    """Función para ACTION_MAP - listar workflows"""
    try:
        # Usar la versión simple que no depende de ACTION_MAP
        return simple_list()
    except Exception as e:
        logger.error(f"Error listando workflows: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }
