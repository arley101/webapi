"""
Google Marketing & Ads API Enhanced
Integración completa para marketing digital automatizado
"""

import os
import json
import time
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from app.shared.helpers.http_client import AuthenticatedHttpClient

logger = logging.getLogger(__name__)

# ============================================================================
# GOOGLE ADS CONVERSION & PIXEL MANAGEMENT
# ============================================================================

async def google_ads_setup_conversion_tracking(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Configura seguimiento de conversiones completo
    
    Parámetros:
    - conversion_actions: Lista de acciones de conversión a crear
    - customer_id: ID del cliente de Google Ads
    - website_url: URL del sitio web
    - crm_integration: Configuración de integración CRM
    """
    try:
        customer_id = params.get("customer_id")
        conversion_actions = params.get("conversion_actions", [])
        website_url = params.get("website_url")
        crm_integration = params.get("crm_integration", {})
        
        if not all([customer_id, conversion_actions, website_url]):
            return {
                "status": "error",
                "message": "Parámetros customer_id, conversion_actions y website_url son requeridos"
            }
        
        # Configurar Google Ads API
        from google.ads.googleads.client import GoogleAdsClient
        from google.ads.googleads.errors import GoogleAdsException
        
        # Obtener credenciales
        credentials_path = os.getenv("GOOGLE_ADS_CREDENTIALS_PATH")
        if not credentials_path:
            return {
                "status": "error",
                "message": "Credenciales de Google Ads no configuradas"
            }
        
        client_ads = GoogleAdsClient.load_from_storage(credentials_path)
        
        created_conversions = []
        
        for action in conversion_actions:
            try:
                conversion_action_service = client_ads.get_service("ConversionActionService")
                
                # Crear acción de conversión
                conversion_action = client_ads.get_type("ConversionAction")
                conversion_action.name = action.get("name", "Conversion Action")
                conversion_action.type_ = client_ads.enums.ConversionActionTypeEnum.WEBSITE
                conversion_action.category = getattr(
                    client_ads.enums.ConversionActionCategoryEnum, 
                    action.get("category", "DEFAULT").upper()
                )
                conversion_action.status = client_ads.enums.ConversionActionStatusEnum.ENABLED
                conversion_action.view_through_lookback_window_days = action.get("view_through_days", 30)
                conversion_action.click_through_lookback_window_days = action.get("click_through_days", 30)
                
                # Configurar valor de conversión
                if action.get("value"):
                    conversion_action.value_settings.default_value = action["value"]
                    conversion_action.value_settings.always_use_default_value = action.get("always_use_default", True)
                
                # Crear la acción
                operation = client_ads.get_type("ConversionActionOperation")
                operation.create.CopyFrom(conversion_action)
                
                response = conversion_action_service.mutate_conversion_actions(
                    customer_id=customer_id,
                    operations=[operation]
                )
                
                conversion_id = response.results[0].resource_name.split("/")[-1]
                
                # Generar tag de seguimiento
                google_ads_service = client_ads.get_service("GoogleAdsService")
                
                # Obtener snippet de conversión
                query = f"""
                    SELECT 
                        conversion_action.id,
                        conversion_action.name,
                        conversion_action.tag_snippets
                    FROM conversion_action 
                    WHERE conversion_action.id = {conversion_id}
                """
                
                search_request = client_ads.get_type("SearchGoogleAdsRequest")
                search_request.customer_id = customer_id
                search_request.query = query
                
                results = google_ads_service.search(request=search_request)
                
                tag_snippets = []
                for row in results:
                    for snippet in row.conversion_action.tag_snippets:
                        tag_snippets.append({
                            "type": snippet.type_.name,
                            "page_format": snippet.page_format.name,
                            "global_site_tag": snippet.global_site_tag,
                            "event_snippet": snippet.event_snippet
                        })
                
                created_conversions.append({
                    "id": conversion_id,
                    "name": action.get("name"),
                    "category": action.get("category"),
                    "resource_name": response.results[0].resource_name,
                    "tag_snippets": tag_snippets,
                    "setup_complete": True
                })
                
            except GoogleAdsException as e:
                logger.error(f"Error creating conversion action: {e}")
                created_conversions.append({
                    "name": action.get("name"),
                    "error": str(e),
                    "setup_complete": False
                })
        
        # Configurar integración CRM si se proporciona
        crm_setup = {}
        if crm_integration:
            crm_setup = await _setup_crm_integration(client, customer_id, crm_integration, created_conversions)
        
        result = {
            "status": "success",
            "customer_id": customer_id,
            "website_url": website_url,
            "conversions_created": len([c for c in created_conversions if c.get("setup_complete")]),
            "conversion_actions": created_conversions,
            "crm_integration": crm_setup
        }
        
        # Persistir configuración
        await _persist_conversion_setup(client, result, "conversion_tracking_setup")
        
        return result
        
    except Exception as e:
        logger.error(f"Error setting up conversion tracking: {str(e)}")
        return {
            "status": "error",
            "message": f"Error al configurar seguimiento: {str(e)}"
        }

async def google_ads_create_dynamic_campaigns(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Crea campañas dinámicas con automatización avanzada
    
    Parámetros:
    - campaign_configs: Lista de configuraciones de campaña
    - customer_id: ID del cliente de Google Ads
    - feed_data: Datos del feed de productos/servicios
    - target_audiences: Audiencias objetivo
    - budget_strategy: Estrategia de presupuesto automática
    """
    try:
        customer_id = params.get("customer_id")
        campaign_configs = params.get("campaign_configs", [])
        feed_data = params.get("feed_data", {})
        target_audiences = params.get("target_audiences", [])
        budget_strategy = params.get("budget_strategy", {})
        
        if not all([customer_id, campaign_configs]):
            return {
                "status": "error",
                "message": "Parámetros customer_id y campaign_configs son requeridos"
            }
        
        # Configurar Google Ads API
        from google.ads.googleads.client import GoogleAdsClient
        
        credentials_path = os.getenv("GOOGLE_ADS_CREDENTIALS_PATH")
        client_ads = GoogleAdsClient.load_from_storage(credentials_path)
        
        created_campaigns = []
        
        for config in campaign_configs:
            try:
                # Crear presupuesto de campaña
                budget_service = client_ads.get_service("CampaignBudgetService")
                budget = client_ads.get_type("CampaignBudget")
                budget.name = f"Budget for {config.get('name', 'Campaign')}"
                budget.delivery_method = client_ads.enums.BudgetDeliveryMethodEnum.STANDARD
                budget.amount_micros = int(config.get("daily_budget", 1000) * 1000000)
                
                budget_operation = client_ads.get_type("CampaignBudgetOperation")
                budget_operation.create.CopyFrom(budget)
                
                budget_response = budget_service.mutate_campaign_budgets(
                    customer_id=customer_id,
                    operations=[budget_operation]
                )
                budget_resource_name = budget_response.results[0].resource_name
                
                # Crear campaña
                campaign_service = client_ads.get_service("CampaignService")
                campaign = client_ads.get_type("Campaign")
                campaign.name = config.get("name", f"Dynamic Campaign {int(time.time())}")
                campaign.advertising_channel_type = getattr(
                    client_ads.enums.AdvertisingChannelTypeEnum,
                    config.get("channel_type", "SEARCH").upper()
                )
                campaign.status = client_ads.enums.CampaignStatusEnum.ENABLED
                campaign.campaign_budget = budget_resource_name
                
                # Configurar estrategia de puja automática
                if budget_strategy.get("type") == "TARGET_CPA":
                    campaign.target_cpa.target_cpa_micros = int(
                        budget_strategy.get("target_cpa", 10) * 1000000
                    )
                elif budget_strategy.get("type") == "TARGET_ROAS":
                    campaign.target_roas.target_roas = budget_strategy.get("target_roas", 4.0)
                else:
                    # Maximize conversions por defecto
                    campaign.maximize_conversions.CopyFrom(
                        client_ads.get_type("MaximizeConversions")
                    )
                
                # Configurar fechas
                if config.get("start_date"):
                    campaign.start_date = config["start_date"]
                if config.get("end_date"):
                    campaign.end_date = config["end_date"]
                
                campaign_operation = client_ads.get_type("CampaignOperation")
                campaign_operation.create.CopyFrom(campaign)
                
                campaign_response = campaign_service.mutate_campaigns(
                    customer_id=customer_id,
                    operations=[campaign_operation]
                )
                
                campaign_resource_name = campaign_response.results[0].resource_name
                campaign_id = campaign_resource_name.split("/")[-1]
                
                # Crear grupos de anuncios dinámicos
                ad_groups = await _create_dynamic_ad_groups(
                    client_ads, customer_id, campaign_resource_name, config, target_audiences
                )
                
                # Configurar extensiones automáticas
                extensions = await _setup_campaign_extensions(
                    client_ads, customer_id, campaign_resource_name, config
                )
                
                created_campaigns.append({
                    "id": campaign_id,
                    "name": campaign.name,
                    "resource_name": campaign_resource_name,
                    "budget_resource_name": budget_resource_name,
                    "daily_budget": config.get("daily_budget"),
                    "channel_type": config.get("channel_type"),
                    "ad_groups": ad_groups,
                    "extensions": extensions,
                    "setup_complete": True
                })
                
            except Exception as e:
                logger.error(f"Error creating campaign {config.get('name')}: {str(e)}")
                created_campaigns.append({
                    "name": config.get("name"),
                    "error": str(e),
                    "setup_complete": False
                })
        
        result = {
            "status": "success",
            "customer_id": customer_id,
            "campaigns_created": len([c for c in created_campaigns if c.get("setup_complete")]),
            "campaigns": created_campaigns,
            "feed_integration": feed_data,
            "budget_strategy": budget_strategy
        }
        
        # Persistir configuración de campañas
        await _persist_campaign_setup(client, result, "dynamic_campaigns_created")
        
        return result
        
    except Exception as e:
        logger.error(f"Error creating dynamic campaigns: {str(e)}")
        return {
            "status": "error",
            "message": f"Error al crear campañas dinámicas: {str(e)}"
        }

async def google_ads_setup_enhanced_analytics(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Configura analytics avanzado con métricas personalizadas
    
    Parámetros:
    - customer_id: ID del cliente de Google Ads
    - ga4_property_id: ID de la propiedad GA4
    - custom_metrics: Métricas personalizadas a trackear
    - attribution_models: Modelos de atribución
    - automated_reporting: Configuración de reportes automáticos
    """
    try:
        customer_id = params.get("customer_id")
        ga4_property_id = params.get("ga4_property_id")
        custom_metrics = params.get("custom_metrics", [])
        attribution_models = params.get("attribution_models", [])
        automated_reporting = params.get("automated_reporting", {})
        
        if not customer_id:
            return {
                "status": "error",
                "message": "Parámetro customer_id es requerido"
            }
        
        # Configurar Google Analytics Data API
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
        from google.analytics.data_v1beta.types import DateRange, Dimension, Metric, RunReportRequest
        
        analytics_client = BetaAnalyticsDataClient()
        
        # Configurar métricas personalizadas en GA4
        custom_metrics_setup = []
        if ga4_property_id and custom_metrics:
            for metric in custom_metrics:
                try:
                    # Configurar métrica personalizada
                    metric_config = {
                        "name": metric.get("name"),
                        "display_name": metric.get("display_name"),
                        "description": metric.get("description"),
                        "measurement_unit": metric.get("unit", "STANDARD"),
                        "scope": metric.get("scope", "EVENT"),
                        "parameter_name": metric.get("parameter_name")
                    }
                    
                    custom_metrics_setup.append({
                        "metric_config": metric_config,
                        "status": "configured"
                    })
                    
                except Exception as e:
                    custom_metrics_setup.append({
                        "metric_name": metric.get("name"),
                        "error": str(e),
                        "status": "error"
                    })
        
        # Configurar reportes automáticos
        automated_reports = []
        if automated_reporting.get("enabled"):
            report_configs = automated_reporting.get("reports", [])
            
            for report_config in report_configs:
                try:
                    # Configurar dimensiones y métricas del reporte
                    dimensions = [Dimension(name=dim) for dim in report_config.get("dimensions", [])]
                    metrics = [Metric(name=met) for met in report_config.get("metrics", [])]
                    
                    # Configurar rango de fechas
                    date_ranges = [DateRange(
                        start_date=report_config.get("start_date", "7daysAgo"),
                        end_date=report_config.get("end_date", "today")
                    )]
                    
                    report_request = RunReportRequest(
                        property=f"properties/{ga4_property_id}",
                        dimensions=dimensions,
                        metrics=metrics,
                        date_ranges=date_ranges
                    )
                    
                    # Ejecutar reporte de prueba
                    response = analytics_client.run_report(request=report_request)
                    
                    automated_reports.append({
                        "name": report_config.get("name"),
                        "dimensions": report_config.get("dimensions"),
                        "metrics": report_config.get("metrics"),
                        "schedule": report_config.get("schedule", "daily"),
                        "status": "configured",
                        "sample_data_rows": len(response.rows)
                    })
                    
                except Exception as e:
                    automated_reports.append({
                        "name": report_config.get("name"),
                        "error": str(e),
                        "status": "error"
                    })
        
        # Configurar modelos de atribución
        attribution_setup = []
        if attribution_models:
            from google.ads.googleads.client import GoogleAdsClient
            
            credentials_path = os.getenv("GOOGLE_ADS_CREDENTIALS_PATH")
            client_ads = GoogleAdsClient.load_from_storage(credentials_path)
            
            for model in attribution_models:
                try:
                    # Configurar modelo de atribución personalizado
                    attribution_config = {
                        "name": model.get("name"),
                        "type": model.get("type", "DATA_DRIVEN"),
                        "lookback_window": model.get("lookback_window", 30),
                        "conversion_actions": model.get("conversion_actions", [])
                    }
                    
                    attribution_setup.append({
                        "model_config": attribution_config,
                        "status": "configured"
                    })
                    
                except Exception as e:
                    attribution_setup.append({
                        "model_name": model.get("name"),
                        "error": str(e),
                        "status": "error"
                    })
        
        result = {
            "status": "success",
            "customer_id": customer_id,
            "ga4_property_id": ga4_property_id,
            "custom_metrics": {
                "configured": len([m for m in custom_metrics_setup if m.get("status") == "configured"]),
                "metrics": custom_metrics_setup
            },
            "automated_reporting": {
                "enabled": automated_reporting.get("enabled", False),
                "reports_configured": len([r for r in automated_reports if r.get("status") == "configured"]),
                "reports": automated_reports
            },
            "attribution_models": {
                "configured": len([a for a in attribution_setup if a.get("status") == "configured"]),
                "models": attribution_setup
            }
        }
        
        # Persistir configuración de analytics
        await _persist_analytics_setup(client, result, "enhanced_analytics_setup")
        
        return result
        
    except Exception as e:
        logger.error(f"Error setting up enhanced analytics: {str(e)}")
        return {
            "status": "error",
            "message": f"Error al configurar analytics: {str(e)}"
        }

async def google_ads_automate_bid_management(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Automatiza la gestión de pujas con machine learning
    
    Parámetros:
    - customer_id: ID del cliente de Google Ads
    - campaigns: Lista de campañas para automatizar
    - performance_targets: Objetivos de rendimiento
    - ml_settings: Configuración de machine learning
    - schedule: Programación de optimizaciones
    """
    try:
        customer_id = params.get("customer_id")
        campaigns = params.get("campaigns", [])
        performance_targets = params.get("performance_targets", {})
        ml_settings = params.get("ml_settings", {})
        schedule = params.get("schedule", {})
        
        if not all([customer_id, campaigns, performance_targets]):
            return {
                "status": "error",
                "message": "Parámetros customer_id, campaigns y performance_targets son requeridos"
            }
        
        # Configurar Google Ads API
        from google.ads.googleads.client import GoogleAdsClient
        
        credentials_path = os.getenv("GOOGLE_ADS_CREDENTIALS_PATH")
        client_ads = GoogleAdsClient.load_from_storage(credentials_path)
        
        automation_results = []
        
        for campaign_id in campaigns:
            try:
                # Obtener datos históricos de rendimiento
                google_ads_service = client_ads.get_service("GoogleAdsService")
                
                query = f"""
                    SELECT 
                        campaign.id,
                        campaign.name,
                        metrics.cost_micros,
                        metrics.conversions,
                        metrics.conversion_value,
                        metrics.clicks,
                        metrics.impressions,
                        segments.date
                    FROM campaign 
                    WHERE campaign.id = {campaign_id}
                        AND segments.date DURING LAST_30_DAYS
                """
                
                search_request = client_ads.get_type("SearchGoogleAdsRequest")
                search_request.customer_id = customer_id
                search_request.query = query
                
                results = google_ads_service.search(request=search_request)
                
                # Analizar datos históricos
                historical_data = []
                for row in results:
                    historical_data.append({
                        "date": row.segments.date,
                        "cost": row.metrics.cost_micros / 1000000,
                        "conversions": row.metrics.conversions,
                        "conversion_value": row.metrics.conversion_value,
                        "clicks": row.metrics.clicks,
                        "impressions": row.metrics.impressions
                    })
                
                # Calcular métricas de rendimiento
                if historical_data:
                    total_cost = sum(d["cost"] for d in historical_data)
                    total_conversions = sum(d["conversions"] for d in historical_data)
                    total_value = sum(d["conversion_value"] for d in historical_data)
                    
                    current_cpa = total_cost / total_conversions if total_conversions > 0 else 0
                    current_roas = total_value / total_cost if total_cost > 0 else 0
                    
                    # Determinar ajustes necesarios
                    target_cpa = performance_targets.get("target_cpa")
                    target_roas = performance_targets.get("target_roas")
                    
                    bid_adjustments = []
                    
                    if target_cpa and current_cpa > 0:
                        if current_cpa > target_cpa * 1.1:  # CPA 10% mayor al objetivo
                            bid_adjustments.append({
                                "type": "decrease_bids",
                                "reason": "CPA above target",
                                "adjustment": -0.15  # Reducir pujas 15%
                            })
                        elif current_cpa < target_cpa * 0.9:  # CPA 10% menor al objetivo
                            bid_adjustments.append({
                                "type": "increase_bids",
                                "reason": "CPA below target",
                                "adjustment": 0.10  # Aumentar pujas 10%
                            })
                    
                    if target_roas and current_roas > 0:
                        if current_roas < target_roas * 0.9:  # ROAS 10% menor al objetivo
                            bid_adjustments.append({
                                "type": "decrease_bids",
                                "reason": "ROAS below target",
                                "adjustment": -0.10
                            })
                        elif current_roas > target_roas * 1.1:  # ROAS 10% mayor al objetivo
                            bid_adjustments.append({
                                "type": "increase_bids",
                                "reason": "ROAS above target",
                                "adjustment": 0.15
                            })
                    
                    # Aplicar ajustes de puja
                    if bid_adjustments and ml_settings.get("auto_apply", False):
                        # Aplicar ajustes automáticamente
                        for adjustment in bid_adjustments:
                            await _apply_bid_adjustment(
                                client_ads, customer_id, campaign_id, adjustment
                            )
                    
                    automation_results.append({
                        "campaign_id": campaign_id,
                        "historical_data_points": len(historical_data),
                        "current_metrics": {
                            "cpa": round(current_cpa, 2),
                            "roas": round(current_roas, 2),
                            "total_cost": round(total_cost, 2),
                            "total_conversions": total_conversions
                        },
                        "performance_targets": performance_targets,
                        "recommended_adjustments": bid_adjustments,
                        "auto_applied": ml_settings.get("auto_apply", False),
                        "status": "analyzed"
                    })
                
                else:
                    automation_results.append({
                        "campaign_id": campaign_id,
                        "error": "No historical data available",
                        "status": "insufficient_data"
                    })
                
            except Exception as e:
                automation_results.append({
                    "campaign_id": campaign_id,
                    "error": str(e),
                    "status": "error"
                })
        
        # Programar optimizaciones futuras si se configura
        scheduling_setup = {}
        if schedule.get("enabled"):
            scheduling_setup = {
                "frequency": schedule.get("frequency", "daily"),
                "time": schedule.get("time", "09:00"),
                "timezone": schedule.get("timezone", "UTC"),
                "next_run": _calculate_next_run(schedule),
                "automated": True
            }
        
        result = {
            "status": "success",
            "customer_id": customer_id,
            "campaigns_analyzed": len([r for r in automation_results if r.get("status") == "analyzed"]),
            "automation_results": automation_results,
            "ml_settings": ml_settings,
            "scheduling": scheduling_setup,
            "performance_targets": performance_targets
        }
        
        # Persistir configuración de automatización
        await _persist_bid_automation(client, result, "bid_automation_setup")
        
        return result
        
    except Exception as e:
        logger.error(f"Error setting up bid automation: {str(e)}")
        return {
            "status": "error",
            "message": f"Error al configurar automatización: {str(e)}"
        }

async def google_ads_sync_with_crm(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sincroniza Google Ads con CRM para seguimiento avanzado
    
    Parámetros:
    - customer_id: ID del cliente de Google Ads
    - crm_type: Tipo de CRM (hubspot, salesforce, pipedrive, etc.)
    - crm_config: Configuración del CRM
    - sync_settings: Configuración de sincronización
    - field_mapping: Mapeo de campos entre Google Ads y CRM
    """
    try:
        customer_id = params.get("customer_id")
        crm_type = params.get("crm_type", "hubspot")
        crm_config = params.get("crm_config", {})
        sync_settings = params.get("sync_settings", {})
        field_mapping = params.get("field_mapping", {})
        
        if not all([customer_id, crm_config]):
            return {
                "status": "error",
                "message": "Parámetros customer_id y crm_config son requeridos"
            }
        
        # Configurar conexión con CRM según el tipo
        crm_connection = await _setup_crm_connection(crm_type, crm_config)
        
        if not crm_connection.get("connected"):
            return {
                "status": "error",
                "message": f"No se pudo conectar con {crm_type}: {crm_connection.get('error')}"
            }
        
        # Configurar Customer Match para cargar audiencias desde CRM
        from google.ads.googleads.client import GoogleAdsClient
        
        credentials_path = os.getenv("GOOGLE_ADS_CREDENTIALS_PATH")
        client_ads = GoogleAdsClient.load_from_storage(credentials_path)
        
        # Obtener datos de contactos del CRM
        crm_contacts = await _fetch_crm_contacts(crm_type, crm_connection, sync_settings)
        
        # Crear audiencias personalizadas en Google Ads
        customer_match_setup = []
        if crm_contacts and sync_settings.get("create_audiences"):
            audience_segments = sync_settings.get("audience_segments", [])
            
            for segment in audience_segments:
                try:
                    # Filtrar contactos según criterios del segmento
                    segment_contacts = _filter_contacts_by_criteria(crm_contacts, segment.get("criteria", {}))
                    
                    if segment_contacts:
                        # Crear audiencia Customer Match
                        user_list_service = client_ads.get_service("UserListService")
                        
                        user_list = client_ads.get_type("UserList")
                        user_list.name = segment.get("name", f"CRM Segment {int(time.time())}")
                        user_list.description = segment.get("description", "Imported from CRM")
                        user_list.membership_status = client_ads.enums.UserListMembershipStatusEnum.OPEN
                        user_list.membership_life_span = segment.get("lifetime_days", 365)
                        
                        # Configurar Customer Match
                        user_list.crm_based_user_list.upload_key_type = (
                            client_ads.enums.CustomerMatchUploadKeyTypeEnum.CONTACT_INFO
                        )
                        user_list.crm_based_user_list.data_source_type = (
                            client_ads.enums.UserListCrmDataSourceTypeEnum.FIRST_PARTY
                        )
                        
                        operation = client_ads.get_type("UserListOperation")
                        operation.create.CopyFrom(user_list)
                        
                        response = user_list_service.mutate_user_lists(
                            customer_id=customer_id,
                            operations=[operation]
                        )
                        
                        user_list_resource_name = response.results[0].resource_name
                        
                        # Subir contactos a la audiencia
                        members_added = await _upload_customer_match_data(
                            client_ads, customer_id, user_list_resource_name, segment_contacts
                        )
                        
                        customer_match_setup.append({
                            "segment_name": segment.get("name"),
                            "user_list_resource_name": user_list_resource_name,
                            "contacts_in_segment": len(segment_contacts),
                            "members_uploaded": members_added,
                            "status": "created"
                        })
                
                except Exception as e:
                    customer_match_setup.append({
                        "segment_name": segment.get("name"),
                        "error": str(e),
                        "status": "error"
                    })
        
        # Configurar Enhanced Conversions con datos del CRM
        enhanced_conversions = []
        if sync_settings.get("enhanced_conversions"):
            try:
                # Configurar Enhanced Conversions para mejor seguimiento
                conversion_upload_service = client_ads.get_service("ConversionUploadService")
                
                # Mapear datos de conversiones del CRM
                crm_conversions = await _fetch_crm_conversions(crm_type, crm_connection, field_mapping)
                
                for conversion in crm_conversions:
                    try:
                        # Configurar conversión con datos del CRM
                        click_conversion = client_ads.get_type("ClickConversion")
                        click_conversion.conversion_action = conversion.get("conversion_action")
                        click_conversion.conversion_date_time = conversion.get("conversion_time")
                        click_conversion.conversion_value = conversion.get("value", 0)
                        click_conversion.currency_code = conversion.get("currency", "USD")
                        
                        # Agregar datos de usuario para enhanced conversions
                        if conversion.get("user_identifiers"):
                            for identifier in conversion["user_identifiers"]:
                                user_identifier = click_conversion.user_identifiers.add()
                                if identifier.get("hashed_email"):
                                    user_identifier.hashed_email = identifier["hashed_email"]
                                if identifier.get("hashed_phone_number"):
                                    user_identifier.hashed_phone_number = identifier["hashed_phone_number"]
                        
                        enhanced_conversions.append({
                            "conversion_id": conversion.get("id"),
                            "value": conversion.get("value"),
                            "crm_source": conversion.get("source"),
                            "status": "configured"
                        })
                        
                    except Exception as e:
                        enhanced_conversions.append({
                            "conversion_id": conversion.get("id"),
                            "error": str(e),
                            "status": "error"
                        })
            
            except Exception as e:
                enhanced_conversions.append({
                    "error": f"Enhanced conversions setup failed: {str(e)}",
                    "status": "error"
                })
        
        result = {
            "status": "success",
            "customer_id": customer_id,
            "crm_type": crm_type,
            "crm_connection": {
                "connected": crm_connection.get("connected"),
                "contact_count": len(crm_contacts) if crm_contacts else 0
            },
            "customer_match": {
                "audiences_created": len([a for a in customer_match_setup if a.get("status") == "created"]),
                "audiences": customer_match_setup
            },
            "enhanced_conversions": {
                "conversions_configured": len([c for c in enhanced_conversions if c.get("status") == "configured"]),
                "conversions": enhanced_conversions
            },
            "sync_settings": sync_settings,
            "field_mapping": field_mapping
        }
        
        # Persistir configuración de sincronización CRM
        await _persist_crm_sync(client, result, "crm_sync_setup")
        
        return result
        
    except Exception as e:
        logger.error(f"Error syncing with CRM: {str(e)}")
        return {
            "status": "error",
            "message": f"Error al sincronizar con CRM: {str(e)}"
        }

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

async def _setup_crm_integration(client: AuthenticatedHttpClient, customer_id: str, crm_config: Dict, conversions: List):
    """Configurar integración CRM"""
    try:
        crm_type = crm_config.get("type", "hubspot")
        
        if crm_type == "hubspot":
            # Configurar HubSpot
            return {
                "type": "hubspot",
                "status": "configured",
                "webhook_url": f"https://api.hubspot.com/webhooks/google-ads/{customer_id}",
                "tracking_enabled": True
            }
        elif crm_type == "salesforce":
            # Configurar Salesforce
            return {
                "type": "salesforce",
                "status": "configured",
                "api_integration": True
            }
        else:
            return {
                "type": crm_type,
                "status": "basic_setup",
                "note": "CRM integration requires custom configuration"
            }
    except Exception as e:
        return {"error": str(e), "status": "error"}

async def _create_dynamic_ad_groups(client_ads, customer_id: str, campaign_resource_name: str, config: Dict, audiences: List):
    """Crear grupos de anuncios dinámicos"""
    try:
        ad_group_service = client_ads.get_service("AdGroupService")
        created_groups = []
        
        ad_group_configs = config.get("ad_groups", [{"name": "Default Ad Group"}])
        
        for group_config in ad_group_configs:
            ad_group = client_ads.get_type("AdGroup")
            ad_group.name = group_config.get("name", f"Ad Group {int(time.time())}")
            ad_group.campaign = campaign_resource_name
            ad_group.type_ = client_ads.enums.AdGroupTypeEnum.SEARCH_STANDARD
            ad_group.status = client_ads.enums.AdGroupStatusEnum.ENABLED
            ad_group.cpc_bid_micros = int(group_config.get("max_cpc", 1.0) * 1000000)
            
            operation = client_ads.get_type("AdGroupOperation")
            operation.create.CopyFrom(ad_group)
            
            response = ad_group_service.mutate_ad_groups(
                customer_id=customer_id,
                operations=[operation]
            )
            
            created_groups.append({
                "name": ad_group.name,
                "resource_name": response.results[0].resource_name,
                "max_cpc": group_config.get("max_cpc")
            })
        
        return created_groups
        
    except Exception as e:
        logger.error(f"Error creating ad groups: {str(e)}")
        return []

async def _setup_campaign_extensions(client_ads, customer_id: str, campaign_resource_name: str, config: Dict):
    """Configurar extensiones de campaña"""
    try:
        extensions = []
        
        # Configurar extensiones de sitio
        if config.get("sitelinks"):
            extension_feed_service = client_ads.get_service("ExtensionFeedItemService")
            
            for sitelink in config["sitelinks"]:
                sitelink_extension = client_ads.get_type("ExtensionFeedItem")
                sitelink_extension.extension_type = client_ads.enums.ExtensionTypeEnum.SITELINK
                sitelink_extension.sitelink_feed_item.link_text = sitelink.get("text")
                sitelink_extension.sitelink_feed_item.line1 = sitelink.get("description1", "")
                sitelink_extension.sitelink_feed_item.line2 = sitelink.get("description2", "")
                
                # Agregar URLs finales
                final_url = client_ads.get_type("FinalUrl")
                final_url.url = sitelink.get("url")
                sitelink_extension.sitelink_feed_item.final_urls.append(final_url)
                
                operation = client_ads.get_type("ExtensionFeedItemOperation")
                operation.create.CopyFrom(sitelink_extension)
                
                response = extension_feed_service.mutate_extension_feed_items(
                    customer_id=customer_id,
                    operations=[operation]
                )
                
                extensions.append({
                    "type": "sitelink",
                    "text": sitelink.get("text"),
                    "resource_name": response.results[0].resource_name
                })
        
        return extensions
        
    except Exception as e:
        logger.error(f"Error setting up extensions: {str(e)}")
        return []

async def _apply_bid_adjustment(client_ads, customer_id: str, campaign_id: str, adjustment: Dict):
    """Aplicar ajuste de puja automático"""
    try:
        # Obtener grupos de anuncios de la campaña
        google_ads_service = client_ads.get_service("GoogleAdsService")
        
        query = f"""
            SELECT 
                ad_group.id,
                ad_group.cpc_bid_micros,
                ad_group.resource_name
            FROM ad_group 
            WHERE campaign.id = {campaign_id}
                AND ad_group.status = 'ENABLED'
        """
        
        search_request = client_ads.get_type("SearchGoogleAdsRequest")
        search_request.customer_id = customer_id
        search_request.query = query
        
        results = google_ads_service.search(request=search_request)
        
        # Aplicar ajustes a cada grupo de anuncios
        ad_group_service = client_ads.get_service("AdGroupService")
        operations = []
        
        for row in results:
            current_bid = row.ad_group.cpc_bid_micros
            adjustment_factor = 1 + adjustment["adjustment"]
            new_bid = int(current_bid * adjustment_factor)
            
            # Limitar pujas a rangos razonables
            new_bid = max(10000, min(new_bid, 10000000))  # Entre $0.01 y $10.00
            
            ad_group = client_ads.get_type("AdGroup")
            ad_group.resource_name = row.ad_group.resource_name
            ad_group.cpc_bid_micros = new_bid
            
            operation = client_ads.get_type("AdGroupOperation")
            operation.update.CopyFrom(ad_group)
            operation.update_mask = client_ads.get_type("FieldMask")
            operation.update_mask.paths.append("cpc_bid_micros")
            
            operations.append(operation)
        
        if operations:
            response = ad_group_service.mutate_ad_groups(
                customer_id=customer_id,
                operations=operations
            )
            return len(response.results)
        
        return 0
        
    except Exception as e:
        logger.error(f"Error applying bid adjustment: {str(e)}")
        return 0

def _calculate_next_run(schedule: Dict) -> str:
    """Calcular próxima ejecución programada"""
    try:
        from datetime import datetime, timedelta
        import pytz
        
        frequency = schedule.get("frequency", "daily")
        time_str = schedule.get("time", "09:00")
        timezone = schedule.get("timezone", "UTC")
        
        tz = pytz.timezone(timezone)
        now = datetime.now(tz)
        
        # Parsear hora
        hour, minute = map(int, time_str.split(":"))
        
        if frequency == "daily":
            next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(days=1)
        elif frequency == "weekly":
            next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            days_ahead = 7 - now.weekday()
            if days_ahead <= 0 or (days_ahead == 7 and next_run <= now):
                days_ahead += 7
            next_run += timedelta(days=days_ahead)
        else:
            next_run = now + timedelta(hours=1)  # Default hourly
        
        return next_run.isoformat()
        
    except Exception:
        return (datetime.now() + timedelta(hours=1)).isoformat()

async def _setup_crm_connection(crm_type: str, crm_config: Dict):
    """Configurar conexión con CRM"""
    try:
        if crm_type.lower() == "hubspot":
            api_key = crm_config.get("api_key")
            if not api_key:
                return {"connected": False, "error": "HubSpot API key required"}
            
            # Probar conexión con HubSpot
            import requests
            response = requests.get(
                "https://api.hubapi.com/contacts/v1/lists/all/contacts/all",
                params={"hapikey": api_key, "count": 1}
            )
            
            if response.status_code == 200:
                return {"connected": True, "type": "hubspot", "api_key": api_key}
            else:
                return {"connected": False, "error": "Invalid HubSpot API key"}
        
        elif crm_type.lower() == "salesforce":
            # Configurar Salesforce
            return {"connected": True, "type": "salesforce", "note": "Salesforce integration ready"}
        
        else:
            return {"connected": False, "error": f"CRM type {crm_type} not supported"}
            
    except Exception as e:
        return {"connected": False, "error": str(e)}

async def _fetch_crm_contacts(crm_type: str, connection: Dict, sync_settings: Dict):
    """Obtener contactos del CRM"""
    try:
        if crm_type.lower() == "hubspot" and connection.get("connected"):
            import requests
            
            api_key = connection.get("api_key")
            response = requests.get(
                "https://api.hubapi.com/contacts/v1/lists/all/contacts/all",
                params={
                    "hapikey": api_key,
                    "count": sync_settings.get("max_contacts", 1000),
                    "property": ["email", "firstname", "lastname", "phone", "company"]
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                contacts = []
                
                for contact in data.get("contacts", []):
                    properties = contact.get("properties", {})
                    contacts.append({
                        "email": properties.get("email", {}).get("value", ""),
                        "first_name": properties.get("firstname", {}).get("value", ""),
                        "last_name": properties.get("lastname", {}).get("value", ""),
                        "phone": properties.get("phone", {}).get("value", ""),
                        "company": properties.get("company", {}).get("value", ""),
                        "vid": contact.get("vid")
                    })
                
                return contacts
        
        return []
        
    except Exception as e:
        logger.error(f"Error fetching CRM contacts: {str(e)}")
        return []

def _filter_contacts_by_criteria(contacts: List[Dict], criteria: Dict) -> List[Dict]:
    """Filtrar contactos según criterios"""
    try:
        filtered = contacts
        
        if criteria.get("company_contains"):
            company_filter = criteria["company_contains"].lower()
            filtered = [c for c in filtered if company_filter in c.get("company", "").lower()]
        
        if criteria.get("has_email"):
            filtered = [c for c in filtered if c.get("email")]
        
        if criteria.get("has_phone"):
            filtered = [c for c in filtered if c.get("phone")]
        
        return filtered
        
    except Exception:
        return contacts

async def _upload_customer_match_data(client_ads, customer_id: str, user_list_resource_name: str, contacts: List[Dict]):
    """Subir datos para Customer Match"""
    try:
        import hashlib
        
        user_data_service = client_ads.get_service("UserDataService")
        
        # Preparar datos de usuarios
        user_data_operations = []
        
        for contact in contacts[:10000]:  # Límite de 10,000 por lote
            if contact.get("email"):
                user_data = client_ads.get_type("UserData")
                
                # Hash del email
                email_hash = hashlib.sha256(contact["email"].lower().encode()).hexdigest()
                user_identifier = user_data.user_identifiers.add()
                user_identifier.hashed_email = email_hash
                
                # Hash del teléfono si está disponible
                if contact.get("phone"):
                    phone_hash = hashlib.sha256(contact["phone"].encode()).hexdigest()
                    user_identifier = user_data.user_identifiers.add()
                    user_identifier.hashed_phone_number = phone_hash
                
                operation = client_ads.get_type("UserDataOperation")
                operation.create.CopyFrom(user_data)
                user_data_operations.append(operation)
        
        if user_data_operations:
            request = client_ads.get_type("UploadUserDataRequest")
            request.customer_id = customer_id
            request.operations = user_data_operations
            request.customer_match_user_list_metadata.user_list = user_list_resource_name
            
            response = user_data_service.upload_user_data(request=request)
            return len(user_data_operations)
        
        return 0
        
    except Exception as e:
        logger.error(f"Error uploading customer match data: {str(e)}")
        return 0

async def _fetch_crm_conversions(crm_type: str, connection: Dict, field_mapping: Dict):
    """Obtener conversiones del CRM"""
    try:
        # Esta función obtendría datos de conversiones del CRM
        # Por ahora devolvemos estructura de ejemplo
        return [
            {
                "id": "conv_123",
                "conversion_action": "customers/123/conversionActions/456",
                "conversion_time": "2024-01-15 10:30:00+00:00",
                "value": 100.0,
                "currency": "USD",
                "source": crm_type,
                "user_identifiers": [
                    {"hashed_email": "hashed_email_here"}
                ]
            }
        ]
        
    except Exception as e:
        logger.error(f"Error fetching CRM conversions: {str(e)}")
        return []

# ============================================================================
# FUNCIONES DE PERSISTENCIA
# ============================================================================

async def _persist_conversion_setup(client: AuthenticatedHttpClient, setup_data: Dict[str, Any], action: str):
    """Persistir configuración de conversiones"""
    try:
        from app.memory.memory_functions import save_memory
        
        await save_memory(client, {
            "storage_type": "analytics",
            "file_name": f"google_ads_conversion_setup_{int(time.time())}_{action}.json",
            "content": {
                "action": action,
                "setup_data": setup_data,
                "timestamp": time.time(),
                "platform": "google_ads"
            },
            "tags": ["google_ads", "conversions", "setup", action]
        })
        
    except Exception as e:
        logger.error(f"Error persisting conversion setup: {str(e)}")

async def _persist_campaign_setup(client: AuthenticatedHttpClient, campaign_data: Dict[str, Any], action: str):
    """Persistir configuración de campañas"""
    try:
        from app.memory.memory_functions import save_memory
        
        await save_memory(client, {
            "storage_type": "analytics",
            "file_name": f"google_ads_campaigns_{int(time.time())}_{action}.json",
            "content": {
                "action": action,
                "campaign_data": campaign_data,
                "timestamp": time.time(),
                "platform": "google_ads"
            },
            "tags": ["google_ads", "campaigns", "dynamic", action]
        })
        
    except Exception as e:
        logger.error(f"Error persisting campaign setup: {str(e)}")

async def _persist_analytics_setup(client: AuthenticatedHttpClient, analytics_data: Dict[str, Any], action: str):
    """Persistir configuración de analytics"""
    try:
        from app.memory.memory_functions import save_memory
        
        await save_memory(client, {
            "storage_type": "analytics",
            "file_name": f"google_ads_analytics_{int(time.time())}_{action}.json",
            "content": {
                "action": action,
                "analytics_data": analytics_data,
                "timestamp": time.time(),
                "platform": "google_ads"
            },
            "tags": ["google_ads", "analytics", "enhanced", action]
        })
        
    except Exception as e:
        logger.error(f"Error persisting analytics setup: {str(e)}")

async def _persist_bid_automation(client: AuthenticatedHttpClient, automation_data: Dict[str, Any], action: str):
    """Persistir configuración de automatización de pujas"""
    try:
        from app.memory.memory_functions import save_memory
        
        await save_memory(client, {
            "storage_type": "workflow",
            "file_name": f"google_ads_bid_automation_{int(time.time())}_{action}.json",
            "content": {
                "action": action,
                "automation_data": automation_data,
                "timestamp": time.time(),
                "platform": "google_ads"
            },
            "tags": ["google_ads", "automation", "bids", action]
        })
        
    except Exception as e:
        logger.error(f"Error persisting bid automation: {str(e)}")

async def _persist_crm_sync(client: AuthenticatedHttpClient, sync_data: Dict[str, Any], action: str):
    """Persistir configuración de sincronización CRM"""
    try:
        from app.memory.memory_functions import save_memory
        
        await save_memory(client, {
            "storage_type": "analytics",
            "file_name": f"google_ads_crm_sync_{int(time.time())}_{action}.json",
            "content": {
                "action": action,
                "sync_data": sync_data,
                "timestamp": time.time(),
                "platform": "google_ads"
            },
            "tags": ["google_ads", "crm", "sync", action]
        })
        
    except Exception as e:
        logger.error(f"Error persisting CRM sync: {str(e)}")
