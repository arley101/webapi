# app/api/routes/dynamics_actions.py
import logging
import json 
import os # Asegúrate que os esté importado si lo usas para invocation_id
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks, status as http_status_codes
from fastapi.responses import JSONResponse, StreamingResponse, Response 
from azure.identity import DefaultAzureCredential, CredentialUnavailableError
from azure.core.exceptions import ClientAuthenticationError
from typing import Any, Optional, Union 

from app.api.schemas import ActionRequest, ErrorResponse 
from app.core.action_mapper import ACTION_MAP 
from app.core.config import settings 
from app.shared.helpers.http_client import AuthenticatedHttpClient

logger = logging.getLogger(__name__)
router = APIRouter()

def create_error_response(
    status_code: int,
    action: Optional[str] = None,
    message: str = "Error procesando la solicitud.",
    details: Optional[Any] = None,
    graph_error_code: Optional[str] = None 
) -> JSONResponse:
    error_content = ErrorResponse(
        action=action,
        message=message,
        http_status=status_code,
        details=details,
        graph_error_code=graph_error_code 
    ).model_dump(exclude_none=True) 
    return JSONResponse(status_code=status_code, content=error_content)

@router.post(
    "/dynamics", 
    summary="Procesa una acción dinámica basada en la solicitud.",
    description="Recibe un nombre de acción y sus parámetros, y ejecuta la lógica de negocio correspondiente. "
                "Este es el punto de entrada principal para todas las operaciones del backend.",
    response_description="El resultado de la acción ejecutada (JSON, archivo binario, CSV) o un mensaje de error estandarizado.",
    responses={ 
        200: {"description": "Acción completada exitosamente (respuesta JSON o archivo)."},
        202: {"description": "Acción aceptada para procesamiento asíncrono (respuesta JSON)."},
        204: {"description": "Acción completada exitosamente sin contenido que devolver."},
        400: {"description": "Error en la solicitud.", "model": ErrorResponse},
        401: {"description": "No autorizado.", "model": ErrorResponse},
        403: {"description": "Prohibido (Permisos insuficientes).", "model": ErrorResponse},
        422: {"description": "Error de validación de la entidad."}, 
        500: {"description": "Error interno del servidor.", "model": ErrorResponse},
        503: {"description": "Servicio no disponible.", "model": ErrorResponse}
    }
)
async def process_dynamic_action(
    request: Request, 
    action_request: ActionRequest, 
    background_tasks: BackgroundTasks 
):
    action_name = action_request.action
    params_req = action_request.params if action_request.params is not None else {}
    
    invocation_id = request.headers.get("x-ms-invocation-id") or \
                    request.headers.get("x-request-id") or \
                    request.headers.get("traceparent") or \
                    ("local-dev-" + os.urandom(4).hex())
                    
    logging_prefix = f"[InvId: {invocation_id.split('-')[0] if invocation_id else 'N/A'}] [Action: {action_name}]"
    logger.info(f"{logging_prefix} Petición recibida. Claves de params: {list(params_req.keys())}")

    auth_http_client: Optional[AuthenticatedHttpClient] = None
    try:
        credential = DefaultAzureCredential()
        try:
            token_test_scope = settings.GRAPH_API_DEFAULT_SCOPE 
            if not token_test_scope or not token_test_scope[0]: 
                raise ValueError("GRAPH_API_DEFAULT_SCOPE no está configurado correctamente.")
            token_info = credential.get_token(*token_test_scope) 
            logger.debug(f"{logging_prefix} DefaultAzureCredential validada. Token para '{token_test_scope[0]}' expira (UTC): {token_info.expires_on}")
        except CredentialUnavailableError as cred_err:
            logger.error(f"{logging_prefix} Credencial de Azure no disponible: {cred_err}. Esto puede afectar acciones que requieran autenticación Graph/Azure.")
        except ClientAuthenticationError as client_auth_err: 
            logger.error(f"{logging_prefix} Error de autenticación del cliente con Azure: {client_auth_err}. Esto puede afectar acciones que requieran autenticación Graph/Azure.")
        except Exception as token_ex: 
            logger.error(f"{logging_prefix} Error inesperado al obtener token de prueba inicial: {token_ex}", exc_info=False)
            
        auth_http_client = AuthenticatedHttpClient(credential=credential)
        logger.debug(f"{logging_prefix} AuthenticatedHttpClient instanciado.")

    except Exception as auth_setup_ex: 
        logger.warning(f"{logging_prefix} Excepción durante configuración de autenticación (AuthenticatedHttpClient no se pudo crear): {auth_setup_ex}. Las acciones que requieran este cliente fallarán.")
        # auth_http_client permanecerá None. Las acciones deben verificar si el client es None si lo necesitan.

    action_function = ACTION_MAP.get(action_name)
    if not action_function:
        logger.warning(f"{logging_prefix} Acción '{action_name}' no encontrada en ACTION_MAP.")
        return create_error_response(status_code=http_status_codes.HTTP_400_BAD_REQUEST, action=action_name,
            message=f"La acción '{action_name}' no es válida o no está implementada.")

    logger.info(f"{logging_prefix} Ejecutando función '{action_function.__name__}' del módulo '{action_function.__module__}'")
    
    try:
        result = action_function(auth_http_client, params_req)

        if isinstance(result, bytes):
            media_type = "application/octet-stream"; content_disposition = "attachment"
            filename_hint_key = params_req.get("filename_hint_key", "filename") # Para permitir flexibilidad
            filename_from_params = params_req.get(filename_hint_key, params_req.get("nombre_archivo", params_req.get("item_id_or_path", "downloaded_file")))
            safe_filename = "".join(c if c.isalnum() or c in ['.', '-', '_'] else '_' for c in str(filename_from_params))
            if "." not in safe_filename: safe_filename += ".bin" 
            content_disposition = f"attachment; filename=\"{safe_filename}\""
            
            if "photo" in action_name.lower(): media_type = "image/jpeg"; content_disposition = "inline"
            elif safe_filename.endswith(".pdf"): media_type = "application/pdf"
            elif safe_filename.endswith((".xlsx",".xls")): media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            elif safe_filename.endswith((".docx",".doc")): media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            elif safe_filename.endswith(".csv"): media_type = "text/csv"
            elif safe_filename.endswith(".png"): media_type = "image/png"
            logger.info(f"{logging_prefix} Devolviendo datos binarios ({len(result)} bytes) como '{media_type}' con nombre '{safe_filename}'.")
            return Response(content=result, media_type=media_type, headers={"Content-Disposition": content_disposition})

        elif isinstance(result, str) and action_name == "sp_export_list_to_format" and params_req.get("format") == "csv":
            logger.info(f"{logging_prefix} Devolviendo CSV como string ({len(result)} chars).")
            return Response(content=result, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=export.csv"})

        elif isinstance(result, dict):
            if result.get("status") == "error":
                error_status_code = result.get("http_status", http_status_codes.HTTP_500_INTERNAL_SERVER_ERROR)
                if not (400 <= error_status_code < 600): error_status_code = 500
                logger.warning(f"{logging_prefix} Acción devolvió error: {result.get('message')} (Status: {error_status_code})")
                return create_error_response(status_code=error_status_code, action=result.get("action", action_name), 
                    message=result.get("message", "Error desconocido en la acción."), details=result.get("details"),
                    graph_error_code=result.get("graph_error_code") or result.get("api_error_code"))
            else: 
                success_status_code = result.get("http_status", http_status_codes.HTTP_200_OK)
                if not (200 <= success_status_code < 300): success_status_code = 200
                logger.info(f"{logging_prefix} Acción completada exitosamente (Status: {success_status_code}).")
                return JSONResponse(status_code=success_status_code, content=result)
        else: 
            logger.error(f"{logging_prefix} Tipo de resultado inesperado de la acción: {type(result)}. Resultado: {str(result)[:200]}...")
            return create_error_response(status_code=http_status_codes.HTTP_500_INTERNAL_SERVER_ERROR, action=action_name, message="Tipo de resultado inesperado devuelto por la acción.")
            
    except Exception as e: 
        logger.exception(f"{logging_prefix} Excepción no controlada al ejecutar la acción '{action_name}': {e}")
        return create_error_response(status_code=http_status_codes.HTTP_500_INTERNAL_SERVER_ERROR, action=action_name,
            message="Error interno del servidor al procesar la acción.", details=f"{type(e).__name__}: {str(e)}")

# --- FIN DEL MÓDULO api/routes/dynamics_actions.py ---