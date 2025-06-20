# app/actions/googleads_actions.py
import logging
from typing import Dict, List, Optional, Any, Union # Asegurar que Union esté si se usa
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
from google.protobuf import json_format, field_mask_pb2 

from app.core.config import settings
# IMPORTACIÓN CRUCIAL AÑADIDA/VERIFICADA:
from app.shared.helpers.http_client import AuthenticatedHttpClient 

logger = logging.getLogger(__name__)

_google_ads_client_instance: Optional[GoogleAdsClient] = None

def get_google_ads_client(client_config_override: Optional[Dict[str, Any]] = None) -> GoogleAdsClient:
    """
    Inicializa y devuelve una instancia del cliente de Google Ads utilizando
    la configuración de variables de entorno o un override.
    Reutiliza la instancia si ya ha sido creada y no hay override.
    """
    global _google_ads_client_instance
    if _google_ads_client_instance and not client_config_override:
        return _google_ads_client_instance

    effective_config = {}
    if client_config_override:
        effective_config = client_config_override
        logger.info("Utilizando configuración de Google Ads proporcionada en 'client_config_override'.")
    else:
        required_env_vars_map = {
            "developer_token": settings.GOOGLE_ADS.DEVELOPER_TOKEN,
            "client_id": settings.GOOGLE_ADS.CLIENT_ID,
            "client_secret": settings.GOOGLE_ADS.CLIENT_SECRET,
            "refresh_token": settings.GOOGLE_ADS.REFRESH_TOKEN,
            "login_customer_id": settings.GOOGLE_ADS.LOGIN_CUSTOMER_ID,
        }
        missing = [key for key, value in required_env_vars_map.items() if not value]
        if missing:
            msg = f"Faltan credenciales/configuraciones de Google Ads en settings: {', '.join(missing)}."
            logger.critical(msg)
            raise ValueError(msg)
        
        effective_config = {
            "developer_token": str(settings.GOOGLE_ADS.DEVELOPER_TOKEN),
            "client_id": str(settings.GOOGLE_ADS.CLIENT_ID),
            "client_secret": str(settings.GOOGLE_ADS.CLIENT_SECRET),
            "refresh_token": str(settings.GOOGLE_ADS.REFRESH_TOKEN),
            "login_customer_id": str(settings.GOOGLE_ADS.LOGIN_CUSTOMER_ID).replace("-", ""),
            "use_proto_plus": True,
        }

    logger.info(f"Inicializando cliente de Google Ads con login_customer_id: {effective_config.get('login_customer_id')}")
    try:
        if client_config_override:
            return GoogleAdsClient.load_from_dict(effective_config)
        else:
            _google_ads_client_instance = GoogleAdsClient.load_from_dict(effective_config)
            logger.info("Cliente de Google Ads inicializado exitosamente (instancia global).")
            return _google_ads_client_instance
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
        logger.warning(f"Fallo al convertir GoogleAdsRow a dict usando json_format ({e_json_format}). Intentando serialización manual limitada.")
        row_dict = {}
        try:
            for field_name in google_ads_row._meta.fields:
                value = getattr(google_ads_row, field_name)
                if hasattr(value, "_pb"): 
                    try:
                        row_dict[field_name] = json_format.MessageToDict(value._pb, preserving_proto_field_name=True, including_default_value_fields=False)
                    except: 
                        row_dict[field_name] = str(value) 
                elif isinstance(value, (list, tuple)) and value and hasattr(value[0], "_pb"):
                    try:
                        row_dict[field_name] = [json_format.MessageToDict(item._pb, preserving_proto_field_name=True, including_default_value_fields=False) for item in value]
                    except: 
                        row_dict[field_name] = [str(item) for item in value] 
                elif hasattr(value, 'name') and isinstance(value, type(google_ads_row._meta.fields_by_name[field_name].enum_type())): # Manejo de Enums más genérico
                    row_dict[field_name] = value.name
                else:
                    row_dict[field_name] = value
        except Exception as inner_e:
            logger.error(f"Error durante serialización manual de GoogleAdsRow: {inner_e}")
            return {"_raw_repr_": str(google_ads_row), "_serialization_error_": str(inner_e)}
        return row_dict

