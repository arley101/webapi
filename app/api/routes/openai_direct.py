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
        
        # Extraer action y params de forma flexible
        action = None
        params = {}
        
        # Intentar múltiples formatos
        if isinstance(body, dict):
            # Formato estándar: {"action": "...", "params": {...}}
            if "action" in body:
                action = body["action"]
                params = body.get("params", {})
                
                # NUEVO: Si no hay params explícitos, tomar todos los otros campos como params
                if not params:
                    params = {k: v for k, v in body.items() if k != "action"}
                    
            # Formato alternativo: {"message": "action_name", "params": {...}}
            elif "message" in body:
                action = body["message"]
                params = body.get("params", {})
                
                # NUEVO: Si no hay params explícitos, tomar todos los otros campos como params
                if not params:
                    params = {k: v for k, v in body.items() if k != "message"}
                    
            # Formato directo: {"function_name": "...", "arguments": {...}}
            elif "function_name" in body:
                action = body["function_name"]
                params = body.get("arguments", {})
            else:
                # Si no hay action clara, usar la primera clave como action
                keys = list(body.keys())
                if keys:
                    action = keys[0]
                    params = body.get(keys[0], {}) if isinstance(body.get(keys[0]), dict) else {}
        
        if not action:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "message": "No action specified. Use format: {'action': 'action_name', 'params': {...}}",
                    "received_body": body,
                    "timestamp": datetime.now().isoformat()
                }
            )
        
        logger.info(f"OpenAI Direct: Executing action '{action}' with params: {params}")
        logger.info(f"OpenAI Direct: Raw body received: {body}")
        logger.info(f"OpenAI Direct: Extracted params keys: {list(params.keys())}")
        
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
        
        # Ejecutar la acción
        try:
            result = action_function(auth_client, params)
            
            # Formatear respuesta para OpenAI
            if isinstance(result, dict):
                if result.get("status") == "error":
                    return JSONResponse(
                        status_code=400,
                        content={
                            "status": "error",
                            "action": action,
                            "message": result.get("message", "Action execution failed"),
                            "details": result.get("details"),
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
                        "timestamp": datetime.now().isoformat()
                    }
                )
                
        except Exception as execution_error:
            logger.error(f"Execution error for action '{action}': {execution_error}")
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "action": action,
                    "message": "Action execution failed",
                    "details": str(execution_error),
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
