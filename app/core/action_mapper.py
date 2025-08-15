# ============================================================================
# ACTION_MAP CORREGIDO - FUNCIONES REALES ENCONTRADAS
# ============================================================================
# Generado automáticamente por el reparador crítico
# Solo incluye funciones que realmente existen y son importables

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from typing import Dict, Callable, Any
import logging

logger = logging.getLogger(__name__)

# Importar módulos de acciones que realmente existen
from app.actions import azuremgmt_actions
from app.actions import bookings_actions
from app.actions import calendario_actions
from app.actions import correo_actions
from app.actions import email_optimized_actions
from app.actions import forms_actions
from app.actions import gemini_actions
from app.actions import github_actions
from app.actions import google_marketing_enhanced
from app.actions import google_services_actions
from app.actions import googleads_actions
from app.actions import graph_actions
from app.actions import hubspot_actions
from app.actions import intelligent_assistant_actions
from app.actions import linkedin_ads_actions
from app.actions import linkedin_enhanced_actions
from app.actions import metaads_actions
from app.actions import notion_actions
from app.actions import office_actions
from app.actions import onedrive_actions
from app.actions import openai_actions
from app.actions import planner_actions
from app.actions import power_automate_actions
from app.actions import powerbi_actions
from app.actions import resolver_actions
from app.actions import runway_actions
from app.actions import runway_enhanced
from app.actions import sharepoint_actions
from app.actions import stream_actions
from app.actions import teams_actions
from app.actions import tiktok_ads_actions
from app.actions import tiktok_enhanced
from app.actions import todo_actions
from app.actions import userprofile_actions
from app.actions import users_actions
from app.actions import vivainsights_actions
from app.actions import webresearch_actions
from app.actions import whatsapp_actions
from app.actions import wordpress_actions
from app.actions import wordpress_enhanced
from app.actions import x_ads_actions
from app.actions import x_enhanced
from app.actions import youtube_channel_actions


# ============================================================================
# ACTION_MAP PRINCIPAL - SOLO FUNCIONES REALES
# ============================================================================

