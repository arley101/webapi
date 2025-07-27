import logging
from typing import Dict, Any, Callable

# Configurar logging
logger = logging.getLogger(__name__)

# Importar todos los módulos de acciones
from app.actions import (
    azuremgmt_actions, bookings_actions, calendario_actions, correo_actions,
    forms_actions, github_actions, googleads_actions, graph_actions,
    hubspot_actions, linkedin_ads_actions, metaads_actions, notion_actions,
    office_actions, onedrive_actions, openai_actions, planner_actions,
    power_automate_actions, powerbi_actions, sharepoint_actions,
    stream_actions, teams_actions, tiktok_ads_actions, todo_actions,
    userprofile_actions, users_actions, vivainsights_actions,
    youtube_channel_actions, gemini_actions, x_ads_actions, webresearch_actions, 
    wordpress_actions, resolver_actions
)

# ============================================================================
# CATEGORÍAS DE ACCIONES
# ============================================================================

# Categorías principales
AZURE_MGMT_CATEGORY = "Azure Management"
BOOKINGS_CATEGORY = "Bookings"
CALENDAR_CATEGORY = "Calendar"
EMAIL_CATEGORY = "Email"
FORMS_CATEGORY = "Forms"
GEMINI_CATEGORY = "Gemini AI"
GITHUB_CATEGORY = "GitHub"
GOOGLEADS_CATEGORY = "Google Ads"
GRAPH_CATEGORY = "Microsoft Graph"
HUBSPOT_CATEGORY = "HubSpot CRM"
LINKEDIN_CATEGORY = "LinkedIn Ads"
META_CATEGORY = "Meta Ads"
NOTION_CATEGORY = "Notion"
OFFICE_CATEGORY = "Office"
ONEDRIVE_CATEGORY = "OneDrive"
OPENAI_CATEGORY = "Azure OpenAI"
PLANNER_CATEGORY = "Microsoft Planner"
POWER_AUTOMATE_CATEGORY = "Power Automate"
POWERBI_CATEGORY = "Power BI"
RESOLVER_CATEGORY = "Resource Resolver"
SHAREPOINT_CATEGORY = "SharePoint"
STREAM_CATEGORY = "Microsoft Stream"
TEAMS_CATEGORY = "Microsoft Teams"
TIKTOK_CATEGORY = "TikTok Ads"
TODO_CATEGORY = "Microsoft To Do"
USER_PROFILE_CATEGORY = "User Profile"
USERS_CATEGORY = "Users & Directory"
VIVA_CATEGORY = "Viva Insights"
YOUTUBE_CATEGORY = "YouTube Channel"
X_ADS_CATEGORY = "X (Twitter) Ads"
WEBRESEARCH_CATEGORY = "Web Research"
WORDPRESS_CATEGORY = "WordPress"
WOOCOMMERCE_CATEGORY = "WooCommerce"

# ============================================================================
# MAPEO DE ACCIONES - AZURE MANAGEMENT (10 acciones)
# ============================================================================

AZURE_MGMT_ACTIONS: Dict[str, Callable] = {
    "azure_list_resource_groups": azuremgmt_actions.list_resource_groups,
    "azure_list_resources_in_rg": azuremgmt_actions.list_resources_in_rg,
    "azure_get_resource": azuremgmt_actions.get_resource,
    "azure_create_deployment": azuremgmt_actions.create_deployment,
    "azure_list_functions": azuremgmt_actions.list_functions,
    "azure_get_function_status": azuremgmt_actions.get_function_status,
    "azure_restart_function_app": azuremgmt_actions.restart_function_app,
    "azure_list_logic_apps": azuremgmt_actions.list_logic_apps,
    "azure_trigger_logic_app": azuremgmt_actions.trigger_logic_app,
    "azure_get_logic_app_run_history": azuremgmt_actions.get_logic_app_run_history,
}

# ============================================================================
# MAPEO DE ACCIONES - BOOKINGS (8 acciones)
# ============================================================================

BOOKINGS_ACTIONS: Dict[str, Callable] = {
    "bookings_list_businesses": bookings_actions.list_businesses,
    "bookings_get_business": bookings_actions.get_business,
    "bookings_list_services": bookings_actions.list_services,
    "bookings_list_staff": bookings_actions.list_staff,
    "bookings_create_appointment": bookings_actions.create_appointment,
    "bookings_get_appointment": bookings_actions.get_appointment,
    "bookings_cancel_appointment": bookings_actions.cancel_appointment,
    "bookings_list_appointments": bookings_actions.list_appointments,
}

# ============================================================================
# MAPEO DE ACCIONES - CALENDAR (7 acciones)
# ============================================================================

CALENDAR_ACTIONS: Dict[str, Callable] = {
    "calendar_list_events": calendario_actions.calendar_list_events,
    "calendar_create_event": calendario_actions.calendar_create_event,
    "calendar_get_event": calendario_actions.get_event,
    "calendar_update_event": calendario_actions.update_event,
    "calendar_delete_event": calendario_actions.delete_event,
    "calendar_find_meeting_times": calendario_actions.find_meeting_times,
    "calendar_get_schedule": calendario_actions.get_schedule,
}

# ============================================================================
# MAPEO DE ACCIONES - EMAIL (10 acciones)
# ============================================================================

