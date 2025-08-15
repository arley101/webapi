# app/api/routes/workflow_manager.py
"""
🔄 CENTRO DE CONTROL DE WORKFLOWS
Interfaz para ejecutar y monitorear todos los workflows del sistema
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime
import uuid

from app.core.auth_manager import get_current_user, AuthenticatedUser
from app.workflows.auto_workflow import AutoWorkflowManager
from app.shared.helpers.response_helpers import create_success_response, create_error_response

logger = logging.getLogger(__name__)
router = APIRouter(tags=["🔄 Workflow Management"])

# Estado global de workflows en ejecución
workflow_status = {}

@router.get("/workflows", 
           summary="Listar workflows disponibles",
           description="Obtiene la lista completa de workflows predefinidos disponibles")
async def list_workflows(current_user: AuthenticatedUser = Depends(get_current_user)):
    """Lista todos los workflows disponibles"""
    try:
        workflow_manager = AutoWorkflowManager()
        workflows = workflow_manager.predefined_workflows
        
        workflow_list = []
        for key, workflow in workflows.items():
            workflow_list.append({
                "id": key,
                "name": workflow["name"],
                "description": workflow["description"],
                "total_steps": len(workflow["steps"]),
                "estimated_duration": f"{len(workflow['steps']) * 2}-{len(workflow['steps']) * 5} segundos"
            })
        
        return create_success_response(
            data={
                "workflows": workflow_list,
                "total_workflows": len(workflow_list),
                "workflow_manager_status": "active"
            },
            message=f"Se encontraron {len(workflow_list)} workflows disponibles"
        )
        
    except Exception as e:
        logger.error(f"Error listando workflows: {e}")
        return create_error_response(error=str(e), status_code=500)

@router.post("/workflows/{workflow_id}/execute",
            summary="Ejecutar workflow específico",
            description="Ejecuta un workflow predefinido con parámetros opcionales")
async def execute_workflow(
    workflow_id: str,
    background_tasks: BackgroundTasks,
    params: Dict[str, Any] = None,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Ejecuta un workflow específico"""
    try:
        workflow_manager = AutoWorkflowManager()
        
        if workflow_id not in workflow_manager.predefined_workflows:
            available_workflows = list(workflow_manager.predefined_workflows.keys())
            raise HTTPException(
                status_code=404, 
                detail=f"Workflow '{workflow_id}' no encontrado. Disponibles: {available_workflows}"
            )
        
        # Generar ID único para esta ejecución
        execution_id = str(uuid.uuid4())
        
        # Registrar inicio de ejecución
        workflow_status[execution_id] = {
            "workflow_id": workflow_id,
            "status": "iniciando",
            "started_at": datetime.now().isoformat(),
            "user_id": current_user.user_id,
            "current_step": 0,
            "total_steps": len(workflow_manager.predefined_workflows[workflow_id]["steps"]),
            "results": []
        }
        
        # Ejecutar workflow en background
        background_tasks.add_task(
            _execute_workflow_background,
            execution_id,
            workflow_id,
            params or {},
            current_user
        )
        
        return create_success_response(
            data={
                "execution_id": execution_id,
                "workflow_id": workflow_id,
                "status": "iniciado",
                "monitor_url": f"/api/v1/workflows/status/{execution_id}"
            },
            message=f"Workflow '{workflow_id}' iniciado correctamente"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ejecutando workflow {workflow_id}: {e}")
        return create_error_response(error=str(e), status_code=500)

@router.get("/workflows/status/{execution_id}",
           summary="Consultar estado de ejecución",
           description="Obtiene el estado actual de una ejecución de workflow")
async def get_workflow_status(
    execution_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Consulta el estado de una ejecución de workflow"""
    try:
        if execution_id not in workflow_status:
            raise HTTPException(
                status_code=404,
                detail=f"Ejecución '{execution_id}' no encontrada"
            )
        
        status = workflow_status[execution_id]
        
        # Verificar que el usuario puede ver este workflow
        if status["user_id"] != current_user.user_id:
            raise HTTPException(
                status_code=403,
                detail="No tienes permisos para ver esta ejecución"
            )
        
        return create_success_response(
            data=status,
            message=f"Estado del workflow: {status['status']}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error consultando estado {execution_id}: {e}")
        return create_error_response(error=str(e), status_code=500)

@router.get("/workflows/history",
           summary="Historial de ejecuciones",
           description="Obtiene el historial de ejecuciones de workflows del usuario")
async def get_workflow_history(
    limit: int = 10,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Obtiene el historial de workflows del usuario"""
    try:
        user_workflows = []
        
        for execution_id, status in workflow_status.items():
            if status["user_id"] == current_user.user_id:
                user_workflows.append({
                    "execution_id": execution_id,
                    "workflow_id": status["workflow_id"],
                    "status": status["status"],
                    "started_at": status["started_at"],
                    "current_step": status["current_step"],
                    "total_steps": status["total_steps"]
                })
        
        # Ordenar por fecha más reciente
        user_workflows.sort(key=lambda x: x["started_at"], reverse=True)
        
        # Aplicar límite
        user_workflows = user_workflows[:limit]
        
        return create_success_response(
            data={
                "executions": user_workflows,
                "total_executions": len(user_workflows),
                "showing": len(user_workflows)
            },
            message=f"Se encontraron {len(user_workflows)} ejecuciones"
        )
        
    except Exception as e:
        logger.error(f"Error obteniendo historial: {e}")
        return create_error_response(error=str(e), status_code=500)

async def _execute_workflow_background(
    execution_id: str,
    workflow_id: str,
    params: Dict[str, Any],
    current_user: AuthenticatedUser
):
    """Ejecuta el workflow en background"""
    try:
        workflow_manager = AutoWorkflowManager()
        
        # Actualizar estado a 'ejecutando'
        workflow_status[execution_id]["status"] = "ejecutando"
        
        # Ejecutar workflow
        result = await workflow_manager.execute_predefined_workflow(
            workflow_id, 
            params, 
            current_user
        )
        
        # Actualizar estado final
        workflow_status[execution_id].update({
            "status": "completado" if result.get("success") else "error",
            "completed_at": datetime.now().isoformat(),
            "final_result": result,
            "current_step": workflow_status[execution_id]["total_steps"]
        })
        
    except Exception as e:
        logger.error(f"Error en ejecución background {execution_id}: {e}")
        workflow_status[execution_id].update({
            "status": "error",
            "completed_at": datetime.now().isoformat(),
            "error": str(e)
        })
