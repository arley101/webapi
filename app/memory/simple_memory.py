# app/memory/simple_memory.py
"""
Sistema de Memoria Simplificado sin dependencias circulares
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class SimpleMemoryManager:
    """Gestor simplificado de memoria"""
    
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
    return simple_memory_manager.export_session_summary(session_id, format_type)