ACTION_MAP: Dict[str, Callable] = {

    # AZUREMGMT_ACTIONS (20 funciones)

    # BOOKINGS_ACTIONS (8 funciones)

    # CALENDARIO_ACTIONS (11 funciones)

    # CORREO_ACTIONS (14 funciones)

    # EMAIL_OPTIMIZED_ACTIONS (5 funciones)

    # FORMS_ACTIONS (3 funciones)

    # GEMINI_ACTIONS (7 funciones)

    # GITHUB_ACTIONS (3 funciones)

    # GOOGLE_MARKETING_ENHANCED (5 funciones)

    # GOOGLE_SERVICES_ACTIONS (5 funciones)

    # GOOGLEADS_ACTIONS (25 funciones)

    # GRAPH_ACTIONS (4 funciones)

    # HUBSPOT_ACTIONS (24 funciones)

    # INTELLIGENT_ASSISTANT_ACTIONS (10 funciones)

    # LINKEDIN_ADS_ACTIONS (21 funciones)

    # LINKEDIN_ENHANCED_ACTIONS (5 funciones)

    # METAADS_ACTIONS (36 funciones)

    # NOTION_ACTIONS (17 funciones)

    # OFFICE_ACTIONS (8 funciones)

    # ONEDRIVE_ACTIONS (15 funciones)

    # OPENAI_ACTIONS (4 funciones)

    # PLANNER_ACTIONS (13 funciones)

    # POWER_AUTOMATE_ACTIONS (7 funciones)

    # POWERBI_ACTIONS (5 funciones)

    # RESOLVER_ACTIONS (14 funciones)

    # RUNWAY_ACTIONS (12 funciones)

    # RUNWAY_ENHANCED (5 funciones)

    # SHAREPOINT_ACTIONS (69 funciones)

    # STREAM_ACTIONS (4 funciones)

    # TEAMS_ACTIONS (20 funciones)

    # TIKTOK_ADS_ACTIONS (7 funciones)

    # TIKTOK_ENHANCED (5 funciones)

    # TODO_ACTIONS (7 funciones)

    # USERPROFILE_ACTIONS (5 funciones)

    # USERS_ACTIONS (11 funciones)

    # VIVAINSIGHTS_ACTIONS (2 funciones)

    # WEBRESEARCH_ACTIONS (11 funciones)

    # WHATSAPP_ACTIONS (14 funciones)

    # WORDPRESS_ACTIONS (25 funciones)

    # WORDPRESS_ENHANCED (5 funciones)

    # X_ADS_ACTIONS (5 funciones)

    # X_ENHANCED (5 funciones)

    # YOUTUBE_CHANNEL_ACTIONS (20 funciones)
    "azure_create_deployment": azuremgmt_actions.azure_create_deployment,
    "azure_get_function_status": azuremgmt_actions.azure_get_function_status,
    "azure_get_logic_app_run_history": azuremgmt_actions.azure_get_logic_app_run_history,
    "azure_get_resource": azuremgmt_actions.azure_get_resource,
    "azure_list_functions": azuremgmt_actions.azure_list_functions,
    "azure_list_logic_apps": azuremgmt_actions.azure_list_logic_apps,
    "azure_list_resource_groups": azuremgmt_actions.azure_list_resource_groups,
    "azure_list_resources_in_rg": azuremgmt_actions.azure_list_resources_in_rg,
    "azure_restart_function_app": azuremgmt_actions.azure_restart_function_app,
    "azure_trigger_logic_app": azuremgmt_actions.azure_trigger_logic_app,
    "create_deployment": azuremgmt_actions.create_deployment,
    "get_function_status": azuremgmt_actions.get_function_status,
    "get_logic_app_run_history": azuremgmt_actions.get_logic_app_run_history,
    "get_resource": azuremgmt_actions.get_resource,
    "list_functions": azuremgmt_actions.list_functions,
    "list_logic_apps": azuremgmt_actions.list_logic_apps,
    "list_resource_groups": azuremgmt_actions.list_resource_groups,
    "list_resources_in_rg": azuremgmt_actions.list_resources_in_rg,
    "restart_function_app": azuremgmt_actions.restart_function_app,
    "trigger_logic_app": azuremgmt_actions.trigger_logic_app,
    "cancel_appointment": bookings_actions.cancel_appointment,
    "create_appointment": bookings_actions.create_appointment,
    "get_appointment": bookings_actions.get_appointment,
    "get_business": bookings_actions.get_business,
    "list_appointments": bookings_actions.list_appointments,
    "list_businesses": bookings_actions.list_businesses,
    "list_services": bookings_actions.list_services,
    "list_staff": bookings_actions.list_staff,
    "calendar_create_event": calendario_actions.calendar_create_event,
    "calendar_list_events": calendario_actions.calendar_list_events,
    "calendario_create_calendar_group": calendario_actions.calendario_create_calendar_group,
    "calendario_create_recurring_event": calendario_actions.calendario_create_recurring_event,
    "calendario_get_calendar_permissions": calendario_actions.calendario_get_calendar_permissions,
    "calendario_get_event_attachments": calendario_actions.calendario_get_event_attachments,
    "delete_event": calendario_actions.delete_event,
    "find_meeting_times": calendario_actions.find_meeting_times,
    "get_event": calendario_actions.get_event,
    "get_schedule": calendario_actions.get_schedule,
    "update_event": calendario_actions.update_event,
    "correo_create_mail_folder": correo_actions.correo_create_mail_folder,
    "correo_get_mail_rules": correo_actions.correo_get_mail_rules,
    "correo_get_message_properties": correo_actions.correo_get_message_properties,
    "correo_move_message": correo_actions.correo_move_message,
    "create_folder": correo_actions.create_folder,
    "delete_message": correo_actions.delete_message,
    "forward_message": correo_actions.forward_message,
    "get_message": correo_actions.get_message,
    "list_folders": correo_actions.list_folders,
    "list_messages": correo_actions.list_messages,
    "move_message": correo_actions.move_message,
    "reply_message": correo_actions.reply_message,
    "search_messages": correo_actions.search_messages,
    "send_message": correo_actions.send_message,
    "email_get_latest_messages": email_optimized_actions.email_get_latest_messages,
    "email_get_message_preview": email_optimized_actions.email_get_message_preview,
    "email_get_unread_count": email_optimized_actions.email_get_unread_count,
    "email_list_messages_summary": email_optimized_actions.email_list_messages_summary,
    "email_search_messages_optimized": email_optimized_actions.email_search_messages_optimized,
    "get_form": forms_actions.get_form,
    "get_form_responses": forms_actions.get_form_responses,
    "list_forms": forms_actions.list_forms,
    "analyze_conversation_context": gemini_actions.analyze_conversation_context,
    "classify_message_intent": gemini_actions.classify_message_intent,
    "extract_key_information": gemini_actions.extract_key_information,
    "gemini_suggest_action": gemini_actions.gemini_suggest_action,
    "generate_execution_plan": gemini_actions.generate_execution_plan,
    "generate_response_suggestions": gemini_actions.generate_response_suggestions,
    "summarize_conversation": gemini_actions.summarize_conversation,
    "github_create_issue": github_actions.github_create_issue,
    "github_get_repo_details": github_actions.github_get_repo_details,
    "github_list_repos": github_actions.github_list_repos,
    "google_ads_automate_bid_management": google_marketing_enhanced.google_ads_automate_bid_management,
    "google_ads_create_dynamic_campaigns": google_marketing_enhanced.google_ads_create_dynamic_campaigns,
    "google_ads_setup_conversion_tracking": google_marketing_enhanced.google_ads_setup_conversion_tracking,
    "google_ads_setup_enhanced_analytics": google_marketing_enhanced.google_ads_setup_enhanced_analytics,
    "google_ads_sync_with_crm": google_marketing_enhanced.google_ads_sync_with_crm,
    "calendar_schedule_event_with_meet": google_services_actions.calendar_schedule_event_with_meet,
    "drive_sync_assets_with_wordpress": google_services_actions.drive_sync_assets_with_wordpress,
    "drive_upload_to_campaign_folder": google_services_actions.drive_upload_to_campaign_folder,
    "gmail_get_leads_from_inbox": google_services_actions.gmail_get_leads_from_inbox,
    "gmail_send_bulk": google_services_actions.gmail_send_bulk,
    "get_google_ads_client": googleads_actions.get_google_ads_client,
    "googleads_add_keywords_to_ad_group": googleads_actions.googleads_add_keywords_to_ad_group,
    "googleads_apply_audience_to_ad_group": googleads_actions.googleads_apply_audience_to_ad_group,
    "googleads_create_campaign": googleads_actions.googleads_create_campaign,
    "googleads_create_conversion_action": googleads_actions.googleads_create_conversion_action,
    "googleads_create_performance_max_campaign": googleads_actions.googleads_create_performance_max_campaign,
    "googleads_create_remarketing_list": googleads_actions.googleads_create_remarketing_list,
    "googleads_create_responsive_search_ad": googleads_actions.googleads_create_responsive_search_ad,
    "googleads_get_ad_groups": googleads_actions.googleads_get_ad_groups,
    "googleads_get_ad_performance": googleads_actions.googleads_get_ad_performance,
    "googleads_get_budgets": googleads_actions.googleads_get_budgets,
    "googleads_get_campaign": googleads_actions.googleads_get_campaign,
    "googleads_get_campaign_by_name": googleads_actions.googleads_get_campaign_by_name,
    "googleads_get_campaign_performance": googleads_actions.googleads_get_campaign_performance,
    "googleads_get_campaign_performance_by_device": googleads_actions.googleads_get_campaign_performance_by_device,
    "googleads_get_campaigns": googleads_actions.googleads_get_campaigns,
    "googleads_get_conversion_actions": googleads_actions.googleads_get_conversion_actions,
    "googleads_get_conversion_metrics": googleads_actions.googleads_get_conversion_metrics,
    "googleads_get_keyword_performance_report": googleads_actions.googleads_get_keyword_performance_report,
    "googleads_list_accessible_customers": googleads_actions.googleads_list_accessible_customers,
    "googleads_set_daily_budget": googleads_actions.googleads_set_daily_budget,
    "googleads_update_campaign_status": googleads_actions.googleads_update_campaign_status,
    "googleads_upload_click_conversion": googleads_actions.googleads_upload_click_conversion,
    "googleads_upload_image_asset": googleads_actions.googleads_upload_image_asset,
    "googleads_upload_offline_conversion": googleads_actions.googleads_upload_offline_conversion,
    "generic_get": graph_actions.generic_get,
    "generic_get_compat": graph_actions.generic_get_compat,
    "generic_post": graph_actions.generic_post,
    "generic_post_compat": graph_actions.generic_post_compat,
    "hubspot_add_note_to_contact": hubspot_actions.hubspot_add_note_to_contact,
    "hubspot_associate_contact_to_deal": hubspot_actions.hubspot_associate_contact_to_deal,
    "hubspot_create_company": hubspot_actions.hubspot_create_company,
    "hubspot_create_company_and_associate_contact": hubspot_actions.hubspot_create_company_and_associate_contact,
    "hubspot_create_contact": hubspot_actions.hubspot_create_contact,
    "hubspot_create_deal": hubspot_actions.hubspot_create_deal,
    "hubspot_create_task": hubspot_actions.hubspot_create_task,
    "hubspot_delete_contact": hubspot_actions.hubspot_delete_contact,
    "hubspot_delete_deal": hubspot_actions.hubspot_delete_deal,
    "hubspot_enroll_contact_in_workflow": hubspot_actions.hubspot_enroll_contact_in_workflow,
    "hubspot_find_contact_by_email": hubspot_actions.hubspot_find_contact_by_email,
    "hubspot_get_company_by_id": hubspot_actions.hubspot_get_company_by_id,
    "hubspot_get_contact_by_id": hubspot_actions.hubspot_get_contact_by_id,
    "hubspot_get_contacts": hubspot_actions.hubspot_get_contacts,
    "hubspot_get_contacts_from_list": hubspot_actions.hubspot_get_contacts_from_list,
    "hubspot_get_deal_by_id": hubspot_actions.hubspot_get_deal_by_id,
    "hubspot_get_deals": hubspot_actions.hubspot_get_deals,
    "hubspot_get_pipeline_stages": hubspot_actions.hubspot_get_pipeline_stages,
    "hubspot_get_timeline_events": hubspot_actions.hubspot_get_timeline_events,
    "hubspot_manage_pipeline": hubspot_actions.hubspot_manage_pipeline,
    "hubspot_search_companies_by_domain": hubspot_actions.hubspot_search_companies_by_domain,
    "hubspot_update_contact": hubspot_actions.hubspot_update_contact,
    "hubspot_update_deal": hubspot_actions.hubspot_update_deal,
    "hubspot_update_deal_stage": hubspot_actions.hubspot_update_deal_stage,
    "analyze_user_behavior_patterns": intelligent_assistant_actions.analyze_user_behavior_patterns,
    "end_intelligent_session": intelligent_assistant_actions.end_intelligent_session,
    "get_conversation_history": intelligent_assistant_actions.get_conversation_history,
    "get_learning_insights": intelligent_assistant_actions.get_learning_insights,
    "get_user_intelligence_profile": intelligent_assistant_actions.get_user_intelligence_profile,
    "process_intelligent_query": intelligent_assistant_actions.process_intelligent_query,
    "search_files_intelligently": intelligent_assistant_actions.search_files_intelligently,
    "start_intelligent_session": intelligent_assistant_actions.start_intelligent_session,
    "submit_user_feedback": intelligent_assistant_actions.submit_user_feedback,
    "upload_file_intelligently": intelligent_assistant_actions.upload_file_intelligently,
    "linkedin_ads_generate_leads": linkedin_ads_actions.linkedin_ads_generate_leads,
    "linkedin_ads_get_demographics": linkedin_ads_actions.linkedin_ads_get_demographics,
    "linkedin_create_ad": linkedin_ads_actions.linkedin_create_ad,
    "linkedin_create_campaign": linkedin_ads_actions.linkedin_create_campaign,
    "linkedin_create_campaign_group": linkedin_ads_actions.linkedin_create_campaign_group,
    "linkedin_create_lead_gen_form": linkedin_ads_actions.linkedin_create_lead_gen_form,
    "linkedin_delete_ad": linkedin_ads_actions.linkedin_delete_ad,
    "linkedin_delete_campaign": linkedin_ads_actions.linkedin_delete_campaign,
    "linkedin_get_account_analytics_by_company": linkedin_ads_actions.linkedin_get_account_analytics_by_company,
    "linkedin_get_ad_accounts": linkedin_ads_actions.linkedin_get_ad_accounts,
    "linkedin_get_audience_insights": linkedin_ads_actions.linkedin_get_audience_insights,
    "linkedin_get_basic_report": linkedin_ads_actions.linkedin_get_basic_report,
    "linkedin_get_budget_usage": linkedin_ads_actions.linkedin_get_budget_usage,
    "linkedin_get_campaign_analytics_by_day": linkedin_ads_actions.linkedin_get_campaign_analytics_by_day,
    "linkedin_get_campaign_demographics": linkedin_ads_actions.linkedin_get_campaign_demographics,
    "linkedin_get_conversion_report": linkedin_ads_actions.linkedin_get_conversion_report,
    "linkedin_get_creative_analytics": linkedin_ads_actions.linkedin_get_creative_analytics,
    "linkedin_list_campaigns": linkedin_ads_actions.linkedin_list_campaigns,
    "linkedin_update_ad": linkedin_ads_actions.linkedin_update_ad,
    "linkedin_update_campaign": linkedin_ads_actions.linkedin_update_campaign,
    "linkedin_update_campaign_group_status": linkedin_ads_actions.linkedin_update_campaign_group_status,
    "linkedin_get_engagement_metrics": linkedin_enhanced_actions.linkedin_get_engagement_metrics,
    "linkedin_message_new_connections": linkedin_enhanced_actions.linkedin_message_new_connections,
    "linkedin_post_update": linkedin_enhanced_actions.linkedin_post_update,
    "linkedin_schedule_post": linkedin_enhanced_actions.linkedin_schedule_post,
    "linkedin_send_connection_requests": linkedin_enhanced_actions.linkedin_send_connection_requests,
    "get_insights": metaads_actions.get_insights,
    "meta_create_ad_set": metaads_actions.meta_create_ad_set,
    "meta_create_campaign": metaads_actions.meta_create_campaign,
    "meta_get_campaign_metrics": metaads_actions.meta_get_campaign_metrics,
    "meta_update_budget_and_schedule": metaads_actions.meta_update_budget_and_schedule,
    "meta_upload_creatives": metaads_actions.meta_upload_creatives,
    "metaads_create_ad": metaads_actions.metaads_create_ad,
    "metaads_create_ad_creative": metaads_actions.metaads_create_ad_creative,
    "metaads_create_ad_set": metaads_actions.metaads_create_ad_set,
    "metaads_create_campaign": metaads_actions.metaads_create_campaign,
    "metaads_create_custom_audience": metaads_actions.metaads_create_custom_audience,
    "metaads_delete_ad": metaads_actions.metaads_delete_ad,
    "metaads_delete_ad_set": metaads_actions.metaads_delete_ad_set,
    "metaads_delete_campaign": metaads_actions.metaads_delete_campaign,
    "metaads_get_account_insights": metaads_actions.metaads_get_account_insights,
    "metaads_get_ad_details": metaads_actions.metaads_get_ad_details,
    "metaads_get_ad_preview": metaads_actions.metaads_get_ad_preview,
    "metaads_get_ad_set_details": metaads_actions.metaads_get_ad_set_details,
    "metaads_get_ad_set_insights": metaads_actions.metaads_get_ad_set_insights,
    "metaads_get_audience_insights": metaads_actions.metaads_get_audience_insights,
    "metaads_get_business_details": metaads_actions.metaads_get_business_details,
    "metaads_get_campaign_details": metaads_actions.metaads_get_campaign_details,
    "metaads_get_campaign_insights": metaads_actions.metaads_get_campaign_insights,
    "metaads_get_page_engagement": metaads_actions.metaads_get_page_engagement,
    "metaads_get_pixel_events": metaads_actions.metaads_get_pixel_events,
    "metaads_list_campaigns": metaads_actions.metaads_list_campaigns,
    "metaads_list_custom_audiences": metaads_actions.metaads_list_custom_audiences,
    "metaads_list_owned_pages": metaads_actions.metaads_list_owned_pages,
    "metaads_pause_ad": metaads_actions.metaads_pause_ad,
    "metaads_pause_ad_set": metaads_actions.metaads_pause_ad_set,
    "metaads_pause_campaign": metaads_actions.metaads_pause_campaign,
    "metaads_pause_entity": metaads_actions.metaads_pause_entity,
    "metaads_update_ad": metaads_actions.metaads_update_ad,
    "metaads_update_ad_set": metaads_actions.metaads_update_ad_set,
    "metaads_update_campaign": metaads_actions.metaads_update_campaign,
    "metaads_update_page_settings": metaads_actions.metaads_update_page_settings,
    "notion_add_users_to_page": notion_actions.notion_add_users_to_page,
    "notion_append_text_block_to_page": notion_actions.notion_append_text_block_to_page,
    "notion_archive_page": notion_actions.notion_archive_page,
    "notion_create_database": notion_actions.notion_create_database,
    "notion_create_page": notion_actions.notion_create_page,
    "notion_create_page_in_database": notion_actions.notion_create_page_in_database,
    "notion_delete_block": notion_actions.notion_delete_block,
    "notion_error_handler": notion_actions.notion_error_handler,
    "notion_find_database_by_name": notion_actions.notion_find_database_by_name,
    "notion_get_block": notion_actions.notion_get_block,
    "notion_get_database": notion_actions.notion_get_database,
    "notion_get_page_content": notion_actions.notion_get_page_content,
    "notion_query_database": notion_actions.notion_query_database,
    "notion_retrieve_page": notion_actions.notion_retrieve_page,
    "notion_search_general": notion_actions.notion_search_general,
    "notion_update_block": notion_actions.notion_update_block,
    "notion_update_page": notion_actions.notion_update_page,
    "agregar_filas_tabla_excel": office_actions.agregar_filas_tabla_excel,
    "crear_documento_word": office_actions.crear_documento_word,
    "crear_libro_excel": office_actions.crear_libro_excel,
    "crear_tabla_excel": office_actions.crear_tabla_excel,
    "escribir_celda_excel": office_actions.escribir_celda_excel,
    "leer_celda_excel": office_actions.leer_celda_excel,
    "obtener_documento_word_binario": office_actions.obtener_documento_word_binario,
    "reemplazar_contenido_word": office_actions.reemplazar_contenido_word,
    "copy_item": onedrive_actions.copy_item,
    "create_folder": onedrive_actions.create_folder,
    "delete_item": onedrive_actions.delete_item,
    "download_file": onedrive_actions.download_file,
    "get_item": onedrive_actions.get_item,
    "get_sharing_link": onedrive_actions.get_sharing_link,
    "list_items": onedrive_actions.list_items,
    "move_item": onedrive_actions.move_item,
    "onedrive_create_folder_structure": onedrive_actions.onedrive_create_folder_structure,
    "onedrive_get_file_versions": onedrive_actions.onedrive_get_file_versions,
    "onedrive_get_storage_quota": onedrive_actions.onedrive_get_storage_quota,
    "onedrive_set_file_permissions": onedrive_actions.onedrive_set_file_permissions,
    "search_items": onedrive_actions.search_items,
    "update_item_metadata": onedrive_actions.update_item_metadata,
    "upload_file": onedrive_actions.upload_file,
    "chat_completion": openai_actions.chat_completion,
    "completion": openai_actions.completion,
    "get_embedding": openai_actions.get_embedding,
    "list_models": openai_actions.list_models,
    "create_bucket": planner_actions.create_bucket,
    "create_task": planner_actions.create_task,
    "delete_task": planner_actions.delete_task,
    "get_plan": planner_actions.get_plan,
    "get_task": planner_actions.get_task,
    "list_buckets": planner_actions.list_buckets,
    "list_plans": planner_actions.list_plans,
    "list_tasks": planner_actions.list_tasks,
    "planner_assign_task_to_user": planner_actions.planner_assign_task_to_user,
    "planner_create_task_checklist": planner_actions.planner_create_task_checklist,
    "planner_get_plan_by_name": planner_actions.planner_get_plan_by_name,
    "planner_get_plan_categories": planner_actions.planner_get_plan_categories,
    "update_task": planner_actions.update_task,
    "pa_create_or_update_flow": power_automate_actions.pa_create_or_update_flow,
    "pa_delete_flow": power_automate_actions.pa_delete_flow,
    "pa_get_flow": power_automate_actions.pa_get_flow,
    "pa_get_flow_run_details": power_automate_actions.pa_get_flow_run_details,
    "pa_get_flow_run_history": power_automate_actions.pa_get_flow_run_history,
    "pa_list_flows": power_automate_actions.pa_list_flows,
    "pa_run_flow_trigger": power_automate_actions.pa_run_flow_trigger,
    "export_report": powerbi_actions.export_report,
    "list_dashboards": powerbi_actions.list_dashboards,
    "list_datasets": powerbi_actions.list_datasets,
    "list_reports": powerbi_actions.list_reports,
    "refresh_dataset": powerbi_actions.refresh_dataset,
    "clear_resolution_cache": resolver_actions.clear_resolution_cache,
    "execute_workflow": resolver_actions.execute_workflow,
    "get_credentials_from_vault": resolver_actions.get_credentials_from_vault,
    "get_resolution_analytics": resolver_actions.get_resolution_analytics,
    "get_resource_config": resolver_actions.get_resource_config,
    "list_available_resources": resolver_actions.list_available_resources,
    "resolve_contextual_action": resolver_actions.resolve_contextual_action,
    "resolve_dynamic_query": resolver_actions.resolve_dynamic_query,
    "resolve_resource": resolver_actions.resolve_resource,
    "resolve_smart_workflow": resolver_actions.resolve_smart_workflow,
    "save_to_notion_registry": resolver_actions.save_to_notion_registry,
    "search_resources": resolver_actions.search_resources,
    "smart_save_resource": resolver_actions.smart_save_resource,
    "validate_resource_id": resolver_actions.validate_resource_id,
    "runway_batch_generate": runway_actions.runway_batch_generate,
    "runway_cancel_task": runway_actions.runway_cancel_task,
    "runway_estimate_cost": runway_actions.runway_estimate_cost,
    "runway_generate_image": runway_actions.runway_generate_image,
    "runway_generate_video": runway_actions.runway_generate_video,
    "runway_generate_video_from_multiple_images": runway_actions.runway_generate_video_from_multiple_images,
    "runway_generate_video_from_text": runway_actions.runway_generate_video_from_text,
    "runway_get_result_url": runway_actions.runway_get_result_url,
    "runway_get_task_history": runway_actions.runway_get_task_history,
    "runway_get_video_status": runway_actions.runway_get_video_status,
    "runway_list_models": runway_actions.runway_list_models,
    "runway_wait_and_save": runway_actions.runway_wait_and_save,
    "runway_generate_video_advanced": runway_enhanced.runway_generate_video_advanced,
    "runway_image_to_video_pro": runway_enhanced.runway_image_to_video_pro,
    "runway_model_training_custom": runway_enhanced.runway_model_training_custom,
    "runway_text_to_video_studio": runway_enhanced.runway_text_to_video_studio,
    "runway_video_editing_suite": runway_enhanced.runway_video_editing_suite,
    "add_item_permissions": sharepoint_actions.add_item_permissions,
    "add_list_item": sharepoint_actions.add_list_item,
    "copy_item": sharepoint_actions.copy_item,
    "create_folder": sharepoint_actions.create_folder,
    "create_list": sharepoint_actions.create_list,
    "delete_document": sharepoint_actions.delete_document,
    "delete_item": sharepoint_actions.delete_item,
    "delete_list": sharepoint_actions.delete_list,
    "delete_list_item": sharepoint_actions.delete_list_item,
    "download_document": sharepoint_actions.download_document,
    "get_file_metadata": sharepoint_actions.get_file_metadata,
    "get_list": sharepoint_actions.get_list,
    "get_list_item": sharepoint_actions.get_list_item,
    "get_sharing_link": sharepoint_actions.get_sharing_link,
    "get_site_info": sharepoint_actions.get_site_info,
    "list_document_libraries": sharepoint_actions.list_document_libraries,
    "list_folder_contents": sharepoint_actions.list_folder_contents,
    "list_item_permissions": sharepoint_actions.list_item_permissions,
    "list_list_items": sharepoint_actions.list_list_items,
    "list_lists": sharepoint_actions.list_lists,
    "memory_delete": sharepoint_actions.memory_delete,
    "memory_ensure_list": sharepoint_actions.memory_ensure_list,
    "memory_export_session": sharepoint_actions.memory_export_session,
    "memory_get": sharepoint_actions.memory_get,
    "memory_list_keys": sharepoint_actions.memory_list_keys,
    "memory_save": sharepoint_actions.memory_save,
    "move_item": sharepoint_actions.move_item,
    "remove_item_permissions": sharepoint_actions.remove_item_permissions,
    "search_list_items": sharepoint_actions.search_list_items,
    "search_sites": sharepoint_actions.search_sites,
    "sp_add_item_permissions": sharepoint_actions.sp_add_item_permissions,
    "sp_add_list_item": sharepoint_actions.sp_add_list_item,
    "sp_copy_item": sharepoint_actions.sp_copy_item,
    "sp_create_folder": sharepoint_actions.sp_create_folder,
    "sp_create_list": sharepoint_actions.sp_create_list,
    "sp_delete_document": sharepoint_actions.sp_delete_document,
    "sp_delete_item": sharepoint_actions.sp_delete_item,
    "sp_delete_list": sharepoint_actions.sp_delete_list,
    "sp_delete_list_item": sharepoint_actions.sp_delete_list_item,
    "sp_download_document": sharepoint_actions.sp_download_document,
    "sp_export_list_to_format": sharepoint_actions.sp_export_list_to_format,
    "sp_get_file_metadata": sharepoint_actions.sp_get_file_metadata,
    "sp_get_list": sharepoint_actions.sp_get_list,
    "sp_get_list_item": sharepoint_actions.sp_get_list_item,
    "sp_get_sharing_link": sharepoint_actions.sp_get_sharing_link,
    "sp_get_site_info": sharepoint_actions.sp_get_site_info,
    "sp_list_document_libraries": sharepoint_actions.sp_list_document_libraries,
    "sp_list_folder_contents": sharepoint_actions.sp_list_folder_contents,
    "sp_list_item_permissions": sharepoint_actions.sp_list_item_permissions,
    "sp_list_list_items": sharepoint_actions.sp_list_list_items,
    "sp_list_lists": sharepoint_actions.sp_list_lists,
    "sp_memory_delete": sharepoint_actions.sp_memory_delete,
    "sp_memory_ensure_list": sharepoint_actions.sp_memory_ensure_list,
    "sp_memory_export_session": sharepoint_actions.sp_memory_export_session,
    "sp_memory_get": sharepoint_actions.sp_memory_get,
    "sp_memory_list_keys": sharepoint_actions.sp_memory_list_keys,
    "sp_memory_save": sharepoint_actions.sp_memory_save,
    "sp_move_item": sharepoint_actions.sp_move_item,
    "sp_remove_item_permissions": sharepoint_actions.sp_remove_item_permissions,
    "sp_search_list_items": sharepoint_actions.sp_search_list_items,
    "sp_search_sites": sharepoint_actions.sp_search_sites,
    "sp_update_file_metadata": sharepoint_actions.sp_update_file_metadata,
    "sp_update_list": sharepoint_actions.sp_update_list,
    "sp_update_list_item": sharepoint_actions.sp_update_list_item,
    "sp_upload_document": sharepoint_actions.sp_upload_document,
    "update_file_metadata": sharepoint_actions.update_file_metadata,
    "update_list": sharepoint_actions.update_list,
    "update_list_item": sharepoint_actions.update_list_item,
    "upload_document": sharepoint_actions.upload_document,
    "get_video_playback_url": stream_actions.get_video_playback_url,
    "listar_videos": stream_actions.listar_videos,
    "obtener_metadatos_video": stream_actions.obtener_metadatos_video,
    "obtener_transcripcion_video": stream_actions.obtener_transcripcion_video,
    "create_chat": teams_actions.create_chat,
    "get_channel": teams_actions.get_channel,
    "get_chat": teams_actions.get_chat,
    "get_meeting_details": teams_actions.get_meeting_details,
    "get_team": teams_actions.get_team,
    "list_channel_messages": teams_actions.list_channel_messages,
    "list_channels": teams_actions.list_channels,
    "list_chat_messages": teams_actions.list_chat_messages,
    "list_chats": teams_actions.list_chats,
    "list_joined_teams": teams_actions.list_joined_teams,
    "list_members": teams_actions.list_members,
    "reply_to_message": teams_actions.reply_to_message,
    "schedule_meeting": teams_actions.schedule_meeting,
    "send_channel_message": teams_actions.send_channel_message,
    "send_chat_message": teams_actions.send_chat_message,
    "teams_create_team_channel": teams_actions.teams_create_team_channel,
    "teams_create_team_meeting": teams_actions.teams_create_team_meeting,
    "teams_get_channel_tabs": teams_actions.teams_get_channel_tabs,
    "teams_get_team_apps": teams_actions.teams_get_team_apps,
    "teams_get_team_by_name": teams_actions.teams_get_team_by_name,
    "tiktok_create_ad": tiktok_ads_actions.tiktok_create_ad,
    "tiktok_create_ad_group": tiktok_ads_actions.tiktok_create_ad_group,
    "tiktok_create_campaign": tiktok_ads_actions.tiktok_create_campaign,
    "tiktok_get_ad_accounts": tiktok_ads_actions.tiktok_get_ad_accounts,
    "tiktok_get_analytics_report": tiktok_ads_actions.tiktok_get_analytics_report,
    "tiktok_get_campaigns": tiktok_ads_actions.tiktok_get_campaigns,
    "tiktok_update_campaign_status": tiktok_ads_actions.tiktok_update_campaign_status,
    "tiktok_audience_growth_suite": tiktok_enhanced.tiktok_audience_growth_suite,
    "tiktok_campaign_automation_pro": tiktok_enhanced.tiktok_campaign_automation_pro,
    "tiktok_post_advanced_video": tiktok_enhanced.tiktok_post_advanced_video,
    "tiktok_trending_analytics_pro": tiktok_enhanced.tiktok_trending_analytics_pro,
    "tiktok_viral_content_factory": tiktok_enhanced.tiktok_viral_content_factory,
    "create_task": todo_actions.create_task,
    "create_task_list": todo_actions.create_task_list,
    "delete_task": todo_actions.delete_task,
    "get_task": todo_actions.get_task,
    "list_task_lists": todo_actions.list_task_lists,
    "list_tasks": todo_actions.list_tasks,
    "update_task": todo_actions.update_task,
    "profile_get_my_direct_reports": userprofile_actions.profile_get_my_direct_reports,
    "profile_get_my_manager": userprofile_actions.profile_get_my_manager,
    "profile_get_my_photo": userprofile_actions.profile_get_my_photo,
    "profile_get_my_profile": userprofile_actions.profile_get_my_profile,
    "profile_update_my_profile": userprofile_actions.profile_update_my_profile,
    "add_group_member": users_actions.add_group_member,
    "check_group_membership": users_actions.check_group_membership,
    "create_user": users_actions.create_user,
    "delete_user": users_actions.delete_user,
    "get_group": users_actions.get_group,
    "get_user": users_actions.get_user,
    "list_group_members": users_actions.list_group_members,
    "list_groups": users_actions.list_groups,
    "list_users": users_actions.list_users,
    "remove_group_member": users_actions.remove_group_member,
    "update_user": users_actions.update_user,
    "get_focus_plan": vivainsights_actions.get_focus_plan,
    "get_my_analytics": vivainsights_actions.get_my_analytics,
    "batch_url_analysis": webresearch_actions.batch_url_analysis,
    "check_url_status": webresearch_actions.check_url_status,
    "extract_text_from_url": webresearch_actions.extract_text_from_url,
    "fetch_url": webresearch_actions.fetch_url,
    "monitor_website_changes": webresearch_actions.monitor_website_changes,
    "scrape_website_data": webresearch_actions.scrape_website_data,
    "search_web": webresearch_actions.search_web,
    "webresearch_extract_emails": webresearch_actions.webresearch_extract_emails,
    "webresearch_extract_phone_numbers": webresearch_actions.webresearch_extract_phone_numbers,
    "webresearch_scrape_url": webresearch_actions.webresearch_scrape_url,
    "webresearch_search_web": webresearch_actions.webresearch_search_web,
    "whatsapp_broadcast_segment": whatsapp_actions.whatsapp_broadcast_segment,
    "whatsapp_close_ticket": whatsapp_actions.whatsapp_close_ticket,
    "whatsapp_create_template": whatsapp_actions.whatsapp_create_template,
    "whatsapp_download_media": whatsapp_actions.whatsapp_download_media,
    "whatsapp_get_media": whatsapp_actions.whatsapp_get_media,
    "whatsapp_get_message_status": whatsapp_actions.whatsapp_get_message_status,
    "whatsapp_handover_to_human": whatsapp_actions.whatsapp_handover_to_human,
    "whatsapp_list_templates": whatsapp_actions.whatsapp_list_templates,
    "whatsapp_mark_read": whatsapp_actions.whatsapp_mark_read,
    "whatsapp_send_interactive": whatsapp_actions.whatsapp_send_interactive,
    "whatsapp_send_media": whatsapp_actions.whatsapp_send_media,
    "whatsapp_send_template": whatsapp_actions.whatsapp_send_template,
    "whatsapp_send_text": whatsapp_actions.whatsapp_send_text,
    "whatsapp_upload_media": whatsapp_actions.whatsapp_upload_media,
    "woocommerce_create_customer": wordpress_actions.woocommerce_create_customer,
    "woocommerce_create_order": wordpress_actions.woocommerce_create_order,
    "woocommerce_create_product": wordpress_actions.woocommerce_create_product,
    "woocommerce_get_customers": wordpress_actions.woocommerce_get_customers,
    "woocommerce_get_orders": wordpress_actions.woocommerce_get_orders,
    "woocommerce_get_orders_by_customer": wordpress_actions.woocommerce_get_orders_by_customer,
    "woocommerce_get_product_categories": wordpress_actions.woocommerce_get_product_categories,
    "woocommerce_get_products": wordpress_actions.woocommerce_get_products,
    "woocommerce_get_reports": wordpress_actions.woocommerce_get_reports,
    "woocommerce_update_order_status": wordpress_actions.woocommerce_update_order_status,
    "woocommerce_update_product": wordpress_actions.woocommerce_update_product,
    "wordpress_backup_content": wordpress_actions.wordpress_backup_content,
    "wordpress_create_category": wordpress_actions.wordpress_create_category,
    "wordpress_create_page": wordpress_actions.wordpress_create_page,
    "wordpress_create_post": wordpress_actions.wordpress_create_post,
    "wordpress_create_user": wordpress_actions.wordpress_create_user,
    "wordpress_delete_post": wordpress_actions.wordpress_delete_post,
    "wordpress_get_categories": wordpress_actions.wordpress_get_categories,
    "wordpress_get_pages": wordpress_actions.wordpress_get_pages,
    "wordpress_get_post": wordpress_actions.wordpress_get_post,
    "wordpress_get_posts": wordpress_actions.wordpress_get_posts,
    "wordpress_get_tags": wordpress_actions.wordpress_get_tags,
    "wordpress_get_users": wordpress_actions.wordpress_get_users,
    "wordpress_update_post": wordpress_actions.wordpress_update_post,
    "wordpress_upload_media": wordpress_actions.wordpress_upload_media,
    "wordpress_backup_and_restore": wordpress_enhanced.wordpress_backup_and_restore,
    "wordpress_create_advanced_post": wordpress_enhanced.wordpress_create_advanced_post,
    "wordpress_manage_plugins_advanced": wordpress_enhanced.wordpress_manage_plugins_advanced,
    "wordpress_manage_users_advanced": wordpress_enhanced.wordpress_manage_users_advanced,
    "wordpress_optimize_performance": wordpress_enhanced.wordpress_optimize_performance,
    "x_ads_create_campaign": x_ads_actions.x_ads_create_campaign,
    "x_ads_delete_campaign": x_ads_actions.x_ads_delete_campaign,
    "x_ads_get_analytics": x_ads_actions.x_ads_get_analytics,
    "x_ads_get_campaigns": x_ads_actions.x_ads_get_campaigns,
    "x_ads_update_campaign": x_ads_actions.x_ads_update_campaign,
    "x_audience_analytics_pro": x_enhanced.x_audience_analytics_pro,
    "x_campaign_management_suite": x_enhanced.x_campaign_management_suite,
    "x_community_management_pro": x_enhanced.x_community_management_pro,
    "x_post_advanced_tweet": x_enhanced.x_post_advanced_tweet,
    "x_viral_content_optimizer": x_enhanced.x_viral_content_optimizer,
    "validate_date_format": youtube_channel_actions.validate_date_format,
    "youtube_add_video_to_playlist": youtube_channel_actions.youtube_add_video_to_playlist,
    "youtube_bulk_upload_from_folder": youtube_channel_actions.youtube_bulk_upload_from_folder,
    "youtube_create_playlist": youtube_channel_actions.youtube_create_playlist,
    "youtube_delete_video": youtube_channel_actions.youtube_delete_video,
    "youtube_get_analytics": youtube_channel_actions.youtube_get_analytics,
    "youtube_get_audience_demographics": youtube_channel_actions.youtube_get_audience_demographics,
    "youtube_get_channel_analytics": youtube_channel_actions.youtube_get_channel_analytics,
    "youtube_get_channel_info": youtube_channel_actions.youtube_get_channel_info,
    "youtube_get_video_analytics": youtube_channel_actions.youtube_get_video_analytics,
    "youtube_get_video_comments": youtube_channel_actions.youtube_get_video_comments,
    "youtube_list_channel_videos": youtube_channel_actions.youtube_list_channel_videos,
    "youtube_list_videos_in_playlist": youtube_channel_actions.youtube_list_videos_in_playlist,
    "youtube_manage_comments": youtube_channel_actions.youtube_manage_comments,
    "youtube_moderate_comment": youtube_channel_actions.youtube_moderate_comment,
    "youtube_reply_to_comment": youtube_channel_actions.youtube_reply_to_comment,
    "youtube_schedule_video": youtube_channel_actions.youtube_schedule_video,
    "youtube_set_video_thumbnail": youtube_channel_actions.youtube_set_video_thumbnail,
    "youtube_update_video_metadata": youtube_channel_actions.youtube_update_video_metadata,
    "youtube_upload_video": youtube_channel_actions.youtube_upload_video
}


