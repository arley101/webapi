# app/actions/resolver_actions.py
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Cache simple para resoluciones
_resolution_cache = {}
_resolution_analytics = {
    "total_queries": 0,
    "successful_resolutions": 0,
    "failed_resolutions": 0,
    "cache_hits": 0,
    "start_time": datetime.now()
}

# Mapa de recursos centralizados
RESOURCE_MAP = {
    "google_ads": {
        "main_customer_id": "1415018442",
        "campaigns": {
            "search_campaigns": ["campaign_123", "campaign_456"],
            "display_campaigns": ["campaign_789"]
        }
    },
    "sharepoint": {
        "main_site": "eliteimagenesdiagnostica.sharepoint.com,95e1c135-ab4e-4c77-afb0-d18c31eb6e76,d3c21d5f-e8f9-4e93-aa03-51abe47c6e31",
        "memory_list": "AsistenteMemoria",
        "document_libraries": ["Documents", "Reports", "Templates"]
    },
    "notion": {
        "memory_db": "2361b98f39dd8037b973edddd15fba5d",
        "workspace_id": "elite-dynamics-workspace"
    },
    "meta_ads": {
        "business_account_id": "7527480784568091704",
        "pages": {
            "main_page": "page_123456",
            "secondary_page": "page_789012"
        }
    },
    "planner": {
        "groups": {
            "main_group": "group_id_123",
            "dev_team": "group_id_456"
        }
    }
}

