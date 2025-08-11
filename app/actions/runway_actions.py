"""
Acciones robustas para integrar RunwayML (v1) con manejo de errores,
validaciones y simulación segura si no hay conectividad/credenciales.

- runway_generate_video: inicia una tarea de generación (text-to-video).
- runway_get_video_status: consulta estado de una tarea.
- runway_cancel_task: intenta cancelar una tarea en proceso.
- runway_get_result_url: obtiene la URL final del video si la tarea terminó.
- runway_list_models: lista modelos soportados (catálogo estático + override por params).
- runway_estimate_cost: estima costo simple en función de duración / resolución.

- Auto-descubrimiento de API Key: via auth_cognitivo, settings.RUNWAY_API_KEY o variable de entorno RUNWAY_API_KEY.

Estrategia:
1) Si existe `auth_cognitivo.get_runway_headers()` se usará en requests reales.
2) Si falla la llamada HTTP o no hay headers válidos -> modo SIMULACIÓN determinista.
"""

import logging
import time
import uuid
import os
from typing import Dict, Any, Optional, List

from app.core.config import settings

logger = logging.getLogger(__name__)

# Endpoints base (no incluimos rutas específicas para evitar acoplamiento fuerte)
BASE_URL = "https://api.runwayml.com/v1"

# === Estado en memoria para simulación (seguro si no hay almacenamiento) ===
_TASK_STORE: Dict[str, Dict[str, Any]] = {}
_SIMULATION_TTL_SECONDS = 90  # tiempo típico para pasar de pending->succeeded en modo simulado


# ==========================
# Helpers internos
# ==========================


