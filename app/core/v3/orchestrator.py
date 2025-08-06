import json
import asyncio
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
from app.core.config import settings
from app.core.v3.state_manager import state_manager
from app.core.v3.event_bus import event_bus
from app.core.v3.audit_manager import audit_manager
try:
    from app.core.action_mapper import ACTION_MAP
except ImportError as e:
    logging.getLogger(__name__).error(
        f"Failed to import ACTION_MAP: {e}. Action execution will be disabled as a result."
    )
    raise
from app.core.auth_manager import get_auth_client

logger = logging.getLogger(__name__)

class AutonomousOrchestrator:
    """
    Orquestador principal que reemplaza al Proxy de Vercel
    Ejecuta workflows complejos de forma autónoma
    """
    
    def __init__(self):
        self.state_manager = state_manager
        self.event_bus = event_bus
        self.audit_manager = audit_manager
        self.action_map = ACTION_MAP
        self.auth_client = None
        
    async def initialize(self):
        """Inicializa el orquestador"""
        try:
            self.auth_client = get_auth_client()
            await self.state_manager.start_cleanup_task()
            logger.info("Orquestador inicializado correctamente")
        except Exception as e:
            logger.error(f"Error inicializando orquestador: {e}")
            raise
    
    async def execute_natural_language(
        self, 
        prompt: str, 
        mode: str = "execution",  # "execution" o "suggestion"
        user_id: str = "system",
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Punto de entrada principal - recibe lenguaje natural y ejecuta
        """
        workflow_id = str(uuid.uuid4())
        start_time = datetime.utcnow()
        
        # Emitir evento de inicio
        await self.event_bus.emit(
            "workflow.started",
            "orchestrator",
            {
                "workflow_id": workflow_id,
                "prompt": prompt,
                "user_id": user_id,
                "mode": mode
            }
        )
        
        # Iniciar auditoría
        await self.audit_manager.log_execution_start(
            workflow_id, prompt, user_id, {"mode": mode, "context": context}
        )
        
        try:
            # 1. Analizar con Gemini para generar plan
            plan = await self._generate_execution_plan(prompt, context)
            
            # 2. Guardar estado inicial
            await self.state_manager.set_workflow_state(workflow_id, {
                "prompt": prompt,
                "plan": plan,
                "status": "planning",
                "user_id": user_id,
                "context": context
            })
            
            # 3. Ejecutar o sugerir según el modo
            if mode == "execution":
                result = await self._execute_plan(plan, workflow_id)
                final_status = "completed"
            else:
                result = {
                    "status": "suggested",
                    "plan": plan,
                    "message": "Plan generado pero no ejecutado (mode=suggestion)"
                }
                final_status = "suggested"
            
            # 4. Actualizar estado final
            await self.state_manager.set_workflow_state(workflow_id, {
                "prompt": prompt,
                "plan": plan,
                "status": final_status,
                "result": result,
                "user_id": user_id,
                "completed_at": datetime.utcnow().isoformat()
            })
            
            # 5. Completar auditoría
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            await self.audit_manager.log_execution_complete(
                workflow_id, result, duration_ms
            )
            
            # 6. Emitir evento de finalización
            await self.event_bus.emit(
                "workflow.completed",
                "orchestrator",
                {
                    "workflow_id": workflow_id,
                    "status": final_status,
                    "duration_ms": duration_ms
                }
            )
            
            return {
                "status": "success",
                "workflow_id": workflow_id,
                "mode": mode,
                "data": result,
                "duration_ms": duration_ms
            }
            
        except Exception as e:
            logger.error(f"Error en workflow {workflow_id}: {str(e)}")
            
            # Registrar error
            await self.audit_manager.log_execution_error(
                workflow_id, str(e), getattr(e, "__traceback__", None)
            )
            
            # Emitir evento de error
            await self.event_bus.emit(
                "workflow.failed",
                "orchestrator",
                {
                    "workflow_id": workflow_id,
                    "error": str(e)
                }
            )
            
            return {
                "status": "error",
                "workflow_id": workflow_id,
                "error": str(e),
                "message": "Error ejecutando workflow"
            }
    
    async def _generate_execution_plan(self, prompt: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Genera un plan de ejecución usando Gemini"""
        try:
            # Usar la acción de Gemini para generar el plan
            from app.actions import gemini_actions
            
            gemini_prompt = f"""
            Genera un plan de ejecución para: "{prompt}"
            
            Contexto disponible: {json.dumps(context or {}, indent=2)}
            
            Acciones disponibles: {list(self.action_map.keys())}
            
            Devuelve un JSON con la estructura:
            {{
                "steps": [
                    {{
                        "step_id": "1",
                        "action": "nombre_de_accion",
                        "params": {{}},
                        "description": "Descripción del paso",
                        "depends_on": []
                    }}
                ],
                "summary": "Resumen del plan"
            }}
            """

            result = await gemini_actions.generate_execution_plan(self.auth_client, {
                "prompt": gemini_prompt,
                "temperature": 0.2,
                "max_tokens": 2000
            })
            
            if result.get("status") == "success":
                return result.get("data", {}).get("plan", {})
            else:
                # Plan de fallback simple
                return {
                    "steps": [{
                        "step_id": "1",
                        "action": "gemini_suggest_action",
                        "params": {"query": prompt},
                        "description": "Analizar solicitud con Gemini"
                    }],
                    "summary": "Plan de fallback"
                }
                
        except Exception as e:
            logger.error(f"Error generando plan: {e}")
            raise
    
    async def _execute_plan(self, plan: Dict[str, Any], workflow_id: str) -> Dict[str, Any]:
        """Ejecuta un plan paso a paso"""
        results = {}
        steps = plan.get("steps", [])
        context = {"workflow_id": workflow_id}
        
        logger.info(f"Ejecutando plan con {len(steps)} pasos")
        
        for i, step in enumerate(steps):
            step_id = step.get("step_id", str(i))
            action_name = step.get("action")
            params = step.get("params", {})
            
            try:
                # Resolver parámetros dinámicos
                resolved_params = self._resolve_params(params, context, results)
                
                # Log del paso
                await self.audit_manager.log_execution_step(
                    workflow_id, 
                    f"Step {step_id}: {action_name}",
                    "started"
                )
                
                # Ejecutar acción
                if action_name in self.action_map:
                    logger.info(f"Ejecutando paso {step_id}: {action_name}")
                    
                    action_func = self.action_map[action_name]
                    result = await self._execute_action(action_func, resolved_params)
                    
                    results[step_id] = result
                    
                    # Actualizar contexto con resultado
                    if result.get("status") == "success" and result.get("data"):
                        context[f"step_{step_id}_result"] = result["data"]
                    
                    # Log éxito del paso
                    await self.audit_manager.log_execution_step(
                        workflow_id,
                        f"Step {step_id}: {action_name}",
                        "completed",
                        {"result": result}
                    )
                    
                    # Emitir evento
                    await self.event_bus.emit(
                        "step.completed",
                        "orchestrator",
                        {
                            "workflow_id": workflow_id,
                            "step_id": step_id,
                            "action": action_name,
                            "success": result.get("status") == "success"
                        }
                    )
                else:
                    logger.warning(f"Acción no encontrada: {action_name}")
                    results[step_id] = {
                        "status": "error",
                        "error": f"Acción no encontrada: {action_name}"
                    }
                    
            except Exception as e:
                logger.error(f"Error en paso {step_id}: {e}")
                results[step_id] = {
                    "status": "error",
                    "error": str(e)
                }
                
                # Decidir si continuar o abortar
                if step.get("critical", False):
                    break
        
        return {
            "status": "success" if all(r.get("status") == "success" for r in results.values()) else "partial",
            "steps_executed": len(results),
            "results": results,
            "summary": plan.get("summary", "Plan ejecutado")
        }
    
    async def _execute_action(self, action_func: callable, params: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecuta una acción con manejo de errores"""
        try:
            # Si es una coroutine
            if asyncio.iscoroutinefunction(action_func):
                result = await action_func(self.auth_client, params)
            else:
                # Si es síncrona, ejecutar en thread pool
                result = await asyncio.get_running_loop().run_in_executor(
                    None, action_func, self.auth_client, params
                )
            
            return result
        except Exception as e:
            logger.error(f"Error ejecutando acción: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _resolve_params(self, params: Dict[str, Any], context: Dict[str, Any], results: Dict[str, Any]) -> Dict[str, Any]:
        """Resuelve parámetros dinámicos usando contexto y resultados previos"""
        resolved = {}
        
        for key, value in params.items():
            if isinstance(value, str) and value.startswith("{{") and value.endswith("}}"):
                # Es una referencia dinámica
                ref = value[2:-2].strip()
                
                # Buscar en resultados previos
                if ref.startswith("step_") and "_" in ref:
                    parts = ref.split(".")
                    step_ref = parts[0]
                    
                    if step_ref in results and len(parts) > 1:
                        # Navegar por el resultado
                        nav_value = results[step_ref]
                        for part in parts[1:]:
                            if isinstance(nav_value, dict):
                                nav_value = nav_value.get(part)
                            else:
                                nav_value = None
                                break
                        resolved[key] = nav_value
                    else:
                        resolved[key] = None
                        
                # Buscar en contexto
                elif ref in context:
                    resolved[key] = context[ref]
                else:
                    resolved[key] = None
                    
            elif isinstance(value, dict):
                # Recursión para objetos anidados
                resolved[key] = self._resolve_params(value, context, results)
            else:
                resolved[key] = value
                
        return resolved

# Instancia global (se inicializará en main.py)
orchestrator = AutonomousOrchestrator()
