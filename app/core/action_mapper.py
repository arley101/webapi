import os
import json
import logging
from typing import Dict, Callable, Any, Optional, List
from datetime import datetime
import time

# Configurar logging
logger = logging.getLogger(__name__)

# Timing para diagnosticar startup
_startup_start = time.time()
logger.info(f"🚀 ACTION_MAPPER: Iniciando carga optimizada lazy loading - {datetime.now()}")

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
    Inicialización rápida - ACTION_MAP se llena bajo demanda
    """
    logger.info("🚀 FAST STARTUP: Action Mapper inicializando con lazy loading...")
    
    # ACTION_MAP está vacío al inicio - se llenará cuando se necesite
    # Esto es para máxima velocidad de startup
    
    logger.info("✅ Action Mapper listo - módulos se cargarán bajo demanda")
    logger.info("📊 Lazy loading habilitado para startup optimizado")
    
    return True

# Inicializar al importar el módulo
_init_start = time.time()
initialize_action_mapper()
_init_time = time.time() - _init_start
_total_time = time.time() - _startup_start
logger.info(f"✅ ACTION_MAPPER: Inicialización completada en {_init_time:.3f}s, total {_total_time:.3f}s")

# Export de funciones principales para compatibilidad
def _ensure_action_map_loaded():
    """Asegura que ACTION_MAP esté cargado, lo carga si es necesario"""
    global ACTION_MAP
    if ACTION_MAP is None:
        logger.info("⚡ Cargando ACTION_MAP bajo demanda...")
        ACTION_MAP = {}
        
        # Cargar todos los módulos solo cuando realmente se necesite
        module_names = [
            'azuremgmt_actions', 'bookings_actions', 'calendario_actions', 
            'correo_actions', 'forms_actions', 'github_actions', 'googleads_actions',
            'graph_actions', 'hubspot_actions', 'linkedin_enhanced_actions',
            'metaads_actions', 'notion_actions', 'office_actions', 'onedrive_actions',
            'openai_actions', 'planner_actions', 'power_automate_actions', 
            'powerbi_actions', 'runway_actions', 'sharepoint_actions', 'stream_actions',
            'teams_actions', 'tiktok_enhanced', 'todo_actions', 'userprofile_actions',
            'users_actions', 'vivainsights_actions', 'youtube_channel_actions',
            'gemini_actions', 'x_enhanced', 'webresearch_actions', 'wordpress_enhanced',
            'whatsapp_actions', 'google_services_actions', 'email_optimized_actions'
        ]
        
        for module_name in module_names:
            try:
                _load_action_module(module_name)
            except Exception as e:
                logger.warning(f"No se pudo cargar módulo {module_name}: {e}")
        
        logger.info(f"✅ ACTION_MAP cargado: {len(ACTION_MAP)} acciones disponibles")
    
    return ACTION_MAP

def get_all_actions():
    """Devuelve diccionario completo de acciones con lazy loading"""
    return _ensure_action_map_loaded().copy()

def get_action_count():
    """Devuelve número aproximado de acciones sin cargar módulos"""
    return 418  # Número conocido de acciones

def get_action_names():
    """Devuelve lista de nombres de acciones sin cargar módulos - para compatibilidad"""
    # Lista estática de nombres de acciones para evitar imports pesados
    return [
        'create_booking', 'list_bookings', 'calendar_create_event', 'calendar_list_events',
        'email_send', 'email_list', 'forms_create', 'forms_list', 'github_create_repo',
        'github_list_repos', 'googleads_create_campaign', 'googleads_list_campaigns',
        'graph_get_user', 'graph_list_users', 'hubspot_create_contact', 'hubspot_list_contacts',
        'linkedin_create_post', 'linkedin_list_posts', 'meta_create_ad', 'meta_list_ads',
        'notion_create_page', 'notion_list_pages', 'office_create_document', 'office_list_documents',
        'onedrive_upload_file', 'onedrive_list_files', 'openai_chat_completion', 'openai_generate_image',
        'planner_create_task', 'planner_list_tasks', 'powerautomate_create_flow', 'powerautomate_list_flows',
        'powerbi_create_report', 'powerbi_list_reports', 'sharepoint_create_list', 'sharepoint_list_sites',
        'stream_upload_video', 'stream_list_videos', 'teams_send_message', 'teams_list_chats',
        'tiktok_create_ad', 'tiktok_list_ads', 'todo_create_task', 'todo_list_tasks',
        'user_get_profile', 'user_update_profile', 'vivainsights_get_metrics', 'vivainsights_list_reports',
        'youtube_upload_video', 'youtube_list_videos', 'gemini_generate_content', 'gemini_chat',
        'x_create_tweet', 'x_list_tweets', 'webresearch_search', 'webresearch_analyze',
        'wordpress_create_post', 'wordpress_list_posts', 'whatsapp_send_message', 'whatsapp_list_chats'
        # ... más acciones (las principales para mostrar en interfaces)
    ]

# ACTION_MAP que se llena bajo demanda
ACTION_MAP = None

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