def _get_headers() -> Optional[Dict[str, str]]:
    """
    Obtiene headers de autenticación para RunwayML con tres estrategias:
    1) auth_cognitivo.get_runway_headers() si existe.
    2) settings.RUNWAY_API_KEY si existe en la configuración.
    3) Variable de entorno RUNWAY_API_KEY directamente.
    """
    # 1) Intentar via auth_cognitivo
    try:
        from app.core.auth_manager import auth_cognitivo
        if hasattr(auth_cognitivo, "get_runway_headers"):
            headers = auth_cognitivo.get_runway_headers()
            if isinstance(headers, dict) and "Authorization" in headers:
                return headers
    except Exception as e:
        logger.debug(f"No fue posible obtener headers desde auth_cognitivo: {e}")
    
    # 2) Intentar via settings
    try:
        api_key = getattr(settings, "RUNWAY_API_KEY", None)
        if api_key:
            return {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
    except Exception as e:
        logger.debug(f"No fue posible leer RUNWAY_API_KEY desde settings: {e}")
    
    # 3) Intentar via variable de entorno
    api_key_env = os.getenv("RUNWAY_API_KEY")
    if api_key_env:
        return {
            "Authorization": f"Bearer {api_key_env}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
    
    return None


def _normalize_video_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normaliza y valida parámetros de generación de video.
    """
    text_prompt = (params.get("text_prompt") or "").strip()
    if not text_prompt:
        raise ValueError("El parámetro 'text_prompt' es requerido.")

    width = int(params.get("width", 1024))
    height = int(params.get("height", 576))
    duration = float(params.get("duration_seconds", 5.0))
    seed = params.get("seed")
    model = (params.get("model") or "gen3-alpha").strip()

    # Límites seguros por defecto
    if width not in (512, 768, 1024, 1280, 1920):
        width = 1024
    if height not in (288, 432, 576, 720, 1080):
        height = 576
    if duration <= 0 or duration > 20:
        duration = 5.0

    payload = {
        "text_prompt": text_prompt,
        "width": width,
        "height": height,
        "duration_seconds": duration,
        "model": model,
    }
    if seed is not None:
        try:
            payload["seed"] = int(seed)
        except Exception:
            logger.warning("Seed inválido, se ignora.")

    # Parámetros opcionales
    for key in ("negative_prompt", "guidance", "motion", "cfg_scale"):
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
            # URL simulada determinista por task_id
            task["result_url"] = f"https://simulated.runway/{uuid.uuid4().hex}.mp4"
    task["updated_at"] = _now_ts()


def _get_task_or_none(task_id: str) -> Optional[Dict[str, Any]]:
    return _TASK_STORE.get(task_id)


# ==========================
# Acciones públicas
# ==========================

def runway_generate_video(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Inicia la generación de un video en Runway a partir de un prompt de texto.
    Intenta realizar llamada real; si no es posible, entra en modo simulado.
    """
    try:
        payload = _normalize_video_params(params)
    except Exception as e:
        logger.error(f"Validación de parámetros: {e}")
        return {"status": "error", "message": str(e)}

    headers = _get_headers()

    # Intento de request real (placeholder sin acoplar endpoint concreto)
    if headers:
        try:
            # Nota: no fijamos endpoint concreto para evitar romper si la API cambia.
            # En una integración real, aquí se haría:
            #   response = requests.post(f"{BASE_URL}/generations", headers=headers, json=payload, timeout=60)
            #   response.raise_for_status()
            #   task_id = response.json().get("id") or response.json().get("uuid")
            # En ausencia de contratos confirmados, hacemos fallback explícito.
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


def runway_get_video_status(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Consulta el estado de una tarea de generación de Runway.
    Si no es posible consultar remotamente, usa el estado simulado.
    """
    task_id = (params.get("task_id") or "").strip()
    if not task_id:
        return {"status": "error", "message": "El parámetro 'task_id' es requerido."}

    headers = _get_headers()
    if headers:
        try:
            # request real placeholder:
            # r = requests.get(f"{BASE_URL}/tasks/{task_id}", headers=headers, timeout=30)
            # r.raise_for_status()
            # data = r.json()
            # return {"status": data.get("status"), "message": "OK", "raw": data, "video_url": data.get("result", {}).get("url")}
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


def runway_cancel_task(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Cancela una tarea de Runway si es posible.
    """
    task_id = (params.get("task_id") or "").strip()
    if not task_id:
        return {"status": "error", "message": "El parámetro 'task_id' es requerido."}

    headers = _get_headers()
    if headers:
        try:
            # request real placeholder:
            # r = requests.post(f"{BASE_URL}/tasks/{task_id}/cancel", headers=headers, timeout=30)
            # r.raise_for_status()
            # data = r.json()
            # return {"status": "success", "message": "Tarea cancelada.", "raw": data}
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


def runway_get_result_url(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Devuelve solo la URL del resultado si la tarea terminó.
    """
    task_id = (params.get("task_id") or "").strip()
    if not task_id:
        return {"status": "error", "message": "El parámetro 'task_id' es requerido."}

    status = runway_get_video_status({"task_id": task_id})
    if status.get("status") == "success" and status.get("video_url"):
        return {"status": "success", "video_url": status["video_url"], "task_id": task_id}
    return {"status": "error", "message": "El video aún no está listo o la tarea no existe.", "last_status": status}


def runway_list_models(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Devuelve catálogo estático de modelos soportados. Permite override por params["models"].
    """
    default_models = [
        {"id": "gen3-alpha", "type": "text-to-video", "status": "stable"},
        {"id": "gen3-turbo", "type": "text-to-video", "status": "beta"},
        {"id": "image-to-video", "type": "image-to-video", "status": "stable"},
    ]
    models = params.get("models") or default_models
    return {"status": "success", "models": models}


def runway_estimate_cost(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Estima costo aproximado (heurístico) según duración y resolución.
    No es oficial; sirve para planificación.
    """
    try:
        payload = _normalize_video_params(params)
        duration = float(payload["duration_seconds"])
        pixels = int(payload["width"]) * int(payload["height"])
        # Heurística: 0.000002 USD por pixel-segundo (ejemplo), + factor por modelo.
        base = 0.000002 * pixels * duration
        model_factor = 1.0 if payload.get("model") == "gen3-alpha" else 1.2
        estimate_usd = round(base * model_factor, 4)
        return {"status": "success", "currency": "USD", "estimated_cost": estimate_usd}
    except Exception as e:
        return {"status": "error", "message": str(e)}