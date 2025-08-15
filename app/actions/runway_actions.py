# app/actions/runway_actions.py
"""
Acciones robustas para integrar RunwayML (v1) con manejo de errores,
validaciones y capacidad multimedia mejorada (texto a video e imagen a video).

Modo de ejecución:
- SIM (por defecto): no requiere credenciales y usa una cola en memoria.
- REAL: establecer `RUNWAY_MODE=real` y `RUNWAY_API_KEY`. Opcionalmente configurar:
  `RUNWAY_ENDPOINT_GENERATE`, `RUNWAY_ENDPOINT_STATUS`, `RUNWAY_ENDPOINT_CANCEL`.
Esto permite cambiar de simulación a real **sin volver a editar el código**; solo con variables de entorno y reinicio.

Endpoints oficiales (según documentación de Runway API v1):
- POST /v1/image_to_video
- POST /v1/video_to_video
- GET  /v1/tasks/{id}
- DELETE /v1/tasks/{id}
Requiere cabecera: X-Runway-Version (ej.: 2024-11-06).
"""

import logging
import time
import uuid
import os
import base64
import requests
from typing import Dict, Any, Optional, List

from app.core.config import settings

# === Config por variables de entorno (permite usar "real" sin volver a editar código) ===
RUNWAY_MODE = os.getenv("RUNWAY_MODE", "sim").lower().strip()  # valores: "sim" (default) | "real"
BASE_URL = "https://api.runwayml.com/v1"
# Endpoints oficiales (Runway API v1)
ENDPOINT_IMAGE_TO_VIDEO = os.getenv("RUNWAY_ENDPOINT_IMAGE_TO_VIDEO") or f"{BASE_URL}/image_to_video"
ENDPOINT_VIDEO_TO_VIDEO = os.getenv("RUNWAY_ENDPOINT_VIDEO_TO_VIDEO") or f"{BASE_URL}/video_to_video"
ENDPOINT_TEXT_TO_IMAGE = os.getenv("RUNWAY_ENDPOINT_TEXT_TO_IMAGE")  # opcional: p. ej. f"{BASE_URL}/text_to_image"
ENDPOINT_TASK_DETAIL   = os.getenv("RUNWAY_ENDPOINT_TASK_DETAIL")   or f"{BASE_URL}/tasks/{{task_id}}"
ENDPOINT_TASK_CANCEL   = os.getenv("RUNWAY_ENDPOINT_TASK_CANCEL")   or f"{BASE_URL}/tasks/{{task_id}}"
REQUEST_TIMEOUT = int(os.getenv("RUNWAY_TIMEOUT_SECONDS", "60"))
RUNWAY_API_VERSION = os.getenv("RUNWAY_API_VERSION", "2024-11-06")

logger = logging.getLogger(__name__)

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
    api_key = getattr(settings, "RUNWAY_API_KEY", None) or os.getenv("RUNWAY_API_KEY")
    if api_key:
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Runway-Version": RUNWAY_API_VERSION,
        }
    return None

def _build_image_to_video_payload(params: Dict[str, Any]) -> Dict[str, Any]:
    """Payload oficial para POST /v1/image_to_video."""
    payload: Dict[str, Any] = {}
    # Fuente: imagen (URL) o base64
    prompt_image = params.get("promptImage") or params.get("image_url") or params.get("imageUri")
    image_b64 = params.get("promptImageBase64") or params.get("image_base64_data")
    if image_b64 and not prompt_image:
        payload["promptImageBase64"] = image_b64
    elif prompt_image:
        payload["promptImage"] = str(prompt_image)
    # Prompt de texto (opcional)
    if params.get("promptText") or params.get("text_prompt"):
        payload["promptText"] = params.get("promptText") or params.get("text_prompt")
    # Parámetros opcionales comunes
    if params.get("seed") is not None:
        payload["seed"] = int(params["seed"])
    if params.get("model"):
        payload["model"] = str(params["model"])  # ej.: gen3a_turbo, gen4_aleph
    if params.get("duration") or params.get("duration_seconds"):
        payload["duration"] = float(params.get("duration") or params.get("duration_seconds"))
    if params.get("ratio"):
        payload["ratio"] = str(params["ratio"])  # ej.: 1280:720
    if isinstance(params.get("contentModeration"), dict):
        payload["contentModeration"] = params["contentModeration"]
    # Validación mínima
    if not (payload.get("promptImage") or payload.get("promptImageBase64")):
        raise ValueError("Se requiere 'promptImage' (URL) o 'promptImageBase64' para image_to_video.")
    return payload

