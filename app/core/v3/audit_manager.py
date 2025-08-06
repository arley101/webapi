from typing import Dict, Any, Optional
from datetime import datetime
import json
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class AuditManager:
    """
    Gestor de auditoría que registra todas las operaciones en Notion
    """
    
    def __init__(self):
        self.audit_db = settings.NOTION_REGISTRY_DB
        self.enabled = bool(settings.NOTION_API_TOKEN)
        
    async def log_execution_start(self, execution_id: str, prompt: str, user_id: str, metadata: Optional[Dict] = None):
        """Registra el inicio de una ejecución"""
        if not self.enabled:
            return
            
        try:
            from app.actions import notion_actions
            
            properties = {
                "ID": {"title": [{"text": {"content": execution_id}}]},
                "Tipo": {"select": {"name": "Ejecución"}},
                "Prompt": {"rich_text": [{"text": {"content": prompt[:2000]}}]},  # Limite de Notion
                "Usuario": {"rich_text": [{"text": {"content": user_id}}]},
                "Estado": {"select": {"name": "En Progreso"}},
                "Inicio": {"date": {"start": datetime.utcnow().isoformat()}},
                "Metadata": {"rich_text": [{"text": {"content": json.dumps(metadata or {}, indent=2)[:2000]}}]}
            }
            
            result = await notion_actions.notion_create_page(None, {
                "database_id": self.audit_db,
                "properties": properties
            })
            
            if result.get("status") == "success":
                logger.info(f"Auditoría iniciada: {execution_id}")
                return result.get("data", {}).get("id")
                
        except Exception as e:
            logger.error(f"Error en auditoría: {e}")
            # No fallar si la auditoría falla
    
    async def log_execution_step(self, execution_id: str, step_name: str, status: str, details: Optional[Dict] = None):
        """Registra un paso de ejecución"""
        if not self.enabled:
            return
            
        try:
            # Aquí podrías actualizar la página existente o crear una entrada relacionada
            logger.info(f"Paso registrado: {execution_id} - {step_name} - {status}")
        except Exception as e:
            logger.error(f"Error registrando paso: {e}")
    
    async def log_execution_complete(self, execution_id: str, result: Dict[str, Any], duration_ms: Optional[int] = None):
        """Registra la finalización de una ejecución"""
        if not self.enabled:
            return
            
        try:
            from app.actions import notion_actions
            
            # Buscar la página original por ID de ejecución
            search_result = await notion_actions.notion_search_general(None, {
                "query": execution_id,
                "filter": {"property": "object", "value": "page"}
            })
            
            if search_result.get("status") == "success" and search_result.get("data", {}).get("results"):
                page_id = search_result["data"]["results"][0]["id"]
                
                # Actualizar la página
                update_props = {
                    "Estado": {"select": {"name": "Completado" if result.get("status") == "success" else "Error"}},
                    "Fin": {"date": {"start": datetime.utcnow().isoformat()}},
                    "Duración (ms)": {"number": duration_ms} if duration_ms else None,
                    "Resultado": {"rich_text": [{"text": {"content": json.dumps(result, indent=2)[:2000]}}]}
                }
                
                # Filtrar None values
                update_props = {k: v for k, v in update_props.items() if v is not None}
                
                await notion_actions.notion_update_page(None, {
                    "page_id": page_id,
                    "properties": update_props
                })
                
                logger.info(f"Auditoría completada: {execution_id}")
                
        except Exception as e:
            logger.error(f"Error completando auditoría: {e}")
    
    async def log_execution_error(self, execution_id: str, error: str, stack_trace: Optional[str] = None):
        """Registra un error de ejecución"""
        await self.log_execution_complete(execution_id, {
            "status": "error",
            "error": error,
            "stack_trace": stack_trace
        })

# Instancia global
audit_manager = AuditManager()