def _extract_google_ads_errors(failure_message: Any, client: GoogleAdsClient) -> List[Dict[str, Any]]:
    """Extrae y formatea errores de un objeto GoogleAdsFailure."""
    error_list = []
    if failure_message and hasattr(failure_message, 'errors') and failure_message.errors:
        for error_item in failure_message.errors:
            err_detail = {"message": error_item.message}
            if hasattr(error_item, 'error_code') and error_item.error_code:
                try:
                    # Obtener el nombre del campo oneof que está activo para error_code
                    oneof_field_name = error_item.error_code._pb.WhichOneof('error_code')
                    if oneof_field_name:
                        # Obtener el enum type y luego el valor
                        enum_type = client.enums[f"{oneof_field_name[0].upper()}{oneof_field_name[1:].replace('_error', 'ErrorEnum')}"] # Heurística para el nombre del Enum
                        enum_value = getattr(error_item.error_code, oneof_field_name)
                        err_detail["errorCode"] = enum_type(enum_value).name
                    else:
                        err_detail["errorCode"] = str(error_item.error_code) # Fallback
                except Exception as e_enum_extract:
                    logger.warning(f"No se pudo extraer el nombre del enum para el código de error de Google Ads: {error_item.error_code}. Error: {e_enum_extract}")
                    err_detail["errorCode"] = str(error_item.error_code)

            if hasattr(error_item, 'trigger') and error_item.trigger and error_item.trigger.string_value:
                err_detail["triggerValue"] = error_item.trigger.string_value
            
            if hasattr(error_item, 'location') and error_item.location and \
               hasattr(error_item.location, 'field_path_elements') and error_item.location.field_path_elements:
                field_path_details = []
                for path_element in error_item.location.field_path_elements:
                    element_info = {"fieldName": path_element.field_name}
                    if path_element.index is not None: 
                        element_info["index"] = path_element.index
                    field_path_details.append(element_info)
                if field_path_details:
                    err_detail["location"] = {"fieldPathElements": field_path_details}
            error_list.append(err_detail)
    return error_list

def _handle_google_ads_api_exception(
    ex: GoogleAdsException,
    action_name: str,
    gads_client_for_enums: GoogleAdsClient, # Necesario para decodificar enums de error
    customer_id_log: Optional[str] = None
) -> Dict[str, Any]:
    """Formatea una GoogleAdsException en una respuesta de error estándar."""
    error_details_extracted = _extract_google_ads_errors(ex.failure, gads_client_for_enums)
    
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

def _create_field_mask(client: GoogleAdsClient, resource_dict: Dict[str, Any], resource_name_if_present: Optional[str] = None) -> Optional[field_mask_pb2.FieldMask]:
    if not resource_dict:
        return None
    paths = [key for key in resource_dict.keys() if key != "resource_name" and (resource_name_if_present is None or key != resource_name_if_present)]
    if not paths: 
        return None
    return field_mask_pb2.FieldMask(paths=paths)

def _build_resource_from_dict(client: GoogleAdsClient, resource_type_name: str, data_dict: Dict[str, Any]):
    resource_obj = client.get_type(resource_type_name)
    dict_to_copy = data_dict.copy() # Trabajar con una copia
    
    enum_mappings_cache = {} # Cache para nombres de enum

    def get_enum_mapping(field_descriptor):
        if field_descriptor.name in enum_mappings_cache:
            return enum_mappings_cache[field_descriptor.name]
        
        if field_descriptor.type == field_descriptor.TYPE_ENUM:
            # Construir el nombre del tipo enum (ej. 'CampaignStatusEnum')
            # El tipo enum se llama como el campo pero con 'Enum' al final y capitalizado.
            # Esto es una heurística y puede necesitar ajustes.
            enum_type_name_candidate = f"{field_descriptor.message_type.name}{field_descriptor.name[0].upper()}{field_descriptor.name[1:]}Enum"
            if not hasattr(client.enums, enum_type_name_candidate) and field_descriptor.enum_type is not None:
                enum_type_name_candidate = field_descriptor.enum_type.name # Usar el nombre directo del descriptor si está disponible
            
            if hasattr(client.enums, enum_type_name_candidate):
                enum_mappings_cache[field_descriptor.name] = (enum_type_name_candidate, field_descriptor.name)
                return enum_type_name_candidate, field_descriptor.name
        return None, None

    # Iterar sobre los campos del objeto Protobuf destino
    for field_descriptor in resource_obj._meta.fields.values():
        payload_key = field_descriptor.name # Asumir que las claves del payload coinciden con los nombres de campo protobuf
        
        if payload_key in dict_to_copy:
            value_from_payload = dict_to_copy[payload_key]
            
            if field_descriptor.type == field_descriptor.TYPE_ENUM and isinstance(value_from_payload, str):
                enum_type_name, _ = get_enum_mapping(field_descriptor)
                if enum_type_name:
                    try:
                        google_ads_enum_type = getattr(client.enums, enum_type_name)
                        enum_value_from_str = google_ads_enum_type[value_from_payload.upper()]
                        setattr(resource_obj, payload_key, enum_value_from_str)
                    except (KeyError, AttributeError) as e_enum:
                        raise ValueError(f"Valor de enum inválido '{value_from_payload}' para el campo '{payload_key}' (Tipo Enum Esperado: {enum_type_name}). Error: {e_enum}")
                else: # No se encontró mapeo de enum, intentar copy_from
                    logger.debug(f"No se encontró mapeo de enum para {payload_key}, se intentará copy_from.")
            
            elif field_descriptor.type == field_descriptor.TYPE_MESSAGE and isinstance(value_from_payload, dict):
                # Campo anidado (mensaje)
                nested_resource_type_name = field_descriptor.message_type.name # ej. "ManualCpc", "TargetSpend"
                nested_obj = getattr(resource_obj, payload_key) # Obtener el sub-mensaje
                # Llamada recursiva o manejo similar para el objeto anidado
                # Por simplicidad, dependemos de copy_from para anidados por ahora si no son enums
                # Si se necesita manejo de enums anidados, esta lógica debe ser recursiva
                # o copy_from debe ser suficiente si los enums anidados ya están convertidos.
                logger.debug(f"Procesando mensaje anidado '{payload_key}' de tipo '{nested_resource_type_name}' con copy_from.")


    # Usar client.copy_from para el grueso de la asignación después de manejar enums explícitamente
    try:
        client.copy_from(resource_obj, dict_to_copy)
    except Exception as e_copy:
        logger.error(f"Error durante client.copy_from para {resource_type_name} con dict {dict_to_copy}: {e_copy}", exc_info=True)
        raise TypeError(f"Error convirtiendo dict a {resource_type_name}: {e_copy}. Verifique la estructura del payload y los tipos de datos.")
            
    return resource_obj

