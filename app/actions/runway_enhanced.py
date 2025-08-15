"""
Runway ML Enhanced API Integration
Integración completa con Runway ML para generación de contenido con IA
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
# RUNWAY ML VIDEO & IMAGE GENERATION
# ============================================================================

async def runway_generate_video_advanced(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generación avanzada de videos con Runway ML
    
    Parámetros:
    - model_type: Tipo de modelo (gen-2, gen-3, motion-brush, etc.)
    - generation_params: Parámetros de generación específicos
    - input_media: Media de entrada (imagen, texto, video)
    - style_settings: Configuraciones de estilo
    - quality_settings: Configuraciones de calidad
    - batch_processing: Procesamiento en lote
    """
    try:
        api_key = os.getenv("RUNWAY_API_KEY")
        if not api_key:
            return {
                "status": "error",
                "message": "RUNWAY_API_KEY no configurada"
            }
        
        model_type = params.get("model_type", "gen-2")
        generation_params = params.get("generation_params", {})
        input_media = params.get("input_media", {})
        style_settings = params.get("style_settings", {})
        quality_settings = params.get("quality_settings", {})
        batch_processing = params.get("batch_processing", {})
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        base_url = "https://api.runwayml.com/v1"
        
        generation_results = []
        
        # Procesar generación única o en lote
        if batch_processing.get("enabled"):
            prompts = batch_processing.get("prompts", [])
            max_concurrent = batch_processing.get("max_concurrent", 3)
            
            # Procesar en lotes para no sobrecargar la API
            for i in range(0, len(prompts), max_concurrent):
                batch = prompts[i:i + max_concurrent]
                batch_results = await _process_video_batch(
                    base_url, headers, model_type, batch, generation_params, 
                    style_settings, quality_settings
                )
                generation_results.extend(batch_results)
                
                # Pausa entre lotes para respetar rate limits
                if i + max_concurrent < len(prompts):
                    await asyncio.sleep(2)
        
        else:
            # Generación única
            single_result = await _generate_single_video(
                base_url, headers, model_type, generation_params, 
                input_media, style_settings, quality_settings
            )
            generation_results.append(single_result)
        
        # Procesar resultados y configurar seguimiento
        successful_generations = [r for r in generation_results if r.get("status") == "success"]
        
        # Configurar monitoreo de progreso para generaciones largas
        monitoring_config = {}
        if successful_generations:
            monitoring_config = await _setup_generation_monitoring(
                successful_generations, generation_params.get("monitor_progress", True)
            )
        
        result = {
            "status": "success",
            "model_type": model_type,
            "total_generations": len(generation_results),
            "successful_generations": len(successful_generations),
            "generation_results": generation_results,
            "monitoring": monitoring_config,
            "batch_processing": batch_processing.get("enabled", False),
            "estimated_completion_time": _calculate_completion_time(successful_generations)
        }
        
        # Persistir información de generación
        await _persist_runway_action(client, result, "video_generation_advanced")
        
        return result
        
    except Exception as e:
        logger.error(f"Error generating video with Runway: {str(e)}")
        return {
            "status": "error",
            "message": f"Error al generar video: {str(e)}"
        }

