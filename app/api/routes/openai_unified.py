# app/api/routes/openai_unified.py
"""
🤖 ENDPOINT UNIFICADO PARA OPENAI ASSISTANT & CHATGPT
Reemplaza todos los endpoints conflictivos actuales.
Diseñado para máxima compatibilidad con OpenAI Custom GPT y Assistant API.

✅ CARACTERÍSTICAS:
- Parsing robusto de TODOS los formatos de OpenAI
- Acceso directo a las 476+ acciones del action_mapper
- Autenticación OAuth automática unificada
- Compatible con OpenAPI 3.0.3 y 3.1.0
- Sin limitaciones ni validaciones problemáticas
"""

import logging
import json
import asyncio
from datetime import datetime
from typing import Any, Dict, Optional, List, Union
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Importaciones core
from app.core.action_mapper import ACTION_MAP, get_all_actions
from app.core.auth_manager import get_current_user, AuthenticatedUser
from app.core.unified_oauth_manager import unified_oauth

# Importaciones de memoria y workflows
try:
    from app.memory.simple_memory import simple_memory_manager as memory_manager
    from app.workflows.workflow_functions import execute_predefined_workflow, list_available_workflows
except ImportError:
    memory_manager = None
    execute_predefined_workflow = None
    list_available_workflows = None

# Configurar logging
logger = logging.getLogger(__name__)
router = APIRouter()

# ============================================================================
# 📋 MODELOS PYDANTIC PARA OPENAI COMPATIBILITY
# ============================================================================

class OpenAIActionRequest(BaseModel):
    """
    Modelo flexible para requests de OpenAI
    Maneja TODOS los formatos posibles de Custom GPT y Assistant API
    """
    # Campos principales
    action: Optional[str] = Field(None, description="Nombre de la acción a ejecutar")
    params: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Parámetros para la acción")
    
    # Formatos alternativos de OpenAI
    message: Optional[str] = Field(None, description="Formato alternativo: mensaje/acción")
    function_name: Optional[str] = Field(None, description="Formato Assistant API")
    arguments: Optional[Dict[str, Any]] = Field(None, description="Argumentos Assistant API")
    operationId: Optional[str] = Field(None, description="ID de operación OpenAPI")
    
    # Campos contextuales
    context: Optional[str] = Field(None, description="Contexto adicional")
    user_id: Optional[str] = Field(None, description="ID del usuario")
    session_id: Optional[str] = Field(None, description="ID de sesión")
    
    # Permitir campos adicionales (crucial para OpenAI flexibility)
    class Config:
        extra = "allow"  # Permite campos adicionales no definidos

class OpenAIResponse(BaseModel):
    """Respuesta estandarizada para OpenAI"""
    status: str = Field(description="Estado: success, error, partial")
    message: str = Field(description="Mensaje descriptivo")
    data: Optional[Dict[str, Any]] = Field(None, description="Datos de respuesta")
    action_executed: Optional[str] = Field(None, description="Acción que se ejecutó")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    execution_time_ms: Optional[int] = Field(None, description="Tiempo de ejecución en ms")
    
    # Campos específicos para OpenAI Custom GPT
    openai_compatible: bool = Field(True, description="Indica compatibilidad con OpenAI")
    suggestions: Optional[List[str]] = Field(None, description="Sugerencias para el usuario")

# ============================================================================
# 🎯 PARSING INTELIGENTE PARA OPENAI
# ============================================================================

