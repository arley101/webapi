# app/actions/googleads_actions.py
import logging
from typing import Dict, List, Optional, Any, Union
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
from google.protobuf import json_format, field_mask_pb2 

from app.core.config import settings
from app.shared.helpers.http_client import AuthenticatedHttpClient 

logger = logging.getLogger(__name__)

# Instancia global para reutilizar el cliente una vez inicializado
_google_ads_client_instance: Optional[GoogleAdsClient] = None

def get_google_ads_client(client_config_override: Optional[Dict[str, Any]] = None) -> GoogleAdsClient:
    """
    Inicializa y devuelve una instancia del cliente de Google Ads.
    Esta versión es robusta: utiliza las credenciales de settings para construir un cliente 
    que maneja automáticamente la renovación de tokens usando el refresh_token.
    Reutiliza la instancia del cliente para mejorar el rendimiento.
    """
    global _google_ads_client_instance
    if _google_ads_client_instance and not client_config_override:
        logger.debug("Reutilizando instancia existente del cliente de Google Ads.")
        return _google_ads_client_instance

    effective_config = {}
    if client_config_override:
        effective_config = client_config_override
        logger.info("Utilizando configuración de Google Ads proporcionada en 'client_config_override'.")
    else:
        # Cargar credenciales desde la configuración global (app/core/config.py)
        required_vars = {
            "developer_token": settings.GOOGLE_ADS.DEVELOPER_TOKEN,
            "client_id": settings.GOOGLE_ADS.CLIENT_ID,
            "client_secret": settings.GOOGLE_ADS.CLIENT_SECRET,
            "refresh_token": settings.GOOGLE_ADS.REFRESH_TOKEN,
        }
        missing = [key for key, value in required_vars.items() if not value]
        if missing:
            msg = f"Faltan credenciales de Google Ads en settings: {', '.join(missing)}."
            logger.critical(msg)
            raise ValueError(msg)
        
        effective_config = {
            "developer_token": str(settings.GOOGLE_ADS.DEVELOPER_TOKEN),
            "client_id": str(settings.GOOGLE_ADS.CLIENT_ID),
            "client_secret": str(settings.GOOGLE_ADS.CLIENT_SECRET),
            "refresh_token": str(settings.GOOGLE_ADS.REFRESH_TOKEN),
            "login_customer_id": str(settings.GOOGLE_ADS.LOGIN_CUSTOMER_ID).replace("-", "") if settings.GOOGLE_ADS.LOGIN_CUSTOMER_ID else None,
            "use_proto_plus": True,
        }

    logger.info(f"Inicializando cliente de Google Ads. Login Customer ID: {effective_config.get('login_customer_id') or 'No especificado'}")
    try:
        # GoogleAdsClient.load_from_dict usará el refresh_token para generar access_tokens automáticamente.
        # El error 'invalid_grant' ocurre si el refresh_token mismo es inválido o ha sido revocado.
        client_instance = GoogleAdsClient.load_from_dict(effective_config)
        
        if not client_config_override:
            _google_ads_client_instance = client_instance
            logger.info("Cliente de Google Ads inicializado y cacheado exitosamente.")
        
        return client_instance
    except Exception as e:
        logger.exception(f"Error crítico inicializando el cliente de Google Ads: {e}")
        raise ConnectionError(f"No se pudo inicializar el cliente de Google Ads: {e}")


def _format_google_ads_row_to_dict(google_ads_row: Any) -> Dict[str, Any]:
    """Convierte un objeto GoogleAdsRow (protobuf) a un diccionario Python serializable."""
    try:
        return json_format.MessageToDict(
            google_ads_row._pb, 
            preserving_proto_field_name=True,
            including_default_value_fields=False 
        )
    except Exception as e_json_format:
        logger.warning(f"Fallo al convertir GoogleAdsRow a dict usando json_format ({e_json_format}). La fila se omitirá o se representará como string.")
        return {"_raw_repr_": str(google_ads_row), "_serialization_error_": str(e_json_format)}


def _extract_google_ads_errors(failure_message: Any) -> List[Dict[str, Any]]:
    """Extrae y formatea errores de un objeto GoogleAdsFailure."""
    error_list = []
    if not (failure_message and hasattr(failure_message, 'errors')):
        return error_list

    for error_item in failure_message.errors:
        err_detail = {
            "message": error_item.message,
            "trigger": str(error_item.trigger.string_value) if error_item.trigger else None,
            "location": [
                {"field_name": el.field_name, "index": el.index if el.index is not None else None}
                for el in error_item.location.field_path_elements
            ] if error_item.location else None
        }
        
        # Simplifica la extracción del código de error
        if hasattr(error_item, 'error_code'):
            for field, value in error_item.error_code.items():
                err_detail["error_code_type"] = field
                err_detail["error_code_value"] = value.name if hasattr(value, 'name') else value
                break 
        error_list.append(err_detail)
    return error_list

