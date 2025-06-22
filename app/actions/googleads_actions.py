# app/actions/googleads_actions.py
import logging
from typing import Dict, List, Optional, Any, Union
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
from google.protobuf import json_format
from google.api_core import protobuf_helpers

from app.core.config import settings
from app.shared.helpers.http_client import AuthenticatedHttpClient 

logger = logging.getLogger(__name__)

_google_ads_client_instance: Optional[GoogleAdsClient] = None

def get_google_ads_client(client_config_override: Optional[Dict[str, Any]] = None) -> GoogleAdsClient:
    global _google_ads_client_instance
    if _google_ads_client_instance and not client_config_override:
        return _google_ads_client_instance
    effective_config = {}
    if client_config_override:
        effective_config = client_config_override
    else:
        required_vars = {
            "developer_token": settings.GOOGLE_ADS.DEVELOPER_TOKEN,
            "client_id": settings.GOOGLE_ADS.CLIENT_ID,
            "client_secret": settings.GOOGLE_ADS.CLIENT_SECRET,
            "refresh_token": settings.GOOGLE_ADS.REFRESH_TOKEN,
        }
        missing = [key for key, value in required_vars.items() if not value]
        if missing: raise ValueError(f"Faltan credenciales de Google Ads en settings: {', '.join(missing)}")
        effective_config = {
            "developer_token": str(settings.GOOGLE_ADS.DEVELOPER_TOKEN),
            "client_id": str(settings.GOOGLE_ADS.CLIENT_ID),
            "client_secret": str(settings.GOOGLE_ADS.CLIENT_SECRET),
            "refresh_token": str(settings.GOOGLE_ADS.REFRESH_TOKEN),
            "login_customer_id": str(settings.GOOGLE_ADS.LOGIN_CUSTOMER_ID).replace("-", "") if settings.GOOGLE_ADS.LOGIN_CUSTOMER_ID else None,
            "use_proto_plus": True,
        }
    try:
        client_instance = GoogleAdsClient.load_from_dict(effective_config)
        if not client_config_override: _google_ads_client_instance = client_instance
        return client_instance
    except Exception as e:
        raise ConnectionError(f"No se pudo inicializar el cliente de Google Ads: {e}")

def _format_google_ads_row_to_dict(google_ads_row: Any) -> Dict[str, Any]:
    try:
        return json_format.MessageToDict(google_ads_row._pb, preserving_proto_field_name=True)
    except Exception as e:
        return {"_raw_repr_": str(google_ads_row), "_serialization_error_": str(e)}

def _extract_google_ads_errors(failure_message: Any, client: GoogleAdsClient) -> List[Dict[str, Any]]:
    error_list = []
    if not (failure_message and hasattr(failure_message, 'errors')): return error_list
    for error_item in failure_message.errors:
        err_detail = {"message": error_item.message}
        if hasattr(error_item, 'trigger') and error_item.trigger and error_item.trigger.string_value:
            err_detail["triggerValue"] = error_item.trigger.string_value
        if hasattr(error_item, 'location') and error_item.location and hasattr(error_item.location, 'field_path_elements'):
            err_detail["location"] = [{"fieldName": el.field_name, "index": el.index if el.index is not None else None} for el in error_item.location.field_path_elements]
        if hasattr(error_item, 'error_code'):
             oneof_field_name = error_item.error_code._pb.WhichOneof('error_code')
             if oneof_field_name:
                try:
                    enum_type_name = f"{oneof_field_name[0].upper()}{oneof_field_name[1:].replace('_error', 'ErrorEnum')}"
                    enum_type = client.enums[enum_type_name]
                    enum_value = getattr(error_item.error_code, oneof_field_name)
                    err_detail["errorCode"] = enum_type(enum_value).name
                except (KeyError, AttributeError): err_detail["errorCode"] = str(getattr(error_item.error_code, oneof_field_name))
             else: err_detail["errorCode"] = "UNKNOWN"
        error_list.append(err_detail)
    return error_list

def _handle_google_ads_api_exception(ex: GoogleAdsException, action_name: str, gads_client_for_enums: GoogleAdsClient, customer_id_log: Optional[str] = None) -> Dict[str, Any]:
    error_details_extracted = _extract_google_ads_errors(ex.failure, gads_client_for_enums)
    logger.error(f"Google Ads API Exception en '{action_name}' para customer_id '{customer_id_log or 'N/A'}'. Request ID: {ex.request_id}. Errors: {error_details_extracted}", exc_info=False)
    primary_message = error_details_extracted[0]["message"] if error_details_extracted else "Error en la API de Google Ads."
    return {"status": "error", "action": action_name, "message": primary_message, "details": {"googleAdsFailure": {"errors": error_details_extracted, "requestId": ex.request_id}}, "http_status": 400}

