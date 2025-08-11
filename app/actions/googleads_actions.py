# app/actions/googleads_actions.py
import logging
import base64
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
from google.protobuf import json_format

from app.core.config import settings
# ✅ IMPORTACIÓN DIRECTA DEL RESOLVER PARA EVITAR CIRCULARIDAD
def _get_resolver():
    from app.actions.resolver_actions import Resolver
    return Resolver()

logger = logging.getLogger(__name__)

# --- INICIALIZACIÓN DEL CLIENTE Y HELPERS ROBUSTOS ---
_google_ads_client_instance: Optional[GoogleAdsClient] = None

def get_google_ads_client() -> GoogleAdsClient:
    global _google_ads_client_instance
    if _google_ads_client_instance:
        return _google_ads_client_instance
    
    try:
        # Intentar obtener access_token automáticamente (si existe token_manager)
        access_token = None
        try:
            from app.core.auth_manager import token_manager
            access_token = token_manager.get_google_access_token("google_ads")
        except ImportError:
            logger.warning("auth_manager no disponible, usando refresh token tradicional")
        except Exception as e:
            logger.warning(f"No se pudo obtener access_token automático: {e}")
        
        # Configuración robusta para Google Ads API v20
        config = {
            "developer_token": settings.GOOGLE_ADS_DEVELOPER_TOKEN,
            "client_id": settings.GOOGLE_ADS_CLIENT_ID,
            "client_secret": settings.GOOGLE_ADS_CLIENT_SECRET,
            "refresh_token": settings.GOOGLE_ADS_REFRESH_TOKEN,
            "login_customer_id": str(settings.GOOGLE_ADS_LOGIN_CUSTOMER_ID).replace("-", "") if settings.GOOGLE_ADS_LOGIN_CUSTOMER_ID else None,
            # Preferimos proto_plus activado para acceder a .name y helpers
            "use_proto_plus": True,
            "api_version": "v20",
            "http_timeout": 60,
        }
        if access_token:
            config["access_token"] = access_token
            logger.info("Google Ads: usando access_token automático para API v20")
        
        logger.info("Inicializando Google Ads Client (v20, proto_plus=True)")
        _google_ads_client_instance = GoogleAdsClient.load_from_dict(config)
        return _google_ads_client_instance
    except Exception as e:
        logger.error(f"Error inicializando cliente Google Ads: {e}")
        raise ValueError(f"Google Ads client initialization failed: {str(e)}")

