# app/api/routes/dynamics_actions.py
import logging
import json 
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks, status as http_status_codes
from fastapi.responses import JSONResponse, StreamingResponse, Response 
from azure.identity import DefaultAzureCredential, CredentialUnavailableError
from azure.core.exceptions import ClientAuthenticationError
from typing import Any, Optional, Union 

from app.api.schemas import ActionRequest, ErrorResponse 
from app.core.action_mapper import ACTION_MAP 
from app.core.config import settings 
from app.shared.helpers.http_client import AuthenticatedHttpClient
from app.core.orchestrator import orchestrator, execute_plan_as_workflow
from app.core.state_manager import state_manager
from app.core.event_bus import event_bus, EventType

logger = logging.getLogger(__name__)
router = APIRouter()

# Helper para crear la respuesta de error estandarizada
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
                "Este es el punto de entrada principal para todas las operaciones del backend. "
                "Soporta mode=execution para ejecución automática sin confirmación.",
    response_description="El resultado de la acción ejecutada (JSON, archivo binario, CSV) o un mensaje de error estandarizado.",
    responses={ 
        200: {"description": "Acción completada exitosamente (respuesta JSON o archivo)."},
        202: {"description": "Acción aceptada para procesamiento asíncrono (respuesta JSON)."},
        204: {"description": "Acción completada exitosamente sin contenido que devolver."},
        400: {"description": "Error en la solicitud (ej. acción desconocida, parámetros inválidos).", "model": ErrorResponse},
        401: {"description": "No autorizado (problema de credenciales de la API).", "model": ErrorResponse},
        422: {"description": "Error de validación de la entidad (cuerpo de solicitud malformado)."}, 
        500: {"description": "Error interno del servidor.", "model": ErrorResponse},
        503: {"description": "Servicio no disponible (ej. dependencia externa caída).", "model": ErrorResponse}
    }
)
async def process_dynamic_action(
    request: Request, 
    action_request: ActionRequest, 
    background_tasks: BackgroundTasks 
):
    action_name = action_request.action
    params_req = action_request.params 
    
    # Phase 2: Task 2.2 - Extract execution mode
    mode = action_request.mode or "suggestion"
    execution_mode = action_request.execution
    if execution_mode is None:
        execution_mode = (mode == "execution") or settings.EXECUTION_MODE_DEFAULT
    
    # Extract session and workflow IDs for orchestration
    session_id = action_request.session_id
    workflow_id = action_request.workflow_id
    
    invocation_id = request.headers.get("x-ms-invocation-id") or \
                    request.headers.get("x-request-id") or \
                    request.headers.get("traceparent") or \
                    "local-dev" 
                    
    logging_prefix = f"[InvId: {invocation_id.split('-')[0] if invocation_id else 'N/A'}] [Action: {action_name}] [Mode: {mode}]"

    logger.info(f"{logging_prefix} Petición recibida. Execution mode: {execution_mode}. Claves de parámetros: {list(params_req.keys())}")

    # Store request context in state manager if session_id provided
    if session_id:
        await state_manager.set_conversation_context(session_id, {
            "last_action": action_name,
            "last_params": params_req,
            "execution_mode": execution_mode,
            "invocation_id": invocation_id
        })

    try:
        credential = DefaultAzureCredential()
        try:
            token_test_scope = settings.GRAPH_API_DEFAULT_SCOPE 
            if not token_test_scope or not token_test_scope[0]: 
                raise ValueError("GRAPH_API_DEFAULT_SCOPE no está configurado correctamente en settings.")
            
            token_info = credential.get_token(*token_test_scope) 
            logger.debug(f"{logging_prefix} DefaultAzureCredential validada exitosamente. Token para '{token_test_scope[0]}' expira en (UTC): {token_info.expires_on}")
        except CredentialUnavailableError as cred_err:
            logger.error(f"{logging_prefix} Credencial de Azure no disponible (Managed Identity o variables de entorno podrían estar mal configuradas): {cred_err}")
            return create_error_response(
                status_code=http_status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
                action=action_name,
                message="Error de autenticación del servidor: Credencial de Azure no disponible.",
                details=f"CredentialUnavailableError: {str(cred_err)}"
            )
        except ClientAuthenticationError as client_auth_err: 
            logger.error(f"{logging_prefix} Error de autenticación del cliente con Azure (problema con Service Principal o identidad): {client_auth_err}")
            return create_error_response(
                status_code=http_status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
                action=action_name,
                message="Error de autenticación del servidor: Fallo al autenticar el cliente de Azure.",
                details=f"ClientAuthenticationError: {str(client_auth_err)}"
            )
        except Exception as token_ex: 
            logger.error(f"{logging_prefix} Error inesperado al obtener token de prueba inicial: {token_ex}", exc_info=True)
            return create_error_response(
                status_code=http_status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
                action=action_name,
                message="Error de autenticación del servidor: Fallo inesperado al obtener token de prueba.",
                details=str(token_ex)
            )
            
        auth_http_client = AuthenticatedHttpClient(credential=credential)
        logger.debug(f"{logging_prefix} AuthenticatedHttpClient inicializado y listo.")

    except Exception as auth_setup_ex: 
        logger.exception(f"{logging_prefix} Excepción crítica durante la configuración de autenticación: {auth_setup_ex}")
        return create_error_response(
            status_code=http_status_codes.HTTP_503_SERVICE_UNAVAILABLE, 
            action=action_name,
            message="Error interno crítico: Fallo en la configuración de autenticación del servidor.",
            details=str(auth_setup_ex)
        )

    # Check if this is a workflow action or single action
    if action_name == "execute_workflow" and "workflow" in params_req:
        # Execute workflow through orchestrator
        logger.info(f"{logging_prefix} Executing workflow through orchestrator")
        try:
            workflow_plan = params_req["workflow"]
            workflow_name = params_req.get("workflow_name", "API Generated Workflow")
            
            result = await execute_plan_as_workflow(
                workflow_plan, 
                auth_http_client, 
                execution_mode=execution_mode,
                workflow_name=workflow_name
            )
            
            # Add metadata to response
            result["execution_metadata"] = {
                "mode": mode,
                "execution_mode": execution_mode,
                "session_id": session_id,
                "invocation_id": invocation_id
            }
            
            return JSONResponse(content=result, status_code=200)
            
        except Exception as workflow_ex:
            logger.error(f"{logging_prefix} Workflow execution failed: {workflow_ex}")
            return create_error_response(
                status_code=http_status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
                action=action_name,
                message="Workflow execution failed",
                details=str(workflow_ex)
            )

    # Single action execution
    action_function = ACTION_MAP.get(action_name)
    if not action_function:
        logger.warning(f"{logging_prefix} Acción '{action_name}' no encontrada en ACTION_MAP.")
        return create_error_response(
            status_code=http_status_codes.HTTP_400_BAD_REQUEST,
            action=action_name,
            message=f"La acción '{action_name}' no es válida o no está implementada en el backend."
        )

    logger.info(f"{logging_prefix} Ejecutando función mapeada '{action_function.__name__}' del módulo '{action_function.__module__}'")
    
    # Emit action started event
    await event_bus.emit(
        EventType.ACTION_STARTED,
        "dynamics_api",
        {
            "action": action_name,
            "params": params_req,
            "execution_mode": execution_mode,
            "session_id": session_id
        },
        session_id=session_id
    )
    
    try:
        # Phase 2: In suggestion mode, return the action plan without execution
        if not execution_mode:
            suggestion_response = {
                "status": "suggestion",
                "action": action_name,
                "params": params_req,
                "message": f"Acción '{action_name}' preparada para ejecución. Para ejecutar, envía la misma solicitud con mode='execution' o execution=true.",
                "execution_metadata": {
                    "mode": mode,
                    "execution_mode": execution_mode,
                    "session_id": session_id,
                    "invocation_id": invocation_id
                }
            }
            
            logger.info(f"{logging_prefix} Returning suggestion (execution mode disabled)")
            return JSONResponse(content=suggestion_response, status_code=200)
        
        # Execute the action
        result = action_function(auth_http_client, params_req)

        # Emit action completed event
        await event_bus.emit_action_completed(
            "dynamics_api",
            action_name,
            params_req,
            result,
            session_id=session_id
        )

        if isinstance(result, bytes):
            logger.info(f"{logging_prefix} Acción devolvió datos binarios ({len(result)} bytes).")
            media_type = "application/octet-stream" 
            content_disposition = "attachment"

            if "photo" in action_name.lower() or action_name.endswith("_get_my_photo"):
                media_type = "image/jpeg" 
                content_disposition = f"inline; filename=\"{action_name}.jpg\""
            elif action_name.endswith("_download_document") or \
                 action_name.endswith("_export_report") or \
                 action_name.endswith("_obtener_documento_word_binario"):
                
                filename_hint = params_req.get("filename", 
                                  params_req.get("nombre_archivo", 
                                     params_req.get("item_id_or_path", "downloaded_file")))
                
                safe_filename = "".join(c if c.isalnum() or c in ['.', '-', '_'] else '_' for c in str(filename_hint))
                
                file_extension = safe_filename.split(".")[-1].lower() if "." in safe_filename else ""

                if file_extension == "pdf": media_type = "application/pdf"
                elif file_extension in ["xlsx", "xls"]: media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                elif file_extension in ["docx", "doc"]: media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                elif file_extension == "csv": media_type = "text/csv"
                elif file_extension == "png": media_type = "image/png"
                elif file_extension == "zip": media_type = "application/zip"
                
                content_disposition = f"attachment; filename=\"{safe_filename}\""
                
            return Response(content=result, media_type=media_type, headers={"Content-Disposition": content_disposition})

        elif isinstance(result, str) and \
             action_name == "memory_export_session" and \
             params_req.get("format") == "csv":
            logger.info(f"{logging_prefix} Acción devolvió CSV como string ({len(result)} chars).")
            return Response(content=result, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=memory_export.csv"})

        elif isinstance(result, dict):
            if result.get("status") == "error":
                error_status_code = result.get("http_status", http_status_codes.HTTP_500_INTERNAL_SERVER_ERROR)
                if 200 <= error_status_code < 300: 
                    logger.warning(f"{logging_prefix} Acción devolvió status='error' pero con http_status de éxito ({error_status_code}). Forzando a 500.")
                    error_status_code = http_status_codes.HTTP_500_INTERNAL_SERVER_ERROR
                
                logger.error(f"{logging_prefix} Acción resultó en error explícito. Status: {error_status_code}, Mensaje: {result.get('message')}, Detalles: {result.get('details')}")
                return create_error_response(
                    status_code=error_status_code,
                    action=result.get("action", action_name), 
                    message=result.get("message", "Error desconocido en la ejecución de la acción."),
                    details=result.get("details"),
                    graph_error_code=result.get("graph_error_code") or result.get("api_error_code") 
                )
            else: 
                logger.info(f"{logging_prefix} Acción completada exitosamente. Resultado (claves): {list(result.keys())}")
                success_status_code = result.get("http_status", http_status_codes.HTTP_200_OK)
                if not (200 <= success_status_code < 300):
                    logger.warning(f"{logging_prefix} Acción devolvió status de éxito pero con http_status de error/redirect ({success_status_code}). Usando 200 OK.")
                    success_status_code = http_status_codes.HTTP_200_OK
                
                return JSONResponse(status_code=success_status_code, content=result)
        else: 
            logger.error(f"{logging_prefix} La acción devolvió un tipo de resultado inesperado: {type(result)}. Resultado: {str(result)[:200]}...")
            return create_error_response(
                status_code=http_status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
                action=action_name,
                message="Error interno del servidor: La acción devolvió un tipo de resultado inesperado."
            )
            
    except Exception as e: 
        logger.exception(f"{logging_prefix} Excepción no controlada durante la ejecución de la acción '{action_name}': {e}")
        return create_error_response(
            status_code=http_status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            action=action_name,
            message="Error interno del servidor al ejecutar la acción.",
            details=f"{type(e).__name__}: {str(e)}"
        )