def googleads_search_stream(client: Optional[AuthenticatedHttpClient], params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "googleads_search_stream"
    customer_id_to_use = params.get("customer_id") or settings.GOOGLE_ADS.LOGIN_CUSTOMER_ID
    gaql_query = params.get("query")
    if not customer_id_to_use or not gaql_query:
        return {"status": "error", "message": "'customer_id' y 'query' son requeridos.", "http_status": 400}
    customer_id_clean = str(customer_id_to_use).replace("-", "")
    try:
        gads_client = get_google_ads_client(params.get("client_config_override"))
        ga_service = gads_client.get_service("GoogleAdsService")
        search_request = gads_client.get_type("SearchGoogleAdsStreamRequest")
        search_request.customer_id = customer_id_clean
        search_request.query = gaql_query
        stream = ga_service.search_stream(request=search_request)
        results = [_format_google_ads_row_to_dict(row) for batch in stream for row in batch.results]
        return {"status": "success", "data": {"results": results, "total_results": len(results)}}
    except GoogleAdsException as ex:
        return _handle_google_ads_api_exception(ex, action_name, get_google_ads_client(), customer_id_clean)
    except Exception as e:
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
    customer_id_to_use = params.get("customer_id") or settings.GOOGLE_ADS.LOGIN_CUSTOMER_ID
    operations_payload = params.get("operations")
    if not customer_id_to_use or not operations_payload:
        return {"status": "error", "message": "'customer_id' y 'operations' son requeridos.", "http_status": 400}
    customer_id_clean = str(customer_id_to_use).replace("-", "")
    try:
        gads_client = get_google_ads_client(params.get("client_config_override"))
        service_client = gads_client.get_service(service_name)
        
        sdk_operations = []
        for op_dict in operations_payload:
            operation = gads_client.get_type(operation_type_name)
            
            if "create" in op_dict and isinstance(op_dict["create"], dict):
                resource_obj = gads_client.get_type(resource_type_name)
                gads_client.copy_from(resource_obj, op_dict["create"])
                getattr(operation, "create").CopyFrom(resource_obj)

            elif "update" in op_dict and isinstance(op_dict["update"], dict):
                # ***** INICIO DE LA CORRECCIÓN DEFINITIVA *****
                update_data = op_dict["update"]
                if "resource_name" not in update_data:
                    raise ValueError("La operación de 'update' debe contener 'resource_name'.")
                
                # Obtener el objeto de la operación que se va a modificar (ej. operation.update)
                update_obj = getattr(operation, "update")
                
                # Usar el método oficial `copy_from` para poblar el objeto de forma segura.
                # Este método maneja correctamente los enums y otros tipos de datos.
                gads_client.copy_from(update_obj, update_data)
                
                # Crear la máscara de campo (field_mask) para decirle a la API qué campos actualizar
                field_mask = protobuf_helpers.field_mask(None, update_obj._pb)
                operation.update_mask.CopyFrom(field_mask)
                # ***** FIN DE LA CORRECCIÓN DEFINITIVA *****

            elif "remove" in op_dict and isinstance(op_dict["remove"], str):
                operation.remove = op_dict["remove"]
            else:
                continue
            sdk_operations.append(operation)

        if not sdk_operations: 
            return {"status": "error", "action": action_name, "message": "No se proveyeron operaciones válidas.", "http_status": 400}

        mutate_request = gads_client.get_type(request_type_name)
        mutate_request.customer_id = customer_id_clean
        mutate_request.operations.extend(sdk_operations)
        mutate_request.partial_failure = params.get("partial_failure", False)
        mutate_request.validate_only = params.get("validate_only", False)
        
        response = getattr(service_client, mutate_method_name)(request=mutate_request)
        
        formatted_response: Dict[str, Any] = {"results": [json_format.MessageToDict(r._pb) for r in response.results]}
        if response.partial_failure_error:
            failure_message = gads_client.get_type("GoogleAdsFailure")
            failure_message.ParseFromString(response.partial_failure_error.details[0].value)
            formatted_response["partial_failure_error"] = _extract_google_ads_errors(failure_message, gads_client)
            
        return {"status": "success", "data": formatted_response}

    except GoogleAdsException as ex:
        return _handle_google_ads_api_exception(ex, action_name, get_google_ads_client(), customer_id_clean)
    except Exception as e:
        return {"status": "error", "action": action_name, "message": f"Error inesperado: {str(e)}", "http_status": 500}


def googleads_mutate_campaigns(client: Optional[AuthenticatedHttpClient], params: Dict[str, Any]) -> Dict[str, Any]:
    return _execute_mutate_operation("CampaignService", "CampaignOperation", "Campaign", "mutate_campaigns", "MutateCampaignsRequest", client, params)

def googleads_mutate_adgroups(client: Optional[AuthenticatedHttpClient], params: Dict[str, Any]) -> Dict[str, Any]:
    return _execute_mutate_operation("AdGroupService", "AdGroupOperation", "AdGroup", "mutate_ad_groups", "MutateAdGroupsRequest", client, params)

def googleads_mutate_ads(client: Optional[AuthenticatedHttpClient], params: Dict[str, Any]) -> Dict[str, Any]:
    return _execute_mutate_operation("AdGroupAdService", "AdGroupAdOperation", "AdGroupAd", "mutate_ad_group_ads", "MutateAdGroupAdsRequest", client, params)

def googleads_mutate_keywords(client: Optional[AuthenticatedHttpClient], params: Dict[str, Any]) -> Dict[str, Any]:
    return _execute_mutate_operation("AdGroupCriterionService", "AdGroupCriterionOperation", "AdGroupCriterion", "mutate_ad_group_criteria", "MutateAdGroupCriteriaRequest", client, params)