# --- ACCIONES ---

def googleads_search_stream(client: Optional[AuthenticatedHttpClient], params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "googleads_search_stream"
    logger.info(f"Ejecutando {action_name} con params: {params}")
    
    customer_id: Optional[str] = params.get("customer_id")
    gaql_query: Optional[str] = params.get("query")
    client_config_override: Optional[Dict[str, Any]] = params.get("client_config_override") 

    if not customer_id:
        return {"status": "error", "action": action_name, "message": "'customer_id' es requerido.", "http_status": 400}
    if not gaql_query:
        return {"status": "error", "action": action_name, "message": "'query' (GAQL) es requerida.", "http_status": 400}
    
    customer_id_clean = str(customer_id).replace("-", "")

    try:
        gads_client = get_google_ads_client(client_config_override)
        ga_service = gads_client.get_service("GoogleAdsService")
        
        logger.info(f"Ejecutando GAQL query en Customer ID '{customer_id_clean}': {gaql_query[:300]}...")
        
        search_request = gads_client.get_type("SearchGoogleAdsStreamRequest")
        search_request.customer_id = customer_id_clean
        search_request.query = gaql_query
        if params.get("summary_row_setting"): 
             search_request.summary_row_setting = gads_client.enums.SummaryRowSettingEnum[params["summary_row_setting"].upper()]

        stream = ga_service.search_stream(request=search_request)
        results = []
        summary_row = None
        field_mask = None 

        for batch in stream:
            if field_mask is None and batch.field_mask:
                field_mask = [path for path in batch.field_mask.paths]
            for google_ads_row in batch.results:
                results.append(_format_google_ads_row_to_dict(google_ads_row))
            if batch.summary_row:
                summary_row = _format_google_ads_row_to_dict(batch.summary_row)
        
        response_data: Dict[str, Any] = {"results": results, "total_results": len(results)}
        if summary_row: response_data["summary_row"] = summary_row
        if field_mask: response_data["_field_mask_debug_"] = field_mask
            
        return {"status": "success", "data": response_data}

    except GoogleAdsException as ex:
        # Necesitamos la instancia de gads_client para decodificar enums de error correctamente
        gads_client_for_error = _google_ads_client_instance or GoogleAdsClient.load_from_dict(settings.GOOGLE_ADS.model_dump(exclude_none=True)) if not client_config_override else GoogleAdsClient.load_from_dict(client_config_override)
        return _handle_google_ads_api_exception(ex, action_name, gads_client_for_error, customer_id_clean)
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
    action_name = f"googleads_mutate_{resource_type_name.lower().replace('adgroupcriterion', 'keywords')}s" 
    logger.info(f"Ejecutando {action_name} con params (operations omitido del log): %s", {k:v for k,v in params.items() if k != 'operations'})

    customer_id: Optional[str] = params.get("customer_id")
    operations_payload: Optional[List[Dict[str, Any]]] = params.get("operations")
    partial_failure: bool = params.get("partial_failure", False) 
    validate_only: bool = params.get("validate_only", False)
    response_content_type_str: Optional[str] = params.get("response_content_type") 
    client_config_override: Optional[Dict[str, Any]] = params.get("client_config_override")

    if not customer_id: 
        return {"status": "error", "action": action_name, "message": "'customer_id' es requerido.", "http_status": 400}
    if not operations_payload or not isinstance(operations_payload, list) or not operations_payload: 
        return {"status": "error", "action": action_name, "message": "'operations' (lista no vacía de operaciones) es requerida.", "http_status": 400}

    customer_id_clean = str(customer_id).replace("-", "")

    try:
        gads_client = get_google_ads_client(client_config_override)
        service_client = gads_client.get_service(service_name)
        
        sdk_operations = []
        for op_idx, op_dict in enumerate(operations_payload):
            operation = gads_client.get_type(operation_type_name)
            
            if "create" in op_dict and isinstance(op_dict["create"], dict):
                created_resource_obj = _build_resource_from_dict(gads_client, resource_type_name, op_dict["create"])
                getattr(operation, "create").CopyFrom(created_resource_obj)
            elif "update" in op_dict and isinstance(op_dict["update"], dict):
                resource_data = op_dict["update"]
                if "resource_name" not in resource_data:
                    raise ValueError(f"Operación de actualización (índice {op_idx}) debe incluir 'resource_name'.")
                
                updated_resource_obj = _build_resource_from_dict(gads_client, resource_type_name, resource_data)
                getattr(operation, "update").CopyFrom(updated_resource_obj)
                
                update_mask_paths: Optional[List[str]] = None
                if "update_mask" in op_dict and isinstance(op_dict["update_mask"], (list, str)):
                    update_mask_paths = [p.strip() for p in op_dict["update_mask"].split(',')] if isinstance(op_dict["update_mask"], str) else op_dict["update_mask"]
                else: 
                    update_mask_paths = [key for key in resource_data.keys() if key != "resource_name"]

                if update_mask_paths:
                    operation.update_mask.CopyFrom(field_mask_pb2.FieldMask(paths=update_mask_paths))
            elif "remove" in op_dict and isinstance(op_dict["remove"], str):
                setattr(operation, "remove", op_dict["remove"])
            else:
                logger.warning(f"Operación para {resource_type_name} (índice {op_idx}) no soportada o malformada: {op_dict}. Se omite.")
                continue
            sdk_operations.append(operation)

        if not sdk_operations: 
            return {"status": "error", "action": action_name, "message": "No se proveyeron operaciones válidas.", "http_status": 400}

        mutate_request = gads_client.get_type(request_type_name)
        mutate_request.customer_id = customer_id_clean
        mutate_request.operations.extend(sdk_operations)
        mutate_request.partial_failure = partial_failure
        mutate_request.validate_only = validate_only
        if response_content_type_str:
            try:
                response_content_enum_val = gads_client.enums.ResponseContentTypeEnum[response_content_type_str.upper()]
                mutate_request.response_content_type = response_content_enum_val
            except KeyError:
                 logger.warning(f"ResponseContentType '{response_content_type_str}' inválido. Usando default.")

        response = getattr(service_client, mutate_method_name)(request=mutate_request)
        
        formatted_response: Dict[str, Any] = {"mutate_operation_responses": []}
        if response.partial_failure_error and response.partial_failure_error.IsInitialized():
            google_ads_failure_from_partial = gads_client.get_type("GoogleAdsFailure")
            for detail_any_value in response.partial_failure_error.details:
                if detail_any_value.Is(google_ads_failure_from_partial.DESCRIPTOR): 
                    detail_any_value.Unpack(google_ads_failure_from_partial) 
                    break
            partial_failure_ex = GoogleAdsException(failure_message=google_ads_failure_from_partial, call=None, trigger=None, request_id="N/A_PARTIAL")
            formatted_response["partial_failure_error_details"] = _handle_google_ads_api_exception(partial_failure_ex, f"{action_name}_partial_failure", gads_client, customer_id_clean).get("details", {}).get("googleAdsFailure")

        for result in response.results:
            res_dict = {"resource_name": result.resource_name}
            resource_returned_field_name = resource_type_name.split("::")[-1].lower()
            if resource_type_name == "AdGroupCriterion": resource_returned_field_name = "ad_group_criterion"

            if hasattr(result, resource_returned_field_name):
                resource_object_returned = getattr(result, resource_returned_field_name)
                if hasattr(resource_object_returned, '_pb') and resource_object_returned._pb.ByteSize() > 0:
                    res_dict[resource_returned_field_name] = _format_google_ads_row_to_dict(resource_object_returned)
            formatted_response["mutate_operation_responses"].append(res_dict)
            
        return {"status": "success", "data": formatted_response}

    except GoogleAdsException as ex:
        gads_client_for_error = _google_ads_client_instance or GoogleAdsClient.load_from_dict(settings.GOOGLE_ADS.model_dump(exclude_none=True)) if not client_config_override else GoogleAdsClient.load_from_dict(client_config_override)
        return _handle_google_ads_api_exception(ex, action_name, gads_client_for_error, customer_id_clean)
    except (ValueError, ConnectionError, TypeError) as conf_err: 
        logger.error(f"Error de configuración/conexión/payload en {action_name}: {conf_err}", exc_info=True)
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