def parse_openai_request(raw_data: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
    """
    🧠 PARSER ULTRA-ROBUSTO para TODOS los formatos de OpenAI
    Maneja Custom GPT, Assistant API, y formatos personalizados
    """
    action = None
    params = {}
    
    logger.info(f"🔍 Parsing OpenAI request: {json.dumps(raw_data, indent=2)}")
    
    # FORMATO 1: {"action": "X", "params": {...}} - Formato estándar
    if "action" in raw_data:
        action = raw_data["action"]
        if "params" in raw_data and isinstance(raw_data["params"], dict):
            params = raw_data["params"]
        else:
            # Excluir campos de control, usar el resto como parámetros
            control_fields = {"action", "message", "function_name", "operationId", "context", "user_id", "session_id"}
            params = {k: v for k, v in raw_data.items() if k not in control_fields}
    
    # FORMATO 2: {"message": "action_name", ...} - Custom GPT común
    elif "message" in raw_data:
        action = raw_data["message"]
        if "params" in raw_data and isinstance(raw_data["params"], dict):
            params = raw_data["params"]
        else:
            control_fields = {"action", "message", "function_name", "operationId", "context", "user_id", "session_id"}
            params = {k: v for k, v in raw_data.items() if k not in control_fields}
    
    # FORMATO 3: {"function_name": "X", "arguments": {...}} - Assistant API
    elif "function_name" in raw_data:
        action = raw_data["function_name"]
        if "arguments" in raw_data and isinstance(raw_data["arguments"], dict):
            params = raw_data["arguments"]
        elif "params" in raw_data and isinstance(raw_data["params"], dict):
            params = raw_data["params"]
        else:
            control_fields = {"action", "function_name", "message", "operationId", "arguments", "context", "user_id", "session_id"}
            params = {k: v for k, v in raw_data.items() if k not in control_fields}
    
    # FORMATO 4: {"operationId": "X", ...} - OpenAPI 3.0.3 format
    elif "operationId" in raw_data:
        action = raw_data["operationId"]
        control_fields = {"action", "function_name", "message", "operationId", "context", "user_id", "session_id"}
        params = {k: v for k, v in raw_data.items() if k not in control_fields}
    
    # FORMATO 5: Inteligencia artificial - buscar acción en cualquier campo string
    else:
        # Buscar en todos los campos string si alguno coincide con una acción disponible
        for key, value in raw_data.items():
            if isinstance(value, str) and value in ACTION_MAP:
                action = value
                params = {k: v for k, v in raw_data.items() if k != key}
                break
        
        # Si no encuentra, usar la primera clave como acción potencial
        if not action and raw_data:
            keys = list(raw_data.keys())
            potential_action = keys[0]
            if isinstance(raw_data[potential_action], dict):
                action = potential_action
                params = raw_data[potential_action]
            else:
                # Asumir que todas las claves son parámetros, necesitamos más información
                action = None
    
    # Limpiar acción
    if action:
        action = str(action).strip()
    
    # Asegurar que params es un dict
    if not isinstance(params, dict):
        params = {}
    
    logger.info(f"✅ Parsed - Action: {action}, Params: {params}")
    return action, params

# ============================================================================
# 🌟 MAPEO INTELIGENTE DE LENGUAJE NATURAL
# ============================================================================

NATURAL_LANGUAGE_ACTIONS = {
    # Marketing Digital
    "crear campaña facebook": "metaads_create_campaign",
    "crear campaña meta": "metaads_create_campaign", 
    "crear campaña google": "googleads_create_campaign",
    "crear campaña linkedin": "linkedin_ads_create_campaign",
    "crear campaña tiktok": "tiktok_ads_create_campaign",
    
    # Correo y Comunicación
    "enviar correo": "email_send_message",
    "enviar email": "email_send_message",
    "leer correos": "email_list_messages",
    "crear contacto": "graph_create_contact",
    
    # YouTube y Video
    "subir video youtube": "youtube_upload_video",
    "listar videos youtube": "youtube_list_videos",
    "descargar video": "youtube_download_video",
    
    # Teams y Colaboración
    "crear equipo teams": "teams_create_team",
    "enviar mensaje teams": "teams_send_message",
    "crear reunión": "calendar_create_event",
    
    # SharePoint y Documentos
    "crear sitio sharepoint": "sharepoint_create_site",
    "subir archivo sharepoint": "sharepoint_upload_file",
    "listar archivos": "onedrive_list_files",
    
    # OneDrive y Almacenamiento
    "subir archivo onedrive": "onedrive_upload_file",
    "crear carpeta": "onedrive_create_folder",
    "compartir archivo": "onedrive_share_file",
    
    # WordPress y CMS
    "crear post wordpress": "wordpress_create_post",
    "publicar contenido": "wordpress_publish_post",
    "actualizar sitio": "wordpress_update_post",
    
    # Workflows y Automatización
    "ejecutar workflow": "execute_predefined_workflow",
    "listar workflows": "list_available_workflows",
    "crear automatización": "create_dynamic_workflow",
    
    # Memoria y IA
    "guardar memoria": "save_memory",
    "buscar memoria": "search_memory",
    "consultar historial": "get_memory_history",
    "generar contenido": "openai_generate_content",
    
    # Sistema y Utilidades
    "listar acciones": "list_all_actions",
    "estado sistema": "get_system_status",
    "refrescar tokens": "refresh_all_tokens"
}

def find_action_by_natural_language(query: str) -> Optional[str]:
    """
    🧠 BÚSQUEDA INTELIGENTE de acciones usando lenguaje natural
    """
    query = query.lower().strip()
    
    # 1. Búsqueda exacta en el mapa
    for phrase, action in NATURAL_LANGUAGE_ACTIONS.items():
        if phrase in query:
            return action
    
    # 2. Búsqueda por palabras clave en acciones disponibles
    query_words = query.split()
    best_match = None
    max_score = 0
    
    for action_name in ACTION_MAP.keys():
        score = 0
        action_lower = action_name.lower()
        
        # Puntuación por coincidencias de palabras
        for word in query_words:
            if word in action_lower:
                score += 2
            elif any(word in part for part in action_lower.split('_')):
                score += 1
        
        if score > max_score:
            max_score = score
            best_match = action_name
    
    return best_match if max_score > 0 else None

# ============================================================================
# 🚀 ENDPOINT PRINCIPAL UNIFICADO
# ============================================================================

@router.post("/openai", response_model=OpenAIResponse)
@router.post("/assistant", response_model=OpenAIResponse)  # Alias para Assistant API
@router.post("/chatgpt", response_model=OpenAIResponse)    # Alias para Custom GPT
async def openai_unified_endpoint(
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user)
):
    """
    🎯 ENDPOINT UNIFICADO PARA OPENAI
    
    Maneja TODOS los formatos de OpenAI:
    - Custom GPT requests
    - Assistant API calls  
    - Function calling
    - Natural language queries
    
    Sin limitaciones ni validaciones problemáticas.
    Acceso directo a todas las 476+ acciones disponibles.
    """
    start_time = datetime.now()
    
    try:
        # 1. OBTENER DATOS RAW DE LA REQUEST
        raw_body = await request.body()
        
        try:
            raw_data = json.loads(raw_body.decode('utf-8'))
        except json.JSONDecodeError:
            return OpenAIResponse(
                status="error",
                message="Invalid JSON format in request body",
                suggestions=["Ensure request body contains valid JSON"]
            )
        
        logger.info(f"🤖 OpenAI Unified Endpoint - User: {user.user_id}, Data keys: {list(raw_data.keys())}")
        
        # 2. PARSING INTELIGENTE
        action, params = parse_openai_request(raw_data)
        
        # 3. BÚSQUEDA POR LENGUAJE NATURAL SI NO ENCUENTRA ACCIÓN
        if not action or action not in ACTION_MAP:
            # Buscar en campos de texto por lenguaje natural
            for key, value in raw_data.items():
                if isinstance(value, str) and len(value) > 3:
                    natural_action = find_action_by_natural_language(value)
                    if natural_action:
                        action = natural_action
                        break
        
        # 4. VALIDACIONES MÍNIMAS
        if not action:
            available_actions = list(ACTION_MAP.keys())[:10]  # Primeras 10 para ejemplo
            return OpenAIResponse(
                status="error",
                message="No action specified or found in request",
                suggestions=[
                    "Specify 'action' field with valid action name",
                    "Use natural language like 'enviar correo' or 'crear campaña facebook'",
                    f"Available actions include: {', '.join(available_actions[:5])}..."
                ],
                data={"available_actions_sample": available_actions}
            )
        
        if action not in ACTION_MAP:
            similar_actions = [a for a in ACTION_MAP.keys() if action.lower() in a.lower()][:5]
            return OpenAIResponse(
                status="error", 
                message=f"Action '{action}' not found in action mapper",
                suggestions=[
                    f"Did you mean: {', '.join(similar_actions)}" if similar_actions else "Check available actions",
                    "Use 'list_all_actions' to see all available actions"
                ],
                data={"similar_actions": similar_actions}
            )
        
        # 5. PREPARAR CONTEXTO DE EJECUCIÓN
        # Crear cliente HTTP autenticado (usando el sistema OAuth unificado)
        from app.shared.helpers.http_client import AuthenticatedHttpClient
        from azure.identity import DefaultAzureCredential
        
        client = AuthenticatedHttpClient(DefaultAzureCredential())
        
        # Agregar información del usuario a los parámetros
        if not isinstance(params, dict):
            params = {}
        
        params["_user_context"] = {
            "user_id": user.user_id,
            "email": user.email,
            "tenant_id": user.tenant_id
        }
        
        # 6. EJECUTAR ACCIÓN
        logger.info(f"🚀 Executing action: {action} with params: {list(params.keys())}")
        
        try:
            action_function = ACTION_MAP[action]
            
            # Ejecutar la acción (puede ser sync o async)
            if asyncio.iscoroutinefunction(action_function):
                result = await action_function(client, params)
            else:
                result = action_function(client, params)
            
            # 7. PROCESAR RESULTADO
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # Asegurar que el resultado sea serializable
            if isinstance(result, dict):
                response_data = result
                status = result.get("status", "success")
                message = result.get("message", f"Action '{action}' executed successfully")
            else:
                response_data = {"result": str(result)}
                status = "success"
                message = f"Action '{action}' completed"
            
            return OpenAIResponse(
                status=status,
                message=message,
                data=response_data,
                action_executed=action,
                execution_time_ms=execution_time
            )
            
        except Exception as action_error:
            logger.error(f"💥 Error executing action {action}: {str(action_error)}")
            return OpenAIResponse(
                status="error",
                message=f"Error executing action '{action}': {str(action_error)}",
                action_executed=action,
                execution_time_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                suggestions=[
                    "Check if all required parameters are provided",
                    "Verify OAuth tokens are valid",
                    "Try refreshing authentication"
                ]
            )
    
    except Exception as e:
        logger.error(f"💥 Critical error in OpenAI unified endpoint: {str(e)}")
        return OpenAIResponse(
            status="error", 
            message=f"Critical error: {str(e)}",
            execution_time_ms=int((datetime.now() - start_time).total_seconds() * 1000),
            suggestions=[
                "Check request format",
                "Verify authentication", 
                "Contact system administrator if error persists"
            ]
        )