EMAIL_ACTIONS: Dict[str, Callable] = {
    "email_list_messages": correo_actions.list_messages,
    "email_get_message": correo_actions.get_message,
    "email_send_message": correo_actions.send_message,
    "email_reply_message": correo_actions.reply_message,
    "email_forward_message": correo_actions.forward_message,
    "email_delete_message": correo_actions.delete_message,
    "email_move_message": correo_actions.move_message,
    "email_list_folders": correo_actions.list_folders,
    "email_create_folder": correo_actions.create_folder,
    "email_search_messages": correo_actions.search_messages,
}

# ============================================================================
# MAPEO DE ACCIONES - FORMS (3 acciones)
# ============================================================================

FORMS_ACTIONS: Dict[str, Callable] = {
    "forms_list_forms": forms_actions.list_forms,
    "forms_get_form": forms_actions.get_form,
    "forms_get_form_responses": forms_actions.get_form_responses,
}

# ============================================================================
# MAPEO DE ACCIONES - GEMINI AI (5 acciones)
# ============================================================================

GEMINI_ACTIONS: Dict[str, Callable] = {
    "analyze_conversation_context": gemini_actions.analyze_conversation_context,
    "generate_response_suggestions": gemini_actions.generate_response_suggestions,
    "extract_key_information": gemini_actions.extract_key_information,
    "summarize_conversation": gemini_actions.summarize_conversation,
    "classify_message_intent": gemini_actions.classify_message_intent,
    "gemini_suggest_action": gemini_actions.generate_response_suggestions,  # requerido por validador
}
# ============================================================================
# MAPEO DE ACCIONES - GITHUB (3 acciones)
# ============================================================================

GITHUB_ACTIONS: Dict[str, Callable] = {
    "github_list_repos": github_actions.github_list_repos,
    "github_create_issue": github_actions.github_create_issue,
    "github_get_repo_details": github_actions.github_get_repo_details,
}

# ============================================================================
# MAPEO DE ACCIONES - GOOGLE ADS (19 acciones)
# ============================================================================

GOOGLEADS_ACTIONS: Dict[str, Callable] = {
    "googleads_get_campaigns": googleads_actions.googleads_get_campaigns,
    "googleads_create_campaign": googleads_actions.googleads_create_campaign,
    "googleads_get_ad_groups": googleads_actions.googleads_get_ad_groups,
    "googleads_get_campaign": googleads_actions.googleads_get_campaign,
    "googleads_update_campaign_status": googleads_actions.googleads_update_campaign_status,
    "googleads_create_performance_max_campaign": googleads_actions.googleads_create_performance_max_campaign,
    "googleads_create_remarketing_list": googleads_actions.googleads_create_remarketing_list,
    "googleads_get_campaign_performance": googleads_actions.googleads_get_campaign_performance,
    "googleads_list_accessible_customers": googleads_actions.googleads_list_accessible_customers,
    "googleads_get_campaign_by_name": googleads_actions.googleads_get_campaign_by_name,
    "googleads_upload_click_conversion": googleads_actions.googleads_upload_click_conversion,
    "googleads_upload_image_asset": googleads_actions.googleads_upload_image_asset,
    "googleads_get_keyword_performance_report": googleads_actions.googleads_get_keyword_performance_report,
    "googleads_get_campaign_performance_by_device": googleads_actions.googleads_get_campaign_performance_by_device,
    "googleads_add_keywords_to_ad_group": googleads_actions.googleads_add_keywords_to_ad_group,
    "googleads_apply_audience_to_ad_group": googleads_actions.googleads_apply_audience_to_ad_group,
    "googleads_create_responsive_search_ad": googleads_actions.googleads_create_responsive_search_ad,
    "googleads_get_ad_performance": googleads_actions.googleads_get_ad_performance,
    "googleads_upload_offline_conversion": googleads_actions.googleads_upload_offline_conversion,
}

# ============================================================================
# MAPEO DE ACCIONES - MICROSOFT GRAPH (2 acciones)
# ============================================================================

GRAPH_ACTIONS: Dict[str, Callable] = {
    "graph_generic_get": graph_actions.generic_get,
    "graph_generic_post": graph_actions.generic_post,
}

# ============================================================================
# MAPEO DE ACCIONES - HUBSPOT CRM (18 acciones)
# ============================================================================