def _build_video_to_video_payload(params: Dict[str, Any]) -> Dict[str, Any]:
    """Payload oficial para POST /v1/video_to_video."""
    payload: Dict[str, Any] = {}
    video_uri = params.get("videoUri") or params.get("video_url")
    if not video_uri:
        raise ValueError("'videoUri' es obligatorio para video_to_video")
    payload["videoUri"] = video_uri
    if params.get("promptText") or params.get("text_prompt"):
        payload["promptText"] = params.get("promptText") or params.get("text_prompt")
    if params.get("seed") is not None:
        payload["seed"] = int(params["seed"])
    if params.get("model"):
        payload["model"] = str(params["model"])  # ej.: gen4_aleph
    if params.get("ratio"):
        payload["ratio"] = str(params["ratio"])  # ej.: 1280:720
    if isinstance(params.get("references"), list):
        payload["references"] = params["references"]
    if isinstance(params.get("contentModeration"), dict):
        payload["contentModeration"] = params["contentModeration"]
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
    Inicia una tarea en Runway **oficial**:
    - Si trae `videoUri|video_url` => POST /v1/video_to_video
    - En caso contrario => POST /v1/image_to_video
    """
    try:
        use_v2v = bool(params.get("videoUri") or params.get("video_url"))
        payload = _build_video_to_video_payload(params) if use_v2v else _build_image_to_video_payload(params)
    except Exception as e:
        logger.error(f"Validación de parámetros: {e}")
        return {"status": "error", "message": str(e)}

    headers = _get_headers()
    if headers and RUNWAY_MODE == "real":
        try:
            url = ENDPOINT_VIDEO_TO_VIDEO if use_v2v else ENDPOINT_IMAGE_TO_VIDEO
            response = requests.post(url, headers=headers, json=payload, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json() if response.content else {}
            task_id = (data.get("id") or data.get("taskId") or str(uuid.uuid4()))
            return {"status": "pending", "message": "Tarea creada en Runway (REAL)", "task_id": task_id, "mode": "real", "raw": data}
        except Exception as e:
            logger.warning("Fallo al iniciar generación REAL en Runway: %s", e)
            # fallback a simulación si falla la real

    # SIMULACIÓN
    task_id = _simulate_enqueue(payload)
    return {"status": "pending", "message": "La generación del video ha comenzado (SIM).", "task_id": task_id, "mode": "simulation"}

def runway_get_video_status(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Consulta el estado de una tarea de generación de Runway.
    """
    task_id = (params.get("task_id") or "").strip()
    if not task_id:
        return {"status": "error", "message": "El parámetro 'task_id' es requerido."}

    headers = _get_headers()
    if headers and RUNWAY_MODE == "real":
        try:
            url = ENDPOINT_TASK_DETAIL.replace("{task_id}", task_id)
            response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json() if response.content else {}
            status = (data.get("status") or data.get("state") or data.get("taskStatus") or "processing").lower()
            video_url = None
            if isinstance(data.get("output"), list) and data["output"]:
                video_url = data["output"][0]
            elif isinstance(data.get("assets"), list) and data["assets"] and isinstance(data["assets"][0], dict):
                video_url = data["assets"][0].get("url")
            out = {"status": status, "task_id": task_id, "raw": data}
            if status in {"succeeded","completed","success"} and video_url:
                out.update({"status": "success", "video_url": video_url})
            elif status in {"failed","error"}:
                out.update({"status": "error", "message": data.get("failureCode") or data.get("message") or "Fallo en Runway"})
            return out
        except Exception as e:
            logger.warning("Fallo al consultar estado REAL en Runway: %s", e)
            # fallback a simulación

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
    if headers and RUNWAY_MODE == "real":
        try:
            url = ENDPOINT_TASK_CANCEL.replace("{task_id}", task_id)
            response = requests.delete(url, headers=headers, timeout=REQUEST_TIMEOUT)
            if response.status_code == 204:
                return {"status": "success", "message": "Tarea cancelada/eliminada (REAL)", "task_id": task_id}
            data = response.json() if response.content else {}
            return {"status": data.get("status") or "success", "message": data.get("message") or "Cancelación solicitada (REAL)", "task_id": task_id, "raw": data}
        except Exception as e:
            logger.warning("Fallo al cancelar tarea REAL en Runway: %s", e)
            # fallback a simulación

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
        duration = float(
            params.get("duration") or params.get("duration_seconds") or 5.0
        )
        ratio = (params.get("ratio") or "1280:720")
        try:
            w, h = [int(x) for x in ratio.split(":")] if ":" in ratio else (1280, 720)
        except Exception:
            w, h = 1280, 720
        pixels = w * h
        base = 0.000002 * pixels * duration
        model = (params.get("model") or "gen3a_turbo").lower()
        model_factor = 1.0 if "gen3" in model else 1.2
        estimate_usd = round(base * model_factor, 4)
        return {"status": "success", "currency": "USD", "estimated_cost": estimate_usd}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ==========================
