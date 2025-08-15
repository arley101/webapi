# app/actions/metaads_actions.py
import logging
import os
import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from app.core.config import settings
from app.shared.helpers.http_client import AuthenticatedHttpClient  # ✅ IMPORTACIÓN CORREGIDA

# ✅ IMPORTACIÓN DIRECTA DEL RESOLVER PARA EVITAR CIRCULARIDAD
def _get_resolver():
    from app.actions.resolver_actions import Resolver
    return Resolver()

from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.business import Business
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.adcreative import AdCreative
from facebook_business.adobjects.customaudience import CustomAudience
from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.page import Page
from facebook_business.adobjects.adimage import AdImage
from facebook_business.adobjects.advideo import AdVideo
from facebook_business.adobjects.adsinsights import AdsInsights
from facebook_business.adobjects.targeting import Targeting
from facebook_business.exceptions import FacebookRequestError

try:
    from facebook_business.adobjects.campaignbudget import CampaignBudget
except ImportError:
    # Fallback para versiones diferentes del SDK - usar Campaign para presupuesto
    CampaignBudget = None

logger = logging.getLogger(__name__)

# --- SDK INITIALIZATION AND HELPERS ---

def _get_meta_ads_api_client(params: Dict[str, Any]) -> FacebookAdsApi:
    access_token = settings.META_ADS.ACCESS_TOKEN
    app_id = settings.META_ADS.APP_ID
    app_secret = settings.META_ADS.APP_SECRET

    if not all([app_id, app_secret, access_token]):
        raise ValueError("Credenciales de Meta Ads (APP_ID, APP_SECRET, ACCESS_TOKEN) deben estar configuradas.")

    return FacebookAdsApi.init(
        app_id=str(app_id),
        app_secret=str(app_secret),
        access_token=str(access_token),
        api_version="v19.0"
    )

# ============================================================================
# ENHANCED META ADS ACTIONS - NUEVAS FUNCIONES AGREGADAS
# ============================================================================

# Función helper para manejar errores
def _handle_meta_ads_api_error(error: Exception, action_name: str) -> Dict[str, Any]:
    """
    Maneja errores de la API de Meta Ads de manera consistente
    """
    error_message = str(error)
    error_code = getattr(error, 'api_error_code', 'UNKNOWN')
    
    logger.error(f"Meta Ads API Error in {action_name}: {error_message}")
    
    return {
        "status": "error",
        "message": f"Error en {action_name}: {error_message}",
        "error_code": error_code,
        "action": action_name
    }

def _get_ad_account_id(params: Dict[str, Any]) -> str:
    ad_account_id = params.get("ad_account_id", os.getenv("META_AD_ACCOUNT_ID"))
    if not ad_account_id:
        raise ValueError("'ad_account_id' es requerido.")
    return f"act_{str(ad_account_id).replace('act_', '')}"

