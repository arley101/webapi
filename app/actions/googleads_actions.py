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

# Instancia global para reutilizar el cliente una vez inicializado
_google_ads_client_instance: Optional[GoogleAdsClient] = None

def get_google_ads_client(client_config_override: Optional[Dict[str, Any]] = None) -> GoogleAdsClient:
    """
    Inicializa y devuelve una instancia del cliente de Google Ads.
    Reutiliza la instancia si ya ha sido creada y no hay override.
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
        # Cargar credenciales desde la configuración global
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
        # CORRECCIÓN 1: Se elimina el parámetro `including_default_value_fields` que causaba el primer error.
        return json_format.MessageToDict(
            google_ads_row._pb, 
            preserving_proto_field_name=True
        )
    except Exception as e_json_format:
        logger.warning(f"Fallo al convertir GoogleAdsRow a dict usando json_format ({e_json_format}). La fila se representará como string.")
        return {"_raw_repr_": str(google_ads_row), "_serialization_error_": str(e_json_format)}


def _extract_google_ads_errors(failure_message: Any, client: GoogleAdsClient) -> List[Dict[str, Any]]:
    """Extrae y formatea errores de un objeto GoogleAdsFailure."""
    error_list = []
    if not (failure_message and hasattr(failure_message, 'errors')):
        return error_list

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
                    # Construye dinámicamente el nombre del Enum (ej. 'CampaignErrorEnum')
                    enum_type_name = f"{oneof_field_name[0].upper()}{oneof_field_name[1:].replace('_error', 'ErrorEnum')}"
                    enum_type = client.enums[enum_type_name]
                    # Obtiene el valor numérico del enum (ej. 2 para 'PAUSED')
                    enum_value = getattr(error_item.error_code, oneof_field_name)
                    # Convierte el valor numérico de nuevo a su nombre de string (ej. 'PAUSED')
                    err_detail["errorCode"] = enum_type(enum_value).name
                except (KeyError, AttributeError):
                    err_detail["errorCode"] = str(getattr(error_item.error_code, oneof_field_name))
             else:
                err_detail["errorCode"] = "UNKNOWN"
        error_list.append(err_detail)
    return error_list


def _handle_google_ads_api_exception(ex: GoogleAdsException, action_name: str, gads_client_for_enums: GoogleAdsClient, customer_id_log: Optional[str] = None) -> Dict[str, Any]:
    """Formatea una GoogleAdsException en una respuesta de error estándar."""
    error_details_extracted = _extract_google_ads_errors(ex.failure, gads_client_for_enums)
    
    logger.error(f"Google Ads API Exception en acción '{action_name}' para customer_id '{customer_id_log or 'N/A'}'. Request ID: {ex.request_id}. Errors: {error_details_extracted}", exc_info=False)
    
    primary_message = "Error en la API de Google Ads."
    if error_details_extracted and error_details_extracted[0].get("message"):
        primary_message = error_details_extracted[0]["message"]

    return {"status": "error", "action": action_name, "message": primary_message, "details": {"googleAdsFailure": {"errors": error_details_extracted, "requestId": ex.request_id}},"http_status": 400}

def _build_resource_from_dict(client: GoogleAdsClient, resource_obj: Any, data_dict: Dict[str, Any]):
    """
    CORRECCIÓN 2: Popula un objeto de recurso protobuf desde un dict, manejando enums de forma inteligente.
    """
    for key, value in data_dict.items():
        if isinstance(value, dict):
            # Recurso anidado
            _build_resource_from_dict(client, getattr(resource_obj, key), value)
        elif isinstance(value, list):
            # Campo repetido (no común en los updates simples que estamos haciendo, pero es robusto tenerlo)
            list_field = getattr(resource_obj, key)
            for item in value:
                if isinstance(item, dict):
                    new_item = list_field.add()
                    _build_resource_from_dict(client, new_item, item)
                else:
                    list_field.append(item)
        elif hasattr(resource_obj, key):
            # Es un campo simple. Verificar si es un enum.
            field_descriptor = getattr(type(resource_obj), key).meta.descriptor
            if field_descriptor.enum_type:
                # ¡Esta es la corrección clave!
                # Se busca el tipo de enum (ej. CampaignStatusEnum) y se convierte el string "PAUSED"
                # al valor numérico que el SDK espera.
                enum_type = client.enums[f"{field_descriptor.enum_type.name}"]
                enum_value = enum_type[value] # Esto busca "PAUSED" en CampaignStatusEnum y devuelve el objeto enum
                setattr(resource_obj, key, enum_value)
            else:
                # No es un enum, asignar directamente
                setattr(resource_obj, key, value)
    return resource_obj


# --- ACCIONES ---

def googleads_search_stream(client: Optional[AuthenticatedHttpClient], params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "googleads_search_stream"
    logger.info(f"Ejecutando {action_name} con params: {params}")
    
    customer_id_to_use = params.get("customer_id") or settings.GOOGLE_ADS.LOGIN_CUSTOMER_ID
    gaql_query: Optional[str] = params.get("query")
    if not customer_id_to_use or not gaql_query:
        return {"status": "error", "action": action_name, "message": "Se requiere 'customer_id' y 'query'.", "http_status": 400}
    
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
    logger.info(f"Ejecutando {action_name} con params (operations omitido del log): %s", {k:v for k,v in params.items() if k != 'operations'})

    customer_id_to_use = params.get("customer_id") or settings.GOOGLE_ADS.LOGIN_CUSTOMER_ID
    operations_payload = params.get("operations")
    if not customer_id_to_use or not operations_payload:
        return {"status": "error", "action": action_name, "message": "Se requiere 'customer_id' y 'operations'.", "http_status": 400}

    customer_id_clean = str(customer_id_to_use).replace("-", "")

    try:
        gads_client = get_google_ads_client(params.get("client_config_override"))
        service_client = gads_client.get_service(service_name)
        
        sdk_operations = []
        for op_dict in operations_payload:
            operation = gads_client.get_type(operation_type_name)
            
            if "create" in op_dict and isinstance(op_dict["create"], dict):
                resource_obj = gads_client.get_type(resource_type_name)
                _build_resource_from_dict(gads_client, resource_obj, op_dict["create"])
                getattr(operation, "create").CopyFrom(resource_obj)

            elif "update" in op_dict and isinstance(op_dict["update"], dict):
                resource_data = op_dict["update"]
                resource_name = resource_data.get("resource_name")
                if not resource_name: raise ValueError("Operación de actualización debe incluir 'resource_name'.")
                
                resource_obj = gads_client.get_type(resource_type_name)
                # No se puede asignar resource_name y luego otros campos, se debe construir desde el dict
                _build_resource_from_dict(gads_client, resource_obj, resource_data)
                getattr(operation, "update").CopyFrom(resource_obj)

                # Crear máscara de campo a partir de las claves en el diccionario de actualización (excepto resource_name)
                update_mask = protobuf_helpers.field_mask(None, resource_obj._pb)
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
        mutate_request.partial_failure = params.get("partial_failure", False)
        mutate_request.validate_only = params.get("validate_only", False)

        response = getattr(service_client, mutate_method_name)(request=mutate_request)
        
        formatted_response: Dict[str, Any] = {"results": []}
        if response.partial_failure_error:
            failure_message = gads_client.get_type("GoogleAdsFailure")
            failure_message.ParseFromString(response.partial_failure_error.details[0].value)
            formatted_response["partial_failure_error"] = _extract_google_ads_errors(failure_message, gads_client)

        for result in response.results:
            formatted_response["results"].append(json_format.MessageToDict(result._pb))
            
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