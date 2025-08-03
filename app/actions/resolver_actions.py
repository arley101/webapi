# app/actions/resolver_actions.py
from typing import Dict, Any, Optional, List, Tuple
import json
import logging
import os
from datetime import datetime
from app.core.config import settings
from app.actions import gemini_actions, sharepoint_actions, notion_actions, onedrive_actions, webresearch_actions

logger = logging.getLogger(__name__)

class IntelligentResourceManager:
    """Sistema inteligente de gestión de recursos multi-plataforma"""
    
    def __init__(self):
        self.supported_platforms = ["sharepoint", "onedrive", "notion"]
        self.resource_cache = {}
        
    def determine_best_platform(self, resource_type: str, size_kb: float = 0) -> str:
        """Determina la mejor plataforma según el tipo de recurso"""
        if resource_type in ["document", "report", "excel", "word"]:
            return "sharepoint" if size_kb > 5000 else "onedrive"
        elif resource_type in ["note", "task", "memory"]:
            return "notion"
        elif resource_type in ["image", "video", "media"]:
            return "onedrive"
        else:
            return "notion"  # Default

# Instancia global del gestor de recursos
resource_manager = IntelligentResourceManager()

# Ruta del archivo de estado
STATE_FILE_PATH = os.path.join(os.path.dirname(__file__), '..', 'ecosystem_state.json')