HUBSPOT_ACTIONS: Dict[str, Callable] = {
    "hubspot_get_contacts": hubspot_actions.hubspot_get_contacts,
    "hubspot_create_contact": hubspot_actions.hubspot_create_contact,
    "hubspot_update_contact": hubspot_actions.hubspot_update_contact,
    "hubspot_delete_contact": hubspot_actions.hubspot_delete_contact,
    "hubspot_get_deals": hubspot_actions.hubspot_get_deals,
    "hubspot_create_deal": hubspot_actions.hubspot_create_deal,
    "hubspot_update_deal": hubspot_actions.hubspot_update_deal,
    "hubspot_delete_deal": hubspot_actions.hubspot_delete_deal,
    "hubspot_find_contact_by_email": hubspot_actions.hubspot_find_contact_by_email,
    "hubspot_update_deal_stage": hubspot_actions.hubspot_update_deal_stage,
    "hubspot_enroll_contact_in_workflow": hubspot_actions.hubspot_enroll_contact_in_workflow,
    "hubspot_get_contacts_from_list": hubspot_actions.hubspot_get_contacts_from_list,
    "hubspot_create_company_and_associate_contact": hubspot_actions.hubspot_create_company_and_associate_contact,
    "hubspot_get_contact_by_id": hubspot_actions.hubspot_get_contact_by_id,
    "hubspot_create_company": hubspot_actions.hubspot_create_company,
    "hubspot_get_company_by_id": hubspot_actions.hubspot_get_company_by_id,
    "hubspot_get_deal_by_id": hubspot_actions.hubspot_get_deal_by_id,
    "hubspot_associate_contact_to_deal": hubspot_actions.hubspot_associate_contact_to_deal,
    "hubspot_add_note_to_contact": hubspot_actions.hubspot_add_note_to_contact,
    "hubspot_get_timeline_events": hubspot_actions.hubspot_get_timeline_events,
    "hubspot_search_companies_by_domain": hubspot_actions.hubspot_search_companies_by_domain,
}

# ============================================================================
# MAPEO DE ACCIONES - LINKEDIN ADS (15 acciones)
# ============================================================================

LINKEDIN_ADS_ACTIONS: Dict[str, Callable] = {
    "linkedin_get_ad_accounts": linkedin_ads_actions.linkedin_get_ad_accounts,
    "linkedin_list_campaigns": linkedin_ads_actions.linkedin_list_campaigns,
    "linkedin_get_basic_report": linkedin_ads_actions.linkedin_get_basic_report,
    "linkedin_create_campaign_group": linkedin_ads_actions.linkedin_create_campaign_group,
    "linkedin_update_campaign_group_status": linkedin_ads_actions.linkedin_update_campaign_group_status,
    "linkedin_get_campaign_analytics_by_day": linkedin_ads_actions.linkedin_get_campaign_analytics_by_day,
    "linkedin_get_account_analytics_by_company": linkedin_ads_actions.linkedin_get_account_analytics_by_company,
    "linkedin_create_campaign": linkedin_ads_actions.linkedin_create_campaign,
    "linkedin_update_campaign": linkedin_ads_actions.linkedin_update_campaign,
    "linkedin_delete_campaign": linkedin_ads_actions.linkedin_delete_campaign,
    "linkedin_create_ad": linkedin_ads_actions.linkedin_create_ad,
    "linkedin_update_ad": linkedin_ads_actions.linkedin_update_ad,
    "linkedin_delete_ad": linkedin_ads_actions.linkedin_delete_ad,
    "linkedin_get_creative_analytics": linkedin_ads_actions.linkedin_get_creative_analytics,
    "linkedin_get_conversion_report": linkedin_ads_actions.linkedin_get_conversion_report,
    "linkedin_get_budget_usage": linkedin_ads_actions.linkedin_get_budget_usage,
    "linkedin_get_audience_insights": linkedin_ads_actions.linkedin_get_audience_insights,
}

# ============================================================================
# MAPEO DE ACCIONES - META ADS (25 acciones)
# ============================================================================

METAADS_ACTIONS: Dict[str, Callable] = {
    "metaads_get_business_details": metaads_actions.metaads_get_business_details,
    "metaads_list_owned_pages": metaads_actions.metaads_list_owned_pages,
    "metaads_get_page_engagement": metaads_actions.metaads_get_page_engagement,
    "metaads_list_campaigns": metaads_actions.metaads_list_campaigns,
    "metaads_create_campaign": metaads_actions.metaads_create_campaign,
    "metaads_update_campaign": metaads_actions.metaads_update_campaign,
    "metaads_delete_campaign": metaads_actions.metaads_delete_campaign,
    "metaads_get_insights": metaads_actions.get_insights,
    "metaads_get_campaign_details": metaads_actions.metaads_get_campaign_details,
    "metaads_create_ad_set": metaads_actions.metaads_create_ad_set,
    "metaads_get_ad_set_details": metaads_actions.metaads_get_ad_set_details,
    "metaads_get_account_insights": metaads_actions.metaads_get_account_insights,
    "metaads_create_ad": metaads_actions.metaads_create_ad,
    "metaads_get_ad_preview": metaads_actions.metaads_get_ad_preview,
    "metaads_update_ad": metaads_actions.metaads_update_ad,
    "metaads_delete_ad": metaads_actions.metaads_delete_ad,
    "metaads_update_ad_set": metaads_actions.metaads_update_ad_set,
    "metaads_delete_ad_set": metaads_actions.metaads_delete_ad_set,
    "metaads_update_page_settings": metaads_actions.metaads_update_page_settings,
    "metaads_create_custom_audience": metaads_actions.metaads_create_custom_audience,
    "metaads_list_custom_audiences": metaads_actions.metaads_list_custom_audiences,
    "metaads_create_ad_creative": metaads_actions.metaads_create_ad_creative,
    "metaads_get_ad_details": metaads_actions.metaads_get_ad_details,
    "metaads_get_ad_set_insights": metaads_actions.metaads_get_ad_set_insights,
    "metaads_get_campaign_insights": metaads_actions.metaads_get_campaign_insights,
    "metaads_pause_campaign": metaads_actions.metaads_pause_campaign,
    "metaads_pause_ad": metaads_actions.metaads_pause_ad,
    "metaads_pause_ad_set": metaads_actions.metaads_pause_ad_set,
    "metaads_get_pixel_events": metaads_actions.metaads_get_pixel_events,
}

