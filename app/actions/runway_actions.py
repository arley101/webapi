"""
Runway ML API Integration - Versión Unificada
Integración completa con Runway ML para generación de contenido con IA
Solo modo REAL - Sin simulaciones
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
from app.core.config import settings

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURACIÓN DE LA API
# ============================================================================

BASE_URL = "https://api.runwayml.com/v1"
RUNWAY_API_VERSION = os.getenv("RUNWAY_API_VERSION", "2024-11-06")
REQUEST_TIMEOUT = int(os.getenv("RUNWAY_TIMEOUT_SECONDS", "60"))

def _get_headers() -> Dict[str, str]:
    """
    Obtiene headers de autenticación para RunwayML.
    """
    # Intentar múltiples nombres de variables según documentación oficial
    api_key = (
        getattr(settings, "RUNWAYML_API_SECRET", None) or 
        os.getenv("RUNWAYML_API_SECRET") or
        getattr(settings, "RUNWAYML_API_TOKEN", None) or 
        os.getenv("RUNWAYML_API_TOKEN") or
        getattr(settings, "RUNWAY_API_KEY", None) or 
        os.getenv("RUNWAY_API_KEY")
    )
    
    if not api_key:
        raise ValueError("API Key de Runway no configurada. Configura la variable de entorno RUNWAYML_API_SECRET o RUNWAYML_API_TOKEN.")
    
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-Runway-Version": RUNWAY_API_VERSION,
    }

def _make_request(method: str, url: str, data: Dict = None) -> Dict[str, Any]:
    """
    Realizar petición HTTP a la API de Runway
    """
    headers = _get_headers()
    
    try:
        if method.upper() == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=REQUEST_TIMEOUT)
        elif method.upper() == "GET":
            response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=headers, timeout=REQUEST_TIMEOUT)
        else:
            raise ValueError(f"Método HTTP no soportado: {method}")
        
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error en petición a Runway API: {str(e)}")
        raise Exception(f"Error en API de Runway: {str(e)}")

# ============================================================================
# FUNCIONES PRINCIPALES DE RUNWAY
# ============================================================================

def runway_generate_video(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generar video usando Runway ML (imagen a video o texto a video)
    
    Parámetros:
    - prompt: Descripción del video (para texto a video)
    - promptImage: URL de imagen base (para imagen a video)
    - promptImageBase64: Imagen en base64 (alternativa a promptImage)
    - model: Modelo a usar (gen3a_turbo, gen4_aleph, etc.)
    - duration: Duración en segundos
    - ratio: Relación de aspecto (1280:720, 1920:1080, etc.)
    - seed: Semilla para reproducibilidad
    """
    try:
        # Determinar tipo de generación
        if params.get("promptImage") or params.get("promptImageBase64"):
            # Imagen a video
            endpoint = f"{BASE_URL}/image_to_video"
            payload = {
                "model": params.get("model", "gen3a_turbo"),
                "promptText": params.get("prompt", ""),
            }
            
            if params.get("promptImage"):
                payload["promptImage"] = params["promptImage"]
            elif params.get("promptImageBase64"):
                payload["promptImageBase64"] = params["promptImageBase64"]
                
        else:
            # Texto a video (si la API lo soporta)
            endpoint = f"{BASE_URL}/text_to_video"
            payload = {
                "model": params.get("model", "gen3a_turbo"),
                "promptText": params.get("prompt", ""),
            }
        
        # Parámetros opcionales
        if params.get("duration"):
            payload["duration"] = float(params["duration"])
        if params.get("ratio"):
            payload["ratio"] = params["ratio"]
        if params.get("seed"):
            payload["seed"] = int(params["seed"])
        
        # Realizar petición
        result = _make_request("POST", endpoint, payload)
        
        return {
            "status": "success",
            "task_id": result.get("id"),
            "message": "Video generation started",
            "model": payload.get("model"),
            "duration": payload.get("duration"),
            "endpoint_used": endpoint
        }
        
    except Exception as e:
        logger.error(f"Error generating video: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }

def runway_get_video_status(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Obtener el estado de un video en generación
    
    Parámetros:
    - task_id: ID de la tarea
    """
    try:
        task_id = params.get("task_id")
        if not task_id:
            return {"status": "error", "message": "task_id requerido"}
        
        endpoint = f"{BASE_URL}/tasks/{task_id}"
        result = _make_request("GET", endpoint)
        
        return {
            "status": "success",
            "task_id": task_id,
            "task_status": result.get("status"),
            "progress": result.get("progress", 0),
            "video_url": result.get("output", [{}])[0].get("url") if result.get("output") else None,
            "failure_reason": result.get("failure_reason"),
            "created_at": result.get("createdAt"),
            "estimated_time_remaining": result.get("estimatedTimeToStart")
        }
        
    except Exception as e:
        logger.error(f"Error getting video status: {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "task_id": params.get("task_id")
        }

def runway_cancel_task(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Cancelar una tarea de generación
    
    Parámetros:
    - task_id: ID de la tarea a cancelar
    """
    try:
        task_id = params.get("task_id")
        if not task_id:
            return {"status": "error", "message": "task_id requerido"}
        
        endpoint = f"{BASE_URL}/tasks/{task_id}"
        _make_request("DELETE", endpoint)
        
        return {
            "status": "success",
            "task_id": task_id,
            "message": "Task cancelled successfully"
        }
        
    except Exception as e:
        logger.error(f"Error cancelling task: {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "task_id": params.get("task_id")
        }

def runway_list_models(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Listar modelos disponibles en Runway ML - API REAL
    """
    try:
        logger.info("🎬 Obteniendo lista de modelos de Runway ML...")
        
        response = _make_request("GET", f"{BASE_URL}/models")
        
        if response.get("models"):
            logger.info(f"✅ Se obtuvieron {len(response['models'])} modelos de Runway ML")
            return {
                "status": "success",
                "models": response["models"],
                "total_models": len(response["models"])
            }
        else:
            logger.warning("⚠️ No se encontraron modelos en la respuesta de la API")
            return {
                "status": "success",
                "models": [],
                "total_models": 0,
                "message": "No se encontraron modelos disponibles"
            }
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo modelos de Runway: {str(e)}")
        return {
            "status": "error",
            "message": f"Error obteniendo modelos: {str(e)}"
        }

def runway_estimate_cost(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Estimar el costo de una generación de video
    
    Parámetros:
    - duration: Duración en segundos
    - model: Modelo a usar
    - quality: Calidad del video
    """
    try:
        duration = params.get("duration", 3)
        model = params.get("model", "gen3a_turbo")
        
        # Estimaciones aproximadas (pueden variar)
        base_cost_per_second = 0.10 if model == "gen3a_turbo" else 0.15
        estimated_cost = duration * base_cost_per_second
        
        return {
            "status": "success",
            "estimated_cost_usd": round(estimated_cost, 2),
            "duration_seconds": duration,
            "model": model,
            "cost_per_second": base_cost_per_second,
            "currency": "USD",
            "disclaimer": "Estimación aproximada. El costo real puede variar."
        }
        
    except Exception as e:
        logger.error(f"Error estimating cost: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }

# ============================================================================
# FUNCIONES AVANZADAS DE RUNWAY
# ============================================================================

def runway_generate_video_advanced(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generación avanzada de videos con parámetros extendidos
    
    Parámetros:
    - model_type: Tipo de modelo (gen-2, gen-3, etc.)
    - input_media: Media de entrada (imagen, texto, video)
    - generation_params: Parámetros de generación específicos
    - style_settings: Configuraciones de estilo
    - quality_settings: Configuraciones de calidad
    """
    try:
        model_type = params.get("model_type", "gen3a_turbo")
        input_media = params.get("input_media", {})
        generation_params = params.get("generation_params", {})
        
        # Construir payload para la API
        if input_media.get("type") == "image":
            endpoint = f"{BASE_URL}/image_to_video"
            payload = {
                "model": model_type,
                "promptImage": input_media.get("url") or input_media.get("content"),
                "promptText": input_media.get("description", "")
            }
        else:
            endpoint = f"{BASE_URL}/text_to_video"
            payload = {
                "model": model_type,
                "promptText": input_media.get("content", "")
            }
        
        # Agregar parámetros de generación
        if generation_params.get("duration"):
            payload["duration"] = float(generation_params["duration"])
        if generation_params.get("ratio"):
            payload["ratio"] = generation_params["ratio"]
        if generation_params.get("seed"):
            payload["seed"] = int(generation_params["seed"])
        
        # Realizar petición
        result = _make_request("POST", endpoint, payload)
        
        return {
            "status": "success",
            "task_id": result.get("id"),
            "model_type": model_type,
            "input_type": input_media.get("type", "text"),
            "generation_params": generation_params,
            "estimated_completion_time": f"{generation_params.get('duration', 3) * 2} minutos"
        }
        
    except Exception as e:
        logger.error(f"Error in advanced video generation: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }

def runway_image_to_video_pro(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Conversión profesional de imagen a video con controles avanzados
    
    Parámetros:
    - source_images: Lista de imágenes fuente
    - motion_settings: Configuraciones de movimiento
    - camera_controls: Controles de cámara
    - duration_settings: Configuraciones de duración
    """
    try:
        source_images = params.get("source_images", [])
        if not source_images:
            return {"status": "error", "message": "Se requiere al menos una imagen fuente"}
        
        motion_settings = params.get("motion_settings", {})
        duration_settings = params.get("duration_settings", {})
        
        results = []
        
        for image in source_images:
            payload = {
                "model": "gen3a_turbo",
                "promptImage": image.get("url"),
                "promptText": image.get("motion_prompt", ""),
                "duration": duration_settings.get("duration", 3)
            }
            
            # Aplicar configuraciones de movimiento
            if motion_settings.get("intensity"):
                payload["promptText"] += f" with {motion_settings['intensity']} motion"
            
            endpoint = f"{BASE_URL}/image_to_video"
            result = _make_request("POST", endpoint, payload)
            
            results.append({
                "image_id": image.get("id", "unknown"),
                "task_id": result.get("id"),
                "status": "started"
            })
        
        return {
            "status": "success",
            "total_conversions": len(results),
            "conversions": results,
            "motion_settings": motion_settings,
            "duration": duration_settings.get("duration", 3)
        }
        
    except Exception as e:
        logger.error(f"Error in professional image to video: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }

def runway_text_to_video_studio(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Estudio de texto a video con capacidades narrativas
    
    Parámetros:
    - narrative_prompts: Lista de prompts narrativos
    - scene_settings: Configuraciones de escena
    - style_guide: Guía de estilo
    """
    try:
        narrative_prompts = params.get("narrative_prompts", [])
        if not narrative_prompts:
            return {"status": "error", "message": "Se requiere al menos un prompt narrativo"}
        
        scene_settings = params.get("scene_settings", {})
        style_guide = params.get("style_guide", {})
        
        generations = []
        
        for i, prompt_data in enumerate(narrative_prompts):
            prompt_text = prompt_data.get("text", "")
            
            # Aplicar configuraciones de estilo
            if style_guide.get("visual_style"):
                prompt_text += f" in {style_guide['visual_style']} style"
            
            payload = {
                "model": "gen3a_turbo",
                "promptText": prompt_text,
                "duration": prompt_data.get("duration", 3)
            }
            
            # Aplicar configuraciones de escena
            if scene_settings.get("lighting"):
                payload["promptText"] += f" with {scene_settings['lighting']} lighting"
            
            endpoint = f"{BASE_URL}/text_to_video"
            result = _make_request("POST", endpoint, payload)
            
            generations.append({
                "scene_number": i + 1,
                "task_id": result.get("id"),
                "prompt": prompt_text,
                "duration": payload["duration"],
                "status": "generating"
            })
        
        return {
            "status": "success",
            "total_scenes": len(generations),
            "narrative_generations": generations,
            "style_guide": style_guide,
            "estimated_total_time": f"{sum([g.get('duration', 3) for g in generations])} segundos"
        }
        
    except Exception as e:
        logger.error(f"Error in text to video studio: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }

# ============================================================================
# FUNCIONES DE UTILIDAD
# ============================================================================

def runway_get_result_url(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Obtener URL del resultado de un video generado
    """
    try:
        task_id = params.get("task_id")
        if not task_id:
            return {"status": "error", "message": "task_id requerido"}
        
        status_result = runway_get_video_status(client, {"task_id": task_id})
        
        if status_result.get("status") == "success" and status_result.get("video_url"):
            return {
                "status": "success",
                "task_id": task_id,
                "video_url": status_result["video_url"],
                "ready": True
            }
        else:
            return {
                "status": "pending",
                "task_id": task_id,
                "video_url": None,
                "ready": False,
                "task_status": status_result.get("task_status")
            }
        
    except Exception as e:
        logger.error(f"Error getting result URL: {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "task_id": params.get("task_id")
        }

def runway_wait_and_save(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Esperar a que termine una generación y guardar el resultado
    
    Parámetros:
    - task_id: ID de la tarea
    - max_wait_minutes: Tiempo máximo de espera en minutos
    - check_interval_seconds: Intervalo de verificación en segundos
    """
    try:
        task_id = params.get("task_id")
        max_wait_minutes = params.get("max_wait_minutes", 10)
        check_interval_seconds = params.get("check_interval_seconds", 30)
        
        if not task_id:
            return {"status": "error", "message": "task_id requerido"}
        
        max_checks = (max_wait_minutes * 60) // check_interval_seconds
        
        for check in range(max_checks):
            status_result = runway_get_video_status(client, {"task_id": task_id})
            
            if status_result.get("task_status") == "succeeded":
                # Video completado
                return {
                    "status": "success",
                    "task_id": task_id,
                    "video_url": status_result.get("video_url"),
                    "completion_time": f"{check * check_interval_seconds} segundos",
                    "ready": True
                }
            elif status_result.get("task_status") == "failed":
                return {
                    "status": "error",
                    "task_id": task_id,
                    "message": status_result.get("failure_reason", "Generación falló"),
                    "failed": True
                }
            
            # Esperar antes del siguiente check
            time.sleep(check_interval_seconds)
        
        # Tiempo agotado
        return {
            "status": "timeout",
            "task_id": task_id,
            "message": f"Tiempo de espera agotado después de {max_wait_minutes} minutos",
            "last_status": status_result.get("task_status") if 'status_result' in locals() else "unknown"
        }
        
    except Exception as e:
        logger.error(f"Error waiting for completion: {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "task_id": params.get("task_id")
        }

def runway_check_configuration(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verificar la configuración actual de Runway
    """
    try:
        # Verificar múltiples nombres de variables según documentación oficial
        api_key = (
            getattr(settings, "RUNWAYML_API_SECRET", None) or 
            os.getenv("RUNWAYML_API_SECRET") or
            getattr(settings, "RUNWAYML_API_TOKEN", None) or 
            os.getenv("RUNWAYML_API_TOKEN") or
            getattr(settings, "RUNWAY_API_KEY", None) or 
            os.getenv("RUNWAY_API_KEY")
        )
        
        # Determinar la fuente de la API key
        api_source = "none"
        if os.getenv("RUNWAYML_API_SECRET"):
            api_source = "environment (RUNWAYML_API_SECRET)"
        elif os.getenv("RUNWAYML_API_TOKEN"):
            api_source = "environment (RUNWAYML_API_TOKEN)"
        elif os.getenv("RUNWAY_API_KEY"):
            api_source = "environment (RUNWAY_API_KEY - deprecated)"
        elif getattr(settings, "RUNWAYML_API_SECRET", None):
            api_source = "settings (RUNWAYML_API_SECRET)"
        elif getattr(settings, "RUNWAYML_API_TOKEN", None):
            api_source = "settings (RUNWAYML_API_TOKEN)"
        elif getattr(settings, "RUNWAY_API_KEY", None):
            api_source = "settings (RUNWAY_API_KEY - deprecated)"
        
        return {
            "status": "success",
            "configuration": {
                "api_key_configured": bool(api_key),
                "api_key_source": api_source,
                "base_url": BASE_URL,
                "api_version": RUNWAY_API_VERSION,
                "timeout": REQUEST_TIMEOUT,
                "mode": "REAL_API_ONLY",
                "recommended_var": "RUNWAYML_API_SECRET"
            },
            "endpoints": {
                "image_to_video": f"{BASE_URL}/image_to_video",
                "text_to_video": f"{BASE_URL}/text_to_video",
                "task_status": f"{BASE_URL}/tasks/{{task_id}}"
            },
            "ready": bool(api_key)
        }
        
    except Exception as e:
        logger.error(f"Error checking configuration: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }
