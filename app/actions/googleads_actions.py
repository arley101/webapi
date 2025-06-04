# app/actions/googleads_actions.py
import logging
from typing import Dict, List, Optional, Any, Union 
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
from google.protobuf import json_format, field_mask_pb2 

from app.core.config import settings
from app.shared.helpers.http_client import AuthenticatedHttpClient # No se usa directamente, pero se mantiene firma

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
        creds = {
            "developer_token": settings.GOOGLE_ADS.DEVELOPER_TOKEN, "client_id": settings.GOOGLE_ADS.CLIENT_ID,
            "client_secret": settings.GOOGLE_ADS.CLIENT_SECRET, "refresh_token": settings.GOOGLE_ADS.REFRESH_TOKEN,
            "login_customer_id": settings.GOOGLE_ADS.LOGIN_CUSTOMER_ID,
        }
        if not all(creds.values()): raise ValueError(f"Faltan credenciales/configuraciones de Google Ads: {', '.join(k for k,v in creds.items() if not v)}.")
        effective_config = {k: str(v).replace("-", "") if k == "login_customer_id" else str(v) for k,v in creds.items()}
        effective_config["use_proto_plus"] = True
    
    try:
        instance = GoogleAdsClient.load_from_dict(effective_config)
        if not client_config_override: _google_ads_client_instance = instance
        logger.info(f"Cliente Google Ads inicializado para login_customer_id: {effective_config.get('login_customer_id')}")
        return instance
    except Exception as e:
        logger.exception(f"Error crítico inicializando cliente Google Ads: {e}")
        raise ConnectionError(f"No se pudo inicializar cliente Google Ads: {e}")


def _format_google_ads_row_to_dict(google_ads_row: Any) -> Dict[str, Any]:
    try:
        return json_format.MessageToDict(google_ads_row._pb, preserving_proto_field_name=True, including_default_value_fields=False)
    except Exception as e_json:
        logger.warning(f"Fallo al convertir GoogleAdsRow a dict con json_format: {e_json}. Intentando serialización manual limitada.")
        row_dict = {}
        try:
            for field_name in google_ads_row._meta.fields:
                value = getattr(google_ads_row, field_name)
                # Simplificación de la serialización manual; puede necesitar ajustes para tipos complejos o enums profundos
                if hasattr(value, "_pb"): 
                    try: row_dict[field_name] = json_format.MessageToDict(value._pb, preserving_proto_field_name=True, including_default_value_fields=False)
                    except: row_dict[field_name] = str(value) 
                elif isinstance(value, (list, tuple)) and value and hasattr(value[0], "_pb"):
                    try: row_dict[field_name] = [json_format.MessageToDict(item._pb, preserving_proto_field_name=True, including_default_value_fields=False) for item in value]
                    except: row_dict[field_name] = [str(item) for item in value]
                elif hasattr(value, 'name') and hasattr(google_ads_row._meta.fields_by_name[field_name], 'enum_type') and value.__class__ == google_ads_row._meta.fields_by_name[field_name].enum_type():
                    row_dict[field_name] = value.name # Enum
                else: row_dict[field_name] = value
        except Exception as inner_e: logger.error(f"Error serialización manual GoogleAdsRow: {inner_e}")
        return row_dict if row_dict else {"_raw_repr_": str(google_ads_row), "_serialization_error_": "Fallback a string"}

