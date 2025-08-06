import asyncio
from typing import Dict, Any, Callable, List
from datetime import datetime
import json
import logging
from app.core.v3.state_manager import state_manager

logger = logging.getLogger(__name__)

class EventBus:
    """
    Sistema de eventos para comunicación entre servicios
    Permite acciones en cascada automáticas
    """
    
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = {}
        self.event_history = []
        self.max_history = 1000
        
    async def emit(self, event_name: str, source: str, data: Dict[str, Any]):
        """Emite un evento al bus"""
        event = {
            "event_id": f"{event_name}_{datetime.utcnow().timestamp()}",
            "event_name": event_name,
            "source": source,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Guardar en historial
        self.event_history.append(event)
        if len(self.event_history) > self.max_history:
            self.event_history.pop(0)
        
        # Guardar evento importante en state manager
        if event_name in ["workflow.started", "workflow.completed", "error.critical"]:
            await state_manager.store_resource_id(
                "event",
                event["event_id"],
                event
            )
        
        logger.info(f"Evento emitido: {event_name} desde {source}")
        
        # Ejecutar suscriptores
        if event_name in self.subscribers:
            for callback in self.subscribers[event_name]:
                try:
                    asyncio.create_task(callback(event))
                except Exception as e:
                    logger.error(f"Error en callback para {event_name}: {e}")
    
    def subscribe(self, event_name: str, callback: Callable):
        """Suscribe una función a un evento"""
        if event_name not in self.subscribers:
            self.subscribers[event_name] = []
        self.subscribers[event_name].append(callback)
        logger.info(f"Suscriptor agregado para: {event_name}")
    
    def unsubscribe(self, event_name: str, callback: Callable):
        """Desuscribe una función de un evento"""
        if event_name in self.subscribers:
            self.subscribers[event_name].remove(callback)
    
    def get_recent_events(self, count: int = 10) -> List[Dict[str, Any]]:
        """Obtiene los eventos más recientes"""
        return self.event_history[-count:]
    
    def get_events_by_source(self, source: str) -> List[Dict[str, Any]]:
        """Obtiene eventos de una fuente específica"""
        return [e for e in self.event_history if e.get("source") == source]

# Instancia global
event_bus = EventBus()

# Registrar eventos de cascada predefinidos
async def setup_cascade_events():
    """Configura las cascadas automáticas"""
    
    # Cuando se sube un archivo
    async def on_file_uploaded(event: Dict[str, Any]):
        from app.actions import notion_actions
        try:
            # Crear registro en Notion automáticamente
            from app.core.settings import settings
            await notion_actions.notion_create_page({
                "api_token": settings.NOTION_API_TOKEN,
                "database_id": settings.NOTION_REGISTRY_DB,
                "properties": {
                    "Nombre": {"title": [{"text": {"content": event["data"].get("file_name", "Archivo")}}]},
                    "Tipo": {"select": {"name": "Archivo"}},
                    "URL": {"url": event["data"].get("web_url", "")},
                    "Origen": {"select": {"name": event["source"]}},
                    "Fecha": {"date": {"start": datetime.utcnow().isoformat()}}
                }
            })
            logger.info("Archivo registrado en Notion automáticamente")
        except Exception as e:
            logger.error(f"Error en cascada file.uploaded: {e}")
    
    # Cuando se completa una auditoría
    async def on_audit_completed(event: Dict[str, Any]):
        # Aquí puedes agregar lógica para:
        # - Generar reporte PDF
        # - Enviarlo por email
        # - Crear tarea de seguimiento
        logger.info("Procesando auditoría completada")
    
    # Registrar los handlers
    event_bus.subscribe("file.uploaded", on_file_uploaded)
    event_bus.subscribe("audit.completed", on_audit_completed)