# ============================================================================
# MAPEO DE ACCIONES - NOTION (16 acciones)
# ============================================================================

NOTION_ACTIONS: Dict[str, Callable] = {
    "notion_search_general": notion_actions.notion_search_general,
    "notion_get_database": notion_actions.notion_get_database,
    "notion_query_database": notion_actions.notion_query_database,
    "notion_retrieve_page": notion_actions.notion_retrieve_page,
    "notion_create_page": notion_actions.notion_create_page,
    "notion_update_page": notion_actions.notion_update_page,
    "notion_delete_block": notion_actions.notion_delete_block,
    "notion_find_database_by_name": notion_actions.notion_find_database_by_name,
    "notion_create_page_in_database": notion_actions.notion_create_page_in_database,
    "notion_append_text_block_to_page": notion_actions.notion_append_text_block_to_page,
    "notion_get_page_content": notion_actions.notion_get_page_content,
    "notion_update_block": notion_actions.notion_update_block,
    "notion_get_block": notion_actions.notion_get_block,
    "notion_create_database": notion_actions.notion_create_database,
    "notion_add_users_to_page": notion_actions.notion_add_users_to_page,
    "notion_archive_page": notion_actions.notion_archive_page,
}

# ============================================================================
# MAPEO DE ACCIONES - OFFICE (8 acciones)
# ============================================================================

OFFICE_ACTIONS: Dict[str, Callable] = {
    "office_crear_documento_word": office_actions.crear_documento_word,
    "office_reemplazar_contenido_word": office_actions.reemplazar_contenido_word,
    "office_obtener_documento_word_binario": office_actions.obtener_documento_word_binario,
    "office_crear_libro_excel": office_actions.crear_libro_excel,
    "office_leer_celda_excel": office_actions.leer_celda_excel,
    "office_escribir_celda_excel": office_actions.escribir_celda_excel,
    "office_crear_tabla_excel": office_actions.crear_tabla_excel,
    "office_agregar_filas_tabla_excel": office_actions.agregar_filas_tabla_excel,
}

# ============================================================================
# MAPEO DE ACCIONES - ONEDRIVE (10 acciones)
# ============================================================================

ONEDRIVE_ACTIONS: Dict[str, Callable] = {
    "onedrive_list_items": onedrive_actions.list_items,
    "onedrive_get_item": onedrive_actions.get_item,
    "onedrive_upload_file": onedrive_actions.upload_file,
    "onedrive_download_file": onedrive_actions.download_file,
    "onedrive_delete_item": onedrive_actions.delete_item,
    "onedrive_create_folder": onedrive_actions.create_folder,
    "onedrive_move_item": onedrive_actions.move_item,
    "onedrive_copy_item": onedrive_actions.copy_item,
    "onedrive_update_item_metadata": onedrive_actions.update_item_metadata,
    "onedrive_search_items": onedrive_actions.search_items,
    "onedrive_get_sharing_link": onedrive_actions.get_sharing_link,
}

# ============================================================================
# MAPEO DE ACCIONES - AZURE OPENAI (4 acciones)
# ============================================================================

OPENAI_ACTIONS: Dict[str, Callable] = {
    "openai_chat_completion": openai_actions.chat_completion,
    "openai_get_embedding": openai_actions.get_embedding,
    "openai_completion": openai_actions.completion,
    "openai_list_models": openai_actions.list_models,
}

# ============================================================================
# MAPEO DE ACCIONES - PLANNER (8 acciones)
# ============================================================================

PLANNER_ACTIONS: Dict[str, Callable] = {
    "planner_list_plans": planner_actions.list_plans,
    "planner_get_plan": planner_actions.get_plan,
    "planner_list_tasks": planner_actions.list_tasks,
    "planner_create_task": planner_actions.create_task,
    "planner_get_task": planner_actions.get_task,
    "planner_update_task": planner_actions.update_task,
    "planner_delete_task": planner_actions.delete_task,
    "planner_list_buckets": planner_actions.list_buckets,
    "planner_create_bucket": planner_actions.create_bucket,
    "planner_get_plan_by_name": planner_actions.planner_get_plan_by_name,
}

# ============================================================================
# MAPEO DE ACCIONES - POWER AUTOMATE (7 acciones)
# ============================================================================

POWER_AUTOMATE_ACTIONS: Dict[str, Callable] = {
    "pa_list_flows": power_automate_actions.pa_list_flows,
    "pa_get_flow": power_automate_actions.pa_get_flow,
    "pa_create_or_update_flow": power_automate_actions.pa_create_or_update_flow,
    "pa_delete_flow": power_automate_actions.pa_delete_flow,
    "pa_run_flow_trigger": power_automate_actions.pa_run_flow_trigger,
    "pa_get_flow_run_history": power_automate_actions.pa_get_flow_run_history,
    "pa_get_flow_run_details": power_automate_actions.pa_get_flow_run_details,
}

# ============================================================================
# MAPEO DE ACCIONES - POWER BI (5 acciones)
# ============================================================================