def resolve_dynamic_query(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Resuelve consultas dinámicas usando análisis inteligente y el mapa de recursos
    """
    try:
        query = params.get("query", "")
        resource_path = params.get("resource_path", "")
        
        if not query and not resource_path:
            return {
                "success": False,
                "message": "Query or resource_path parameter is required",
                "error": "MISSING_PARAMS"
            }
        
        _resolution_analytics["total_queries"] += 1
        
        # Si es una consulta de recurso específico
        if resource_path:
            path_parts = resource_path.split('.')
            current = RESOURCE_MAP
            
            for part in path_parts:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    return {
                        "success": False,
                        "message": f"Resource path '{resource_path}' not found",
                        "error": "RESOURCE_NOT_FOUND"
                    }
            
            _resolution_analytics["successful_resolutions"] += 1
            return {
                "success": True,
                "message": "Resource resolved successfully",
                "data": {
                    "resource_path": resource_path,
                    "value": current,
                    "resolved_at": datetime.now().isoformat()
                }
            }
        
        # Verificar caché
        cache_key = f"query_{hash(query)}"
        if cache_key in _resolution_cache:
            _resolution_analytics["cache_hits"] += 1
            return {
                "success": True,
                "message": "Query resolved from cache",
                "data": _resolution_cache[cache_key],
                "cached": True
            }
        
        # Resolver query (simulado por ahora)
        resolved_data = {
            "query": query,
            "resolved_at": datetime.now().isoformat(),
            "resolution_type": "dynamic_analysis",
            "confidence": 0.85,
            "suggested_actions": [
                "analyze_conversation_context",
                "generate_response_suggestions"
            ]
        }
        
        # Guardar en caché
        _resolution_cache[cache_key] = resolved_data
        _resolution_analytics["successful_resolutions"] += 1
        
        return {
            "success": True,
            "message": "Query resolved successfully",
            "data": resolved_data,
            "cached": False
        }
        
    except Exception as e:
        _resolution_analytics["failed_resolutions"] += 1
        logger.error(f"Error in resolve_dynamic_query: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to resolve query: {str(e)}",
            "error": "RESOLUTION_ERROR"
        }

def resolve_contextual_action(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Resuelve acciones basadas en contexto
    """
    try:
        context = params.get("context", {})
        user_intent = params.get("user_intent", "")
        
        if not context and not user_intent:
            return {
                "success": False,
                "message": "Context or user_intent is required",
                "error": "MISSING_CONTEXT"
            }
        
        _resolution_analytics["total_queries"] += 1
        
        # Análisis contextual (simulado)
        contextual_resolution = {
            "context": context,
            "user_intent": user_intent,
            "resolved_at": datetime.now().isoformat(),
            "recommended_action": "gemini_analyze_conversation",
            "confidence": 0.92,
            "reasoning": "Based on context analysis and user intent pattern recognition"
        }
        
        _resolution_analytics["successful_resolutions"] += 1
        
        return {
            "success": True,
            "message": "Contextual action resolved",
            "data": contextual_resolution
        }
        
    except Exception as e:
        _resolution_analytics["failed_resolutions"] += 1
        logger.error(f"Error in resolve_contextual_action: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to resolve contextual action: {str(e)}",
            "error": "CONTEXTUAL_RESOLUTION_ERROR"
        }

def get_resolution_analytics(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Obtiene analíticas del sistema de resolución
    """
    try:
        uptime = datetime.now() - _resolution_analytics["start_time"]
        
        analytics_data = {
            **_resolution_analytics,
            "uptime_seconds": uptime.total_seconds(),
            "success_rate": (
                _resolution_analytics["successful_resolutions"] / 
                max(_resolution_analytics["total_queries"], 1)
            ) * 100,
            "cache_hit_rate": (
                _resolution_analytics["cache_hits"] / 
                max(_resolution_analytics["total_queries"], 1)
            ) * 100,
            "cache_size": len(_resolution_cache),
            "retrieved_at": datetime.now().isoformat()
        }
        
        return {
            "success": True,
            "message": "Analytics retrieved successfully",
            "data": analytics_data
        }
        
    except Exception as e:
        logger.error(f"Error in get_resolution_analytics: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to get analytics: {str(e)}",
            "error": "ANALYTICS_ERROR"
        }

def clear_resolution_cache(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Limpia el caché de resoluciones
    """
    try:
        cache_size_before = len(_resolution_cache)
        _resolution_cache.clear()
        
        return {
            "success": True,
            "message": f"Cache cleared successfully. {cache_size_before} entries removed",
            "data": {
                "entries_removed": cache_size_before,
                "cleared_at": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error in clear_resolution_cache: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to clear cache: {str(e)}",
            "error": "CACHE_CLEAR_ERROR"
        }

def resolve_smart_workflow(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Resuelve flujos de trabajo inteligentes
    """
    try:
        workflow_type = params.get("workflow_type", "")
        workflow_params = params.get("workflow_params", {})
        
        if not workflow_type:
            return {
                "success": False,
                "message": "workflow_type is required",
                "error": "MISSING_WORKFLOW_TYPE"
            }
        
        _resolution_analytics["total_queries"] += 1
        
        # Resolución de workflow (simulado)
        workflow_resolution = {
            "workflow_type": workflow_type,
            "workflow_params": workflow_params,
            "resolved_at": datetime.now().isoformat(),
            "execution_plan": [
                {
                    "step": 1,
                    "action": "analyze_conversation_context",
                    "description": "Analyze user input and context"
                },
                {
                    "step": 2,
                    "action": "generate_response_suggestions",
                    "description": "Generate intelligent response options"
                },
                {
                    "step": 3,
                    "action": "extract_key_information",
                    "description": "Extract key insights from the interaction"
                }
            ],
            "estimated_duration": "2-3 minutes",
            "confidence": 0.88
        }
        
        _resolution_analytics["successful_resolutions"] += 1
        
        return {
            "success": True,
            "message": "Smart workflow resolved",
            "data": workflow_resolution
        }
        
    except Exception as e:
        _resolution_analytics["failed_resolutions"] += 1
        logger.error(f"Error in resolve_smart_workflow: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to resolve smart workflow: {str(e)}",
            "error": "WORKFLOW_RESOLUTION_ERROR"
        }

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

# Configurar logging
logger = logging.getLogger(__name__)

# Diccionario de recursos del sistema
RESOURCE_MAP = {
    "google_ads": {
        "main_customer_id": "1415018442",
        "test_customer_id": "1234567890"
    },
    "sharepoint": {
        "main_site": "eliteimagenesdiagnostica.sharepoint.com,95e1...",
        "memoria_list": "AsistenteMemoria",
        "documents_library": "Documentos"
    },
    "notion": {
        "memory_db": "2361b98f39dd8037b973edddd15fba5d",
        "tasks_db": "1234567890abcdef",
        "contacts_db": "abcdef1234567890"
    },
    "hubspot": {
        "portal_id": "12345678",
        "main_pipeline": "default"
    },
    "wordpress": {
        "main_site": "https://example.com",
        "staging_site": "https://staging.example.com"
    }
}

def _handle_resolver_error(error: Exception, action_name: str) -> Dict[str, Any]:
    """Maneja errores del resolver de forma centralizada."""
    error_message = f"Error en {action_name}: {str(error)}"
    logger.error(error_message)
    
    return {
        "status": "error",
        "error": error_message,
        "action": action_name,
        "timestamp": datetime.now().isoformat()
    }

def resolve_resource(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Resuelve un recurso por su nombre amigable.
    
    Args:
        client: Cliente (no usado, mantenido por consistencia)
        params: Dict con:
            - resource_type: Tipo de recurso (google_ads, sharepoint, etc.)
            - resource_name: Nombre del recurso a resolver
    
    Returns:
        Dict con el ID o información del recurso
    """
    action_name = "resolve_resource"
    
    try:
        resource_type = params.get("resource_type", "")
        resource_name = params.get("resource_name", "")
        
        if not resource_type or not resource_name:
            raise ValueError("resource_type y resource_name son requeridos")
        
        # Buscar en el mapa de recursos
        if resource_type in RESOURCE_MAP:
            resources = RESOURCE_MAP[resource_type]
            if resource_name in resources:
                return {
                    "status": "success",
                    "data": {
                        "resource_type": resource_type,
                        "resource_name": resource_name,
                        "resource_value": resources[resource_name]
                    },
                    "timestamp": datetime.now().isoformat()
                }
            else:
                # Buscar recursos disponibles
                available = list(resources.keys())
                return {
                    "status": "not_found",
                    "message": f"Recurso '{resource_name}' no encontrado en '{resource_type}'",
                    "available_resources": available,
                    "timestamp": datetime.now().isoformat()
                }
        else:
            # Tipos de recursos disponibles
            available_types = list(RESOURCE_MAP.keys())
            return {
                "status": "error",
                "message": f"Tipo de recurso '{resource_type}' no válido",
                "available_types": available_types,
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        return _handle_resolver_error(e, action_name)

def list_available_resources(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Lista todos los recursos disponibles en el sistema.
    
    Args:
        client: Cliente (no usado, mantenido por consistencia)
        params: Dict con:
            - resource_type (opcional): Filtrar por tipo de recurso
    
    Returns:
        Dict con la lista de recursos disponibles
    """
    action_name = "list_available_resources"
    
    try:
        resource_type = params.get("resource_type")
        
        if resource_type:
            # Filtrar por tipo específico
            if resource_type in RESOURCE_MAP:
                return {
                    "status": "success",
                    "data": {
                        resource_type: RESOURCE_MAP[resource_type]
                    },
                    "total_resources": len(RESOURCE_MAP[resource_type]),
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "status": "error",
                    "message": f"Tipo de recurso '{resource_type}' no encontrado",
                    "available_types": list(RESOURCE_MAP.keys()),
                    "timestamp": datetime.now().isoformat()
                }
        else:
            # Devolver todos los recursos
            total_count = sum(len(resources) for resources in RESOURCE_MAP.values())
            return {
                "status": "success",
                "data": RESOURCE_MAP,
                "total_resources": total_count,
                "resource_types": list(RESOURCE_MAP.keys()),
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        return _handle_resolver_error(e, action_name)

def validate_resource_id(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Valida si un ID de recurso existe en el sistema.
    
    Args:
        client: Cliente (no usado, mantenido por consistencia)
        params: Dict con:
            - resource_id: ID del recurso a validar
            - resource_type (opcional): Tipo de recurso esperado
    
    Returns:
        Dict con el resultado de la validación
    """
    action_name = "validate_resource_id"
    
    try:
        resource_id = params.get("resource_id", "")
        resource_type = params.get("resource_type")
        
        if not resource_id:
            raise ValueError("resource_id es requerido")
        
        # Buscar el ID en todos los recursos
        found_in = []
        
        for r_type, resources in RESOURCE_MAP.items():
            if resource_type and r_type != resource_type:
                continue
                
            for r_name, r_value in resources.items():
                if str(r_value) == str(resource_id):
                    found_in.append({
                        "resource_type": r_type,
                        "resource_name": r_name
                    })
        
        if found_in:
            return {
                "status": "success",
                "valid": True,
                "found_in": found_in,
                "resource_id": resource_id,
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "status": "success",
                "valid": False,
                "message": f"ID '{resource_id}' no encontrado en el sistema",
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        return _handle_resolver_error(e, action_name)

def get_resource_config(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Obtiene la configuración completa de un tipo de recurso.
    
    Args:
        client: Cliente (no usado, mantenido por consistencia)
        params: Dict con:
            - resource_type: Tipo de recurso
    
    Returns:
        Dict con la configuración del recurso
    """
    action_name = "get_resource_config"
    
    try:
        resource_type = params.get("resource_type", "")
        
        if not resource_type:
            raise ValueError("resource_type es requerido")
        
        if resource_type in RESOURCE_MAP:
            config = RESOURCE_MAP[resource_type]
            
            # Agregar metadatos adicionales según el tipo
            metadata = {
                "resource_count": len(config),
                "resource_names": list(config.keys())
            }
            
            # Metadatos específicos por tipo
            if resource_type == "google_ads":
                metadata["primary_customer"] = config.get("main_customer_id")
            elif resource_type == "sharepoint":
                metadata["primary_site"] = config.get("main_site")
            elif resource_type == "notion":
                metadata["databases"] = [k for k in config.keys() if k.endswith("_db")]
            
            return {
                "status": "success",
                "data": {
                    "resource_type": resource_type,
                    "config": config,
                    "metadata": metadata
                },
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "status": "error",
                "message": f"Tipo de recurso '{resource_type}' no encontrado",
                "available_types": list(RESOURCE_MAP.keys()),
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        return _handle_resolver_error(e, action_name)

def search_resources(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Busca recursos por término de búsqueda.
    
    Args:
        client: Cliente (no usado, mantenido por consistencia)
        params: Dict con:
            - search_term: Término de búsqueda
            - search_in (opcional): Lista de tipos donde buscar
    
    Returns:
        Dict con los recursos encontrados
    """
    action_name = "search_resources"
    
    try:
        search_term = params.get("search_term", "").lower()
        search_in = params.get("search_in", list(RESOURCE_MAP.keys()))
        
        if not search_term:
            raise ValueError("search_term es requerido")
        
        # Normalizar search_in a lista
        if isinstance(search_in, str):
            search_in = [search_in]
        
        results = []
        
        for resource_type in search_in:
            if resource_type not in RESOURCE_MAP:
                continue
                
            resources = RESOURCE_MAP[resource_type]
            
            for resource_name, resource_value in resources.items():
                # Buscar en el nombre y valor del recurso
                if (search_term in resource_name.lower() or 
                    search_term in str(resource_value).lower()):
                    results.append({
                        "resource_type": resource_type,
                        "resource_name": resource_name,
                        "resource_value": resource_value,
                        "match_type": "name" if search_term in resource_name.lower() else "value"
                    })
        
        return {
            "status": "success",
            "data": {
                "search_term": search_term,
                "results": results,
                "total_found": len(results)
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return _handle_resolver_error(e, action_name)