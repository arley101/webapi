# app/api/routes/openai_direct.py
"""
Endpoint directo optimizado para OpenAI Custom GPT
Bypasea todos los validadores y procesadores problemáticos
"""
import logging
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from typing import Any, Dict, Optional
from datetime import datetime
import json

# Importar lo esencial
from app.core.action_mapper import ACTION_MAP, get_all_actions
from app.shared.helpers.http_client import AuthenticatedHttpClient
from azure.identity import DefaultAzureCredential

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/openai")
async def openai_direct_action(request: Request):
    """
    Endpoint directo para OpenAI Custom GPT
    Acepta cualquier formato y bypasea validaciones problemáticas
    """
    try:
        # Obtener el cuerpo de la request de forma flexible
        raw_body = await request.body()
        
        try:
            body = json.loads(raw_body.decode('utf-8'))
        except:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error", 
                    "message": "Invalid JSON format",
                    "timestamp": datetime.now().isoformat()
                }
            )
        
        # Extraer action y params de forma ROBUSTA - Maneja TODOS los formatos de OpenAI
        action = None
        params = {}
        
        logger.info(f"OpenAI Direct: Raw body received: {body}")
        
        # Parsing robusto que maneja MÚLTIPLES formatos de OpenAI Custom GPT
        if isinstance(body, dict):
            # FORMATO 1: {"action": "X", "params": {...}}  
            if "action" in body:
                action = body["action"]
                
                # Si hay params explícitos, usarlos
                if "params" in body and isinstance(body["params"], dict):
                    params = body["params"]
                # Si NO hay params explícitos, extraer TODOS los otros campos como params
                else:
                    # Excluir campos de control, tomar todo lo demás como parámetros
                    reserved_fields = {"action", "function_name", "message", "operationId"}
                    params = {k: v for k, v in body.items() if k not in reserved_fields}
                    
            # FORMATO 2: {"message": "action_name", "params": {...}} o {"message": "action_name", "field1": "value1"}
            elif "message" in body:
                action = body["message"]
                
                if "params" in body and isinstance(body["params"], dict):
                    params = body["params"]
                else:
                    reserved_fields = {"action", "function_name", "message", "operationId"}
                    params = {k: v for k, v in body.items() if k not in reserved_fields}
                    
            # FORMATO 3: {"function_name": "X", "arguments": {...}}
            elif "function_name" in body:
                action = body["function_name"]
                
                if "arguments" in body and isinstance(body["arguments"], dict):
                    params = body["arguments"]
                elif "params" in body and isinstance(body["params"], dict):
                    params = body["params"]
                else:
                    reserved_fields = {"action", "function_name", "message", "operationId", "arguments"}
                    params = {k: v for k, v in body.items() if k not in reserved_fields}
                    
            # FORMATO 4: Formato directo donde la primera clave podría ser la acción
            else:
                keys = list(body.keys())
                if keys:
                    # Intentar usar la primera clave como action si parece válida
                    potential_action = keys[0]
                    if isinstance(body[potential_action], dict):
                        action = potential_action
                        params = body[potential_action]
                    else:
                        # Si no es dict, asumir que todas las claves son parámetros y necesitamos una acción explícita
                        action = None
        
        # Validación robusta de la acción extraída
        if not action or not isinstance(action, str) or not action.strip():
            available_formats = [
                '{"action": "action_name", "param1": "value1"}',
                '{"action": "action_name", "params": {"param1": "value1"}}',
                '{"function_name": "action_name", "arguments": {"param1": "value1"}}',
                '{"message": "action_name", "param1": "value1"}'
            ]
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "message": "No valid action specified. Use one of these formats:",
                    "supported_formats": available_formats,
                    "received_body": body,
                    "timestamp": datetime.now().isoformat()
                }
            )
        
        # Normalizar params (asegurar que sea dict)
        if not isinstance(params, dict):
            params = {}
            
        # Logging detallado para debugging
        logger.info(f"OpenAI Direct: Action extracted: '{action}'")
        logger.info(f"OpenAI Direct: Params extracted: {params}")
        logger.info(f"OpenAI Direct: Params keys: {list(params.keys())}")
        logger.info(f"OpenAI Direct: Params count: {len(params)}")
        
        # Obtener todas las acciones disponibles
        all_actions = get_all_actions()
        
        # Verificar si la acción existe
        if action not in all_actions:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "error",
                    "message": f"Action '{action}' not found",
                    "available_actions": list(all_actions.keys())[:20],  # Primeras 20 para no saturar
                    "total_actions": len(all_actions),
                    "timestamp": datetime.now().isoformat()
                }
            )
        
        # Obtener la función
        action_function = all_actions[action]
        
        # Crear cliente autenticado
        try:
            credential = DefaultAzureCredential()
            auth_client = AuthenticatedHttpClient(credential=credential)
        except Exception as auth_error:
            logger.error(f"Authentication error: {auth_error}")
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "message": "Authentication failed",
                    "details": str(auth_error),
                    "timestamp": datetime.now().isoformat()
                }
            )
        
        # Ejecutar la acción con manejo robusto de errores
        try:
            logger.info(f"OpenAI Direct: About to execute {action} with client type: {type(auth_client).__name__}")
            
            # Ejecutar la función de acción
            result = action_function(auth_client, params)
            
            logger.info(f"OpenAI Direct: Action {action} completed successfully")
            
            # Formatear respuesta para OpenAI
            if isinstance(result, dict):
                if result.get("status") == "error":
                    logger.warning(f"OpenAI Direct: Action {action} returned error: {result.get('message')}")
                    return JSONResponse(
                        status_code=400,
                        content={
                            "status": "error",
                            "action": action,
                            "message": result.get("message", "Action execution failed"),
                            "details": result.get("details"),
                            "params_used": params,
                            "timestamp": datetime.now().isoformat()
                        }
                    )
                else:
                    # Respuesta exitosa
                    return JSONResponse(
                        status_code=200,
                        content={
                            "status": "success",
                            "action": action,
                            "data": result,
                            "params_used": list(params.keys()),
                            "timestamp": datetime.now().isoformat()
                        }
                    )
            else:
                # Resultado no es dict, wrapearlo
                return JSONResponse(
                    status_code=200,
                    content={
                        "status": "success",
                        "action": action,
                        "data": {"result": result},
                        "params_used": list(params.keys()),
                        "timestamp": datetime.now().isoformat()
                    }
                )
                
        except TypeError as type_error:
            # Error de tipo - probablemente parámetros incorrectos
            error_msg = str(type_error)
            logger.error(f"TypeError in action '{action}': {error_msg}")
            
            # Información detallada para debugging
            import inspect
            sig = inspect.signature(action_function)
            expected_params = list(sig.parameters.keys())
            
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "action": action,
                    "error_type": "TypeError",
                    "message": f"Parameter mismatch for action '{action}'",
                    "details": error_msg,
                    "expected_signature": str(sig),
                    "expected_params": expected_params,
                    "provided_params": list(params.keys()),
                    "params_received": params,
                    "debugging_info": {
                        "function_name": action_function.__name__,
                        "function_module": action_function.__module__
                    },
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as execution_error:
            # Error general de ejecución
            error_type = type(execution_error).__name__
            error_msg = str(execution_error)
            
            logger.error(f"Execution error ({error_type}) for action '{action}': {error_msg}")
            
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "action": action,
                    "error_type": error_type,
                    "message": f"Failed to execute action '{action}'",
                    "details": error_msg,
                    "params_used": params,
                    "debugging_info": {
                        "function_name": action_function.__name__,
                        "function_module": action_function.__module__,
                        "total_available_actions": len(all_actions)
                    },
                    "timestamp": datetime.now().isoformat()
                }
            )
            
    except Exception as general_error:
        logger.error(f"General error in openai_direct: {general_error}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": "Internal server error",
                "details": str(general_error),
                "timestamp": datetime.now().isoformat()
            }
        )

