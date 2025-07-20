# app/actions/hubspot_actions.py
import logging
import time  # Agregar esta importación para timestamp en hubspot_add_note_to_contact
from typing import Dict, Any, Optional, List
from hubspot import HubSpot
from hubspot.crm.contacts import SimplePublicObjectInput, PublicObjectSearchRequest
from hubspot.crm.deals import SimplePublicObjectInput as DealSimplePublicObjectInput
from hubspot.crm.companies import SimplePublicObjectInput as CompanySimplePublicObjectInput
from hubspot.crm.timeline import TimelineEvent
from hubspot.auth.oauth import ApiException

from app.core.config import settings

logger = logging.getLogger(__name__)

# Definiciones manuales de clases faltantes si las importaciones no funcionan
class BatchInputSimplePublicObjectBatchInput:
    def __init__(self, inputs: List[Dict]):
        self.inputs = inputs

class BatchInputPublicObjectAssociation:
    def __init__(self, inputs: List[Dict]):
        self.inputs = inputs

def _get_hubspot_client(params: Dict[str, Any]) -> HubSpot:
    token = params.get("hubspot_token_override", settings.HUBSPOT_PRIVATE_APP_TOKEN)
    if not token: raise ValueError("Se requiere el Token de App Privada de HubSpot.")
    return HubSpot(access_token=token)

def _handle_hubspot_api_error(e: ApiException, action_name: str) -> Dict[str, Any]:
    logger.error(f"Error en HubSpot Action '{action_name}': {e.status} - {e.body}", exc_info=True)
    return {"status": "error", "action": action_name, "message": f"Error en API de HubSpot: {e.reason}", "details": e.body, "http_status": e.status}

# --- ACCIONES CRUD ESTÁNDAR ---

