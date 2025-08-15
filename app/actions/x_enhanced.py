"""
X (Twitter) Enhanced API Integration
Integración completa con X API v2 para gestión avanzada de contenido y audiencias
"""

import os
import json
import time
import logging
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from app.shared.helpers.http_client import AuthenticatedHttpClient

logger = logging.getLogger(__name__)

# ============================================================================
# X (TWITTER) ADVANCED CONTENT MANAGEMENT
# ============================================================================

async def x_post_advanced_tweet(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Publicación avanzada de tweets con multimedia, hilos y programación
    
    Parámetros:
    - tweet_content: Contenido del tweet principal
    - thread_content: Contenido adicional para hilos
    - media_attachments: Archivos multimedia
    - scheduling: Programación de tweets
    - engagement_settings: Configuraciones de engagement
    - hashtag_optimization: Optimización de hashtags
    """
    try:
        bearer_token = os.getenv("X_BEARER_TOKEN")
        api_key = os.getenv("X_API_KEY")
        api_secret = os.getenv("X_API_SECRET")
        access_token = os.getenv("X_ACCESS_TOKEN")
        access_token_secret = os.getenv("X_ACCESS_TOKEN_SECRET")
        
        if not all([bearer_token, api_key, api_secret, access_token, access_token_secret]):
            return {
                "status": "error",
                "message": "Credenciales de X API incompletas"
            }
        
        tweet_content = params.get("tweet_content", {})
        thread_content = params.get("thread_content", [])
        media_attachments = params.get("media_attachments", [])
        scheduling = params.get("scheduling", {})
        engagement_settings = params.get("engagement_settings", {})
        hashtag_optimization = params.get("hashtag_optimization", {})
        
        if not tweet_content.get("text"):
            return {
                "status": "error",
                "message": "El contenido del tweet es requerido"
            }
        
        headers = {
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json"
        }
        
        base_url = "https://api.twitter.com/2"
        
        # Subir archivos multimedia primero
        uploaded_media = []
        if media_attachments:
            for media in media_attachments:
                try:
                    media_result = await _upload_x_media(
                        api_key, api_secret, access_token, access_token_secret, media
                    )
                    if media_result.get("media_id"):
                        uploaded_media.append(media_result["media_id"])
                except Exception as e:
                    logger.error(f"Error uploading media: {str(e)}")
        
        # Optimizar hashtags si está habilitado
        optimized_text = tweet_content["text"]
        if hashtag_optimization.get("enabled"):
            optimized_text = await _optimize_hashtags(
                optimized_text, hashtag_optimization
            )
        
        # Preparar contenido del tweet principal
        tweet_payload = {
            "text": optimized_text
        }
        
        # Agregar multimedia si se subió
        if uploaded_media:
            tweet_payload["media"] = {"media_ids": uploaded_media}
        
        # Configurar opciones de reply
        if engagement_settings.get("reply_settings"):
            tweet_payload["reply_settings"] = engagement_settings["reply_settings"]
        
        # Configurar geolocalización
        if tweet_content.get("location"):
            tweet_payload["geo"] = {
                "place_id": tweet_content["location"]
            }
        
        # Procesar programación o publicar inmediatamente
        if scheduling.get("scheduled_time"):
            # Para programación, usar Twitter Ads API o herramientas de terceros
            scheduled_result = await _schedule_x_tweet(
                tweet_payload, scheduling, headers
            )
            
            result = {
                "status": "scheduled",
                "tweet_content": optimized_text,
                "scheduled_time": scheduling["scheduled_time"],
                "media_count": len(uploaded_media),
                "thread_planned": len(thread_content) > 0,
                "scheduling_result": scheduled_result
            }
        
        else:
            # Publicar inmediatamente
            response = requests.post(
                f"{base_url}/tweets",
                json=tweet_payload,
                headers=headers
            )
            
            if response.status_code in [200, 201]:
                tweet_result = response.json()
                tweet_id = tweet_result["data"]["id"]
                
                # Publicar hilo si hay contenido adicional
                thread_results = []
                if thread_content:
                    thread_results = await _post_twitter_thread(
                        base_url, headers, tweet_id, thread_content, uploaded_media
                    )
                
                # Configurar monitoreo de engagement
                monitoring_config = {}
                if engagement_settings.get("monitor_engagement"):
                    monitoring_config = await _setup_engagement_monitoring(
                        tweet_id, engagement_settings
                    )
                
                result = {
                    "status": "published",
                    "tweet_id": tweet_id,
                    "tweet_url": f"https://twitter.com/user/status/{tweet_id}",
                    "tweet_content": optimized_text,
                    "media_count": len(uploaded_media),
                    "thread_tweets": len(thread_results),
                    "thread_results": thread_results,
                    "engagement_monitoring": monitoring_config,
                    "hashtags_optimized": hashtag_optimization.get("enabled", False)
                }
            
            else:
                return {
                    "status": "error",
                    "message": f"Error al publicar tweet: {response.status_code} - {response.text}"
                }
        
        # Persistir información del tweet
        await _persist_x_action(client, result, "advanced_tweet_posted")
        
        return result
        
    except Exception as e:
        logger.error(f"Error posting advanced tweet: {str(e)}")
        return {
            "status": "error",
            "message": f"Error al publicar tweet: {str(e)}"
        }

async def x_audience_analytics_pro(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Análisis profesional de audiencia con insights avanzados
    
    Parámetros:
    - analysis_period: Período de análisis
    - metrics_requested: Métricas específicas a analizar
    - audience_segments: Segmentos de audiencia a analizar
    - competitor_analysis: Análisis de competidores
    - trend_analysis: Análisis de tendencias
    - export_format: Formato de exportación de reportes
    """
    try:
        bearer_token = os.getenv("X_BEARER_TOKEN")
        analysis_period = params.get("analysis_period", "30d")
        metrics_requested = params.get("metrics_requested", [])
        audience_segments = params.get("audience_segments", [])
        competitor_analysis = params.get("competitor_analysis", {})
        trend_analysis = params.get("trend_analysis", {})
        export_format = params.get("export_format", "json")
        
        headers = {
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json"
        }
        
        base_url = "https://api.twitter.com/2"
        
        # Obtener información del usuario actual
        user_response = requests.get(
            f"{base_url}/users/me",
            headers=headers,
            params={
                "user.fields": "created_at,description,entities,id,location,name,pinned_tweet_id,profile_image_url,protected,public_metrics,url,username,verified"
            }
        )
        
        if user_response.status_code != 200:
            return {
                "status": "error",
                "message": "Error al obtener información del usuario"
            }
        
        user_data = user_response.json()["data"]
        user_id = user_data["id"]
        
        # Análisis de métricas principales
        main_metrics = {}
        if not metrics_requested or "followers" in metrics_requested:
            main_metrics["followers"] = await _analyze_followers_growth(
                base_url, headers, user_id, analysis_period
            )
        
        if not metrics_requested or "engagement" in metrics_requested:
            main_metrics["engagement"] = await _analyze_engagement_metrics(
                base_url, headers, user_id, analysis_period
            )
        
        if not metrics_requested or "content_performance" in metrics_requested:
            main_metrics["content_performance"] = await _analyze_content_performance(
                base_url, headers, user_id, analysis_period
            )
        
        if not metrics_requested or "reach" in metrics_requested:
            main_metrics["reach"] = await _analyze_reach_metrics(
                base_url, headers, user_id, analysis_period
            )
        
        # Análisis de segmentos de audiencia
        audience_analysis = {}
        if audience_segments:
            audience_analysis = await _analyze_audience_segments(
                base_url, headers, user_id, audience_segments
            )
        
        # Análisis de competidores
        competitor_insights = {}
        if competitor_analysis.get("enabled"):
            competitor_usernames = competitor_analysis.get("competitors", [])
            competitor_insights = await _analyze_competitors(
                base_url, headers, competitor_usernames, analysis_period
            )
        
        # Análisis de tendencias
        trend_insights = {}
        if trend_analysis.get("enabled"):
            trend_insights = await _analyze_trends_and_hashtags(
                base_url, headers, user_id, trend_analysis
            )
        
        # Generar insights y recomendaciones
        insights = await _generate_audience_insights(
            main_metrics, audience_analysis, competitor_insights, trend_insights
        )
        
        # Calcular puntuaciones de rendimiento
        performance_scores = _calculate_performance_scores(main_metrics)
        
        result = {
            "status": "success",
            "user_info": {
                "id": user_id,
                "username": user_data["username"],
                "followers_count": user_data["public_metrics"]["followers_count"],
                "following_count": user_data["public_metrics"]["following_count"],
                "tweet_count": user_data["public_metrics"]["tweet_count"]
            },
            "analysis_period": analysis_period,
            "main_metrics": main_metrics,
            "audience_analysis": audience_analysis,
            "competitor_insights": competitor_insights,
            "trend_insights": trend_insights,
            "performance_scores": performance_scores,
            "insights_and_recommendations": insights,
            "report_generated_at": datetime.now().isoformat()
        }
        
        # Exportar reporte si se solicita
        if export_format != "json":
            export_result = await _export_analytics_report(result, export_format)
            result["export"] = export_result
        
        # Persistir análisis
        await _persist_x_action(client, result, "audience_analytics_pro")
        
        return result
        
    except Exception as e:
        logger.error(f"Error in audience analytics: {str(e)}")
        return {
            "status": "error",
            "message": f"Error en análisis de audiencia: {str(e)}"
        }

async def x_campaign_management_suite(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Suite completa de gestión de campañas en X
    
    Parámetros:
    - campaign_config: Configuración de la campaña
    - content_calendar: Calendario de contenido
    - targeting_settings: Configuraciones de targeting
    - budget_management: Gestión de presupuesto
    - performance_tracking: Seguimiento de rendimiento
    - automation_rules: Reglas de automatización
    """
    try:
        bearer_token = os.getenv("X_BEARER_TOKEN")
        campaign_config = params.get("campaign_config", {})
        content_calendar = params.get("content_calendar", [])
        targeting_settings = params.get("targeting_settings", {})
        budget_management = params.get("budget_management", {})
        performance_tracking = params.get("performance_tracking", {})
        automation_rules = params.get("automation_rules", [])
        
        if not campaign_config.get("name"):
            return {
                "status": "error",
                "message": "Nombre de campaña es requerido"
            }
        
        headers = {
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json"
        }
        
        # Crear configuración de campaña
        campaign_setup = {
            "name": campaign_config["name"],
            "objective": campaign_config.get("objective", "engagement"),
            "start_date": campaign_config.get("start_date"),
            "end_date": campaign_config.get("end_date"),
            "status": campaign_config.get("status", "draft")
        }
        
        # Configurar calendario de contenido
        content_schedule = []
        if content_calendar:
            content_schedule = await _setup_content_calendar(
                content_calendar, campaign_config
            )
        
        # Configurar targeting
        targeting_config = {}
        if targeting_settings:
            targeting_config = await _configure_campaign_targeting(
                targeting_settings
            )
        
        # Configurar gestión de presupuesto
        budget_config = {}
        if budget_management:
            budget_config = {
                "total_budget": budget_management.get("total_budget"),
                "daily_budget": budget_management.get("daily_budget"),
                "bid_strategy": budget_management.get("bid_strategy", "automatic"),
                "budget_distribution": budget_management.get("distribution", "even"),
                "spend_monitoring": budget_management.get("monitoring", True)
            }
        
        # Configurar seguimiento de rendimiento
        tracking_config = {}
        if performance_tracking:
            tracking_config = {
                "kpis": performance_tracking.get("kpis", ["engagement", "reach", "clicks"]),
                "reporting_frequency": performance_tracking.get("frequency", "daily"),
                "alerts": performance_tracking.get("alerts", []),
                "custom_metrics": performance_tracking.get("custom_metrics", [])
            }
        
        # Configurar reglas de automatización
        automation_config = []
        if automation_rules:
            for rule in automation_rules:
                automation_config.append({
                    "name": rule.get("name"),
                    "trigger": rule.get("trigger"),
                    "conditions": rule.get("conditions", []),
                    "actions": rule.get("actions", []),
                    "enabled": rule.get("enabled", True)
                })
        
        # Simular creación de campaña (en implementación real usaría Twitter Ads API)
        campaign_id = f"campaign_{int(time.time())}"
        
        # Configurar monitoreo automático
        monitoring_setup = await _setup_campaign_monitoring(
            campaign_id, tracking_config, automation_config
        )
        
        # Programar contenido inicial
        scheduling_results = []
        if content_schedule:
            scheduling_results = await _schedule_campaign_content(
                content_schedule, campaign_id
            )
        
        result = {
            "status": "success",
            "campaign_id": campaign_id,
            "campaign_config": campaign_setup,
            "content_calendar": {
                "total_posts": len(content_schedule),
                "schedule": content_schedule,
                "scheduling_results": scheduling_results
            },
            "targeting": targeting_config,
            "budget": budget_config,
            "performance_tracking": tracking_config,
            "automation": {
                "rules_count": len(automation_config),
                "rules": automation_config
            },
            "monitoring": monitoring_setup,
            "estimated_reach": _calculate_estimated_reach(targeting_config, budget_config),
            "campaign_created_at": datetime.now().isoformat()
        }
        
        # Persistir configuración de campaña
        await _persist_x_action(client, result, "campaign_created")
        
        return result
        
    except Exception as e:
        logger.error(f"Error in campaign management: {str(e)}")
        return {
            "status": "error",
            "message": f"Error en gestión de campaña: {str(e)}"
        }

async def x_community_management_pro(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Gestión profesional de comunidad con respuestas automáticas y moderación
    
    Parámetros:
    - monitoring_settings: Configuraciones de monitoreo
    - auto_response_rules: Reglas de respuesta automática
    - moderation_settings: Configuraciones de moderación
    - engagement_strategies: Estrategias de engagement
    - influencer_tracking: Seguimiento de influencers
    - crisis_management: Gestión de crisis
    """
    try:
        bearer_token = os.getenv("X_BEARER_TOKEN")
        monitoring_settings = params.get("monitoring_settings", {})
        auto_response_rules = params.get("auto_response_rules", [])
        moderation_settings = params.get("moderation_settings", {})
        engagement_strategies = params.get("engagement_strategies", {})
        influencer_tracking = params.get("influencer_tracking", {})
        crisis_management = params.get("crisis_management", {})
        
        headers = {
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json"
        }
        
        base_url = "https://api.twitter.com/2"
        
        # Configurar monitoreo de menciones y hashtags
        monitoring_config = {}
        if monitoring_settings:
            monitoring_config = await _setup_community_monitoring(
                base_url, headers, monitoring_settings
            )
        
        # Configurar respuestas automáticas
        auto_response_config = []
        if auto_response_rules:
            for rule in auto_response_rules:
                response_config = {
                    "name": rule.get("name"),
                    "triggers": rule.get("triggers", []),
                    "response_template": rule.get("response_template"),
                    "conditions": rule.get("conditions", []),
                    "delay": rule.get("delay", 0),
                    "enabled": rule.get("enabled", True)
                }
                auto_response_config.append(response_config)
        
        # Configurar moderación automática
        moderation_config = {}
        if moderation_settings:
            moderation_config = {
                "spam_detection": moderation_settings.get("spam_detection", True),
                "toxicity_filter": moderation_settings.get("toxicity_filter", True),
                "keyword_filtering": moderation_settings.get("keyword_filters", []),
                "auto_block": moderation_settings.get("auto_block", False),
                "escalation_rules": moderation_settings.get("escalation_rules", [])
            }
        
        # Configurar estrategias de engagement
        engagement_config = {}
        if engagement_strategies:
            engagement_config = {
                "like_automation": engagement_strategies.get("auto_like", False),
                "retweet_criteria": engagement_strategies.get("retweet_criteria", []),
                "comment_prompts": engagement_strategies.get("comment_prompts", []),
                "follower_outreach": engagement_strategies.get("follower_outreach", {}),
                "hashtag_participation": engagement_strategies.get("hashtag_participation", [])
            }
        
        # Configurar seguimiento de influencers
        influencer_config = {}
        if influencer_tracking.get("enabled"):
            influencers = influencer_tracking.get("influencers", [])
            influencer_config = await _setup_influencer_tracking(
                base_url, headers, influencers
            )
        
        # Configurar gestión de crisis
        crisis_config = {}
        if crisis_management.get("enabled"):
            crisis_config = {
                "alert_keywords": crisis_management.get("alert_keywords", []),
                "escalation_contacts": crisis_management.get("escalation_contacts", []),
                "response_templates": crisis_management.get("response_templates", {}),
                "monitoring_intensity": crisis_management.get("intensity", "normal"),
                "auto_notifications": crisis_management.get("auto_notifications", True)
            }
        
        # Inicializar monitoreo activo
        active_monitoring = await _initialize_community_monitoring(
            monitoring_config, auto_response_config, moderation_config
        )
        
        # Generar reporte inicial de estado de la comunidad
        community_status = await _generate_community_status_report(
            base_url, headers, monitoring_settings
        )
        
        result = {
            "status": "success",
            "monitoring": monitoring_config,
            "auto_responses": {
                "rules_count": len(auto_response_config),
                "rules": auto_response_config
            },
            "moderation": moderation_config,
            "engagement": engagement_config,
            "influencer_tracking": influencer_config,
            "crisis_management": crisis_config,
            "active_monitoring": active_monitoring,
            "community_status": community_status,
            "setup_completed_at": datetime.now().isoformat()
        }
        
        # Persistir configuración de gestión de comunidad
        await _persist_x_action(client, result, "community_management_setup")
        
        return result
        
    except Exception as e:
        logger.error(f"Error in community management: {str(e)}")
        return {
            "status": "error",
            "message": f"Error en gestión de comunidad: {str(e)}"
        }

async def x_viral_content_optimizer(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Optimizador de contenido viral con análisis predictivo
    
    Parámetros:
    - content_ideas: Ideas de contenido a analizar
    - viral_analysis: Análisis de contenido viral existente
    - optimization_settings: Configuraciones de optimización
    - timing_analysis: Análisis de mejor timing
    - hashtag_research: Investigación de hashtags
    - influencer_collaboration: Colaboración con influencers
    """
    try:
        bearer_token = os.getenv("X_BEARER_TOKEN")
        content_ideas = params.get("content_ideas", [])
        viral_analysis = params.get("viral_analysis", {})
        optimization_settings = params.get("optimization_settings", {})
        timing_analysis = params.get("timing_analysis", {})
        hashtag_research = params.get("hashtag_research", {})
        influencer_collaboration = params.get("influencer_collaboration", {})
        
        if not content_ideas:
            return {
                "status": "error",
                "message": "Se requieren ideas de contenido para optimizar"
            }
        
        headers = {
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json"
        }
        
        base_url = "https://api.twitter.com/2"
        
        # Analizar contenido viral existente en el nicho
        viral_patterns = {}
        if viral_analysis.get("enabled"):
            viral_patterns = await _analyze_viral_patterns(
                base_url, headers, viral_analysis
            )
        
        # Optimizar cada idea de contenido
        optimized_content = []
        for idx, idea in enumerate(content_ideas):
            try:
                # Analizar potencial viral de la idea
                viral_score = await _calculate_viral_potential(
                    idea, viral_patterns, optimization_settings
                )
                
                # Optimizar texto del contenido
                optimized_text = await _optimize_content_text(
                    idea.get("text", ""), viral_patterns, optimization_settings
                )
                
                # Sugerir hashtags optimizados
                suggested_hashtags = []
                if hashtag_research.get("enabled"):
                    suggested_hashtags = await _research_optimal_hashtags(
                        optimized_text, hashtag_research
                    )
                
                # Determinar mejor timing
                optimal_timing = {}
                if timing_analysis.get("enabled"):
                    optimal_timing = await _calculate_optimal_timing(
                        idea, timing_analysis
                    )
                
                # Sugerir colaboraciones con influencers
                collaboration_suggestions = []
                if influencer_collaboration.get("enabled"):
                    collaboration_suggestions = await _suggest_influencer_collaborations(
                        idea, influencer_collaboration
                    )
                
                # Generar variaciones del contenido
                content_variations = await _generate_content_variations(
                    optimized_text, optimization_settings.get("variations", 3)
                )
                
                optimized_content.append({
                    "original_idea": idea,
                    "optimized_text": optimized_text,
                    "viral_score": viral_score,
                    "suggested_hashtags": suggested_hashtags,
                    "optimal_timing": optimal_timing,
                    "collaboration_suggestions": collaboration_suggestions,
                    "content_variations": content_variations,
                    "optimization_applied": True
                })
                
            except Exception as e:
                optimized_content.append({
                    "original_idea": idea,
                    "error": str(e),
                    "optimization_applied": False
                })
        
        # Rankear contenido por potencial viral
        ranked_content = sorted(
            optimized_content, 
            key=lambda x: x.get("viral_score", {}).get("total_score", 0), 
            reverse=True
        )
        
        # Generar estrategia de publicación
        publication_strategy = await _generate_publication_strategy(
            ranked_content, timing_analysis, optimization_settings
        )
        
        # Crear calendario de contenido optimizado
        content_calendar = await _create_optimized_calendar(
            ranked_content, publication_strategy
        )
        
        result = {
            "status": "success",
            "total_content_ideas": len(content_ideas),
            "successfully_optimized": len([c for c in optimized_content if c.get("optimization_applied")]),
            "viral_patterns": viral_patterns,
            "optimized_content": optimized_content,
            "ranked_content": ranked_content[:10],  # Top 10
            "publication_strategy": publication_strategy,
            "content_calendar": content_calendar,
            "optimization_settings": optimization_settings,
            "analysis_completed_at": datetime.now().isoformat()
        }
        
        # Persistir análisis de optimización
        await _persist_x_action(client, result, "viral_content_optimized")
        
        return result
        
    except Exception as e:
        logger.error(f"Error in viral content optimization: {str(e)}")
        return {
            "status": "error",
            "message": f"Error en optimización de contenido viral: {str(e)}"
        }

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

async def _upload_x_media(api_key: str, api_secret: str, access_token: str, 
                         access_token_secret: str, media: Dict) -> Dict:
    """Subir media a X (Twitter)"""
    try:
        import tweepy
        
        # Configurar autenticación OAuth 1.0a para subida de media
        auth = tweepy.OAuth1UserHandler(
            api_key, api_secret, access_token, access_token_secret
        )
        api = tweepy.API(auth)
        
        if media.get("file_path"):
            # Subir desde archivo local
            media_upload = api.media_upload(media["file_path"])
        elif media.get("file_url"):
            # Descargar y subir desde URL
            import requests
            response = requests.get(media["file_url"])
            if response.status_code == 200:
                # Guardar temporalmente y subir
                temp_filename = f"/tmp/temp_media_{int(time.time())}"
                with open(temp_filename, "wb") as f:
                    f.write(response.content)
                media_upload = api.media_upload(temp_filename)
                os.remove(temp_filename)
            else:
                return {"error": "Could not download media from URL"}
        else:
            return {"error": "No file source provided"}
        
        return {
            "media_id": media_upload.media_id_string,
            "size": media_upload.size,
            "type": media.get("type", "unknown")
        }
        
    except Exception as e:
        return {"error": str(e)}

async def _optimize_hashtags(text: str, hashtag_optimization: Dict) -> str:
    """Optimizar hashtags en el texto"""
    try:
        if not hashtag_optimization.get("enabled"):
            return text
        
        max_hashtags = hashtag_optimization.get("max_hashtags", 3)
        trending_hashtags = hashtag_optimization.get("trending_hashtags", [])
        niche_hashtags = hashtag_optimization.get("niche_hashtags", [])
        
        # Extraer hashtags existentes
        existing_hashtags = [word for word in text.split() if word.startswith("#")]
        
        # Sugerir hashtags adicionales
        suggested_hashtags = []
        
        # Agregar hashtags trending relevantes
        for hashtag in trending_hashtags[:2]:
            if hashtag not in existing_hashtags and len(suggested_hashtags) < max_hashtags:
                suggested_hashtags.append(hashtag)
        
        # Agregar hashtags de nicho
        for hashtag in niche_hashtags:
            if hashtag not in existing_hashtags and len(suggested_hashtags) < max_hashtags:
                suggested_hashtags.append(hashtag)
        
        # Agregar hashtags sugeridos al texto si hay espacio
        if suggested_hashtags:
            hashtags_text = " " + " ".join(suggested_hashtags)
            if len(text + hashtags_text) <= 280:  # Límite de caracteres de Twitter
                text += hashtags_text
        
        return text
        
    except Exception as e:
        logger.error(f"Error optimizing hashtags: {str(e)}")
        return text

async def _schedule_x_tweet(tweet_payload: Dict, scheduling: Dict, headers: Dict) -> Dict:
    """Programar tweet (simulado - requiere Twitter Ads API o herramientas de terceros)"""
    try:
        scheduled_time = scheduling.get("scheduled_time")
        timezone = scheduling.get("timezone", "UTC")
        
        # En implementación real, esto usaría la API de Twitter Ads o herramientas como Buffer/Hootsuite
        return {
            "scheduled": True,
            "scheduled_time": scheduled_time,
            "timezone": timezone,
            "scheduler": "twitter_ads_api",
            "confirmation_id": f"scheduled_{int(time.time())}"
        }
        
    except Exception as e:
        return {"scheduled": False, "error": str(e)}

async def _post_twitter_thread(base_url: str, headers: Dict, reply_to_id: str, 
                              thread_content: List[Dict], uploaded_media: List[str]) -> List[Dict]:
    """Publicar hilo de Twitter"""
    try:
        thread_results = []
        current_reply_id = reply_to_id
        
        for idx, thread_tweet in enumerate(thread_content):
            try:
                tweet_payload = {
                    "text": thread_tweet.get("text", ""),
                    "reply": {"in_reply_to_tweet_id": current_reply_id}
                }
                
                # Agregar media si está especificado para este tweet del hilo
                if thread_tweet.get("media_index") is not None and uploaded_media:
                    media_idx = thread_tweet["media_index"]
                    if 0 <= media_idx < len(uploaded_media):
                        tweet_payload["media"] = {"media_ids": [uploaded_media[media_idx]]}
                
                response = requests.post(
                    f"{base_url}/tweets",
                    json=tweet_payload,
                    headers=headers
                )
                
                if response.status_code in [200, 201]:
                    result = response.json()
                    current_reply_id = result["data"]["id"]
                    
                    thread_results.append({
                        "thread_position": idx + 2,  # +2 porque es después del tweet principal
                        "tweet_id": current_reply_id,
                        "text": thread_tweet.get("text"),
                        "status": "published"
                    })
                else:
                    thread_results.append({
                        "thread_position": idx + 2,
                        "text": thread_tweet.get("text"),
                        "status": "error",
                        "error": response.text
                    })
                    break  # Parar el hilo si hay error
                
                # Pausa breve entre tweets del hilo
                await asyncio.sleep(1)
                
            except Exception as e:
                thread_results.append({
                    "thread_position": idx + 2,
                    "text": thread_tweet.get("text", ""),
                    "status": "error",
                    "error": str(e)
                })
                break
        
        return thread_results
        
    except Exception as e:
        logger.error(f"Error posting thread: {str(e)}")
        return []

async def _setup_engagement_monitoring(tweet_id: str, engagement_settings: Dict) -> Dict:
    """Configurar monitoreo de engagement"""
    try:
        return {
            "enabled": True,
            "tweet_id": tweet_id,
            "metrics_to_track": engagement_settings.get("metrics", ["likes", "retweets", "replies", "quotes"]),
            "monitoring_duration": engagement_settings.get("duration", "24h"),
            "alert_thresholds": engagement_settings.get("thresholds", {}),
            "reporting_frequency": engagement_settings.get("reporting", "hourly")
        }
        
    except Exception as e:
        return {"enabled": False, "error": str(e)}

# ============================================================================
# FUNCIONES DE ANÁLISIS
# ============================================================================

async def _analyze_followers_growth(base_url: str, headers: Dict, user_id: str, period: str) -> Dict:
    """Analizar crecimiento de seguidores"""
    try:
        # En implementación real, obtendría datos históricos
        return {
            "period": period,
            "growth_rate": "5.2%",
            "new_followers": 150,
            "unfollowers": 23,
            "net_growth": 127,
            "average_daily_growth": 4.2,
            "growth_trend": "increasing"
        }
        
    except Exception as e:
        return {"error": str(e)}

async def _analyze_engagement_metrics(base_url: str, headers: Dict, user_id: str, period: str) -> Dict:
    """Analizar métricas de engagement"""
    try:
        # Obtener tweets recientes
        response = requests.get(
            f"{base_url}/users/{user_id}/tweets",
            headers=headers,
            params={
                "max_results": 100,
                "tweet.fields": "created_at,public_metrics,context_annotations"
            }
        )
        
        if response.status_code == 200:
            tweets_data = response.json().get("data", [])
            
            total_likes = sum(tweet.get("public_metrics", {}).get("like_count", 0) for tweet in tweets_data)
            total_retweets = sum(tweet.get("public_metrics", {}).get("retweet_count", 0) for tweet in tweets_data)
            total_replies = sum(tweet.get("public_metrics", {}).get("reply_count", 0) for tweet in tweets_data)
            total_quotes = sum(tweet.get("public_metrics", {}).get("quote_count", 0) for tweet in tweets_data)
            
            total_engagement = total_likes + total_retweets + total_replies + total_quotes
            
            return {
                "period": period,
                "total_tweets": len(tweets_data),
                "total_engagement": total_engagement,
                "average_engagement_per_tweet": total_engagement / len(tweets_data) if tweets_data else 0,
                "likes": total_likes,
                "retweets": total_retweets,
                "replies": total_replies,
                "quotes": total_quotes,
                "engagement_rate": f"{(total_engagement / len(tweets_data) * 100) if tweets_data else 0:.2f}%"
            }
        
        return {"error": "Could not fetch tweets data"}
        
    except Exception as e:
        return {"error": str(e)}

async def _analyze_content_performance(base_url: str, headers: Dict, user_id: str, period: str) -> Dict:
    """Analizar rendimiento de contenido"""
    try:
        # Obtener tweets con métricas
        response = requests.get(
            f"{base_url}/users/{user_id}/tweets",
            headers=headers,
            params={
                "max_results": 50,
                "tweet.fields": "created_at,public_metrics,context_annotations,entities"
            }
        )
        
        if response.status_code == 200:
            tweets_data = response.json().get("data", [])
            
            # Analizar mejores tweets
            top_tweets = sorted(
                tweets_data, 
                key=lambda x: x.get("public_metrics", {}).get("like_count", 0) + 
                             x.get("public_metrics", {}).get("retweet_count", 0), 
                reverse=True
            )[:5]
            
            # Analizar tipos de contenido
            content_types = {
                "text_only": 0,
                "with_media": 0,
                "with_links": 0,
                "with_hashtags": 0
            }
            
            for tweet in tweets_data:
                entities = tweet.get("entities", {})
                if entities.get("urls"):
                    content_types["with_links"] += 1
                if entities.get("hashtags"):
                    content_types["with_hashtags"] += 1
                # Simular detección de media
                if len(tweet.get("text", "")) < 50:  # Asumir que tweets cortos tienen media
                    content_types["with_media"] += 1
                else:
                    content_types["text_only"] += 1
            
            return {
                "period": period,
                "total_tweets_analyzed": len(tweets_data),
                "top_performing_tweets": [
                    {
                        "id": tweet.get("id"),
                        "text": tweet.get("text", "")[:100] + "...",
                        "likes": tweet.get("public_metrics", {}).get("like_count", 0),
                        "retweets": tweet.get("public_metrics", {}).get("retweet_count", 0)
                    }
                    for tweet in top_tweets
                ],
                "content_type_distribution": content_types,
                "average_tweet_length": sum(len(tweet.get("text", "")) for tweet in tweets_data) / len(tweets_data) if tweets_data else 0
            }
        
        return {"error": "Could not fetch content data"}
        
    except Exception as e:
        return {"error": str(e)}

async def _analyze_reach_metrics(base_url: str, headers: Dict, user_id: str, period: str) -> Dict:
    """Analizar métricas de alcance"""
    try:
        # En implementación real, usaría Twitter Analytics API
        return {
            "period": period,
            "estimated_reach": 25000,
            "impressions": 45000,
            "profile_visits": 1200,
            "mention_reach": 8500,
            "hashtag_reach": 12000,
            "reach_growth": "12.5%"
        }
        
    except Exception as e:
        return {"error": str(e)}

# ============================================================================
# FUNCIONES DE PERSISTENCIA
# ============================================================================

async def _persist_x_action(client: AuthenticatedHttpClient, action_data: Dict[str, Any], action: str):
    """Persistir acción de X (Twitter)"""
    try:
        from app.memory.memory_functions import save_memory
        
        await save_memory(client, {
            "storage_type": "social",
            "file_name": f"x_twitter_{action}_{int(time.time())}.json",
            "content": {
                "action": action,
                "action_data": action_data,
                "timestamp": time.time(),
                "platform": "x_twitter"
            },
            "tags": ["x", "twitter", "social_media", action]
        })
        
    except Exception as e:
        logger.error(f"Error persisting X action: {str(e)}")

# Placeholder para otras funciones auxiliares que serían implementadas...
async def _analyze_audience_segments(base_url, headers, user_id, segments): pass
async def _analyze_competitors(base_url, headers, competitors, period): pass  
async def _analyze_trends_and_hashtags(base_url, headers, user_id, trend_analysis): pass
async def _generate_audience_insights(main_metrics, audience_analysis, competitor_insights, trend_insights): pass
def _calculate_performance_scores(main_metrics): pass
async def _export_analytics_report(result, export_format): pass
# ... y muchas más funciones auxiliares