# ============================================================================
# ESTADÍSTICAS DEL ACTION_MAP
# ============================================================================

TOTAL_ACTIONS = 521
TOTAL_MODULES = 43
TOTAL_FILES_ANALYZED = 43

print(f"🎯 ACTION_MAP cargado exitosamente:")
print(f"   ✅ {TOTAL_ACTIONS} acciones disponibles")
print(f"   📦 {TOTAL_MODULES} módulos importados")
print(f"   📊 Porcentaje éxito: {(TOTAL_MODULES/TOTAL_FILES_ANALYZED*100):.1f}%")

# ============================================================================
# FUNCIONES DE UTILIDAD
# ============================================================================

def get_available_actions() -> Dict[str, str]:
    """Retorna diccionario con todas las acciones disponibles y sus módulos"""
    actions_info = {}
    actions_info["azure_create_deployment"] = "azuremgmt_actions"
    actions_info["azure_get_function_status"] = "azuremgmt_actions"
    actions_info["azure_get_logic_app_run_history"] = "azuremgmt_actions"
    actions_info["azure_get_resource"] = "azuremgmt_actions"
    actions_info["azure_list_functions"] = "azuremgmt_actions"
    actions_info["azure_list_logic_apps"] = "azuremgmt_actions"
    actions_info["azure_list_resource_groups"] = "azuremgmt_actions"
    actions_info["azure_list_resources_in_rg"] = "azuremgmt_actions"
    actions_info["azure_restart_function_app"] = "azuremgmt_actions"
    actions_info["azure_trigger_logic_app"] = "azuremgmt_actions"
    actions_info["create_deployment"] = "azuremgmt_actions"
    actions_info["get_function_status"] = "azuremgmt_actions"
    actions_info["get_logic_app_run_history"] = "azuremgmt_actions"
    actions_info["get_resource"] = "azuremgmt_actions"
    actions_info["list_functions"] = "azuremgmt_actions"
    actions_info["list_logic_apps"] = "azuremgmt_actions"
    actions_info["list_resource_groups"] = "azuremgmt_actions"
    actions_info["list_resources_in_rg"] = "azuremgmt_actions"
    actions_info["restart_function_app"] = "azuremgmt_actions"
    actions_info["trigger_logic_app"] = "azuremgmt_actions"
    actions_info["cancel_appointment"] = "bookings_actions"
    actions_info["create_appointment"] = "bookings_actions"
    actions_info["get_appointment"] = "bookings_actions"
    actions_info["get_business"] = "bookings_actions"
    actions_info["list_appointments"] = "bookings_actions"
    actions_info["list_businesses"] = "bookings_actions"
    actions_info["list_services"] = "bookings_actions"
    actions_info["list_staff"] = "bookings_actions"
    actions_info["calendar_create_event"] = "calendario_actions"
    actions_info["calendar_list_events"] = "calendario_actions"
    actions_info["calendario_create_calendar_group"] = "calendario_actions"
    actions_info["calendario_create_recurring_event"] = "calendario_actions"
    actions_info["calendario_get_calendar_permissions"] = "calendario_actions"
    actions_info["calendario_get_event_attachments"] = "calendario_actions"
    actions_info["delete_event"] = "calendario_actions"
    actions_info["find_meeting_times"] = "calendario_actions"
    actions_info["get_event"] = "calendario_actions"
    actions_info["get_schedule"] = "calendario_actions"
    actions_info["update_event"] = "calendario_actions"
    actions_info["correo_create_mail_folder"] = "correo_actions"
    actions_info["correo_get_mail_rules"] = "correo_actions"
    actions_info["correo_get_message_properties"] = "correo_actions"
    actions_info["correo_move_message"] = "correo_actions"
    actions_info["create_folder"] = "correo_actions"
    actions_info["delete_message"] = "correo_actions"
    actions_info["forward_message"] = "correo_actions"
    actions_info["get_message"] = "correo_actions"
    actions_info["list_folders"] = "correo_actions"
    actions_info["list_messages"] = "correo_actions"
    actions_info["move_message"] = "correo_actions"
    actions_info["reply_message"] = "correo_actions"
    actions_info["search_messages"] = "correo_actions"
    actions_info["send_message"] = "correo_actions"
    actions_info["email_get_latest_messages"] = "email_optimized_actions"
    actions_info["email_get_message_preview"] = "email_optimized_actions"
    actions_info["email_get_unread_count"] = "email_optimized_actions"
    actions_info["email_list_messages_summary"] = "email_optimized_actions"
    actions_info["email_search_messages_optimized"] = "email_optimized_actions"
    actions_info["get_form"] = "forms_actions"
    actions_info["get_form_responses"] = "forms_actions"
    actions_info["list_forms"] = "forms_actions"
    actions_info["analyze_conversation_context"] = "gemini_actions"
    actions_info["classify_message_intent"] = "gemini_actions"
    actions_info["extract_key_information"] = "gemini_actions"
    actions_info["gemini_suggest_action"] = "gemini_actions"
    actions_info["generate_execution_plan"] = "gemini_actions"
    actions_info["generate_response_suggestions"] = "gemini_actions"
    actions_info["summarize_conversation"] = "gemini_actions"
    actions_info["github_create_issue"] = "github_actions"
    actions_info["github_get_repo_details"] = "github_actions"
    actions_info["github_list_repos"] = "github_actions"
    actions_info["google_ads_automate_bid_management"] = "google_marketing_enhanced"
    actions_info["google_ads_create_dynamic_campaigns"] = "google_marketing_enhanced"
    actions_info["google_ads_setup_conversion_tracking"] = "google_marketing_enhanced"
    actions_info["google_ads_setup_enhanced_analytics"] = "google_marketing_enhanced"
    actions_info["google_ads_sync_with_crm"] = "google_marketing_enhanced"
    actions_info["calendar_schedule_event_with_meet"] = "google_services_actions"
    actions_info["drive_sync_assets_with_wordpress"] = "google_services_actions"
    actions_info["drive_upload_to_campaign_folder"] = "google_services_actions"
    actions_info["gmail_get_leads_from_inbox"] = "google_services_actions"
    actions_info["gmail_send_bulk"] = "google_services_actions"
    actions_info["get_google_ads_client"] = "googleads_actions"
    actions_info["googleads_add_keywords_to_ad_group"] = "googleads_actions"
    actions_info["googleads_apply_audience_to_ad_group"] = "googleads_actions"
    actions_info["googleads_create_campaign"] = "googleads_actions"
    actions_info["googleads_create_conversion_action"] = "googleads_actions"
    actions_info["googleads_create_performance_max_campaign"] = "googleads_actions"
    actions_info["googleads_create_remarketing_list"] = "googleads_actions"
    actions_info["googleads_create_responsive_search_ad"] = "googleads_actions"
    actions_info["googleads_get_ad_groups"] = "googleads_actions"
    actions_info["googleads_get_ad_performance"] = "googleads_actions"
    actions_info["googleads_get_budgets"] = "googleads_actions"
    actions_info["googleads_get_campaign"] = "googleads_actions"
    actions_info["googleads_get_campaign_by_name"] = "googleads_actions"
    actions_info["googleads_get_campaign_performance"] = "googleads_actions"
    actions_info["googleads_get_campaign_performance_by_device"] = "googleads_actions"
    actions_info["googleads_get_campaigns"] = "googleads_actions"
    actions_info["googleads_get_conversion_actions"] = "googleads_actions"
    actions_info["googleads_get_conversion_metrics"] = "googleads_actions"
    actions_info["googleads_get_keyword_performance_report"] = "googleads_actions"
    actions_info["googleads_list_accessible_customers"] = "googleads_actions"
    actions_info["googleads_set_daily_budget"] = "googleads_actions"
    actions_info["googleads_update_campaign_status"] = "googleads_actions"
    actions_info["googleads_upload_click_conversion"] = "googleads_actions"
    actions_info["googleads_upload_image_asset"] = "googleads_actions"
    actions_info["googleads_upload_offline_conversion"] = "googleads_actions"
    actions_info["generic_get"] = "graph_actions"
    actions_info["generic_get_compat"] = "graph_actions"
    actions_info["generic_post"] = "graph_actions"
    actions_info["generic_post_compat"] = "graph_actions"
    actions_info["hubspot_add_note_to_contact"] = "hubspot_actions"
    actions_info["hubspot_associate_contact_to_deal"] = "hubspot_actions"
    actions_info["hubspot_create_company"] = "hubspot_actions"
    actions_info["hubspot_create_company_and_associate_contact"] = "hubspot_actions"
    actions_info["hubspot_create_contact"] = "hubspot_actions"
    actions_info["hubspot_create_deal"] = "hubspot_actions"
    actions_info["hubspot_create_task"] = "hubspot_actions"
    actions_info["hubspot_delete_contact"] = "hubspot_actions"
    actions_info["hubspot_delete_deal"] = "hubspot_actions"
    actions_info["hubspot_enroll_contact_in_workflow"] = "hubspot_actions"
    actions_info["hubspot_find_contact_by_email"] = "hubspot_actions"
    actions_info["hubspot_get_company_by_id"] = "hubspot_actions"
    actions_info["hubspot_get_contact_by_id"] = "hubspot_actions"
    actions_info["hubspot_get_contacts"] = "hubspot_actions"
    actions_info["hubspot_get_contacts_from_list"] = "hubspot_actions"
    actions_info["hubspot_get_deal_by_id"] = "hubspot_actions"
    actions_info["hubspot_get_deals"] = "hubspot_actions"
    actions_info["hubspot_get_pipeline_stages"] = "hubspot_actions"
    actions_info["hubspot_get_timeline_events"] = "hubspot_actions"
    actions_info["hubspot_manage_pipeline"] = "hubspot_actions"
    actions_info["hubspot_search_companies_by_domain"] = "hubspot_actions"
    actions_info["hubspot_update_contact"] = "hubspot_actions"
    actions_info["hubspot_update_deal"] = "hubspot_actions"
    actions_info["hubspot_update_deal_stage"] = "hubspot_actions"
    actions_info["analyze_user_behavior_patterns"] = "intelligent_assistant_actions"
    actions_info["end_intelligent_session"] = "intelligent_assistant_actions"
    actions_info["get_conversation_history"] = "intelligent_assistant_actions"
    actions_info["get_learning_insights"] = "intelligent_assistant_actions"
    actions_info["get_user_intelligence_profile"] = "intelligent_assistant_actions"
    actions_info["process_intelligent_query"] = "intelligent_assistant_actions"
    actions_info["search_files_intelligently"] = "intelligent_assistant_actions"
    actions_info["start_intelligent_session"] = "intelligent_assistant_actions"
    actions_info["submit_user_feedback"] = "intelligent_assistant_actions"
    actions_info["upload_file_intelligently"] = "intelligent_assistant_actions"
    actions_info["linkedin_ads_generate_leads"] = "linkedin_ads_actions"
    actions_info["linkedin_ads_get_demographics"] = "linkedin_ads_actions"
    actions_info["linkedin_create_ad"] = "linkedin_ads_actions"
    actions_info["linkedin_create_campaign"] = "linkedin_ads_actions"
    actions_info["linkedin_create_campaign_group"] = "linkedin_ads_actions"
    actions_info["linkedin_create_lead_gen_form"] = "linkedin_ads_actions"
    actions_info["linkedin_delete_ad"] = "linkedin_ads_actions"
    actions_info["linkedin_delete_campaign"] = "linkedin_ads_actions"
    actions_info["linkedin_get_account_analytics_by_company"] = "linkedin_ads_actions"
    actions_info["linkedin_get_ad_accounts"] = "linkedin_ads_actions"
    actions_info["linkedin_get_audience_insights"] = "linkedin_ads_actions"
    actions_info["linkedin_get_basic_report"] = "linkedin_ads_actions"
    actions_info["linkedin_get_budget_usage"] = "linkedin_ads_actions"
    actions_info["linkedin_get_campaign_analytics_by_day"] = "linkedin_ads_actions"
    actions_info["linkedin_get_campaign_demographics"] = "linkedin_ads_actions"
    actions_info["linkedin_get_conversion_report"] = "linkedin_ads_actions"
    actions_info["linkedin_get_creative_analytics"] = "linkedin_ads_actions"
    actions_info["linkedin_list_campaigns"] = "linkedin_ads_actions"
    actions_info["linkedin_update_ad"] = "linkedin_ads_actions"
    actions_info["linkedin_update_campaign"] = "linkedin_ads_actions"
    actions_info["linkedin_update_campaign_group_status"] = "linkedin_ads_actions"
    actions_info["linkedin_get_engagement_metrics"] = "linkedin_enhanced_actions"
    actions_info["linkedin_message_new_connections"] = "linkedin_enhanced_actions"
    actions_info["linkedin_post_update"] = "linkedin_enhanced_actions"
    actions_info["linkedin_schedule_post"] = "linkedin_enhanced_actions"
    actions_info["linkedin_send_connection_requests"] = "linkedin_enhanced_actions"
    actions_info["get_insights"] = "metaads_actions"
    actions_info["meta_create_ad_set"] = "metaads_actions"
    actions_info["meta_create_campaign"] = "metaads_actions"
    actions_info["meta_get_campaign_metrics"] = "metaads_actions"
    actions_info["meta_update_budget_and_schedule"] = "metaads_actions"
    actions_info["meta_upload_creatives"] = "metaads_actions"
    actions_info["metaads_create_ad"] = "metaads_actions"
    actions_info["metaads_create_ad_creative"] = "metaads_actions"
    actions_info["metaads_create_ad_set"] = "metaads_actions"
    actions_info["metaads_create_campaign"] = "metaads_actions"
    actions_info["metaads_create_custom_audience"] = "metaads_actions"
    actions_info["metaads_delete_ad"] = "metaads_actions"
    actions_info["metaads_delete_ad_set"] = "metaads_actions"
    actions_info["metaads_delete_campaign"] = "metaads_actions"
    actions_info["metaads_get_account_insights"] = "metaads_actions"
    actions_info["metaads_get_ad_details"] = "metaads_actions"
    actions_info["metaads_get_ad_preview"] = "metaads_actions"
    actions_info["metaads_get_ad_set_details"] = "metaads_actions"
    actions_info["metaads_get_ad_set_insights"] = "metaads_actions"
    actions_info["metaads_get_audience_insights"] = "metaads_actions"
    actions_info["metaads_get_business_details"] = "metaads_actions"
    actions_info["metaads_get_campaign_details"] = "metaads_actions"
    actions_info["metaads_get_campaign_insights"] = "metaads_actions"
    actions_info["metaads_get_page_engagement"] = "metaads_actions"
    actions_info["metaads_get_pixel_events"] = "metaads_actions"
    actions_info["metaads_list_campaigns"] = "metaads_actions"
    actions_info["metaads_list_custom_audiences"] = "metaads_actions"
    actions_info["metaads_list_owned_pages"] = "metaads_actions"
    actions_info["metaads_pause_ad"] = "metaads_actions"
    actions_info["metaads_pause_ad_set"] = "metaads_actions"
    actions_info["metaads_pause_campaign"] = "metaads_actions"
    actions_info["metaads_pause_entity"] = "metaads_actions"
    actions_info["metaads_update_ad"] = "metaads_actions"
    actions_info["metaads_update_ad_set"] = "metaads_actions"
    actions_info["metaads_update_campaign"] = "metaads_actions"
    actions_info["metaads_update_page_settings"] = "metaads_actions"
    actions_info["notion_add_users_to_page"] = "notion_actions"
    actions_info["notion_append_text_block_to_page"] = "notion_actions"
    actions_info["notion_archive_page"] = "notion_actions"
    actions_info["notion_create_database"] = "notion_actions"
    actions_info["notion_create_page"] = "notion_actions"
    actions_info["notion_create_page_in_database"] = "notion_actions"
    actions_info["notion_delete_block"] = "notion_actions"
    actions_info["notion_error_handler"] = "notion_actions"
    actions_info["notion_find_database_by_name"] = "notion_actions"
    actions_info["notion_get_block"] = "notion_actions"
    actions_info["notion_get_database"] = "notion_actions"
    actions_info["notion_get_page_content"] = "notion_actions"
    actions_info["notion_query_database"] = "notion_actions"
    actions_info["notion_retrieve_page"] = "notion_actions"
    actions_info["notion_search_general"] = "notion_actions"
    actions_info["notion_update_block"] = "notion_actions"
    actions_info["notion_update_page"] = "notion_actions"
    actions_info["agregar_filas_tabla_excel"] = "office_actions"
    actions_info["crear_documento_word"] = "office_actions"
    actions_info["crear_libro_excel"] = "office_actions"
    actions_info["crear_tabla_excel"] = "office_actions"
    actions_info["escribir_celda_excel"] = "office_actions"
    actions_info["leer_celda_excel"] = "office_actions"
    actions_info["obtener_documento_word_binario"] = "office_actions"
    actions_info["reemplazar_contenido_word"] = "office_actions"
    actions_info["copy_item"] = "onedrive_actions"
    actions_info["create_folder"] = "onedrive_actions"
    actions_info["delete_item"] = "onedrive_actions"
    actions_info["download_file"] = "onedrive_actions"
    actions_info["get_item"] = "onedrive_actions"
    actions_info["get_sharing_link"] = "onedrive_actions"
    actions_info["list_items"] = "onedrive_actions"
    actions_info["move_item"] = "onedrive_actions"
    actions_info["onedrive_create_folder_structure"] = "onedrive_actions"
    actions_info["onedrive_get_file_versions"] = "onedrive_actions"
    actions_info["onedrive_get_storage_quota"] = "onedrive_actions"
    actions_info["onedrive_set_file_permissions"] = "onedrive_actions"
    actions_info["search_items"] = "onedrive_actions"
    actions_info["update_item_metadata"] = "onedrive_actions"
    actions_info["upload_file"] = "onedrive_actions"
    actions_info["chat_completion"] = "openai_actions"
    actions_info["completion"] = "openai_actions"
    actions_info["get_embedding"] = "openai_actions"
    actions_info["list_models"] = "openai_actions"
    actions_info["create_bucket"] = "planner_actions"
    actions_info["create_task"] = "planner_actions"
    actions_info["delete_task"] = "planner_actions"
    actions_info["get_plan"] = "planner_actions"
    actions_info["get_task"] = "planner_actions"
    actions_info["list_buckets"] = "planner_actions"
    actions_info["list_plans"] = "planner_actions"
    actions_info["list_tasks"] = "planner_actions"
    actions_info["planner_assign_task_to_user"] = "planner_actions"
    actions_info["planner_create_task_checklist"] = "planner_actions"
    actions_info["planner_get_plan_by_name"] = "planner_actions"
    actions_info["planner_get_plan_categories"] = "planner_actions"
    actions_info["update_task"] = "planner_actions"
    actions_info["pa_create_or_update_flow"] = "power_automate_actions"
    actions_info["pa_delete_flow"] = "power_automate_actions"
    actions_info["pa_get_flow"] = "power_automate_actions"
    actions_info["pa_get_flow_run_details"] = "power_automate_actions"
    actions_info["pa_get_flow_run_history"] = "power_automate_actions"
    actions_info["pa_list_flows"] = "power_automate_actions"
    actions_info["pa_run_flow_trigger"] = "power_automate_actions"
    actions_info["export_report"] = "powerbi_actions"
    actions_info["list_dashboards"] = "powerbi_actions"
    actions_info["list_datasets"] = "powerbi_actions"
    actions_info["list_reports"] = "powerbi_actions"
    actions_info["refresh_dataset"] = "powerbi_actions"
    actions_info["clear_resolution_cache"] = "resolver_actions"
    actions_info["execute_workflow"] = "resolver_actions"
    actions_info["get_credentials_from_vault"] = "resolver_actions"
    actions_info["get_resolution_analytics"] = "resolver_actions"
    actions_info["get_resource_config"] = "resolver_actions"
    actions_info["list_available_resources"] = "resolver_actions"
    actions_info["resolve_contextual_action"] = "resolver_actions"
    actions_info["resolve_dynamic_query"] = "resolver_actions"
    actions_info["resolve_resource"] = "resolver_actions"
    actions_info["resolve_smart_workflow"] = "resolver_actions"
    actions_info["save_to_notion_registry"] = "resolver_actions"
    actions_info["search_resources"] = "resolver_actions"
    actions_info["smart_save_resource"] = "resolver_actions"
    actions_info["validate_resource_id"] = "resolver_actions"
    actions_info["runway_batch_generate"] = "runway_actions"
    actions_info["runway_cancel_task"] = "runway_actions"
    actions_info["runway_estimate_cost"] = "runway_actions"
    actions_info["runway_generate_image"] = "runway_actions"
    actions_info["runway_generate_video"] = "runway_actions"
    actions_info["runway_generate_video_from_multiple_images"] = "runway_actions"
    actions_info["runway_generate_video_from_text"] = "runway_actions"
    actions_info["runway_get_result_url"] = "runway_actions"
    actions_info["runway_get_task_history"] = "runway_actions"
    actions_info["runway_get_video_status"] = "runway_actions"
    actions_info["runway_list_models"] = "runway_actions"
    actions_info["runway_wait_and_save"] = "runway_actions"
    actions_info["runway_generate_video_advanced"] = "runway_enhanced"
    actions_info["runway_image_to_video_pro"] = "runway_enhanced"
    actions_info["runway_model_training_custom"] = "runway_enhanced"
    actions_info["runway_text_to_video_studio"] = "runway_enhanced"
    actions_info["runway_video_editing_suite"] = "runway_enhanced"
    actions_info["add_item_permissions"] = "sharepoint_actions"
    actions_info["add_list_item"] = "sharepoint_actions"
    actions_info["copy_item"] = "sharepoint_actions"
    actions_info["create_folder"] = "sharepoint_actions"
    actions_info["create_list"] = "sharepoint_actions"
    actions_info["delete_document"] = "sharepoint_actions"
    actions_info["delete_item"] = "sharepoint_actions"
    actions_info["delete_list"] = "sharepoint_actions"
    actions_info["delete_list_item"] = "sharepoint_actions"
    actions_info["download_document"] = "sharepoint_actions"
    actions_info["get_file_metadata"] = "sharepoint_actions"
    actions_info["get_list"] = "sharepoint_actions"
    actions_info["get_list_item"] = "sharepoint_actions"
    actions_info["get_sharing_link"] = "sharepoint_actions"
    actions_info["get_site_info"] = "sharepoint_actions"
    actions_info["list_document_libraries"] = "sharepoint_actions"
    actions_info["list_folder_contents"] = "sharepoint_actions"
    actions_info["list_item_permissions"] = "sharepoint_actions"
    actions_info["list_list_items"] = "sharepoint_actions"
    actions_info["list_lists"] = "sharepoint_actions"
    actions_info["memory_delete"] = "sharepoint_actions"
    actions_info["memory_ensure_list"] = "sharepoint_actions"
    actions_info["memory_export_session"] = "sharepoint_actions"
    actions_info["memory_get"] = "sharepoint_actions"
    actions_info["memory_list_keys"] = "sharepoint_actions"
    actions_info["memory_save"] = "sharepoint_actions"
    actions_info["move_item"] = "sharepoint_actions"
    actions_info["remove_item_permissions"] = "sharepoint_actions"
    actions_info["search_list_items"] = "sharepoint_actions"
    actions_info["search_sites"] = "sharepoint_actions"
    actions_info["sp_add_item_permissions"] = "sharepoint_actions"
    actions_info["sp_add_list_item"] = "sharepoint_actions"
    actions_info["sp_copy_item"] = "sharepoint_actions"
    actions_info["sp_create_folder"] = "sharepoint_actions"
    actions_info["sp_create_list"] = "sharepoint_actions"
    actions_info["sp_delete_document"] = "sharepoint_actions"
    actions_info["sp_delete_item"] = "sharepoint_actions"
    actions_info["sp_delete_list"] = "sharepoint_actions"
    actions_info["sp_delete_list_item"] = "sharepoint_actions"
    actions_info["sp_download_document"] = "sharepoint_actions"
    actions_info["sp_export_list_to_format"] = "sharepoint_actions"
    actions_info["sp_get_file_metadata"] = "sharepoint_actions"
    actions_info["sp_get_list"] = "sharepoint_actions"
    actions_info["sp_get_list_item"] = "sharepoint_actions"
    actions_info["sp_get_sharing_link"] = "sharepoint_actions"
    actions_info["sp_get_site_info"] = "sharepoint_actions"
    actions_info["sp_list_document_libraries"] = "sharepoint_actions"
    actions_info["sp_list_folder_contents"] = "sharepoint_actions"
    actions_info["sp_list_item_permissions"] = "sharepoint_actions"
    actions_info["sp_list_list_items"] = "sharepoint_actions"
    actions_info["sp_list_lists"] = "sharepoint_actions"
    actions_info["sp_memory_delete"] = "sharepoint_actions"
    actions_info["sp_memory_ensure_list"] = "sharepoint_actions"
    actions_info["sp_memory_export_session"] = "sharepoint_actions"
    actions_info["sp_memory_get"] = "sharepoint_actions"
    actions_info["sp_memory_list_keys"] = "sharepoint_actions"
    actions_info["sp_memory_save"] = "sharepoint_actions"
    actions_info["sp_move_item"] = "sharepoint_actions"
    actions_info["sp_remove_item_permissions"] = "sharepoint_actions"
    actions_info["sp_search_list_items"] = "sharepoint_actions"
    actions_info["sp_search_sites"] = "sharepoint_actions"
    actions_info["sp_update_file_metadata"] = "sharepoint_actions"
    actions_info["sp_update_list"] = "sharepoint_actions"
    actions_info["sp_update_list_item"] = "sharepoint_actions"
    actions_info["sp_upload_document"] = "sharepoint_actions"
    actions_info["update_file_metadata"] = "sharepoint_actions"
    actions_info["update_list"] = "sharepoint_actions"
    actions_info["update_list_item"] = "sharepoint_actions"
    actions_info["upload_document"] = "sharepoint_actions"
    actions_info["get_video_playback_url"] = "stream_actions"
    actions_info["listar_videos"] = "stream_actions"
    actions_info["obtener_metadatos_video"] = "stream_actions"
    actions_info["obtener_transcripcion_video"] = "stream_actions"
    actions_info["create_chat"] = "teams_actions"
    actions_info["get_channel"] = "teams_actions"
    actions_info["get_chat"] = "teams_actions"
    actions_info["get_meeting_details"] = "teams_actions"
    actions_info["get_team"] = "teams_actions"
    actions_info["list_channel_messages"] = "teams_actions"
    actions_info["list_channels"] = "teams_actions"
    actions_info["list_chat_messages"] = "teams_actions"
    actions_info["list_chats"] = "teams_actions"
    actions_info["list_joined_teams"] = "teams_actions"
    actions_info["list_members"] = "teams_actions"
    actions_info["reply_to_message"] = "teams_actions"
    actions_info["schedule_meeting"] = "teams_actions"
    actions_info["send_channel_message"] = "teams_actions"
    actions_info["send_chat_message"] = "teams_actions"
    actions_info["teams_create_team_channel"] = "teams_actions"
    actions_info["teams_create_team_meeting"] = "teams_actions"
    actions_info["teams_get_channel_tabs"] = "teams_actions"
    actions_info["teams_get_team_apps"] = "teams_actions"
    actions_info["teams_get_team_by_name"] = "teams_actions"
    actions_info["tiktok_create_ad"] = "tiktok_ads_actions"
    actions_info["tiktok_create_ad_group"] = "tiktok_ads_actions"
    actions_info["tiktok_create_campaign"] = "tiktok_ads_actions"
    actions_info["tiktok_get_ad_accounts"] = "tiktok_ads_actions"
    actions_info["tiktok_get_analytics_report"] = "tiktok_ads_actions"
    actions_info["tiktok_get_campaigns"] = "tiktok_ads_actions"
    actions_info["tiktok_update_campaign_status"] = "tiktok_ads_actions"
    actions_info["tiktok_audience_growth_suite"] = "tiktok_enhanced"
    actions_info["tiktok_campaign_automation_pro"] = "tiktok_enhanced"
    actions_info["tiktok_post_advanced_video"] = "tiktok_enhanced"
    actions_info["tiktok_trending_analytics_pro"] = "tiktok_enhanced"
    actions_info["tiktok_viral_content_factory"] = "tiktok_enhanced"
    actions_info["create_task"] = "todo_actions"
    actions_info["create_task_list"] = "todo_actions"
    actions_info["delete_task"] = "todo_actions"
    actions_info["get_task"] = "todo_actions"
    actions_info["list_task_lists"] = "todo_actions"
    actions_info["list_tasks"] = "todo_actions"
    actions_info["update_task"] = "todo_actions"
    actions_info["profile_get_my_direct_reports"] = "userprofile_actions"
    actions_info["profile_get_my_manager"] = "userprofile_actions"
    actions_info["profile_get_my_photo"] = "userprofile_actions"
    actions_info["profile_get_my_profile"] = "userprofile_actions"
    actions_info["profile_update_my_profile"] = "userprofile_actions"
    actions_info["add_group_member"] = "users_actions"
    actions_info["check_group_membership"] = "users_actions"
    actions_info["create_user"] = "users_actions"
    actions_info["delete_user"] = "users_actions"
    actions_info["get_group"] = "users_actions"
    actions_info["get_user"] = "users_actions"
    actions_info["list_group_members"] = "users_actions"
    actions_info["list_groups"] = "users_actions"
    actions_info["list_users"] = "users_actions"
    actions_info["remove_group_member"] = "users_actions"
    actions_info["update_user"] = "users_actions"
    actions_info["get_focus_plan"] = "vivainsights_actions"
    actions_info["get_my_analytics"] = "vivainsights_actions"
    actions_info["batch_url_analysis"] = "webresearch_actions"
    actions_info["check_url_status"] = "webresearch_actions"
    actions_info["extract_text_from_url"] = "webresearch_actions"
    actions_info["fetch_url"] = "webresearch_actions"
    actions_info["monitor_website_changes"] = "webresearch_actions"
    actions_info["scrape_website_data"] = "webresearch_actions"
    actions_info["search_web"] = "webresearch_actions"
    actions_info["webresearch_extract_emails"] = "webresearch_actions"
    actions_info["webresearch_extract_phone_numbers"] = "webresearch_actions"
    actions_info["webresearch_scrape_url"] = "webresearch_actions"
    actions_info["webresearch_search_web"] = "webresearch_actions"
    actions_info["whatsapp_broadcast_segment"] = "whatsapp_actions"
    actions_info["whatsapp_close_ticket"] = "whatsapp_actions"
    actions_info["whatsapp_create_template"] = "whatsapp_actions"
    actions_info["whatsapp_download_media"] = "whatsapp_actions"
    actions_info["whatsapp_get_media"] = "whatsapp_actions"
    actions_info["whatsapp_get_message_status"] = "whatsapp_actions"
    actions_info["whatsapp_handover_to_human"] = "whatsapp_actions"
    actions_info["whatsapp_list_templates"] = "whatsapp_actions"
    actions_info["whatsapp_mark_read"] = "whatsapp_actions"
    actions_info["whatsapp_send_interactive"] = "whatsapp_actions"
    actions_info["whatsapp_send_media"] = "whatsapp_actions"
    actions_info["whatsapp_send_template"] = "whatsapp_actions"
    actions_info["whatsapp_send_text"] = "whatsapp_actions"
    actions_info["whatsapp_upload_media"] = "whatsapp_actions"
    actions_info["woocommerce_create_customer"] = "wordpress_actions"
    actions_info["woocommerce_create_order"] = "wordpress_actions"
    actions_info["woocommerce_create_product"] = "wordpress_actions"
    actions_info["woocommerce_get_customers"] = "wordpress_actions"
    actions_info["woocommerce_get_orders"] = "wordpress_actions"
    actions_info["woocommerce_get_orders_by_customer"] = "wordpress_actions"
    actions_info["woocommerce_get_product_categories"] = "wordpress_actions"
    actions_info["woocommerce_get_products"] = "wordpress_actions"
    actions_info["woocommerce_get_reports"] = "wordpress_actions"
    actions_info["woocommerce_update_order_status"] = "wordpress_actions"
    actions_info["woocommerce_update_product"] = "wordpress_actions"
    actions_info["wordpress_backup_content"] = "wordpress_actions"
    actions_info["wordpress_create_category"] = "wordpress_actions"
    actions_info["wordpress_create_page"] = "wordpress_actions"
    actions_info["wordpress_create_post"] = "wordpress_actions"
    actions_info["wordpress_create_user"] = "wordpress_actions"
    actions_info["wordpress_delete_post"] = "wordpress_actions"
    actions_info["wordpress_get_categories"] = "wordpress_actions"
    actions_info["wordpress_get_pages"] = "wordpress_actions"
    actions_info["wordpress_get_post"] = "wordpress_actions"
    actions_info["wordpress_get_posts"] = "wordpress_actions"
    actions_info["wordpress_get_tags"] = "wordpress_actions"
    actions_info["wordpress_get_users"] = "wordpress_actions"
    actions_info["wordpress_update_post"] = "wordpress_actions"
    actions_info["wordpress_upload_media"] = "wordpress_actions"
    actions_info["wordpress_backup_and_restore"] = "wordpress_enhanced"
    actions_info["wordpress_create_advanced_post"] = "wordpress_enhanced"
    actions_info["wordpress_manage_plugins_advanced"] = "wordpress_enhanced"
    actions_info["wordpress_manage_users_advanced"] = "wordpress_enhanced"
    actions_info["wordpress_optimize_performance"] = "wordpress_enhanced"
    actions_info["x_ads_create_campaign"] = "x_ads_actions"
    actions_info["x_ads_delete_campaign"] = "x_ads_actions"
    actions_info["x_ads_get_analytics"] = "x_ads_actions"
    actions_info["x_ads_get_campaigns"] = "x_ads_actions"
    actions_info["x_ads_update_campaign"] = "x_ads_actions"
    actions_info["x_audience_analytics_pro"] = "x_enhanced"
    actions_info["x_campaign_management_suite"] = "x_enhanced"
    actions_info["x_community_management_pro"] = "x_enhanced"
    actions_info["x_post_advanced_tweet"] = "x_enhanced"
    actions_info["x_viral_content_optimizer"] = "x_enhanced"
    actions_info["validate_date_format"] = "youtube_channel_actions"
    actions_info["youtube_add_video_to_playlist"] = "youtube_channel_actions"
    actions_info["youtube_bulk_upload_from_folder"] = "youtube_channel_actions"
    actions_info["youtube_create_playlist"] = "youtube_channel_actions"
    actions_info["youtube_delete_video"] = "youtube_channel_actions"
    actions_info["youtube_get_analytics"] = "youtube_channel_actions"
    actions_info["youtube_get_audience_demographics"] = "youtube_channel_actions"
    actions_info["youtube_get_channel_analytics"] = "youtube_channel_actions"
    actions_info["youtube_get_channel_info"] = "youtube_channel_actions"
    actions_info["youtube_get_video_analytics"] = "youtube_channel_actions"
    actions_info["youtube_get_video_comments"] = "youtube_channel_actions"
    actions_info["youtube_list_channel_videos"] = "youtube_channel_actions"
    actions_info["youtube_list_videos_in_playlist"] = "youtube_channel_actions"
    actions_info["youtube_manage_comments"] = "youtube_channel_actions"
    actions_info["youtube_moderate_comment"] = "youtube_channel_actions"
    actions_info["youtube_reply_to_comment"] = "youtube_channel_actions"
    actions_info["youtube_schedule_video"] = "youtube_channel_actions"
    actions_info["youtube_set_video_thumbnail"] = "youtube_channel_actions"
    actions_info["youtube_update_video_metadata"] = "youtube_channel_actions"
    actions_info["youtube_upload_video"] = "youtube_channel_actions"

    return actions_info