def _handle_google_ads_api_exception(ex: GoogleAdsException, action_name: str, customer_id_log: Optional[str] = None) -> Dict[str, Any]:
    """Formatea una GoogleAdsException en una respuesta de error estándar."""
    error_details_extracted = _extract_google_ads_errors(ex.failure)
    
    logger.error(
        f"Google Ads API Exception en acción '{action_name}' para customer_id '{customer_id_log or 'N/A'}'. "
        f"Request ID: {ex.request_id}. Errors: {error_details_extracted}",
        exc_info=False 
    )
    
    primary_message = "Error en la API de Google Ads."
    if error_details_extracted and error_details_extracted[0].get("message"):
        primary_message = error_details_extracted[0]["message"]

    return {
        "status": "error",
        "action": action_name,
        "message": primary_message,
        "details": {
            "googleAdsFailure": {
                "errors": error_details_extracted,
                "requestId": ex.request_id
            }
        },
        "http_status": 400 
    }

def _build_resource_from_dict(client: GoogleAdsClient, resource_type_name: str, data_dict: Dict[str, Any]):
    resource_obj = client.get_type(resource_type_name)
    try:
        # copy_from es el método recomendado y robusto para esto.
        client.copy_from(resource_obj, data_dict)
        return resource_obj
    except Exception as e_copy:
        logger.error(f"Error durante client.copy_from para {resource_type_name} con dict {data_dict}: {e_copy}", exc_info=True)
        raise TypeError(f"Error convirtiendo dict a {resource_type_name}: {e_copy}. Verifique la estructura del payload y los tipos de datos, incluyendo los enums.")

# --- ACCIONES ---