@router.get("/openai/actions")
async def list_available_actions():
    """
    Lista todas las acciones disponibles para OpenAI
    """
    try:
        all_actions = get_all_actions()
        
        # Organizar por categorías para mejor legibilidad
        categorized_actions = {}
        
        for action_name in all_actions.keys():
            # Extraer categoría del nombre de la acción
            if "_" in action_name:
                category = action_name.split("_")[0]
            else:
                category = "general"
            
            if category not in categorized_actions:
                categorized_actions[category] = []
            
            categorized_actions[category].append(action_name)
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "total_actions": len(all_actions),
                "categories": len(categorized_actions),
                "actions_by_category": categorized_actions,
                "all_actions": list(all_actions.keys()),
                "timestamp": datetime.now().isoformat()
            }
        )
        
    except Exception as error:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": "Failed to list actions",
                "details": str(error),
                "timestamp": datetime.now().isoformat()
            }
        )

@router.post("/openai/test")
async def test_openai_connection():
    """
    Endpoint de prueba simple para OpenAI
    """
    try:
        # Prueba básica con una acción simple
        all_actions = get_all_actions()
        
        # Intentar ejecutar resolver_get_all_actions como prueba
        if "resolver_get_all_actions" in all_actions:
            try:
                credential = DefaultAzureCredential()
                auth_client = AuthenticatedHttpClient(credential=credential)
                
                test_function = all_actions["resolver_get_all_actions"]
                test_result = test_function(auth_client, {})
                
                return JSONResponse(
                    status_code=200,
                    content={
                        "status": "success",
                        "message": "OpenAI endpoint working correctly",
                        "test_action": "resolver_get_all_actions",
                        "test_result": test_result,
                        "available_actions_count": len(all_actions),
                        "timestamp": datetime.now().isoformat()
                    }
                )
            except Exception as test_error:
                return JSONResponse(
                    status_code=500,
                    content={
                        "status": "error",
                        "message": "Test action failed",
                        "details": str(test_error),
                        "timestamp": datetime.now().isoformat()
                    }
                )
        else:
            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "message": "OpenAI endpoint accessible",
                    "available_actions_count": len(all_actions),
                    "note": "Test action not available",
                    "timestamp": datetime.now().isoformat()
                }
            )
            
    except Exception as error:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": "OpenAI endpoint test failed",
                "details": str(error),
                "timestamp": datetime.now().isoformat()
            }
        )
