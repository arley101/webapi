# app/workflows/auto_workflow.py
"""
Sistema de Workflows Automáticos para Elite Dynamics
Permite ejecutar secuencias de acciones de forma inteligente
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json

from app.core.auth_manager import get_auth_client
from app.actions import gemini_actions
from app.actions import resolver_actions

logger = logging.getLogger(__name__)

class AutoWorkflowManager:
    """Gestor de workflows automáticos con IA integrada"""
    
    def __init__(self):
        self.predefined_workflows = {
            "backup_completo": {
                "name": "Backup Completo del Sistema",
                "description": "Respalda datos de todas las plataformas",
                "steps": [
                    {"action": "sp_get_site_info", "save_to": "sharepoint_status"},
                    {"action": "onedrive_list_items", "params": {"path": "/"}, "save_to": "onedrive_files"},
                    {"action": "notion_search_general", "params": {"query": ""}, "save_to": "notion_pages"},
                    {"action": "email_list_messages", "params": {"top": 50}, "save_to": "recent_emails"},
                    {"action": "teams_list_joined_teams", "save_to": "teams_info"},
                    {"action": "resolver_save_backup", "params": {"backup_data": "{{all_previous_results}}"}}
                ]
            },
            
            "sync_marketing": {
                "name": "Sincronización de Marketing",
                "description": "Sincroniza datos entre plataformas de marketing",
                "steps": [
                    {"action": "googleads_get_campaigns", "save_to": "google_campaigns"},
                    {"action": "metaads_list_campaigns", "save_to": "meta_campaigns"},
                    {"action": "linkedin_list_campaigns", "save_to": "linkedin_campaigns"},
                    {"action": "hubspot_get_deals", "save_to": "hubspot_deals"},
                    {"action": "notion_create_page_in_database", 
                     "params": {
                         "database_name": "Marketing Dashboard",
                         "properties": {
                             "Date": {"date": {"start": "{{current_date}}"}},
                             "Google Campaigns": {"number": "{{google_campaigns.total}}"},
                             "Meta Campaigns": {"number": "{{meta_campaigns.total}}"},
                             "LinkedIn Campaigns": {"number": "{{linkedin_campaigns.total}}"},
                             "HubSpot Deals": {"number": "{{hubspot_deals.total}}"}
                         }
                     }}
                ]
            },
            
            "content_creation": {
                "name": "Flujo de Creación de Contenido",
                "description": "Crea y distribuye contenido automáticamente",
                "steps": [
                    {"action": "wordpress_create_post", "save_to": "new_post"},
                    {"action": "onedrive_upload_file", 
                     "params": {"file_data": "{{new_post.content}}", "filename": "post_{{current_date}}.html"}},
                    {"action": "teams_send_channel_message", 
                     "params": {"message": "Nuevo post creado: {{new_post.url}}"}},
                    {"action": "sp_add_list_item", 
                     "params": {
                         "list_name": "Content Calendar",
                         "item_data": {
                             "Title": "{{new_post.title}}",
                             "URL": "{{new_post.url}}",
                             "Created": "{{current_date}}"
                         }
                     }}
                ]
            },
            
            "youtube_pipeline": {
                "name": "Pipeline de YouTube",
                "description": "Gestión completa de contenido YouTube",
                "steps": [
                    {"action": "youtube_get_channel_info", "save_to": "channel_info"},
                    {"action": "youtube_list_channel_videos", "params": {"max_results": 10}, "save_to": "recent_videos"},
                    {"action": "youtube_get_channel_analytics", 
                     "params": {
                         "start_date": "{{30_days_ago}}",
                         "end_date": "{{current_date}}"
                     }, "save_to": "analytics"},
                    {"action": "notion_create_page_in_database",
                     "params": {
                         "database_name": "YouTube Dashboard",
                         "properties": {
                             "Date": {"date": {"start": "{{current_date}}"}},
                             "Subscribers": {"number": "{{channel_info.statistics.subscriberCount}}"},
                             "Videos": {"number": "{{recent_videos.items.length}}"},
                             "Views": {"number": "{{analytics.total_views}}"}
                         }
                     }}
                ]
            },
            
            "client_onboarding": {
                "name": "Onboarding de Cliente",
                "description": "Proceso automático de incorporación de clientes",
                "steps": [
                    {"action": "hubspot_create_contact", "save_to": "new_contact"},
                    {"action": "sp_create_folder", 
                     "params": {"folder_name": "Cliente_{{new_contact.email}}"}},
                    {"action": "teams_create_chat", 
                     "params": {"participants": ["{{new_contact.email}}"]}},
                    {"action": "calendar_create_event",
                     "params": {
                         "subject": "Reunión de Onboarding - {{new_contact.name}}",
                         "start_datetime": "{{next_business_day}}",
                         "attendees": ["{{new_contact.email}}"]
                     }},
                    {"action": "wordpress_create_page",
                     "params": {
                         "title": "Portal Cliente - {{new_contact.name}}",
                         "content": "Portal personalizado para {{new_contact.name}}"
                     }}
                ]
            }
        }
    
    def execute_workflow(self, workflow_name: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Ejecuta un workflow predefinido"""
        
        if workflow_name not in self.predefined_workflows:
            return {
                "status": "error",
                "message": f"Workflow '{workflow_name}' no encontrado",
                "available_workflows": list(self.predefined_workflows.keys())
            }
        
        workflow = self.predefined_workflows[workflow_name]
        logger.info(f"Ejecutando workflow: {workflow['name']}")
        
        try:
            auth_client = get_auth_client()
            context = {
                "current_date": datetime.now().strftime('%Y-%m-%d'),
                "current_datetime": datetime.now().isoformat(),
                "30_days_ago": (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
                "next_business_day": self._get_next_business_day(),
                "workflow_params": params or {}
            }
            
            results = []
            
            for i, step in enumerate(workflow["steps"]):
                step_name = f"step_{i+1}_{step['action']}"
                logger.info(f"Ejecutando paso {i+1}: {step['action']}")
                
                try:
                    # Resolver parámetros con el contexto
                    resolved_params = self._resolve_variables(step.get("params", {}), context)
                    
                    # Ejecutar la acción
                    if step["action"] in ACTION_MAP:
                        action_function = ACTION_MAP[step["action"]]
                        result = action_function(auth_client, resolved_params)
                    else:
                        # Si no está en ACTION_MAP, intentar con resolver
                        result = resolver_actions.resolve_dynamic_query(auth_client, {
                            "query": step["action"],
                            "params": resolved_params
                        })
                    
                    # Guardar resultado en contexto si se especifica
                    if step.get("save_to"):
                        context[step["save_to"]] = result
                    
                    results.append({
                        "step": i + 1,
                        "action": step["action"],
                        "result": result,
                        "timestamp": datetime.now().isoformat()
                    })
                    
                except Exception as e:
                    logger.error(f"Error en paso {i+1}: {e}")
                    results.append({
                        "step": i + 1,
                        "action": step["action"],
                        "error": str(e),
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    # Decidir si continuar o abortar
                    if step.get("critical", True):
                        return {
                            "status": "error",
                            "message": f"Workflow abortado en paso {i+1}: {e}",
                            "results": results,
                            "workflow": workflow_name
                        }
            
            # Guardar resultado del workflow completo
            try:
                final_save = resolver_actions.smart_save_resource(auth_client, {
                    "resource_type": "workflow_result",
                    "resource_name": f"{workflow_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "resource_data": {
                        "workflow": workflow,
                        "results": results,
                        "context": context,
                        "execution_time": datetime.now().isoformat()
                    }
                })
                
                return {
                    "status": "success",
                    "message": f"Workflow '{workflow_name}' ejecutado exitosamente",
                    "workflow": workflow_name,
                    "steps_completed": len(results),
                    "results": results,
                    "saved_to": final_save.get("storage_locations", []),
                    "execution_summary": {
                        "total_steps": len(workflow["steps"]),
                        "successful_steps": len([r for r in results if "error" not in r]),
                        "failed_steps": len([r for r in results if "error" in r])
                    }
                }
                
            except Exception as e:
                logger.warning(f"No se pudo guardar resultado del workflow: {e}")
                return {
                    "status": "success",
                    "message": f"Workflow '{workflow_name}' ejecutado (sin guardado automático)",
                    "workflow": workflow_name,
                    "results": results
                }
        
        except Exception as e:
            logger.error(f"Error crítico en workflow {workflow_name}: {e}")
            return {
                "status": "error",
                "message": f"Error crítico ejecutando workflow: {str(e)}",
                "workflow": workflow_name
            }
    
    def create_custom_workflow(self, natural_request: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Crea un workflow personalizado usando IA"""
        
        try:
            auth_client = get_auth_client()
            
            # Usar Gemini para interpretar la solicitud
            gemini_result = gemini_actions.analyze_conversation_context(auth_client, {
                "conversation_data": {
                    "request": natural_request,
                    "available_actions": list(ACTION_MAP.keys()),
                    "context": "create_workflow",
                    "user_params": params or {}
                }
            })
            
            if not gemini_result.get("success"):
                return {
                    "status": "error",
                    "message": "No se pudo interpretar la solicitud con IA",
                    "details": gemini_result
                }
            
            # Extraer workflow sugerido
            suggested_workflow = gemini_result.get("data", {}).get("workflow", {})
            
            if not suggested_workflow:
                return {
                    "status": "error",
                    "message": "La IA no pudo generar un workflow válido",
                    "suggestion": "Intenta con una solicitud más específica"
                }
            
            # Ejecutar el workflow generado
            return self._execute_custom_workflow(suggested_workflow, auth_client)
            
        except Exception as e:
            logger.error(f"Error creando workflow personalizado: {e}")
            return {
                "status": "error",
                "message": f"Error creando workflow: {str(e)}"
            }
    
    def _execute_custom_workflow(self, workflow_def: Dict[str, Any], auth_client) -> Dict[str, Any]:
        """Ejecuta un workflow generado dinámicamente"""
        
        results = []
        context = {
            "current_date": datetime.now().strftime('%Y-%m-%d'),
            "current_datetime": datetime.now().isoformat()
        }
        
        for i, step in enumerate(workflow_def.get("steps", [])):
            try:
                action_name = step.get("action")
                step_params = self._resolve_variables(step.get("params", {}), context)
                
                if action_name in ACTION_MAP:
                    action_function = ACTION_MAP[action_name]
                    result = action_function(auth_client, step_params)
                    
                    if step.get("save_to"):
                        context[step["save_to"]] = result
                    
                    results.append({
                        "step": i + 1,
                        "action": action_name,
                        "result": result
                    })
                
            except Exception as e:
                logger.error(f"Error en paso personalizado {i+1}: {e}")
                results.append({
                    "step": i + 1,
                    "action": step.get("action", "unknown"),
                    "error": str(e)
                })
        
        return {
            "status": "success",
            "message": "Workflow personalizado ejecutado",
            "results": results,
            "workflow_generated": workflow_def
        }
    
    def _resolve_variables(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Resuelve variables en parámetros usando el contexto"""
        
        if not isinstance(params, dict):
            return params
        
        resolved = {}
        for key, value in params.items():
            if isinstance(value, str) and value.startswith("{{") and value.endswith("}}"):
                var_name = value[2:-2].strip()
                resolved[key] = context.get(var_name, value)
            elif isinstance(value, dict):
                resolved[key] = self._resolve_variables(value, context)
            else:
                resolved[key] = value
        
        return resolved
    
    def _get_next_business_day(self) -> str:
        """Obtiene el próximo día hábil"""
        from datetime import timedelta
        
        next_day = datetime.now() + timedelta(days=1)
        while next_day.weekday() >= 5:  # 5=Saturday, 6=Sunday
            next_day += timedelta(days=1)
        
        return next_day.strftime('%Y-%m-%d')
    
    def list_workflows(self) -> Dict[str, Any]:
        """Lista todos los workflows disponibles"""
        
        return {
            "status": "success",
            "data": {
                "predefined_workflows": {
                    name: {
                        "name": workflow["name"],
                        "description": workflow["description"],
                        "steps_count": len(workflow["steps"])
                    }
                    for name, workflow in self.predefined_workflows.items()
                },
                "total_workflows": len(self.predefined_workflows),
                "can_create_custom": True,
                "usage": {
                    "predefined": "workflow_manager.execute_workflow('workflow_name')",
                    "custom": "workflow_manager.create_custom_workflow('descripción en lenguaje natural')"
                }
            }
        }

# Instancia global
workflow_manager = AutoWorkflowManager()