def hubspot_get_contacts(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "hubspot_get_contacts"
    try:
        hs_client = _get_hubspot_client(params)
        contacts_page = hs_client.crm.contacts.basic_api.get_page(limit=params.get("limit", 100), after=params.get("after"))
        return {"status": "success", "data": contacts_page.to_dict()}
    except ApiException as e:
        return _handle_hubspot_api_error(e, action_name)

def hubspot_create_contact(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "hubspot_create_contact"
    try:
        hs_client = _get_hubspot_client(params)
        properties = params.get("properties_payload")
        if not properties: raise ValueError("'properties_payload' es requerido.")
        contact_input = SimplePublicObjectInput(properties=properties)
        created_contact = hs_client.crm.contacts.basic_api.create(simple_public_object_input=contact_input)
        return {"status": "success", "data": created_contact.to_dict()}
    except ApiException as e:
        return _handle_hubspot_api_error(e, action_name)

def hubspot_update_contact(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "hubspot_update_contact"
    try:
        hs_client = _get_hubspot_client(params)
        contact_id = params.get("contact_id")
        properties = params.get("properties_payload")
        if not contact_id or not properties: raise ValueError("'contact_id' y 'properties_payload' son requeridos.")
        contact_input = SimplePublicObjectInput(properties=properties)
        updated_contact = hs_client.crm.contacts.basic_api.update(contact_id=contact_id, simple_public_object_input=contact_input)
        return {"status": "success", "data": updated_contact.to_dict()}
    except ApiException as e:
        return _handle_hubspot_api_error(e, action_name)

def hubspot_delete_contact(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "hubspot_delete_contact"
    try:
        hs_client = _get_hubspot_client(params)
        contact_id = params.get("contact_id")
        if not contact_id: raise ValueError("'contact_id' es requerido.")
        hs_client.crm.contacts.basic_api.archive(contact_id=contact_id)
        return {"status": "success", "message": f"Contacto '{contact_id}' eliminado."}
    except ApiException as e:
        return _handle_hubspot_api_error(e, action_name)

def hubspot_get_deals(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "hubspot_get_deals"
    try:
        hs_client = _get_hubspot_client(params)
        deals_page = hs_client.crm.deals.basic_api.get_page(limit=params.get("limit", 100), after=params.get("after"))
        return {"status": "success", "data": deals_page.to_dict()}
    except ApiException as e:
        return _handle_hubspot_api_error(e, action_name)

def hubspot_create_deal(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "hubspot_create_deal"
    try:
        hs_client = _get_hubspot_client(params)
        properties = params.get("properties_payload")
        if not properties: raise ValueError("'properties_payload' es requerido.")
        deal_input = DealSimplePublicObjectInput(properties=properties)
        created_deal = hs_client.crm.deals.basic_api.create(simple_public_object_input=deal_input)
        return {"status": "success", "data": created_deal.to_dict()}
    except ApiException as e:
        return _handle_hubspot_api_error(e, action_name)

def hubspot_update_deal(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "hubspot_update_deal"
    try:
        hs_client = _get_hubspot_client(params)
        deal_id = params.get("deal_id")
        properties = params.get("properties_payload")
        if not deal_id or not properties: raise ValueError("'deal_id' y 'properties_payload' son requeridos.")
        deal_input = DealSimplePublicObjectInput(properties=properties)
        updated_deal = hs_client.crm.deals.basic_api.update(deal_id=deal_id, simple_public_object_input=deal_input)
        return {"status": "success", "data": updated_deal.to_dict()}
    except ApiException as e:
        return _handle_hubspot_api_error(e, action_name)

def hubspot_delete_deal(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "hubspot_delete_deal"
    try:
        hs_client = _get_hubspot_client(params)
        deal_id = params.get("deal_id")
        if not deal_id: raise ValueError("'deal_id' es requerido.")
        hs_client.crm.deals.basic_api.archive(deal_id=deal_id)
        return {"status": "success", "message": f"Negocio '{deal_id}' eliminado."}
    except ApiException as e:
        return _handle_hubspot_api_error(e, action_name)

# --- ACCIONES AVANZADAS Y "RESOLVERS" ---

def hubspot_find_contact_by_email(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "hubspot_find_contact_by_email"
    try:
        hs_client = _get_hubspot_client(params)
        email = params.get("email")
        if not email: raise ValueError("'email' es requerido.")

        filter_group = {
            "filters": [{
                "propertyName": "email",
                "operator": "EQ",
                "value": email
            }]
        }
        search_request = PublicObjectSearchRequest(
            filter_groups=[filter_group],
            properties=["email", "firstname", "lastname", "phone"],
            limit=1
        )
        search_result = hs_client.crm.contacts.search_api.do_search(public_object_search_request=search_request)
        
        if search_result.total == 0:
            return {"status": "error", "message": f"No se encontró un contacto con el email '{email}'.", "http_status": 404}
            
        return {"status": "success", "data": search_result.results[0].to_dict()}
    except ApiException as e:
        return _handle_hubspot_api_error(e, action_name)

def hubspot_update_deal_stage(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "hubspot_update_deal_stage"
    try:
        deal_id = params.get("deal_id")
        new_stage = params.get("new_stage_id")
        if not deal_id or not new_stage:
            raise ValueError("'deal_id' y 'new_stage_id' son requeridos.")
        
        # Esta acción es un caso específico de 'hubspot_update_deal'
        update_params = {
            "deal_id": deal_id,
            "properties_payload": {"dealstage": new_stage}
        }
        return hubspot_update_deal(client, update_params)
    except ApiException as e:
        return _handle_hubspot_api_error(e, action_name)

def hubspot_enroll_contact_in_workflow(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "hubspot_enroll_contact_in_workflow"
    try:
        hs_client = _get_hubspot_client(params)
        workflow_id = params.get("workflow_id")
        contact_id = params.get("contact_id")
        if not workflow_id or not contact_id:
            raise ValueError("'workflow_id' y 'contact_id' son requeridos.")
        
        # Usamos un diccionario en lugar de la clase si sigue dando problemas
        batch_input = {
            "inputs": [{"id": str(contact_id)}]
        }
        
        hs_client.crm.workflows.workflows_api.enroll_contacts(
            workflow_id=str(workflow_id),
            batch_input_simple_public_object_batch_input=batch_input
        )
        return {"status": "success", "message": f"Contacto '{contact_id}' inscrito en el workflow '{workflow_id}'."}
    except ApiException as e:
        return _handle_hubspot_api_error(e, action_name)

def hubspot_get_contacts_from_list(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "hubspot_get_contacts_from_list"
    try:
        hs_client = _get_hubspot_client(params)
        list_id = params.get("list_id")
        if not list_id:
            raise ValueError("'list_id' es requerido.")

        # La API de listas no devuelve los contactos directamente, hay que usar la API de búsqueda
        # con el ID de la lista como filtro.
        filter_group = {
            "filters": [{
                "propertyName": "hs_list_memberships",
                "operator": "EQ",
                "value": list_id
            }]
        }
        search_request = PublicObjectSearchRequest(
            filter_groups=[filter_group],
            properties=["email", "firstname", "lastname"],
            limit=params.get("limit", 100)
        )
        search_result = hs_client.crm.contacts.search_api.do_search(public_object_search_request=search_request)
        
        return {"status": "success", "data": search_result.to_dict()}
    except ApiException as e:
        return _handle_hubspot_api_error(e, action_name)

def hubspot_create_company_and_associate_contact(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "hubspot_create_company_and_associate_contact"
    try:
        hs_client = _get_hubspot_client(params)
        company_properties = params.get("company_properties")
        contact_id = params.get("contact_id")
        if not company_properties or not contact_id:
            raise ValueError("'company_properties' y 'contact_id' son requeridos.")

        # 1. Crear la compañía
        company_input = CompanySimplePublicObjectInput(properties=company_properties)
        created_company = hs_client.crm.companies.basic_api.create(simple_public_object_input=company_input)
        company_id = created_company.id
        
        # 2. Asociar el contacto a la compañía usando un diccionario
        association = {
            "inputs": [{
                "from": {"id": contact_id},
                "to": {"id": company_id},
                "type": "contact_to_company"
            }]
        }
        
        hs_client.crm.associations.batch_api.create(
            from_object_type="contacts",
            to_object_type="companies",
            batch_input_public_object_association=association
        )

        return {"status": "success", "message": f"Compañía creada (ID: {company_id}) y asociada al contacto (ID: {contact_id}).", "data": created_company.to_dict()}
    except ApiException as e:

        return _handle_hubspot_api_error(e, action_name)
# --- NUEVAS FUNCIONES ---

def hubspot_get_contact_by_id(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "hubspot_get_contact_by_id"
    try:
        hs_client = _get_hubspot_client(params)
        contact_id = params.get("contact_id")
        if not contact_id:
            raise ValueError("'contact_id' es requerido.")
        
        properties = params.get("properties", ["email", "firstname", "lastname", "phone"])
        contact = hs_client.crm.contacts.basic_api.get_by_id(
            contact_id=contact_id,
            properties=properties
        )
        return {"status": "success", "data": contact.to_dict()}
    except ApiException as e:
        return _handle_hubspot_api_error(e, action_name)

def hubspot_create_company(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "hubspot_create_company"
    try:
        hs_client = _get_hubspot_client(params)
        properties = params.get("properties_payload")
        if not properties:
            raise ValueError("'properties_payload' es requerido.")
        
        company_input = CompanySimplePublicObjectInput(properties=properties)
        created_company = hs_client.crm.companies.basic_api.create(simple_public_object_input=company_input)
        return {"status": "success", "data": created_company.to_dict()}
    except ApiException as e:
        return _handle_hubspot_api_error(e, action_name)

def hubspot_get_company_by_id(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "hubspot_get_company_by_id"
    try:
        hs_client = _get_hubspot_client(params)
        company_id = params.get("company_id")
        if not company_id:
            raise ValueError("'company_id' es requerido.")
        
        properties = params.get("properties", ["name", "domain", "industry", "website"])
        company = hs_client.crm.companies.basic_api.get_by_id(
            company_id=company_id,
            properties=properties
        )
        return {"status": "success", "data": company.to_dict()}
    except ApiException as e:
        return _handle_hubspot_api_error(e, action_name)

def hubspot_get_deal_by_id(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "hubspot_get_deal_by_id"
    try:
        hs_client = _get_hubspot_client(params)
        deal_id = params.get("deal_id")
        if not deal_id:
            raise ValueError("'deal_id' es requerido.")
        
        properties = params.get("properties", ["dealname", "amount", "dealstage", "closedate"])
        deal = hs_client.crm.deals.basic_api.get_by_id(
            deal_id=deal_id,
            properties=properties
        )
        return {"status": "success", "data": deal.to_dict()}
    except ApiException as e:
        return _handle_hubspot_api_error(e, action_name)

def hubspot_associate_contact_to_deal(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "hubspot_associate_contact_to_deal"
    try:
        hs_client = _get_hubspot_client(params)
        contact_id = params.get("contact_id")
        deal_id = params.get("deal_id")
        if not contact_id or not deal_id:
            raise ValueError("'contact_id' y 'deal_id' son requeridos.")
        
        association_type = params.get("association_type", "contact_to_deal")
        
        # Usar diccionario en lugar de la clase
        association = {
            "inputs": [{
                "from": {"id": contact_id},
                "to": {"id": deal_id},
                "type": association_type
            }]
        }
        
        hs_client.crm.associations.batch_api.create(
            from_object_type="contacts",
            to_object_type="deals",
            batch_input_public_object_association=association
        )
        
        return {
            "status": "success", 
            "message": f"Contacto (ID: {contact_id}) asociado al negocio (ID: {deal_id})."
        }
    except ApiException as e:
        return _handle_hubspot_api_error(e, action_name)

def hubspot_add_note_to_contact(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "hubspot_add_note_to_contact"
    try:
        hs_client = _get_hubspot_client(params)
        contact_id = params.get("contact_id")
        note_body = params.get("note_body")
        if not contact_id or not note_body:
            raise ValueError("'contact_id' y 'note_body' son requeridos.")
        
        # Crear la nota
        note_properties = {
            "hs_note_body": note_body,
            "hs_timestamp": params.get("timestamp", int(time.time() * 1000))  # Milisegundos
        }
        
        note_input = SimplePublicObjectInput(properties=note_properties)
        created_note = hs_client.crm.objects.notes.basic_api.create(simple_public_object_input=note_input)
        note_id = created_note.id
        
        # Asociar la nota al contacto usando un diccionario
        association = {
            "inputs": [{
                "from": {"id": note_id},
                "to": {"id": contact_id},
                "type": "note_to_contact"
            }]
        }
        
        hs_client.crm.associations.batch_api.create(
            from_object_type="notes",
            to_object_type="contacts",
            batch_input_public_object_association=association
        )
        
        return {
            "status": "success", 
            "message": f"Nota creada (ID: {note_id}) y asociada al contacto (ID: {contact_id}).",
            "data": created_note.to_dict()
        }
    except ApiException as e:
        return _handle_hubspot_api_error(e, action_name)

def hubspot_get_timeline_events(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "hubspot_get_timeline_events"
    try:
        hs_client = _get_hubspot_client(params)
        object_id = params.get("object_id")
        object_type = params.get("object_type", "contact")
        event_type = params.get("event_type")
        
        if not object_id:
            raise ValueError("'object_id' es requerido.")
        
        # Construir la URL para la API de timeline events
        url = f"/crm/v3/objects/{object_type}/{object_id}/timeline-events"
        query_params = {}
        
        if event_type:
            query_params["eventType"] = event_type
        
        # Parámetros opcionales
        if "limit" in params:
            query_params["limit"] = params["limit"]
        if "after" in params:
            query_params["after"] = params["after"]
        
        # Realizar la solicitud
        response = hs_client.crm.timeline.timeline_events_api._get(url, params=query_params)
        
        return {"status": "success", "data": response.to_dict()}
    except ApiException as e:
        return _handle_hubspot_api_error(e, action_name)

def hubspot_search_companies_by_domain(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "hubspot_search_companies_by_domain"
    try:
        hs_client = _get_hubspot_client(params)
        domain = params.get("domain")
        if not domain:
            raise ValueError("'domain' es requerido.")
        
        # Crear filtros para la búsqueda
        filter_group = {
            "filters": [{
                "propertyName": "domain",
                "operator": "EQ",
                "value": domain
            }]
        }
        
        properties = params.get("properties", ["name", "domain", "website", "industry"])
        limit = params.get("limit", 100)
        
        search_request = PublicObjectSearchRequest(
            filter_groups=[filter_group],
            properties=properties,
            limit=limit
        )
        
        search_result = hs_client.crm.companies.search_api.do_search(public_object_search_request=search_request)
        
        return {"status": "success", "data": search_result.to_dict()}
    except ApiException as e:
        return _handle_hubspot_api_error(e, action_name)