async def meta_create_campaign(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Crea una nueva campaña en Meta Ads
    
    Parámetros:
    - name: Nombre de la campaña
    - objective: Objetivo (REACH, TRAFFIC, ENGAGEMENT, etc.)
    - budget_amount: Presupuesto total en centavos
    - start_time: Fecha inicio (ISO 8601) - opcional
    - end_time: Fecha fin (ISO 8601) - opcional
    """
    try:
        # Validar parámetros requeridos
        name = params.get("name")
        objective = params.get("objective", "TRAFFIC")
        budget_amount = params.get("budget_amount")
        
        if not name or not budget_amount:
            return {
                "status": "error",
                "message": "Parámetros 'name' y 'budget_amount' son requeridos"
            }
        
        # Configurar Meta Business SDK
        _get_meta_ads_api_client(params)
        
        # Obtener ad account ID
        ad_account_id = _get_ad_account_id(params)
        ad_account = AdAccount(ad_account_id)
        
        # Configurar campaña
        campaign_data = {
            Campaign.Field.name: name,
            Campaign.Field.objective: objective,
            Campaign.Field.status: Campaign.Status.paused,  # Crear pausada por defecto
            Campaign.Field.buying_type: "AUCTION"
        }
        
        # Agregar fechas si se proporcionan
        start_time = params.get("start_time")
        end_time = params.get("end_time")
        
        if start_time:
            campaign_data[Campaign.Field.start_time] = start_time
        if end_time:
            campaign_data[Campaign.Field.stop_time] = end_time
        
        # Crear campaña
        campaign = ad_account.create_campaign(fields=[], params=campaign_data)
        
        # Crear presupuesto de campaña si CampaignBudget está disponible
        if CampaignBudget:
            budget_data = {
                CampaignBudget.Field.name: f"Budget for {name}",
                CampaignBudget.Field.budget_rebalance_flag: True,
                CampaignBudget.Field.lifetime_budget: int(budget_amount)
            }
            
            budget = ad_account.create_campaign_budget(fields=[], params=budget_data)
            
            # Actualizar campaña con presupuesto
            campaign.api_update(params={
                Campaign.Field.budget_id: budget[CampaignBudget.Field.id]
            })
        
        # Obtener detalles de la campaña creada
        campaign = campaign.api_get(fields=[
            Campaign.Field.id,
            Campaign.Field.name,
            Campaign.Field.objective,
            Campaign.Field.status,
            Campaign.Field.created_time
        ])
        
        result = {
            "status": "success",
            "campaign": {
                "id": campaign[Campaign.Field.id],
                "name": campaign[Campaign.Field.name],
                "objective": campaign[Campaign.Field.objective],
                "status": campaign[Campaign.Field.status],
                "budget_amount": budget_amount,
                "created_time": campaign.get(Campaign.Field.created_time)
            }
        }
        
        # Persistir campaña creada usando STORAGE_RULES
        await _persist_campaign_data(client, result["campaign"], "created")
        
        return result
        
    except Exception as e:
        logger.error(f"Error creating Meta campaign: {str(e)}")
        return {
            "status": "error",
            "message": f"Error al crear campaña: {str(e)}"
        }

async def meta_create_ad_set(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Crea un conjunto de anuncios en Meta Ads
    
    Parámetros:
    - campaign_id: ID de la campaña
    - name: Nombre del ad set
    - targeting: Configuración de targeting (dict)
    - daily_budget: Presupuesto diario en centavos
    - bid_amount: Puja en centavos - opcional
    """
    try:
        # Validar parámetros requeridos
        campaign_id = params.get("campaign_id")
        name = params.get("name")
        targeting = params.get("targeting", {})
        daily_budget = params.get("daily_budget")
        
        if not all([campaign_id, name, daily_budget]):
            return {
                "status": "error",
                "message": "Parámetros 'campaign_id', 'name' y 'daily_budget' son requeridos"
            }
        
        # Configurar Meta Business SDK
        _get_meta_ads_api_client(params)
        ad_account_id = _get_ad_account_id(params)
        ad_account = AdAccount(ad_account_id)
        
        # Configuración básica de targeting
        targeting_config = {
            Targeting.Field.geo_locations: targeting.get("geo_locations", {
                'countries': ['US']  # Default a US
            }),
            Targeting.Field.age_min: targeting.get("age_min", 18),
            Targeting.Field.age_max: targeting.get("age_max", 65)
        }
        
        # Agregar intereses si se proporcionan
        if targeting.get("interests"):
            targeting_config[Targeting.Field.interests] = targeting["interests"]
        
        # Configurar ad set
        adset_data = {
            AdSet.Field.name: name,
            AdSet.Field.campaign_id: campaign_id,
            AdSet.Field.daily_budget: int(daily_budget),
            AdSet.Field.billing_event: AdSet.BillingEvent.impressions,
            AdSet.Field.optimization_goal: AdSet.OptimizationGoal.reach,
            AdSet.Field.bid_amount: params.get("bid_amount", 100),
            AdSet.Field.targeting: targeting_config,
            AdSet.Field.status: AdSet.Status.paused
        }
        
        # Crear ad set
        adset = ad_account.create_ad_set(fields=[], params=adset_data)
        
        # Obtener detalles del ad set creado
        adset = adset.api_get(fields=[
            AdSet.Field.id,
            AdSet.Field.name,
            AdSet.Field.campaign_id,
            AdSet.Field.daily_budget,
            AdSet.Field.status,
            AdSet.Field.created_time
        ])
        
        result = {
            "status": "success",
            "ad_set": {
                "id": adset[AdSet.Field.id],
                "name": adset[AdSet.Field.name],
                "campaign_id": adset[AdSet.Field.campaign_id],
                "daily_budget": adset[AdSet.Field.daily_budget],
                "status": adset[AdSet.Field.status],
                "targeting": targeting_config,
                "created_time": adset.get(AdSet.Field.created_time)
            }
        }
        
        # Persistir ad set creado
        await _persist_adset_data(client, result["ad_set"], "created")
        
        return result
        
    except Exception as e:
        logger.error(f"Error creating Meta ad set: {str(e)}")
        return {
            "status": "error",
            "message": f"Error al crear conjunto de anuncios: {str(e)}"
        }

async def meta_upload_creatives(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sube creativos (imágenes/videos) para Meta Ads
    
    Parámetros:
    - files: Lista de archivos a subir (paths o URLs)
    - creative_type: Tipo de creativo (IMAGE, VIDEO)
    - names: Lista de nombres para los creativos - opcional
    """
    try:
        files = params.get("files", [])
        creative_type = params.get("creative_type", "IMAGE")
        names = params.get("names", [])
        
        if not files:
            return {
                "status": "error",
                "message": "Parámetro 'files' es requerido"
            }
        
        # Configurar Meta Business SDK
        _get_meta_ads_api_client(params)
        ad_account_id = _get_ad_account_id(params)
        ad_account = AdAccount(ad_account_id)
        
        uploaded_creatives = []
        
        for i, file_path in enumerate(files):
            try:
                creative_name = names[i] if i < len(names) else f"Creative_{int(time.time())}_{i}"
                
                if creative_type.upper() == "IMAGE":
                    # Subir imagen
                    if file_path.startswith("http"):
                        # URL remota
                        import requests
                        response = requests.get(file_path)
                        response.raise_for_status()
                        
                        with open(f"/tmp/temp_image_{i}.jpg", "wb") as f:
                            f.write(response.content)
                        file_path = f"/tmp/temp_image_{i}.jpg"
                    
                    image = ad_account.create_ad_image(params={
                        AdImage.Field.filename: file_path,
                        AdImage.Field.name: creative_name
                    })
                    
                    uploaded_creatives.append({
                        "type": "image",
                        "id": image[AdImage.Field.id],
                        "hash": image[AdImage.Field.hash],
                        "name": creative_name,
                        "url": image.get(AdImage.Field.url)
                    })
                    
                elif creative_type.upper() == "VIDEO":
                    # Subir video
                    if file_path.startswith("http"):
                        # URL remota
                        import requests
                        response = requests.get(file_path)
                        response.raise_for_status()
                        
                        with open(f"/tmp/temp_video_{i}.mp4", "wb") as f:
                            f.write(response.content)
                        file_path = f"/tmp/temp_video_{i}.mp4"
                    
                    video = ad_account.create_ad_video(params={
                        AdVideo.Field.source: file_path,
                        AdVideo.Field.name: creative_name
                    })
                    
                    uploaded_creatives.append({
                        "type": "video",
                        "id": video[AdVideo.Field.id],
                        "name": creative_name
                    })
                
            except Exception as e:
                logger.error(f"Error uploading creative {i}: {str(e)}")
                uploaded_creatives.append({
                    "type": creative_type.lower(),
                    "error": str(e),
                    "file": file_path
                })
        
        result = {
            "status": "success",
            "uploaded_count": len([c for c in uploaded_creatives if "error" not in c]),
            "error_count": len([c for c in uploaded_creatives if "error" in c]),
            "creatives": uploaded_creatives
        }
        
        # Persistir creativos subidos
        await _persist_creatives_data(client, uploaded_creatives, "uploaded")
        
        return result
        
    except Exception as e:
        logger.error(f"Error uploading Meta creatives: {str(e)}")
        return {
            "status": "error",
            "message": f"Error al subir creativos: {str(e)}"
        }

async def meta_get_campaign_metrics(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Obtiene métricas de campañas de Meta Ads
    
    Parámetros:
    - campaign_ids: Lista de IDs de campañas - opcional (todas si no se especifica)
    - date_range: Rango de fechas {"since": "YYYY-MM-DD", "until": "YYYY-MM-DD"}
    - metrics: Lista de métricas a obtener - opcional
    """
    try:
        campaign_ids = params.get("campaign_ids", [])
        date_range = params.get("date_range", {})
        metrics = params.get("metrics", [
            "impressions", "clicks", "spend", "reach", "frequency", "ctr", "cpm", "cpp"
        ])
        
        # Configurar Meta Business SDK
        _get_meta_ads_api_client(params)
        ad_account_id = _get_ad_account_id(params)
        ad_account = AdAccount(ad_account_id)
        
        # Configurar parámetros de insights
        insight_params = {
            'level': AdsInsights.Level.campaign,
            'fields': metrics
        }
        
        # Agregar rango de fechas
        if date_range.get("since"):
            insight_params['time_range'] = {
                'since': date_range["since"],
                'until': date_range.get("until", datetime.now().strftime("%Y-%m-%d"))
            }
        
        # Filtrar por campañas específicas si se proporcionan
        if campaign_ids:
            insight_params['filtering'] = [
                {
                    'field': 'campaign.id',
                    'operator': 'IN',
                    'value': campaign_ids
                }
            ]
        
        # Obtener insights
        insights = ad_account.get_insights(params=insight_params)
        
        campaign_metrics = []
        for insight in insights:
            campaign_data = {
                "campaign_id": insight.get("campaign_id"),
                "campaign_name": insight.get("campaign_name"),
                "date_start": insight.get("date_start"),
                "date_stop": insight.get("date_stop"),
                "metrics": {}
            }
            
            # Agregar métricas solicitadas
            for metric in metrics:
                campaign_data["metrics"][metric] = insight.get(metric, 0)
            
            campaign_metrics.append(campaign_data)
        
        result = {
            "status": "success",
            "campaigns_count": len(campaign_metrics),
            "date_range": date_range,
            "metrics_requested": metrics,
            "campaigns": campaign_metrics
        }
        
        # Persistir métricas para análisis
        await _persist_metrics_data(client, campaign_metrics, "campaign_metrics")
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting Meta campaign metrics: {str(e)}")
        return {
            "status": "error",
            "message": f"Error al obtener métricas: {str(e)}"
        }

async def meta_update_budget_and_schedule(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Actualiza presupuesto y programación de campañas/ad sets
    
    Parámetros:
    - target_type: Tipo de objetivo ("campaign" o "adset")
    - target_id: ID de la campaña o ad set
    - budget_amount: Nuevo presupuesto (centavos)
    - budget_type: Tipo de presupuesto ("daily" o "lifetime")
    - start_time: Nueva fecha inicio - opcional
    - end_time: Nueva fecha fin - opcional
    - status: Nuevo estado ("ACTIVE", "PAUSED") - opcional
    """
    try:
        target_type = params.get("target_type", "campaign")
        target_id = params.get("target_id")
        budget_amount = params.get("budget_amount")
        budget_type = params.get("budget_type", "daily")
        
        if not target_id or not budget_amount:
            return {
                "status": "error",
                "message": "Parámetros 'target_id' y 'budget_amount' son requeridos"
            }
        
        # Configurar Meta Business SDK
        _get_meta_ads_api_client(params)
        
        update_params = {}
        
        if target_type.lower() == "campaign":
            # Actualizar campaña
            campaign = Campaign(target_id)
            
            # Para campañas, el presupuesto se maneja a través del CampaignBudget
            if CampaignBudget:
                current_campaign = campaign.api_get(fields=[Campaign.Field.budget_id])
                budget_id = current_campaign.get(Campaign.Field.budget_id)
                
                if budget_id:
                    budget = CampaignBudget(budget_id)
                    budget_params = {}
                    
                    if budget_type == "daily":
                        budget_params[CampaignBudget.Field.daily_budget] = int(budget_amount)
                    else:
                        budget_params[CampaignBudget.Field.lifetime_budget] = int(budget_amount)
                    
                    budget.api_update(params=budget_params)
            
            # Actualizar fechas y estado de campaña
            if params.get("start_time"):
                update_params[Campaign.Field.start_time] = params["start_time"]
            if params.get("end_time"):
                update_params[Campaign.Field.stop_time] = params["end_time"]
            if params.get("status"):
                update_params[Campaign.Field.status] = params["status"]
            
            if update_params:
                campaign.api_update(params=update_params)
            
            # Obtener datos actualizados
            updated_campaign = campaign.api_get(fields=[
                Campaign.Field.id,
                Campaign.Field.name,
                Campaign.Field.status,
                Campaign.Field.start_time,
                Campaign.Field.stop_time
            ])
            
            result = {
                "status": "success",
                "target_type": "campaign",
                "updated_campaign": {
                    "id": updated_campaign[Campaign.Field.id],
                    "name": updated_campaign[Campaign.Field.name],
                    "status": updated_campaign[Campaign.Field.status],
                    "budget_amount": budget_amount,
                    "budget_type": budget_type,
                    "start_time": updated_campaign.get(Campaign.Field.start_time),
                    "stop_time": updated_campaign.get(Campaign.Field.stop_time)
                }
            }
            
        elif target_type.lower() == "adset":
            # Actualizar ad set
            adset = AdSet(target_id)
            
            if budget_type == "daily":
                update_params[AdSet.Field.daily_budget] = int(budget_amount)
            else:
                update_params[AdSet.Field.lifetime_budget] = int(budget_amount)
            
            if params.get("start_time"):
                update_params[AdSet.Field.start_time] = params["start_time"]
            if params.get("end_time"):
                update_params[AdSet.Field.end_time] = params["end_time"]
            if params.get("status"):
                update_params[AdSet.Field.status] = params["status"]
            
            adset.api_update(params=update_params)
            
            # Obtener datos actualizados
            updated_adset = adset.api_get(fields=[
                AdSet.Field.id,
                AdSet.Field.name,
                AdSet.Field.status,
                AdSet.Field.daily_budget,
                AdSet.Field.lifetime_budget
            ])
            
            result = {
                "status": "success",
                "target_type": "adset",
                "updated_adset": {
                    "id": updated_adset[AdSet.Field.id],
                    "name": updated_adset[AdSet.Field.name],
                    "status": updated_adset[AdSet.Field.status],
                    "daily_budget": updated_adset.get(AdSet.Field.daily_budget),
                    "lifetime_budget": updated_adset.get(AdSet.Field.lifetime_budget),
                    "budget_type": budget_type
                }
            }
        
        else:
            return {
                "status": "error",
                "message": "target_type debe ser 'campaign' o 'adset'"
            }
        
        # Persistir actualización
        await _persist_budget_update(client, result, "budget_schedule_update")
        
        return result
        
    except Exception as e:
        logger.error(f"Error updating Meta budget/schedule: {str(e)}")
        return {
            "status": "error",
            "message": f"Error al actualizar presupuesto/programación: {str(e)}"
        }

# ============================================================================
# FUNCIONES AUXILIARES DE PERSISTENCIA
# ============================================================================

async def _persist_campaign_data(client: AuthenticatedHttpClient, campaign_data: Dict[str, Any], action: str):
    """Persiste datos de campaña usando STORAGE_RULES"""
    try:
        from app.memory.memory_functions import save_memory
        
        await save_memory(client, {
            "storage_type": "analytics",
            "file_name": f"meta_campaign_{campaign_data.get('id', int(time.time()))}_{action}.json",
            "content": {
                "action": action,
                "campaign_data": campaign_data,
                "timestamp": time.time(),
                "platform": "meta_ads"
            },
            "tags": ["meta_ads", "campaign", action]
        })
        
    except Exception as e:
        logger.error(f"Error persisting campaign data: {str(e)}")

async def _persist_adset_data(client: AuthenticatedHttpClient, adset_data: Dict[str, Any], action: str):
    """Persiste datos de ad set usando STORAGE_RULES"""
    try:
        from app.memory.memory_functions import save_memory
        
        await save_memory(client, {
            "storage_type": "analytics",
            "file_name": f"meta_adset_{adset_data.get('id', int(time.time()))}_{action}.json",
            "content": {
                "action": action,
                "adset_data": adset_data,
                "timestamp": time.time(),
                "platform": "meta_ads"
            },
            "tags": ["meta_ads", "adset", action]
        })
        
    except Exception as e:
        logger.error(f"Error persisting adset data: {str(e)}")

async def _persist_creatives_data(client: AuthenticatedHttpClient, creatives_data: List[Dict[str, Any]], action: str):
    """Persiste datos de creativos usando STORAGE_RULES"""
    try:
        from app.memory.memory_functions import save_memory
        
        await save_memory(client, {
            "storage_type": "document",
            "file_name": f"meta_creatives_{int(time.time())}_{action}.json",
            "content": {
                "action": action,
                "creatives": creatives_data,
                "timestamp": time.time(),
                "platform": "meta_ads"
            },
            "tags": ["meta_ads", "creatives", action]
        })
        
    except Exception as e:
        logger.error(f"Error persisting creatives data: {str(e)}")

async def _persist_metrics_data(client: AuthenticatedHttpClient, metrics_data: List[Dict[str, Any]], action: str):
    """Persiste métricas usando STORAGE_RULES"""
    try:
        from app.memory.memory_functions import save_memory
        
        await save_memory(client, {
            "storage_type": "analytics",
            "file_name": f"meta_metrics_{int(time.time())}_{action}.json",
            "content": {
                "action": action,
                "metrics": metrics_data,
                "timestamp": time.time(),
                "platform": "meta_ads"
            },
            "tags": ["meta_ads", "metrics", action]
        })
        
    except Exception as e:
        logger.error(f"Error persisting metrics data: {str(e)}")

async def _persist_budget_update(client: AuthenticatedHttpClient, update_data: Dict[str, Any], action: str):
    """Persiste actualización de presupuesto usando STORAGE_RULES"""
    try:
        from app.memory.memory_functions import save_memory
        
        await save_memory(client, {
            "storage_type": "analytics",
            "file_name": f"meta_budget_update_{int(time.time())}_{action}.json",
            "content": {
                "action": action,
                "update_data": update_data,
                "timestamp": time.time(),
                "platform": "meta_ads"
            },
            "tags": ["meta_ads", "budget", "schedule", action]
        })
        
    except Exception as e:
        logger.error(f"Error persisting budget update: {str(e)}")

# ============================================================================
# ACCIONES EXISTENTES - MANTENIDAS PARA COMPATIBILIDAD
# ============================================================================

def metaads_get_business_details(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "metaads_get_business_details"
    try:
        _get_meta_ads_api_client(params)
        business_id = params.get("business_id", settings.META_ADS.BUSINESS_ACCOUNT_ID)
        if not business_id:
            raise ValueError("'business_id' es requerido.")
        business = Business(business_id)
        info = business.api_get(fields=params.get("fields", ["id", "name", "verification_status"]))
        return {"status": "success", "data": info.export_all_data()}
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)

def metaads_list_owned_pages(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "metaads_list_owned_pages"
    try:
        _get_meta_ads_api_client(params)
        business_id = params.get("business_id", settings.META_ADS.BUSINESS_ACCOUNT_ID)
        if not business_id:
            raise ValueError("'business_id' es requerido.")
        business = Business(business_id)
        pages = business.get_owned_pages(fields=params.get("fields", ["id", "name", "access_token"]))
        return {"status": "success", "data": [page.export_all_data() for page in pages]}
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)

def metaads_get_page_engagement(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "metaads_get_page_engagement"
    try:
        page_id = params.get("page_id")
        if not page_id:
            raise ValueError("'page_id' es requerido.")
        api = _get_meta_ads_api_client(params)
        page = Page(page_id, api=api)
        info = page.api_get(fields=params.get("fields", ["id", "name", "engagement", "fan_count"]))
        return {"status": "success", "data": info.export_all_data()}
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)

def metaads_list_campaigns(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "metaads_list_campaigns"
    try:
        _get_meta_ads_api_client(params)
        ad_account_id = params.get("ad_account_id")
        if not ad_account_id:
            raise ValueError("'ad_account_id' es requerido.")
        ad_account = AdAccount(f"act_{str(ad_account_id).replace('act_', '')}")
        campaigns = ad_account.get_campaigns(fields=params.get("fields", ["id", "name", "status", "objective"]))
        return {"status": "success", "data": [c.export_all_data() for c in campaigns]}
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)

def metaads_create_campaign(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Crea una nueva campaña en Meta Ads
    """
    action_name = "metaads_create_campaign"
    try:
        # Extraer parámetros correctamente
        account_id = params.get('account_id') or settings.META_ADS.BUSINESS_ACCOUNT_ID
        name = params.get('name', f'Campaign_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
        objective = params.get('objective', 'OUTCOME_TRAFFIC')
        status = params.get('status', 'PAUSED')
        special_ad_categories = params.get('special_ad_categories', [])
        
        if not account_id:
            return {
                "status": "error",
                "message": "account_id es requerido"
            }
        
        # Configurar parámetros de la campaña
        campaign_params = {
            'name': name,
            'objective': objective,
            'status': status,
            'special_ad_categories': special_ad_categories
        }
        
        # Crear la campaña usando el SDK de Facebook
        ad_account = AdAccount(f'act_{account_id}')
        campaign = ad_account.create_campaign(params=campaign_params)
        
        # Obtener los datos de la campaña creada
        campaign_data = campaign.export_all_data()
        
        result = {
            "status": "success",
            "message": f"Campaña '{name}' creada exitosamente",
            "data": {
                "id": campaign_data.get('id'),
                "name": campaign_data.get('name'),
                "status": campaign_data.get('status'),
                "objective": campaign_data.get('objective'),
                "account_id": account_id,
                "created_time": campaign_data.get('created_time')
            }
        }
        
        # ✅ PERSISTENCIA DE MEMORIA - FUNCIÓN DE CREACIÓN
        _get_resolver().save_action_result(action_name, params, result)
        
        return result
        
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)

def metaads_update_campaign(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "metaads_update_campaign"
    try:
        _get_meta_ads_api_client(params)
        campaign_id = params.get("campaign_id")
        update_payload = params.get("update_payload")
        if not campaign_id or not update_payload:
            raise ValueError("'campaign_id' y 'update_payload' son requeridos.")
        campaign = Campaign(campaign_id)
        campaign.api_update(params=update_payload)
        updated = campaign.api_get(fields=["id", "name", "status"])
        
        result = {"status": "success", "data": updated.export_all_data()}
        
        # ✅ PERSISTENCIA DE MEMORIA - FUNCIÓN DE MODIFICACIÓN
        _get_resolver().save_action_result(action_name, params, result)
        
        return result
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)

def metaads_delete_campaign(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "metaads_delete_campaign"
    try:
        _get_meta_ads_api_client(params)
        campaign_id = params.get("campaign_id")
        if not campaign_id:
            raise ValueError("'campaign_id' es requerido.")
        Campaign(campaign_id).api_delete()
        return {"status": "success", "message": f"Campaña '{campaign_id}' eliminada."}
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)

def get_insights(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "metaads_get_insights"
    try:
        _get_meta_ads_api_client(params)
        ad_account_id = params.get("ad_account_id")
        insights_params = params.get("insights_params")
        if not ad_account_id or not insights_params:
            raise ValueError("'ad_account_id' y 'insights_params' son requeridos.")
        ad_account = AdAccount(f"act_{str(ad_account_id).replace('act_', '')}")
        insights = ad_account.get_insights(params=insights_params)
        return {"status": "success", "data": [i.export_all_data() for i in insights]}
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)

def metaads_get_campaign_details(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "metaads_get_campaign_details"
    try:
        _get_meta_ads_api_client(params)
        campaign_id = params.get("campaign_id")
        fields = params.get("fields", ["id", "name", "status", "objective", "daily_budget", "lifetime_budget"])
        if not campaign_id:
            raise ValueError("'campaign_id' es requerido.")
        
        campaign = Campaign(campaign_id)
        details = campaign.api_get(fields=fields)
        return {"status": "success", "data": details.export_all_data()}
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)

def metaads_create_ad_set(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "metaads_create_ad_set"
    try:
        _get_meta_ads_api_client(params)
        ad_account_id = params.get("ad_account_id")
        ad_set_payload = params.get("ad_set_payload")
        if not ad_account_id or not ad_set_payload:
            raise ValueError("'ad_account_id' y 'ad_set_payload' son requeridos.")
        
        ad_account = AdAccount(f"act_{str(ad_account_id).replace('act_', '')}")
        ad_set = ad_account.create_ad_set(params=ad_set_payload)
        
        result = {"status": "success", "data": ad_set.export_all_data()}
        
        # ✅ PERSISTENCIA DE MEMORIA - FUNCIÓN DE CREACIÓN
        _get_resolver().save_action_result(action_name, params, result)
        
        return result
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)

def metaads_get_ad_set_details(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "metaads_get_ad_set_details"
    try:
        _get_meta_ads_api_client(params)
        ad_set_id = params.get("ad_set_id")
        fields = params.get("fields", ["id", "name", "status", "campaign_id", "targeting", "daily_budget"])
        if not ad_set_id:
            raise ValueError("'ad_set_id' es requerido.")

        ad_set = AdSet(ad_set_id)
        details = ad_set.api_get(fields=fields)
        return {"status": "success", "data": details.export_all_data()}
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)

def metaads_get_account_insights(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    # Reemplaza la función existente get_insights con esta versión actualizada
    action_name = "metaads_get_account_insights"
    try:
        _get_meta_ads_api_client(params)
        ad_account_id = params.get("ad_account_id")
        insights_params = params.get("insights_params", {})
        if not ad_account_id:
            raise ValueError("'ad_account_id' es requerido.")
        
        ad_account = AdAccount(f"act_{str(ad_account_id).replace('act_', '')}")
        insights = ad_account.get_insights(params=insights_params)
        return {"status": "success", "data": [i.export_all_data() for i in insights]}
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)

def metaads_create_ad(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "metaads_create_ad"
    try:
        _get_meta_ads_api_client(params)
        ad_account_id = _get_ad_account_id(params)
        payload = params.get("ad_payload")
        if not payload:
            raise ValueError("'ad_payload' es requerido.")
        ad_account = AdAccount(ad_account_id)
        ad = ad_account.create_ad(params=payload)
        
        result = {"status": "success", "data": ad.export_all_data()}
        
        # ✅ PERSISTENCIA DE MEMORIA - FUNCIÓN DE CREACIÓN
        _get_resolver().save_action_result(action_name, params, result)
        
        return result
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)

def metaads_get_ad_preview(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "metaads_get_ad_preview"
    try:
        _get_meta_ads_api_client(params)
        ad_id = params.get("ad_id")
        ad_format = params.get("ad_format", "DESKTOP_FEED_STANDARD")
        if not ad_id:
            raise ValueError("'ad_id' es requerido.")
        ad = Ad(ad_id)
        previews = ad.get_previews(params={'ad_format': ad_format})
        return {"status": "success", "data": [p.export_all_data() for p in previews]}
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)

def metaads_update_ad(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "metaads_update_ad"
    try:
        _get_meta_ads_api_client(params)
        ad_id = params.get("ad_id")
        update_payload = params.get("update_payload")
        if not ad_id or not update_payload:
            raise ValueError("'ad_id' y 'update_payload' son requeridos.")
        ad = Ad(ad_id)
        ad.api_update(params=update_payload)
        updated = ad.api_get(fields=["id", "name", "status", "creative"])
        
        result = {"status": "success", "data": updated.export_all_data()}
        
        # ✅ PERSISTENCIA DE MEMORIA - FUNCIÓN DE MODIFICACIÓN
        _get_resolver().save_action_result(action_name, params, result)
        
        return result
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)

def metaads_delete_ad(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "metaads_delete_ad"
    try:
        _get_meta_ads_api_client(params)
        ad_id = params.get("ad_id")
        if not ad_id:
            raise ValueError("'ad_id' es requerido.")
        Ad(ad_id).api_delete()
        return {"status": "success", "message": f"Anuncio '{ad_id}' eliminado."}
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)

def metaads_update_ad_set(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "metaads_update_ad_set"
    try:
        _get_meta_ads_api_client(params)
        ad_set_id = params.get("ad_set_id")
        update_payload = params.get("update_payload")
        if not ad_set_id or not update_payload:
            raise ValueError("'ad_set_id' y 'update_payload' son requeridos.")
        ad_set = AdSet(ad_set_id)
        ad_set.api_update(params=update_payload)
        updated = ad_set.api_get(fields=["id", "name", "status", "targeting", "budget_remaining"])
        
        result = {"status": "success", "data": updated.export_all_data()}
        
        # ✅ PERSISTENCIA DE MEMORIA - FUNCIÓN DE MODIFICACIÓN
        _get_resolver().save_action_result(action_name, params, result)
        
        return result
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)

def metaads_delete_ad_set(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "metaads_delete_ad_set"
    try:
        _get_meta_ads_api_client(params)
        ad_set_id = params.get("ad_set_id")
        if not ad_set_id:
            raise ValueError("'ad_set_id' es requerido.")
        AdSet(ad_set_id).api_delete()
        return {"status": "success", "message": f"Conjunto de anuncios '{ad_set_id}' eliminado."}
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)

def metaads_update_page_settings(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "metaads_update_page_settings"
    try:
        _get_meta_ads_api_client(params)
        page_id = params.get("page_id")
        settings_payload = params.get("settings_payload")
        if not page_id or not settings_payload:
            raise ValueError("'page_id' y 'settings_payload' son requeridos.")
        page = Page(page_id)
        page.api_update(params=settings_payload)
        updated = page.api_get(fields=["id", "name", "settings"])
        return {"status": "success", "data": updated.export_all_data()}
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)

def metaads_create_custom_audience(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "metaads_create_custom_audience"
    try:
        _get_meta_ads_api_client(params)
        ad_account_id = _get_ad_account_id(params)
        audience_payload = params.get("audience_payload")
        if not audience_payload:
            raise ValueError("'audience_payload' es requerido.")
        ad_account = AdAccount(ad_account_id)
        audience = ad_account.create_custom_audience(params=audience_payload)
        
        result = {"status": "success", "data": audience.export_all_data()}
        
        # ✅ PERSISTENCIA DE MEMORIA - FUNCIÓN DE CREACIÓN
        _get_resolver().save_action_result(action_name, params, result)
        
        return result
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)

def metaads_list_custom_audiences(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "metaads_list_custom_audiences"
    try:
        _get_meta_ads_api_client(params)
        ad_account_id = _get_ad_account_id(params)
        ad_account = AdAccount(ad_account_id)
        audiences = ad_account.get_custom_audiences(fields=["id", "name", "subtype", "approximate_count"])
        return {"status": "success", "data": [a.export_all_data() for a in audiences]}
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)

def metaads_create_ad_creative(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "metaads_create_ad_creative"
    try:
        _get_meta_ads_api_client(params)
        ad_account_id = _get_ad_account_id(params)
        creative_payload = params.get("creative_payload")
        if not creative_payload:
            raise ValueError("'creative_payload' es requerido.")
        ad_account = AdAccount(ad_account_id)
        creative = ad_account.create_ad_creative(params=creative_payload)
        
        result = {"status": "success", "data": creative.export_all_data()}
        
        # ✅ PERSISTENCIA DE MEMORIA - FUNCIÓN DE CREACIÓN
        _get_resolver().save_action_result(action_name, params, result)
        
        return result
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)

def metaads_get_ad_details(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "metaads_get_ad_details"
    try:
        _get_meta_ads_api_client(params)
        ad_id = params.get("ad_id")
        if not ad_id:
            raise ValueError("'ad_id' es requerido.")
        ad = Ad(ad_id)
        details = ad.api_get(fields=["id", "name", "status", "creative", "tracking_specs", "conversion_specs"])
        return {"status": "success", "data": details.export_all_data()}
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)

def metaads_get_ad_set_insights(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "metaads_get_ad_set_insights"
    try:
        _get_meta_ads_api_client(params)
        ad_set_id = params.get("ad_set_id")
        if not ad_set_id:
            raise ValueError("'ad_set_id' es requerido.")
        ad_set = AdSet(ad_set_id)
        insights = ad_set.get_insights(params=params.get("insights_params", {}))
        return {"status": "success", "data": [i.export_all_data() for i in insights]}
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)

def metaads_get_campaign_insights(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "metaads_get_campaign_insights"
    try:
        _get_meta_ads_api_client(params)
        campaign_id = params.get("campaign_id")
        if not campaign_id:
            raise ValueError("'campaign_id' es requerido.")
        campaign = Campaign(campaign_id)
        insights = campaign.get_insights(params=params.get("insights_params", {}))
        return {"status": "success", "data": [i.export_all_data() for i in insights]}
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)

def metaads_pause_entity(client: Any, params: Dict[str, Any], entity_type: str) -> Dict[str, Any]:
    action_name = f"metaads_pause_{entity_type}"
    try:
        _get_meta_ads_api_client(params)
        entity_id = params.get(f"{entity_type}_id")
        if not entity_id:
            raise ValueError(f"'{entity_type}_id' es requerido.")
        
        entity_map = {
            "campaign": Campaign,
            "ad": Ad,
            "ad_set": AdSet
        }
        
        EntityClass = entity_map.get(entity_type)
        if not EntityClass:
            raise ValueError(f"Tipo de entidad no válido: {entity_type}")
            
        entity = EntityClass(entity_id)
        entity.api_update(params={"status": "PAUSED"})
        updated = entity.api_get(fields=["id", "name", "status"])
        return {"status": "success", "data": updated.export_all_data()}
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)

def metaads_pause_campaign(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    return metaads_pause_entity(client, params, "campaign")

def metaads_pause_ad(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    return metaads_pause_entity(client, params, "ad")

def metaads_pause_ad_set(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    return metaads_pause_entity(client, params, "ad_set")

def metaads_get_pixel_events(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "metaads_get_pixel_events"
    try:
        _get_meta_ads_api_client(params)
        pixel_id = params.get("pixel_id")
        if not pixel_id:
            raise ValueError("'pixel_id' es requerido.")
        
        ad_account_id = _get_ad_account_id(params)
        ad_account = AdAccount(ad_account_id)
        events = ad_account.get_pixels(fields=["id", "name", "code", "last_fired_time"])
        return {"status": "success", "data": [e.export_all_data() for e in events]}
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)


# ============================================================================
# FUNCIONES ADICIONALES RESTAURADAS
# ============================================================================

def metaads_get_audience_insights(params: Dict[str, Any]) -> Dict[str, Any]:
    """Obtener insights de audiencia de Meta Ads."""
    action_name = "metaads_get_audience_insights"
    logger.info(f"Ejecutando {action_name} con params: {params}")
    
    try:
        _get_meta_ads_api_client(params)
        
        ad_account_id = _get_ad_account_id(params)
        ad_account = AdAccount(ad_account_id)
        
        # Configurar parámetros para insights de audiencia
        audience_params = {
            'targeting_spec': params.get('targeting_spec', {}),
            'optimization_goal': params.get('optimization_goal', 'REACH'),
            'currency': params.get('currency', 'USD')
        }
        
        # Campos de insights a obtener
        fields = params.get('fields', [
            'audience_size_lower_bound',
            'audience_size_upper_bound',
            'cpm',
            'cpc',
            'ctr'
        ])
        
        # Obtener delivery estimate (estimación de entrega)
        delivery_estimate = ad_account.get_delivery_estimate(
            optimization_goal=audience_params['optimization_goal'],
            targeting_spec=audience_params['targeting_spec'],
            fields=fields
        )
        
        insights_data = []
        for estimate in delivery_estimate:
            data = estimate.export_all_data()
            insights_data.append(data)
        
        # También obtener información adicional de targeting
        targeting_search = ad_account.get_targeting_browse(
            type='interests',
            limit=params.get('interest_limit', 50)
        )
        
        interests_data = []
        for interest in targeting_search:
            interests_data.append(interest.export_all_data())
        
        # Obtener sugerencias de audiencia similar
        lookalike_params = params.get('lookalike_source')
        lookalike_data = []
        if lookalike_params:
            try:
                lookalike_audiences = ad_account.get_custom_audiences(
                    fields=['name', 'approximate_count', 'lookalike_spec'],
                    params={'limit': 20}
                )
                for audience in lookalike_audiences:
                    audience_data = audience.export_all_data()
                    if audience_data.get('lookalike_spec'):
                        lookalike_data.append(audience_data)
            except Exception as lookalike_error:
                logger.warning(f"Error obteniendo audiencias lookalike: {lookalike_error}")
        
        result = {
            "delivery_estimates": insights_data,
            "available_interests": interests_data[:10],  # Limitar a 10 primeros
            "lookalike_audiences": lookalike_data,
            "targeting_spec": audience_params['targeting_spec'],
            "account_id": ad_account_id,
            "currency": audience_params['currency']
        }
        
        logger.info(f"Insights de audiencia obtenidos para cuenta {ad_account_id}")
        return {"status": "success", "data": result}
        
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)

# --- FIN DEL MÓDULO actions/metaads_actions.py ---