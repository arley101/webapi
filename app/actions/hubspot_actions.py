# app/actions/hubspot_actions.py
import logging
from typing import Dict, Any, Optional
from hubspot import HubSpot
from hubspot.crm.contacts import SimplePublicObjectInput
from hubspot.crm.deals import SimplePublicObjectInput as DealSimplePublicObjectInput
from hubspot.core.exceptions import ApiException

from app.core.config import settings

logger = logging.getLogger(__name__)

def _get_hubspot_client(params: Dict[str, Any]) -> HubSpot:
    token = params.get("hubspot_token_override", settings.HUBSPOT_PRIVATE_APP_TOKEN)
    if not token: raise ValueError("Se requiere el Token de App Privada de HubSpot.")
    return HubSpot(access_token=token)

def _handle_hubspot_api_error(e: ApiException, action_name: str) -> Dict[str, Any]:
    logger.error(f"Error en HubSpot Action '{action_name}': {e.status} - {e.body}", exc_info=True)
    return {"status": "error", "action": action_name, "message": f"Error en API de HubSpot: {e.reason}", "details": e.body, "http_status": e.status}

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