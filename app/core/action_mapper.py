# app/core/action_mapper.py
import logging
from app.actions import (
    azuremgmt_actions, bookings_actions, calendario_actions, correo_actions,
    forms_actions, github_actions, googleads_actions, graph_actions,
    hubspot_actions, linkedin_ads_actions, metaads_actions, notion_actions,
    office_actions, onedrive_actions, openai_actions, planner_actions,
    power_automate_actions, powerbi_actions, sharepoint_actions,
    stream_actions, teams_actions, tiktok_ads_actions, todo_actions,
    userprofile_actions, users_actions, vivainsights_actions,
    youtube_channel_actions, gemini_actions
)

logger = logging.getLogger(__name__)

ACTION_MAP = {

    # --- Azure Management Actions ---
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

    # --- Bookings Actions ---
    "bookings_list_businesses": bookings_actions.list_businesses,
    "bookings_get_business": bookings_actions.get_business,
    "bookings_list_services": bookings_actions.list_services,
    "bookings_list_staff": bookings_actions.list_staff,
    "bookings_create_appointment": bookings_actions.create_appointment,
    "bookings_get_appointment": bookings_actions.get_appointment,
    "bookings_cancel_appointment": bookings_actions.cancel_appointment,
    "bookings_list_appointments": bookings_actions.list_appointments,

    # --- Calendario Actions ---
    "calendar_list_events": calendario_actions.calendar_list_events,
    "calendar_create_event": calendario_actions.calendar_create_event,
    "calendar_get_event": calendario_actions.get_event,
    "calendar_update_event": calendario_actions.update_event,
    "calendar_delete_event": calendario_actions.delete_event,
    "calendar_find_meeting_times": calendario_actions.find_meeting_times,
    "calendar_get_schedule": calendario_actions.get_schedule,

    # --- Correo Actions ---
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

    # --- Forms Actions ---
    "forms_list_forms": forms_actions.list_forms,
    "forms_get_form": forms_actions.get_form,
    "forms_get_form_responses": forms_actions.get_form_responses,

    # --- Gemini Actions ---
    "gemini_simple_text_prompt": gemini_actions.gemini_simple_text_prompt,

    # --- GitHub Actions ---
    "github_list_repos": github_actions.github_list_repos,
    "github_create_issue": github_actions.github_create_issue,
    "github_get_repo_details": github_actions.github_get_repo_details,
    
    # --- Google Ads Actions ---
    "googleads_get_campaigns": googleads_actions.googleads_get_campaigns,
    "googleads_create_campaign": googleads_actions.googleads_create_campaign,
    "googleads_get_ad_groups": googleads_actions.googleads_get_ad_groups,

    # --- Graph Actions (Genéricas) ---
    "graph_generic_get": graph_actions.generic_get,
    "graph_generic_post": graph_actions.generic_post,
    
    # --- HubSpot CRM Actions ---
    "hubspot_get_contacts": hubspot_actions.hubspot_get_contacts,
    "hubspot_create_contact": hubspot_actions.hubspot_create_contact,
    "hubspot_update_contact": hubspot_actions.hubspot_update_contact,
    "hubspot_delete_contact": hubspot_actions.hubspot_delete_contact,
    "hubspot_get_deals": hubspot_actions.hubspot_get_deals,
    "hubspot_create_deal": hubspot_actions.hubspot_create_deal,
    "hubspot_update_deal": hubspot_actions.hubspot_update_deal,
    "hubspot_delete_deal": hubspot_actions.hubspot_delete_deal,

    # --- LinkedIn Ads Actions ---
    "linkedin_find_ad_accounts": linkedin_ads_actions.linkedin_find_ad_accounts,
    "linkedin_get_campaigns": linkedin_ads_actions.linkedin_get_campaigns,
    "linkedin_get_campaign_groups": linkedin_ads_actions.linkedin_get_campaign_groups,
    "linkedin_get_analytics": linkedin_ads_actions.linkedin_get_analytics,

    # --- Meta Ads Actions ---
    "metaads_get_business_details": metaads_actions.metaads_get_business_details,
    "metaads_list_owned_pages": metaads_actions.metaads_list_owned_pages,
    "metaads_get_page_engagement": metaads_actions.metaads_get_page_engagement,
    "metaads_list_campaigns": metaads_actions.metaads_list_campaigns,
    "metaads_create_campaign": metaads_actions.metaads_create_campaign,
    "metaads_update_campaign": metaads_actions.metaads_update_campaign,
    "metaads_delete_campaign": metaads_actions.metaads_delete_campaign,
    "metaads_get_insights": metaads_actions.metaads_get_insights,

    # --- Notion Actions ---
    "notion_search_general": notion_actions.notion_search_general,
    "notion_get_database": notion_actions.notion_get_database,
    "notion_query_database": notion_actions.notion_query_database,
    "notion_retrieve_page": notion_actions.notion_retrieve_page,
    "notion_create_page": notion_actions.notion_create_page,
    "notion_update_page": notion_actions.notion_update_page,
    "notion_delete_block": notion_actions.notion_delete_block,

    # --- Office Actions ---
    "office_crear_documento_word": office_actions.crear_documento_word,
    "office_reemplazar_contenido_word": office_actions.reemplazar_contenido_word,
    "office_obtener_documento_word_binario": office_actions.obtener_documento_word_binario,
    "office_crear_libro_excel": office_actions.crear_libro_excel,
    "office_leer_celda_excel": office_actions.leer_celda_excel,
    "office_escribir_celda_excel": office_actions.escribir_celda_excel,
    "office_crear_tabla_excel": office_actions.crear_tabla_excel,
    "office_agregar_filas_tabla_excel": office_actions.agregar_filas_tabla_excel,

    # --- OneDrive Actions ---
    "onedrive_list_items": onedrive_actions.list_items,
    "onedrive_get_item": onedrive_actions.get_item,
    "onedrive_upload_file": onedrive_actions.upload_file,
    "onedrive_download_file": onedrive_actions.download_file,
    "onedrive_delete_item": onedrive_actions.delete_item,
    "onedrive_create_folder": onedrive_actions.create_folder,
    "onedrive_move_item": onedrive_actions.move_item,
    "onedrive_copy_item": onedrive_actions.copy_item,
    "onedrive_search_items": onedrive_actions.search_items,
    "onedrive_get_sharing_link": onedrive_actions.get_sharing_link,
    "onedrive_update_item_metadata": onedrive_actions.update_item_metadata,

    # --- Azure OpenAI Actions ---
    "openai_chat_completion": openai_actions.chat_completion,
    "openai_completion": openai_actions.completion,
    "openai_get_embedding": openai_actions.get_embedding,
    "openai_list_models": openai_actions.list_models,

    # --- Planner Actions ---
    "planner_list_plans": planner_actions.list_plans,
    "planner_get_plan": planner_actions.get_plan,
    "planner_list_tasks": planner_actions.list_tasks,
    "planner_create_task": planner_actions.create_task,
    "planner_get_task": planner_actions.get_task,
    "planner_update_task": planner_actions.update_task,
    "planner_delete_task": planner_actions.delete_task,
    "planner_list_buckets": planner_actions.list_buckets,
    "planner_create_bucket": planner_actions.create_bucket,

    # --- Power Automate Actions ---
    "pa_list_flows": power_automate_actions.pa_list_flows,
    "pa_get_flow": power_automate_actions.pa_get_flow,
    "pa_create_or_update_flow": power_automate_actions.pa_create_or_update_flow,
    "pa_delete_flow": power_automate_actions.pa_delete_flow,
    "pa_run_flow_trigger": power_automate_actions.pa_run_flow_trigger,
    "pa_get_flow_run_history": power_automate_actions.pa_get_flow_run_history,
    "pa_get_flow_run_details": power_automate_actions.pa_get_flow_run_details,

    # --- Power BI Actions ---
    "powerbi_list_reports": powerbi_actions.list_reports,
    "powerbi_export_report": powerbi_actions.export_report,
    "powerbi_list_dashboards": powerbi_actions.list_dashboards,
    "powerbi_list_datasets": powerbi_actions.list_datasets,
    "powerbi_refresh_dataset": powerbi_actions.refresh_dataset,

    # --- SharePoint Actions ---
    "sp_list_lists": sharepoint_actions.list_lists,
    "sp_get_list": sharepoint_actions.get_list,
    "sp_create_list": sharepoint_actions.create_list,
    "sp_update_list": sharepoint_actions.update_list,
    "sp_delete_list": sharepoint_actions.delete_list,
    "sp_list_list_items": sharepoint_actions.list_list_items,
    "sp_get_list_item": sharepoint_actions.get_list_item,
    "sp_add_list_item": sharepoint_actions.add_list_item,
    "sp_update_list_item": sharepoint_actions.update_list_item,
    "sp_delete_list_item": sharepoint_actions.delete_list_item,
    "sp_search_list_items": sharepoint_actions.search_list_items,
    "sp_list_document_libraries": sharepoint_actions.list_document_libraries,
    "sp_list_folder_contents": sharepoint_actions.list_folder_contents,
    "sp_get_file_metadata": sharepoint_actions.get_file_metadata,
    "sp_upload_document": sharepoint_actions.upload_document,
    "sp_download_document": sharepoint_actions.download_document,
    "sp_delete_document": sharepoint_actions.delete_document, 
    "sp_delete_item": sharepoint_actions.delete_item,
    "sp_create_folder": sharepoint_actions.create_folder,
    "sp_move_item": sharepoint_actions.move_item,
    "sp_copy_item": sharepoint_actions.copy_item,
    "sp_update_file_metadata": sharepoint_actions.update_file_metadata,
    "sp_get_site_info": sharepoint_actions.get_site_info,
    "sp_search_sites": sharepoint_actions.search_sites,
    "sp_memory_ensure_list": sharepoint_actions.memory_ensure_list,
    "sp_memory_save": sharepoint_actions.memory_save,
    "sp_memory_get": sharepoint_actions.memory_get,
    "sp_memory_delete": sharepoint_actions.memory_delete,
    "sp_memory_list_keys": sharepoint_actions.memory_list_keys,
    "sp_memory_export_session": sharepoint_actions.memory_export_session,
    "sp_get_sharing_link": sharepoint_actions.get_sharing_link,
    "sp_add_item_permissions": sharepoint_actions.add_item_permissions,
    "sp_remove_item_permissions": sharepoint_actions.remove_item_permissions,
    "sp_list_item_permissions": sharepoint_actions.list_item_permissions,
    "sp_export_list_to_format": sharepoint_actions.sp_export_list_to_format,

    # --- Stream Actions ---
    "stream_get_video_playback_url": stream_actions.get_video_playback_url,
    "stream_listar_videos": stream_actions.listar_videos,
    "stream_obtener_metadatos_video": stream_actions.obtener_metadatos_video,
    "stream_obtener_transcripcion_video": stream_actions.obtener_transcripcion_video,

    # --- Teams Actions ---
    "teams_list_joined_teams": teams_actions.list_joined_teams,
    "teams_get_team": teams_actions.get_team,
    "teams_list_channels": teams_actions.list_channels,
    "teams_get_channel": teams_actions.get_channel,
    "teams_send_channel_message": teams_actions.send_channel_message,
    "teams_list_channel_messages": teams_actions.list_channel_messages,
    "teams_reply_to_message": teams_actions.reply_to_message,
    "teams_send_chat_message": teams_actions.send_chat_message,
    "teams_list_chats": teams_actions.list_chats,
    "teams_get_chat": teams_actions.get_chat,
    "teams_create_chat": teams_actions.create_chat,
    "teams_list_chat_messages": teams_actions.list_chat_messages,
    "teams_schedule_meeting": teams_actions.schedule_meeting,
    "teams_get_meeting_details": teams_actions.get_meeting_details,
    "teams_list_members": teams_actions.list_members,

    # --- TikTok Ads Actions ---
    "tiktok_get_ad_accounts": tiktok_ads_actions.tiktok_get_ad_accounts,
    "tiktok_get_campaigns": tiktok_ads_actions.tiktok_get_campaigns,
    "tiktok_get_analytics_report": tiktok_ads_actions.tiktok_get_analytics_report,

    # --- ToDo Actions ---
    "todo_list_task_lists": todo_actions.list_task_lists,
    "todo_create_task_list": todo_actions.create_task_list,
    "todo_list_tasks": todo_actions.list_tasks,
    "todo_create_task": todo_actions.create_task,
    "todo_get_task": todo_actions.get_task,
    "todo_update_task": todo_actions.update_task,
    "todo_delete_task": todo_actions.delete_task,

    # --- User Profile Actions ---
    "profile_get_my_profile": userprofile_actions.profile_get_my_profile,
    "profile_get_my_manager": userprofile_actions.profile_get_my_manager,
    "profile_get_my_direct_reports": userprofile_actions.profile_get_my_direct_reports,
    "profile_get_my_photo": userprofile_actions.profile_get_my_photo,
    "profile_update_my_profile": userprofile_actions.profile_update_my_profile, 

    # --- Users Actions (Directory) ---
    "user_list_users": users_actions.list_users,
    "user_get_user": users_actions.get_user,
    "user_create_user": users_actions.create_user,
    "user_update_user": users_actions.update_user,
    "user_delete_user": users_actions.delete_user,
    "user_list_groups": users_actions.list_groups,
    "user_get_group": users_actions.get_group,
    "user_list_group_members": users_actions.list_group_members,
    "user_add_group_member": users_actions.add_group_member,
    "user_remove_group_member": users_actions.remove_group_member,
    "user_check_group_membership": users_actions.check_group_membership,

    # --- Viva Insights Actions ---
    "viva_get_my_analytics": vivainsights_actions.get_my_analytics,
    "viva_get_focus_plan": vivainsights_actions.get_focus_plan,
    
    # --- YouTube Channel Actions ---
    "youtube_upload_video": youtube_channel_actions.youtube_upload_video,
    "youtube_update_video_details": youtube_channel_actions.youtube_update_video_details,
    "youtube_list_comments": youtube_channel_actions.youtube_list_comments,
    "youtube_reply_to_comment": youtube_channel_actions.youtube_reply_to_comment,
}

num_actions = len(ACTION_MAP)
logger.info(f"ACTION_MAP cargado y validado. Total de {num_actions} acciones mapeadas y listas para usar.")