# app/actions/bookings_actions.py
import logging
import requests 
import json 
from typing import Dict, List, Optional, Any

from app.core.config import settings
from app.shared.helpers.http_client import AuthenticatedHttpClient

logger = logging.getLogger(__name__)

def _handle_bookings_api_error(e: Exception, action_name: str, params_for_log: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    log_message = f"Error en Bookings action '{action_name}'"
    safe_params = {k: (v if k not in ['appointment_payload'] else f"[{type(v).__name__} OMITIDO]") for k, v in (params_for_log or {}).items()}
    log_message += f" con params: {safe_params}"
    logger.error(f"{log_message}: {type(e).__name__} - {str(e)}", exc_info=True)
    details_str = str(e); status_code_int = 500; graph_error_code = None
    if isinstance(e, requests.exceptions.HTTPError) and e.response is not None:
        status_code_int = e.response.status_code
        try:
            error_data = e.response.json(); error_info = error_data.get("error", {})
            details_str = error_info.get("message", e.response.text); graph_error_code = error_info.get("code")
        except json.JSONDecodeError: details_str = e.response.text[:500] if e.response.text else "No response body"
    return {"status": "error", "action": action_name, "message": f"Error ejecutando {action_name}: {details_str}",
            "http_status": status_code_int, "details": str(e) if not isinstance(e, requests.exceptions.HTTPError) else details_str,
            "graph_error_code": graph_error_code}

def list_businesses(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; action_name = "bookings_list_businesses"; logger.info(f"Ejecutando {action_name}: {params}")
    url = f"{settings.GRAPH_API_BASE_URL}/solutions/bookingBusinesses"
    query_params: Dict[str, Any] = {}
    if params.get("query"): query_params["query"] = params["query"]
    if params.get("$top"): query_params["$top"] = params["$top"] # Aunque no documentado, se intenta pasar
    if params.get("$skip"): query_params["$skip"] = params["$skip"]
    
    scope = getattr(settings, 'GRAPH_SCOPE_BOOKINGS_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE) # type: ignore
    try:
        response_data = client.get(url, scope=scope, params=query_params if query_params else None)
        if not isinstance(response_data, dict): raise Exception(f"Respuesta inesperada: {type(response_data)}")
        if response_data.get("status") == "error": return response_data
        return {"status": "success", "data": response_data.get("value", [])}
    except Exception as e: return _handle_bookings_api_error(e, action_name, params)

def get_business(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; action_name = "bookings_get_business"; logger.info(f"Ejecutando {action_name}: {params}")
    business_id = params.get("business_id")
    if not business_id: return {"status": "error", "action": action_name, "message": "'business_id' es requerido.", "http_status": 400}
    url = f"{settings.GRAPH_API_BASE_URL}/solutions/bookingBusinesses/{business_id}"
    odata_params = {'$select': params['$select']} if params.get("$select") else {}
    scope = getattr(settings, 'GRAPH_SCOPE_BOOKINGS_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE) # type: ignore
    try:
        response_data = client.get(url, scope=scope, params=odata_params if odata_params else None)
        if not isinstance(response_data, dict): raise Exception(f"Respuesta inesperada: {type(response_data)}")
        if response_data.get("status") == "error": return response_data
        return {"status": "success", "data": response_data}
    except Exception as e: return _handle_bookings_api_error(e, action_name, params)

def list_services(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; action_name = "bookings_list_services"; logger.info(f"Ejecutando {action_name}: {params}")
    business_id = params.get("business_id")
    if not business_id: return {"status": "error", "action": action_name, "message": "'business_id' es requerido.", "http_status": 400}
    url = f"{settings.GRAPH_API_BASE_URL}/solutions/bookingBusinesses/{business_id}/services"
    odata_params: Dict[str, Any] = {k:v for k,v in params.items() if k in ["$select", "$top", "$filter"]}
    scope = getattr(settings, 'GRAPH_SCOPE_BOOKINGS_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE) # type: ignore
    try:
        response_data = client.get(url, scope=scope, params=odata_params if odata_params else None)
        if not isinstance(response_data, dict): raise Exception(f"Respuesta inesperada: {type(response_data)}")
        if response_data.get("status") == "error": return response_data
        return {"status": "success", "data": response_data.get("value", [])}
    except Exception as e: return _handle_bookings_api_error(e, action_name, params)

def list_staff(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; action_name = "bookings_list_staff"; logger.info(f"Ejecutando {action_name}: {params}")
    business_id = params.get("business_id")
    if not business_id: return {"status": "error", "action": action_name, "message": "'business_id' es requerido.", "http_status": 400}
    url = f"{settings.GRAPH_API_BASE_URL}/solutions/bookingBusinesses/{business_id}/staffMembers"
    odata_params: Dict[str, Any] = {k:v for k,v in params.items() if k in ["$select", "$top"]}
    scope = getattr(settings, 'GRAPH_SCOPE_BOOKINGS_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE) # type: ignore
    try:
        response_data = client.get(url, scope=scope, params=odata_params if odata_params else None)
        if not isinstance(response_data, dict): raise Exception(f"Respuesta inesperada: {type(response_data)}")
        if response_data.get("status") == "error": return response_data
        return {"status": "success", "data": response_data.get("value", [])}
    except Exception as e: return _handle_bookings_api_error(e, action_name, params)

def create_appointment(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; action_name = "bookings_create_appointment"; log_safe = {k:v for k,v in params.items() if k != 'appointment_payload'}
    logger.info(f"Ejecutando {action_name} (payload omitido): %s", log_safe)
    business_id = params.get("business_id"); appointment_payload = params.get("appointment_payload")
    if not business_id: return {"status": "error", "action": action_name, "message": "'business_id' requerido.", "http_status": 400}
    if not appointment_payload or not isinstance(appointment_payload, dict): return {"status": "error", "action": action_name, "message": "'appointment_payload' (dict) requerido.", "http_status": 400}
    required_keys = ["customerEmailAddress", "serviceId", "start", "end"] 
    if not all(k in appointment_payload for k in required_keys) or \
       not isinstance(appointment_payload.get("start"), dict) or not isinstance(appointment_payload.get("end"), dict):
        return {"status": "error", "action": action_name, "message": f"Faltan campos o 'start'/'end' malformados en 'appointment_payload'. Requeridos: {required_keys}.", "http_status": 400}
    url = f"{settings.GRAPH_API_BASE_URL}/solutions/bookingBusinesses/{business_id}/appointments"
    scope = getattr(settings, 'GRAPH_SCOPE_BOOKINGS_READWRITE_ALL', getattr(settings, 'GRAPH_SCOPE_BOOKINGS_APPOINTMENT_READWRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)) # type: ignore
    try:
        response_obj = client.post(url, scope=scope, json_data=appointment_payload) # client.post devuelve requests.Response
        return {"status": "success", "data": response_obj.json()}
    except Exception as e: return _handle_bookings_api_error(e, action_name, params)

def list_appointments(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; action_name = "bookings_list_appointments"; logger.info(f"Ejecutando {action_name}: {params}")
    business_id = params.get("business_id"); start_dt = params.get("start_datetime_str"); end_dt = params.get("end_datetime_str")     
    if not business_id: return {"status": "error", "action": action_name, "message": "'business_id' requerido.", "http_status": 400}
    odata_params: Dict[str, Any] = {}
    if start_dt and end_dt:
        url = f"{settings.GRAPH_API_BASE_URL}/solutions/bookingBusinesses/{business_id}/calendarView"
        odata_params["start"] = start_dt; odata_params["end"] = end_dt
    else: 
        url = f"{settings.GRAPH_API_BASE_URL}/solutions/bookingBusinesses/{business_id}/appointments"
        if params.get("$top"): odata_params["$top"] = params["$top"]
        if params.get("$filter"): odata_params["$filter"] = params["$filter"]
    if params.get("$select"): odata_params["$select"] = params["$select"]
    if params.get("$orderby"): odata_params["$orderby"] = params["$orderby"]
    scope = getattr(settings, 'GRAPH_SCOPE_BOOKINGS_READ_ALL', getattr(settings, 'GRAPH_SCOPE_BOOKINGS_APPOINTMENT_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)) # type: ignore
    try:
        response_data = client.get(url, scope=scope, params=odata_params)
        if not isinstance(response_data, dict): raise Exception(f"Respuesta inesperada: {type(response_data)}")
        if response_data.get("status") == "error": return response_data
        return {"status": "success", "data": response_data.get("value", [])}
    except Exception as e: return _handle_bookings_api_error(e, action_name, params)

def get_appointment(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; action_name = "bookings_get_appointment"; logger.info(f"Ejecutando {action_name}: {params}")
    business_id = params.get("business_id"); appointment_id = params.get("appointment_id")
    if not business_id or not appointment_id: return {"status": "error", "action": action_name, "message": "'business_id' y 'appointment_id' requeridos.", "http_status": 400}
    url = f"{settings.GRAPH_API_BASE_URL}/solutions/bookingBusinesses/{business_id}/appointments/{appointment_id}"
    odata_params = {'$select': params['$select']} if params.get("$select") else {}
    scope = getattr(settings, 'GRAPH_SCOPE_BOOKINGS_READ_ALL', getattr(settings, 'GRAPH_SCOPE_BOOKINGS_APPOINTMENT_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)) # type: ignore
    try:
        response_data = client.get(url, scope=scope, params=odata_params if odata_params else None)
        if not isinstance(response_data, dict): raise Exception(f"Respuesta inesperada: {type(response_data)}")
        if response_data.get("status") == "error": return response_data
        return {"status": "success", "data": response_data}
    except Exception as e: return _handle_bookings_api_error(e, action_name, params)

def cancel_appointment(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; action_name = "bookings_cancel_appointment"; logger.info(f"Ejecutando {action_name}: {params}")
    business_id = params.get("business_id"); appointment_id = params.get("appointment_id")
    if not business_id or not appointment_id: return {"status": "error", "action": action_name, "message": "'business_id' y 'appointment_id' requeridos.", "http_status": 400}
    url = f"{settings.GRAPH_API_BASE_URL}/solutions/bookingBusinesses/{business_id}/appointments/{appointment_id}/cancel"
    payload = {"cancellationMessage": params.get("cancellation_message", "Esta cita ha sido cancelada.")}
    scope = getattr(settings, 'GRAPH_SCOPE_BOOKINGS_READWRITE_ALL', getattr(settings, 'GRAPH_SCOPE_BOOKINGS_APPOINTMENT_READWRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)) # type: ignore
    try:
        response_obj = client.post(url, scope=scope, json_data=payload) # client.post devuelve requests.Response
        if response_obj.status_code == 204:
            return {"status": "success", "message": f"Cita '{appointment_id}' cancelada.", "http_status": 204}
        else: 
            response_obj.raise_for_status() # Dejar que HTTPError se maneje arriba si no es 204
            return {"status": "warning", "message": f"Respuesta inesperada {response_obj.status_code}.", "http_status": response_obj.status_code} # No debería llegar
    except Exception as e: return _handle_bookings_api_error(e, action_name, params)

# --- FIN DEL MÓDULO actions/bookings_actions.py ---