POWERBI_ACTIONS: Dict[str, Callable] = {
    "powerbi_list_reports": powerbi_actions.list_reports,
    "powerbi_export_report": powerbi_actions.export_report,
    "powerbi_list_dashboards": powerbi_actions.list_dashboards,
    "powerbi_list_datasets": powerbi_actions.list_datasets,
    "powerbi_refresh_dataset": powerbi_actions.refresh_dataset,
}

# ============================================================================
# MAPEO DE ACCIONES - RESOLVER INTELIGENTE (10 acciones)
# ============================================================================

RESOLVER_ACTIONS: Dict[str, Callable] = {
    "resolve_dynamic_query": resolver_actions.resolve_dynamic_query,
    "resolve_contextual_action": resolver_actions.resolve_contextual_action,
    "get_resolution_analytics": resolver_actions.get_resolution_analytics,
    "clear_resolution_cache": resolver_actions.clear_resolution_cache,
    "resolve_smart_workflow": resolver_actions.resolve_smart_workflow,
    # Agregar las funciones adicionales del archivo
    "resolve_resource": resolver_actions.resolve_resource,
    "list_available_resources": resolver_actions.list_available_resources,
    "validate_resource_id": resolver_actions.validate_resource_id,
    "get_resource_config": resolver_actions.get_resource_config,
    "search_resources": resolver_actions.search_resources,
}

# ============================================================================
# MAPEO DE ACCIONES - SHAREPOINT (29 acciones + 6 de memoria = 35 acciones totales)
# ============================================================================

SHAREPOINT_ACTIONS: Dict[str, Callable] = {
    # Gestión de Sitios (3 acciones)
    "sp_get_site_info": sharepoint_actions.get_site_info,
    "sp_search_sites": sharepoint_actions.search_sites,
    "sp_list_document_libraries": sharepoint_actions.list_document_libraries,
    
    # Gestión de Listas (8 acciones)
    "sp_create_list": sharepoint_actions.create_list,
    "sp_list_lists": sharepoint_actions.list_lists,
    "sp_get_list": sharepoint_actions.get_list,
    "sp_update_list": sharepoint_actions.update_list,
    "sp_delete_list": sharepoint_actions.delete_list,
    "sp_add_list_item": sharepoint_actions.add_list_item,
    "sp_list_list_items": sharepoint_actions.list_list_items,
    "sp_get_list_item": sharepoint_actions.get_list_item,
    
    # Gestión de Items de Lista (4 acciones)
    "sp_update_list_item": sharepoint_actions.update_list_item,
    "sp_delete_list_item": sharepoint_actions.delete_list_item,
    "sp_search_list_items": sharepoint_actions.search_list_items,
    "sp_export_list_to_format": sharepoint_actions.sp_export_list_to_format,
    
    # Gestión de Documentos (7 acciones)
    "sp_list_folder_contents": sharepoint_actions.list_folder_contents,
    "sp_get_file_metadata": sharepoint_actions.get_file_metadata,
    "sp_upload_document": sharepoint_actions.upload_document,
    "sp_download_document": sharepoint_actions.download_document,
    "sp_delete_document": sharepoint_actions.delete_document,
    "sp_delete_item": sharepoint_actions.delete_item,
    "sp_create_folder": sharepoint_actions.create_folder,
    
    # Gestión de Archivos y Carpetas (3 acciones)
    "sp_move_item": sharepoint_actions.move_item,
    "sp_copy_item": sharepoint_actions.copy_item,
    "sp_update_file_metadata": sharepoint_actions.update_file_metadata,
    
    # Gestión de Permisos (4 acciones)
    "sp_get_sharing_link": sharepoint_actions.get_sharing_link,
    "sp_list_item_permissions": sharepoint_actions.list_item_permissions,
    "sp_add_item_permissions": sharepoint_actions.add_item_permissions,
    "sp_remove_item_permissions": sharepoint_actions.remove_item_permissions,
    
    # Sistema de Memoria (6 acciones)
    "sp_memory_ensure_list": sharepoint_actions.memory_ensure_list,
    "sp_memory_save": sharepoint_actions.memory_save,
    "sp_memory_get": sharepoint_actions.memory_get,
    "sp_memory_delete": sharepoint_actions.memory_delete,
    "sp_memory_list_keys": sharepoint_actions.memory_list_keys,
    "sp_memory_export_session": sharepoint_actions.memory_export_session,
}

# ============================================================================
# MAPEO DE ACCIONES - MICROSOFT STREAM (4 acciones)
# ============================================================================

STREAM_ACTIONS: Dict[str, Callable] = {
    "stream_listar_videos": stream_actions.listar_videos,
    "stream_obtener_metadatos_video": stream_actions.obtener_metadatos_video,
    "stream_get_video_playback_url": stream_actions.get_video_playback_url,
    "stream_obtener_transcripcion_video": stream_actions.obtener_transcripcion_video,
}

# ============================================================================
# MAPEO DE ACCIONES - TEAMS (16 acciones)
# ============================================================================

