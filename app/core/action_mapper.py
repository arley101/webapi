import os
import sys

# AGREGAR ESTA LÍNEA AL INICIO
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import json
import logging
from typing import Dict, Callable, Any, Optional, List
from datetime import datetime

# Configurar logging
logger = logging.getLogger(__name__)

# ===============================================
# LAZY LOADING OPTIMIZATION
# ===============================================
# Solo importamos auth_manager que es esencial
from app.core.auth_manager import get_auth_client

# Diccionario para almacenar módulos cargados dinámicamente
_loaded_modules = {}

def _load_action_module(module_name: str):
    """Carga un módulo de acciones dinámicamente solo cuando se necesita"""
    if module_name in _loaded_modules:
        return _loaded_modules[module_name]
    
    try:
        if module_name == 'azuremgmt_actions':
            from app.actions import azuremgmt_actions
            _loaded_modules[module_name] = azuremgmt_actions
        elif module_name == 'bookings_actions':
            from app.actions import bookings_actions
            _loaded_modules[module_name] = bookings_actions
        elif module_name == 'calendario_actions':
            from app.actions import calendario_actions
            _loaded_modules[module_name] = calendario_actions
        elif module_name == 'correo_actions':
            from app.actions import correo_actions
            _loaded_modules[module_name] = correo_actions
        elif module_name == 'forms_actions':
            from app.actions import forms_actions
            _loaded_modules[module_name] = forms_actions
        elif module_name == 'github_actions':
            from app.actions import github_actions
            _loaded_modules[module_name] = github_actions
        elif module_name == 'googleads_actions':
            from app.actions import googleads_actions
            _loaded_modules[module_name] = googleads_actions
        elif module_name == 'graph_actions':
            from app.actions import graph_actions
            _loaded_modules[module_name] = graph_actions
        elif module_name == 'hubspot_actions':
            from app.actions import hubspot_actions
            _loaded_modules[module_name] = hubspot_actions
        elif module_name == 'linkedin_enhanced_actions':
            from app.actions import linkedin_enhanced_actions
            _loaded_modules[module_name] = linkedin_enhanced_actions
        elif module_name == 'metaads_actions':
            from app.actions import metaads_actions
            _loaded_modules[module_name] = metaads_actions
        elif module_name == 'notion_actions':
            from app.actions import notion_actions
            _loaded_modules[module_name] = notion_actions
        elif module_name == 'office_actions':
            from app.actions import office_actions
            _loaded_modules[module_name] = office_actions
        elif module_name == 'onedrive_actions':
            from app.actions import onedrive_actions
            _loaded_modules[module_name] = onedrive_actions
        elif module_name == 'openai_actions':
            from app.actions import openai_actions
            _loaded_modules[module_name] = openai_actions
        elif module_name == 'planner_actions':
            from app.actions import planner_actions
            _loaded_modules[module_name] = planner_actions
        elif module_name == 'power_automate_actions':
            from app.actions import power_automate_actions
            _loaded_modules[module_name] = power_automate_actions
        elif module_name == 'powerbi_actions':
            from app.actions import powerbi_actions
            _loaded_modules[module_name] = powerbi_actions
        elif module_name == 'runway_actions':
            from app.actions import runway_actions
            _loaded_modules[module_name] = runway_actions
        elif module_name == 'sharepoint_actions':
            from app.actions import sharepoint_actions
            _loaded_modules[module_name] = sharepoint_actions
        elif module_name == 'stream_actions':
            from app.actions import stream_actions
            _loaded_modules[module_name] = stream_actions
        elif module_name == 'teams_actions':
            from app.actions import teams_actions
            _loaded_modules[module_name] = teams_actions
        elif module_name == 'tiktok_enhanced':
            from app.actions import tiktok_enhanced
            _loaded_modules[module_name] = tiktok_enhanced
        elif module_name == 'todo_actions':
            from app.actions import todo_actions
            _loaded_modules[module_name] = todo_actions
        elif module_name == 'userprofile_actions':
            from app.actions import userprofile_actions
            _loaded_modules[module_name] = userprofile_actions
        elif module_name == 'users_actions':
            from app.actions import users_actions
            _loaded_modules[module_name] = users_actions
        elif module_name == 'vivainsights_actions':
            from app.actions import vivainsights_actions
            _loaded_modules[module_name] = vivainsights_actions
        elif module_name == 'youtube_channel_actions':
            from app.actions import youtube_channel_actions
            _loaded_modules[module_name] = youtube_channel_actions
        elif module_name == 'gemini_actions':
            from app.actions import gemini_actions
            _loaded_modules[module_name] = gemini_actions
        elif module_name == 'x_enhanced':
            from app.actions import x_enhanced
            _loaded_modules[module_name] = x_enhanced
        elif module_name == 'webresearch_actions':
            from app.actions import webresearch_actions
            _loaded_modules[module_name] = webresearch_actions
        elif module_name == 'wordpress_enhanced':
            from app.actions import wordpress_enhanced
            _loaded_modules[module_name] = wordpress_enhanced
        elif module_name == 'resolver_actions':
            from app.actions import resolver_actions
            _loaded_modules[module_name] = resolver_actions
        elif module_name == 'intelligent_assistant_actions':
            from app.actions import intelligent_assistant_actions
            _loaded_modules[module_name] = intelligent_assistant_actions
        elif module_name == 'whatsapp_actions':
            from app.actions import whatsapp_actions
            _loaded_modules[module_name] = whatsapp_actions
        elif module_name == 'google_services_actions':
            from app.actions import google_services_actions
            _loaded_modules[module_name] = google_services_actions
        elif module_name == 'email_optimized_actions':
            from app.actions import email_optimized_actions
            _loaded_modules[module_name] = email_optimized_actions
        elif module_name == 'google_marketing_enhanced':
            try:
                from app.actions import google_marketing_enhanced
                _loaded_modules[module_name] = google_marketing_enhanced
            except ImportError:
                _loaded_modules[module_name] = None
        else:
            logger.warning(f"Módulo desconocido: {module_name}")
            _loaded_modules[module_name] = None
            
        return _loaded_modules[module_name]
    except ImportError as e:
        logger.error(f"Error al cargar módulo {module_name}: {e}")
        _loaded_modules[module_name] = None
        return None

