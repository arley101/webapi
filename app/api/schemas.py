# app/api/schemas.py
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List, Union


class ActionRequest(BaseModel):
    action: str = Field(..., example="calendar_list_events", description="Nombre de la acción a ejecutar.")
    params: Dict[str, Any] = Field(default_factory=dict, example={"start_datetime": "2025-05-20T08:00:00Z", "end_datetime": "2025-05-20T17:00:00Z"}, description="Parámetros para la acción.")

class ErrorDetail(BaseModel):
    code: Optional[str] = None
    message: Optional[str] = None
    target: Optional[str] = None
    details: Optional[List[Any]] = None 

class ErrorResponse(BaseModel):
    status: str = "error"
    action: Optional[str] = Field(default=None, description="La acción que se intentó ejecutar.")
    message: str = Field(..., example="Descripción del error.", description="Mensaje legible por humanos describiendo el error.")
    http_status: Optional[int] = Field(default=500, example=500, description="El código de estado HTTP asociado con este error.")
    details: Optional[Union[str, Dict[str, Any], List[Dict[str, Any]], ErrorDetail]] = Field(default=None, description="Detalles técnicos adicionales sobre el error.")
    graph_error_code: Optional[str] = Field(default=None, description="Código de error específico devuelto por Microsoft Graph, si aplica.")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": "error",
                    "action": "calendar_list_events",
                    "message": "Error de autenticación: Credencial de Azure no disponible.",
                    "http_status": 500,
                    "details": "CredentialUnavailableError: DefaultAzureCredential DefaultAzureCredential انواع اعتبارنامه موجود را امتحان کرد اما هیچکدام کار نکردند.",
                    "graph_error_code": None
                },
                {
                    "status": "error",
                    "action": "graph_generic_get",
                    "message": "'graph_path' es requerido dentro de 'params' (ej. {'graph_path': 'organization'}).",
                    "http_status": 400,
                    "details": "Params recibidos: {}",
                    "graph_error_code": None
                }
            ]
        }
    }