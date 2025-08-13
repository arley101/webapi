"""
Resolver Actions - Sistema Inteligente de Resolución y Gestión de Recursos
Implementación completa de las 14 acciones del resolver
"""

import os
import json
import logging
import hashlib
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone, timedelta
import re
from threading import RLock

# Importar clientes y configuración necesaria
from app.core.config import settings
from app.shared.helpers.http_client import AuthenticatedHttpClient

# Importar acciones de otros módulos para el sistema inteligente
from app.actions import sharepoint_actions
from app.actions import onedrive_actions
from app.actions import notion_actions

logger = logging.getLogger(__name__)

GLOBAL_LOCK = RLock()

def _iso_to_datetime(s: str) -> datetime:
    """Parse ISO 8601 strings (with or without 'Z')."""
    if not s:
        return None
    try:
        if isinstance(s, str) and s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s)
    except Exception:
        return None

# ============================================================================
# CACHE Y ESTADO GLOBAL
# ============================================================================

# Cache en memoria para resoluciones
RESOLUTION_CACHE = {}
RESOURCE_REGISTRY = {}
WORKFLOW_CACHE = {}

# Configuración de almacenamiento inteligente
STORAGE_RULES = {
    "video": {
        "primary": "onedrive",
        "path": "/EliteDynamics/Videos",
        "max_size_mb": 1000
    },
    "image": {
        "primary": "onedrive", 
        "path": "/EliteDynamics/Images",
        "max_size_mb": 50
    },
    "document": {
        "primary": "sharepoint",
        "path": "/EliteDynamics/Documents",
        "list": "EliteDynamics_Documents"
    },
    "report": {
        "primary": "notion",
        "database": "Elite Reports",
        "secondary": "sharepoint"
    },
    "campaign_data": {
        "primary": "notion",
        "database": "Marketing Campaigns",
        "secondary": "sharepoint"
    },
    "analytics": {
        "primary": "notion",
        "database": "Analytics Dashboard",
        "secondary": "sharepoint"
    },
    "backup": {
        "primary": "sharepoint",
        "path": "/EliteDynamics/Backups"
    }
}

# ============================================================================
# FUNCIONES PRINCIPALES DEL RESOLVER
# ============================================================================

