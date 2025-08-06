import json
import os
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import aiofiles
import asyncio
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class StateManager:
    """
    Gestor de estado con memoria multinivel:
    - HOT: Memoria en proceso (inmediato)
    - WARM: Archivo JSON local (rápido)
    - COLD: SharePoint/Notion (permanente)
    """
    
    def __init__(self):
        self.memory = {}  # HOT storage
        # Use a designated data directory for state backup
        data_dir = getattr(settings, "DATA_DIR", None)
        if not data_dir:
            # Fallback to ~/.app_state if DATA_DIR is not set
            data_dir = os.path.expanduser("~/.app_state")
        os.makedirs(data_dir, exist_ok=True)
        self.persistence_file = os.path.join(data_dir, "state_backup.json")  # WARM storage
        self._load_state()
        self._cleanup_task = None
        
    def _load_state(self):
        """Carga el estado desde el archivo de respaldo"""
        try:
            if os.path.exists(self.persistence_file):
                with open(self.persistence_file, 'r') as f:
                    self.memory = json.load(f)
                logger.info(f"Estado cargado: {len(self.memory)} items")
        except Exception as e:
            logger.error(f"Error cargando estado: {e}")
            self.memory = {}
    
    async def set_workflow_state(self, workflow_id: str, state: Dict[str, Any]):
        """Guarda el estado de un workflow"""
        key = f"workflow:{workflow_id}"
        self.memory[key] = {
            "data": state,
            "timestamp": datetime.utcnow().isoformat(),
            "ttl": 86400  # 24 horas
        }
        await self._persist_state()
        logger.info(f"Estado guardado para workflow: {workflow_id}")
    
    async def get_workflow_state(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Recupera el estado de un workflow"""
        key = f"workflow:{workflow_id}"
        if key in self.memory:
            entry = self.memory[key]
            # Verificar TTL
            timestamp = datetime.fromisoformat(entry["timestamp"])
            if datetime.utcnow() - timestamp < timedelta(seconds=entry.get("ttl", 86400)):
                return entry["data"]
            else:
                # Expirado
                del self.memory[key]
                await self._persist_state()
        return None
    
    async def store_resource_id(self, resource_type: str, resource_id: str, metadata: Dict[str, Any]):
        """Almacena IDs de recursos para uso posterior"""
        key = f"resource:{resource_type}:{resource_id}"
        self.memory[key] = {
            "metadata": metadata,
            "created_at": datetime.utcnow().isoformat(),
            "ttl": 604800  # 7 días
        }
        await self._persist_state()
        logger.info(f"Resource ID almacenado: {resource_type}/{resource_id}")
    
    async def get_resource_by_type(self, resource_type: str) -> List[Dict[str, Any]]:
        """Obtiene todos los recursos de un tipo"""
        resources = []
        prefix = f"resource:{resource_type}:"
        for key, value in self.memory.items():
            if key.startswith(prefix):
                resources.append({
                    "id": key.replace(prefix, ""),
                    **value
                })
        return resources
    
    async def _persist_state(self):
        """Persiste el estado en archivo"""
        try:
            async with aiofiles.open(self.persistence_file, 'w') as f:
                await f.write(json.dumps(self.memory, indent=2))
        except Exception as e:
            logger.error(f"Error persistiendo estado: {e}")
    
    async def cleanup_expired(self):
        """Limpia entradas expiradas"""
        now = datetime.utcnow()
        keys_to_delete = []
        
        for key, value in self.memory.items():
            if "timestamp" in value:
                timestamp = datetime.fromisoformat(value["timestamp"])
                ttl = value.get("ttl", 86400)
                if now - timestamp > timedelta(seconds=ttl):
                    keys_to_delete.append(key)
        
        for key in keys_to_delete:
            del self.memory[key]
        
        if keys_to_delete:
            await self._persist_state()
            logger.info(f"Limpiados {len(keys_to_delete)} items expirados")
    
    async def start_cleanup_task(self):
        """Inicia tarea de limpieza periódica"""
        async def cleanup_loop():
            while True:
                await asyncio.sleep(3600)  # Cada hora
                await self.cleanup_expired()
        
        self._cleanup_task = asyncio.create_task(cleanup_loop())
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del estado"""
        workflows = sum(1 for k in self.memory if k.startswith("workflow:"))
        resources = sum(1 for k in self.memory if k.startswith("resource:"))
        
        return {
            "total_items": len(self.memory),
            "workflows": workflows,
            "resources": resources,
            "memory_size_bytes": len(json.dumps(self.memory))
        }

# Instancia global
state_manager = StateManager()
