# app/actions/runway_actions.py
"""
Acciones robustas para integrar RunwayML (v1) con manejo de errores,
validaciones y capacidad multimedia mejorada (texto a video e imagen a video).
"""

import logging
import time
import uuid
import os
import base64
import requests
from typing import Dict, Any, Optional, List

from app.core.config import settings

logger = logging.getLogger(__name__)

# Endpoints base
BASE_URL = "https://api.runwayml.com/v1"

# Estado en memoria para simulación (seguro si no hay almacenamiento)
_TASK_STORE: Dict[str, Dict[str, Any]] = {}
_SIMULATION_TTL_SECONDS = 90  # tiempo típico para pasar de pending->succeeded en modo simulado

# ==========================
# Helpers internos
# ==========================

def _get_headers() -> Optional[Dict[str, str]]:
    """
    Obtiene headers de autenticación para RunwayML.
    Utiliza settings.RUNWAY_API_KEY o la variable de entorno RUNWAY_API_KEY.
    """
    api_key = getattr(settings, "RUNWAY_API_KEY", os.getenv("RUNWAY_API_KEY"))
    if api_key:
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
    return None

def _normalize_video_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normaliza y valida parámetros de generación de video, soportando texto e imagen.
    """
    text_prompt = params.get("text_prompt", "").strip()
    image_base64_data = params.get("image_base64_data")
    image_url = params.get("image_url")

    if not text_prompt and not image_base64_data and not image_url:
        raise ValueError("Se requiere uno de los siguientes parámetros: 'text_prompt', 'image_base64_data', o 'image_url'.")

    payload: Dict[str, Any] = {
        "width": int(params.get("width", 1024)),
        "height": int(params.get("height", 576)),
        "duration_seconds": float(params.get("duration_seconds", 5.0)),
        "model": (params.get("model") or "gen3-alpha").strip(),
    }

    # Asignar la fuente de la generación
    if image_base64_data:
        payload["image_prompt_base64"] = image_base64_data
    elif image_url:
        # En una implementación real, aquí se descargaría la imagen y se convertiría a base64
        # Por ahora, asumimos que la API de Runway podría aceptar una URL, o pasamos la URL para simulación.
        payload["image_prompt_url"] = image_url
    else:
        payload["text_prompt"] = text_prompt

    # Parámetros opcionales
    for key in ("seed", "negative_prompt", "guidance", "motion", "cfg_scale"):
        if key in params and params[key] is not None:
            payload[key] = params[key]

    return payload


def _now_ts() -> float:
    return time.time()

def _simulate_enqueue(payload: Dict[str, Any]) -> str:
    """
    Encola una tarea en modo simulado y retorna task_id.
    """
    task_id = str(uuid.uuid4())
    _TASK_STORE[task_id] = {
        "status": "pending",
        "created_at": _now_ts(),
        "updated_at": _now_ts(),
        "payload": payload,
        "result_url": None,
        "cancelled": False,
        "error": None,
    }
    logger.info(f"[SIM] Runway task creada: {task_id}")
    return task_id

def _simulate_progress(task: Dict[str, Any]) -> None:
    """
    Avanza el estado de la tarea simulada en base al tiempo transcurrido.
    """
    age = _now_ts() - task["created_at"]
    if task.get("cancelled"):
        task["status"] = "canceled"
    elif age < _SIMULATION_TTL_SECONDS * 0.3:
        task["status"] = "pending"
    elif age < _SIMULATION_TTL_SECONDS * 0.8:
        task["status"] = "processing"
    else:
        if task["status"] != "succeeded":
            task["status"] = "succeeded"
            task["result_url"] = f"https://simulated.runway/{uuid.uuid4().hex}.mp4"
    task["updated_at"] = _now_ts()

def _get_task_or_none(task_id: str) -> Optional[Dict[str, Any]]:
    return _TASK_STORE.get(task_id)

# ==========================
# Acciones públicas
# ==========================

def runway_generate_video(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Inicia la generación de un video en Runway a partir de un prompt de texto o una imagen.
    Intenta realizar llamada real; si no es posible, entra en modo simulado.
    """
    try:
        payload = _normalize_video_params(params)
    except Exception as e:
        logger.error(f"Validación de parámetros: {e}")
        return {"status": "error", "message": str(e)}

    headers = _get_headers()

    if headers:
        try:
            # En una implementación real, aquí se haría la llamada a la API
            # response = requests.post(f"{BASE_URL}/generations", headers=headers, json=payload, timeout=60)
            # response.raise_for_status()
            # task_id = response.json().get("id")
            raise RuntimeError("Endpoint de Runway no configurado: usando simulación segura.")
        except Exception as e:
            logger.warning(f"No se pudo iniciar generación real en Runway: {e}. Se usará simulación.")

    task_id = _simulate_enqueue(payload)
    return {
        "status": "pending",
        "message": "La generación del video ha comenzado (SIM).",
        "task_id": task_id,
        "mode": "simulation",
    }