# ============================================================================
# 🔧 ENDPOINTS DE UTILIDAD
# ============================================================================

@router.get("/actions", response_model=Dict[str, Any])
async def list_available_actions():
    """Lista todas las acciones disponibles para OpenAI"""
    try:
        actions = list(ACTION_MAP.keys())
        categorized_actions = {}
        
        # Categorizar acciones por prefijo
        categories = {}
        for action in actions:
            prefix = action.split('_')[0] if '_' in action else 'other'
            if prefix not in categories:
                categories[prefix] = []
            categories[prefix].append(action)
        
        return {
            "status": "success",
            "total_actions": len(actions),
            "categories": categories,
            "natural_language_examples": list(NATURAL_LANGUAGE_ACTIONS.keys())[:10],
            "openai_compatible": True
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/oauth/status", response_model=Dict[str, Any])
async def oauth_status():
    """Estado de los tokens OAuth"""
    try:
        status = unified_oauth.get_token_status()
        return {
            "status": "success",
            "oauth_services": status,
            "openai_compatible": True
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/oauth/refresh", response_model=Dict[str, Any])
async def refresh_oauth_tokens():
    """Refresca todos los tokens OAuth"""
    try:
        results = await unified_oauth.refresh_all_tokens()
        return {
            "status": "success",
            "refresh_results": results,
            "openai_compatible": True
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/health", response_model=Dict[str, Any])
async def health_check():
    """Health check para OpenAI"""
    return {
        "status": "healthy",
        "service": "OpenAI Unified Endpoint",
        "timestamp": datetime.now().isoformat(),
        "actions_available": len(ACTION_MAP),
        "oauth_system": "unified",
        "openai_compatible": True
    }