def execute_action(action_name: str, client: Any, params: Dict[str, Any]) -> Any:
    """Ejecutar una acción específica de manera segura"""
    if action_name not in ACTION_MAP:
        available_actions = list(ACTION_MAP.keys())
        raise ValueError(f"Acción '{action_name}' no encontrada. Acciones disponibles: {len(available_actions)}")
    
    try:
        action_func = ACTION_MAP[action_name]
        logger.info(f"Ejecutando acción: {action_name}")
        result = action_func(client, params)
        logger.info(f"Acción {action_name} ejecutada exitosamente")
        return result
    except Exception as e:
        logger.error(f"Error ejecutando acción {action_name}: {e}")
        raise

def list_actions_by_category() -> Dict[str, list]:
    """Listar acciones agrupadas por categoría"""
    categories = {}
    actions_info = get_available_actions()
    
    for action, module in actions_info.items():
        category = module.replace('_actions', '').upper()
        if category not in categories:
            categories[category] = []
        categories[category].append(action)
    
    return categories

# ============================================================================
# WORKFLOW FUNCTIONS (placeholder para compatibilidad)
# ============================================================================

def workflow_execute_backup_completo(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Ejecutar workflow de backup completo"""
    # Esta función será implementada cuando los workflows estén listos
    return {"status": "workflow_placeholder", "message": "Workflow functions pendientes de implementación"}

def workflow_list_available(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Listar workflows disponibles"""
    return {"workflows": ["backup_completo", "sync_marketing", "content_creation", "youtube_pipeline", "client_onboarding"]}

# Agregar funciones de workflow al ACTION_MAP
ACTION_MAP.update({
    "workflow_execute_backup_completo": workflow_execute_backup_completo,
    "workflow_list_available": workflow_list_available,
})

# Actualizar contador
TOTAL_ACTIONS += 2