def _handle_google_ads_api_error(ex: GoogleAdsException, action_name: str) -> Dict[str, Any]:
    """
    Manejo avanzado de errores Google Ads API v20 con diagnóstico y recomendaciones.
    """
    error_details: List[Dict[str, Any]] = []
    try:
        for error in ex.failure.errors:
            error_code_str = str(error.error_code)
            info = {
                "message": getattr(error, "message", ""),
                "error_code": error_code_str,
                "trigger": getattr(error, "trigger", None),
                "location": getattr(error, "location", None),
                "severity": "CRITICAL" if "PERMISSION" in error_code_str else "WARNING",
            }
            if "DEPRECATED" in error_code_str or "UNSUPPORTED_VERSION" in error_code_str:
                info.update({
                    "severity": "CRITICAL",
                    "migration_required": True,
                    "recommendation": "Actualizar a Google Ads API v20 inmediatamente",
                })
            elif "QUOTA_EXCEEDED" in error_code_str or "RATE_LIMIT" in error_code_str:
                info.update({
                    "severity": "HIGH",
                    "retry_strategy": "exponential_backoff",
                    "recommendation": "Aplicar throttling y reintentar con backoff",
                })
            elif "PERMISSION_DENIED" in error_code_str or "AUTHENTICATION" in error_code_str:
                info.update({
                    "severity": "CRITICAL",
                    "auth_issue": True,
                    "recommendation": "Verificar credenciales y permisos del Customer ID",
                })
            error_details.append(info)
        
        logger.error(f"Google Ads API v20 Exception en '{action_name}': {len(error_details)} errores")
        
        return {
            "success": False,
            "error": "Error en Google Ads API v20",
            "action": action_name,
            "api_version": "v20",
            "details": {
                "errors": error_details,
                "request_id": ex.request_id,
                "error_summary": {
                    "total_errors": len(error_details),
                    "critical_errors": len([e for e in error_details if e.get("severity") == "CRITICAL"]),
                    "auth_errors": len([e for e in error_details if e.get("auth_issue")]),
                },
            },
            "recovery_recommendations": _generate_recovery_recommendations_v20(error_details),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as processing_error:
        logger.error(f"Error procesando excepción Google Ads: {processing_error}")
        return {
            "success": False,
            "error": f"Error procesando respuesta de Google Ads API: {str(processing_error)}",
            "original_exception": str(ex),
            "timestamp": datetime.now().isoformat(),
        }

# --- Helper para recomendaciones de recuperación v20 ---
def _generate_recovery_recommendations_v20(error_details: List[Dict[str, Any]]) -> List[str]:
    """Generación de recomendaciones de recuperación específicas para API v20."""
    recommendations: List[str] = []
    for error in error_details:
        if error.get("migration_required"):
            recommendations.append("🚀 ACCIÓN CRÍTICA: Migrar a Google Ads API v20 inmediatamente")
        if error.get("auth_issue"):
            recommendations.append("🔐 Verificar y renovar credenciales de autenticación")
            recommendations.append("👤 Confirmar permisos de Customer ID en Google Ads")
        if error.get("retry_strategy") == "exponential_backoff":
            recommendations.append("⏰ Implementar delays exponenciales entre requests")
            recommendations.append("📊 Considerar reducir frecuencia de consultas")
    if not recommendations:
        recommendations.extend([
            "🔍 Revisar configuración general de Google Ads API v20",
            "📝 Verificar sintaxis de queries GAQL para v20",
            "🌐 Confirmar conectividad y configuración de red"
        ])
    # Eliminar duplicados preservando orden
    seen = set()
    unique: List[str] = []
    for r in recommendations:
        if r not in seen:
            unique.append(r)
            seen.add(r)
    return unique

def _execute_search_query(customer_id: str, query: str, action_name: str) -> Dict[str, Any]:
    """
    Ejecución optimizada de GAQL con search_stream y conversión segura a dict.
    """
    try:
        max_attempts = 3
        backoff_base = 2
        attempt = 0
        last_exception: Optional[Exception] = None
        while attempt < max_attempts:
            start_ts = datetime.now()
            try:
                gads_client = get_google_ads_client()
                ga_service = gads_client.get_service("GoogleAdsService")
                logger.info(f"🔍 Ejecutando GAQL v20 (intento {attempt+1}/{max_attempts}): {query[:120]}...")
                stream = ga_service.search_stream(customer_id=customer_id, query=query)
                results: List[Dict[str, Any]] = []
                batches = 0
                total_rows = 0
                for batch in stream:
                    batches += 1
                    for row in batch.results:
                        try:
                            results.append(json_format.MessageToDict(row._pb))
                            total_rows += 1
                        except Exception as conv_err:
                            logger.warning(f"⚠️ Error convirtiendo fila: {conv_err}")
                            continue
                elapsed = (datetime.now() - start_ts).total_seconds()
                logger.info(f"✅ GAQL OK: {total_rows} filas en {elapsed:.2f}s ({batches} batches)")
                return {
                    "success": True,
                    "data": results,
                    "metadata": {
                        "api_version": "v20",
                        "total_results": total_rows,
                        "batches_processed": batches,
                        "execution_time_seconds": round(elapsed, 2),
                        "query_hash": hash(query),
                        "timestamp": datetime.now().isoformat(),
                    },
                }
            except GoogleAdsException as ex:
                last_exception = ex
                # Detectar rate limit / quota exceeded para reintentar
                try:
                    codes = [str(err.error_code) for err in ex.failure.errors]
                except Exception:
                    codes = []
                if any("QUOTA_EXCEEDED" in c or "RATE_LIMIT" in c for c in codes):
                    wait_s = backoff_base ** attempt
                    logger.warning(f"⏳ Rate limit/quota: reintentando en {wait_s}s (códigos: {codes})")
                    time.sleep(wait_s)
                    attempt += 1
                    continue
                # Otros errores -> manejar y salir
                return _handle_google_ads_api_error(ex, action_name)
            except Exception as e:
                last_exception = e
                logger.error(f"❌ Error general (intento {attempt+1}): {e}")
                wait_s = backoff_base ** attempt
                time.sleep(wait_s)
                attempt += 1
        # Si agotó reintentos
        if isinstance(last_exception, GoogleAdsException):
            return _handle_google_ads_api_error(last_exception, action_name)  # type: ignore
        return {
            "success": False,
            "error": str(last_exception) if last_exception else "Error desconocido tras reintentos",
            "error_type": "general_execution_error",
            "action": action_name,
            "api_version": "v20",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"❌ Error no controlado en {action_name}: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": "general_execution_error",
            "action": action_name,
            "api_version": "v20",
            "timestamp": datetime.now().isoformat(),
        }

def _execute_mutate_operations(customer_id: str, operations: list, service_name: str, action_name: str) -> Dict[str, Any]:
    try:
        gads_client = get_google_ads_client()
        service = gads_client.get_service(service_name)
        max_attempts = 3
        backoff_base = 2
        attempt = 0
        last_exception: Optional[Exception] = None
        while attempt < max_attempts:
            try:
                response = service.mutate(customer_id=customer_id, operations=operations)
                return {"success": True, "data": json_format.MessageToDict(response._pb)}
            except GoogleAdsException as ex:
                last_exception = ex
                try:
                    codes = [str(err.error_code) for err in ex.failure.errors]
                except Exception:
                    codes = []
                if any("QUOTA_EXCEEDED" in c or "RATE_LIMIT" in c for c in codes):
                    wait_s = backoff_base ** attempt
                    logger.warning(f"⏳ Rate limit/quota en mutate: reintentando en {wait_s}s (códigos: {codes})")
                    time.sleep(wait_s)
                    attempt += 1
                    continue
                return _handle_google_ads_api_error(ex, action_name)
            except Exception as e:
                last_exception = e
                logger.error(f"❌ Error general mutate (intento {attempt+1}): {e}")
                wait_s = backoff_base ** attempt
                time.sleep(wait_s)
                attempt += 1
        if isinstance(last_exception, GoogleAdsException):
            return _handle_google_ads_api_error(last_exception, action_name)  # type: ignore
        return {"success": False, "error": str(last_exception) if last_exception else "Error desconocido tras reintentos"}
    except Exception as e:
        logger.error(f"Error en {action_name}: {str(e)}")
        return {"success": False, "error": str(e)}

def _get_customer_id(params: Dict[str, Any]) -> str:
    # CORRECCIÓN: Usar la propiedad correcta de settings
    customer_id = params.get("customer_id", settings.GOOGLE_ADS_LOGIN_CUSTOMER_ID)
    if not customer_id: raise ValueError("Se requiere 'customer_id'.")
    return str(customer_id).replace("-", "")

def _validate_budget_for_currency(amount_micros: int, currency_code: str = "COP") -> int:
    """Valida y ajusta el presupuesto según la moneda."""
    # Configuraciones por moneda (mínimos en micros)
    currency_configs = {
        "COP": {"min_micros": 10000, "multiple_of": 10000},  # Peso colombiano
        "USD": {"min_micros": 1000000, "multiple_of": 10000},  # Dólar
        "EUR": {"min_micros": 1000000, "multiple_of": 10000},  # Euro
        "MXN": {"min_micros": 10000, "multiple_of": 10000},   # Peso mexicano
    }
    
    config = currency_configs.get(currency_code, currency_configs["USD"])
    
    # CORRECCIÓN: Verificar si ya es válido antes de ajustar
    if amount_micros >= config["min_micros"] and amount_micros % config["multiple_of"] == 0:
        logger.info(f"Presupuesto COP válido: {amount_micros} micros")
        return amount_micros
    
    # Solo ajustar si es necesario
    if amount_micros % config["multiple_of"] != 0:
        amount_micros = ((amount_micros // config["multiple_of"]) + 1) * config["multiple_of"]
    
    # Asegurar mínimo
    if amount_micros < config["min_micros"]:
        amount_micros = config["min_micros"]
    
    logger.info(f"Presupuesto ajustado para {currency_code}: {amount_micros} micros")
    return amount_micros

# NUEVA: Función helper para obtener configuración de moneda
def _get_currency_config(currency_code: str = "COP") -> Dict[str, int]:
    """Obtiene la configuración de moneda específica."""
    currency_configs = {
        "COP": {"min_micros": 10000, "multiple_of": 10000},  # Peso colombiano
        "USD": {"min_micros": 1000000, "multiple_of": 10000},  # Dólar
        "EUR": {"min_micros": 1000000, "multiple_of": 10000},  # Euro
        "MXN": {"min_micros": 10000, "multiple_of": 10000},   # Peso mexicano
    }
    return currency_configs.get(currency_code, currency_configs["USD"])

def _create_campaign_budget(client, customer_id, name, amount_micros, is_shared=False):
    """
    Crea un presupuesto de campaña en Google Ads.
    
    Args:
        client: Cliente de Google Ads
        customer_id: ID del cliente
        name: Nombre del presupuesto
        amount_micros: Monto en micros (1,000,000 = 1 unidad de moneda)
        is_shared: Si el presupuesto puede ser compartido entre campañas
        
    Returns:
        Resource name del presupuesto creado
    """
    campaign_budget_service = client.get_service("CampaignBudgetService")
    campaign_budget_operation = client.get_type("CampaignBudgetOperation")
    
    campaign_budget = campaign_budget_operation.create
    campaign_budget.name = name
    campaign_budget.delivery_method = client.enums.BudgetDeliveryMethodEnum.STANDARD
    campaign_budget.amount_micros = amount_micros
    campaign_budget.explicitly_shared = is_shared
    
    try:
        response = campaign_budget_service.mutate_campaign_budgets(
            customer_id=customer_id,
            operations=[campaign_budget_operation]
        )
        
        budget_resource_name = response.results[0].resource_name
        logger.info(f"Created campaign budget: {budget_resource_name}")
        return budget_resource_name
        
    except GoogleAdsException as e:
        logger.error(f"Error creating campaign budget: {e}")
        raise

# --- ACCIONES COMPLETAS Y FUNCIONALES ---

def googleads_get_campaigns(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Obtener campañas de Google Ads con métricas y análisis.
    """
    logger.info("📢 Iniciando obtención de campañas Google Ads")
    action_name = "googleads_get_campaigns"

    try:
        # Validación básica de entrada
        customer_id = params.get("customer_id")
        if not customer_id:
            return {
                "status": "error",
                "error": "customer_id es requerido",
                "timestamp": datetime.now().isoformat()
            }

        # Obtener cliente de Google Ads
        ads_client = get_google_ads_client()
        customer_id = customer_id.replace("-", "")
        
        # Configurar consulta GAQL básica
        query = """
        SELECT
            campaign.id,
            campaign.name,
            campaign.status,
            campaign.advertising_channel_type,
            campaign.advertising_channel_sub_type,
            campaign.start_date,
            campaign.end_date,
            campaign.campaign_budget,
            metrics.impressions,
            metrics.clicks,
            metrics.ctr,
            metrics.average_cpc,
            metrics.cost_micros,
            metrics.conversions,
            metrics.conversions_value
        FROM campaign
        ORDER BY campaign.name
        """
        
        # Agregar filtros si se proporcionan
        if params.get("status_filter"):
            status = params["status_filter"].upper()
            query = query.replace("ORDER BY", f"WHERE campaign.status = {status} ORDER BY")
        
        # Ejecutar consulta
        ga_service = ads_client.get_service("GoogleAdsService")
        stream = ga_service.search_stream(customer_id=customer_id, query=query)
        
        # Procesar resultados
        campaigns = []
        total_impressions = 0
        total_clicks = 0
        total_cost = 0
        
        for batch in stream:
            for row in batch.results:
                campaign_data = {
                    "id": row.campaign.id,
                    "name": row.campaign.name,
                    "status": row.campaign.status.name,
                    "advertising_channel_type": row.campaign.advertising_channel_type.name,
                    "start_date": row.campaign.start_date,
                    "end_date": row.campaign.end_date,
                    "metrics": {
                        "impressions": row.metrics.impressions,
                        "clicks": row.metrics.clicks,
                        "ctr": row.metrics.ctr,
                        "average_cpc": row.metrics.average_cpc,
                        "cost_micros": row.metrics.cost_micros,
                        "cost_usd": row.metrics.cost_micros / 1_000_000,
                        "conversions": row.metrics.conversions,
                        "conversions_value": row.metrics.conversions_value
                    }
                }
                campaigns.append(campaign_data)
                total_impressions += row.metrics.impressions
                total_clicks += row.metrics.clicks
                total_cost += row.metrics.cost_micros / 1_000_000

        # Calcular métricas resumidas
        avg_ctr = (total_clicks / total_impressions) * 100 if total_impressions > 0 else 0
        avg_cpc = total_cost / total_clicks if total_clicks > 0 else 0

        logger.info(f"Obtenidas {len(campaigns)} campañas de Google Ads")
        
        return {
            "status": "success",
            "data": campaigns,
            "summary": {
                "total_campaigns": len(campaigns),
                "total_impressions": total_impressions,
                "total_clicks": total_clicks,
                "total_cost_usd": round(total_cost, 2),
                "average_ctr": round(avg_ctr, 2),
                "average_cpc": round(avg_cpc, 2),
                "customer_id": customer_id
            },
            "timestamp": datetime.now().isoformat()
        }

    except GoogleAdsException as ex:
        error_details = []
        for error in ex.failure.errors:
            error_details.append({
                "error_code": error.error_code,
                "message": error.message,
                "location": [location.field_path_elements for location in error.location.field_path_elements] if error.location else []
            })
        return {
            "status": "error",
            "error": f"Google Ads API error: {ex.failure.errors[0].message}",
            "error_details": error_details,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


def googleads_create_campaign(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Crea una nueva campaña en Google Ads (SEARCH por defecto)."""
    action_name = "googleads_create_campaign"
    try:
        gads_client = get_google_ads_client()

        # Parámetros de entrada
        customer_id = str(params.get("customer_id", settings.GOOGLE_ADS_LOGIN_CUSTOMER_ID)).replace("-", "")
        if not customer_id:
            raise ValueError("Se requiere 'customer_id'.")
        campaign_name = params.get("name", f"Campaign_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        currency = params.get("currency_code", "USD")
        budget_amount = int(params.get("budget_amount_micros", 1_000_000))  # 1 unidad monetaria
        budget_amount = _validate_budget_for_currency(budget_amount, currency)

        advertising_type = (params.get("type") or "SEARCH").upper()

        # Crear presupuesto (usa helper correcto: name y amount)
        budget_name = f"{campaign_name}_budget"
        budget_resource_name = _create_campaign_budget(
            gads_client,
            customer_id,
            budget_name,
            budget_amount,
            is_shared=False,
        )

        # Construir operación de campaña
        campaign_service = gads_client.get_service("CampaignService")
        campaign_operation = gads_client.get_type("CampaignOperation")
        campaign = campaign_operation.create
        campaign.name = campaign_name
        campaign.campaign_budget = budget_resource_name

        # Canal
        campaign.advertising_channel_type = gads_client.enums.AdvertisingChannelTypeEnum[advertising_type]
        if advertising_type == "PERFORMANCE_MAX":
            campaign.advertising_channel_sub_type = gads_client.enums.AdvertisingChannelSubTypeEnum.PERFORMANCE_MAX

        # Estado inicial
        campaign.status = gads_client.enums.CampaignStatusEnum.PAUSED

        # Ejecutar
        response = campaign_service.mutate_campaigns(customer_id=customer_id, operations=[campaign_operation])
        created = response.results[0]

        return {
            "status": "success",
            "message": f"Campaña '{campaign_name}' creada exitosamente",
            "data": {
                "resource_name": created.resource_name,
                "name": campaign_name,
                "status": "PAUSED",
                "budget_micros": budget_amount,
                "type": advertising_type,
            },
        }
        
        # ✅ PERSISTENCIA DE MEMORIA - FUNCIÓN DE CREACIÓN
        _get_resolver().save_action_result(action_name, params, result)
        
        return result
    except GoogleAdsException as ex:
        return _handle_google_ads_api_error(ex, action_name)
    except Exception as e:
        logger.error(f"Error en {action_name}: {e}")
        return {
            "status": "error",
            "message": f"Error al crear campaña: {str(e)}",
            "action": action_name,
        }

def googleads_get_ad_groups(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    customer_id = _get_customer_id(params)
    campaign_id = params.get("campaign_id")
    if not campaign_id: raise ValueError("Se requiere 'campaign_id'.")
    query = f"SELECT ad_group.id, ad_group.name, ad_group.status FROM ad_group WHERE campaign.id = {campaign_id}"
    return _execute_search_query(customer_id, query, "googleads_get_ad_groups")

# --- NUEVAS FUNCIONES INTEGRADAS ---

def googleads_get_campaign(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Obtiene detalles específicos de una campaña."""
    customer_id = _get_customer_id(params)
    campaign_id = params.get("campaign_id")
    if not campaign_id:
        raise ValueError("Se requiere 'campaign_id'.")
    query = """
        SELECT 
            campaign.id, 
            campaign.name, 
            campaign.status, 
            campaign.bidding_strategy_type, 
            campaign.campaign_budget 
        FROM campaign 
        WHERE campaign.id = %s
    """ % campaign_id
    return _execute_search_query(customer_id, query, "googleads_get_campaign")

def googleads_update_campaign_status(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Actualiza el estado de una campaña específica."""
    customer_id = _get_customer_id(params)
    campaign_id = params.get("campaign_id")
    status = params.get("status")
    if not campaign_id or not status:
        raise ValueError("Se requieren 'campaign_id' y 'status'.")

    try:
        gads_client = get_google_ads_client()
        campaign_service = gads_client.get_service("CampaignService")
        operation = gads_client.get_type("CampaignOperation")
        
        campaign = operation.update
        campaign.resource_name = campaign_service.campaign_path(customer_id, campaign_id)
        campaign.status = gads_client.enums.CampaignStatusEnum[status.upper()]
        
        field_mask = gads_client.get_type("FieldMask")
        field_mask.paths.append("status")
        operation.update_mask.CopyFrom(field_mask)
        
        result = _execute_mutate_operations(
            customer_id, 
            [operation], 
            "CampaignService", 
            "googleads_update_campaign_status"
        )
        
        # ✅ PERSISTENCIA DE MEMORIA - FUNCIÓN DE MODIFICACIÓN
        _get_resolver().save_action_result("googleads_update_campaign_status", params, result)
        
        return result
    except Exception as e:
        logger.error(f"Error al actualizar estado de campaña: {str(e)}")
        return {"success": False, "error": str(e), "timestamp": datetime.now().isoformat()}

def googleads_create_performance_max_campaign(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Crea una campaña Performance Max con configuraciones optimizadas."""
    params['type'] = 'PERFORMANCE_MAX'
    return googleads_create_campaign(client, params)

def googleads_create_remarketing_list(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Crea una nueva lista de remarketing."""
    customer_id = _get_customer_id(params)
    name = params.get("name")
    description = params.get("description")
    membership_days = params.get("membership_days", 365)
    
    if not name:
        raise ValueError("Se requiere 'name' para la lista.")

    try:
        gads_client = get_google_ads_client()
        operation = gads_client.get_type("UserListOperation")
        user_list = operation.create
        user_list.name = name
        user_list.description = description or f"Lista creada automáticamente - {name}"
        user_list.membership_life_span = membership_days
        user_list.crm_based_user_list.upload_key_type = (
            gads_client.enums.CustomerMatchUploadKeyTypeEnum.CONTACT_INFO
        )

        result = _execute_mutate_operations(
            customer_id,
            [operation],
            "UserListService",
            "googleads_create_remarketing_list"
        )
        
        # ✅ PERSISTENCIA DE MEMORIA - FUNCIÓN DE CREACIÓN
        _get_resolver().save_action_result("googleads_create_remarketing_list", params, result)
        
        return result
    except Exception as e:
        logger.error(f"Error al crear lista de remarketing: {str(e)}")
        return {"success": False, "error": str(e), "timestamp": datetime.now().isoformat()}

# --- FUNCIONES DE REPORTE Y ANÁLISIS ---

def googleads_get_campaign_performance(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Obtiene métricas de rendimiento de campaña."""
    customer_id = _get_customer_id(params)
    campaign_id = params.get("campaign_id")
    date_range = params.get("date_range", "LAST_30_DAYS")
    
    query = f"""
        SELECT 
            campaign.id,
            campaign.name,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros,
            metrics.conversions
        FROM campaign
        WHERE campaign.id = {campaign_id}
        AND segments.date DURING {date_range}
    """
    
    return _execute_search_query(customer_id, query, "googleads_get_campaign_performance")

# --- NUEVAS FUNCIONES AVANZADAS ---

def googleads_list_accessible_customers(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "googleads_list_accessible_customers"
    try:
        gads_client = get_google_ads_client()
        customer_service = gads_client.get_service("CustomerService")
        accessible_customers = customer_service.list_accessible_customers()
        return {"success": True, "data": {"resource_names": accessible_customers.resource_names}}
    except GoogleAdsException as ex:
        return _handle_google_ads_api_error(ex, action_name)
    except Exception as e:
        return {"success": False, "error": str(e), "timestamp": datetime.now().isoformat()}

def googleads_get_campaign_by_name(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "googleads_get_campaign_by_name"
    customer_id = _get_customer_id(params)
    campaign_name = params.get("name")
    if not campaign_name:
        return {"success": False, "error": "El parámetro 'name' es requerido.", "timestamp": datetime.now().isoformat()}
    
    sanitized_name = campaign_name.replace("'", "\\'")
    query = f"SELECT campaign.id, campaign.name, campaign.status, campaign.resource_name FROM campaign WHERE campaign.name = '{sanitized_name}' LIMIT 1"
    response = _execute_search_query(customer_id, query, action_name)
    
    if response["success"] == True:
        if not response["data"]:
            return {"success": False, "error": f"No se encontró campaña con nombre '{campaign_name}'.", "timestamp": datetime.now().isoformat()}
        return {"success": True, "data": response["data"][0]['campaign']}
    return response

def googleads_upload_click_conversion(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "googleads_upload_click_conversion"
    try:
        customer_id = _get_customer_id(params)
        gclid = params.get("gclid")
        conversion_action_id = params.get("conversion_action_id")
        conversion_datetime = params.get("conversion_datetime")
        conversion_value = params.get("conversion_value")

        if not all([gclid, conversion_action_id, conversion_datetime, conversion_value is not None]):
            raise ValueError("Se requieren 'gclid', 'conversion_action_id', 'conversion_datetime' y 'conversion_value'.")

        gads_client = get_google_ads_client()
        conversion_upload_service = gads_client.get_service("ConversionUploadService")
        
        click_conversion = gads_client.get_type("ClickConversion")
        click_conversion.gclid = gclid
        click_conversion.conversion_action = f"customers/{customer_id}/conversionActions/{conversion_action_id}"
        click_conversion.conversion_date_time = conversion_datetime
        click_conversion.conversion_value = float(conversion_value)
        click_conversion.currency_code = params.get("currency_code", "USD")

        request = gads_client.get_type("UploadClickConversionsRequest")
        request.customer_id = customer_id
        request.conversions.append(click_conversion)
        request.partial_failure = True

        response = conversion_upload_service.upload_click_conversions(request=request)
        
        response_dict = json_format.MessageToDict(response._pb)
        if "partialFailureError" in response_dict:
            return {"success": False, "error": "La carga de conversiones tuvo fallos parciales.", "data": response_dict}

        return {"success": True, "data": response_dict}
    except GoogleAdsException as ex:
        return _handle_google_ads_api_error(ex, action_name)
    except Exception as e:
        return {"success": False, "error": str(e), "timestamp": datetime.now().isoformat()}

def googleads_upload_image_asset(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "googleads_upload_image_asset"
    try:
        customer_id = _get_customer_id(params)
        image_base64 = params.get("image_base64_data")
        asset_name = params.get("asset_name")

        if not image_base64 or not asset_name:
            raise ValueError("Se requieren 'image_base64_data' y 'asset_name'.")

        gads_client = get_google_ads_client()
        asset_operation = gads_client.get_type("AssetOperation")
        asset = asset_operation.create
        asset.name = asset_name
        asset.type_ = gads_client.enums.AssetTypeEnum.IMAGE
        asset.image_asset.data = base64.b64decode(image_base64)
        
        return _execute_mutate_operations(customer_id, [asset_operation], "AssetService", action_name)
    except Exception as e:
        return {"success": False, "error": str(e), "timestamp": datetime.now().isoformat()}

def googleads_get_keyword_performance_report(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "googleads_get_keyword_performance_report"
    customer_id = _get_customer_id(params)
    date_range = params.get("date_range", "LAST_7_DAYS")
    
    query = f"""
        SELECT
            ad_group.name,
            ad_group_criterion.criterion_id,
            ad_group_criterion.keyword.text,
            metrics.clicks,
            metrics.impressions,
            metrics.ctr,
            metrics.average_cpc,
            metrics.cost_micros
        FROM keyword_view
        WHERE segments.date DURING {date_range}
        AND campaign.status = 'ENABLED'
        AND ad_group.status = 'ENABLED'
        ORDER BY metrics.clicks DESC
        LIMIT 50
    """
    return _execute_search_query(customer_id, query, action_name)

def googleads_get_campaign_performance_by_device(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "googleads_get_campaign_performance_by_device"
    customer_id = _get_customer_id(params)
    campaign_id = params.get("campaign_id")
    date_range = params.get("date_range", "LAST_30_DAYS")

    query = f"""
        SELECT
            campaign.id,
            campaign.name,
            segments.device,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros,
            metrics.conversions,
            metrics.ctr
        FROM campaign
        WHERE campaign.id = {campaign_id}
        AND segments.date DURING {date_range}
        ORDER BY metrics.clicks DESC
    """
    return _execute_search_query(customer_id, query, action_name)

def googleads_add_keywords_to_ad_group(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Agrega palabras clave a un grupo de anuncios."""
    action_name = "googleads_add_keywords_to_ad_group"
    try:
        customer_id = _get_customer_id(params)
        ad_group_id = params.get("ad_group_id")
        keywords = params.get("keywords", [])
        match_type = (params.get("match_type") or "EXACT").upper()
        status = (params.get("status") or "ENABLED").upper()

        if not ad_group_id or not keywords:
            raise ValueError("Se requieren 'ad_group_id' y 'keywords'")

        gads_client = get_google_ads_client()
        ad_group_service = gads_client.get_service("AdGroupService")
        ad_group_resource = ad_group_service.ad_group_path(customer_id, ad_group_id)
        operations = []

        for kw in keywords:
            op = gads_client.get_type("AdGroupCriterionOperation")
            criterion = op.create
            criterion.ad_group = ad_group_resource
            criterion.status = gads_client.enums.AdGroupCriterionStatusEnum[status]
            criterion.keyword.text = str(kw)
            # Mapear match type
            m = match_type if match_type in {"EXACT", "PHRASE", "BROAD"} else "EXACT"
            criterion.keyword.match_type = gads_client.enums.KeywordMatchTypeEnum[m]
            operations.append(op)

        result = _execute_mutate_operations(customer_id, operations, "AdGroupCriterionService", action_name)
        
        # ✅ PERSISTENCIA DE MEMORIA - FUNCIÓN DE CREACIÓN/MODIFICACIÓN
        _get_resolver().save_action_result(action_name, params, result)
        
        return result
    except GoogleAdsException as ex:
        return _handle_google_ads_api_error(ex, action_name)
    except Exception as e:
        return {"success": False, "error": str(e), "timestamp": datetime.now().isoformat()}

# --- UTILIDADES EXTRAS GOOGLE ADS ---

def googleads_get_budgets(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Lista budgets del cliente (nombre, monto, compartido)."""
    action_name = "googleads_get_budgets"
    try:
        customer_id = _get_customer_id(params)
        query = (
            "SELECT campaign_budget.id, campaign_budget.name, "
            "campaign_budget.amount_micros, campaign_budget.explicitly_shared "
            "FROM campaign_budget ORDER BY campaign_budget.name"
        )
        return _execute_search_query(customer_id, query, action_name)
    except Exception as e:
        return {"success": False, "error": str(e), "timestamp": datetime.now().isoformat()}

def googleads_set_daily_budget(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Actualiza el presupuesto diario de una campaña (amount_micros)."""
    action_name = "googleads_set_daily_budget"
    try:
        customer_id = _get_customer_id(params)
        campaign_id = params.get("campaign_id")
        amount_micros = int(params.get("amount_micros"))
        currency_code = params.get("currency_code", "USD")
        amount_micros = _validate_budget_for_currency(amount_micros, currency_code)

        if not campaign_id:
            raise ValueError("Se requiere 'campaign_id'.")

        # Obtener resource_name del budget desde la campaña
        campaign_query = (
            f"SELECT campaign.campaign_budget FROM campaign WHERE campaign.id = {campaign_id} LIMIT 1"
        )
        campaign_res = _execute_search_query(customer_id, campaign_query, action_name)
        if not campaign_res.get("success") or not campaign_res.get("data"):
            return {"success": False, "error": "No se encontró la campaña o falló la consulta de budget."}
        budget_resource = campaign_res["data"][0]["campaign"]["campaignBudget"]

        # Actualizar el amount del budget
        gads_client = get_google_ads_client()
        budget_op = gads_client.get_type("CampaignBudgetOperation")
        budget = budget_op.update
        budget.resource_name = budget_resource
        budget.amount_micros = amount_micros
        field_mask = gads_client.get_type("FieldMask")
        field_mask.paths.append("amount_micros")
        budget_op.update_mask.CopyFrom(field_mask)

        return _execute_mutate_operations(customer_id, [budget_op], "CampaignBudgetService", action_name)
    except GoogleAdsException as ex:
        return _handle_google_ads_api_error(ex, action_name)
    except Exception as e:
        logger.error(f"Error en {action_name}: {e}")
        return {"success": False, "error": str(e), "timestamp": datetime.now().isoformat()}

        return _execute_mutate_operations(
            customer_id, 
            operations, 
            "AdGroupCriterionService", 
            action_name
        )
    except Exception as e:
        return {"success": False, "error": str(e), "timestamp": datetime.now().isoformat()}

def googleads_apply_audience_to_ad_group(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Aplica una audiencia a un grupo de anuncios."""
    action_name = "googleads_apply_audience_to_ad_group"
    try:
        customer_id = _get_customer_id(params)
        ad_group_id = params.get("ad_group_id")
        audience_id = params.get("audience_id")

        if not ad_group_id or not audience_id:
            raise ValueError("Se requieren 'ad_group_id' y 'audience_id'")

        gads_client = get_google_ads_client()
        operation = gads_client.get_type("AdGroupCriterionOperation")
        criterion = operation.create
        criterion.ad_group = gads_client.get_service("AdGroupService").ad_group_path(
            customer_id, ad_group_id
        )
        criterion.user_list.user_list = gads_client.get_service("UserListService").user_list_path(
            customer_id, audience_id
        )

        return _execute_mutate_operations(
            customer_id,
            [operation],
            "AdGroupCriterionService",
            action_name
        )
    except Exception as e:
        return {"success": False, "error": str(e), "timestamp": datetime.now().isoformat()}

def googleads_create_responsive_search_ad(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Crea un anuncio de búsqueda responsive."""
    action_name = "googleads_create_responsive_search_ad"
    try:
        customer_id = _get_customer_id(params)
        ad_group_id = params.get("ad_group_id")
        headlines = params.get("headlines", [])
        descriptions = params.get("descriptions", [])

        if not ad_group_id or not headlines or not descriptions:
            raise ValueError("Se requieren 'ad_group_id', 'headlines' y 'descriptions'")

        gads_client = get_google_ads_client()
        operation = gads_client.get_type("AdGroupAdOperation")
        ad_group_ad = operation.create
        ad_group_ad.ad_group = gads_client.get_service("AdGroupService").ad_group_path(
            customer_id, ad_group_id
        )
        ad_group_ad.status = gads_client.enums.AdGroupAdStatusEnum.PAUSED

        # Configurar el anuncio responsive
        ad = ad_group_ad.ad
        ad.responsive_search_ad.headlines = [
            {"text": headline} for headline in headlines[:15]  # Máximo 15 títulos
        ]
        ad.responsive_search_ad.descriptions = [
            {"text": description} for description in descriptions[:4]  # Máximo 4 descripciones
        ]

        result = _execute_mutate_operations(
            customer_id,
            [operation],
            "AdGroupAdService",
            action_name
        )
        
        # ✅ PERSISTENCIA DE MEMORIA - FUNCIÓN DE CREACIÓN
        _get_resolver().save_action_result(action_name, params, result)
        
        return result
    except Exception as e:
        return {"success": False, "error": str(e), "timestamp": datetime.now().isoformat()}

def googleads_get_ad_performance(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Obtiene el rendimiento de los anuncios."""
    action_name = "googleads_get_ad_performance"
    customer_id = _get_customer_id(params)
    ad_group_id = params.get("ad_group_id")
    date_range = params.get("date_range", "LAST_30_DAYS")

    where_clause = f"AND ad_group.id = {ad_group_id}" if ad_group_id else ""
    
    query = f"""
        SELECT
            ad_group_ad.ad.id,
            ad_group_ad.ad.responsive_search_ad.headlines,
            ad_group_ad.ad.responsive_search_ad.descriptions,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros,
            metrics.conversions,
            metrics.ctr
        FROM ad_group_ad
        WHERE segments.date DURING {date_range}
        {where_clause}
        ORDER BY metrics.clicks DESC
    """
    
    return _execute_search_query(customer_id, query, action_name)

def googleads_upload_offline_conversion(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Carga conversiones offline."""
    action_name = "googleads_upload_offline_conversion"
    try:
        customer_id = _get_customer_id(params)
        conversion_action_id = params.get("conversion_action_id")
        conversion_data = params.get("conversion_data", [])

        if not conversion_action_id or not conversion_data:
            raise ValueError("Se requieren 'conversion_action_id' y 'conversion_data'")

        gads_client = get_google_ads_client()
        operations = []

        for data in conversion_data:
            operation = gads_client.get_type("OfflineUserDataJobOperation")
            job = operation.create
            job.type_ = gads_client.enums.OfflineUserDataJobTypeEnum.STORE_SALES_UPLOAD_FIRST_PARTY
            job.store_sales_metadata.loyalty_fraction = 1.0
            job.store_sales_metadata.transaction_upload_fraction = 1.0

            user_data = job.user_data.add()
            user_data.transaction_attribute.conversion_action = (
                f"customers/{customer_id}/conversionActions/{conversion_action_id}"
            )
            user_data.transaction_attribute.currency_code = data.get("currency_code", "USD")
            user_data.transaction_attribute.transaction_amount_micros = int(
                float(data.get("transaction_amount", 0)) * 1_000_000
            )
            user_data.transaction_attribute.transaction_date_time = data.get(
                "transaction_date_time"
            )

        return _execute_mutate_operations(
            customer_id,
            operations,
            "OfflineUserDataJobService",
            action_name
        )
    except Exception as e:
        return {"success": False, "error": str(e), "timestamp": datetime.now().isoformat()}


# ============================================================================
# FUNCIONES ADICIONALES RESTAURADAS
# ============================================================================

def googleads_create_conversion_action(params: Dict[str, Any]) -> Dict[str, Any]:
    """Crear una acción de conversión en Google Ads."""
    action_name = "googleads_create_conversion_action"
    logger.info(f"Ejecutando {action_name} con params: {params}")
    
    customer_id = params.get("customer_id")
    if not customer_id:
        return {"success": False, "error": "customer_id es requerido", "timestamp": datetime.now().isoformat()}
    
    conversion_name = params.get("conversion_name")
    if not conversion_name:
        return {"success": False, "error": "conversion_name es requerido", "timestamp": datetime.now().isoformat()}
    
    try:
        client = get_google_ads_client()
        customer_id = customer_id.replace("-", "")
        
        # Crear la acción de conversión
        conversion_action_operation = client.get_type("ConversionActionOperation")
        conversion_action = conversion_action_operation.create
        
        conversion_action.name = conversion_name
        conversion_action.type_ = client.enums.ConversionActionTypeEnum.WEBPAGE
        conversion_action.category = client.enums.ConversionActionCategoryEnum.DEFAULT
        conversion_action.status = client.enums.ConversionActionStatusEnum.ENABLED
        conversion_action.view_through_lookback_window_days = 30
        conversion_action.click_through_lookback_window_days = 30
        
        # Configurar el valor de conversión
        value_settings = conversion_action.value_settings
        value_settings.default_value = params.get("default_value", 1.0)
        value_settings.default_currency_code = params.get("currency_code", "USD")
        value_settings.always_use_default_value = params.get("always_use_default_value", True)
        
        # Configurar el conteo
        conversion_action.counting_type = client.enums.ConversionActionCountingTypeEnum.ONE_PER_CLICK
        
        # Ejecutar la operación
        conversion_action_service = client.get_service("ConversionActionService")
        response = conversion_action_service.mutate_conversion_actions(
            customer_id=customer_id, 
            operations=[conversion_action_operation]
        )
        
        result = response.results[0]
        logger.info(f"Acción de conversión creada: {result.resource_name}")
        
        return {
            "success": True,
            "resource_name": result.resource_name,
            "conversion_action_id": result.resource_name.split("/")[-1],
            "timestamp": datetime.now().isoformat()
        }
        
    except GoogleAdsException as ex:
        error_details = []
        for error in ex.failure.errors:
            error_details.append({
                "error_code": error.error_code,
                "message": error.message,
                "location": [location.field_path_elements for location in error.location.field_path_elements] if error.location else []
            })
        return {
            "success": False,
            "error": f"Google Ads API error: {ex.failure.errors[0].message}",
            "error_details": error_details,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {"success": False, "error": str(e), "timestamp": datetime.now().isoformat()}


def googleads_get_conversion_metrics(params: Dict[str, Any]) -> Dict[str, Any]:
    """Obtener métricas de conversión de Google Ads."""
    action_name = "googleads_get_conversion_metrics"
    logger.info(f"Ejecutando {action_name} con params: {params}")
    
    customer_id = params.get("customer_id")
    if not customer_id:
        return {"success": False, "error": "customer_id es requerido", "timestamp": datetime.now().isoformat()}
    
    try:
        client = get_google_ads_client()
        customer_id = customer_id.replace("-", "")
        
        # Configurar el rango de fechas
        start_date = params.get("start_date", "2024-01-01")
        end_date = params.get("end_date", "2024-12-31")
        
        # Consulta GAQL para obtener métricas de conversión
        query = f"""
        SELECT
            campaign.id,
            campaign.name,
            campaign.status,
            metrics.conversions,
            metrics.conversions_value,
            metrics.cost_per_conversion,
            metrics.conversion_rate,
            metrics.conversions_from_interactions_rate,
            metrics.view_through_conversions,
            segments.conversion_action_name,
            segments.conversion_action_category,
            segments.date
        FROM campaign
        WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
        AND metrics.conversions > 0
        ORDER BY metrics.conversions DESC
        LIMIT {params.get('limit', 100)}
        """
        
        ga_service = client.get_service("GoogleAdsService")
        stream = ga_service.search_stream(customer_id=customer_id, query=query)
        
        conversions_data = []
        total_conversions = 0
        total_conversion_value = 0
        
        for batch in stream:
            for row in batch.results:
                conversion_data = {
                    "campaign_id": row.campaign.id,
                    "campaign_name": row.campaign.name,
                    "campaign_status": row.campaign.status.name,
                    "date": row.segments.date,
                    "conversion_action_name": row.segments.conversion_action_name,
                    "conversion_action_category": row.segments.conversion_action_category.name,
                    "conversions": row.metrics.conversions,
                    "conversions_value": row.metrics.conversions_value,
                    "cost_per_conversion": row.metrics.cost_per_conversion,
                    "conversion_rate": row.metrics.conversion_rate,
                    "conversions_from_interactions_rate": row.metrics.conversions_from_interactions_rate,
                    "view_through_conversions": row.metrics.view_through_conversions
                }
                conversions_data.append(conversion_data)
                total_conversions += row.metrics.conversions
                total_conversion_value += row.metrics.conversions_value
        
        # Calcular métricas agregadas
        avg_conversion_rate = sum(row["conversion_rate"] for row in conversions_data) / len(conversions_data) if conversions_data else 0
        avg_cost_per_conversion = sum(row["cost_per_conversion"] for row in conversions_data) / len(conversions_data) if conversions_data else 0
        
        logger.info(f"Obtenidas {len(conversions_data)} filas de métricas de conversión")
        
        return {
            "success": True,
            "data": conversions_data,
            "summary": {
                "total_conversions": total_conversions,
                "total_conversion_value": total_conversion_value,
                "average_conversion_rate": avg_conversion_rate,
                "average_cost_per_conversion": avg_cost_per_conversion,
                "total_campaigns": len(set(row["campaign_id"] for row in conversions_data)),
                "date_range": f"{start_date} to {end_date}",
                "total_records": len(conversions_data)
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except GoogleAdsException as ex:
        error_details = []
        for error in ex.failure.errors:
            error_details.append({
                "error_code": error.error_code,
                "message": error.message,
                "location": [location.field_path_elements for location in error.location.field_path_elements] if error.location else []
            })
        return {
            "success": False,
            "error": f"Google Ads API error: {ex.failure.errors[0].message}",
            "error_details": error_details,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {"success": False, "error": str(e), "timestamp": datetime.now().isoformat()}


def googleads_get_conversion_actions(params: Dict[str, Any]) -> Dict[str, Any]:
    """Obtener todas las acciones de conversión configuradas en Google Ads."""
    action_name = "googleads_get_conversion_actions"
    logger.info(f"Ejecutando {action_name} con params: {params}")
    
    customer_id = params.get("customer_id")
    if not customer_id:
        return {"success": False, "error": "customer_id es requerido", "timestamp": datetime.now().isoformat()}
    
    try:
        client = get_google_ads_client()
        customer_id = customer_id.replace("-", "")
        
        # Consulta GAQL para obtener todas las acciones de conversión
        query = """
        SELECT
            conversion_action.id,
            conversion_action.name,
            conversion_action.status,
            conversion_action.type,
            conversion_action.category,
            conversion_action.origin,
            conversion_action.primary_for_goal,
            conversion_action.click_through_lookback_window_days,
            conversion_action.view_through_lookback_window_days,
            conversion_action.value_settings.default_value,
            conversion_action.value_settings.default_currency_code,
            conversion_action.value_settings.always_use_default_value,
            conversion_action.counting_type,
            conversion_action.attribution_model_settings.attribution_model,
            conversion_action.attribution_model_settings.data_driven_model_status
        FROM conversion_action
        ORDER BY conversion_action.name
        """
        
        ga_service = client.get_service("GoogleAdsService")
        stream = ga_service.search_stream(customer_id=customer_id, query=query)
        
        conversion_actions = []
        
        for batch in stream:
            for row in batch.results:
                conversion_action = {
                    "id": row.conversion_action.id,
                    "name": row.conversion_action.name,
                    "status": row.conversion_action.status.name,
                    "type": row.conversion_action.type_.name,
                    "category": row.conversion_action.category.name,
                    "origin": row.conversion_action.origin.name,
                    "primary_for_goal": row.conversion_action.primary_for_goal,
                    "click_through_lookback_window_days": row.conversion_action.click_through_lookback_window_days,
                    "view_through_lookback_window_days": row.conversion_action.view_through_lookback_window_days,
                    "counting_type": row.conversion_action.counting_type.name,
                    "value_settings": {
                        "default_value": row.conversion_action.value_settings.default_value,
                        "default_currency_code": row.conversion_action.value_settings.default_currency_code,
                        "always_use_default_value": row.conversion_action.value_settings.always_use_default_value
                    },
                    "attribution_model_settings": {
                        "attribution_model": row.conversion_action.attribution_model_settings.attribution_model.name,
                        "data_driven_model_status": row.conversion_action.attribution_model_settings.data_driven_model_status.name
                    }
                }
                conversion_actions.append(conversion_action)
        
        # Estadísticas resumidas
        total_actions = len(conversion_actions)
        enabled_actions = len([ca for ca in conversion_actions if ca["status"] == "ENABLED"])
        paused_actions = len([ca for ca in conversion_actions if ca["status"] == "PAUSED"])
        
        # Agrupar por categoría
        categories = {}
        for ca in conversion_actions:
            category = ca["category"]
            if category not in categories:
                categories[category] = 0
            categories[category] += 1
        
        logger.info(f"Obtenidas {total_actions} acciones de conversión")
        
        return {
            "success": True,
            "data": conversion_actions,
            "summary": {
                "total_conversion_actions": total_actions,
                "enabled_actions": enabled_actions,
                "paused_actions": paused_actions,
                "categories_breakdown": categories,
                "customer_id": customer_id
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except GoogleAdsException as ex:
        error_details = []
        for error in ex.failure.errors:
            error_details.append({
                "error_code": error.error_code,
                "message": error.message,
                "location": [location.field_path_elements for location in error.location.field_path_elements] if error.location else []
            })
        return {
            "success": False,
            "error": f"Google Ads API error: {ex.failure.errors[0].message}",
            "error_details": error_details,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {"success": False, "error": str(e), "timestamp": datetime.now().isoformat()}

# --- FIN DEL MÓDULO actions/googleads_actions.py ---