async def runway_image_to_video_pro(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Conversión profesional de imagen a video con controles avanzados
    
    Parámetros:
    - source_images: Lista de imágenes fuente
    - motion_settings: Configuraciones de movimiento
    - camera_controls: Controles de cámara (zoom, pan, rotate)
    - effects: Efectos visuales a aplicar
    - duration_settings: Configuraciones de duración
    - export_settings: Configuraciones de exportación
    """
    try:
        api_key = os.getenv("RUNWAY_API_KEY")
        source_images = params.get("source_images", [])
        motion_settings = params.get("motion_settings", {})
        camera_controls = params.get("camera_controls", {})
        effects = params.get("effects", [])
        duration_settings = params.get("duration_settings", {})
        export_settings = params.get("export_settings", {})
        
        if not source_images:
            return {
                "status": "error",
                "message": "Se requiere al menos una imagen fuente"
            }
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        base_url = "https://api.runwayml.com/v1"
        conversion_results = []
        
        for idx, image_config in enumerate(source_images):
            try:
                # Preparar configuración de conversión
                conversion_payload = {
                    "model": "gen-2",
                    "image": image_config.get("url") or image_config.get("base64"),
                    "prompt": image_config.get("motion_prompt", "subtle movement"),
                    "duration": duration_settings.get("duration", 4),
                    "resolution": export_settings.get("resolution", "1280x720"),
                    "fps": export_settings.get("fps", 24)
                }
                
                # Configurar controles de movimiento
                if motion_settings:
                    conversion_payload["motion_config"] = {
                        "intensity": motion_settings.get("intensity", 0.5),
                        "smoothness": motion_settings.get("smoothness", 0.8),
                        "coherence": motion_settings.get("coherence", 0.9),
                        "motion_type": motion_settings.get("type", "natural")
                    }
                
                # Configurar controles de cámara
                if camera_controls:
                    conversion_payload["camera_motion"] = {
                        "zoom": camera_controls.get("zoom", {"start": 1.0, "end": 1.0}),
                        "pan": camera_controls.get("pan", {"x": 0, "y": 0}),
                        "rotate": camera_controls.get("rotate", 0),
                        "tilt": camera_controls.get("tilt", 0)
                    }
                
                # Aplicar efectos visuales
                if effects:
                    conversion_payload["effects"] = []
                    for effect in effects:
                        effect_config = {
                            "type": effect.get("type"),
                            "intensity": effect.get("intensity", 0.5),
                            "timing": effect.get("timing", "throughout")
                        }
                        conversion_payload["effects"].append(effect_config)
                
                # Enviar solicitud de conversión
                response = requests.post(
                    f"{base_url}/image_to_video",
                    json=conversion_payload,
                    headers=headers
                )
                
                if response.status_code in [200, 201]:
                    result_data = response.json()
                    
                    conversion_results.append({
                        "image_index": idx,
                        "source_image": image_config.get("name", f"image_{idx}"),
                        "task_id": result_data.get("id"),
                        "status": "processing",
                        "estimated_completion": result_data.get("estimated_time", "3-5 minutes"),
                        "motion_prompt": image_config.get("motion_prompt"),
                        "camera_motion": bool(camera_controls),
                        "effects_applied": len(effects)
                    })
                    
                else:
                    conversion_results.append({
                        "image_index": idx,
                        "source_image": image_config.get("name", f"image_{idx}"),
                        "status": "error",
                        "error": f"API Error: {response.status_code} - {response.text}"
                    })
            
            except Exception as e:
                conversion_results.append({
                    "image_index": idx,
                    "source_image": image_config.get("name", f"image_{idx}"),
                    "status": "error",
                    "error": str(e)
                })
        
        # Configurar seguimiento automático de conversiones
        tracking_config = {}
        processing_tasks = [r for r in conversion_results if r.get("status") == "processing"]
        
        if processing_tasks:
            tracking_config = await _setup_conversion_tracking(processing_tasks)
        
        result = {
            "status": "success",
            "total_conversions": len(conversion_results),
            "processing_conversions": len(processing_tasks),
            "conversion_results": conversion_results,
            "tracking": tracking_config,
            "motion_settings": motion_settings,
            "camera_controls": camera_controls,
            "effects_count": len(effects),
            "export_settings": export_settings
        }
        
        # Persistir información de conversión
        await _persist_runway_action(client, result, "image_to_video_pro")
        
        return result
        
    except Exception as e:
        logger.error(f"Error in image to video conversion: {str(e)}")
        return {
            "status": "error",
            "message": f"Error en conversión imagen a video: {str(e)}"
        }

async def runway_text_to_video_studio(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generación de video desde texto con controles de estudio profesional
    
    Parámetros:
    - text_prompts: Lista de prompts de texto
    - style_presets: Presets de estilo predefinidos
    - cinematic_settings: Configuraciones cinematográficas
    - narrative_structure: Estructura narrativa
    - music_integration: Integración con música
    - branding: Configuraciones de marca
    """
    try:
        api_key = os.getenv("RUNWAY_API_KEY")
        text_prompts = params.get("text_prompts", [])
        style_presets = params.get("style_presets", {})
        cinematic_settings = params.get("cinematic_settings", {})
        narrative_structure = params.get("narrative_structure", {})
        music_integration = params.get("music_integration", {})
        branding = params.get("branding", {})
        
        if not text_prompts:
            return {
                "status": "error",
                "message": "Se requiere al menos un prompt de texto"
            }
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        base_url = "https://api.runwayml.com/v1"
        video_results = []
        
        # Procesar estructura narrativa si está definida
        if narrative_structure.get("enabled"):
            text_prompts = await _structure_narrative_prompts(
                text_prompts, narrative_structure
            )
        
        for idx, prompt_config in enumerate(text_prompts):
            try:
                # Preparar configuración de generación
                generation_payload = {
                    "model": "gen-3",
                    "prompt": prompt_config.get("text"),
                    "duration": prompt_config.get("duration", 4),
                    "resolution": cinematic_settings.get("resolution", "1920x1080"),
                    "fps": cinematic_settings.get("fps", 30),
                    "seed": prompt_config.get("seed", None)
                }
                
                # Aplicar presets de estilo
                if style_presets:
                    style_prompt = _apply_style_preset(
                        prompt_config.get("text"), style_presets
                    )
                    generation_payload["prompt"] = style_prompt
                
                # Configurar aspectos cinematográficos
                if cinematic_settings:
                    generation_payload["cinematic"] = {
                        "camera_angle": cinematic_settings.get("camera_angle", "medium"),
                        "lighting": cinematic_settings.get("lighting", "natural"),
                        "color_grading": cinematic_settings.get("color_grading", "neutral"),
                        "depth_of_field": cinematic_settings.get("depth_of_field", False),
                        "motion_blur": cinematic_settings.get("motion_blur", False)
                    }
                
                # Configurar branding si está especificado
                if branding:
                    generation_payload["branding"] = {
                        "logo_placement": branding.get("logo_placement"),
                        "color_palette": branding.get("color_palette", []),
                        "watermark": branding.get("watermark", False),
                        "brand_elements": branding.get("brand_elements", [])
                    }
                
                # Configurar integración de música
                if music_integration.get("enabled"):
                    generation_payload["audio"] = {
                        "background_music": music_integration.get("track_url"),
                        "sync_to_beats": music_integration.get("sync_to_beats", False),
                        "audio_style": music_integration.get("style", "cinematic"),
                        "volume": music_integration.get("volume", 0.7)
                    }
                
                # Enviar solicitud de generación
                response = requests.post(
                    f"{base_url}/text_to_video",
                    json=generation_payload,
                    headers=headers
                )
                
                if response.status_code in [200, 201]:
                    result_data = response.json()
                    
                    video_results.append({
                        "prompt_index": idx,
                        "original_prompt": prompt_config.get("text"),
                        "enhanced_prompt": generation_payload.get("prompt"),
                        "task_id": result_data.get("id"),
                        "status": "generating",
                        "duration": prompt_config.get("duration"),
                        "resolution": cinematic_settings.get("resolution"),
                        "style_applied": bool(style_presets),
                        "cinematic_enhanced": bool(cinematic_settings),
                        "branded": bool(branding),
                        "music_integrated": music_integration.get("enabled", False),
                        "estimated_completion": result_data.get("estimated_time", "4-8 minutes")
                    })
                    
                else:
                    video_results.append({
                        "prompt_index": idx,
                        "original_prompt": prompt_config.get("text"),
                        "status": "error",
                        "error": f"API Error: {response.status_code} - {response.text}"
                    })
            
            except Exception as e:
                video_results.append({
                    "prompt_index": idx,
                    "original_prompt": prompt_config.get("text", ""),
                    "status": "error",
                    "error": str(e)
                })
        
        # Configurar seguimiento de generación
        tracking_config = {}
        generating_videos = [v for v in video_results if v.get("status") == "generating"]
        
        if generating_videos:
            tracking_config = await _setup_video_generation_tracking(generating_videos)
        
        result = {
            "status": "success",
            "total_videos": len(video_results),
            "generating_videos": len(generating_videos),
            "video_results": video_results,
            "tracking": tracking_config,
            "narrative_structure": narrative_structure.get("enabled", False),
            "style_presets": style_presets,
            "cinematic_settings": cinematic_settings,
            "music_integration": music_integration.get("enabled", False),
            "branding_applied": bool(branding)
        }
        
        # Persistir información de generación
        await _persist_runway_action(client, result, "text_to_video_studio")
        
        return result
        
    except Exception as e:
        logger.error(f"Error in text to video generation: {str(e)}")
        return {
            "status": "error",
            "message": f"Error en generación texto a video: {str(e)}"
        }

async def runway_video_editing_suite(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Suite completa de edición de video con IA
    
    Parámetros:
    - source_videos: Videos fuente para editar
    - editing_operations: Lista de operaciones de edición
    - ai_enhancements: Mejoras con IA (upscaling, denoising, etc.)
    - transitions: Configuración de transiciones
    - effects_timeline: Timeline de efectos
    - output_formats: Formatos de salida
    """
    try:
        api_key = os.getenv("RUNWAY_API_KEY")
        source_videos = params.get("source_videos", [])
        editing_operations = params.get("editing_operations", [])
        ai_enhancements = params.get("ai_enhancements", {})
        transitions = params.get("transitions", {})
        effects_timeline = params.get("effects_timeline", [])
        output_formats = params.get("output_formats", [])
        
        if not source_videos:
            return {
                "status": "error",
                "message": "Se requiere al menos un video fuente"
            }
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        base_url = "https://api.runwayml.com/v1"
        editing_results = []
        
        for video_config in source_videos:
            try:
                video_id = video_config.get("id") or video_config.get("url")
                
                # Preparar configuración de edición
                editing_payload = {
                    "source_video": video_id,
                    "operations": [],
                    "output_settings": {
                        "resolution": video_config.get("target_resolution", "1920x1080"),
                        "fps": video_config.get("target_fps", 30),
                        "codec": video_config.get("codec", "h264"),
                        "quality": video_config.get("quality", "high")
                    }
                }
                
                # Procesar operaciones de edición
                for operation in editing_operations:
                    op_config = {
                        "type": operation.get("type"),  # trim, crop, scale, rotate, etc.
                        "parameters": operation.get("parameters", {}),
                        "timing": operation.get("timing", {"start": 0, "end": -1})
                    }
                    
                    # Configuraciones específicas por tipo de operación
                    if operation.get("type") == "trim":
                        op_config["parameters"] = {
                            "start_time": operation.get("start_time", 0),
                            "end_time": operation.get("end_time", -1)
                        }
                    
                    elif operation.get("type") == "crop":
                        op_config["parameters"] = {
                            "x": operation.get("x", 0),
                            "y": operation.get("y", 0),
                            "width": operation.get("width", -1),
                            "height": operation.get("height", -1)
                        }
                    
                    elif operation.get("type") == "color_correction":
                        op_config["parameters"] = {
                            "brightness": operation.get("brightness", 0),
                            "contrast": operation.get("contrast", 0),
                            "saturation": operation.get("saturation", 0),
                            "hue": operation.get("hue", 0)
                        }
                    
                    editing_payload["operations"].append(op_config)
                
                # Configurar mejoras con IA
                if ai_enhancements:
                    ai_config = {}
                    
                    if ai_enhancements.get("upscale"):
                        ai_config["upscale"] = {
                            "factor": ai_enhancements.get("upscale_factor", 2),
                            "model": ai_enhancements.get("upscale_model", "real-esrgan")
                        }
                    
                    if ai_enhancements.get("denoise"):
                        ai_config["denoise"] = {
                            "strength": ai_enhancements.get("denoise_strength", 0.5),
                            "preserve_details": ai_enhancements.get("preserve_details", True)
                        }
                    
                    if ai_enhancements.get("stabilization"):
                        ai_config["stabilization"] = {
                            "strength": ai_enhancements.get("stabilization_strength", 0.7),
                            "crop_compensation": ai_enhancements.get("crop_compensation", True)
                        }
                    
                    if ai_enhancements.get("frame_interpolation"):
                        ai_config["frame_interpolation"] = {
                            "target_fps": ai_enhancements.get("target_fps", 60),
                            "quality": ai_enhancements.get("interpolation_quality", "high")
                        }
                    
                    editing_payload["ai_enhancements"] = ai_config
                
                # Configurar transiciones
                if transitions:
                    editing_payload["transitions"] = {
                        "type": transitions.get("type", "fade"),
                        "duration": transitions.get("duration", 1.0),
                        "easing": transitions.get("easing", "ease-in-out"),
                        "custom_parameters": transitions.get("custom_parameters", {})
                    }
                
                # Configurar timeline de efectos
                if effects_timeline:
                    editing_payload["effects"] = []
                    for effect in effects_timeline:
                        effect_config = {
                            "type": effect.get("type"),
                            "start_time": effect.get("start_time", 0),
                            "duration": effect.get("duration", 1),
                            "intensity": effect.get("intensity", 0.5),
                            "parameters": effect.get("parameters", {})
                        }
                        editing_payload["effects"].append(effect_config)
                
                # Enviar solicitud de edición
                response = requests.post(
                    f"{base_url}/video_edit",
                    json=editing_payload,
                    headers=headers
                )
                
                if response.status_code in [200, 201]:
                    result_data = response.json()
                    
                    editing_results.append({
                        "source_video": video_config.get("name", video_id),
                        "task_id": result_data.get("id"),
                        "status": "processing",
                        "operations_count": len(editing_operations),
                        "ai_enhancements": list(ai_enhancements.keys()) if ai_enhancements else [],
                        "transitions_applied": bool(transitions),
                        "effects_count": len(effects_timeline),
                        "estimated_completion": result_data.get("estimated_time", "5-15 minutes"),
                        "output_settings": editing_payload["output_settings"]
                    })
                    
                else:
                    editing_results.append({
                        "source_video": video_config.get("name", video_id),
                        "status": "error",
                        "error": f"API Error: {response.status_code} - {response.text}"
                    })
            
            except Exception as e:
                editing_results.append({
                    "source_video": video_config.get("name", "unknown"),
                    "status": "error",
                    "error": str(e)
                })
        
        # Configurar seguimiento de edición
        tracking_config = {}
        processing_edits = [e for e in editing_results if e.get("status") == "processing"]
        
        if processing_edits:
            tracking_config = await _setup_editing_tracking(processing_edits)
        
        # Configurar múltiples formatos de salida
        output_config = {}
        if output_formats:
            output_config = await _configure_multiple_outputs(processing_edits, output_formats)
        
        result = {
            "status": "success",
            "total_edits": len(editing_results),
            "processing_edits": len(processing_edits),
            "editing_results": editing_results,
            "tracking": tracking_config,
            "output_formats": output_config,
            "ai_enhancements": ai_enhancements,
            "operations_applied": len(editing_operations),
            "effects_timeline": len(effects_timeline)
        }
        
        # Persistir información de edición
        await _persist_runway_action(client, result, "video_editing_suite")
        
        return result
        
    except Exception as e:
        logger.error(f"Error in video editing suite: {str(e)}")
        return {
            "status": "error",
            "message": f"Error en suite de edición: {str(e)}"
        }

async def runway_model_training_custom(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Entrenamiento de modelos personalizados en Runway
    
    Parámetros:
    - training_data: Datos de entrenamiento
    - model_config: Configuración del modelo
    - training_params: Parámetros de entrenamiento
    - validation_settings: Configuraciones de validación
    - deployment_config: Configuración de despliegue
    """
    try:
        api_key = os.getenv("RUNWAY_API_KEY")
        training_data = params.get("training_data", {})
        model_config = params.get("model_config", {})
        training_params = params.get("training_params", {})
        validation_settings = params.get("validation_settings", {})
        deployment_config = params.get("deployment_config", {})
        
        if not training_data.get("dataset_url") and not training_data.get("dataset_id"):
            return {
                "status": "error",
                "message": "Se requiere dataset_url o dataset_id para el entrenamiento"
            }
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        base_url = "https://api.runwayml.com/v1"
        
        # Preparar configuración de entrenamiento
        training_payload = {
            "model_name": model_config.get("name", f"custom_model_{int(time.time())}"),
            "model_type": model_config.get("type", "image_generation"),
            "base_model": model_config.get("base_model", "stable-diffusion-v1-5"),
            "dataset": {
                "source": training_data.get("dataset_url") or training_data.get("dataset_id"),
                "format": training_data.get("format", "images"),
                "size": training_data.get("size", "auto"),
                "preprocessing": training_data.get("preprocessing", {})
            },
            "training_config": {
                "epochs": training_params.get("epochs", 100),
                "batch_size": training_params.get("batch_size", 4),
                "learning_rate": training_params.get("learning_rate", 1e-4),
                "resolution": training_params.get("resolution", 512),
                "gradient_accumulation": training_params.get("gradient_accumulation", 1),
                "mixed_precision": training_params.get("mixed_precision", True)
            }
        }
        
        # Configurar validación
        if validation_settings:
            training_payload["validation"] = {
                "validation_split": validation_settings.get("split", 0.1),
                "validation_prompts": validation_settings.get("prompts", []),
                "validation_frequency": validation_settings.get("frequency", 10),
                "early_stopping": validation_settings.get("early_stopping", {})
            }
        
        # Configurar técnicas avanzadas de entrenamiento
        if training_params.get("advanced_techniques"):
            advanced = training_params["advanced_techniques"]
            training_payload["advanced"] = {
                "lora_rank": advanced.get("lora_rank", 4),
                "dreambooth": advanced.get("dreambooth", False),
                "textual_inversion": advanced.get("textual_inversion", False),
                "controlnet": advanced.get("controlnet", False),
                "style_transfer": advanced.get("style_transfer", False)
            }
        
        # Enviar solicitud de entrenamiento
        response = requests.post(
            f"{base_url}/model/train",
            json=training_payload,
            headers=headers
        )
        
        if response.status_code in [200, 201]:
            training_result = response.json()
            
            # Configurar monitoreo de entrenamiento
            monitoring_config = await _setup_training_monitoring(
                training_result.get("training_id"), training_params
            )
            
            # Configurar despliegue automático si está habilitado
            deployment_setup = {}
            if deployment_config.get("auto_deploy"):
                deployment_setup = await _configure_auto_deployment(
                    training_result.get("training_id"), deployment_config
                )
            
            result = {
                "status": "success",
                "training_id": training_result.get("training_id"),
                "model_name": training_payload["model_name"],
                "model_type": training_payload["model_type"],
                "dataset_info": training_payload["dataset"],
                "training_config": training_payload["training_config"],
                "estimated_training_time": training_result.get("estimated_time", "2-6 hours"),
                "monitoring": monitoring_config,
                "deployment": deployment_setup,
                "status_url": training_result.get("status_url"),
                "cost_estimate": training_result.get("cost_estimate")
            }
            
            # Persistir información de entrenamiento
            await _persist_runway_action(client, result, "model_training_started")
            
            return result
        
        else:
            return {
                "status": "error",
                "message": f"Error al iniciar entrenamiento: {response.status_code} - {response.text}"
            }
        
    except Exception as e:
        logger.error(f"Error in model training: {str(e)}")
        return {
            "status": "error",
            "message": f"Error en entrenamiento de modelo: {str(e)}"
        }

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

async def _process_video_batch(base_url: str, headers: Dict, model_type: str, 
                             prompts: List, generation_params: Dict, 
                             style_settings: Dict, quality_settings: Dict) -> List[Dict]:
    """Procesar lote de videos"""
    try:
        batch_results = []
        
        for prompt_config in prompts:
            try:
                payload = {
                    "model": model_type,
                    "prompt": prompt_config.get("text"),
                    "duration": generation_params.get("duration", 4),
                    "resolution": quality_settings.get("resolution", "1280x720"),
                    "fps": quality_settings.get("fps", 24)
                }
                
                # Aplicar configuraciones de estilo
                if style_settings:
                    payload["style"] = style_settings
                
                response = requests.post(
                    f"{base_url}/generate",
                    json=payload,
                    headers=headers
                )
                
                if response.status_code in [200, 201]:
                    result = response.json()
                    batch_results.append({
                        "prompt": prompt_config.get("text"),
                        "task_id": result.get("id"),
                        "status": "success"
                    })
                else:
                    batch_results.append({
                        "prompt": prompt_config.get("text"),
                        "status": "error",
                        "error": response.text
                    })
                
            except Exception as e:
                batch_results.append({
                    "prompt": prompt_config.get("text", ""),
                    "status": "error",
                    "error": str(e)
                })
        
        return batch_results
        
    except Exception as e:
        logger.error(f"Error processing video batch: {str(e)}")
        return []

async def _generate_single_video(base_url: str, headers: Dict, model_type: str,
                                generation_params: Dict, input_media: Dict,
                                style_settings: Dict, quality_settings: Dict) -> Dict:
    """Generar video único"""
    try:
        payload = {
            "model": model_type,
            "prompt": generation_params.get("prompt", ""),
            "duration": generation_params.get("duration", 4),
            "resolution": quality_settings.get("resolution", "1280x720"),
            "fps": quality_settings.get("fps", 24)
        }
        
        # Agregar media de entrada si se proporciona
        if input_media.get("image_url"):
            payload["image"] = input_media["image_url"]
        
        if input_media.get("video_url"):
            payload["video"] = input_media["video_url"]
        
        # Aplicar configuraciones de estilo
        if style_settings:
            payload.update(style_settings)
        
        response = requests.post(
            f"{base_url}/generate",
            json=payload,
            headers=headers
        )
        
        if response.status_code in [200, 201]:
            result = response.json()
            return {
                "prompt": generation_params.get("prompt"),
                "task_id": result.get("id"),
                "status": "success",
                "estimated_time": result.get("estimated_time")
            }
        else:
            return {
                "prompt": generation_params.get("prompt"),
                "status": "error",
                "error": f"API Error: {response.status_code} - {response.text}"
            }
        
    except Exception as e:
        return {
            "prompt": generation_params.get("prompt", ""),
            "status": "error",
            "error": str(e)
        }

async def _setup_generation_monitoring(successful_generations: List[Dict], 
                                     monitor_progress: bool) -> Dict:
    """Configurar monitoreo de generación"""
    try:
        if not monitor_progress:
            return {"enabled": False}
        
        task_ids = [g.get("task_id") for g in successful_generations if g.get("task_id")]
        
        return {
            "enabled": True,
            "task_ids": task_ids,
            "check_interval": 30,  # segundos
            "notification_webhook": os.getenv("RUNWAY_WEBHOOK_URL"),
            "progress_tracking": True,
            "auto_download": True
        }
        
    except Exception as e:
        logger.error(f"Error setting up monitoring: {str(e)}")
        return {"enabled": False, "error": str(e)}

def _calculate_completion_time(successful_generations: List[Dict]) -> str:
    """Calcular tiempo estimado de completación"""
    try:
        if not successful_generations:
            return "N/A"
        
        # Tiempo promedio por generación (en minutos)
        avg_time_per_generation = 5
        total_generations = len(successful_generations)
        
        estimated_minutes = total_generations * avg_time_per_generation
        
        if estimated_minutes < 60:
            return f"{estimated_minutes} minutos"
        else:
            hours = estimated_minutes // 60
            minutes = estimated_minutes % 60
            return f"{hours}h {minutes}m"
        
    except Exception:
        return "Calculando..."

async def _setup_conversion_tracking(processing_tasks: List[Dict]) -> Dict:
    """Configurar seguimiento de conversiones"""
    try:
        task_ids = [task.get("task_id") for task in processing_tasks if task.get("task_id")]
        
        return {
            "enabled": True,
            "conversion_tasks": task_ids,
            "status_check_interval": 45,  # segundos
            "auto_notification": True,
            "download_completed": True,
            "tracking_webhook": os.getenv("RUNWAY_CONVERSION_WEBHOOK")
        }
        
    except Exception as e:
        return {"enabled": False, "error": str(e)}

async def _structure_narrative_prompts(text_prompts: List[Dict], 
                                     narrative_structure: Dict) -> List[Dict]:
    """Estructurar prompts según narrativa"""
    try:
        structure_type = narrative_structure.get("type", "linear")
        
        if structure_type == "three_act":
            # Estructura de tres actos
            act_distribution = narrative_structure.get("act_distribution", [0.25, 0.5, 0.25])
            total_prompts = len(text_prompts)
            
            act1_count = int(total_prompts * act_distribution[0])
            act2_count = int(total_prompts * act_distribution[1])
            act3_count = total_prompts - act1_count - act2_count
            
            # Modificar prompts según el acto
            structured_prompts = []
            
            for i, prompt in enumerate(text_prompts):
                if i < act1_count:
                    # Acto 1: Establecimiento
                    enhanced_text = f"establishing shot, introduction, {prompt.get('text')}"
                elif i < act1_count + act2_count:
                    # Acto 2: Desarrollo
                    enhanced_text = f"development, conflict, {prompt.get('text')}"
                else:
                    # Acto 3: Resolución
                    enhanced_text = f"resolution, climax, {prompt.get('text')}"
                
                structured_prompts.append({
                    **prompt,
                    "text": enhanced_text,
                    "act": f"act_{1 + (i >= act1_count) + (i >= act1_count + act2_count)}"
                })
            
            return structured_prompts
        
        return text_prompts
        
    except Exception as e:
        logger.error(f"Error structuring narrative: {str(e)}")
        return text_prompts

def _apply_style_preset(original_prompt: str, style_presets: Dict) -> str:
    """Aplicar preset de estilo al prompt"""
    try:
        preset_name = style_presets.get("preset", "cinematic")
        
        style_modifiers = {
            "cinematic": "cinematic lighting, film grain, shallow depth of field",
            "anime": "anime style, vibrant colors, detailed animation",
            "realistic": "photorealistic, high detail, natural lighting",
            "artistic": "artistic style, creative composition, unique perspective",
            "vintage": "vintage aesthetic, retro colors, film grain",
            "modern": "modern style, clean composition, contemporary"
        }
        
        modifier = style_modifiers.get(preset_name, "")
        
        if modifier:
            return f"{original_prompt}, {modifier}"
        
        return original_prompt
        
    except Exception:
        return original_prompt

async def _setup_video_generation_tracking(generating_videos: List[Dict]) -> Dict:
    """Configurar seguimiento de generación de videos"""
    try:
        task_ids = [video.get("task_id") for video in generating_videos if video.get("task_id")]
        
        return {
            "enabled": True,
            "video_tasks": task_ids,
            "check_interval": 60,  # segundos
            "progress_notifications": True,
            "auto_download": True,
            "quality_check": True,
            "webhook_url": os.getenv("RUNWAY_VIDEO_WEBHOOK")
        }
        
    except Exception as e:
        return {"enabled": False, "error": str(e)}

async def _setup_editing_tracking(processing_edits: List[Dict]) -> Dict:
    """Configurar seguimiento de edición"""
    try:
        task_ids = [edit.get("task_id") for edit in processing_edits if edit.get("task_id")]
        
        return {
            "enabled": True,
            "editing_tasks": task_ids,
            "status_interval": 90,  # segundos
            "progress_reporting": True,
            "quality_validation": True,
            "auto_download": True
        }
        
    except Exception as e:
        return {"enabled": False, "error": str(e)}

async def _configure_multiple_outputs(processing_edits: List[Dict], 
                                    output_formats: List[Dict]) -> Dict:
    """Configurar múltiples formatos de salida"""
    try:
        output_config = {
            "formats": [],
            "total_outputs": len(processing_edits) * len(output_formats),
            "auto_convert": True
        }
        
        for format_config in output_formats:
            format_info = {
                "format": format_config.get("format", "mp4"),
                "resolution": format_config.get("resolution", "1920x1080"),
                "bitrate": format_config.get("bitrate", "5000k"),
                "codec": format_config.get("codec", "h264"),
                "preset": format_config.get("preset", "medium")
            }
            output_config["formats"].append(format_info)
        
        return output_config
        
    except Exception as e:
        return {"error": str(e)}

async def _setup_training_monitoring(training_id: str, training_params: Dict) -> Dict:
    """Configurar monitoreo de entrenamiento"""
    try:
        return {
            "enabled": True,
            "training_id": training_id,
            "check_interval": 300,  # 5 minutos
            "loss_tracking": True,
            "validation_metrics": True,
            "sample_generation": training_params.get("generate_samples", True),
            "early_stopping": training_params.get("early_stopping", False),
            "notification_webhook": os.getenv("RUNWAY_TRAINING_WEBHOOK")
        }
        
    except Exception as e:
        return {"enabled": False, "error": str(e)}

async def _configure_auto_deployment(training_id: str, deployment_config: Dict) -> Dict:
    """Configurar despliegue automático"""
    try:
        return {
            "enabled": True,
            "training_id": training_id,
            "deployment_trigger": deployment_config.get("trigger", "training_complete"),
            "model_name": deployment_config.get("model_name", f"model_{training_id}"),
            "endpoint_config": {
                "instance_type": deployment_config.get("instance_type", "small"),
                "auto_scaling": deployment_config.get("auto_scaling", True),
                "max_instances": deployment_config.get("max_instances", 3)
            },
            "validation_required": deployment_config.get("validation_required", True)
        }
        
    except Exception as e:
        return {"enabled": False, "error": str(e)}

# ============================================================================
# FUNCIÓN DE PERSISTENCIA
# ============================================================================

async def _persist_runway_action(client: AuthenticatedHttpClient, action_data: Dict[str, Any], action: str):
    """Persistir acción de Runway"""
    try:
        from app.memory.memory_functions import save_memory
        
        await save_memory(client, {
            "storage_type": "creative",
            "file_name": f"runway_{action}_{int(time.time())}.json",
            "content": {
                "action": action,
                "action_data": action_data,
                "timestamp": time.time(),
                "platform": "runway_ml"
            },
            "tags": ["runway", "ai_video", "creative", action]
        })
        
    except Exception as e:
        logger.error(f"Error persisting Runway action: {str(e)}")