TEAMS_ACTIONS: Dict[str, Callable] = {
    "teams_list_joined_teams": teams_actions.list_joined_teams,
    "teams_get_team": teams_actions.get_team,
    "teams_list_channels": teams_actions.list_channels,
    "teams_get_channel": teams_actions.get_channel,
    "teams_send_channel_message": teams_actions.send_channel_message,
    "teams_list_channel_messages": teams_actions.list_channel_messages,
    "teams_reply_to_message": teams_actions.reply_to_message,
    "teams_list_chats": teams_actions.list_chats,
    "teams_get_chat": teams_actions.get_chat,
    "teams_create_chat": teams_actions.create_chat,
    "teams_send_chat_message": teams_actions.send_chat_message,
    "teams_list_chat_messages": teams_actions.list_chat_messages,
    "teams_schedule_meeting": teams_actions.schedule_meeting,
    "teams_get_meeting_details": teams_actions.get_meeting_details,
    "teams_list_members": teams_actions.list_members,
    "teams_get_team_by_name": teams_actions.teams_get_team_by_name,
}

# ============================================================================
# MAPEO DE ACCIONES - TIKTOK ADS (8 acciones)
# ============================================================================

TIKTOK_ADS_ACTIONS: Dict[str, Callable] = {
    "tiktok_get_ad_accounts": tiktok_ads_actions.tiktok_get_ad_accounts,
    "tiktok_get_campaigns": tiktok_ads_actions.tiktok_get_campaigns,
    "tiktok_get_analytics_report": tiktok_ads_actions.tiktok_get_analytics_report,
    "tiktok_create_campaign": tiktok_ads_actions.tiktok_create_campaign,
    "tiktok_update_campaign_status": tiktok_ads_actions.tiktok_update_campaign_status,
    "tiktok_create_ad_group": tiktok_ads_actions.tiktok_create_ad_group,
    "tiktok_create_ad": tiktok_ads_actions.tiktok_create_ad,
}

# ============================================================================
# MAPEO DE ACCIONES - TODO (7 acciones)
# ============================================================================

TODO_ACTIONS: Dict[str, Callable] = {
    "todo_list_task_lists": todo_actions.list_task_lists,
    "todo_create_task_list": todo_actions.create_task_list,
    "todo_list_tasks": todo_actions.list_tasks,
    "todo_create_task": todo_actions.create_task,
    "todo_get_task": todo_actions.get_task,
    "todo_update_task": todo_actions.update_task,
    "todo_delete_task": todo_actions.delete_task,
}

# ============================================================================
# MAPEO DE ACCIONES - USER PROFILE (5 acciones)
# ============================================================================

USER_PROFILE_ACTIONS: Dict[str, Callable] = {
    "profile_get_my_profile": userprofile_actions.profile_get_my_profile,
    "profile_get_my_manager": userprofile_actions.profile_get_my_manager,
    "profile_get_my_direct_reports": userprofile_actions.profile_get_my_direct_reports,
    "profile_get_my_photo": userprofile_actions.profile_get_my_photo,
    "profile_update_my_profile": userprofile_actions.profile_update_my_profile,
}

# ============================================================================
# MAPEO DE ACCIONES - USERS & DIRECTORY (9 acciones)
# ============================================================================

USERS_ACTIONS: Dict[str, Callable] = {
    "users_list_users": users_actions.list_users,
    "users_get_user": users_actions.get_user,
    "users_create_user": users_actions.create_user,
    "users_update_user": users_actions.update_user,
    "users_delete_user": users_actions.delete_user,
    "users_list_groups": users_actions.list_groups,
    "users_get_group": users_actions.get_group,
    "users_list_group_members": users_actions.list_group_members,
    "users_add_group_member": users_actions.add_group_member,
    "users_remove_group_member": users_actions.remove_group_member,
    "users_check_group_membership": users_actions.check_group_membership,
}

# ============================================================================
# MAPEO DE ACCIONES - VIVA INSIGHTS (2 acciones)
# ============================================================================

VIVA_INSIGHTS_ACTIONS: Dict[str, Callable] = {
    "viva_get_my_analytics": vivainsights_actions.get_my_analytics,
    "viva_get_focus_plan": vivainsights_actions.get_focus_plan,
}

# ============================================================================
# MAPEO DE ACCIONES - YOUTUBE CHANNEL (13 acciones)
# ============================================================================

YOUTUBE_CHANNEL_ACTIONS: Dict[str, Callable] = {
    "youtube_upload_video": youtube_channel_actions.youtube_upload_video,
    "youtube_update_video_metadata": youtube_channel_actions.youtube_update_video_metadata,
    "youtube_set_video_thumbnail": youtube_channel_actions.youtube_set_video_thumbnail,
    "youtube_delete_video": youtube_channel_actions.youtube_delete_video,
    "youtube_create_playlist": youtube_channel_actions.youtube_create_playlist,
    "youtube_add_video_to_playlist": youtube_channel_actions.youtube_add_video_to_playlist,
    "youtube_list_videos_in_playlist": youtube_channel_actions.youtube_list_videos_in_playlist,
    "youtube_get_video_comments": youtube_channel_actions.youtube_get_video_comments,
    "youtube_reply_to_comment": youtube_channel_actions.youtube_reply_to_comment,
    "youtube_moderate_comment": youtube_channel_actions.youtube_moderate_comment,
    "youtube_get_video_analytics": youtube_channel_actions.youtube_get_video_analytics,
    "youtube_get_channel_analytics": youtube_channel_actions.youtube_get_channel_analytics,
    "youtube_get_audience_demographics": youtube_channel_actions.youtube_get_audience_demographics,
}

