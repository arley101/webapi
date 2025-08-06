from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from app.core.v3.orchestrator import orchestrator
from app.core.v3.state_manager import state_manager
from app.core.v3.event_bus import event_bus
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v3", tags=["orchestration"])

class OrchestrationRequest(BaseModel):
    """Modelo de request para orquestación"""
    prompt: str = Field(..., description="Instrucción en lenguaje natural")
    mode: str = Field("execution", description="Modo: 'execution' o 'suggestion'")
    user_id: str = Field("system", description="ID del usuario")
    context: Optional[Dict[str, Any]] = Field(None, description="Contexto adicional")

class WorkflowStatusResponse(BaseModel):
    """Respuesta de estado de workflow"""
    workflow_id: str
    status: str
    prompt: str
    created_at: str
    completed_at: Optional[str]
    result: Optional[Dict[str, Any]]

@router.post("/orchestrate", summary="Ejecutar workflow desde lenguaje natural")
async def orchestrate_workflow(
    request: OrchestrationRequest,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    Endpoint principal que reemplaza al Proxy de Vercel.
    Recibe lenguaje natural y ejecuta automáticamente.
    """
    try:
        logger.info(f"Orquestación solicitada: {request.prompt[:100]}...")
        
        # Validar modo
        if request.mode not in ["execution", "suggestion"]:
            raise HTTPException(
                status_code=400,
                detail="El modo debe ser 'execution' o 'suggestion'"
            )
        
        # Ejecutar orquestación
        result = await orchestrator.execute_natural_language(
            prompt=request.prompt,
            mode=request.mode,
            user_id=request.user_id,
            context=request.context
        )
        
        if result.get("status") == "error":
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Error desconocido")
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en orquestación: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )

@router.get("/workflow/{workflow_id}", summary="Obtener estado de workflow")
async def get_workflow_status(workflow_id: str) -> WorkflowStatusResponse:
    """
    Obtiene el estado actual de un workflow
    """
    try:
        # Obtener estado del workflow
        state = await state_manager.get_workflow_state(workflow_id)
        
        if not state:
            raise HTTPException(
                status_code=404,
                detail=f"Workflow {workflow_id} no encontrado"
            )
        
        return WorkflowStatusResponse(
            workflow_id=workflow_id,
            status=state.get("status", "unknown"),
            prompt=state.get("prompt", ""),
            created_at=state.get("created_at", ""),
            completed_at=state.get("completed_at"),
            result=state.get("result")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo estado: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )

@router.get("/workflows", summary="Listar workflows recientes")
async def list_workflows(
    limit: int = 10,
    status: Optional[str] = None
) -> Dict[str, Any]:
    """
    Lista los workflows recientes
    """
    try:
        # Obtener todos los workflows del state manager
        all_resources = await state_manager.get_resource_by_type("workflow")
        
        # Filtrar por estado si se especifica
        if status:
            workflows = [w for w in all_resources if w.get("metadata", {}).get("status") == status]
        else:
            workflows = all_resources
        
        # Ordenar por fecha y limitar
        workflows.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        workflows = workflows[:limit]
        
        return {
            "status": "success",
            "total": len(workflows),
            "workflows": workflows
        }
        
    except Exception as e:
        logger.error(f"Error listando workflows: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )

@router.get("/events/recent", summary="Obtener eventos recientes")
async def get_recent_events(count: int = 10) -> Dict[str, Any]:
    """
    Obtiene los eventos más recientes del sistema
    """
    try:
        events = event_bus.get_recent_events(count)
        
        return {
            "status": "success",
            "count": len(events),
            "events": events
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo eventos: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )

@router.get("/stats", summary="Estadísticas del sistema")
async def get_system_stats() -> Dict[str, Any]:
    """
    Obtiene estadísticas del sistema de orquestación
    """
    try:
        state_stats = state_manager.get_stats()
        
        return {
            "status": "success",
            "state_manager": state_stats,
            "event_bus": {
                "subscribers": len(event_bus.subscribers),
                "recent_events": len(event_bus.event_history)
            }
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )
