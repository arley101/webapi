# app/api/schemas.py
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List, Union


class ActionRequest(BaseModel):
    """
    Modelo para el cuerpo de la solicitud de acción.
    Valida que 'action' esté presente y que 'params' sea un diccionario.
    """
    action: str = Field(..., example="calendar_list_events", description="Nombre de la acción a ejecutar.")
    params: Dict[str, Any] = Field(default_factory=dict, example={"start_datetime": "2025-05-20T08:00:00Z", "end_datetime": "2025-05-20T17:00:00Z"}, description="Parámetros para la acción.")
    
    # Phase 2: Task 2.2 - mode=execution flag
    mode: Optional[str] = Field(default="suggestion", example="execution", description="Modo de operación: 'suggestion' para depuración, 'execution' para ejecución sin confirmación.")
    execution: Optional[bool] = Field(default=None, example=True, description="Flag booleano para mode=execution. Si es true, ejecuta sin confirmación.")
    
    # Additional orchestration parameters
    session_id: Optional[str] = Field(default=None, example="session_123", description="ID de sesión para tracking de workflow.")
    workflow_id: Optional[str] = Field(default=None, example="workflow_456", description="ID de workflow si es parte de una secuencia.")

class ErrorDetail(BaseModel):
    """
    Modelo para detalles de error específicos, si los hay.
    No se usa directamente en ErrorResponse en la versión actual del ZIP, pero está disponible.
    """
    code: Optional[str] = None
    message: Optional[str] = None
    target: Optional[str] = None
    details: Optional[List[Any]] = None # Podría ser una lista de otros ErrorDetail

class ErrorResponse(BaseModel):
    """
    Modelo para una respuesta de error estandarizada.
    """
    status: str = "error"
    action: Optional[str] = Field(default=None, description="La acción que se intentó ejecutar.")
    message: str = Field(..., example="Descripción del error.", description="Mensaje legible por humanos describiendo el error.")
    http_status: Optional[int] = Field(default=500, example=500, description="El código de estado HTTP asociado con este error.")
    # 'details' permite flexibilidad en el tipo de información de error adicional que se puede proporcionar.
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
                    "details": "CredentialUnavailableError: DefaultAzureCredential انواع اعتبارنامه موجود را امتحان کرد اما هیچکدام کار نکردند.",
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

# Ejemplo de cómo podría usarse SuccessActionResponse si se estandariza.
# No está en el archivo original, pero es una buena práctica.
# class SuccessActionResponse(BaseModel):
#     status: str = "success"
#     action: str
#     message: Optional[str] = None
#     http_status: int = Field(default=200, example=200)
#     data: Optional[Any] = None # El resultado de la acción
#     total_retrieved: Optional[int] = None
#     pages_processed: Optional[int] = None
