# app/api/routes/debug_info.py
"""
Router temporal para diagnosticar problemas de deployment en Azure
"""

import logging
import sys
import os
from datetime import datetime
from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/debug/system", tags=["Debug"])
async def debug_system_info():
    """Endpoint para diagnosticar el estado del sistema en Azure"""
    
    debug_info = {
        "timestamp": datetime.now().isoformat(),
        "python_version": sys.version,
        "python_path": sys.path[:5],  # Solo primeros 5 para no saturar
        "current_directory": os.getcwd(),
        "environment_variables": {
            key: "***" if "key" in key.lower() or "secret" in key.lower() or "password" in key.lower()
            else value[:100]  # Truncar valores largos
            for key, value in os.environ.items() 
            if key.startswith(('AZURE_', 'GOOGLE_', 'META_', 'APP_', 'PYTHON', 'LOG_'))
        },
        "imports_status": {}
    }
    
    # Probar imports críticos
    imports_to_test = [
        "app.core.config",
        "app.core.action_mapper", 
        "app.core.auth_manager",
        "app.api.routes.unified_assistant",
        "app.api.routes.dynamics_actions",
        "app.memory.intelligent_assistant"
    ]
    
    for module_name in imports_to_test:
        try:
            __import__(module_name)
            debug_info["imports_status"][module_name] = "OK"
        except Exception as e:
            debug_info["imports_status"][module_name] = f"ERROR: {str(e)}"
    
    # Probar ACTION_MAP específicamente
    try:
        from app.core.action_mapper import ACTION_MAP
        debug_info["action_map_status"] = {
            "loaded": True,
            "total_actions": len(ACTION_MAP),
            "first_5_actions": list(ACTION_MAP.keys())[:5]
        }
    except Exception as e:
        debug_info["action_map_status"] = {
            "loaded": False,
            "error": str(e)
        }
    
    # Verificar archivos críticos
    files_to_check = [
        "app/main.py",
        "app/core/action_mapper.py",
        "app/api/routes/unified_assistant.py",
        "requirements.txt",
        "runtime.txt"
    ]
    
    debug_info["files_status"] = {}
    for file_path in files_to_check:
        full_path = os.path.join(os.getcwd(), file_path)
        debug_info["files_status"][file_path] = {
            "exists": os.path.exists(full_path),
            "size": os.path.getsize(full_path) if os.path.exists(full_path) else 0
        }
    
    return debug_info

@router.get("/debug/requirements", tags=["Debug"])
async def debug_requirements():
    """Verificar qué paquetes están instalados"""
    
    import subprocess
    
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "list"], 
            capture_output=True, 
            text=True, 
            timeout=10
        )
        
        if result.returncode == 0:
            # Parsear la salida para obtener solo paquetes relevantes
            lines = result.stdout.split('\n')
            packages = {}
            for line in lines[2:]:  # Saltar headers
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 2:
                        packages[parts[0]] = parts[1]
            
            # Filtrar solo paquetes importantes
            important_packages = [
                'fastapi', 'uvicorn', 'gunicorn', 'pydantic', 
                'requests', 'python-multipart', 'python-jose',
                'passlib', 'bcrypt', 'azure-identity', 'google-auth'
            ]
            
            filtered_packages = {
                pkg: version for pkg, version in packages.items() 
                if any(important in pkg.lower() for important in important_packages)
            }
            
            return {
                "status": "success",
                "total_packages": len(packages),
                "important_packages": filtered_packages,
                "all_packages_count": len(packages)
            }
        else:
            return {
                "status": "error",
                "error": result.stderr,
                "returncode": result.returncode
            }
            
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

@router.get("/debug/action-map", tags=["Debug"])
async def debug_action_map():
    """Diagnosticar específicamente el ACTION_MAP"""
    
    try:
        from app.core.action_mapper import ACTION_MAP, get_action_function
        
        # Probar cargar algunas acciones
        test_results = {}
        test_actions = ["gmail_oauth", "teams_oauth", "google_search", "openai_chat"]
        
        for action_name in test_actions:
            if action_name in ACTION_MAP:
                try:
                    func = get_action_function(action_name)
                    test_results[action_name] = "LOADED_OK"
                except Exception as e:
                    test_results[action_name] = f"LOAD_ERROR: {str(e)}"
            else:
                test_results[action_name] = "NOT_FOUND"
        
        return {
            "status": "success",
            "total_actions": len(ACTION_MAP),
            "sample_actions": list(ACTION_MAP.keys())[:10],
            "test_results": test_results,
            "action_categories": {
                category: [name for name in ACTION_MAP.keys() if name.startswith(category)][:3]
                for category in ["gmail_", "teams_", "google_", "openai_", "meta_", "linkedin_"]
            }
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "traceback": str(e.__traceback__)
        }