def _extract_google_ads_errors(failure_message: Any, client: GoogleAdsClient) -> List[Dict[str, Any]]:
    error_list = []
    if failure_message and hasattr(failure_message, 'errors') and failure_message.errors:
        for error_item in failure_message.errors:
            err_detail = {"message": error_item.message}
            if hasattr(error_item, 'error_code') and error_item.error_code:
                try:
                    oneof_field_name = error_item.error_code._pb.WhichOneof('error_code')
                    if oneof_field_name:
                        enum_type_name_candidate = f"{oneof_field_name[0].upper()}{oneof_field_name[1:].replace('_error', 'ErrorEnum')}"
                        # Corregir búsqueda del enum type
                        found_enum_type = None
                        for enum_collection_name in dir(client.enums):
                            enum_collection = getattr(client.enums, enum_collection_name)
                            if hasattr(enum_collection, enum_type_name_candidate):
                                found_enum_type = getattr(enum_collection, enum_type_name_candidate)
                                break
                            # Fallback por si el nombre no coincide exactamente (ej. RequestErrorEnum vs RequestError)
                            if hasattr(enum_collection, oneof_field_name.replace('_error','').capitalize() + "ErrorEnum"):
                                 found_enum_type = getattr(enum_collection, oneof_field_name.replace('_error','').capitalize() + "ErrorEnum")
                                 break
                        
                        if found_enum_type:
                            enum_value = getattr(error_item.error_code, oneof_field_name)
                            err_detail["errorCode"] = found_enum_type(enum_value).name
                        else:
                            err_detail["errorCode"] = f"UnknownEnumCategory: {str(error_item.error_code)}"
                    else: err_detail["errorCode"] = str(error_item.error_code)
                except Exception as e_enum: err_detail["errorCode"] = f"ErrorParsingEnum ({e_enum}): {str(error_item.error_code)}"
            if hasattr(error_item, 'trigger.string_value'): err_detail["triggerValue"] = error_item.trigger.string_value
            if hasattr(error_item, 'location.field_path_elements'):
                err_detail["location"] = [{"fieldName": p.field_name, "index": p.index if p.index is not None else None} for p in error_item.location.field_path_elements]
            error_list.append(err_detail)
    return error_list

def _handle_google_ads_api_exception(ex: GoogleAdsException, action_name: str, gads_client: GoogleAdsClient, customer_id_log: Optional[str] = None) -> Dict[str, Any]:
    error_details = _extract_google_ads_errors(ex.failure, gads_client)
    logger.error(f"Google Ads API Exception en '{action_name}' para customer_id '{customer_id_log or 'N/A'}'. Request ID: {ex.request_id}. Errors: {error_details}", exc_info=False)
    primary_message = error_details[0]["message"] if error_details and error_details[0].get("message") else "Error en la API de Google Ads."
    return {"status": "error", "action": action_name, "message": primary_message, 
            "details": {"googleAdsFailure": {"errors": error_details, "requestId": ex.request_id}}, "http_status": 400}

def _build_resource_from_dict(client: GoogleAdsClient, resource_type_name: str, data_dict: Dict[str, Any]):
    resource_obj = client.get_type(resource_type_name)
    # El método copy_from del SDK es generalmente robusto para convertir dicts a protos,
    # incluyendo el manejo de enums si los strings coinciden con los nombres de los enum members.
    try:
        json_format.ParseDict(data_dict, resource_obj._pb, ignore_unknown_fields=True)
    except Exception as e_parse:
        logger.error(f"Error con json_format.ParseDict para {resource_type_name}: {e_parse}. Intentando client.copy_from.")
        try: # Fallback a client.copy_from que podría ser más permisivo o manejar enums de forma diferente
            client.copy_from(resource_obj, data_dict)
        except Exception as e_copy:
            logger.error(f"Error durante client.copy_from para {resource_type_name}: {e_copy}", exc_info=True)
            raise TypeError(f"Error convirtiendo dict a {resource_type_name}: {e_copy}. Verifique payload y tipos.")
    return resource_obj