# Acciones ampliadas (alto nivel)
# ==========================

def runway_generate_image(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Genera imagen desde texto (si tu cuenta soporta el endpoint de texto→imagen).
    Requiere configurar la variable de entorno RUNWAY_ENDPOINT_TEXT_TO_IMAGE.
    Params esperados (comunes): promptText, seed, model, ratio.
    """
    if not ENDPOINT_TEXT_TO_IMAGE:
        return {"status": "error", "message": "RUNWAY_ENDPOINT_TEXT_TO_IMAGE no configurado en el entorno."}
    headers = _get_headers()
    if not headers:
        return {"status": "error", "message": "RUNWAY_API_KEY no configurada."}
    payload: Dict[str, Any] = {}
    if params.get("promptText") or params.get("text_prompt"):
        payload["promptText"] = params.get("promptText") or params.get("text_prompt")
    else:
        return {"status": "error", "message": "'promptText' es obligatorio."}
    if params.get("seed") is not None:
        payload["seed"] = int(params["seed"])
    if params.get("model"):
        payload["model"] = str(params["model"])  # si aplica
    if params.get("ratio"):
        payload["ratio"] = str(params["ratio"])  # ej.: 1024:1024
    try:
        response = requests.post(ENDPOINT_TEXT_TO_IMAGE, headers=headers, json=payload, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json() if response.content else {}
        # Convención: devolveremos una URL si viene en output/assets
        image_url = None
        if isinstance(data.get("output"), list) and data["output"]:
            image_url = data["output"][0]
        elif isinstance(data.get("assets"), list) and data["assets"] and isinstance(data["assets"][0], dict):
            image_url = data["assets"][0].get("url")
        out = {"status": "success", "raw": data}
        if image_url:
            out["image_url"] = image_url
        return out
    except Exception as e:
        return {"status": "error", "message": str(e)}

def runway_generate_video_from_text(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Alias de conveniencia: genera video desde texto usando la ruta de image_to_video
    con una imagen base obligatoria. Si no se provee `promptImage`, devuelve error
    explícito para evitar ambigüedad. (Runway v1 no publica un texto→video universal).
    """
    if not (params.get("promptImage") or params.get("image_url") or params.get("imageUri")):
        return {"status": "error", "message": "Se requiere 'promptImage' (URL) para generar video desde texto."}
    # Reutiliza la implementación oficial
    return runway_generate_video(client, params)

def runway_generate_video_from_multiple_images(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Secuencia de imágenes a video (alto nivel). Usa image_to_video con la primera
    imagen como base y pasa imágenes adicionales como 'references' si están disponibles.
    """
    images: List[str] = params.get("images") or []
    if not images or not isinstance(images, list):
        return {"status": "error", "message": "'images' (lista de URLs) es obligatorio."}
    p = dict(params)
    p["promptImage"] = images[0]
    # Algunas cuentas/planes admiten 'references'; si no, la API las ignora
    p["references"] = [{"type": "image", "uri": u} for u in images[1:]] if len(images) > 1 else []
    return runway_generate_video(client, p)

def runway_batch_generate(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Lanza múltiples tareas (batch). 'items' es una lista de payloads individuales
    compatibles con image_to_video o video_to_video.
    """
    items: List[Dict[str, Any]] = params.get("items") or []
    if not items or not isinstance(items, list):
        return {"status": "error", "message": "'items' (lista de objetos params) es obligatorio."}
    results = []
    for i, it in enumerate(items, 1):
        res = runway_generate_video(client, it)
        results.append({"index": i, "result": res})
    return {"status": "success", "batch": results}

def runway_get_task_history(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Devuelve historial simple de tareas vistas por este proceso (SIM y/o REAL si se registró).
    Puedes limitar con 'limit' (default 20).
    """
    limit = int(params.get("limit", 20))
    # Para SIM tenemos _TASK_STORE; para REAL podrías tener un storage persistente
    # Aquí devolvemos lo que tengamos en memoria para no romper contrato.
    items = []
    for tid, data in list(_TASK_STORE.items())[-limit:]:
        items.append({
            "task_id": tid,
            "status": data.get("status"),
            "created_at": data.get("created_at"),
            "updated_at": data.get("updated_at"),
            "has_result": bool(data.get("result_url"))
        })
    return {"status": "success", "items": items}

def runway_wait_and_save(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Crea o continúa una tarea y espera hasta que termine (con backoff). Si 'persist'=true
    y se obtiene 'video_url', devuelve una estructura de persistencia sugerida para que
    el servicio de almacenamiento la ejecute (SharePoint/OneDrive) a nivel superior.

    Params:
      - task_id (opcional): si viene, solo espera ese id. Si no, crea con el resto de params.
      - timeout_seconds (opcional, default 300)
      - poll_interval (opcional, default 3)
      - persist (bool, default false)
      - storage_type, file_name, tags (si persist=true)
    """
    timeout = int(params.get("timeout_seconds", 300))
    interval = max(1, int(params.get("poll_interval", 3)))
    persist = bool(params.get("persist", False))

    # Crear o reutilizar tarea
    task_id = (params.get("task_id") or "").strip()
    if not task_id:
        create_res = runway_generate_video(client, params)
        if create_res.get("status") == "error":
            return create_res
        task_id = create_res.get("task_id")
        if not task_id:
            return {"status": "error", "message": "No se obtuvo task_id al crear la tarea."}

    # Polling con backoff lineal simple
    start = _now_ts()
    last = None
    while _now_ts() - start < timeout:
        last = runway_get_video_status(client, {"task_id": task_id})
        st = (last.get("status") or "").lower()
        if st in {"success", "error"}:
            break
        time.sleep(interval)

    if not last:
        return {"status": "error", "message": "No se pudo obtener estado de la tarea."}

    if last.get("status") != "success":
        return last  # error o sigue procesando

    # Si se solicita persistir, devolvemos instrucción de persistencia de alto nivel
    if persist and last.get("video_url"):
        persist_payload = {
            "action": "save_memory",
            "params": {
                "storage_type": params.get("storage_type") or "document",
                "file_name": params.get("file_name") or f"runway_{task_id}.mp4",
                "content": {"video_url": last["video_url"], "task_id": task_id, "source": "runway"},
                "tags": params.get("tags") or ["runway", "video"],
            }
        }
        return {"status": "success", "task_id": task_id, "video_url": last["video_url"], "persist_suggestion": persist_payload}

    return {"status": "success", "task_id": task_id, "video_url": last.get("video_url")}
