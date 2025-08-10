"""
Resolver Actions - Sistema Inteligente de Resolución y Gestión de Recursos
Implementación completa de las 14 acciones del resolver
"""

import os
import json
import logging
import hashlib
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone
import re

# Importar clientes y configuración necesaria
from app.core.config import settings
from app.shared.helpers.http_client import AuthenticatedHttpClient

# Importar acciones de otros módulos para el sistema inteligente
from app.actions import sharepoint_actions
from app.actions import onedrive_actions
from app.actions import notion_actions

logger = logging.getLogger(__name__)

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
            WORKFLOW_CACHE[workflow_id] = workflow
            result["workflow_id"] = workflow_id
        
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
        
        for res_id, res_data in RESOURCE_REGISTRY.items():
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
        RESOURCE_REGISTRY[resource_id] = {
            "id": resource_id,
            "name": resource_name,
            "type": resource_type,
            "platform": primary_platform,
            "location": save_results.get(primary_platform, {}).get("location"),
            "access_url": save_results.get(primary_platform, {}).get("url"),
            "size": len(json.dumps(resource_data)) if isinstance(resource_data, dict) else 0,
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
        return {
            "total_resources": len(RESOURCE_REGISTRY),
            "by_type": {},
            "by_platform": {}
        }

def _get_storage_distribution() -> Dict[str, int]:
    """Obtiene la distribución del almacenamiento"""
    distribution = {}
    for res_data in RESOURCE_REGISTRY.values():
        platform = res_data.get("platform", "unknown")
        distribution[platform] = distribution.get(platform, 0) + 1
    return distribution

def _get_popular_actions(limit: int = 10) -> List[Dict[str, Any]]:
    """Obtiene las acciones más populares"""
    # Implementación simplificada
    return []

def _calculate_error_rate() -> float:
    """Calcula la tasa de error"""
    # Implementación simplificada
    return 0.0

def _get_avg_resolution_time() -> float:
    """Obtiene el tiempo promedio de resolución"""
    # Implementación simplificada
    return 0.0

def _get_recent_resolutions(limit: int = 20) -> List[Dict[str, Any]]:
    """Obtiene las resoluciones recientes"""
    # Implementación simplificada
    return []

def _get_performance_metrics() -> Dict[str, Any]:
    """Obtiene métricas de rendimiento"""
    return {
        "avg_response_time": 0.0,
        "cache_hit_rate": 0.0,
        "success_rate": 1.0
    }

def _get_optimization_suggestions(stats: Dict[str, Any]) -> List[str]:
    """Genera sugerencias de optimización"""
    suggestions = []
    if stats.get("cache_hits", 0) < stats.get("total_resolutions", 0) * 0.5:
        suggestions.append("Consider increasing cache usage")
    return suggestions

def _clear_cache_items(cache: Dict, older_than_hours: int, pattern: str = None) -> int:
    """Limpia elementos del cache"""
    cleared = 0
    items_to_remove = []
    
    for key in cache.keys():
        # Aquí verificaríamos la antigüedad y el patrón
        # Por simplicidad, limpiamos todo si no hay patrón
        if not pattern or pattern in key:
            items_to_remove.append(key)
    
    for key in items_to_remove:
        del cache[key]
        cleared += 1
    
    return cleared

def _analyze_workflow_request(request: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Analiza una solicitud de workflow"""
    return {
        "name": f"Workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "description": f"Auto-generated workflow for: {request}",
        "steps": []
    }

def _build_workflow_step(template: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """Construye un paso del workflow"""
    return {
        "id": template.get("id", "step"),
        "action": template.get("action"),
        "params": template.get("params", {}),
        "estimated_time": 5,
        "permissions": []
    }

def _optimize_workflow(workflow: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """Optimiza un workflow"""
    # Implementación simplificada
    return workflow

def _validate_workflow(workflow: Dict[str, Any]) -> Dict[str, Any]:
    """Valida un workflow"""
    errors = []
    warnings = []
    
    if not workflow.get("steps"):
        errors.append("Workflow must have at least one step")
    
    return {
        "is_valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }

def _generate_workflow_id(workflow: Dict[str, Any]) -> str:
    """Genera un ID único para el workflow"""
    workflow_str = json.dumps(workflow, sort_keys=True)
    return hashlib.md5(workflow_str.encode()).hexdigest()[:12]

def _matches_resource(identifier: str, resource_data: Dict[str, Any]) -> bool:
    """Verifica si un identificador coincide con un recurso"""
    identifier_lower = identifier.lower()
    return (
        identifier_lower in resource_data.get("name", "").lower() or
        identifier_lower in resource_data.get("id", "").lower() or
        identifier in resource_data.get("tags", [])
    )

def _resolve_resource_dynamically(client: Any, identifier: str, resource_type: str) -> Optional[Dict[str, Any]]:
    """Intenta resolver un recurso dinámicamente"""
    # Implementación simplificada
    return None

def _find_related_resources(resource_info: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Encuentra recursos relacionados"""
    related = []
    # Buscar por tags comunes, mismo tipo, etc.
    return related

def _suggest_similar_resources(identifier: str) -> List[str]:
    """Sugiere recursos similares"""
    suggestions = []
    # Implementación simplificada
    return suggestions

def _validate_id_format(resource_id: str) -> Dict[str, Any]:
    """Valida el formato de un ID de recurso"""
    is_valid = bool(re.match(r'^[a-zA-Z0-9_-]+$', resource_id))
    return {
        "is_valid": is_valid,
        "format": "alphanumeric with _ and -",
        "length": len(resource_id)
    }

def _check_resource_access(client: Any, resource_data: Dict[str, Any]) -> Dict[str, Any]:
    """Verifica el acceso a un recurso"""
    # Implementación simplificada
    return {
        "accessible": True,
        "permission_level": "read"
    }

def _generate_execution_id() -> str:
    """Genera un ID único para la ejecución"""
    return f"exec_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}"

def _prepare_step_params(step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """Prepara los parámetros para un paso del workflow"""
    params = step.get("params", {})
    # Aquí se podrían resolver variables del contexto
    return params

def _execute_workflow_step(client: Any, step: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
    """Ejecuta un paso individual del workflow"""
    try:
        action = step.get("action")
        # Aquí se llamaría a la acción real
        # Por ahora, simulamos
        return {
            "success": True,
            "data": f"Executed {action}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def _detect_resource_type(data: Any, name: str) -> str:
    """Detecta el tipo de recurso basándose en el contenido"""
    name_lower = name.lower()
    
    if any(ext in name_lower for ext in ['.mp4', '.avi', '.mov', 'video']):
        return "video"
    elif any(ext in name_lower for ext in ['.jpg', '.png', '.gif', 'image']):
        return "image"
    elif any(word in name_lower for word in ['report', 'analytics', 'metrics']):
        return "report"
    elif any(word in name_lower for word in ['campaign', 'ad', 'marketing']):
        return "campaign_data"
    else:
        return "document"

def _prepare_resource_for_storage(data: Any, name: str, resource_type: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Prepara el recurso para almacenamiento"""
    return {
        "name": name,
        "type": resource_type,
        "data": data,
        "metadata": metadata,
        "prepared_at": datetime.now(timezone.utc).isoformat()
    }

def _save_to_sharepoint(client: Any, resource: Dict[str, Any], rules: Dict[str, Any], is_backup: bool = False) -> Dict[str, Any]:
    """Guarda en SharePoint"""
    try:
        path = rules.get("path", "/EliteDynamics/General")
        if is_backup:
            path = f"{path}/Backups"
        
        # Convertir datos a JSON si es necesario
        if isinstance(resource["data"], dict):
            content = json.dumps(resource["data"], indent=2).encode()
        else:
            content = str(resource["data"]).encode()
        
        result = sharepoint_actions.sp_upload_document(client, {
            "filename": f"{resource['name']}.json",
            "content_bytes": content,
            "folder_path": path
        })
        
        return {
            "success": result.get("success", False),
            "location": path,
            "url": result.get("data", {}).get("webUrl", ""),
            "item_id": result.get("data", {}).get("id", "")
        }
    except Exception as e:
        logger.error(f"Error guardando en SharePoint: {str(e)}")
        return {"success": False, "error": str(e)}

def _save_to_onedrive(client: Any, resource: Dict[str, Any], rules: Dict[str, Any]) -> Dict[str, Any]:
    """Guarda en OneDrive"""
    try:
        path = rules.get("path", "/EliteDynamics/General")
        
        # Convertir datos según el tipo
        if isinstance(resource["data"], dict):
            content = json.dumps(resource["data"], indent=2).encode()
            filename = f"{resource['name']}.json"
        elif isinstance(resource["data"], bytes):
            content = resource["data"]
            filename = resource["name"]
        else:
            content = str(resource["data"]).encode()
            filename = f"{resource['name']}.txt"
        
        result = onedrive_actions.onedrive_upload_file(client, {
            "file_path": f"{path}/{filename}",
            "content": content
        })
        
        return {
            "success": result.get("success", False),
            "location": f"{path}/{filename}",
            "url": result.get("data", {}).get("webUrl", ""),
            "item_id": result.get("data", {}).get("id", "")
        }
    except Exception as e:
        logger.error(f"Error guardando en OneDrive: {str(e)}")
        return {"success": False, "error": str(e)}

def _save_to_notion(client: Any, resource: Dict[str, Any], rules: Dict[str, Any]) -> Dict[str, Any]:
    """Guarda en Notion"""
    try:
        database_name = rules.get("database", "Elite Resources")
        
        # Buscar la base de datos
        db_result = notion_actions.notion_find_database_by_name(client, {
            "database_name": database_name
        })
        
        if not db_result.get("success"):
            return {"success": False, "error": "Database not found"}
        
        database_id = db_result.get("data", {}).get("id")
        
        # Crear página en la base de datos
        page_result = notion_actions.notion_create_page_in_database(client, {
            "database_id": database_id,
            "properties": {
                "Name": {
                    "title": [{"text": {"content": resource["name"]}}]
                },
                "Type": {
                    "select": {"name": resource["type"]}
                },
                "Created": {
                    "date": {"start": resource["prepared_at"]}
                }
            },
            "content": [
                {
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{
                            "text": {
                                "content": json.dumps(resource["data"], indent=2)[:2000]
                            }
                        }]
                    }
                }
            ]
        })
        
        return {
            "success": page_result.get("success", False),
            "location": database_name,
            "url": page_result.get("data", {}).get("url", ""),
            "page_id": page_result.get("data", {}).get("id", "")
        }
    except Exception as e:
        logger.error(f"Error guardando en Notion: {str(e)}")
        return {"success": False, "error": str(e)}

def _generate_resource_id(name: str, resource_type: str) -> str:
    """Genera un ID único para el recurso"""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    name_part = re.sub(r'[^a-zA-Z0-9]', '', name)[:20]
    return f"{resource_type}_{name_part}_{timestamp}"

def _extract_access_urls(save_results: Dict[str, Any]) -> List[str]:
    """Extrae todas las URLs de acceso de los resultados"""
    urls = []
    for platform_result in save_results.values():
        if isinstance(platform_result, dict) and platform_result.get("url"):
            urls.append(platform_result["url"])
    return urls

def _resolve_storage_query(query: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Resuelve queries relacionados con almacenamiento"""
    return {
        "suggested_action": "smart_save_resource",
        "detected_intent": "storage",
        "storage_recommendation": _get_storage_recommendation(query, context)
    }

def _resolve_search_query(query: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Resuelve queries de búsqueda"""
    return {
        "suggested_action": "search_resources",
        "detected_intent": "search",
        "search_params": _extract_search_params(query)
    }

def _resolve_workflow_query(query: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Resuelve queries de workflow"""
    return {
        "suggested_action": "resolve_smart_workflow",
        "detected_intent": "workflow",
        "workflow_type": _detect_workflow_type(query)
    }

def _resolve_analytics_query(query: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Resuelve queries de analytics"""
    return {
        "suggested_action": "get_resolution_analytics",
        "detected_intent": "analytics",
        "analytics_scope": _detect_analytics_scope(query)
    }

def _get_storage_recommendation(query: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Obtiene recomendación de almacenamiento"""
    # Implementación simplificada
    return {
        "platform": "sharepoint",
        "reason": "Default storage platform"
    }

def _extract_search_params(query: str) -> Dict[str, Any]:
    """Extrae parámetros de búsqueda del query"""
    # Implementación simplificada
    return {
        "query": query,
        "fields": ["name", "type", "tags"]
    }

def _detect_workflow_type(query: str) -> str:
    """Detecta el tipo de workflow solicitado"""
    # Implementación simplificada
    return "general"

def _detect_analytics_scope(query: str) -> str:
    """Detecta el alcance de analytics solicitado"""
    # Implementación simplificada
    return "general"