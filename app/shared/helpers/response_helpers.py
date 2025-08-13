# app/shared/helpers/response_helpers.py
"""
Helpers para respuestas HTTP estandarizadas
"""

from typing import Any, Dict, Optional
from fastapi import HTTPException
from app.shared.constants import SUCCESS_RESPONSE, ERROR_RESPONSE

def create_success_response(data: Any = None, message: str = "Success") -> Dict[str, Any]:
    """Crea una respuesta de éxito estandarizada"""
    response = {
        "success": True,
        "message": message
    }
    
    if data is not None:
        if isinstance(data, dict) and "success" in data:
            # Si data ya contiene los campos de respuesta, usarlos directamente
            response.update(data)
        else:
            response["data"] = data
    
    return response

def create_error_response(error: str, status_code: int = 400, details: Any = None) -> Dict[str, Any]:
    """Crea una respuesta de error estandarizada"""
    response = {
        "success": False,
        "error": error,
        "status_code": status_code
    }
    
    if details is not None:
        response["details"] = details
    
    return response

def handle_action_result(result: Dict[str, Any], success_message: str = "Operación exitosa", error_message: str = "Error en la operación") -> Dict[str, Any]:
    """Maneja el resultado de una acción y devuelve respuesta estandarizada"""
    if result.get("success"):
        return create_success_response(data=result, message=success_message)
    else:
        error = result.get("error", error_message)
        return create_error_response(error=error)
