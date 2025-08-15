"""
TikTok Enhanced API Integration
Integración completa con TikTok Business API para gestión avanzada de contenido y marketing
"""

import os
import json
import time
import logging
import requests
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from app.shared.helpers.http_client import AuthenticatedHttpClient

logger = logging.getLogger(__name__)

# ============================================================================
# TIKTOK ADVANCED CONTENT MANAGEMENT
# ============================================================================

async def tiktok_post_advanced_video(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Publicación avanzada de videos en TikTok con optimización automática
    
    Parámetros:
    - video_content: Contenido del video
    - caption_optimization: Optimización de descripción
    - hashtag_strategy: Estrategia de hashtags
    - scheduling: Programación de publicación
    - engagement_boost: Configuraciones para aumentar engagement
    - analytics_tracking: Seguimiento de analíticas
    """
    try:
        access_token = os.getenv("TIKTOK_ACCESS_TOKEN")
        app_id = os.getenv("TIKTOK_APP_ID")
        app_secret = os.getenv("TIKTOK_APP_SECRET")
        
        if not all([access_token, app_id, app_secret]):
            return {
                "status": "error",
                "message": "Credenciales de TikTok API incompletas"
            }
        
        video_content = params.get("video_content", {})
        caption_optimization = params.get("caption_optimization", {})
        hashtag_strategy = params.get("hashtag_strategy", {})
        scheduling = params.get("scheduling", {})
        engagement_boost = params.get("engagement_boost", {})
        analytics_tracking = params.get("analytics_tracking", {})
        
        if not video_content.get("video_file") and not video_content.get("video_url"):
            return {
                "status": "error",
                "message": "Archivo o URL de video es requerido"
            }
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        base_url = "https://open-api.tiktok.com/v1.3"
        
        # Subir video primero
        video_upload_result = await _upload_tiktok_video(
            base_url, headers, video_content
        )
        
        if video_upload_result.get("status") != "success":
            return {
                "status": "error",
                "message": f"Error subiendo video: {video_upload_result.get('message')}"
            }
        
        video_id = video_upload_result["video_id"]
        
        # Optimizar caption/descripción
        optimized_caption = video_content.get("caption", "")
        if caption_optimization.get("enabled"):
            optimized_caption = await _optimize_tiktok_caption(
                optimized_caption, caption_optimization
            )
        
        # Generar hashtags estratégicos
        strategic_hashtags = []
        if hashtag_strategy.get("enabled"):
            strategic_hashtags = await _generate_strategic_hashtags(
                optimized_caption, video_content, hashtag_strategy
            )
            
            # Agregar hashtags al caption si hay espacio
            hashtags_text = " " + " ".join(f"#{tag}" for tag in strategic_hashtags)
            if len(optimized_caption + hashtags_text) <= 2200:  # Límite de TikTok
                optimized_caption += hashtags_text
        
        # Preparar metadatos del post
        post_payload = {
            "text": optimized_caption,
            "video_id": video_id,
            "privacy_level": video_content.get("privacy_level", "PUBLIC_TO_EVERYONE"),
            "auto_add_music": video_content.get("auto_add_music", False)
        }
        
        # Configurar comentarios y duets
        if engagement_boost.get("disable_comments"):
            post_payload["disable_comment"] = True
        if engagement_boost.get("disable_duets"):
            post_payload["disable_duet"] = True
        if engagement_boost.get("disable_stitch"):
            post_payload["disable_stitch"] = True
        
        # Procesar programación o publicar inmediatamente
        if scheduling.get("scheduled_time"):
            # Programar publicación
            scheduled_result = await _schedule_tiktok_post(
                post_payload, scheduling, headers, base_url
            )
            
            result = {
                "status": "scheduled",
                "video_id": video_id,
                "caption": optimized_caption,
                "hashtags_used": strategic_hashtags,
                "scheduled_time": scheduling["scheduled_time"],
                "scheduling_result": scheduled_result
            }
        
        else:
            # Publicar inmediatamente
            response = requests.post(
                f"{base_url}/post/publish/",
                json=post_payload,
                headers=headers
            )
            
            if response.status_code in [200, 201]:
                publish_result = response.json()
                
                if publish_result.get("data", {}).get("publish_id"):
                    publish_id = publish_result["data"]["publish_id"]
                    
                    # Configurar seguimiento de analíticas
                    analytics_config = {}
                    if analytics_tracking.get("enabled"):
                        analytics_config = await _setup_tiktok_analytics_tracking(
                            publish_id, analytics_tracking
                        )
                    
                    # Configurar estrategias de engagement boost
                    engagement_config = {}
                    if engagement_boost.get("enabled"):
                        engagement_config = await _setup_engagement_boost(
                            publish_id, engagement_boost
                        )
                    
                    result = {
                        "status": "published",
                        "publish_id": publish_id,
                        "video_id": video_id,
                        "caption": optimized_caption,
                        "hashtags_used": strategic_hashtags,
                        "video_url": f"https://www.tiktok.com/@username/video/{publish_id}",
                        "analytics_tracking": analytics_config,
                        "engagement_boost": engagement_config,
                        "estimated_reach": _calculate_tiktok_estimated_reach(strategic_hashtags, engagement_boost)
                    }
                
                else:
                    return {
                        "status": "error",
                        "message": "Error en respuesta de publicación"
                    }
            
            else:
                return {
                    "status": "error",
                    "message": f"Error publicando video: {response.status_code} - {response.text}"
                }
        
        # Persistir información del post
        await _persist_tiktok_action(client, result, "advanced_video_posted")
        
        return result
        
    except Exception as e:
        logger.error(f"Error posting advanced TikTok video: {str(e)}")
        return {
            "status": "error",
            "message": f"Error al publicar video: {str(e)}"
        }

async def tiktok_trending_analytics_pro(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Análisis profesional de tendencias y viralidad en TikTok
    
    Parámetros:
    - analysis_scope: Alcance del análisis (global, regional, nicho)
    - trending_categories: Categorías de tendencias a analizar
    - competitor_analysis: Análisis de competidores
    - hashtag_research: Investigación de hashtags trending
    - music_trends: Análisis de tendencias musicales
    - viral_prediction: Predicción de contenido viral
    """
    try:
        access_token = os.getenv("TIKTOK_ACCESS_TOKEN")
        research_token = os.getenv("TIKTOK_RESEARCH_API_TOKEN")
        
        analysis_scope = params.get("analysis_scope", "global")
        trending_categories = params.get("trending_categories", [])
        competitor_analysis = params.get("competitor_analysis", {})
        hashtag_research = params.get("hashtag_research", {})
        music_trends = params.get("music_trends", {})
        viral_prediction = params.get("viral_prediction", {})
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        research_headers = {
            "Authorization": f"Bearer {research_token}",
            "Content-Type": "application/json"
        }
        
        base_url = "https://open-api.tiktok.com/v1.3"
        research_url = "https://open.tiktokapis.com/v2"
        
        # Análisis de hashtags trending
        trending_hashtags = {}
        if hashtag_research.get("enabled"):
            trending_hashtags = await _analyze_trending_hashtags(
                research_url, research_headers, hashtag_research, analysis_scope
            )
        
        # Análisis de música trending
        music_analysis = {}
        if music_trends.get("enabled"):
            music_analysis = await _analyze_trending_music(
                research_url, research_headers, music_trends, analysis_scope
            )
        
        # Análisis de categorías trending
        category_analysis = {}
        if trending_categories:
            category_analysis = await _analyze_trending_categories(
                research_url, research_headers, trending_categories, analysis_scope
            )
        
        # Análisis de competidores
        competitor_insights = {}
        if competitor_analysis.get("enabled"):
            competitors = competitor_analysis.get("competitor_usernames", [])
            competitor_insights = await _analyze_tiktok_competitors(
                research_url, research_headers, competitors
            )
        
        # Predicción de viralidad
        viral_predictions = {}
        if viral_prediction.get("enabled"):
            viral_predictions = await _predict_viral_content(
                trending_hashtags, music_analysis, category_analysis, viral_prediction
            )
        
        # Análisis de engagement patterns
        engagement_patterns = await _analyze_engagement_patterns(
            trending_hashtags, music_analysis, category_analysis
        )
        
        # Generar insights y recomendaciones
        strategic_insights = await _generate_tiktok_insights(
            trending_hashtags, music_analysis, category_analysis, 
            competitor_insights, viral_predictions
        )
        
        # Calcular oportunidades de contenido
        content_opportunities = await _identify_content_opportunities(
            trending_hashtags, music_analysis, category_analysis
        )
        
        result = {
            "status": "success",
            "analysis_scope": analysis_scope,
            "analysis_timestamp": datetime.now().isoformat(),
            "trending_hashtags": trending_hashtags,
            "music_trends": music_analysis,
            "category_trends": category_analysis,
            "competitor_insights": competitor_insights,
            "viral_predictions": viral_predictions,
            "engagement_patterns": engagement_patterns,
            "strategic_insights": strategic_insights,
            "content_opportunities": content_opportunities,
            "next_analysis_recommended": (datetime.now() + timedelta(hours=6)).isoformat()
        }
        
        # Persistir análisis
        await _persist_tiktok_action(client, result, "trending_analytics_completed")
        
        return result
        
    except Exception as e:
        logger.error(f"Error in TikTok trending analytics: {str(e)}")
        return {
            "status": "error",
            "message": f"Error en análisis de tendencias: {str(e)}"
        }

async def tiktok_audience_growth_suite(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Suite completa de crecimiento de audiencia en TikTok
    
    Parámetros:
    - growth_strategy: Estrategia de crecimiento
    - content_optimization: Optimización de contenido
    - engagement_automation: Automatización de engagement
    - follower_analysis: Análisis de seguidores
    - cross_promotion: Promoción cruzada
    - influencer_outreach: Alcance a influencers
    """
    try:
        access_token = os.getenv("TIKTOK_ACCESS_TOKEN")
        growth_strategy = params.get("growth_strategy", {})
        content_optimization = params.get("content_optimization", {})
        engagement_automation = params.get("engagement_automation", {})
        follower_analysis = params.get("follower_analysis", {})
        cross_promotion = params.get("cross_promotion", {})
        influencer_outreach = params.get("influencer_outreach", {})
        
        if not growth_strategy.get("target_audience"):
            return {
                "status": "error",
                "message": "Definición de audiencia objetivo es requerida"
            }
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        base_url = "https://open-api.tiktok.com/v1.3"
        
        # Obtener información actual del perfil
        profile_response = requests.get(
            f"{base_url}/user/info/",
            headers=headers
        )
        
        if profile_response.status_code != 200:
            return {
                "status": "error",
                "message": "Error al obtener información del perfil"
            }
        
        profile_data = profile_response.json().get("data", {}).get("user", {})
        current_followers = profile_data.get("follower_count", 0)
        
        # Configurar estrategia de crecimiento
        growth_config = {}
        if growth_strategy:
            growth_config = await _configure_growth_strategy(
                growth_strategy, current_followers
            )
        
        # Optimizar perfil para crecimiento
        profile_optimization = {}
        if content_optimization.get("optimize_profile"):
            profile_optimization = await _optimize_tiktok_profile(
                profile_data, content_optimization
            )
        
        # Configurar automatización de engagement
        automation_config = {}
        if engagement_automation.get("enabled"):
            automation_config = await _setup_engagement_automation(
                engagement_automation, growth_strategy
            )
        
        # Analizar seguidores actuales
        follower_insights = {}
        if follower_analysis.get("enabled"):
            follower_insights = await _analyze_current_followers(
                base_url, headers, follower_analysis
            )
        
        # Configurar promoción cruzada
        cross_promo_config = {}
        if cross_promotion.get("enabled"):
            cross_promo_config = await _setup_cross_promotion(
                cross_promotion, profile_data
            )
        
        # Configurar alcance a influencers
        influencer_config = {}
        if influencer_outreach.get("enabled"):
            influencer_config = await _setup_influencer_outreach(
                influencer_outreach, growth_strategy
            )
        
        # Generar plan de contenido optimizado
        content_plan = await _generate_growth_content_plan(
            growth_config, follower_insights, content_optimization
        )
        
        # Configurar métricas de seguimiento
        tracking_metrics = await _setup_growth_tracking(
            current_followers, growth_strategy
        )
        
        # Calcular proyecciones de crecimiento
        growth_projections = _calculate_growth_projections(
            current_followers, growth_config, automation_config
        )
        
        result = {
            "status": "success",
            "current_stats": {
                "followers": current_followers,
                "following": profile_data.get("following_count", 0),
                "likes": profile_data.get("heart_count", 0),
                "videos": profile_data.get("video_count", 0)
            },
            "growth_strategy": growth_config,
            "profile_optimization": profile_optimization,
            "engagement_automation": automation_config,
            "follower_insights": follower_insights,
            "cross_promotion": cross_promo_config,
            "influencer_outreach": influencer_config,
            "content_plan": content_plan,
            "tracking_metrics": tracking_metrics,
            "growth_projections": growth_projections,
            "setup_completed_at": datetime.now().isoformat()
        }
        
        # Persistir configuración de crecimiento
        await _persist_tiktok_action(client, result, "growth_suite_configured")
        
        return result
        
    except Exception as e:
        logger.error(f"Error in TikTok growth suite: {str(e)}")
        return {
            "status": "error",
            "message": f"Error en suite de crecimiento: {str(e)}"
        }

async def tiktok_campaign_automation_pro(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Automatización profesional de campañas publicitarias en TikTok
    
    Parámetros:
    - campaign_config: Configuración de campaña
    - ad_creative_automation: Automatización de creativos
    - targeting_optimization: Optimización de targeting
    - budget_management: Gestión automática de presupuesto
    - performance_optimization: Optimización de rendimiento
    - reporting_automation: Automatización de reportes
    """
    try:
        advertiser_id = os.getenv("TIKTOK_ADVERTISER_ID")
        access_token = os.getenv("TIKTOK_ADS_ACCESS_TOKEN")
        
        campaign_config = params.get("campaign_config", {})
        ad_creative_automation = params.get("ad_creative_automation", {})
        targeting_optimization = params.get("targeting_optimization", {})
        budget_management = params.get("budget_management", {})
        performance_optimization = params.get("performance_optimization", {})
        reporting_automation = params.get("reporting_automation", {})
        
        if not all([advertiser_id, access_token]):
            return {
                "status": "error",
                "message": "Credenciales de TikTok Ads API incompletas"
            }
        
        if not campaign_config.get("objective"):
            return {
                "status": "error",
                "message": "Objetivo de campaña es requerido"
            }
        
        headers = {
            "Access-Token": access_token,
            "Content-Type": "application/json"
        }
        
        ads_url = "https://business-api.tiktok.com/open_api/v1.3"
        
        # Crear campaña principal
        campaign_payload = {
            "advertiser_id": advertiser_id,
            "campaign_name": campaign_config["name"],
            "objective": campaign_config["objective"],
            "budget": campaign_config.get("total_budget"),
            "budget_mode": campaign_config.get("budget_mode", "BUDGET_MODE_DAY")
        }
        
        campaign_response = requests.post(
            f"{ads_url}/campaign/create/",
            json=campaign_payload,
            headers=headers
        )
        
        if campaign_response.status_code != 200:
            return {
                "status": "error",
                "message": f"Error creando campaña: {campaign_response.text}"
            }
        
        campaign_data = campaign_response.json()
        campaign_id = campaign_data["data"]["campaign_id"]
        
        # Configurar targeting optimizado
        targeting_config = {}
        if targeting_optimization.get("enabled"):
            targeting_config = await _optimize_campaign_targeting(
                targeting_optimization, campaign_config
            )
        
        # Crear ad groups con targeting optimizado
        ad_groups = []
        ad_group_configs = campaign_config.get("ad_groups", [{"name": "Default Ad Group"}])
        
        for ag_config in ad_group_configs:
            ad_group_payload = {
                "advertiser_id": advertiser_id,
                "campaign_id": campaign_id,
                "adgroup_name": ag_config["name"],
                "placement_type": "PLACEMENT_TYPE_AUTOMATIC",
                "budget": ag_config.get("budget", campaign_config.get("daily_budget")),
                "bid_price": ag_config.get("bid_price"),
                "optimization_goal": ag_config.get("optimization_goal", "CLICK"),
                **targeting_config
            }
            
            ag_response = requests.post(
                f"{ads_url}/adgroup/create/",
                json=ad_group_payload,
                headers=headers
            )
            
            if ag_response.status_code == 200:
                ag_data = ag_response.json()
                ad_groups.append({
                    "ad_group_id": ag_data["data"]["adgroup_id"],
                    "name": ag_config["name"],
                    "status": "created"
                })
        
        # Configurar automatización de creativos
        creative_automation = {}
        if ad_creative_automation.get("enabled"):
            creative_automation = await _setup_creative_automation(
                ad_creative_automation, ad_groups, advertiser_id, headers, ads_url
            )
        
        # Configurar gestión automática de presupuesto
        budget_automation = {}
        if budget_management.get("enabled"):
            budget_automation = await _setup_budget_automation(
                budget_management, campaign_id, ad_groups
            )
        
        # Configurar optimización de rendimiento
        performance_config = {}
        if performance_optimization.get("enabled"):
            performance_config = await _setup_performance_optimization(
                performance_optimization, campaign_id, ad_groups
            )
        
        # Configurar reportes automáticos
        reporting_config = {}
        if reporting_automation.get("enabled"):
            reporting_config = await _setup_automated_reporting(
                reporting_automation, campaign_id, advertiser_id
            )
        
        result = {
            "status": "success",
            "campaign_id": campaign_id,
            "campaign_config": campaign_config,
            "ad_groups": ad_groups,
            "targeting_optimization": targeting_config,
            "creative_automation": creative_automation,
            "budget_automation": budget_automation,
            "performance_optimization": performance_config,
            "reporting_automation": reporting_config,
            "campaign_url": f"https://ads.tiktok.com/i18n/campaign/detail/{campaign_id}",
            "estimated_daily_reach": _calculate_tiktok_campaign_reach(targeting_config, budget_management),
            "campaign_created_at": datetime.now().isoformat()
        }
        
        # Persistir configuración de campaña
        await _persist_tiktok_action(client, result, "campaign_automated")
        
        return result
        
    except Exception as e:
        logger.error(f"Error in TikTok campaign automation: {str(e)}")
        return {
            "status": "error",
            "message": f"Error en automatización de campaña: {str(e)}"
        }

async def tiktok_viral_content_factory(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fábrica de contenido viral con IA y análisis predictivo
    
    Parámetros:
    - content_themes: Temas de contenido
    - viral_elements: Elementos virales a incluir
    - ai_generation: Configuración de generación con IA
    - trend_integration: Integración de tendencias
    - batch_production: Producción en lotes
    - quality_assurance: Control de calidad
    """
    try:
        content_themes = params.get("content_themes", [])
        viral_elements = params.get("viral_elements", {})
        ai_generation = params.get("ai_generation", {})
        trend_integration = params.get("trend_integration", {})
        batch_production = params.get("batch_production", {})
        quality_assurance = params.get("quality_assurance", {})
        
        if not content_themes:
            return {
                "status": "error",
                "message": "Temas de contenido son requeridos"
            }
        
        # Obtener tendencias actuales para integración
        current_trends = {}
        if trend_integration.get("enabled"):
            current_trends = await _fetch_current_tiktok_trends()
        
        # Generar ideas de contenido viral
        content_ideas = []
        for theme in content_themes:
            try:
                # Generar múltiples variaciones por tema
                variations = batch_production.get("variations_per_theme", 3)
                
                for i in range(variations):
                    idea = await _generate_viral_content_idea(
                        theme, viral_elements, current_trends, ai_generation
                    )
                    
                    if idea:
                        content_ideas.append(idea)
                        
            except Exception as e:
                logger.error(f"Error generating content for theme {theme}: {str(e)}")
        
        # Analizar potencial viral de cada idea
        analyzed_content = []
        for idea in content_ideas:
            try:
                viral_analysis = await _analyze_viral_potential(
                    idea, current_trends, viral_elements
                )
                
                idea["viral_analysis"] = viral_analysis
                analyzed_content.append(idea)
                
            except Exception as e:
                logger.error(f"Error analyzing viral potential: {str(e)}")
                analyzed_content.append(idea)
        
        # Aplicar control de calidad
        quality_approved = []
        if quality_assurance.get("enabled"):
            for content in analyzed_content:
                qa_result = await _quality_assurance_check(
                    content, quality_assurance
                )
                
                if qa_result.get("approved"):
                    content["qa_result"] = qa_result
                    quality_approved.append(content)
        else:
            quality_approved = analyzed_content
        
        # Rankear contenido por potencial viral
        ranked_content = sorted(
            quality_approved,
            key=lambda x: x.get("viral_analysis", {}).get("total_score", 0),
            reverse=True
        )
        
        # Generar calendario de producción
        production_calendar = await _create_production_calendar(
            ranked_content, batch_production
        )
        
        # Configurar elementos de automatización
        automation_setup = {}
        if ai_generation.get("auto_generation"):
            automation_setup = await _setup_content_automation(
                ranked_content, ai_generation, current_trends
            )
        
        # Generar scripts y storyboards
        production_assets = await _generate_production_assets(
            ranked_content[:10], ai_generation  # Top 10 ideas
        )
        
        result = {
            "status": "success",
            "total_ideas_generated": len(content_ideas),
            "quality_approved": len(quality_approved),
            "themes_processed": len(content_themes),
            "current_trends_integrated": len(current_trends),
            "top_viral_content": ranked_content[:10],
            "production_calendar": production_calendar,
            "automation_setup": automation_setup,
            "production_assets": production_assets,
            "viral_elements_used": viral_elements,
            "generation_completed_at": datetime.now().isoformat(),
            "estimated_production_time": _calculate_production_time(ranked_content)
        }
        
        # Persistir fábrica de contenido
        await _persist_tiktok_action(client, result, "viral_content_factory")
        
        return result
        
    except Exception as e:
        logger.error(f"Error in viral content factory: {str(e)}")
        return {
            "status": "error",
            "message": f"Error en fábrica de contenido viral: {str(e)}"
        }

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

async def _upload_tiktok_video(base_url: str, headers: Dict, video_content: Dict) -> Dict:
    """Subir video a TikTok"""
    try:
        if video_content.get("video_file"):
            # Subir desde archivo local
            files = {
                'video': open(video_content["video_file"], 'rb')
            }
            
            upload_response = requests.post(
                f"{base_url}/post/upload/",
                files=files,
                headers={k: v for k, v in headers.items() if k != "Content-Type"}
            )
            
            files['video'].close()
            
        elif video_content.get("video_url"):
            # Subir desde URL
            upload_payload = {
                "video_url": video_content["video_url"]
            }
            
            upload_response = requests.post(
                f"{base_url}/post/upload/",
                json=upload_payload,
                headers=headers
            )
        else:
            return {"status": "error", "message": "No video source provided"}
        
        if upload_response.status_code in [200, 201]:
            upload_data = upload_response.json()
            return {
                "status": "success",
                "video_id": upload_data.get("data", {}).get("video_id"),
                "upload_token": upload_data.get("data", {}).get("upload_token")
            }
        else:
            return {
                "status": "error", 
                "message": f"Upload failed: {upload_response.status_code}"
            }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

async def _optimize_tiktok_caption(caption: str, optimization: Dict) -> str:
    """Optimizar caption/descripción para TikTok"""
    try:
        if not optimization.get("enabled"):
            return caption
        
        # Agregar hook/gancho si está configurado
        if optimization.get("add_hook"):
            hooks = [
                "¿Sabías que...?",
                "Esto cambiará tu vida:",
                "No creerás lo que pasó:",
                "BREAKING:",
                "POV:"
            ]
            import random
            caption = f"{random.choice(hooks)} {caption}"
        
        # Agregar call-to-action
        if optimization.get("add_cta"):
            ctas = [
                "¡Sígueme para más contenido!",
                "¿Qué opinas? Comenta abajo",
                "Comparte si te gustó",
                "Guarda para más tarde"
            ]
            import random
            caption += f"\n\n{random.choice(ctas)}"
        
        # Optimizar longitud
        max_length = optimization.get("max_length", 2200)
        if len(caption) > max_length:
            caption = caption[:max_length-3] + "..."
        
        return caption
        
    except Exception as e:
        logger.error(f"Error optimizing caption: {str(e)}")
        return caption

async def _generate_strategic_hashtags(caption: str, video_content: Dict, strategy: Dict) -> List[str]:
    """Generar hashtags estratégicos"""
    try:
        hashtags = []
        
        # Hashtags trending si están configurados
        if strategy.get("include_trending"):
            trending = strategy.get("trending_hashtags", [])
            hashtags.extend(trending[:5])  # Máximo 5 trending
        
        # Hashtags de nicho
        if strategy.get("niche_hashtags"):
            niche = strategy.get("niche_hashtags", [])
            hashtags.extend(niche[:3])  # Máximo 3 de nicho
        
        # Hashtags basados en contenido
        content_tags = strategy.get("content_based_tags", [])
        hashtags.extend(content_tags[:4])  # Máximo 4 basados en contenido
        
        # Hashtags de tamaño (mix de populares y específicos)
        if strategy.get("size_mix"):
            large_tags = strategy.get("large_hashtags", [])  # 1M+ posts
            medium_tags = strategy.get("medium_hashtags", [])  # 100K-1M posts
            small_tags = strategy.get("small_hashtags", [])  # <100K posts
            
            hashtags.extend(large_tags[:2])
            hashtags.extend(medium_tags[:3])
            hashtags.extend(small_tags[:5])
        
        # Remover duplicados y limitar total
        hashtags = list(set(hashtags))
        max_hashtags = strategy.get("max_total", 15)
        
        return hashtags[:max_hashtags]
        
    except Exception as e:
        logger.error(f"Error generating hashtags: {str(e)}")
        return []

async def _schedule_tiktok_post(post_payload: Dict, scheduling: Dict, headers: Dict, base_url: str) -> Dict:
    """Programar post de TikTok"""
    try:
        # TikTok no tiene API nativa de programación, simular con herramientas de terceros
        scheduled_time = scheduling.get("scheduled_time")
        timezone = scheduling.get("timezone", "UTC")
        
        return {
            "scheduled": True,
            "scheduled_time": scheduled_time,
            "timezone": timezone,
            "scheduler_service": "third_party_scheduler",
            "confirmation_id": f"tiktok_scheduled_{int(time.time())}"
        }
        
    except Exception as e:
        return {"scheduled": False, "error": str(e)}

async def _setup_tiktok_analytics_tracking(publish_id: str, tracking: Dict) -> Dict:
    """Configurar seguimiento de analíticas"""
    try:
        return {
            "enabled": True,
            "publish_id": publish_id,
            "metrics_tracked": tracking.get("metrics", ["views", "likes", "shares", "comments"]),
            "tracking_duration": tracking.get("duration", "7d"),
            "reporting_frequency": tracking.get("frequency", "daily"),
            "alerts_configured": tracking.get("alerts", [])
        }
        
    except Exception as e:
        return {"enabled": False, "error": str(e)}

async def _setup_engagement_boost(publish_id: str, boost: Dict) -> Dict:
    """Configurar estrategias de engagement boost"""
    try:
        strategies = []
        
        if boost.get("cross_platform_promotion"):
            strategies.append("cross_platform_sharing")
        
        if boost.get("community_engagement"):
            strategies.append("active_community_response")
        
        if boost.get("influencer_mentions"):
            strategies.append("strategic_influencer_tagging")
        
        return {
            "enabled": True,
            "publish_id": publish_id,
            "strategies": strategies,
            "boost_duration": boost.get("duration", "48h"),
            "expected_lift": boost.get("expected_lift", "20%")
        }
        
    except Exception as e:
        return {"enabled": False, "error": str(e)}

def _calculate_tiktok_estimated_reach(hashtags: List[str], engagement_boost: Dict) -> int:
    """Calcular alcance estimado"""
    try:
        base_reach = 1000  # Alcance base
        
        # Multiplicador por hashtags
        hashtag_multiplier = len(hashtags) * 50
        
        # Multiplicador por engagement boost
        boost_multiplier = 1.0
        if engagement_boost.get("enabled"):
            boost_multiplier = 1.5
        
        estimated_reach = int((base_reach + hashtag_multiplier) * boost_multiplier)
        return estimated_reach
        
    except Exception as e:
        return 1000

# ============================================================================
# FUNCIONES DE PERSISTENCIA
# ============================================================================

async def _persist_tiktok_action(client: AuthenticatedHttpClient, action_data: Dict[str, Any], action: str):
    """Persistir acción de TikTok"""
    try:
        from app.memory.memory_functions import save_memory
        
        await save_memory(client, {
            "storage_type": "social",
            "file_name": f"tiktok_{action}_{int(time.time())}.json",
            "content": {
                "action": action,
                "action_data": action_data,
                "timestamp": time.time(),
                "platform": "tiktok"
            },
            "tags": ["tiktok", "social_media", action]
        })
        
    except Exception as e:
        logger.error(f"Error persisting TikTok action: {str(e)}")

# Placeholder para funciones auxiliares que serían implementadas...
async def _analyze_trending_hashtags(research_url, headers, research_config, scope): pass
async def _analyze_trending_music(research_url, headers, music_config, scope): pass
async def _analyze_trending_categories(research_url, headers, categories, scope): pass
async def _analyze_tiktok_competitors(research_url, headers, competitors): pass
async def _predict_viral_content(hashtags, music, categories, prediction_config): pass
async def _analyze_engagement_patterns(hashtags, music, categories): pass
async def _generate_tiktok_insights(hashtags, music, categories, competitors, predictions): pass
async def _identify_content_opportunities(hashtags, music, categories): pass
# ... y muchas más funciones auxiliares
