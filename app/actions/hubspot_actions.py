# app/actions/hubspot_actions.py
import logging
from typing import Dict, Any
from hubspot import HubSpot
from hubspot.crm.contacts import SimplePublicObjectInput, PublicObjectSearchRequest
from hubspot.crm.deals import SimplePublicObjectInput as DealSimplePublicObjectInput
from hubspot.crm.companies import SimplePublicObjectInput as CompanySimplePublicObjectInput
from hubspot.crm.objects.notes import SimplePublicObjectInput as NoteSimplePublicObjectInput
from hubspot.crm.associations.v4.models import AssociationSpec
from datetime import datetime

# Importación de la configuración central
from app.core.config import settings
# ✅ IMPORTACIÓN DIRECTA DEL RESOLVER PARA EVITAR CIRCULARIDAD
def _get_resolver():
    from app.actions.resolver_actions import Resolver
    return Resolver()

logger = logging.getLogger(__name__)

# --- FUNCIÓN DE INGENIERÍA PARA CORRECCIÓN DE ERRORES ---
def _serialize_datetimes(data: Any) -> Any:
    """
    Recorre recursivamente un objeto (dict o list) y convierte cualquier
    instancia de datetime a su representación en string ISO 8601 para
    garantizar la compatibilidad con JSON. Soluciona el error 'datetime is not JSON serializable'.
    """
    if isinstance(data, dict):
        return {k: _serialize_datetimes(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [_serialize_datetimes(i) for i in data]
    elif isinstance(data, datetime):
        return data.isoformat()
    else:
        return data

# --- HELPERS DE CONEXIÓN Y MANEJO DE ERRORES ---

def _get_hubspot_client(params: Dict[str, Any]) -> HubSpot:
    """Crea y devuelve un cliente de HubSpot autenticado."""
    # CORRECCIÓN: Se usa settings.HUBSPOT_PRIVATE_APP_KEY que es el nombre correcto de la propiedad en el objeto de configuración.
    token = params.get("hubspot_token_override", settings.HUBSPOT_PRIVATE_APP_KEY)
    if not token:
        raise ValueError("Se requiere el Token de App Privada de HubSpot (HUBSPOT_PRIVATE_APP_TOKEN en variables de entorno).")
    return HubSpot(access_token=token)

def _handle_hubspot_api_error(e: Any, action_name: str) -> Dict[str, Any]:
    """
    Centraliza el manejo de errores de la API de HubSpot.
    """
    if hasattr(e, 'status') and hasattr(e, 'body') and hasattr(e, 'reason'):
        logger.error(f"Error en HubSpot Action '{action_name}': {e.status} - {e.body}", exc_info=True)
        return {
            "status": "error", 
            "action": action_name, 
            "message": f"Error en API de HubSpot: {e.reason}", 
            "details": e.body, 
            "http_status": e.status
        }
    else:
        logger.error(f"Error inesperado en HubSpot Action '{action_name}': {e}", exc_info=True)
        return {
            "status": "error",
            "action": action_name,
            "message": "Error inesperado en el módulo de HubSpot.",
            "details": str(e),
            "http_status": 500
        }

# --- IMPLEMENTACIÓN COMPLETA DE ACCIONES DEL ACTION MAPPER ---

def hubspot_get_contacts(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "hubspot_get_contacts"
    try:
        hs_client = _get_hubspot_client(params)
        properties = params.get("properties", ["email", "firstname", "lastname", "phone", "hs_object_id"])
        contacts_page = hs_client.crm.contacts.basic_api.get_page(
            limit=params.get("limit", 100),
            after=params.get("after"),
            properties=properties
        )
        return {"status": "success", "data": _serialize_datetimes(contacts_page.to_dict())}
    except Exception as e:
        return _handle_hubspot_api_error(e, action_name)

def hubspot_create_contact(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "hubspot_create_contact"
    try:
        hs_client = _get_hubspot_client(params)
        properties = params.get("properties_payload")
        if not properties: raise ValueError("El parámetro 'properties_payload' es requerido.")
        contact_input = SimplePublicObjectInput(properties=properties)
        # CORRECCIÓN: Cambiar de simple_public_object_input a simple_public_object_input_for_create
        created_contact = hs_client.crm.contacts.basic_api.create(simple_public_object_input_for_create=contact_input)

        result = {"status": "success", "data": _serialize_datetimes(created_contact.to_dict())}
        # ✅ PERSISTENCIA DE MEMORIA - FUNCIÓN DE CREACIÓN (protegida)
        try:
            _get_resolver().save_action_result(action_name, params, result)
        except Exception as mem_err:
            logger.warning(f"No se pudo persistir memoria para {action_name}: {mem_err}")
        return result
    except Exception as e:
        return _handle_hubspot_api_error(e, action_name)

def hubspot_update_contact(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "hubspot_update_contact"
    try:
        hs_client = _get_hubspot_client(params)
        contact_id = params.get("contact_id")
        properties = params.get("properties_payload")
        if not contact_id or not properties: raise ValueError("Los parámetros 'contact_id' y 'properties_payload' son requeridos.")
        contact_input = SimplePublicObjectInput(properties=properties)
        updated_contact = hs_client.crm.contacts.basic_api.update(contact_id=str(contact_id), simple_public_object_input=contact_input)
        return {"status": "success", "data": _serialize_datetimes(updated_contact.to_dict())}
    except Exception as e:
        return _handle_hubspot_api_error(e, action_name)

def hubspot_delete_contact(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "hubspot_delete_contact"
    try:
        hs_client = _get_hubspot_client(params)
        contact_id = params.get("contact_id")
        if not contact_id: raise ValueError("El parámetro 'contact_id' es requerido.")
        hs_client.crm.contacts.basic_api.archive(contact_id=str(contact_id))
        return {"status": "success", "message": f"Contacto '{contact_id}' archivado exitosamente."}
    except Exception as e:
        return _handle_hubspot_api_error(e, action_name)

def hubspot_get_deals(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "hubspot_get_deals"
    try:
        hs_client = _get_hubspot_client(params)
        properties = params.get("properties", ["dealname", "amount", "dealstage", "closedate", "pipeline", "hs_object_id"])
        deals_page = hs_client.crm.deals.basic_api.get_page(
            limit=params.get("limit", 100),
            after=params.get("after"),
            properties=properties
        )
        return {"status": "success", "data": _serialize_datetimes(deals_page.to_dict())}
    except Exception as e:
        return _handle_hubspot_api_error(e, action_name)

def hubspot_create_deal(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "hubspot_create_deal"
    try:
        hs_client = _get_hubspot_client(params)
        properties = params.get("properties_payload")
        if not properties: raise ValueError("El parámetro 'properties_payload' es requerido.")
        deal_input = DealSimplePublicObjectInput(properties=properties)
        # CORRECCIÓN: Cambiar de simple_public_object_input a simple_public_object_input_for_create
        created_deal = hs_client.crm.deals.basic_api.create(simple_public_object_input_for_create=deal_input)

        result = {"status": "success", "data": _serialize_datetimes(created_deal.to_dict())}
        # ✅ PERSISTENCIA DE MEMORIA - FUNCIÓN DE CREACIÓN (protegida)
        try:
            _get_resolver().save_action_result(action_name, params, result)
        except Exception as mem_err:
            logger.warning(f"No se pudo persistir memoria para {action_name}: {mem_err}")
        return result
    except Exception as e:
        return _handle_hubspot_api_error(e, action_name)

def hubspot_update_deal(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "hubspot_update_deal"
    try:
        hs_client = _get_hubspot_client(params)
        deal_id = params.get("deal_id")
        properties = params.get("properties_payload")
        if not deal_id or not properties: raise ValueError("Los parámetros 'deal_id' y 'properties_payload' son requeridos.")
        deal_input = DealSimplePublicObjectInput(properties=properties)
        updated_deal = hs_client.crm.deals.basic_api.update(deal_id=str(deal_id), simple_public_object_input=deal_input)
        return {"status": "success", "data": _serialize_datetimes(updated_deal.to_dict())}
    except Exception as e:
        return _handle_hubspot_api_error(e, action_name)

def hubspot_delete_deal(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "hubspot_delete_deal"
    try:
        hs_client = _get_hubspot_client(params)
        deal_id = params.get("deal_id")
        if not deal_id: raise ValueError("El parámetro 'deal_id' es requerido.")
        hs_client.crm.deals.basic_api.archive(deal_id=str(deal_id))
        return {"status": "success", "message": f"Negocio '{deal_id}' archivado exitosamente."}
    except Exception as e:
        return _handle_hubspot_api_error(e, action_name)

def hubspot_find_contact_by_email(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "hubspot_find_contact_by_email"
    try:
        hs_client = _get_hubspot_client(params)
        email = params.get("email")
        if not email: raise ValueError("El parámetro 'email' es requerido.")
        filter_group = {"filters": [{"propertyName": "email", "operator": "EQ", "value": email}]}
        search_request = PublicObjectSearchRequest(filter_groups=[filter_group], properties=["email", "firstname", "lastname", "phone"], limit=1)
        search_result = hs_client.crm.contacts.search_api.do_search(public_object_search_request=search_request)
        total = getattr(search_result, "total", None)
        if total == 0 or (total is None and not getattr(search_result, "results", [])):
            return {"status": "error", "message": f"No se encontró un contacto con el email '{email}'.", "http_status": 404}
        return {"status": "success", "data": _serialize_datetimes(search_result.results[0].to_dict())}
    except Exception as e:
        return _handle_hubspot_api_error(e, action_name)

def hubspot_update_deal_stage(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "hubspot_update_deal_stage"
    try:
        deal_id = params.get("deal_id")
        new_stage_id = params.get("new_stage_id")
        if not deal_id or not new_stage_id: raise ValueError("Los parámetros 'deal_id' y 'new_stage_id' son requeridos.")
        update_params = {"deal_id": deal_id, "properties_payload": {"dealstage": new_stage_id}}
        return hubspot_update_deal(client, update_params)
    except Exception as e:
        return _handle_hubspot_api_error(e, action_name)

def hubspot_enroll_contact_in_workflow(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "hubspot_enroll_contact_in_workflow"
    try:
        return {
            "status": "error",
            "action": action_name,
            "message": "Acción deshabilitada temporalmente: la API de Workflows varía por cuenta. Validar endpoint disponible antes de producción.",
            "http_status": 501
        }
    except Exception as e:
        return _handle_hubspot_api_error(e, action_name)

def hubspot_get_contacts_from_list(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "hubspot_get_contacts_from_list"
    try:
        return {
            "status": "error",
            "action": action_name,
            "message": "No soportado por Search API. Implementar con Lists API (REST) para resultados correctos.",
            "http_status": 501
        }
    except Exception as e:
        return _handle_hubspot_api_error(e, action_name)

def hubspot_create_company_and_associate_contact(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "hubspot_create_company_and_associate_contact"
    try:
        hs_client = _get_hubspot_client(params)
        company_properties = params.get("company_properties")
        contact_id = params.get("contact_id")
        if not company_properties or not contact_id: raise ValueError("Los parámetros 'company_properties' y 'contact_id' son requeridos.")
        company_input = CompanySimplePublicObjectInput(properties=company_properties)
        # CORRECCIÓN: Cambiar de simple_public_object_input a simple_public_object_input_for_create
        created_company = hs_client.crm.companies.basic_api.create(simple_public_object_input_for_create=company_input)
        company_id = created_company.id
        
        assoc_id = getattr(settings, "HUBSPOT_ASSOC_CONTACT_COMPANY", 1)
        association_spec = [AssociationSpec(association_category="HUBSPOT_DEFINED", association_type_id=assoc_id)]
        hs_client.crm.associations.v4.basic_api.create(
            from_object_type="contacts", from_object_id=str(contact_id),
            to_object_type="companies", to_object_id=str(company_id),
            association_spec=association_spec
        )
        return {"status": "success", "message": f"Compañía creada (ID: {company_id}) y asociada al contacto (ID: {contact_id}).", "data": _serialize_datetimes(created_company.to_dict())}
    except Exception as e:
        return _handle_hubspot_api_error(e, action_name)

def hubspot_get_contact_by_id(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "hubspot_get_contact_by_id"
    try:
        hs_client = _get_hubspot_client(params)
        contact_id = params.get("contact_id")
        if not contact_id: raise ValueError("El parámetro 'contact_id' es requerido.")
        properties = params.get("properties", ["email", "firstname", "lastname", "phone"])
        contact = hs_client.crm.contacts.basic_api.get_by_id(contact_id=str(contact_id), properties=properties)
        return {"status": "success", "data": _serialize_datetimes(contact.to_dict())}
    except Exception as e:
        return _handle_hubspot_api_error(e, action_name)

def hubspot_create_company(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "hubspot_create_company"
    try:
        hs_client = _get_hubspot_client(params)
        properties = params.get("properties_payload")
        if not properties: raise ValueError("El parámetro 'properties_payload' es requerido.")
        company_input = CompanySimplePublicObjectInput(properties=properties)
        # CORRECCIÓN: Cambiar de simple_public_object_input a simple_public_object_input_for_create
        created_company = hs_client.crm.companies.basic_api.create(simple_public_object_input_for_create=company_input)

        result = {"status": "success", "data": _serialize_datetimes(created_company.to_dict())}
        # ✅ PERSISTENCIA DE MEMORIA - FUNCIÓN DE CREACIÓN (protegida)
        try:
            _get_resolver().save_action_result(action_name, params, result)
        except Exception as mem_err:
            logger.warning(f"No se pudo persistir memoria para {action_name}: {mem_err}")
        return result
    except Exception as e:
        return _handle_hubspot_api_error(e, action_name)

def hubspot_get_company_by_id(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "hubspot_get_company_by_id"
    try:
        hs_client = _get_hubspot_client(params)
        company_id = params.get("company_id")
        if not company_id: raise ValueError("El parámetro 'company_id' es requerido.")
        properties = params.get("properties", ["name", "domain", "industry", "website"])
        company = hs_client.crm.companies.basic_api.get_by_id(company_id=str(company_id), properties=properties)
        return {"status": "success", "data": _serialize_datetimes(company.to_dict())}
    except Exception as e:
        return _handle_hubspot_api_error(e, action_name)

def hubspot_get_deal_by_id(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "hubspot_get_deal_by_id"
    try:
        hs_client = _get_hubspot_client(params)
        deal_id = params.get("deal_id")
        if not deal_id: raise ValueError("El parámetro 'deal_id' es requerido.")
        properties = params.get("properties", ["dealname", "amount", "dealstage", "closedate"])
        deal = hs_client.crm.deals.basic_api.get_by_id(deal_id=str(deal_id), properties=properties)
        return {"status": "success", "data": _serialize_datetimes(deal.to_dict())}
    except Exception as e:
        return _handle_hubspot_api_error(e, action_name)

def hubspot_associate_contact_to_deal(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "hubspot_associate_contact_to_deal"
    try:
        hs_client = _get_hubspot_client(params)
        contact_id = params.get("contact_id")
        deal_id = params.get("deal_id")
        if not contact_id or not deal_id: raise ValueError("Los parámetros 'contact_id' y 'deal_id' son requeridos.")
        
        assoc_id = getattr(settings, "HUBSPOT_ASSOC_CONTACT_DEAL", 3)
        association_spec = [AssociationSpec(association_category="HUBSPOT_DEFINED", association_type_id=assoc_id)]
        hs_client.crm.associations.v4.basic_api.create(
            from_object_type="contacts", from_object_id=str(contact_id),
            to_object_type="deals", to_object_id=str(deal_id),
            association_spec=association_spec
        )
        return {"status": "success", "message": f"Contacto (ID: {contact_id}) asociado al negocio (ID: {deal_id})."}
    except Exception as e:
        return _handle_hubspot_api_error(e, action_name)

def hubspot_add_note_to_contact(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "hubspot_add_note_to_contact"
    try:
        hs_client = _get_hubspot_client(params)
        contact_id = params.get("contact_id")
        note_body = params.get("note_body")
        if not contact_id or not note_body: raise ValueError("Los parámetros 'contact_id' y 'note_body' son requeridos.")
        
        timestamp = params.get("timestamp", datetime.utcnow().isoformat() + "Z")
        note_properties = {"hs_note_body": note_body, "hs_timestamp": timestamp}
        note_input = NoteSimplePublicObjectInput(properties=note_properties)
        # CORRECCIÓN: Cambiar de simple_public_object_input a simple_public_object_input_for_create
        created_note = hs_client.crm.objects.notes.basic_api.create(simple_public_object_input_for_create=note_input)
        note_id = created_note.id
        
        assoc_id = getattr(settings, "HUBSPOT_ASSOC_NOTE_CONTACT", 202)
        association_spec = [AssociationSpec(association_category="HUBSPOT_DEFINED", association_type_id=assoc_id)]
        hs_client.crm.associations.v4.basic_api.create(
            from_object_type="notes", from_object_id=str(note_id),
            to_object_type="contacts", to_object_id=str(contact_id),
            association_spec=association_spec
        )
        return {"status": "success", "message": f"Nota creada (ID: {note_id}) y asociada al contacto (ID: {contact_id}).", "data": _serialize_datetimes(created_note.to_dict())}
    except Exception as e:
        return _handle_hubspot_api_error(e, action_name)

def hubspot_get_timeline_events(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "hubspot_get_timeline_events"
    return {"status": "error", "action": action_name, "message": "La API de Timeline v3 está obsoleta y la v4 no tiene un equivalente directo para esta acción. Se requiere una implementación personalizada.", "http_status": 501}

def hubspot_search_companies_by_domain(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "hubspot_search_companies_by_domain"
    try:
        hs_client = _get_hubspot_client(params)
        domain = params.get("domain")
        if not domain: raise ValueError("El parámetro 'domain' es requerido.")
        filter_group = {"filters": [{"propertyName": "domain", "operator": "EQ", "value": domain}]}
        properties = params.get("properties", ["name", "domain", "website", "industry"])
        search_request = PublicObjectSearchRequest(filter_groups=[filter_group], properties=properties, limit=params.get("limit", 100))
        search_result = hs_client.crm.companies.search_api.do_search(public_object_search_request=search_request)
        return {"status": "success", "data": _serialize_datetimes(search_result.to_dict())}
    except Exception as e:
        return _handle_hubspot_api_error(e, action_name)


# ============================================================================
# FUNCIONES ADICIONALES RESTAURADAS
# ============================================================================

def hubspot_create_task(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Crear una tarea en HubSpot."""
    action_name = "hubspot_create_task"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    try:
        hs_client = _get_hubspot_client(params)

        # Validar parámetros requeridos
        task_title = params.get("title")
        if not task_title:
            raise ValueError("El parámetro 'title' es requerido.")

        # Construir propiedades de la tarea
        task_properties = {
            "hs_task_subject": task_title,
            "hs_task_body": params.get("description", ""),
            "hs_task_status": params.get("status", "NOT_STARTED"),
            "hs_task_priority": params.get("priority", "MEDIUM"),
            "hs_task_type": params.get("task_type", "TODO"),
        }

        # Agregar fecha de vencimiento si se proporciona (timestamp en ms)
        due_date = params.get("due_date")
        if due_date:
            try:
                if isinstance(due_date, str):
                    due_datetime = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                    task_properties["hs_task_due_date"] = int(due_datetime.timestamp() * 1000)
                elif isinstance(due_date, (int, float)):
                    # Asumir milisegundos si parece grande; si viene en segundos, conviértelo a ms
                    ts = int(due_date)
                    task_properties["hs_task_due_date"] = ts if ts > 10_000_000_000 else ts * 1000
            except Exception:
                logger.warning(f"Formato de fecha inválido en due_date: {due_date}")

        # Agregar propietario si se especifica
        owner_id = params.get("owner_id")
        if owner_id:
            task_properties["hubspot_owner_id"] = owner_id

        # Crear la tarea
        task_input = SimplePublicObjectInput(properties=task_properties)
        result = hs_client.crm.objects.tasks.basic_api.create(
            simple_public_object_input_for_create=task_input
        )

        logger.info(f"Tarea creada exitosamente con ID: {result.id}")
        return {"status": "success", "data": _serialize_datetimes(result.to_dict())}

    except Exception as e:
        return _handle_hubspot_api_error(e, action_name)


def hubspot_get_pipeline_stages(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Obtener las etapas de un pipeline en HubSpot."""
    action_name = "hubspot_get_pipeline_stages"
    logger.info(f"Ejecutando {action_name} con params: {params}")
    
    try:
        hs_client = _get_hubspot_client(params)
        
        # Determinar el tipo de objeto (por defecto deals)
        object_type = params.get("object_type", "deals")
        pipeline_id = params.get("pipeline_id")
        
        if object_type == "deals":
            # Obtener pipelines de deals
            if pipeline_id:
                # Obtener un pipeline específico
                pipeline = hs_client.crm.pipelines.pipelines_api.get_by_id(object_type="deals", pipeline_id=pipeline_id)
                stages = pipeline.stages
                pipeline_info = {
                    "id": pipeline.id,
                    "label": pipeline.label,
                    "display_order": pipeline.display_order,
                    "stages": []
                }
                
                for stage in stages:
                    stage_info = {
                        "id": stage.id,
                        "label": stage.label,
                        "display_order": stage.display_order,
                        "metadata": stage.metadata,
                        "created_at": stage.created_at,
                        "updated_at": stage.updated_at
                    }
                    pipeline_info["stages"].append(stage_info)
                
                return {"status": "success", "data": _serialize_datetimes(pipeline_info)}
            else:
                # Obtener todos los pipelines de deals con sus etapas
                pipelines_result = hs_client.crm.pipelines.pipelines_api.get_all(object_type="deals")
                pipelines_data = []
                
                for pipeline in pipelines_result.results:
                    pipeline_info = {
                        "id": pipeline.id,
                        "label": pipeline.label,
                        "display_order": pipeline.display_order,
                        "stages": []
                    }
                    
                    for stage in pipeline.stages:
                        stage_info = {
                            "id": stage.id,
                            "label": stage.label,
                            "display_order": stage.display_order,
                            "metadata": stage.metadata,
                            "created_at": stage.created_at,
                            "updated_at": stage.updated_at
                        }
                        pipeline_info["stages"].append(stage_info)
                    
                    pipelines_data.append(pipeline_info)
                
                return {"status": "success", "data": _serialize_datetimes(pipelines_data)}
        
        elif object_type == "tickets":
            # Obtener pipelines de tickets
            if pipeline_id:
                pipeline = hs_client.crm.pipelines.pipelines_api.get_by_id(object_type="tickets", pipeline_id=pipeline_id)
            else:
                pipelines_result = hs_client.crm.pipelines.pipelines_api.get_all(object_type="tickets")
                return {"status": "success", "data": _serialize_datetimes(pipelines_result.to_dict())}
        
        else:
            raise ValueError(f"Tipo de objeto no soportado: {object_type}. Use 'deals' o 'tickets'.")
    
    except Exception as e:
        return _handle_hubspot_api_error(e, action_name)

def hubspot_manage_pipeline(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Gestionar pipeline completo de ventas en HubSpot."""
    action_name = "hubspot_manage_pipeline"
    logger.info(f"Ejecutando {action_name} con params: {params}")
    
    operation = params.get("operation", "list")  # list, create, update, delete
    
    try:
        client = _get_hubspot_client(params)
        
        if operation == "list":
            # Obtener todos los pipelines
            from hubspot.crm.pipelines import PipelinesApi
            pipelines_api = PipelinesApi(client)
            
            object_type = params.get("object_type", "deals")
            pipelines = pipelines_api.get_all(object_type=object_type)
            
            pipeline_data = []
            for pipeline in pipelines.results:
                stages_data = []
                for stage in pipeline.stages:
                    stages_data.append({
                        "id": stage.id,
                        "label": stage.label,
                        "display_order": stage.display_order,
                        "metadata": stage.metadata if hasattr(stage, 'metadata') else {}
                    })
                
                pipeline_data.append({
                    "id": pipeline.id,
                    "label": pipeline.label,
                    "display_order": pipeline.display_order,
                    "stages": stages_data,
                    "created_at": str(pipeline.created_at) if hasattr(pipeline, 'created_at') else None,
                    "updated_at": str(pipeline.updated_at) if hasattr(pipeline, 'updated_at') else None
                })
            
            return {
                "status": "success",  # Cambiar de "success: True" a "status: success"
                "data": pipeline_data,
                "total_count": len(pipeline_data),
                "timestamp": datetime.now().isoformat()
            }
            
        elif operation == "create":
            # Crear un nuevo pipeline
            from hubspot.crm.pipelines import PipelineInput, PipelineStageInput, PipelinesApi
            
            pipeline_input = PipelineInput(
                label=params.get("label"),
                display_order=params.get("display_order", 0),
                stages=[]
            )
            
            # Agregar stages si se proporcionan
            if "stages" in params:
                for stage_data in params["stages"]:
                    stage = PipelineStageInput(
                        label=stage_data["label"],
                        display_order=stage_data.get("display_order", 0),
                        metadata=stage_data.get("metadata", {})
                    )
                    pipeline_input.stages.append(stage)
            
            pipelines_api = PipelinesApi(client)
            object_type = params.get("object_type", "deals")
            
            result = pipelines_api.create(
                object_type=object_type,
                pipeline_input=pipeline_input
            )
            
            return {
                "success": True,
                "pipeline_id": result.id,
                "label": result.label,
                "stages_created": len(result.stages),
                "timestamp": datetime.now().isoformat()
            }
            
        elif operation == "update":
            # Actualizar pipeline existente
            from hubspot.crm.pipelines import PipelinePatchInput, PipelinesApi
            
            pipeline_id = params.get("pipeline_id")
            if not pipeline_id:
                return {"success": False, "error": "pipeline_id es requerido para actualizar", "timestamp": datetime.now().isoformat()}
            
            pipeline_patch = PipelinePatchInput()
            
            if "label" in params:
                pipeline_patch.label = params["label"]
            if "display_order" in params:
                pipeline_patch.display_order = params["display_order"]
            
            pipelines_api = PipelinesApi(client)
            object_type = params.get("object_type", "deals")
            
            result = pipelines_api.update(
                object_type=object_type,
                pipeline_id=pipeline_id,
                pipeline_patch_input=pipeline_patch
            )
            
            return {
                "success": True,
                "pipeline_id": result.id,
                "label": result.label,
                "updated_at": str(result.updated_at) if hasattr(result, 'updated_at') else None,
                "timestamp": datetime.now().isoformat()
            }
            
        elif operation == "delete":
            # Eliminar pipeline
            from hubspot.crm.pipelines import PipelinesApi
            
            pipeline_id = params.get("pipeline_id")
            if not pipeline_id:
                return {"success": False, "error": "pipeline_id es requerido para eliminar", "timestamp": datetime.now().isoformat()}
            
            pipelines_api = PipelinesApi(client)
            object_type = params.get("object_type", "deals")
            
            pipelines_api.archive(
                object_type=object_type,
                pipeline_id=pipeline_id
            )
            
            return {
                "success": True,
                "message": f"Pipeline {pipeline_id} eliminado exitosamente",
                "timestamp": datetime.now().isoformat()
            }
            
        else:
            return {
                "status": "error",  # Cambiar de "success: False" a "status: error"
                "message": f"Operación no válida: {operation}. Use: list, create, update, delete",
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Error en {action_name}: {str(e)}")
        return _handle_hubspot_api_error(e, action_name)

# --- FIN DEL MÓDULO actions/hubspot_actions.py ---