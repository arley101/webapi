# app/actions/bookings_actions.py
# -*- coding: utf-8 -*-
import logging
import requests # Para requests.exceptions.HTTPError
import json # Para el helper de error
from typing import Dict, List, Optional, Any

from app.core.config import settings # Para acceder a GRAPH_API_DEFAULT_SCOPE, GRAPH_API_BASE_URL
from app.shared.helpers.http_client import AuthenticatedHttpClient

logger = logging.getLogger(__name__)

# Helper para manejar errores de Bookings API
def _handle_bookings_api_error(e: Exception, action_name: str, params_for_log: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    log_message = f"Error en Bookings action '{action_name}'"
    safe_params = {} # Inicializar
    if params_for_log:
        # Omitir payloads grandes o sensibles del log directo
        sensitive_keys = ['appointment_payload']
        safe_params = {k: (v if k not in sensitive_keys else f"[{type(v).__name__} OMITIDO]") for k, v in params_for_log.items()}
        log_message += f" con params: {safe_params}"
    
    logger.error(f"{log_message}: {type(e).__name__} - {str(e)}", exc_info=True)
    
    details_str = str(e)
    status_code_int = 500
    graph_error_code = None

    if isinstance(e, requests.exceptions.HTTPError) and e.response is not None:
        status_code_int = e.response.status_code
        try:
            error_data = e.response.json()
            error_info = error_data.get("error", {})
            details_str = error_info.get("message", e.response.text)
            graph_error_code = error_info.get("code")
        except json.JSONDecodeError: # Corregido
            details_str = e.response.text[:500] if e.response.text else "No response body"
            
    return {
        "status": "error",
        "action": action_name,
        "message": f"Error ejecutando {action_name}: {details_str}",
        "http_status": status_code_int,
        "details": str(e) if not isinstance(e, requests.exceptions.HTTPError) else details_str,
        "graph_error_code": graph_error_code
    }

# --- Implementación de Acciones de Microsoft Bookings ---

def list_businesses(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "bookings_list_businesses"
    logger.info(f"Ejecutando {action_name} con params: {params}")
    
    url = f"{settings.GRAPH_API_BASE_URL}/solutions/bookingBusinesses"
    
    query_params: Dict[str, Any] = {}
    # El parámetro 'query' es para buscar por displayName según la documentación de Graph
    # https://learn.microsoft.com/en-us/graph/api/bookingbusiness-list?view=graph-rest-1.0&tabs=http#optional-query-parameters
    if params.get("query"): 
        query_params["query"] = params["query"]
    
    # Los parámetros OData como $top, $skip, $filter no parecen ser soportados directamente para este endpoint
    # según la documentación para listar bookingBusinesses (solo 'query').
    # Si se necesitan, se deberían aplicar post-respuesta o verificar si hay un endpoint alternativo.
    if params.get("$top") or params.get("$filter") or params.get("$skip"):
        logger.warning(f"{action_name}: Parámetros OData como $top, $filter, $skip pueden no ser soportados por el endpoint /bookingBusinesses. Se pasarán, pero podrían ser ignorados por la API.")
        if params.get("$top"): query_params["$top"] = params["$top"]
        if params.get("$skip"): query_params["$skip"] = params["$skip"]
        # $filter es más complejo de aplicar si no es soportado directamente.

    logger.info(f"Listando negocios de Microsoft Bookings. Query param: {query_params.get('query')}")
    try:
        # El scope puede requerir Bookings.Read.All o similar.
        # Usar .default asume que los permisos necesarios están concedidos a la aplicación.
        bookings_read_all_scope = getattr(settings, 'GRAPH_SCOPE_BOOKINGS_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response = client.get(url, scope=bookings_read_all_scope, params=query_params if query_params else None)
        return {"status": "success", "data": response.json().get("value", [])}
    except Exception as e:
        return _handle_bookings_api_error(e, action_name, params)

def get_business(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "bookings_get_business"
    logger.info(f"Ejecutando {action_name} con params: {params}")
    
    business_id = params.get("business_id")
    if not business_id:
        return {"status": "error", "action": action_name, "message": "'business_id' es requerido.", "http_status": 400}

    url = f"{settings.GRAPH_API_BASE_URL}/solutions/bookingBusinesses/{business_id}"
    
    # Parámetros $select pueden ser aplicados si se desea limitar los campos devueltos.
    odata_params = {}
    if params.get("$select"):
        odata_params["$select"] = params["$select"]

    logger.info(f"Obteniendo detalles del negocio de Bookings ID: '{business_id}'. Select: {odata_params.get('$select')}")
    bookings_read_all_scope = getattr(settings, 'GRAPH_SCOPE_BOOKINGS_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
    try:
        response = client.get(url, scope=bookings_read_all_scope, params=odata_params if odata_params else None)
        return {"status": "success", "data": response.json()}
    except Exception as e:
        return _handle_bookings_api_error(e, action_name, params)

def list_services(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "bookings_list_services"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    business_id = params.get("business_id")
    if not business_id:
        return {"status": "error", "action": action_name, "message": "'business_id' es requerido.", "http_status": 400}

    url = f"{settings.GRAPH_API_BASE_URL}/solutions/bookingBusinesses/{business_id}/services"
    
    odata_params = {}
    if params.get("$select"): odata_params["$select"] = params["$select"]
    if params.get("$top"): odata_params["$top"] = params["$top"]
    # Otros OData params como $filter podrían ser aplicables.

    logger.info(f"Listando servicios para el negocio de Bookings ID: '{business_id}'. Select: {odata_params.get('$select')}, Top: {odata_params.get('$top')}")
    bookings_read_all_scope = getattr(settings, 'GRAPH_SCOPE_BOOKINGS_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
    try:
        response = client.get(url, scope=bookings_read_all_scope, params=odata_params if odata_params else None)
        return {"status": "success", "data": response.json().get("value", [])}
    except Exception as e:
        return _handle_bookings_api_error(e, action_name, params)

def list_staff(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "bookings_list_staff"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    business_id = params.get("business_id")
    if not business_id:
        return {"status": "error", "action": action_name, "message": "'business_id' es requerido.", "http_status": 400}

    url = f"{settings.GRAPH_API_BASE_URL}/solutions/bookingBusinesses/{business_id}/staffMembers"
    
    odata_params = {}
    if params.get("$select"): odata_params["$select"] = params["$select"]
    if params.get("$top"): odata_params["$top"] = params["$top"]

    logger.info(f"Listando personal para el negocio de Bookings ID: '{business_id}'. Select: {odata_params.get('$select')}, Top: {odata_params.get('$top')}")
    bookings_read_all_scope = getattr(settings, 'GRAPH_SCOPE_BOOKINGS_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
    try:
        response = client.get(url, scope=bookings_read_all_scope, params=odata_params if odata_params else None)
        return {"status": "success", "data": response.json().get("value", [])}
    except Exception as e:
        return _handle_bookings_api_error(e, action_name, params)

def create_appointment(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "bookings_create_appointment"
    logger.info(f"Ejecutando {action_name} con params (appointment_payload omitido del log): %s", {k:v for k,v in params.items() if k != 'appointment_payload'})

    business_id = params.get("business_id")
    appointment_payload = params.get("appointment_payload")

    if not business_id:
        return {"status": "error", "action": action_name, "message": "'business_id' es requerido.", "http_status": 400}
    if not appointment_payload or not isinstance(appointment_payload, dict):
        return {"status": "error", "action": action_name, "message": "'appointment_payload' (dict) es requerido.", "http_status": 400}

    # Validar campos mínimos en appointment_payload (ej: customerEmailAddress, serviceId, start, end)
    # Esto dependerá de la definición de bookingAppointment y los requisitos de la API.
    # Ejemplo de campos que podrían ser requeridos o importantes:
    # 'customerEmailAddress', 'serviceId', 'start' (con dateTime y timeZone), 'end' (con dateTime y timeZone)
    # 'staffMemberIds' (lista de IDs de staff members asignados)
    required_keys_example = ["customerEmailAddress", "serviceId", "start", "end"] 
    if not all(key in appointment_payload for key in required_keys_example):
         missing_keys = [key for key in required_keys_example if key not in appointment_payload]
         logger.error(f"{action_name}: Faltan campos en 'appointment_payload': {missing_keys}. Payload recibido: {appointment_payload}")
         return {"status": "error", "action": action_name, "message": f"Faltan campos requeridos en 'appointment_payload': {missing_keys}. Se necesitan al menos: {required_keys_example}", "http_status": 400}
    if not isinstance(appointment_payload.get("start"), dict) or not isinstance(appointment_payload.get("end"), dict):
        return {"status": "error", "action": action_name, "message": "'start' y 'end' en 'appointment_payload' deben ser objetos con 'dateTime' y 'timeZone'.", "http_status": 400}

    url = f"{settings.GRAPH_API_BASE_URL}/solutions/bookingBusinesses/{business_id}/appointments"
    
    logger.info(f"Creando cita para el negocio de Bookings ID: '{business_id}'. Payload keys: {list(appointment_payload.keys())}")
    try:
        # Scope podría ser Bookings.ReadWrite.All o BookingsAppointment.ReadWrite.All
        bookings_rw_scope = getattr(settings, 'GRAPH_SCOPE_BOOKINGS_READWRITE_ALL', 
                                    getattr(settings, 'GRAPH_SCOPE_BOOKINGS_APPOINTMENT_READWRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE))
        response = client.post(url, scope=bookings_rw_scope, json_data=appointment_payload)
        return {"status": "success", "data": response.json()}
    except Exception as e:
        return _handle_bookings_api_error(e, action_name, params)

def list_appointments(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "bookings_list_appointments"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    business_id = params.get("business_id")
    start_datetime_str = params.get("start_datetime_str") 
    end_datetime_str = params.get("end_datetime_str")     

    if not business_id:
        return {"status": "error", "action": action_name, "message": "'business_id' es requerido.", "http_status": 400}

    odata_params: Dict[str, Any] = {}
    
    # Si se proveen start y end, es mejor usar el endpoint /calendarView
    # que está diseñado para rangos de fechas.
    if start_datetime_str and end_datetime_str:
        url = f"{settings.GRAPH_API_BASE_URL}/solutions/bookingBusinesses/{business_id}/calendarView"
        odata_params["start"] = start_datetime_str # Formato 'YYYY-MM-DDTHH:MM:SSZ'
        odata_params["end"] = end_datetime_str
        logger.info(f"Listando citas (usando calendarView) para negocio '{business_id}' entre {start_datetime_str} y {end_datetime_str}")
    else: # Listar todas las citas (o usar OData $filter si es soportado en /appointments)
        url = f"{settings.GRAPH_API_BASE_URL}/solutions/bookingBusinesses/{business_id}/appointments"
        logger.info(f"Listando todas las citas para el negocio de Bookings ID: '{business_id}' (sin filtro de fecha específico).")
        # Parámetros OData estándar para /appointments si no se usa /calendarView
        if params.get("$top"): odata_params["$top"] = params["$top"]
        if params.get("$filter"): 
            odata_params["$filter"] = params["$filter"]
            logger.info(f"Aplicando OData $filter: {params['$filter']}")
        if params.get("$select"): odata_params["$select"] = params["$select"]
        if params.get("$orderby"): odata_params["$orderby"] = params["$orderby"]
    
    bookings_read_all_scope = getattr(settings, 'GRAPH_SCOPE_BOOKINGS_READ_ALL', 
                                     getattr(settings, 'GRAPH_SCOPE_BOOKINGS_APPOINTMENT_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE))
    try:
        response = client.get(url, scope=bookings_read_all_scope, params=odata_params)
        return {"status": "success", "data": response.json().get("value", [])}
    except Exception as e:
        return _handle_bookings_api_error(e, action_name, params)

def get_appointment(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "bookings_get_appointment"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    business_id = params.get("business_id")
    appointment_id = params.get("appointment_id")

    if not business_id:
        return {"status": "error", "action": action_name, "message": "'business_id' es requerido.", "http_status": 400}
    if not appointment_id:
        return {"status": "error", "action": action_name, "message": "'appointment_id' es requerido.", "http_status": 400}

    url = f"{settings.GRAPH_API_BASE_URL}/solutions/bookingBusinesses/{business_id}/appointments/{appointment_id}"
    
    odata_params = {}
    if params.get("$select"): odata_params["$select"] = params["$select"]

    logger.info(f"Obteniendo detalles de la cita ID '{appointment_id}' para el negocio '{business_id}'. Select: {odata_params.get('$select')}")
    bookings_read_all_scope = getattr(settings, 'GRAPH_SCOPE_BOOKINGS_READ_ALL', 
                                     getattr(settings, 'GRAPH_SCOPE_BOOKINGS_APPOINTMENT_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE))
    try:
        response = client.get(url, scope=bookings_read_all_scope, params=odata_params if odata_params else None)
        return {"status": "success", "data": response.json()}
    except Exception as e:
        return _handle_bookings_api_error(e, action_name, params)

def cancel_appointment(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "bookings_cancel_appointment"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    business_id = params.get("business_id")
    appointment_id = params.get("appointment_id")
    cancellation_message = params.get("cancellation_message", "Esta cita ha sido cancelada.") 

    if not business_id:
        return {"status": "error", "action": action_name, "message": "'business_id' es requerido.", "http_status": 400}
    if not appointment_id:
        return {"status": "error", "action": action_name, "message": "'appointment_id' es requerido.", "http_status": 400}

    url = f"{settings.GRAPH_API_BASE_URL}/solutions/bookingBusinesses/{business_id}/appointments/{appointment_id}/cancel"
    payload = {"cancellationMessage": cancellation_message}
    
    logger.info(f"Cancelando cita ID '{appointment_id}' del negocio '{business_id}' con mensaje: '{cancellation_message}'")
    try:
        bookings_rw_scope = getattr(settings, 'GRAPH_SCOPE_BOOKINGS_READWRITE_ALL', 
                                    getattr(settings, 'GRAPH_SCOPE_BOOKINGS_APPOINTMENT_READWRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE))
        response = client.post(url, scope=bookings_rw_scope, json_data=payload)
        
        if response.status_code == 204:
            return {"status": "success", "message": f"Cita '{appointment_id}' cancelada exitosamente.", "http_status": response.status_code}
        else:
            details = response.text if response.content else "Respuesta inesperada sin cuerpo."
            logger.error(f"Respuesta inesperada {response.status_code} al cancelar cita '{appointment_id}': {details}")
            # Construir un error HTTP para que _handle_bookings_api_error lo procese si es posible.
            # O devolver un error formateado directamente.
            try:
                response.raise_for_status() # Si no era 204, esto debería levantar un error si es 4xx/5xx
            except requests.exceptions.HTTPError as http_e_manual:
                return _handle_bookings_api_error(http_e_manual, action_name, params)
            # Si no levanta error pero no es 204, es inusual.
            return {"status": "warning", "action": action_name, "message": f"Respuesta inesperada del servidor al cancelar: {response.status_code}", "details": details, "http_status": response.status_code}

    except Exception as e:
        return _handle_bookings_api_error(e, action_name, params)

# --- FIN DEL MÓDULO actions/bookings_actions.py ---