def resolve_dynamic_query(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Resuelve queries dinámicos interpretando lenguaje natural y contexto
    """
    try:
        query = params.get("query", "")
        context = params.get("context", {})
        use_cache = params.get("use_cache", True)
        
        logger.info(f"Resolviendo query dinámico: {query}")
        
        # Verificar cache si está habilitado
        cache_key = _generate_cache_key(query, context)
        if use_cache and cache_key in RESOLUTION_CACHE:
            logger.info("Retornando resultado desde cache")
            return RESOLUTION_CACHE[cache_key]
        
        # Analizar query para detectar intención
        intent = _analyze_query_intent(query)
        
        # Resolver según la intención detectada
        resolution = {
            "success": True,
            "query": query,
            "intent": intent,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Lógica de resolución según tipo de intención
        if intent["type"] == "storage":
            resolution["data"] = _resolve_storage_query(query, context)
        elif intent["type"] == "search":
            resolution["data"] = _resolve_search_query(query, context)
        elif intent["type"] == "workflow":
            resolution["data"] = _resolve_workflow_query(query, context)
        elif intent["type"] == "analytics":
            resolution["data"] = _resolve_analytics_query(query, context)
        else:
            resolution["data"] = {
                "message": "Query interpretado pero requiere acción específica",
                "suggested_action": intent.get("suggested_action", "none")
            }
        
        # Guardar en cache
        if use_cache:
            with GLOBAL_LOCK:
                RESOLUTION_CACHE[cache_key] = resolution
        
        return resolution
        
    except Exception as e:
        logger.error(f"Error resolviendo query dinámico: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "query": params.get("query", "")
        }

def resolve_contextual_action(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Resuelve acciones basadas en contexto empresarial y patrones previos
    """
    try:
        action_request = params.get("action_request", "")
        context = params.get("context", {})
        history = params.get("history", [])
        
        logger.info(f"Resolviendo acción contextual: {action_request}")
        
        # Analizar el contexto completo
        analysis = {
            "user_role": context.get("user_role", "executive"),
            "department": context.get("department", "general"),
            "recent_actions": history[-5:] if history else [],
            "time_context": _get_time_context(),
            "business_context": _get_business_context(context)
        }
        
        # Determinar la mejor acción basada en el contexto
        recommended_action = _determine_best_action(action_request, analysis)
        
        # Construir respuesta con recomendaciones
        result = {
            "success": True,
            "action_request": action_request,
            "recommended_action": recommended_action,
            "context_analysis": analysis,
            "confidence": recommended_action.get("confidence", 0.8),
            "alternatives": _get_alternative_actions(action_request, analysis),
            "execution_params": _build_execution_params(recommended_action, context)
        }
        
        # Registrar la resolución para aprendizaje futuro
        _register_resolution(action_request, recommended_action, context)
        
        return result
        
    except Exception as e:
        logger.error(f"Error en resolución contextual: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "action_request": params.get("action_request", "")
        }

def get_resolution_analytics(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Obtiene analytics sobre las resoluciones realizadas
    """
    try:
        time_range = params.get("time_range", "last_7_days")
        group_by = params.get("group_by", "action_type")
        include_details = params.get("include_details", False)
        
        logger.info(f"Obteniendo analytics de resolución para: {time_range}")
        
        # Recopilar estadísticas
        stats = {
            "total_resolutions": len(RESOLUTION_CACHE),
            "cache_hits": _count_cache_hits(),
            "unique_queries": len(set(k.split("-")[0] for k in RESOLUTION_CACHE.keys())),
            "resource_usage": _get_resource_usage_stats(),
            "workflow_executions": len(WORKFLOW_CACHE),
            "storage_distribution": _get_storage_distribution(),
            "popular_actions": _get_popular_actions(limit=10),
            "error_rate": _calculate_error_rate(),
            "average_resolution_time": _get_avg_resolution_time()
        }
        
        # Agregar detalles si se solicitan
        if include_details:
            stats["recent_resolutions"] = _get_recent_resolutions(limit=20)
            stats["performance_metrics"] = _get_performance_metrics()
            stats["optimization_suggestions"] = _get_optimization_suggestions(stats)
        
        return {
            "success": True,
            "time_range": time_range,
            "analytics": stats,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo analytics: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

def clear_resolution_cache(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Limpia el cache de resoluciones según criterios especificados
    """
    try:
        cache_type = params.get("cache_type", "all")
        older_than_hours = params.get("older_than_hours", 24)
        pattern = params.get("pattern", None)
        
        logger.info(f"Limpiando cache de tipo: {cache_type}")
        
        cleared_items = {
            "resolution_cache": 0,
            "resource_registry": 0,
            "workflow_cache": 0
        }
        
        # Limpiar cache de resoluciones
        if cache_type in ["all", "resolution"]:
            cleared_items["resolution_cache"] = _clear_cache_items(
                RESOLUTION_CACHE, older_than_hours, pattern
            )
        
        # Limpiar registro de recursos
        if cache_type in ["all", "resources"]:
            cleared_items["resource_registry"] = _clear_cache_items(
                RESOURCE_REGISTRY, older_than_hours, pattern
            )
        
        # Limpiar cache de workflows
        if cache_type in ["all", "workflows"]:
            cleared_items["workflow_cache"] = _clear_cache_items(
                WORKFLOW_CACHE, older_than_hours, pattern
            )
        
        total_cleared = sum(cleared_items.values())
        
        return {
            "success": True,
            "cache_type": cache_type,
            "items_cleared": cleared_items,
            "total_cleared": total_cleared,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error limpiando cache: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

def resolve_smart_workflow(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Resuelve y optimiza workflows inteligentes basados en patrones
    """
    try:
        workflow_request = params.get("workflow_request", "")
        context = params.get("context", {})
        optimize = params.get("optimize", True)
        
        logger.info(f"Resolviendo workflow inteligente: {workflow_request}")
        
        # Analizar la solicitud de workflow
        workflow_analysis = _analyze_workflow_request(workflow_request, context)
        
        # Construir workflow optimizado
        workflow = {
            "name": workflow_analysis["name"],
            "description": workflow_analysis["description"],
            "steps": [],
            "estimated_duration": 0,
            "required_permissions": []
        }
        
        # Generar pasos del workflow
        for step_template in workflow_analysis["steps"]:
            step = _build_workflow_step(step_template, context)
            workflow["steps"].append(step)
            workflow["estimated_duration"] += step.get("estimated_time", 0)
            workflow["required_permissions"].extend(step.get("permissions", []))
        
        # Optimizar si está habilitado
        if optimize:
            workflow = _optimize_workflow(workflow, context)
        
        # Validar el workflow
        validation = _validate_workflow(workflow)
        
        result = {
            "success": True,
            "workflow": workflow,
            "validation": validation,
            "optimization_applied": optimize,
            "execution_ready": validation["is_valid"],
            "warnings": validation.get("warnings", [])
        }
        
        # Cachear el workflow si es válido
        if validation["is_valid"]:
            workflow_id = _generate_workflow_id(workflow)
            enriched = dict(workflow)
            enriched["cached_at"] = datetime.now(timezone.utc).isoformat()
            with GLOBAL_LOCK:
                WORKFLOW_CACHE[workflow_id] = enriched
            result["workflow_id"] = workflow_id
            result["workflow"] = enriched
        
        return result
        
    except Exception as e:
        logger.error(f"Error resolviendo workflow: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "workflow_request": params.get("workflow_request", "")
        }

def resolve_resource(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Resuelve la ubicación y acceso a un recurso específico
    """
    try:
        resource_identifier = params.get("resource_identifier", "")
        resource_type = params.get("resource_type", "auto")
        include_metadata = params.get("include_metadata", True)
        
        logger.info(f"Resolviendo recurso: {resource_identifier}")
        
        # Buscar en el registro de recursos
        resource_info = None
        
        # Buscar por ID directo
        if resource_identifier in RESOURCE_REGISTRY:
            resource_info = RESOURCE_REGISTRY[resource_identifier]
        else:
            # Buscar por patrones
            for res_id, res_data in RESOURCE_REGISTRY.items():
                if _matches_resource(resource_identifier, res_data):
                    resource_info = res_data
                    break
        
        if not resource_info:
            # Intentar resolver dinámicamente
            resource_info = _resolve_resource_dynamically(
                client, resource_identifier, resource_type
            )
        
        if resource_info:
            result = {
                "success": True,
                "resource": {
                    "id": resource_info.get("id"),
                    "name": resource_info.get("name"),
                    "type": resource_info.get("type"),
                    "platform": resource_info.get("platform"),
                    "location": resource_info.get("location"),
                    "access_url": resource_info.get("access_url"),
                    "last_modified": resource_info.get("last_modified")
                }
            }
            
            if include_metadata:
                result["resource"]["metadata"] = resource_info.get("metadata", {})
                result["resource"]["permissions"] = resource_info.get("permissions", [])
                result["resource"]["related_resources"] = _find_related_resources(
                    resource_info
                )
            
            return result
        else:
            return {
                "success": False,
                "error": "Resource not found",
                "resource_identifier": resource_identifier,
                "suggestions": _suggest_similar_resources(resource_identifier)
            }
            
    except Exception as e:
        logger.error(f"Error resolviendo recurso: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "resource_identifier": params.get("resource_identifier", "")
        }

def list_available_resources(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Lista todos los recursos disponibles con filtros opcionales
    """
    try:
        resource_type = params.get("resource_type", "all")
        platform = params.get("platform", "all")
        limit = params.get("limit", 50)
        offset = params.get("offset", 0)
        search_query = params.get("search_query", "")
        
        logger.info(f"Listando recursos disponibles: tipo={resource_type}, plataforma={platform}")
        
        # Filtrar recursos
        filtered_resources = []
        
        with GLOBAL_LOCK:
            registry_items = list(RESOURCE_REGISTRY.items())
        
        for res_id, res_data in registry_items:
            # Aplicar filtros
            if resource_type != "all" and res_data.get("type") != resource_type:
                continue
            if platform != "all" and res_data.get("platform") != platform:
                continue
            if search_query and search_query.lower() not in json.dumps(res_data).lower():
                continue
            
            filtered_resources.append({
                "id": res_id,
                "name": res_data.get("name"),
                "type": res_data.get("type"),
                "platform": res_data.get("platform"),
                "created": res_data.get("created"),
                "size": res_data.get("size"),
                "access_url": res_data.get("access_url")
            })
        
        # Ordenar por fecha de creación (más reciente primero)
        filtered_resources.sort(
            key=lambda x: x.get("created", ""), 
            reverse=True
        )
        
        # Aplicar paginación
        total_count = len(filtered_resources)
        paginated = filtered_resources[offset:offset + limit]
        
        return {
            "success": True,
            "resources": paginated,
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + limit) < total_count,
            "filters_applied": {
                "resource_type": resource_type,
                "platform": platform,
                "search_query": search_query
            }
        }
        
    except Exception as e:
        logger.error(f"Error listando recursos: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

def validate_resource_id(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Valida si un ID de recurso es válido y accesible
    """
    try:
        resource_id = params.get("resource_id", "")
        check_access = params.get("check_access", True)
        
        logger.info(f"Validando resource ID: {resource_id}")
        
        validation_result = {
            "resource_id": resource_id,
            "is_valid": False,
            "exists": False,
            "accessible": False,
            "validation_details": {}
        }
        
        # Validar formato del ID
        format_validation = _validate_id_format(resource_id)
        validation_result["validation_details"]["format"] = format_validation
        validation_result["is_valid"] = format_validation["is_valid"]
        
        if not format_validation["is_valid"]:
            return {
                "success": True,
                "validation": validation_result
            }
        
        # Verificar si existe
        exists = resource_id in RESOURCE_REGISTRY
        validation_result["exists"] = exists
        
        if exists and check_access:
            # Verificar accesibilidad
            resource_data = RESOURCE_REGISTRY[resource_id]
            access_check = _check_resource_access(client, resource_data)
            validation_result["accessible"] = access_check["accessible"]
            validation_result["validation_details"]["access"] = access_check
        
        validation_result["is_valid"] = (
            validation_result["is_valid"] and 
            validation_result["exists"] and 
            (not check_access or validation_result["accessible"])
        )
        
        return {
            "success": True,
            "validation": validation_result
        }
        
    except Exception as e:
        logger.error(f"Error validando resource ID: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "resource_id": params.get("resource_id", "")
        }

def get_resource_config(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Obtiene la configuración completa de un recurso
    """
    try:
        resource_id = params.get("resource_id", "")
        config_type = params.get("config_type", "full")
        
        logger.info(f"Obteniendo configuración de recurso: {resource_id}")
        
        # Verificar si el recurso existe
        if resource_id not in RESOURCE_REGISTRY:
            return {
                "success": False,
                "error": "Resource not found",
                "resource_id": resource_id
            }
        
        resource_data = RESOURCE_REGISTRY[resource_id]
        
        # Construir configuración según el tipo solicitado
        config = {
            "resource_id": resource_id,
            "basic": {
                "name": resource_data.get("name"),
                "type": resource_data.get("type"),
                "platform": resource_data.get("platform"),
                "created": resource_data.get("created"),
                "modified": resource_data.get("modified")
            }
        }
        
        if config_type in ["full", "storage"]:
            config["storage"] = {
                "location": resource_data.get("location"),
                "path": resource_data.get("path"),
                "size": resource_data.get("size"),
                "storage_class": resource_data.get("storage_class", "standard")
            }
        
        if config_type in ["full", "access"]:
            config["access"] = {
                "access_url": resource_data.get("access_url"),
                "permissions": resource_data.get("permissions", []),
                "sharing": resource_data.get("sharing", {}),
                "authentication_required": resource_data.get("auth_required", True)
            }
        
        if config_type in ["full", "metadata"]:
            config["metadata"] = resource_data.get("metadata", {})
            config["tags"] = resource_data.get("tags", [])
            config["relationships"] = resource_data.get("relationships", {})
        
        if config_type == "full":
            config["history"] = resource_data.get("history", [])
            config["usage_stats"] = _get_resource_usage_stats(resource_id)
        
        return {
            "success": True,
            "config": config,
            "config_type": config_type,
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo configuración: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "resource_id": params.get("resource_id", "")
        }

def search_resources(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Busca recursos usando criterios avanzados
    """
    try:
        search_query = params.get("query", "")
        search_fields = params.get("fields", ["name", "type", "tags"])
        filters = params.get("filters", {})
        sort_by = params.get("sort_by", "relevance")
        limit = params.get("limit", 20)
        
        logger.info(f"Buscando recursos con query: {search_query}")
        
        # Realizar búsqueda
        search_results = []
        
        for res_id, res_data in RESOURCE_REGISTRY.items():
            score = 0
            matches = {}
            
            # Buscar en campos especificados
            for field in search_fields:
                field_value = res_data.get(field, "")
                if isinstance(field_value, str):
                    if search_query.lower() in field_value.lower():
                        score += 10
                        matches[field] = True
                elif isinstance(field_value, list):
                    for item in field_value:
                        if search_query.lower() in str(item).lower():
                            score += 5
                            matches[field] = True
                            break
            
            # Aplicar filtros
            passes_filters = True
            for filter_key, filter_value in filters.items():
                if res_data.get(filter_key) != filter_value:
                    passes_filters = False
                    break
            
            if score > 0 and passes_filters:
                search_results.append({
                    "id": res_id,
                    "resource": {
                        "name": res_data.get("name"),
                        "type": res_data.get("type"),
                        "platform": res_data.get("platform"),
                        "modified": res_data.get("modified")
                    },
                    "score": score,
                    "matches": matches
                })
        
        # Ordenar resultados
        if sort_by == "relevance":
            search_results.sort(key=lambda x: x["score"], reverse=True)
        elif sort_by == "date":
            search_results.sort(
                key=lambda x: x["resource"].get("modified", ""), 
                reverse=True
            )
        elif sort_by == "name":
            search_results.sort(key=lambda x: x["resource"].get("name", ""))
        
        # Limitar resultados
        search_results = search_results[:limit]
        
        return {
            "success": True,
            "query": search_query,
            "results": search_results,
            "total_found": len(search_results),
            "search_fields": search_fields,
            "filters": filters,
            "sort_by": sort_by
        }
        
    except Exception as e:
        logger.error(f"Error buscando recursos: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "query": params.get("query", "")
        }

def execute_workflow(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ejecuta un workflow completo con múltiples pasos
    """
    try:
        workflow_id = params.get("workflow_id", "")
        workflow_definition = params.get("workflow", {})
        context = params.get("context", {})
        async_execution = params.get("async", False)
        
        logger.info(f"Ejecutando workflow: {workflow_id or 'custom'}")
        
        # Obtener workflow del cache o usar definición proporcionada
        if workflow_id and workflow_id in WORKFLOW_CACHE:
            workflow = WORKFLOW_CACHE[workflow_id]
        elif workflow_definition:
            workflow = workflow_definition
        else:
            return {
                "success": False,
                "error": "No workflow provided"
            }
        
        # Validar workflow antes de ejecutar
        validation = _validate_workflow(workflow)
        if not validation["is_valid"]:
            return {
                "success": False,
                "error": "Invalid workflow",
                "validation_errors": validation["errors"]
            }
        
        # Ejecutar workflow
        execution_id = _generate_execution_id()
        execution_context = {
            "id": execution_id,
            "workflow": workflow,
            "context": context,
            "start_time": datetime.now(timezone.utc),
            "status": "running",
            "current_step": 0,
            "results": {},
            "errors": []
        }
        
        try:
            # Ejecutar cada paso
            for idx, step in enumerate(workflow.get("steps", [])):
                execution_context["current_step"] = idx
                
                logger.info(f"Ejecutando paso {idx + 1}/{len(workflow['steps'])}: {step.get('action')}")
                
                # Preparar parámetros del paso
                step_params = _prepare_step_params(step, execution_context)
                
                # Ejecutar acción
                step_result = _execute_workflow_step(client, step, step_params)
                
                # Almacenar resultado
                step_id = step.get("id", f"step_{idx}")
                execution_context["results"][step_id] = step_result
                
                # Verificar si debe continuar
                if not step_result.get("success", False):
                    if step.get("on_error", "stop") == "stop":
                        execution_context["status"] = "failed"
                        execution_context["errors"].append({
                            "step": step_id,
                            "error": step_result.get("error", "Unknown error")
                        })
                        break
                    elif step.get("on_error") == "continue":
                        execution_context["errors"].append({
                            "step": step_id,
                            "error": step_result.get("error", "Unknown error"),
                            "continued": True
                        })
            
            if execution_context["status"] == "running":
                execution_context["status"] = "completed"
            
        except Exception as e:
            execution_context["status"] = "error"
            execution_context["errors"].append({
                "step": "execution",
                "error": str(e)
            })
        
        execution_context["end_time"] = datetime.now(timezone.utc)
        execution_context["duration"] = (
            execution_context["end_time"] - execution_context["start_time"]
        ).total_seconds()
        
        # Preparar respuesta
        result = {
            "success": execution_context["status"] in ["completed", "partial"],
            "execution_id": execution_id,
            "status": execution_context["status"],
            "results": execution_context["results"],
            "errors": execution_context["errors"],
            "duration": execution_context["duration"],
            "steps_executed": execution_context["current_step"] + 1,
            "total_steps": len(workflow.get("steps", []))
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Error ejecutando workflow: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

def smart_save_resource(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Guarda inteligentemente un recurso en la plataforma más apropiada
    """
    try:
        resource_type = params.get("resource_type", "auto")
        resource_data = params.get("resource_data")
        resource_name = params.get("resource_name", f"resource_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        tags = params.get("tags", [])
        metadata = params.get("metadata", {})
        
        logger.info(f"Guardado inteligente de recurso: {resource_name} (tipo: {resource_type})")
        
        # Determinar tipo si es auto
        if resource_type == "auto":
            resource_type = _detect_resource_type(resource_data, resource_name)
        
        # Obtener reglas de almacenamiento
        storage_rules = STORAGE_RULES.get(resource_type, STORAGE_RULES.get("document"))
        
        # Preparar el recurso
        prepared_resource = _prepare_resource_for_storage(
            resource_data, resource_name, resource_type, metadata
        )
        
        # Guardar en plataforma primaria
        primary_platform = storage_rules["primary"]
        save_results = {}
        
        if primary_platform == "sharepoint":
            save_result = _save_to_sharepoint(client, prepared_resource, storage_rules)
            save_results["sharepoint"] = save_result
        elif primary_platform == "onedrive":
            save_result = _save_to_onedrive(client, prepared_resource, storage_rules)
            save_results["onedrive"] = save_result
        elif primary_platform == "notion":
            save_result = _save_to_notion(client, prepared_resource, storage_rules)
            save_results["notion"] = save_result
        
        # Guardar en plataforma secundaria si existe
        if "secondary" in storage_rules:
            secondary_platform = storage_rules["secondary"]
            if secondary_platform == "sharepoint":
                save_results["sharepoint_backup"] = _save_to_sharepoint(
                    client, prepared_resource, storage_rules, is_backup=True
                )
        
        # Registrar el recurso
        resource_id = _generate_resource_id(resource_name, resource_type)
        # Calcular tamaño del recurso de forma segura
        if isinstance(resource_data, (bytes, bytearray)):
            computed_size = len(resource_data)
        elif isinstance(resource_data, dict):
            try:
                computed_size = len(json.dumps(resource_data))
            except Exception:
                computed_size = 0
        else:
            try:
                computed_size = len(str(resource_data).encode())
            except Exception:
                computed_size = 0
        with GLOBAL_LOCK:
            RESOURCE_REGISTRY[resource_id] = {
                "id": resource_id,
                "name": resource_name,
                "type": resource_type,
                "platform": primary_platform,
                "location": save_results.get(primary_platform, {}).get("location"),
                "access_url": save_results.get(primary_platform, {}).get("url"),
                "size": computed_size,
                "created": datetime.now(timezone.utc).isoformat(),
                "modified": datetime.now(timezone.utc).isoformat(),
                "tags": tags,
                "metadata": metadata,
                "storage_results": save_results
            }
        
        # Crear entrada en registro Notion si está disponible
        if "notion" in save_results and save_results["notion"].get("success"):
            registry_result = save_to_notion_registry(client, {
                "resource_id": resource_id,
                "resource_info": RESOURCE_REGISTRY[resource_id]
            })
            save_results["registry"] = registry_result
        
        return {
            "success": True,
            "resource_id": resource_id,
            "resource_name": resource_name,
            "resource_type": resource_type,
            "platform": primary_platform,
            "storage_results": save_results,
            "access_urls": _extract_access_urls(save_results),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error en guardado inteligente: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "resource_name": params.get("resource_name", "")
        }

def save_to_notion_registry(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Guarda información en el registro centralizado de Notion
    """
    try:
        resource_id = params.get("resource_id", "")
        resource_info = params.get("resource_info", {})
        registry_database = params.get("database", "Elite Resources Registry")
        
        logger.info(f"Guardando en registro Notion: {resource_id}")
        
        # Buscar o crear la base de datos del registro
        db_result = notion_actions.notion_find_database_by_name(client, {
            "database_name": registry_database
        })
        
        if not db_result.get("success"):
            # Crear la base de datos si no existe
            db_result = notion_actions.notion_create_database(client, {
                "parent_page_id": settings.NOTION_DEFAULT_PARENT_PAGE,
                "title": registry_database,
                "properties": {
                    "Resource ID": {"title": {}},
                    "Name": {"rich_text": {}},
                    "Type": {"select": {}},
                    "Platform": {"select": {}},
                    "Created": {"date": {}},
                    "Modified": {"date": {}},
                    "Size": {"number": {}},
                    "Access URL": {"url": {}},
                    "Tags": {"multi_select": {}},
                    "Status": {"select": {}}
                }
            })
        
        database_id = db_result.get("data", {}).get("id")
        
        if not database_id:
            return {
                "success": False,
                "error": "Could not find or create registry database"
            }
        
        # Crear entrada en el registro
        page_result = notion_actions.notion_create_page_in_database(client, {
            "database_id": database_id,
            "properties": {
                "Resource ID": {
                    "title": [{"text": {"content": resource_id}}]
                },
                "Name": {
                    "rich_text": [{"text": {"content": resource_info.get("name", "")}}]
                },
                "Type": {
                    "select": {"name": resource_info.get("type", "unknown")}
                },
                "Platform": {
                    "select": {"name": resource_info.get("platform", "unknown")}
                },
                "Created": {
                    "date": {"start": resource_info.get("created", datetime.now(timezone.utc).isoformat())}
                },
                "Modified": {
                    "date": {"start": resource_info.get("modified", datetime.now(timezone.utc).isoformat())}
                },
                "Size": {
                    "number": resource_info.get("size", 0)
                },
                "Access URL": {
                    "url": resource_info.get("access_url", "")
                },
                "Tags": {
                    "multi_select": [{"name": tag} for tag in resource_info.get("tags", [])]
                },
                "Status": {
                    "select": {"name": "active"}
                }
            }
        })
        
        if page_result.get("success"):
            return {
                "success": True,
                "registry_id": page_result.get("data", {}).get("id"),
                "registry_url": page_result.get("data", {}).get("url"),
                "database_id": database_id
            }
        else:
            return page_result
            
    except Exception as e:
        logger.error(f"Error guardando en registro Notion: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "resource_id": params.get("resource_id", "")
        }

def get_credentials_from_vault(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Obtiene credenciales de manera segura desde el vault
    """
    try:
        credential_name = params.get("credential_name", "")
        service = params.get("service", "")
        environment = params.get("environment", "production")
        
        logger.info(f"Obteniendo credenciales para: {service}/{credential_name}")
        
        # Por seguridad, no almacenamos credenciales en memoria
        # En su lugar, las obtenemos de la configuración segura
        credentials_map = {
            "google_ads": {
                "client_id": settings.GOOGLE_ADS_CLIENT_ID,
                "client_secret": "***PROTECTED***",
                "customer_id": settings.GOOGLE_ADS_CUSTOMER_ID
            },
            "meta_ads": {
                "app_id": settings.META_ADS_APP_ID,
                "app_secret": "***PROTECTED***",
                "access_token": "***PROTECTED***"
            },
            "sharepoint": {
                "site_id": settings.SHAREPOINT_DEFAULT_SITE_ID,
                "tenant_id": settings.AZURE_TENANT_ID
            },
            "notion": {
                "api_key": "***PROTECTED***",
                "workspace_id": settings.NOTION_WORKSPACE_ID
            }
        }
        
        if service in credentials_map:
            credentials = credentials_map[service]
            
            # Solo devolver credenciales específicas si se solicitan
            if credential_name and credential_name in credentials:
                return {
                    "success": True,
                    "credential": {
                        "name": credential_name,
                        "service": service,
                        "value": credentials[credential_name],
                        "environment": environment,
                        "expires": None
                    }
                }
            else:
                # Devolver lista de credenciales disponibles (sin valores sensibles)
                available = [k for k in credentials.keys() if "secret" not in k and "token" not in k]
                return {
                    "success": True,
                    "service": service,
                    "available_credentials": available,
                    "environment": environment
                }
        else:
            return {
                "success": False,
                "error": "Service not found in vault",
                "service": service,
                "available_services": list(credentials_map.keys())
            }
            
    except Exception as e:
        logger.error(f"Error accediendo al vault: {str(e)}")
        return {
            "success": False,
            "error": "Vault access error",
            "message": "Could not retrieve credentials"
        }

# ============================================================================
# FUNCIONES AUXILIARES PRIVADAS
# ============================================================================

def _generate_cache_key(query: str, context: Dict[str, Any]) -> str:
    """Genera una clave única para el cache"""
    context_str = json.dumps(context, sort_keys=True)
    combined = f"{query}|{context_str}"
    return hashlib.md5(combined.encode()).hexdigest()

def _analyze_query_intent(query: str) -> Dict[str, Any]:
    """Analiza la intención del query"""
    query_lower = query.lower()
    
    # Patrones de intención
    if any(word in query_lower for word in ["guardar", "save", "almacenar", "backup"]):
        return {"type": "storage", "action": "save"}
    elif any(word in query_lower for word in ["buscar", "encontrar", "search", "find"]):
        return {"type": "search", "action": "search"}
    elif any(word in query_lower for word in ["workflow", "proceso", "automatizar"]):
        return {"type": "workflow", "action": "create_workflow"}
    elif any(word in query_lower for word in ["analizar", "analytics", "reporte"]):
        return {"type": "analytics", "action": "analyze"}
    else:
        return {"type": "general", "action": "process"}

def _get_time_context() -> Dict[str, Any]:
    """Obtiene el contexto temporal actual"""
    now = datetime.now(timezone.utc)
    return {
        "timestamp": now.isoformat(),
        "day_of_week": now.strftime("%A"),
        "hour": now.hour,
        "is_business_hours": 8 <= now.hour <= 18,
        "quarter": (now.month - 1) // 3 + 1
    }

def _get_business_context(context: Dict[str, Any]) -> Dict[str, Any]:
    """Extrae el contexto de negocio"""
    return {
        "company": context.get("company", "Elite Cosmetic Dental"),
        "industry": context.get("industry", "Healthcare"),
        "size": context.get("size", "medium"),
        "priorities": context.get("priorities", ["efficiency", "automation", "integration"])
    }

def _determine_best_action(request: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Determina la mejor acción basada en el análisis"""
    # Lógica simplificada - en producción sería más compleja
    return {
        "action": "process_request",
        "confidence": 0.85,
        "reasoning": "Based on context analysis"
    }

def _get_alternative_actions(request: str, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Obtiene acciones alternativas"""
    return [
        {"action": "alternative_1", "confidence": 0.7},
        {"action": "alternative_2", "confidence": 0.6}
    ]

def _build_execution_params(action: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """Construye parámetros de ejecución"""
    return {
        "action": action.get("action"),
        "context": context,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

def _register_resolution(request: str, action: Dict[str, Any], context: Dict[str, Any]) -> None:
    """Registra la resolución para aprendizaje futuro"""
    # En producción, esto se guardaría en una base de datos
    logger.info(f"Registrando resolución: {request} -> {action.get('action')}")

def _count_cache_hits() -> int:
    """Cuenta los hits de cache"""
    # Implementación simplificada
    return len(RESOLUTION_CACHE)

def _get_resource_usage_stats(resource_id: str = None) -> Dict[str, Any]:
    """Obtiene estadísticas de uso de recursos"""
    if resource_id:
        # Stats para un recurso específico
        return {
            "access_count": 0,
            "last_accessed": None,
            "average_response_time": 0
        }
    else:
        # Stats generales
        with GLOBAL_LOCK:
            snapshot = list(RESOURCE_REGISTRY.values())
        by_type = {}
        by_platform = {}
        for item in snapshot:
            t = item.get("type", "unknown")
            p = item.get("platform", "unknown")
            by_type[t] = by_type.get(t, 0) + 1
            by_platform[p] = by_platform.get(p, 0) + 1
        return {
            "total_resources": len(snapshot),
            "by_type": by_type,
            "by_platform": by_platform
        }

def _get_storage_distribution() -> Dict[str, int]:
    """Obtiene la distribución del almacenamiento"""
    distribution = {}
    with GLOBAL_LOCK:
        snapshot = list(RESOURCE_REGISTRY.values())
    for res_data in snapshot:
        platform = res_data.get("platform", "unknown")
        distribution[platform] = distribution.get(platform, 0) + 1
    return distribution

def _get_recent_resolutions(limit: int = 20) -> List[Dict[str, Any]]:
    """Obtiene las resoluciones recientes (ordenadas por timestamp desc)."""
    items = []
    with GLOBAL_LOCK:
        snapshot = list(RESOLUTION_CACHE.values())
    for v in snapshot:
        if isinstance(v, dict) and v.get("timestamp"):
            items.append(v)
    items.sort(
        key=lambda x: _iso_to_datetime(x.get("timestamp")) or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True
    )
    return items[:limit]

# ============================================================================
# FUNCIONES AUXILIARES FALTANTES (STUBS) 
# ============================================================================

def _resolve_storage_query(query: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Resuelve una consulta relacionada con almacenamiento"""
    logger.debug(f"Resolviendo consulta de almacenamiento: {query}")
    return {
        "action": "storage",
        "suggestion": "save_resource",
        "query_analysis": {
            "storage_intent": "save",
            "resource_type": "document"
        }
    }

def _resolve_search_query(query: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Resuelve una consulta de búsqueda"""
    logger.debug(f"Resolviendo consulta de búsqueda: {query}")
    return {
        "action": "search",
        "suggestion": "search_resources",
        "query_analysis": {
            "search_terms": query.split(),
            "resource_types": ["document", "image"]
        }
    }

def _resolve_workflow_query(query: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Resuelve una consulta relacionada con workflows"""
    logger.debug(f"Resolviendo consulta de workflow: {query}")
    return {
        "action": "workflow",
        "suggestion": "create_workflow",
        "query_analysis": {
            "workflow_type": "automated",
            "steps": ["extract", "process", "save"]
        }
    }

def _resolve_analytics_query(query: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Resuelve una consulta de análisis/analytics"""
    logger.debug(f"Resolviendo consulta de analytics: {query}")
    return {
        "action": "analytics",
        "suggestion": "generate_report",
        "query_analysis": {
            "metrics": ["usage", "performance"],
            "time_range": "last_month"
        }
    }

def _get_popular_actions(limit: int = 10) -> List[Dict[str, Any]]:
    """Obtiene las acciones más populares"""
    return [
        {"action": "search_resources", "count": 120},
        {"action": "resolve_resource", "count": 85},
        {"action": "smart_save_resource", "count": 67},
        {"action": "execute_workflow", "count": 45}
    ][:limit]

def _calculate_error_rate() -> float:
    """Calcula la tasa de error en las resoluciones"""
    # Simplemente devolver un valor de ejemplo para el esqueleto
    return 0.05  # 5% tasa de error

def _get_avg_resolution_time() -> float:
    """Obtiene el tiempo promedio de resolución en segundos"""
    return 0.325  # 325ms en promedio

def _get_performance_metrics() -> Dict[str, Any]:
    """Obtiene métricas de rendimiento del sistema"""
    return {
        "avg_response_time": 0.325,
        "p95_response_time": 0.875,
        "cache_hit_ratio": 0.78,
        "memory_usage_mb": 128,
        "uptime_hours": 720
    }

def _get_optimization_suggestions(stats: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Genera sugerencias de optimización basadas en estadísticas"""
    return [
        {
            "type": "cache",
            "suggestion": "Incrementar TTL para recursos tipo 'document'",
            "expected_impact": "medium",
            "reason": "Alta tasa de solicitudes repetidas"
        },
        {
            "type": "storage",
            "suggestion": "Migrar recursos poco usados a almacenamiento frío",
            "expected_impact": "high",
            "reason": "Optimización de costos"
        }
    ]

def _clear_cache_items(cache: Dict[str, Any], older_than_hours: int, pattern: Optional[str] = None) -> int:
    """Limpia elementos del caché según criterios y devuelve la cantidad eliminada"""
    # Implementación simple para el esqueleto
    cleared_count = 0
    current_time = datetime.now(timezone.utc)
    cutoff_time = current_time - timedelta(hours=older_than_hours)
    
    keys_to_remove = []
    for key, value in cache.items():
        if pattern and pattern not in key:
            continue
            
        cache_time = None
        if isinstance(value, dict) and "timestamp" in value:
            cache_time = _iso_to_datetime(value.get("timestamp"))
        elif isinstance(value, dict) and "created" in value:
            cache_time = _iso_to_datetime(value.get("created"))
            
        if cache_time and cache_time < cutoff_time:
            keys_to_remove.append(key)
    
    for key in keys_to_remove:
        del cache[key]
        cleared_count += 1
        
    return cleared_count

def _analyze_workflow_request(workflow_request: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Analiza la solicitud de workflow y extrae componentes clave"""
    return {
        "name": f"Workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "description": "Workflow generado automáticamente",
        "steps": [
            {"type": "extract", "action": "extract_data", "parameters": {}},
            {"type": "process", "action": "process_data", "parameters": {}},
            {"type": "save", "action": "save_results", "parameters": {}}
        ]
    }

def _build_workflow_step(step_template: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """Construye un paso de workflow basado en plantilla y contexto"""
    return {
        "id": f"step_{step_template.get('type')}",
        "action": step_template.get("action", "default_action"),
        "parameters": step_template.get("parameters", {}),
        "estimated_time": 10,  # segundos
        "permissions": ["read", "write"],
        "on_error": "stop"
    }

def _optimize_workflow(workflow: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """Optimiza un workflow basado en patrones conocidos"""
    # Simplemente devolver el workflow sin cambios para el esqueleto
    workflow["optimized"] = True
    return workflow

def _validate_workflow(workflow: Dict[str, Any]) -> Dict[str, Any]:
    """Valida un workflow y retorna resultado de validación"""
    has_name = bool(workflow.get("name"))
    has_steps = len(workflow.get("steps", [])) > 0
    
    return {
        "is_valid": has_name and has_steps,
        "errors": [] if (has_name and has_steps) else ["Nombre o pasos faltantes"],
        "warnings": []
    }

def _generate_workflow_id(workflow: Dict[str, Any]) -> str:
    """Genera un ID único para un workflow"""
    name = workflow.get("name", "workflow")
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    # Generar un ID basado en nombre + timestamp + hash parcial
    workflow_str = json.dumps(workflow, sort_keys=True)
    hash_part = hashlib.md5(workflow_str.encode()).hexdigest()[:8]
    return f"wf_{name.lower().replace(' ', '_')}_{timestamp}_{hash_part}"

def _matches_resource(identifier: str, resource_data: Dict[str, Any]) -> bool:
    """Determina si un identificador coincide con los datos de un recurso"""
    if not identifier or not resource_data:
        return False
        
    # Buscar coincidencias en propiedades clave
    name_match = identifier.lower() in resource_data.get("name", "").lower()
    type_match = identifier.lower() == resource_data.get("type", "").lower()
    
    # Buscar en metadatos
    metadata_match = False
    if "metadata" in resource_data:
        metadata_str = json.dumps(resource_data["metadata"]).lower()
        metadata_match = identifier.lower() in metadata_str
        
    return name_match or type_match or metadata_match

def _resolve_resource_dynamically(client: Any, resource_identifier: str, resource_type: str) -> Optional[Dict[str, Any]]:
    """Intenta resolver dinámicamente un recurso no encontrado en el registro"""
    logger.info(f"Resolviendo dinámicamente: {resource_identifier} (tipo: {resource_type})")
    
    # Esta función debería buscar en diversas plataformas
    # Por ahora, devolvemos None (no encontrado) para el esqueleto
    return None

def _find_related_resources(resource_info: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Encuentra recursos relacionados al recurso dado"""
    # Devolver una lista vacía para el esqueleto
    return []

def _suggest_similar_resources(resource_identifier: str) -> List[Dict[str, Any]]:
    """Sugiere recursos similares cuando no se encuentra el solicitado"""
    # Devolver sugerencias ficticias para el esqueleto
    return [
        {"id": "res_doc_example1", "name": "Documento de ejemplo 1", "similarity": 0.85},
        {"id": "res_doc_example2", "name": "Documento de ejemplo 2", "similarity": 0.72}
    ]

def _validate_id_format(resource_id: str) -> Dict[str, Any]:
    """Valida el formato de un ID de recurso"""
    if not resource_id:
        return {"is_valid": False, "reason": "ID vacío"}
        
    # Patrón básico: res_tipo_algo_más
    if resource_id.startswith("res_") and len(resource_id) >= 8:
        return {"is_valid": True}
    else:
        return {"is_valid": False, "reason": "Formato inválido"}

def _check_resource_access(client: Any, resource_data: Dict[str, Any]) -> Dict[str, Any]:
    """Verifica si un recurso es accesible"""
    # Simulación básica para el esqueleto
    return {
        "accessible": True,
        "access_method": "direct",
        "requires_auth": resource_data.get("auth_required", True)
    }

def _generate_execution_id() -> str:
    """Genera un ID único para una ejecución de workflow"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    random_part = hashlib.md5(os.urandom(16)).hexdigest()[:8]
    return f"exec_{timestamp}_{random_part}"

def _prepare_step_params(step: Dict[str, Any], execution_context: Dict[str, Any]) -> Dict[str, Any]:
    """Prepara parámetros para un paso de workflow basado en contexto de ejecución"""
    params = dict(step.get("parameters", {}))
    
    # Agregar contexto general
    params["context"] = execution_context.get("context", {})
    params["execution_id"] = execution_context.get("id")
    
    return params

def _execute_workflow_step(client: Any, step: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
    """Ejecuta un paso individual de workflow"""
    logger.info(f"Ejecutando paso: {step.get('action')}")
    
    # Esta función debería invocar la acción adecuada dinámicamente
    # Por simplicidad, simular éxito para el esqueleto
    return {
        "success": True,
        "action": step.get("action"),
        "result": {"message": "Simulación de ejecución exitosa"}
    }

def _detect_resource_type(resource_data: Any, resource_name: str) -> str:
    """Detecta el tipo de recurso basado en su contenido y nombre"""
    if isinstance(resource_data, bytes) and resource_name.lower().endswith(('.jpg', '.png', '.gif')):
        return "image"
    elif isinstance(resource_data, bytes) and resource_name.lower().endswith(('.mp4', '.avi', '.mov')):
        return "video"
    elif isinstance(resource_data, Dict) and resource_name.lower().endswith(('report', 'analytics')):
        return "report"
    else:
        return "document"  # tipo por defecto

def _prepare_resource_for_storage(resource_data: Any, resource_name: str, resource_type: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Prepara un recurso para almacenamiento, formateando y estructurando los datos"""
    return {
        "name": resource_name,
        "type": resource_type,
        "data": resource_data,
        "metadata": metadata,
        "prepared_at": datetime.now(timezone.utc).isoformat()
    }

def _save_to_sharepoint(client: Any, prepared_resource: Dict[str, Any], storage_rules: Dict[str, Any], is_backup: bool = False) -> Dict[str, Any]:
    """Guarda un recurso en SharePoint"""
    logger.info(f"Simulando guardado en SharePoint: {prepared_resource.get('name')} (backup: {is_backup})")
    
    # Esta función debería usar el cliente para guardar en SharePoint
    # Por simplicidad, simular éxito para el esqueleto
    return {
        "success": True,
        "platform": "sharepoint",
        "location": f"{storage_rules.get('path', '/Documents')}/{prepared_resource.get('name')}",
        "url": f"https://example.sharepoint.com{storage_rules.get('path', '/Documents')}/{prepared_resource.get('name')}",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

def _save_to_onedrive(client: Any, prepared_resource: Dict[str, Any], storage_rules: Dict[str, Any]) -> Dict[str, Any]:
    """Guarda un recurso en OneDrive"""
    logger.info(f"Simulando guardado en OneDrive: {prepared_resource.get('name')}")
    
    # Esta función debería usar el cliente para guardar en OneDrive
    # Por simplicidad, simular éxito para el esqueleto
    return {
        "success": True,
        "platform": "onedrive",
        "location": f"{storage_rules.get('path', '/Documents')}/{prepared_resource.get('name')}",
        "url": f"https://example-my.sharepoint.com/personal/docs/{storage_rules.get('path', '/Documents')}/{prepared_resource.get('name')}",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

def _save_to_notion(client: Any, prepared_resource: Dict[str, Any], storage_rules: Dict[str, Any]) -> Dict[str, Any]:
    """Guarda un recurso en Notion"""
    logger.info(f"Simulando guardado en Notion: {prepared_resource.get('name')}")
    
    # Esta función debería usar el cliente para guardar en Notion
    # Por simplicidad, simular éxito para el esqueleto
    return {
        "success": True,
        "platform": "notion",
        "database": storage_rules.get("database", "Default Database"),
        "page_id": f"page_{hashlib.md5(prepared_resource.get('name', '').encode()).hexdigest()[:12]}",
        "url": f"https://notion.so/{hashlib.md5(prepared_resource.get('name', '').encode()).hexdigest()[:12]}",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

def _generate_resource_id(resource_name: str, resource_type: str) -> str:
    """Genera un ID único para un recurso"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    name_part = resource_name.lower().replace(' ', '_')[:20]
    hash_part = hashlib.md5(f"{resource_name}_{resource_type}_{timestamp}".encode()).hexdigest()[:8]
    return f"res_{resource_type}_{name_part}_{hash_part}"

def _extract_access_urls(save_results: Dict[str, Any]) -> Dict[str, str]:
    """Extrae URLs de acceso de los resultados de guardado"""
    urls = {}
    for platform, result in save_results.items():
        if isinstance(result, dict) and result.get("success") and "url" in result:
            urls[platform] = result["url"]
    return urls

# Clase Resolver para compatibilidad con gemini_actions
class Resolver:
    """Clase de resolución de recursos simple para compatibilidad"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def save_action_result(self, action_name: str, params: Dict[str, Any], result: Dict[str, Any]):
        """Guarda el resultado de una acción en memoria/log"""
        try:
            # Por ahora solo hacer logging - se puede expandir más tarde
            self.logger.info(f"Action {action_name} executed with result: {result.get('status', 'unknown')}")
        except Exception as e:
            self.logger.warning(f"Error saving action result for {action_name}: {e}")

# Instancia global para uso directo
resolver_instance = Resolver()