# ============================================================================
# MAPEO DE ACCIONES - X (TWITTER) ADS (5 acciones)
# ============================================================================

X_ADS_ACTIONS: Dict[str, Callable] = {
    "x_ads_get_campaigns": x_ads_actions.x_ads_get_campaigns,
    "x_ads_create_campaign": x_ads_actions.x_ads_create_campaign,
    "x_ads_update_campaign": x_ads_actions.x_ads_update_campaign,
    "x_ads_delete_campaign": x_ads_actions.x_ads_delete_campaign,
    "x_ads_get_analytics": x_ads_actions.x_ads_get_analytics,
}

# ============================================================================
# MAPEO DE ACCIONES - WEB RESEARCH (10 acciones)
# ============================================================================

WEBRESEARCH_ACTIONS: Dict[str, Callable] = {
    "fetch_url": webresearch_actions.fetch_url,
    "search_web": webresearch_actions.search_web,
    "extract_text_from_url": webresearch_actions.extract_text_from_url,
    "check_url_status": webresearch_actions.check_url_status,
    "scrape_website_data": webresearch_actions.scrape_website_data,
    "batch_url_analysis": webresearch_actions.batch_url_analysis,
    "monitor_website_changes": webresearch_actions.monitor_website_changes,
    # Agregar las funciones adicionales del archivo
    "webresearch_search_web": webresearch_actions.webresearch_search_web,
    "webresearch_scrape_url": webresearch_actions.webresearch_scrape_url,
    "webresearch_extract_emails": webresearch_actions.webresearch_extract_emails,
}

# ============================================================================
# MAPEO DE ACCIONES - WORDPRESS & WOOCOMMERCE (25 acciones)
# ============================================================================

WORDPRESS_ACTIONS: Dict[str, Callable] = {
    # WordPress Core Actions (14 acciones)
    "wordpress_create_post": wordpress_actions.wordpress_create_post,
    "wordpress_update_post": wordpress_actions.wordpress_update_post,
    "wordpress_delete_post": wordpress_actions.wordpress_delete_post,
    "wordpress_get_posts": wordpress_actions.wordpress_get_posts,
    "wordpress_get_post": wordpress_actions.wordpress_get_post,
    "wordpress_create_page": wordpress_actions.wordpress_create_page,
    "wordpress_get_pages": wordpress_actions.wordpress_get_pages,
    "wordpress_create_user": wordpress_actions.wordpress_create_user,
    "wordpress_get_users": wordpress_actions.wordpress_get_users,
    "wordpress_upload_media": wordpress_actions.wordpress_upload_media,
    "wordpress_get_categories": wordpress_actions.wordpress_get_categories,
    "wordpress_create_category": wordpress_actions.wordpress_create_category,
    "wordpress_get_tags": wordpress_actions.wordpress_get_tags,
    "wordpress_backup_content": wordpress_actions.wordpress_backup_content,
    
    # WooCommerce Actions (11 acciones)
    "woocommerce_create_product": wordpress_actions.woocommerce_create_product,
    "woocommerce_get_products": wordpress_actions.woocommerce_get_products,
    "woocommerce_update_product": wordpress_actions.woocommerce_update_product,
    "woocommerce_get_orders": wordpress_actions.woocommerce_get_orders,
    "woocommerce_create_order": wordpress_actions.woocommerce_create_order,
    "woocommerce_update_order_status": wordpress_actions.woocommerce_update_order_status,
    "woocommerce_get_customers": wordpress_actions.woocommerce_get_customers,
    "woocommerce_create_customer": wordpress_actions.woocommerce_create_customer,
    "woocommerce_get_orders_by_customer": wordpress_actions.woocommerce_get_orders_by_customer,
    "woocommerce_get_product_categories": wordpress_actions.woocommerce_get_product_categories,
    "woocommerce_get_reports": wordpress_actions.woocommerce_get_reports,
}

# ============================================================================
# CONSOLIDACIÓN DE TODAS LAS ACCIONES
# ============================================================================