def googleads_search_stream(client: Optional[AuthenticatedHttpClient], params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "googleads_search_stream"
    logger.info(f"Ejecutando {action_name} con params: {params}")
    
    # --- LÓGICA MEJORADA ---
    # Usar el customer_id de los params, pero si no está, usar el default de la configuración.
    customer_id_from_params: Optional[str] = params.get("customer_id")
    customer_id_to_use = customer_id_from_params or settings.GOOGLE_ADS.LOGIN_CUSTOMER_ID

    gaql_query: Optional[str] = params.get("query")
    client_config_override: Optional[Dict[str, Any]] = params.get("client_config_override") 

    if not customer_id_to_use:
        return {"status": "error", "action": action_name, "message": "Se requiere 'customer_id' en los params o GOOGLE_ADS_LOGIN_CUSTOMER_ID en la configuración.", "http_status": 400}
    if not gaql_query:
        return {"status": "error", "action": action_name, "message": "'query' (GAQL) es requerida.", "http_status": 400}
    
    customer_id_clean = str(customer_id_to_use).replace("-", "")

    try:
        gads_client = get_google_ads_client(client_config_override)
        ga_service = gads_client.get_service("GoogleAdsService")
        
        logger.info(f"Ejecutando GAQL query en Customer ID '{customer_id_clean}': {gaql_query[:300]}...")
        
        search_request = gads_client.get_type("SearchGoogleAdsStreamRequest")
        search_request.customer_id = customer_id_clean
        search_request.query = gaql_query

        stream = ga_service.search_stream(request=search_request)
        results = [_format_google_ads_row_to_dict(row) for batch in stream for row in batch.results]
        
        response_data: Dict[str, Any] = {"results": results, "total_results": len(results)}
        return {"status": "success", "data": response_data}

    except GoogleAdsException as ex:
        return _handle_google_ads_api_exception(ex, action_name, customer_id_clean)
    except (ValueError, ConnectionError) as conf_err: 
        logger.error(f"Error de configuración/conexión en {action_name}: {conf_err}", exc_info=True)
        return {"status": "error", "action": action_name, "message": str(conf_err), "http_status": 503 if isinstance(conf_err, ConnectionError) else 400}
    except Exception as e:
        logger.exception(f"Error inesperado en {action_name} para customer_id '{customer_id_clean}': {e}")
        return {"status": "error", "action": action_name, "message": f"Error inesperado: {str(e)}", "http_status": 500}


def _execute_mutate_operation(
    service_name: str, 
    operation_type_name: str, 
    resource_type_name: str, 
    mutate_method_name: str, 
    request_type_name: str, 
    client_unused: Optional[AuthenticatedHttpClient], 
    params: Dict[str, Any]
) -> Dict[str, Any]:
    action_name = f"googleads_mutate_{resource_type_name.lower().replace('adgroupad', 'ad').replace('adgroupcriterion', 'keyword')}s"
    logger.info(f"Ejecutando {action_name} con params (operations omitido del log): %s", {k:v for k,v in params.items() if k != 'operations'})

    # --- LÓGICA MEJORADA ---
    customer_id_from_params: Optional[str] = params.get("customer_id")
    customer_id_to_use = customer_id_from_params or settings.GOOGLE_ADS.LOGIN_CUSTOMER_ID
    
    operations_payload: Optional[List[Dict[str, Any]]] = params.get("operations")
    partial_failure: bool = params.get("partial_failure", False) 
    validate_only: bool = params.get("validate_only", False)
    client_config_override: Optional[Dict[str, Any]] = params.get("client_config_override")

    if not customer_id_to_use: 
        return {"status": "error", "action": action_name, "message": "Se requiere 'customer_id' en los params o GOOGLE_ADS_LOGIN_CUSTOMER_ID en la configuración.", "http_status": 400}
    if not operations_payload or not isinstance(operations_payload, list) or not operations_payload: 
        return {"status": "error", "action": action_name, "message": "'operations' (lista no vacía de operaciones) es requerida.", "http_status": 400}

    customer_id_clean = str(customer_id_to_use).replace("-", "")

    try:
        gads_client = get_google_ads_client(client_config_override)
        service_client = gads_client.get_service(service_name)
        
        sdk_operations = []
        for op_dict in operations_payload:
            operation = gads_client.get_type(operation_type_name)
            
            if "create" in op_dict and isinstance(op_dict["create"], dict):
                created_resource_obj = _build_resource_from_dict(gads_client, resource_type_name, op_dict["create"])
                getattr(operation, "create").CopyFrom(created_resource_obj)
            elif "update" in op_dict and isinstance(op_dict["update"], dict):
                resource_data = op_dict["update"]
                if "resource_name" not in resource_data:
                    raise ValueError("Operación de actualización debe incluir 'resource_name'.")
                
                updated_resource_obj = _build_resource_from_dict(gads_client, resource_type_name, resource_data)
                getattr(operation, "update").CopyFrom(updated_resource_obj)
                
                update_mask = gads_client.get_type("FieldMask")
                update_mask.paths.extend([key for key in resource_data.keys() if key != "resource_name"])
                operation.update_mask.CopyFrom(update_mask)
            elif "remove" in op_dict and isinstance(op_dict["remove"], str):
                setattr(operation, "remove", op_dict["remove"])
            else:
                continue
            sdk_operations.append(operation)

        if not sdk_operations: 
            return {"status": "error", "action": action_name, "message": "No se proveyeron operaciones válidas.", "http_status": 400}

        mutate_request = gads_client.get_type(request_type_name)
        mutate_request.customer_id = customer_id_clean
        mutate_request.operations.extend(sdk_operations)
        mutate_request.partial_failure = partial_failure
        mutate_request.validate_only = validate_only

        response = getattr(service_client, mutate_method_name)(request=mutate_request)
        
        formatted_response: Dict[str, Any] = {"results": []}
        if response.partial_failure_error:
            formatted_response["partial_failure_error"] = _extract_google_ads_errors(response.partial_failure_error)

        for result in response.results:
            formatted_response["results"].append(json_format.MessageToDict(result._pb))
            
        return {"status": "success", "data": formatted_response}

    except GoogleAdsException as ex:
        return _handle_google_ads_api_exception(ex, action_name, customer_id_clean)
    except (ValueError, ConnectionError, TypeError) as conf_err: 
        logger.error(f"Error de configuración/payload en {action_name}: {conf_err}", exc_info=True)
        return {"status": "error", "action": action_name, "message": str(conf_err), "http_status": 503 if isinstance(conf_err, ConnectionError) else 400}
    except Exception as e:
        logger.exception(f"Error inesperado en {action_name} para customer_id '{customer_id_clean}': {e}")
        return {"status": "error", "action": action_name, "message": f"Error inesperado: {str(e)}", "http_status": 500}

def googleads_mutate_campaigns(client: Optional[AuthenticatedHttpClient], params: Dict[str, Any]) -> Dict[str, Any]:
    return _execute_mutate_operation("CampaignService", "CampaignOperation", "Campaign", "mutate_campaigns", "MutateCampaignsRequest", client, params)

def googleads_mutate_adgroups(client: Optional[AuthenticatedHttpClient], params: Dict[str, Any]) -> Dict[str, Any]:
    return _execute_mutate_operation("AdGroupService", "AdGroupOperation", "AdGroup", "mutate_ad_groups", "MutateAdGroupsRequest", client, params)

def googleads_mutate_ads(client: Optional[AuthenticatedHttpClient], params: Dict[str, Any]) -> Dict[str, Any]:
    return _execute_mutate_operation("AdGroupAdService", "AdGroupAdOperation", "AdGroupAd", "mutate_ad_group_ads", "MutateAdGroupAdsRequest", client, params)

def googleads_mutate_keywords(client: Optional[AuthenticatedHttpClient], params: Dict[str, Any]) -> Dict[str, Any]:
    return _execute_mutate_operation("AdGroupCriterionService", "AdGroupCriterionOperation", "AdGroupCriterion", "mutate_ad_group_criteria", "MutateAdGroupCriteriaRequest", client, params)

# --- FIN DEL MÓDULO ---
