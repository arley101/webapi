# app/actions/hubspot_actions.py
import logging
import time
from typing import Dict, Any, Optional, List
from hubspot import HubSpot
from hubspot.crm.contacts import SimplePublicObjectInput, PublicObjectSearchRequest
from hubspot.crm.deals import SimplePublicObjectInput as DealSimplePublicObjectInput
from hubspot.crm.companies import SimplePublicObjectInput as CompanySimplePublicObjectInput
from hubspot.crm.objects.notes import SimplePublicObjectInput as NoteSimplePublicObjectInput
from hubspot.crm.associations.v4.models import AssociationSpec
from datetime import datetime

# Importación de la configuración central
from app.core.config import settings

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
    token = params.get("hubspot_token_override", settings.HUBSPOT_PRIVATE_APP_TOKEN)
    if not token:
        raise ValueError("Se requiere el Token de App Privada de HubSpot (HUBSPOT_PRIVATE_APP_TOKEN).")
    return HubSpot(access_token=token)

def _handle_hubspot_api_error(e: Any, action_name: str) -> Dict[str, Any]:
    """
    Centraliza el manejo de errores de la API de HubSpot.
    Esta versión es más robusta y no depende de una importación específica de ApiException.
    """
    # Comprueba si el error tiene los atributos de una ApiException del SDK de HubSpot
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
        # Maneja cualquier otra excepción de forma genérica
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
        created_contact = hs_client.crm.contacts.basic_api.create(simple_public_object_input=contact_input)
        return {"status": "success", "data": _serialize_datetimes(created_contact.to_dict())}
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
        created_deal = hs_client.crm.deals.basic_api.create(simple_public_object_input=deal_input)
        return {"status": "success", "data": _serialize_datetimes(created_deal.to_dict())}
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
        if search_result.total == 0:
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
        hs_client = _get_hubspot_client(params)
        workflow_id = params.get("workflow_id")
        contact_email = params.get("contact_email")
        if not workflow_id or not contact_email: raise ValueError("Los parámetros 'workflow_id' y 'contact_email' son requeridos.")
        
        api_client = hs_client.crm.automation.workflows_api
        api_client.enroll(workflow_id=str(workflow_id), email=str(contact_email))
        
        return {"status": "success", "message": f"Contacto con email '{contact_email}' inscrito en el workflow '{workflow_id}'."}
    except Exception as e:
        return _handle_hubspot_api_error(e, action_name)

def hubspot_get_contacts_from_list(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "hubspot_get_contacts_from_list"
    try:
        hs_client = _get_hubspot_client(params)
        list_id = params.get("list_id")
        if not list_id: raise ValueError("El parámetro 'list_id' es requerido.")
        filter_group = {"filters": [{"propertyName": "hs_list_memberships", "operator": "EQ", "value": list_id}]}
        search_request = PublicObjectSearchRequest(filter_groups=[filter_group], properties=["email", "firstname", "lastname"], limit=params.get("limit", 100))
        search_result = hs_client.crm.contacts.search_api.do_search(public_object_search_request=search_request)
        return {"status": "success", "data": _serialize_datetimes(search_result.to_dict())}
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
        created_company = hs_client.crm.companies.basic_api.create(simple_public_object_input=company_input)
        company_id = created_company.id
        
        association_spec = [AssociationSpec(association_category="HUBSPOT_DEFINED", association_type_id=1)] # 1 = Contact to Company
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
        created_company = hs_client.crm.companies.basic_api.create(simple_public_object_input=company_input)
        return {"status": "success", "data": _serialize_datetimes(created_company.to_dict())}
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
        
        association_spec = [AssociationSpec(association_category="HUBSPOT_DEFINED", association_type_id=3)] # 3 = Contact to Deal
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
        created_note = hs_client.crm.objects.notes.basic_api.create(simple_public_object_input=note_input)
        note_id = created_note.id
        
        association_spec = [AssociationSpec(association_category="HUBSPOT_DEFINED", association_type_id=202)] # 202 = Note to Contact
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