# Mapa principal de acciones - TODAS LAS ACCIONES DISPONIBLES
ACTION_MAP: Dict[str, Callable] = {
    **AZURE_MGMT_ACTIONS,        # 10 acciones
    **BOOKINGS_ACTIONS,          # 8 acciones
    **CALENDAR_ACTIONS,          # 7 acciones
    **EMAIL_ACTIONS,             # 10 acciones
    **FORMS_ACTIONS,             # 3 acciones
    **GEMINI_ACTIONS,            # 6 acciones
    **GITHUB_ACTIONS,            # 3 acciones
    **GOOGLEADS_ACTIONS,         # 19 acciones
    **GRAPH_ACTIONS,             # 2 acciones
    **HUBSPOT_ACTIONS,           # 21 acciones
    **LINKEDIN_ADS_ACTIONS,      # 17 acciones
    **METAADS_ACTIONS,           # 29 acciones
    **NOTION_ACTIONS,            # 16 acciones
    **OFFICE_ACTIONS,            # 8 acciones
    **ONEDRIVE_ACTIONS,          # 11 acciones
    **OPENAI_ACTIONS,            # 4 acciones
    **PLANNER_ACTIONS,           # 10 acciones
    **POWER_AUTOMATE_ACTIONS,    # 7 acciones
    **POWERBI_ACTIONS,           # 5 acciones
    **RESOLVER_ACTIONS,          # 10 acciones
    **SHAREPOINT_ACTIONS,        # 35 acciones
    **STREAM_ACTIONS,            # 4 acciones
    **TEAMS_ACTIONS,             # 16 acciones
    **TIKTOK_ADS_ACTIONS,        # 7 acciones
    **TODO_ACTIONS,              # 7 acciones
    **USER_PROFILE_ACTIONS,      # 5 acciones
    **USERS_ACTIONS,             # 11 acciones
    **VIVA_INSIGHTS_ACTIONS,     # 2 acciones
    **YOUTUBE_CHANNEL_ACTIONS,   # 13 acciones
    **X_ADS_ACTIONS,             # 5 acciones
    **WEBRESEARCH_ACTIONS,       # 10 acciones
    **WORDPRESS_ACTIONS,         # 25 acciones
}

# ============================================================================
# CONTEO DETALLADO POR CATEGORÍA
# ============================================================================

category_counts = {
    AZURE_MGMT_CATEGORY: len(AZURE_MGMT_ACTIONS),
    BOOKINGS_CATEGORY: len(BOOKINGS_ACTIONS),
    CALENDAR_CATEGORY: len(CALENDAR_ACTIONS),
    EMAIL_CATEGORY: len(EMAIL_ACTIONS),
    FORMS_CATEGORY: len(FORMS_ACTIONS),
    GEMINI_CATEGORY: len(GEMINI_ACTIONS),
    GITHUB_CATEGORY: len(GITHUB_ACTIONS),
    GOOGLEADS_CATEGORY: len(GOOGLEADS_ACTIONS),
    GRAPH_CATEGORY: len(GRAPH_ACTIONS),
    HUBSPOT_CATEGORY: len(HUBSPOT_ACTIONS),
    LINKEDIN_CATEGORY: len(LINKEDIN_ADS_ACTIONS),
    META_CATEGORY: len(METAADS_ACTIONS),
    NOTION_CATEGORY: len(NOTION_ACTIONS),
    OFFICE_CATEGORY: len(OFFICE_ACTIONS),
    ONEDRIVE_CATEGORY: len(ONEDRIVE_ACTIONS),
    OPENAI_CATEGORY: len(OPENAI_ACTIONS),
    PLANNER_CATEGORY: len(PLANNER_ACTIONS),
    POWER_AUTOMATE_CATEGORY: len(POWER_AUTOMATE_ACTIONS),
    POWERBI_CATEGORY: len(POWERBI_ACTIONS),
    RESOLVER_CATEGORY: len(RESOLVER_ACTIONS),
    SHAREPOINT_CATEGORY: len(SHAREPOINT_ACTIONS),
    STREAM_CATEGORY: len(STREAM_ACTIONS),
    TEAMS_CATEGORY: len(TEAMS_ACTIONS),
    TIKTOK_CATEGORY: len(TIKTOK_ADS_ACTIONS),
    TODO_CATEGORY: len(TODO_ACTIONS),
    USER_PROFILE_CATEGORY: len(USER_PROFILE_ACTIONS),
    USERS_CATEGORY: len(USERS_ACTIONS),
    VIVA_CATEGORY: len(VIVA_INSIGHTS_ACTIONS),
    YOUTUBE_CATEGORY: len(YOUTUBE_CHANNEL_ACTIONS),
    X_ADS_CATEGORY: len(X_ADS_ACTIONS),
    WEBRESEARCH_CATEGORY: len(WEBRESEARCH_ACTIONS),
    WORDPRESS_CATEGORY + "/" + WOOCOMMERCE_CATEGORY: len(WORDPRESS_ACTIONS),
}

# ============================================================================
# LOGGING Y VALIDACIÓN FINAL
# ============================================================================

# Validación y logging
for category, count in category_counts.items():
    logger.info(f"Categoría {category}: {count} acciones cargadas")

num_wordpress_actions = len(WORDPRESS_ACTIONS)
logger.info(f"WordPress/WooCommerce actions cargadas: {num_wordpress_actions} acciones")

num_actions = len(ACTION_MAP)
logger.info(f"ACTION_MAP cargado y validado. Total de {num_actions} acciones mapeadas y listas para usar.")

# Estadísticas finales
logger.info("=" * 80)
logger.info("ELITE DYNAMICS API - ACTION MAPPER COMPLETADO")
logger.info("=" * 80)
logger.info(f"📊 TOTAL DE ACCIONES: {num_actions}")
logger.info(f"📂 TOTAL DE CATEGORÍAS: {len(category_counts)}")
logger.info("=" * 80)

# Categorías con más acciones
top_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:5]
logger.info("🏆 TOP 5 CATEGORÍAS CON MÁS ACCIONES:")
for i, (category, count) in enumerate(top_categories, 1):
    logger.info(f"   {i}. {category}: {count} acciones")

logger.info("🎉 ACTION_MAP CARGADO EXITOSAMENTE Y LISTO PARA USAR!")
logger.info("=" * 80)