def _load_state() -> Dict[str, Any]:
    """Carga el estado del ecosistema desde archivo"""
    try:
        if os.path.exists(STATE_FILE_PATH):
            with open(STATE_FILE_PATH, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading state: {str(e)}")
    return {"resources": {}, "cache": {}, "last_update": None}

def _save_state(state: Dict[str, Any]) -> None:
    """Guarda el estado del ecosistema en archivo"""
    try:
        state["last_update"] = datetime.now().isoformat()
        os.makedirs(os.path.dirname(STATE_FILE_PATH), exist_ok=True)
        with open(STATE_FILE_PATH, 'w') as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving state: {str(e)}")

def smart_save_resource(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Sistema de guardado inteligente con decisión autónoma"""
    
    try:
        resource_type = params.get('resource_type', 'general')
        resource_data = params.get('resource_data')
        action_name = params.get('action_name', '')
        source = params.get('source', 'unknown')
        
        # 1. ANÁLISIS INTELIGENTE CON GEMINI
        logger.info(f"🧠 Analizando recurso con Gemini para guardado inteligente")
        
        gemini_analysis = gemini_actions.analyze_conversation_context(client, {
            "conversation_data": {
                "task": "analyze_and_decide_storage",
                "resource_type": resource_type,
                "action_name": action_name,
                "data_preview": str(resource_data)[:1000],  # Solo preview
                "available_storage": {
                    "sharepoint": "Documentos, listas, registros estructurados",
                    "onedrive": "Videos, imágenes, archivos multimedia",
                    "notion": "Bases de datos, reportes, dashboards",
                    "teams": "Mensajes, notificaciones, colaboración"
                },
                "instructions": """
                Analiza el contenido y decide:
                1. Dónde guardarlo (puede ser múltiples lugares)
                2. Qué metadata agregar
                3. Si requiere procesamiento adicional
                4. Si debe notificar a alguien
                5. Si debe crear registros relacionados
                
                Responde en formato JSON con estructura:
                {
                    "primary_storage": "platform_name",
                    "secondary_storage": ["platform2", "platform3"],
                    "metadata": {...},
                    "additional_actions": ["action1", "action2"],
                    "notifications": [{...}],
                    "tags": ["tag1", "tag2"]
                }
                """
            }
        })
        
        # Parsear decisión de Gemini
        gemini_decision = {}
        if gemini_analysis.get('success'):
            try:
                gemini_decision = json.loads(gemini_analysis.get('data', {}).get('response', '{}'))
            except:
                gemini_decision = gemini_analysis.get('data', {})
        
        # 2. EJECUTAR GUARDADO BASADO EN DECISIÓN INTELIGENTE
        storage_results = []
        primary_platform = gemini_decision.get('primary_storage', 'sharepoint')
        secondary_platforms = gemini_decision.get('secondary_storage', [])
        
        # Metadata enriquecida por Gemini
        enhanced_metadata = {
            **params.get('metadata', {}),
            **gemini_decision.get('metadata', {}),
            'timestamp': datetime.now().isoformat(),
            'action': action_name,
            'source': source,
            'gemini_tags': gemini_decision.get('tags', []),
            'auto_saved': True
        }
        
        # GUARDADO PRIMARIO
        if primary_platform == 'sharepoint':
            result = _save_to_sharepoint_intelligent(client, resource_data, resource_type, enhanced_metadata)
            storage_results.append(result)
            
        elif primary_platform == 'onedrive':
            result = _save_to_onedrive_intelligent(client, resource_data, resource_type, enhanced_metadata)
            storage_results.append(result)
            
        elif primary_platform == 'notion':
            result = _save_to_notion_intelligent(client, resource_data, resource_type, enhanced_metadata)
            storage_results.append(result)
        
        # GUARDADOS SECUNDARIOS (en paralelo conceptualmente)
        for platform in secondary_platforms:
            if platform == 'sharepoint' and primary_platform != 'sharepoint':
                # Crear registro en lista de SharePoint
                registry_result = _create_sharepoint_registry(client, {
                    'resource_id': storage_results[0].get('id'),
                    'storage_location': storage_results[0].get('url'),
                    'metadata': enhanced_metadata
                })
                storage_results.append(registry_result)
                
            elif platform == 'notion' and primary_platform != 'notion':
                # Crear entrada en base de datos Notion
                notion_result = _create_notion_registry(client, {
                    'title': f"{resource_type} - {datetime.now().strftime('%Y-%m-%d')}",
                    'resource_data': resource_data,
                    'metadata': enhanced_metadata
                })
                storage_results.append(notion_result)
        
        # 3. EJECUTAR ACCIONES ADICIONALES SUGERIDAS POR GEMINI
        additional_results = []
        for action in gemini_decision.get('additional_actions', []):
            if action == 'create_summary':
                summary = gemini_actions.summarize_conversation(client, {
                    'conversation_data': {'content': str(resource_data)}
                })
                additional_results.append({'action': 'summary', 'result': summary})
                
            elif action == 'extract_insights':
                insights = gemini_actions.extract_key_information(client, {
                    'conversation_data': {'content': str(resource_data)}
                })
                additional_results.append({'action': 'insights', 'result': insights})
                
            elif action == 'search_related':
                # Búsqueda web inteligente para contexto adicional
                search_result = _intelligent_web_search(client, resource_data, resource_type)
                additional_results.append({'action': 'web_search', 'result': search_result})
        
        # 4. NOTIFICACIONES AUTOMÁTICAS
        notifications_sent = []
        for notification in gemini_decision.get('notifications', []):
            if notification.get('platform') == 'teams':
                teams_result = _send_teams_notification(client, {
                    'message': notification.get('message'),
                    'channel': notification.get('channel', 'general'),
                    'resource_url': storage_results[0].get('url')
                })
                notifications_sent.append(teams_result)
        
        # 5. CONSTRUCCIÓN DE RESPUESTA CONSOLIDADA
        return {
            'success': True,
            'resource_id': storage_results[0].get('id') if storage_results else None,
            'primary_storage': {
                'platform': primary_platform,
                'url': storage_results[0].get('url') if storage_results else None,
                'id': storage_results[0].get('id') if storage_results else None
            },
            'secondary_storage': storage_results[1:] if len(storage_results) > 1 else [],
            'gemini_analysis': gemini_decision,
            'metadata': enhanced_metadata,
            'additional_actions': additional_results,
            'notifications': notifications_sent,
            'auto_save_complete': True,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error en smart_save_resource: {str(e)}")
        # Fallback a guardado simple
        return _fallback_simple_save(client, params)

def _save_to_sharepoint_intelligent(client: Any, data: Any, resource_type: str, metadata: Dict) -> Dict:
    """Guardado inteligente en SharePoint con decisión autónoma de ubicación"""
    
    # Determinar si es documento o lista
    if resource_type in ['document', 'report', 'export', 'file']:
        # Guardar como documento
        filename = f"{resource_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        folder_path = f"/EliteDynamics/AutoSaved/{resource_type}"
        
        return sharepoint_actions.sp_upload_document(client, {
            'filename': filename,
            'content_bytes': json.dumps(data, ensure_ascii=False).encode('utf-8'),
            'folder_path': folder_path,
            'conflict_behavior': 'rename'
        })
    else:
        # Guardar en lista
        list_name = settings.MEMORIA_LIST_NAME or "EliteDynamics_Registry"
        
        return sharepoint_actions.sp_add_list_item(client, {
            'lista_id_o_nombre': list_name,
            'campos': {
                'Title': f"{resource_type} - {metadata.get('action', 'auto_saved')}",
                'ResourceType': resource_type,
                'ResourceData': json.dumps(data)[:5000],  # Límite para campos de texto
                'Metadata': json.dumps(metadata),
                'Timestamp': metadata.get('timestamp'),
                'Tags': ', '.join(metadata.get('gemini_tags', []))
            }
        })

def _save_to_onedrive_intelligent(client: Any, data: Any, resource_type: str, metadata: Dict) -> Dict:
    """Guardado inteligente en OneDrive para multimedia"""
    
    # Determinar carpeta según tipo
    folder_map = {
        'video': '/EliteDynamics/Videos',
        'image': '/EliteDynamics/Images',
        'audio': '/EliteDynamics/Audio',
        'document': '/EliteDynamics/Documents'
    }
    
    folder_path = folder_map.get(resource_type, '/EliteDynamics/General')
    filename = f"{resource_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Si es JSON, convertir a archivo
    if isinstance(data, dict):
        filename += '.json'
        content = json.dumps(data, ensure_ascii=False).encode('utf-8')
    else:
        content = data
    
    return onedrive_actions.upload_file(client, {
        'filename': filename,
        'content': content,
        'path': folder_path,
        'conflict_behavior': 'rename'
    })

def _save_to_notion_intelligent(client: Any, data: Any, resource_type: str, metadata: Dict) -> Dict:
    """Guardado inteligente en Notion con estructura dinámica"""
    
    # Buscar o crear base de datos apropiada
    db_name = f"Elite Dynamics - {resource_type.title()}"
    
    # Primero intentar encontrar la DB
    db_result = notion_actions.notion_find_database_by_name(client, {'name': db_name})
    
    if not db_result.get('success'):
        # Crear nueva base de datos
        db_result = notion_actions.notion_create_database(client, {
            'parent_page_id': settings.NOTION_MAIN_DATABASE_ID,
            'title': db_name,
            'properties': {
                'Name': {'title': {}},
                'Type': {'select': {'options': []}},
                'Status': {'select': {'options': []}},
                'Data': {'rich_text': {}},
                'Created': {'date': {}},
                'Tags': {'multi_select': {'options': []}},
                'URL': {'url': {}},
                'Action': {'select': {'options': []}}
            }
        })
    
    # Crear página en la base de datos
    return notion_actions.notion_create_page_in_database(client, {
        'database_id': db_result.get('data', {}).get('id'),
        'properties': {
            'Name': {'title': [{'text': {'content': f"{resource_type} - {metadata.get('action', 'saved')}"}}]},
            'Type': {'select': {'name': resource_type}},
            'Status': {'select': {'name': 'Active'}},
            'Data': {'rich_text': [{'text': {'content': str(data)[:2000]}}]},
            'Created': {'date': {'start': metadata.get('timestamp')}},
            'Tags': {'multi_select': [{'name': tag} for tag in metadata.get('gemini_tags', [])]},
            'Action': {'select': {'name': metadata.get('action', 'unknown')}}
        }
    })

def _intelligent_web_search(client: Any, data: Any, resource_type: str) -> Dict:
    """Búsqueda web inteligente basada en contexto"""
    
    # Usar Gemini para extraer términos de búsqueda relevantes
    search_terms_result = gemini_actions.extract_key_information(client, {
        'conversation_data': {
            'content': str(data)[:1000],
            'task': 'extract_search_terms',
            'context': f"Extract 3-5 key search terms for {resource_type}"
        }
    })
    
    if search_terms_result.get('success'):
        search_query = search_terms_result.get('data', {}).get('key_terms', '')
        
        # Ejecutar búsqueda web
        search_result = webresearch_actions.search_web(client, {
            'query': search_query,
            'limit': 5
        })
        
        # Si encuentra resultados relevantes, guardarlos también
        if search_result.get('success') and search_result.get('data'):
            # Guardar contexto web en Notion
            notion_actions.notion_create_page_in_database(client, {
                'database_name': 'Elite Dynamics - Web Context',
                'properties': {
                    'Title': {'title': [{'text': {'content': f"Context for {resource_type}"}}]},
                    'SearchQuery': {'rich_text': [{'text': {'content': search_query}}]},
                    'Results': {'rich_text': [{'text': {'content': json.dumps(search_result['data'])[:2000]}}]},
                    'RelatedResource': {'rich_text': [{'text': {'content': resource_type}}]}
                }
            })
        
        return search_result
    
    return {'success': False, 'message': 'No search terms extracted'}

def execute_workflow(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Ejecutor de workflows con inteligencia Gemini integrada"""
    
    steps = params.get('steps', [])
    context = params.get('context', {})
    
    # Usar Gemini para optimizar el workflow
    optimization_result = gemini_actions.generate_execution_plan(client, {
        'conversation_data': {
            'workflow': steps,
            'context': context,
            'task': 'optimize_workflow',
            'instructions': """
            Analiza este workflow y sugiere:
            1. Si algunos pasos pueden ejecutarse en paralelo
            2. Si hay pasos redundantes
            3. Si falta algún paso crítico
            4. Orden óptimo de ejecución
            """
        }
    })
    
    # Ejecutar workflow con optimizaciones
    results = []
    workflow_context = {'variables': {}, **context}
    
    for i, step in enumerate(steps):
        try:
            logger.info(f"Ejecutando paso {i+1}/{len(steps)}: {step['action']}")
            
            # Resolver variables en parámetros
            resolved_params = _resolve_variables(step.get('params', {}), workflow_context['variables'])
            
            # Ejecutar acción
            if step['action'] in globals():
                result = globals()[step['action']](client, resolved_params)
            else:
                # Delegar a action_mapper
                from app.core.action_mapper import ACTION_MAP
                if step['action'] in ACTION_MAP:
                    result = ACTION_MAP[step['action']](client, resolved_params)
                else:
                    result = {'success': False, 'error': f"Acción no encontrada: {step['action']}"}
            
            # Guardar resultado si es exitoso
            if result.get('success'):
                if step.get('store_as'):
                    workflow_context['variables'][step['store_as']] = result
                
                # AUTO-GUARDAR si el resultado es significativo
                if step.get('save_result', True) and _should_auto_save(result):
                    save_result = smart_save_resource(client, {
                        'resource_type': step['action'].split('_')[0],
                        'resource_data': result,
                        'action_name': step['action'],
                        'source': 'workflow_execution',
                        'metadata': {
                            'workflow_step': i + 1,
                            'workflow_context': context
                        }
                    })
                    result['auto_saved'] = save_result
            
            results.append({
                'step': i + 1,
                'action': step['action'],
                'result': result,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error en paso {i+1}: {str(e)}")
            results.append({
                'step': i + 1,
                'action': step['action'],
                'error': str(e)
            })
    
    return {
        'success': all(r.get('result', {}).get('success', False) for r in results),
        'workflow_results': results,
        'optimization_suggestions': optimization_result.get('data', {}),
        'execution_time': datetime.now().isoformat()
    }

def _should_auto_save(result: Dict) -> bool:
    """Determina si un resultado debe ser auto-guardado"""
    
    # Criterios para auto-guardado
    if not result.get('success'):
        return False
    
    # Guardar si tiene datos significativos
    if result.get('data'):
        data_size = len(str(result['data']))
        if data_size > 1000:  # Más de 1KB de datos
            return True
    
    # Guardar si tiene URLs o IDs importantes
    if any(key in str(result) for key in ['url', 'webUrl', 'id', 'resource_id']):
        return True
    
    # Guardar si es una acción de creación
    action_keywords = ['create', 'upload', 'add', 'new', 'generate']
    if any(keyword in result.get('action', '').lower() for keyword in action_keywords):
        return True
    
    return False

def _resolve_variables(params: Dict, variables: Dict) -> Dict:
    """Resuelve variables en los parámetros del workflow"""
    
    if isinstance(params, str):
        # Buscar patrones {{variable}}
        import re
        pattern = r'\{\{(\w+(?:\.\w+)*)\}\}'
        
        def replacer(match):
            path = match.group(1).split('.')
            value = variables
            for part in path:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    return match.group(0)  # No reemplazar si no existe
            return str(value)
        
        return re.sub(pattern, replacer, params)
    
    elif isinstance(params, dict):
        return {k: _resolve_variables(v, variables) for k, v in params.items()}
    
    elif isinstance(params, list):
        return [_resolve_variables(item, variables) for item in params]
    
    return params

def _send_teams_notification(client: Any, params: Dict) -> Dict:
    """Envía notificación a Teams"""
    try:
        from app.actions import teams_actions
        return teams_actions.teams_send_channel_message(client, {
            'team_name': params.get('team', 'EliteDynamics'),
            'channel_name': params.get('channel', 'general'),
            'message': params.get('message', 'Recurso guardado automáticamente'),
            'content_type': 'html'
        })
    except Exception as e:
        logger.error(f"Error enviando notificación Teams: {str(e)}")
        return {'success': False, 'error': str(e)}

def _create_sharepoint_registry(client: Any, params: Dict) -> Dict:
    """Crea registro en lista de SharePoint"""
    return sharepoint_actions.sp_add_list_item(client, {
        'lista_id_o_nombre': 'EliteDynamics_Registry',
        'campos': {
            'Title': f"Registry - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            'ResourceID': params.get('resource_id'),
            'StorageLocation': params.get('storage_location'),
            'Metadata': json.dumps(params.get('metadata', {}))
        }
    })

def _create_notion_registry(client: Any, params: Dict) -> Dict:
    """Crea registro en base de datos Notion"""
    return notion_actions.notion_create_page_in_database(client, {
        'database_name': 'Elite Dynamics - Resource Registry',
        'properties': {
            'Title': {'title': [{'text': {'content': params.get('title', 'Auto-saved Resource')}}]},
            'ResourceData': {'rich_text': [{'text': {'content': str(params.get('resource_data', ''))[:2000]}}]},
            'Metadata': {'rich_text': [{'text': {'content': json.dumps(params.get('metadata', {}))}}]},
            'Timestamp': {'date': {'start': datetime.now().isoformat()}}
        }
    })

def _fallback_simple_save(client: Any, params: Dict) -> Dict:
    """Guardado simple como fallback"""
    try:
        # Guardar en SharePoint por defecto
        return sharepoint_actions.sp_add_list_item(client, {
            'lista_id_o_nombre': 'EliteDynamics_Fallback',
            'campos': {
                'Title': f"Fallback Save - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                'Data': json.dumps(params)[:5000],
                'Error': 'Smart save failed, using fallback'
            }
        })
    except:
        return {
            'success': False,
            'error': 'Both smart save and fallback failed'
        }

# Exportar las nuevas funciones
__all__ = [
    'smart_save_resource',
    'resolve_resource',
    'list_available_resources',
    'save_to_notion_registry',
    'get_credentials_from_vault',
    'execute_workflow',
    'resolve_dynamic_query',
    'resolve_contextual_action',
    'get_resolution_analytics',
    'clear_resolution_cache',
    'resolve_smart_workflow',
    'validate_resource_id',
    'get_resource_config',
    'search_resources'
]