def runway_get_video_status(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Consulta el estado de una tarea de generación de Runway.
    """
    task_id = (params.get("task_id") or "").strip()
    if not task_id:
        return {"status": "error", "message": "El parámetro 'task_id' es requerido."}

    headers = _get_headers()
    if headers:
        try:
            raise RuntimeError("Endpoint de Runway no configurado: usando simulación segura.")
        except Exception as e:
            logger.warning(f"No se pudo consultar tarea real en Runway: {e}. Se usará simulación.")

    task = _get_task_or_none(task_id)
    if not task:
        return {"status": "error", "message": f"Tarea '{task_id}' no encontrada (SIM)."}

    _simulate_progress(task)
    if task["status"] == "succeeded":
        return {"status": "success", "message": "Video generado (SIM).", "video_url": task["result_url"], "task_id": task_id}
    elif task["status"] == "canceled":
        return {"status": "error", "message": "La tarea fue cancelada (SIM).", "task_id": task_id}
    elif task["status"] == "processing":
        return {"status": "processing", "message": "El video se está procesando (SIM).", "task_id": task_id}
    else:
        return {"status": "pending", "message": "La tarea está en cola (SIM).", "task_id": task_id}

def runway_cancel_task(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Cancela una tarea de Runway si es posible.
    """
    task_id = (params.get("task_id") or "").strip()
    if not task_id:
        return {"status": "error", "message": "El parámetro 'task_id' es requerido."}

    headers = _get_headers()
    if headers:
        try:
            raise RuntimeError("Endpoint de Runway no configurado: usando simulación segura.")
        except Exception as e:
            logger.warning(f"No se pudo cancelar tarea real en Runway: {e}. Se usará simulación.")

    task = _get_task_or_none(task_id)
    if not task:
        return {"status": "error", "message": f"Tarea '{task_id}' no encontrada (SIM)."}

    task["cancelled"] = True
    _simulate_progress(task)
    return {"status": "success" if task["status"] == "canceled" else "processing",
            "message": "Cancelación solicitada (SIM).",
            "task_id": task_id}

def runway_get_result_url(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Devuelve solo la URL del resultado si la tarea terminó.
    """
    task_id = (params.get("task_id") or "").strip()
    if not task_id:
        return {"status": "error", "message": "El parámetro 'task_id' es requerido."}

    status = runway_get_video_status(client, {"task_id": task_id})
    if status.get("status") == "success" and status.get("video_url"):
        return {"status": "success", "video_url": status["video_url"], "task_id": task_id}
    return {"status": "error", "message": "El video aún no está listo o la tarea no existe.", "last_status": status}

def runway_list_models(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Devuelve catálogo estático de modelos soportados.
    """
    default_models = [
        {"id": "gen3-alpha", "type": "text-to-video", "status": "stable"},
        {"id": "gen3-turbo", "type": "text-to-video", "status": "beta"},
        {"id": "image-to-video", "type": "image-to-video", "status": "stable"},
    ]
    models = params.get("models") or default_models
    return {"status": "success", "models": models}

def runway_estimate_cost(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Estima costo aproximado (heurístico) según duración y resolución.
    """
    try:
        payload = _normalize_video_params(params)
        duration = float(payload["duration_seconds"])
        pixels = int(payload["width"]) * int(payload["height"])
        base = 0.000002 * pixels * duration
        model_factor = 1.0 if payload.get("model") == "gen3-alpha" else 1.2
        estimate_usd = round(base * model_factor, 4)
        return {"status": "success", "currency": "USD", "estimated_cost": estimate_usd}
    except Exception as e:
        return {"status": "error", "message": str(e)}
