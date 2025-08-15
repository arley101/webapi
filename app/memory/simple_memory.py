# app/memory/simple_memory.py
"""
Sistema de Memoria Simplificado sin dependencias circulares
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from typing import Callable, Tuple
import json

logger = logging.getLogger(__name__)

class SimpleMemoryManager:
    """Gestor simplificado de memoria"""
    
    # Backends opcionales de persistencia (inyectables desde otras capas)
    _sp_handler: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None
    _od_handler: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None
    _notion_handler: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None

    def attach_backends(
        self,
        sharepoint_handler: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
        onedrive_handler: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
        notion_handler: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
    ) -> None:
        """
        Inyecta funciones de persistencia. Cada handler recibe un payload dict y devuelve un dict
        con, idealmente, {'success': bool, 'url': str?, 'id': str?, 'details': {...}}.
        """
        if sharepoint_handler:
            self._sp_handler = sharepoint_handler
        if onedrive_handler:
            self._od_handler = onedrive_handler
        if notion_handler:
            self._notion_handler = notion_handler

    def _dispatch_persistence(self, payload: Dict[str, Any]) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """
        Decide y ejecuta persistencia opcional según 'persist_to' en payload['data'] o metadatos.
        Retorna (provider_name, result_dict) si se ejecutó, en caso contrario (None, None).
        """
        data = payload.get("data") or {}
        persist_to = (data.get("persist_to") or "").lower().strip()
        handler = None
        provider = None
        if persist_to == "sharepoint" and self._sp_handler:
            handler = self._sp_handler
            provider = "sharepoint"
        elif persist_to == "onedrive" and self._od_handler:
            handler = self._od_handler
            provider = "onedrive"
        elif persist_to == "notion" and self._notion_handler:
            handler = self._notion_handler
            provider = "notion"

        if handler is None:
            return None, None

        try:
            result = handler(data)  # se espera {'success': bool, 'url': str?, 'id': str?, ...}
            return provider, result if isinstance(result, dict) else {"success": True, "details": result}
        except Exception as e:
            logger.error(f"Error persistiendo en {provider}: {e}")
            return provider, {"success": False, "error": str(e)}

    def store(self, key: str, value: Any) -> bool:
        """Método store para compatibilidad con pruebas"""
        try:
            self.memory_storage[key] = {
                "value": value,
                "timestamp": datetime.now().isoformat()
            }
            return True
        except Exception as e:
            logger.error(f"Error almacenando en memoria: {e}")
            return False
    
    def get(self, key: str) -> Any:
        """Método get para compatibilidad con pruebas"""
        try:
            stored = self.memory_storage.get(key)
            return stored["value"] if stored else None
        except Exception as e:
            logger.error(f"Error obteniendo de memoria: {e}")
            return None

    def __init__(self):
        self.memory_storage = {}  # En memoria para simplificar
        self.sessions = {}
    
    def save_interaction(self, session_id: str, interaction_data: Dict[str, Any], user_id: Optional[str] = None) -> Dict[str, Any]:
        """Guardar interacción en memoria"""
        try:
            if session_id not in self.sessions:
                self.sessions[session_id] = []
            
            interaction = {
                "timestamp": datetime.now().isoformat(),
                "user_id": user_id,
                "data": interaction_data,
                "id": len(self.sessions[session_id]) + 1
            }
            
            # Persistencia opcional (SharePoint/OneDrive/Notion) si se indicó en data.persist_to
            provider, persist_result = self._dispatch_persistence({
                "session_id": session_id,
                "user_id": user_id,
                "data": interaction_data,
            })
            if provider:
                interaction["persistence"] = {
                    "provider": provider,
                    "result": persist_result,
                }
                # Enlazar acceso rápido si hay URL/ID
                qa = {}
                if isinstance(persist_result, dict):
                    if persist_result.get("url"):
                        qa["url"] = persist_result["url"]
                    if persist_result.get("id"):
                        qa["id"] = persist_result["id"]
                    if qa:
                        interaction.setdefault("quick_access", {}).update(qa)
            
            self.sessions[session_id].append(interaction)
            
            return {
                "success": True,
                "interaction_id": interaction["id"],
                "session_id": session_id,
                "timestamp": interaction["timestamp"]
            }
        except Exception as e:
            logger.error(f"Error guardando interacción: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_session_history(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Obtener historial de sesión"""
        try:
            if session_id not in self.sessions:
                return []
            
            return self.sessions[session_id][-limit:] if limit > 0 else self.sessions[session_id]
        except Exception as e:
            logger.error(f"Error obteniendo historial: {str(e)}")
            return []
    
    def search_interactions(self, query: str, session_id: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        """Buscar interacciones"""
        try:
            results = []
            sessions_to_search = [session_id] if session_id else list(self.sessions.keys())
            
            for sid in sessions_to_search:
                if sid in self.sessions:
                    for interaction in self.sessions[sid]:
                        # Búsqueda simple por texto
                        interaction_text = json.dumps(interaction, ensure_ascii=False).lower()
                        if query.lower() in interaction_text:
                            results.append(interaction)
                            if len(results) >= limit:
                                return results
            
            return results
        except Exception as e:
            logger.error(f"Error buscando interacciones: {str(e)}")
            return []
    
    def export_session_summary(self, session_id: str, format_type: str = "json") -> Dict[str, Any]:
        """Exportar resumen de sesión"""
        try:
            if session_id not in self.sessions:
                return {
                    "success": False,
                    "error": f"Sesión '{session_id}' no encontrada"
                }
            
            interactions = self.sessions[session_id]
            summary = {
                "session_id": session_id,
                "total_interactions": len(interactions),
                "first_interaction": interactions[0]["timestamp"] if interactions else None,
                "last_interaction": interactions[-1]["timestamp"] if interactions else None,
                "format": format_type,
                "data": interactions if format_type == "json" else str(interactions)
            }
            
            return {
                "success": True,
                "summary": summary
            }
        except Exception as e:
            logger.error(f"Error exportando resumen: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

# Instancia global
simple_memory_manager = SimpleMemoryManager()

# Funciones para ACTION_MAP
def save_memory(session_id: str, interaction_data: Dict[str, Any], user_id: Optional[str] = None) -> Dict[str, Any]:
    """Guardar memoria"""
    return simple_memory_manager.save_interaction(session_id, interaction_data, user_id)

def get_memory_history(session_id: str, limit: int = 50) -> Dict[str, Any]:
    """Obtener historial de memoria"""
    try:
        history = simple_memory_manager.get_session_history(session_id, limit)
        return {
            "success": True,
            "session_id": session_id,
            "history": history,
            "count": len(history)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def search_memory(query: str, session_id: Optional[str] = None, limit: int = 20) -> Dict[str, Any]:
    """Buscar en memoria"""
    try:
        results = simple_memory_manager.search_interactions(query, session_id, limit)
        return {
            "success": True,
            "query": query,
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def export_memory_summary(session_id: str, format_type: str = "json") -> Dict[str, Any]:
    """Exportar resumen de memoria"""
    result = simple_memory_manager.export_session_summary(session_id, format_type)
    # Asegurar estructura homogénea
    if result.get("success") and isinstance(result.get("summary"), dict):
        summary = result["summary"]
        # Si alguna interacción tuvo quick_access, exponer un atajo a la última
        try:
            interactions = summary.get("data") or []
            for item in reversed(interactions):
                qa = item.get("quick_access")
                if isinstance(qa, dict) and (qa.get("url") or qa.get("id")):
                    result.setdefault("quick_access", {}).update({k: v for k, v in qa.items() if v})
                    break
        except Exception:
            pass
    return result


# Alias para compatibilidad
SimpleMemory = SimpleMemoryManager


# Alias para compatibilidad
SimpleMemory = SimpleMemoryManager