# ===============================================
# CONFIGURACIÓN BÁSICA PARA STARTUP RÁPIDO
# ===============================================

# Solo cargar configuración básica al startup
ACTION_MAP = {}  # Se llenará dinámicamente
ALL_ACTIONS = {}  # Se llenará dinámicamente

def get_action_function(action_name: str) -> Optional[Callable]:
    """
    Obtiene una función de acción específica, cargando el módulo solo si es necesario
    """
    # Mapeo de acciones a módulos (lazy loading)
    action_to_module = {
        # Azure Management
        'create_resource_group': 'azuremgmt_actions',
        'list_resource_groups': 'azuremgmt_actions',
        'delete_resource_group': 'azuremgmt_actions',
        'create_storage_account': 'azuremgmt_actions',
        'list_storage_accounts': 'azuremgmt_actions',
        'delete_storage_account': 'azuremgmt_actions',
        'create_function_app': 'azuremgmt_actions',
        'list_function_apps': 'azuremgmt_actions',
        'delete_function_app': 'azuremgmt_actions',
        'get_resource_usage': 'azuremgmt_actions',
        
        # Bookings
        'get_bookings': 'bookings_actions',
        'create_booking': 'bookings_actions',
        'update_booking': 'bookings_actions',
        'delete_booking': 'bookings_actions',
        'get_booking_details': 'bookings_actions',
        'get_business_info': 'bookings_actions',
        'get_services': 'bookings_actions',
        'get_staff_members': 'bookings_actions',
        
        # Calendar
        'get_calendar_events': 'calendario_actions',
        'create_calendar_event': 'calendario_actions',
        'update_calendar_event': 'calendario_actions',
        'delete_calendar_event': 'calendario_actions',
        'get_calendar_details': 'calendario_actions',
        'create_calendar': 'calendario_actions',
        'list_calendars': 'calendario_actions',
        'get_calendar_permissions': 'calendario_actions',
        'set_calendar_permissions': 'calendario_actions',
        'get_calendar_free_busy': 'calendario_actions',
        'search_calendar_events': 'calendario_actions',
        
        # Email
        'send_email': 'correo_actions',
        'get_emails': 'correo_actions',
        'reply_to_email': 'correo_actions',
        'forward_email': 'correo_actions',
        'delete_email': 'correo_actions',
        'create_email_folder': 'correo_actions',
        'move_email_to_folder': 'correo_actions',
        'search_emails': 'correo_actions',
        'get_email_attachments': 'correo_actions',
        'download_email_attachment': 'correo_actions',
        'mark_email_as_read': 'correo_actions',
        'mark_email_as_unread': 'correo_actions',
        'create_email_rule': 'correo_actions',
        'get_mailbox_info': 'correo_actions',
        
        # Lazy loading para el resto...
        # (Se pueden agregar más según se necesiten)
    }
    
    module_name = action_to_module.get(action_name)
    if not module_name:
        # Si no está en el mapeo, intentar buscar en todos los módulos cargados
        for loaded_module_name, loaded_module in _loaded_modules.items():
            if loaded_module and hasattr(loaded_module, action_name):
                return getattr(loaded_module, action_name)
        return None
    
    module = _load_action_module(module_name)
    if module and hasattr(module, action_name):
        return getattr(module, action_name)
    
    return None

def initialize_action_mapper():
    """
    Inicialización básica y rápida del action mapper
    Solo carga lo esencial para que la app inicie rápido
    """
    logger.info("🚀 FAST STARTUP: Action Mapper inicializando con lazy loading...")
    
    # Solo log básico de inicio
    logger.info("✅ Action Mapper listo - módulos se cargarán bajo demanda")
    logger.info("📊 Lazy loading habilitado para startup optimizado")
    
    return True

# Inicializar al importar el módulo
initialize_action_mapper()

# Export de funciones principales para compatibilidad
def get_all_actions():
    """Devuelve lista básica de acciones disponibles"""
    return {
        'status': 'lazy_loading_enabled',
        'message': 'Actions loaded on demand for better performance'
    }

def get_action_categories():
    """Devuelve categorías básicas"""
    return [
        'Azure Management', 'Bookings', 'Calendar', 'Email', 'Forms',
        'GitHub', 'Google Ads', 'Microsoft Graph', 'HubSpot CRM',
        'LinkedIn Ads', 'Meta Ads', 'Notion', 'Office', 'OneDrive',
        'Azure OpenAI', 'Microsoft Planner', 'Power Automate', 'Power BI',
        'Resource Resolver', 'Runway AI', 'SharePoint', 'Microsoft Stream',
        'Microsoft Teams', 'TikTok Ads', 'Microsoft To Do', 'User Profile',
        'Users & Directory', 'Viva Insights', 'YouTube Channel', 'Gemini AI',
        'X (Twitter) Ads', 'Web Research', 'WordPress/WooCommerce',
        'WhatsApp', 'Google Services', 'Email Optimized', 'Workflows', 'Memory System'
    ]