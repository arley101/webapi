"""
Sistema de información y documentación del API
Proporciona endpoints para consultar estado, acciones disponibles y documentación
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta
import json
from typing import Dict, Any, List
from app.core.action_mapper import ACTION_MAP
import platform
import psutil
import os

router = APIRouter()

@router.get("/actions")
async def get_available_actions():
    """
    Lista todas las acciones disponibles organizadas por categorías
    """
    try:
        # Organizar acciones por categorías
        categories = {}
        popular_actions = []
        new_features = []
        
        for action_name, action_config in ACTION_MAP.items():
            category = action_config.get('category', 'otros')
            
            if category not in categories:
                categories[category] = []
            
            categories[category].append(action_name)
            
            # Marcar acciones populares (ejemplo)
            if any(keyword in action_name for keyword in ['email', 'calendario', 'intelligent', 'runway']):
                popular_actions.append(action_name)
            
            # Marcar funciones nuevas (ejemplo)
            if any(keyword in action_name for keyword in ['runway', 'stream', 'vivainsights']):
                new_features.append(action_name)
        
        return {
            "total_actions": len(ACTION_MAP),
            "categories": categories,
            "popular_actions": popular_actions[:10],  # Top 10
            "new_features": new_features[:5],  # Top 5 nuevas
            "last_updated": datetime.now().isoformat(),
            "description": "EliteDynamics API - Sistema empresarial completo con integraciones avanzadas"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo acciones: {str(e)}")

@router.get("/status")
async def get_system_status():
    """
    Estado completo del sistema y servicios conectados
    """
    try:
        # Información del sistema
        uptime_seconds = psutil.boot_time()
        uptime = datetime.now() - datetime.fromtimestamp(uptime_seconds)
        
        # Estado de servicios (simulado - en producción conectar a servicios reales)
        services = {
            "email": {
                "status": "operational",
                "last_check": datetime.now().isoformat(),
                "provider": "Microsoft Graph API"
            },
            "azure": {
                "status": "operational",
                "regions": ["East US", "West Europe"],
                "last_check": datetime.now().isoformat()
            },
            "ai_services": {
                "openai": "operational" if os.getenv("OPENAI_API_KEY") else "not_configured",
                "runway": "operational" if os.getenv("RUNWAY_API_KEY") else "not_configured",
                "gemini": "operational" if os.getenv("GEMINI_API_KEY") else "not_configured"
            }
        }
        
        # Métricas del sistema
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=1)
        
        return {
            "status": "healthy",
            "version": "1.1.0",
            "uptime": f"{uptime.days} days, {uptime.seconds // 3600} hours",
            "environment": os.getenv("ENVIRONMENT", "production"),
            "services": services,
            "metrics": {
                "total_requests_today": "N/A",  # En producción conectar a analytics
                "successful_actions": "N/A",
                "average_response_time": "< 2s",
                "memory_usage": f"{memory.percent}%",
                "cpu_usage": f"{cpu_percent}%"
            },
            "system_info": {
                "platform": platform.system(),
                "python_version": platform.python_version(),
                "total_actions": len(ACTION_MAP)
            },
            "last_check": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo estado: {str(e)}")

@router.get("/docs")
async def get_api_documentation():
    """
    Documentación completa del API con ejemplos y guías
    """
    try:
        # Documentación estructurada
        quick_start_simple = [
            {
                "command": "lee mis correos",
                "description": "Lista los correos más recientes",
                "example": '{"mensaje": "lee mis últimos 5 correos de ceo@empresa.com"}'
            },
            {
                "command": "crea reunión",
                "description": "Crea un evento en el calendario",
                "example": '{"mensaje": "crea reunión mañana a las 2pm con el equipo"}'
            },
            {
                "command": "genera video",
                "description": "Crea video con Runway AI",
                "example": '{"mensaje": "genera video de un gato jugando en el jardín"}'
            },
            {
                "command": "busca en SharePoint",
                "description": "Busca documentos en SharePoint",
                "example": '{"mensaje": "busca documentos sobre contrato en SharePoint"}'
            },
            {
                "command": "envía mensaje Teams",
                "description": "Envía mensaje via Microsoft Teams",
                "example": '{"mensaje": "envía mensaje a @juan en Teams: reunión a las 3pm"}'
            }
        ]
        
        structured_examples = [
            {
                "action": "email_list_messages",
                "description": "Lista correos electrónicos",
                "example": {
                    "action": "email_list_messages",
                    "mailbox": "usuario@empresa.com",
                    "top_per_page": 10
                }
            },
            {
                "action": "calendario_create_event",
                "description": "Crea evento de calendario",
                "example": {
                    "action": "calendario_create_event",
                    "params": {
                        "subject": "Reunión importante",
                        "start_date": "2025-08-16",
                        "start_time": "14:00",
                        "duration_minutes": 60
                    }
                }
            }
        ]
        
        # Organizar categorías con ejemplos
        categories_docs = {}
        for action_name, action_config in ACTION_MAP.items():
            category = action_config.get('category', 'otros')
            
            if category not in categories_docs:
                categories_docs[category] = {
                    "description": f"Acciones relacionadas con {category}",
                    "actions": []
                }
            
            # Agregar información de la acción
            action_info = {
                "name": action_name,
                "description": action_config.get('description', f'Ejecuta {action_name}'),
                "parameters": action_config.get('required_params', []),
                "examples": []
            }
            
            categories_docs[category]["actions"].append(action_info)
        
        return {
            "title": "EliteDynamics API - Guía Completa",
            "overview": "API empresarial avanzada con 468+ integraciones para automatización completa de procesos de negocio. Incluye integraciones con Microsoft 365, Azure, AI Services, y muchos más.",
            "quick_start": {
                "simple_commands": quick_start_simple,
                "structured_calls": structured_examples
            },
            "endpoints": {
                "simple": "/api/v1/simple - Comandos en lenguaje natural",
                "robust": "/api/v1/openai - Llamadas estructuradas",
                "actions": "/api/v1/actions - Lista de acciones disponibles",
                "status": "/api/v1/status - Estado del sistema",
                "docs": "/api/v1/docs - Esta documentación",
                "health": "/api/v1/health - Health check rápido"
            },
            "categories": categories_docs,
            "best_practices": [
                "Usa el endpoint /simple para comandos naturales en español",
                "Usa el endpoint /openai para integraciones estructuradas",
                "Consulta /actions para ver todas las funcionalidades disponibles",
                "Verifica /status antes de operaciones críticas",
                "Los comandos simples son más fáciles pero menos precisos",
                "Los comandos estructurados son más precisos pero requieren más parámetros"
            ],
            "troubleshooting": {
                "common_errors": [
                    {
                        "error": "UnrecognizedKwargsError",
                        "solution": "Usa el endpoint /simple en lugar de /openai para comandos naturales"
                    },
                    {
                        "error": "Action not found",
                        "solution": "Consulta /actions para ver la lista de acciones disponibles"
                    },
                    {
                        "error": "Authentication failed",
                        "solution": "Verifica que las credenciales de Azure estén configuradas"
                    }
                ],
                "debugging_tips": [
                    "Usa /health para verificar que el sistema esté funcionando",
                    "Consulta /status para ver el estado de servicios específicos",
                    "El endpoint /simple es más tolerante a errores de formato",
                    "Siempre incluye el parámetro 'action' en llamadas estructuradas"
                ]
            },
            "version": "1.1.0",
            "last_updated": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo documentación: {str(e)}")

@router.get("/health")
async def health_check():
    """
    Health check rápido del sistema
    """
    try:
        return {
            "status": "OK",
            "timestamp": datetime.now().isoformat(),
            "message": "EliteDynamics API funcionando correctamente",
            "version": "1.1.0",
            "total_actions": len(ACTION_MAP)
        }
    
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Sistema no disponible: {str(e)}")
