# app/core/openapi_compatibility.py
"""
Configuración personalizada de OpenAPI para compatibilidad con Custom GPT
Degrada OpenAPI de 3.1.0 a 3.0.3 para máxima compatibilidad
"""

from fastapi.openapi.utils import get_openapi
from typing import Dict, Any

def get_custom_gpt_openapi(app) -> Dict[str, Any]:
    """
    Genera especificación OpenAPI 3.0.3 compatible con Custom GPT
    Soluciona problemas de compatibilidad con OpenAPI 3.1.0
    """
    if app.openapi_schema:
        return app.openapi_schema
    
    # Generar esquema base
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # FORZAR OpenAPI 3.0.3 para compatibilidad con Custom GPT
    openapi_schema["openapi"] = "3.0.3"
    
    # Optimizar para Custom GPT
    openapi_schema["info"]["title"] = "Elite Dynamics API - Optimizado para Custom GPT"
    openapi_schema["info"]["description"] = """
    API empresarial con 476+ acciones integradas.
    Optimizada para compatibilidad total con OpenAI Custom GPT.
    
    Funcionalidades principales:
    - 📧 Gestión de emails y calendario
    - 📊 Marketing digital (Google Ads, Meta, LinkedIn, TikTok)
    - 💼 Productividad (Teams, SharePoint, OneDrive)
    - 🤖 IA y automatización
    - 📱 Redes sociales y contenido
    """
    
    # Configurar servidor para Custom GPT
    openapi_schema["servers"] = [
        {
            "url": "/",
            "description": "Servidor principal"
        }
    ]
    
    # Agregar esquemas de seguridad simplificados para Custom GPT
    openapi_schema["components"]["securitySchemes"] = {
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Token de autorización Bearer"
        }
    }
    
    # Simplificar respuestas para Custom GPT
    for path, methods in openapi_schema["paths"].items():
        for method, operation in methods.items():
            if isinstance(operation, dict):
                # Simplificar parámetros
                if "parameters" in operation:
                    for param in operation["parameters"]:
                        if "schema" in param:
                            # Convertir schemas complejos a tipos simples
                            schema = param["schema"]
                            if schema.get("type") == "array" and "items" in schema:
                                # Simplificar arrays
                                if "type" not in schema["items"]:
                                    schema["items"] = {"type": "string"}
                
                # Agregar ejemplos claros para Custom GPT
                if "requestBody" in operation:
                    content = operation["requestBody"].get("content", {})
                    for media_type, media_schema in content.items():
                        if "schema" in media_schema:
                            # Agregar ejemplos específicos para Custom GPT
                            if path == "/api/v1/chatgpt":
                                media_schema["example"] = {
                                    "query": "envía un email a juan@empresa.com con asunto 'Reunión' y mensaje 'Hola Juan, confirmemos la reunión para mañana'",
                                    "context": "gestión de emails"
                                }
                            elif path == "/api/v1/dynamics":
                                media_schema["example"] = {
                                    "action": "email_send_message",
                                    "params": {
                                        "to": "destinatario@email.com",
                                        "subject": "Asunto del email",
                                        "body": "Contenido del mensaje"
                                    }
                                }
                
                # Simplificar respuestas
                if "responses" in operation:
                    for status_code, response in operation["responses"].items():
                        if "content" in response:
                            for media_type, content_schema in response["content"].items():
                                if "schema" in content_schema:
                                    # Agregar ejemplos de respuesta para Custom GPT
                                    content_schema["example"] = {
                                        "status": "success",
                                        "message": "Operación completada exitosamente",
                                        "data": "Resultado de la operación"
                                    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

def optimize_for_custom_gpt(app):
    """
    Aplica optimizaciones específicas para Custom GPT
    """
    # Reemplazar la función openapi por nuestra versión compatible
    app.openapi = lambda: get_custom_gpt_openapi(app)
    
    return app
