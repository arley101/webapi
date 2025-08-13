# app/memory/persistent_memory.py
"""
Sistema de Memoria Persistente Simplificado para ChatGPT
Guarda automáticamente todas las interacciones y resultados importantes
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import hashlib

from app.core.auth_manager import get_auth_client
from app.actions import sharepoint_actions
from app.actions import notion_actions

# OneDrive es opcional; si no existe el módulo no rompemos
try:
    from app.actions import onedrive_actions
except Exception:
    onedrive_actions = None

# Reglas opcionales de almacenamiento (si existen)
try:
    from app.core.storage_rules import STORAGE_RULES  # recomendado
except Exception:
    try:
        from app.core.config import STORAGE_RULES  # alternativa
    except Exception:
        STORAGE_RULES = {}

logger = logging.getLogger(__name__)

class PersistentMemoryManager:
    """Gestor de memoria persistente automática"""
    
    def __init__(self):
        self.memory_config = {
            "sharepoint_list": "Elite_Memory_Store",
            "notion_database": "Elite Memory Dashboard", 
            "auto_save_threshold": 1024,  # 1KB
            "categories": [
                "chatgpt_queries",
                "workflow_results", 
                "api_responses",
                "user_interactions",
                "system_events",
                "errors_and_debugging"
            ]
        }
        
        self.session_id = self._generate_session_id()
        self.interactions_count = 0
    
    def save_interaction(self, interaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Guarda una interacción en memoria persistente"""
        try:
            auth_client = get_auth_client()
            self.interactions_count += 1

            # Preparar datos para guardar
            memory_entry = {
                "session_id": self.session_id,
                "interaction_id": self.interactions_count,
                "timestamp": datetime.now().isoformat(),
                "category": interaction_data.get("category", "user_interactions"),
                "query_original": interaction_data.get("query", ""),
                "action_executed": interaction_data.get("action", ""),
                "parameters_used": interaction_data.get("params", {}),
                "result_summary": self._summarize_result(interaction_data.get("result", {})),
                "success": interaction_data.get("success", True),
                "response_size": len(json.dumps(interaction_data.get("result", {})))
            }

            # Detectar pista de almacenamiento (bucket) si viene en el payload o en params
            params_in = interaction_data.get("params", {}) if isinstance(interaction_data.get("params"), dict) else {}
            storage_type = interaction_data.get("storage_type") or params_in.get("storage_type") or params_in.get("resource_type")
            if storage_type:
                memory_entry["storage_type"] = storage_type

            # Aplicar STORAGE_RULES (si existen) y ejecutar persistencia específica por plataforma
            rule = STORAGE_RULES.get(storage_type, {}) if storage_type and isinstance(STORAGE_RULES, dict) else {}
            sp_result = {}
            od_result = {}

            # 1) OneDrive (primario) — subir/guardar recurso si hay path definido y handler disponible
            if isinstance(rule, dict) and rule.get("primary") == "onedrive" and onedrive_actions:
                try:
                    target_path = rule.get("path")  # ej. "/EliteDynamics/Videos"
                    # Buscamos un handler conocido en onedrive_actions
                    od_handler = None
                    for name in ("upload_file", "save_file", "save_resource", "create_file", "upload_binary"):
                        od_handler = getattr(onedrive_actions, name, None)
                        if callable(od_handler):
                            break
                    if callable(od_handler) and target_path:
                        od_payload = {
                            "path": target_path,
                            "file_name": interaction_data.get("file_name") or interaction_data.get("title") or f"int_{self.session_id}_{self.interactions_count}.json",
                            "content": interaction_data.get("content") or json.dumps(interaction_data.get("result", {})),
                            "metadata": {
                                "session_id": self.session_id,
                                "interaction_id": self.interactions_count,
                                "category": memory_entry.get("category"),
                                "storage_type": storage_type
                            }
                        }
                        od_result = od_handler(auth_client, od_payload)  # se espera dict con success/url/id
                except Exception as e:
                    logger.error(f"Error guardando en OneDrive: {e}")

            # 2) SharePoint — índice en lista (siempre) y opcionalmente subida si la regla lo pide
            list_override = None
            if isinstance(rule, dict) and rule.get("primary") == "sharepoint":
                list_override = rule.get("list") or self.memory_config["sharepoint_list"]
                # Si hay 'path' y existe un handler de subida de archivos, intentamos además subir archivo
                try:
                    sp_upload = getattr(sharepoint_actions, "upload_file", None)
                    if callable(sp_upload) and rule.get("path"):
                        upload_payload = {
                            "site_path": rule.get("path"),
                            "file_name": interaction_data.get("file_name") or interaction_data.get("title") or f"int_{self.session_id}_{self.interactions_count}.json",
                            "content": interaction_data.get("content") or json.dumps(interaction_data.get("result", {})),
                            "metadata": {
                                "session_id": self.session_id,
                                "interaction_id": self.interactions_count,
                                "category": memory_entry.get("category"),
                                "storage_type": storage_type
                            }
                        }
                        # no bloqueamos si falla, seguimos con el índice
                        _ = sp_upload(auth_client, upload_payload)
                except Exception as e:
                    logger.error(f"Error subiendo archivo a SharePoint: {e}")

            # Crear/actualizar índice en lista de SharePoint (genérico)
            sp_result = self._save_to_sharepoint(auth_client, memory_entry, list_override=list_override)

            # 3) Notion — override de base de datos si la regla lo indica (report/campaign_data/analytics)
            notion_db_override = None
            if isinstance(rule, dict) and rule.get("primary") == "notion" and rule.get("database"):
                notion_db_override = rule.get("database")
            notion_result = self._save_summary_to_notion(auth_client, memory_entry, database_override=notion_db_override)

            return {
                "status": "success",
                "message": "Interacción guardada en memoria persistente",
                "session_id": self.session_id,
                "interaction_id": self.interactions_count,
                "storage_locations": {
                    "sharepoint": sp_result.get("success", False) if isinstance(sp_result, dict) else False,
                    "onedrive": od_result.get("success", False) if isinstance(od_result, dict) else False,
                    "notion": notion_result.get("success", False) if isinstance(notion_result, dict) else False
                },
                "quick_access": ({
                    **({"sharepoint_id": (sp_result.get("data") or sp_result).get("id")} if isinstance(sp_result, dict) and ((sp_result.get("data") or {}).get("id") or sp_result.get("id")) else {}),
                    **({"sharepoint_url": (sp_result.get("data") or sp_result).get("webUrl") or (sp_result.get("data") or sp_result).get("url")} if isinstance(sp_result, dict) else {}),
                    **({"onedrive_id": od_result.get("id")} if isinstance(od_result, dict) and od_result.get("id") else {}),
                    **({"onedrive_url": od_result.get("webUrl") or od_result.get("url")} if isinstance(od_result, dict) else {}),
                    **({"notion_page_id": notion_result.get("page_id") or notion_result.get("id")} if isinstance(notion_result, dict) else {}),
                    **({"notion_page_url": notion_result.get("url")} if isinstance(notion_result, dict) and notion_result.get("url") else {}),
                } or None)
            }
        except Exception as e:
            logger.error(f"Error guardando en memoria persistente: {e}")
            return {
                "status": "error",
                "message": f"Error guardando memoria: {str(e)}"
            }
    
    def get_session_history(self, limit: int = 50) -> Dict[str, Any]:
        """Obtiene el historial de la sesión actual"""
        
        try:
            auth_client = get_auth_client()
            
            # Buscar en SharePoint
            search_result = sharepoint_actions.search_list_items(auth_client, {
                "list_name": self.memory_config["sharepoint_list"],
                "search_query": f"session_id:{self.session_id}",
                "top": limit
            })
            
            if search_result.get("success"):
                return {
                    "status": "success",
                    "session_id": self.session_id,
                    "interactions_count": self.interactions_count,
                    "history": search_result.get("data", [])
                }
            else:
                return {
                    "status": "error",
                    "message": "No se pudo recuperar historial de sesión"
                }
                
        except Exception as e:
            logger.error(f"Error obteniendo historial: {e}")
            return {
                "status": "error",
                "message": f"Error obteniendo historial: {str(e)}"
            }
    
    def search_memory(self, query: str, category: str = None) -> Dict[str, Any]:
        """Busca en la memoria persistente"""
        
        try:
            auth_client = get_auth_client()
            
            # Construir query de búsqueda
            search_query = query
            if category:
                search_query += f" category:{category}"
            
            # Buscar en SharePoint
            search_result = sharepoint_actions.search_list_items(auth_client, {
                "list_name": self.memory_config["sharepoint_list"],
                "search_query": search_query,
                "top": 100
            })
            
            return {
                "status": "success",
                "query": query,
                "category": category,
                "results": search_result.get("data", []),
                "total_found": len(search_result.get("data", []))
            }
            
        except Exception as e:
            logger.error(f"Error buscando en memoria: {e}")
            return {
                "status": "error",
                "message": f"Error buscando: {str(e)}"
            }
    
    def export_session_summary(self) -> Dict[str, Any]:
        """Exporta un resumen de la sesión actual"""
        
        try:
            auth_client = get_auth_client()
            
            # Obtener historial completo
            history = self.get_session_history(limit=1000)
            
            if not history.get("status") == "success":
                return history
            
            # Generar resumen
            interactions = history.get("history", [])
            summary = {
                "session_id": self.session_id,
                "start_time": interactions[0].get("timestamp") if interactions else None,
                "end_time": datetime.now().isoformat(),
                "total_interactions": len(interactions),
                "successful_interactions": len([i for i in interactions if i.get("success")]),
                "failed_interactions": len([i for i in interactions if not i.get("success")]),
                "categories_used": list(set([i.get("category") for i in interactions])),
                "actions_executed": list(set([i.get("action_executed") for i in interactions if i.get("action_executed")])),
                "average_response_size": sum([i.get("response_size", 0) for i in interactions]) / len(interactions) if interactions else 0
            }
            
            # Guardar resumen en Notion
            notion_result = notion_actions.create_page_in_database(auth_client, {
                "database_name": "Elite Session Summaries",
                "properties": {
                    "Session ID": {"title": [{"text": {"content": self.session_id}}]},
                    "Date": {"date": {"start": datetime.now().strftime('%Y-%m-%d')}},
                    "Interactions": {"number": summary["total_interactions"]},
                    "Success Rate": {"number": round((summary["successful_interactions"] / summary["total_interactions"]) * 100, 2) if summary["total_interactions"] > 0 else 0},
                    "Categories": {"multi_select": [{"name": cat} for cat in summary["categories_used"][:5]]},
                    "Status": {"select": {"name": "Completed"}}
                }
            })
            
            return {
                "status": "success",
                "summary": summary,
                "saved_to_notion": notion_result.get("success", False),
                "export_time": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error exportando resumen: {e}")
            return {
                "status": "error", 
                "message": f"Error exportando: {str(e)}"
            }
    
    def _save_to_sharepoint(self, auth_client, memory_entry: Dict[str, Any], list_override: Optional[str] = None) -> Dict[str, Any]:
        """Guarda entrada en SharePoint"""
        
        target_list = (list_override or self.memory_config["sharepoint_list"])
        
        try:
            # Asegurar que la lista existe
            list_result = sharepoint_actions.create_list(auth_client, {
                "list_name": target_list,
                "description": "Elite Dynamics Memory Store - Automated Storage",
                "template": "GenericList"
            })
            
            # Agregar item a la lista
            item_result = sharepoint_actions.add_list_item(auth_client, {
                "list_name": target_list,
                "item_data": {
                    "Title": f"Session_{memory_entry['session_id']}_Int_{memory_entry['interaction_id']}",
                    "SessionID": memory_entry["session_id"],
                    "InteractionID": memory_entry["interaction_id"],
                    "Timestamp": memory_entry["timestamp"],
                    "Category": memory_entry["category"],
                    "QueryOriginal": memory_entry["query_original"][:255],  # SharePoint text limit
                    "ActionExecuted": memory_entry["action_executed"],
                    "Success": memory_entry["success"],
                    "ResponseSize": memory_entry["response_size"],
                    "ResultSummary": json.dumps(memory_entry["result_summary"])[:2000]  # Limit for SharePoint
                }
            })
            
            return item_result
            
        except Exception as e:
            logger.error(f"Error guardando en SharePoint: {e}")
            return {"success": False, "error": str(e)}
    
    def _save_summary_to_notion(self, auth_client, memory_entry: Dict[str, Any], database_override: Optional[str] = None) -> Dict[str, Any]:
        """Guarda resumen en Notion"""
        try:
            # Solo guardar cada 10 interacciones para no saturar Notion
            if self.interactions_count % 10 != 0:
                return {"success": True, "skipped": True}

            target_db = (database_override or self.memory_config["notion_database"])
            notion_result = notion_actions.create_page_in_database(auth_client, {
                "database_name": target_db,
                "properties": {
                    "Title": {"title": [{"text": {"content": f"Session {self.session_id} - Interaction {memory_entry['interaction_id']}"}}]},
                    "Session ID": {"rich_text": [{"text": {"content": memory_entry["session_id"]}}]},
                    "Category": {"select": {"name": memory_entry["category"]}},
                    "Success": {"checkbox": memory_entry["success"]},
                    "Timestamp": {"date": {"start": memory_entry["timestamp"][:10]}},
                    "Action": {"rich_text": [{"text": {"content": memory_entry["action_executed"][:100]}}]},
                    "Response Size": {"number": memory_entry["response_size"]}
                }
            })

            return notion_result
        except Exception as e:
            logger.error(f"Error guardando en Notion: {e}")
            return {"success": False, "error": str(e)}
    
    def _summarize_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Crea un resumen del resultado para almacenamiento"""
        
        if not isinstance(result, dict):
            return {"type": type(result).__name__, "content": str(result)[:200]}
        
        summary = {
            "status": result.get("status", "unknown"),
            "has_data": bool(result.get("data")),
            "data_type": type(result.get("data", None)).__name__,
            "message": result.get("message", "")[:200],
            "http_status": result.get("http_status"),
            "total_size_bytes": len(json.dumps(result))
        }
        
        # Agregar información específica según el tipo de datos
        if "data" in result and isinstance(result["data"], dict):
            data = result["data"]
            summary["data_keys"] = list(data.keys())[:10]
            
            if "items" in data:
                summary["items_count"] = len(data["items"]) if isinstance(data["items"], list) else 1
                
        return summary
    
    def _generate_session_id(self) -> str:
        """Genera un ID único para la sesión"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        hash_part = hashlib.md5(f"{timestamp}_{datetime.now().microsecond}".encode()).hexdigest()[:8]
        return f"session_{timestamp}_{hash_part}"

# Instancia global
memory_manager = PersistentMemoryManager()

# Funciones para integrar con ACTION_MAP
def save_memory(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """Función para ACTION_MAP - guardar en memoria"""
    return memory_manager.save_interaction(params)

def get_memory_history(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """Función para ACTION_MAP - obtener historial"""
    limit = params.get("limit", 50)
    return memory_manager.get_session_history(limit)

def search_memory_store(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """Función para ACTION_MAP - buscar en memoria"""
    query = params.get("query", "")
    category = params.get("category")
    return memory_manager.search_memory(query, category)

def search_memory(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """Función para ACTION_MAP - buscar en memoria (alias canónico)"""
    query = params.get("query", "")
    category = params.get("category")
    return memory_manager.search_memory(query, category)

def export_memory_summary(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """Función para ACTION_MAP - exportar resumen"""
    return memory_manager.export_session_summary()
