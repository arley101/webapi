# app/actions/vivainsights_actions.py
import logging
import requests # Para requests.exceptions.HTTPError
import json # Para el helper de error
from typing import Dict, List, Optional, Any

from app.core.config import settings
from app.shared.helpers.http_client import AuthenticatedHttpClient

logger = logging.getLogger(__name__)

def _handle_viva_insights_api_error(e: Exception, action_name: str, params_for_log: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Helper para manejar errores de Viva Insights API."""
    log_message = f"Error en Viva Insights Action '{action_name}'"
    if params_for_log:
        log_message += f" con params: {params_for_log}"
    
    logger.error(f"{log_message}: {type(e).__name__} - {str(e)}", exc_info=True)
    
    details_str = str(e)
    status_code_int = 500
    graph_error_code = None # Específico para errores de Graph

    if isinstance(e, requests.exceptions.HTTPError) and e.response is not None:
        status_code_int = e.response.status_code
        try:
            error_data = e.response.json()
            error_info = error_data.get("error", {})
            details_str = error_info.get("message", e.response.text)
            graph_error_code = error_info.get("code")
        except json.JSONDecodeError: 
            details_str = e.response.text[:500] if e.response.text else "No response body"
            
    return {
        "status": "error",
        "action": action_name,
        "message": f"Error en {action_name}: {details_str}",
        "details": str(e) if not isinstance(e, requests.exceptions.HTTPError) else details_str,
        "http_status": status_code_int,
        "graph_error_code": graph_error_code
    }

# --- FUNCIONES DE ACCIÓN PARA VIVA INSIGHTS ---

def get_my_analytics(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "viva_get_my_analytics"
    logger.info(f"Ejecutando {action_name} con params: {params}")
    
    user_identifier: Optional[str] = params.get("user_id") # UPN o ID del usuario

    url: str
    log_context_user: str

    if user_identifier:
        # Intentar usar el endpoint /users/{id}/analytics/activityStatistics
        # Se necesita el permiso de aplicación correcto (ej. Analytics.Read.All si existe, o User.Read.All podría no ser suficiente para esto)
        url = f"{settings.GRAPH_API_BASE_URL}/users/{user_identifier}/analytics/activityStatistics"
        log_context_user = f"usuario '{user_identifier}'"
        logger.info(f"Obteniendo estadísticas de actividad de Viva Insights para {log_context_user}.")
        logger.warning(f"La ruta '/users/{{id}}/analytics/activityStatistics' con permisos de aplicación puede tener limitaciones o no ser soportada por Graph API para todos los tenants/escenarios. Verifique los permisos y la documentación de Graph.")
    else:
        # El endpoint /me/analytics/activityStatistics no tiene sentido con un token de aplicación puro.
        # Devolver un error si no se proporciona user_id.
        logger.error(f"{action_name}: Parámetro 'user_id' (UPN o ID del usuario) es requerido para obtener analíticas con permisos de aplicación.")
        return {
            "status": "error", 
            "action": action_name,
            "message": "'user_id' (UPN o ID del usuario) es requerido para esta acción con permisos de aplicación.",
            "http_status": 400
        }
        
    odata_params: Dict[str, Any] = {}
    if params.get("$select"): 
        odata_params["$select"] = params["$select"]
    if params.get("$filter"): # La documentación para activityStatistics no menciona $filter directamente.
        odata_params["$filter"] = params["$filter"]
        logger.warning(f"{action_name}: El parámetro $filter puede no ser soportado por el endpoint activityStatistics.")
    if params.get("$top"): odata_params["$top"] = params["$top"] # Para paginación si la API lo soporta


    logger.info(f"Solicitando estadísticas de actividad para {log_context_user}. Select: {odata_params.get('$select')}, Filter: {odata_params.get('$filter')}, Top: {odata_params.get('$top')}")
    
    # Permisos como Analytics.Read podrían ser necesarios. .default lo cubriría si están concedidos.
    # Si existe un Analytics.Read.All, sería más apropiado para /users/{id}/...
    analytics_scope = getattr(settings, 'GRAPH_SCOPE_ANALYTICS_READ_ALL', # Suponiendo que podría existir
                              getattr(settings, 'GRAPH_SCOPE_ANALYTICS_READ', settings.GRAPH_API_DEFAULT_SCOPE))
    try:
        response = client.get(url, scope=analytics_scope, params=odata_params if odata_params else None)
        analytics_data = response.json()
        # La respuesta es una colección de objetos activityStatistic bajo la clave "value"
        return {"status": "success", "data": analytics_data.get("value", [])}
    except requests.exceptions.HTTPError as http_err:
        if http_err.response is not None and http_err.response.status_code == 403:
            details = http_err.response.text if http_err.response.text else "Acceso prohibido."
            logger.error(f"Acceso prohibido (403) a Viva Insights para {log_context_user}: {details[:300]}")
            return {
                "status": "error", 
                "action": action_name,
                "message": f"Acceso prohibido a Viva Insights para {log_context_user}. Verifique la licencia, configuración del servicio y permisos de la aplicación.", 
                "http_status": 403, 
                "details": details,
                "graph_error_code": "AccessDenied" 
            }
        return _handle_viva_insights_api_error(http_err, action_name, params)
    except Exception as e:
        return _handle_viva_insights_api_error(e, action_name, params)

def get_focus_plan(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "viva_get_focus_plan"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    user_identifier: Optional[str] = params.get("user_id") # UPN o ID del usuario
    if not user_identifier:
        return {"status": "error", "action": action_name, "message": "'user_id' es requerido.", "http_status": 400}

    logger.info(f"Intentando obtener información del plan de concentración para usuario '{user_identifier}' (basado en estadísticas de actividad 'focus').")

    # Reutilizar get_my_analytics para obtener todas las estadísticas del usuario especificado.
    analytics_params: Dict[str, Any] = {"user_id": user_identifier} # Pasar el user_id
    if params.get("$select_analytics"): 
        analytics_params["$select"] = params["$select_analytics"]

    analytics_result = get_my_analytics(client, analytics_params)

    if analytics_result.get("status") == "success":
        all_activities_stats = analytics_result.get("data", [])
        focus_stats_entries: List[Dict[str, Any]] = []
        
        if isinstance(all_activities_stats, list):
            for stat_entry in all_activities_stats:
                if isinstance(stat_entry, dict) and stat_entry.get("activity", "").lower() == "focus":
                    focus_stats_entries.append(stat_entry)
        
        if focus_stats_entries:
            logger.info(f"Estadísticas de tiempo de concentración ('focus') encontradas para '{user_identifier}': {len(focus_stats_entries)} entrada(s).")
            return {
                "status": "success", 
                "data": focus_stats_entries, 
                "message": (
                    f"Estadísticas de tiempo de concentración para '{user_identifier}' obtenidas. Para ver eventos de calendario "
                    "de focus time, use la acción 'calendar_list_events' con el filtro de categoría o asunto apropiado."
                )
            }
        else:
            logger.info(f"No se encontraron estadísticas específicas para la actividad 'focus' en los datos de analíticas de '{user_identifier}'.")
            return {
                "status": "success", 
                "data": [],
                "message": f"No se encontraron estadísticas de tiempo de concentración para '{user_identifier}'. El plan podría no estar activo o no haber datos recientes."
            }
    else:
        # Propagar el error de get_my_analytics
        logger.error(f"No se pudo obtener la información del plan de concentración para '{user_identifier}' porque falló la obtención de analíticas: {analytics_result.get('message')}")
        propagated_error = analytics_result.copy()
        propagated_error["action"] = action_name # Asegurar que la acción en el error sea la correcta
        return propagated_error

# --- FIN DEL MÓDULO actions/vivainsights_actions.py ---