def googleads_search_stream(client_unused: Optional[AuthenticatedHttpClient], params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; action_name = "googleads_search_stream"; logger.info(f"Ejecutando {action_name}: {params}")
    customer_id = params.get("customer_id"); gaql_query = params.get("query")
    if not customer_id or not gaql_query: return {"status": "error", "action": action_name, "message": "'customer_id' y 'query' (GAQL) requeridos.", "http_status": 400}
    customer_id_clean = str(customer_id).replace("-", "")
    try:
        gads_client = get_google_ads_client(params.get("client_config_override"))
        ga_service = gads_client.get_service("GoogleAdsService")
        search_request = gads_client.get_type("SearchGoogleAdsStreamRequest")
        search_request.customer_id = customer_id_clean; search_request.query = gaql_query
        if params.get("summary_row_setting"): 
            search_request.summary_row_setting = gads_client.enums.SummaryRowSettingEnum[params["summary_row_setting"].upper()]
        stream = ga_service.search_stream(request=search_request)
        results = []; summary_row = None; field_mask = None
        for batch in stream:
            if field_mask is None and batch.field_mask: field_mask = [p for p in batch.field_mask.paths]
            for row in batch.results: results.append(_format_google_ads_row_to_dict(row))
            if batch.summary_row: summary_row = _format_google_ads_row_to_dict(batch.summary_row)
        response_data: Dict[str, Any] = {"results": results, "total_results_returned": len(results)} # Renombrado
        if summary_row: response_data["summary_row"] = summary_row
        if field_mask: response_data["_field_mask_debug_"] = field_mask # Para debugging
        return {"status": "success", "data": response_data}
    except GoogleAdsException as ex:
        gads_client_for_err = _google_ads_client_instance or get_google_ads_client(params.get("client_config_override")) # Asegurar tener un cliente para enums
        return _handle_google_ads_api_exception(ex, action_name, gads_client_for_err, customer_id_clean)
    except (ValueError, ConnectionError) as conf_err: 
        return {"status": "error", "action": action_name, "message": str(conf_err), "http_status": 503 if isinstance(conf_err, ConnectionError) else 400}
    except Exception as e:
        logger.exception(f"Error inesperado en {action_name} para '{customer_id_clean}': {e}")
        return {"status": "error", "action": action_name, "message": f"Error inesperado: {str(e)}", "http_status": 500}

def _execute_mutate_operation(
    service_name: str, operation_type_name: str, resource_type_name: str, 
    mutate_method_name: str, request_type_name: str, 
    client_unused: Optional[AuthenticatedHttpClient], params: Dict[str, Any]
) -> Dict[str, Any]:
    resource_name_key_part = resource_type_name.lower().replace('adgroupcriterion', 'keywords').replace('adgroupad', 'ads').replace('adgroup', 'adgroups')
    action_name = f"googleads_mutate_{resource_name_key_part}" 
    logger.info(f"Ejecutando {action_name} (payloads omitidos del log)")
    customer_id = params.get("customer_id"); operations_payload = params.get("operations")
    if not customer_id or not operations_payload or not isinstance(operations_payload, list) or not operations_payload: 
        return {"status": "error", "action": action_name, "message": "'customer_id' y 'operations' (lista no vacía) requeridos.", "http_status": 400}
    customer_id_clean = str(customer_id).replace("-", "")
    try:
        gads_client = get_google_ads_client(params.get("client_config_override"))
        service_client = gads_client.get_service(service_name)
        sdk_operations = []
        for op_idx, op_dict in enumerate(operations_payload):
            operation = gads_client.get_type(operation_type_name)
            if "create" in op_dict and isinstance(op_dict["create"], dict):
                created_obj = _build_resource_from_dict(gads_client, resource_type_name, op_dict["create"])
                getattr(operation, "create").CopyFrom(created_obj)
            elif "update" in op_dict and isinstance(op_dict["update"], dict):
                resource_data = op_dict["update"]
                if "resource_name" not in resource_data: raise ValueError(f"Update op (idx {op_idx}) debe incluir 'resource_name'.")
                updated_obj = _build_resource_from_dict(gads_client, resource_type_name, resource_data)
                getattr(operation, "update").CopyFrom(updated_obj)
                mask_paths = op_dict.get("update_mask", [k for k in resource_data if k != "resource_name"])
                if isinstance(mask_paths, str): mask_paths = [p.strip() for p in mask_paths.split(',')]
                if mask_paths: operation.update_mask.CopyFrom(field_mask_pb2.FieldMask(paths=mask_paths))
            elif "remove" in op_dict and isinstance(op_dict["remove"], str):
                setattr(operation, "remove", op_dict["remove"])
            else: continue # Operación no soportada o malformada
            sdk_operations.append(operation)
        if not sdk_operations: return {"status": "error", "action": action_name, "message": "No se proveyeron operaciones válidas.", "http_status": 400}
        
        mutate_request = gads_client.get_type(request_type_name)
        mutate_request.customer_id = customer_id_clean
        mutate_request.operations.extend(sdk_operations)
        mutate_request.partial_failure = params.get("partial_failure", False)
        mutate_request.validate_only = params.get("validate_only", False)
        if params.get("response_content_type"):
            try: mutate_request.response_content_type = gads_client.enums.ResponseContentTypeEnum[params["response_content_type"].upper()]
            except KeyError: logger.warning(f"ResponseContentType '{params['response_content_type']}' inválido.")
        
        response = getattr(service_client, mutate_method_name)(request=mutate_request)
        formatted_response: Dict[str, Any] = {"mutate_operation_responses": []}
        if response.partial_failure_error and response.partial_failure_error.IsInitialized():
            # Simplificado: solo loguear, el error completo está en el objeto de respuesta original de Google
            logger.error(f"Partial failure en {action_name}: {response.partial_failure_error}")
            # Extraer y formatear el error parcial para la respuesta JSON
            try:
                error_details_extracted = _extract_google_ads_errors(json_format.Parse(response.partial_failure_error.details[0].value, gads_client.get_type("GoogleAdsFailure")._pb), gads_client)
                formatted_response["partial_failure_error_details"] = {"errors": error_details_extracted}
            except Exception as e_pf:
                logger.error(f"Error parseando partial_failure_error: {e_pf}")
                formatted_response["partial_failure_error_details"] = {"message": "Error parseando detalles de fallo parcial."}


        for result in response.results:
            res_dict = {"resource_name": result.resource_name}
            # Tratar de obtener el recurso específico devuelto (Campaign, AdGroup, etc.)
            # El nombre del campo en el resultado suele ser el tipo de recurso en snake_case
            resource_field_name_candidate = resource_type_name.split("::")[-1] 
            resource_field_name_snake = ''.join(['_' + i.lower() if i.isupper() else i for i in resource_field_name_candidate]).lstrip('_')

            if hasattr(result, resource_field_name_snake):
                resource_object_returned = getattr(result, resource_field_name_snake)
                if hasattr(resource_object_returned, '_pb') and resource_object_returned._pb.ByteSize() > 0: # Asegurarse que no es un objeto vacío
                    res_dict[resource_field_name_snake] = _format_google_ads_row_to_dict(resource_object_returned)
            formatted_response["mutate_operation_responses"].append(res_dict)
        return {"status": "success", "data": formatted_response}
    except GoogleAdsException as ex:
        gads_client_for_err = _google_ads_client_instance or get_google_ads_client(params.get("client_config_override"))
        return _handle_google_ads_api_exception(ex, action_name, gads_client_for_err, customer_id_clean)
    except (ValueError, ConnectionError, TypeError) as conf_err: 
        return {"status": "error", "action": action_name, "message": str(conf_err), "http_status": 503 if isinstance(conf_err, ConnectionError) else 400}
    except Exception as e:
        logger.exception(f"Error inesperado en {action_name} para '{customer_id_clean}': {e}")
        return {"status": "error", "action": action_name, "message": f"Error inesperado: {str(e)}", "http_status": 500}

def googleads_mutate_campaigns(client: Optional[AuthenticatedHttpClient], params: Dict[str, Any]) -> Dict[str, Any]:
    return _execute_mutate_operation("CampaignService", "CampaignOperation", "Campaign", "mutate_campaigns", "MutateCampaignsRequest", client, params)

def googleads_mutate_adgroups(client: Optional[AuthenticatedHttpClient], params: Dict[str, Any]) -> Dict[str, Any]:
    return _execute_mutate_operation("AdGroupService", "AdGroupOperation", "AdGroup", "mutate_ad_groups", "MutateAdGroupsRequest", client, params)

def googleads_mutate_ads(client: Optional[AuthenticatedHttpClient], params: Dict[str, Any]) -> Dict[str, Any]:
    return _execute_mutate_operation("AdGroupAdService", "AdGroupAdOperation", "AdGroupAd", "mutate_ad_group_ads", "MutateAdGroupAdsRequest", client, params)

def googleads_mutate_keywords(client: Optional[AuthenticatedHttpClient], params: Dict[str, Any]) -> Dict[str, Any]:
    # Nota: AdGroupCriterion es el tipo para palabras clave, negativos, etc.
    return _execute_mutate_operation("AdGroupCriterionService", "AdGroupCriterionOperation", "AdGroupCriterion", "mutate_ad_group_criteria", "MutateAdGroupCriteriaRequest", client, params)

# --- FIN DEL MÓDULO ---