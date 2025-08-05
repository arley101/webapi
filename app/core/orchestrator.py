# app/core/orchestrator.py
"""
Task 2.1: Proxy to Orchestrator with State

This module converts the simple proxy into a stateful orchestrator that can:
1. Execute workflows step by step
2. Pass context between steps
3. Handle retries and failures
4. Manage complex multi-step operations autonomously
"""

import json
import logging
import asyncio
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import uuid

from app.core.config import settings
from app.core.state_manager import state_manager
from app.core.event_bus import event_bus, EventType
from app.core.action_mapper import ACTION_MAP
from app.core.gemini_planner import gemini_planner, WorkflowDAG, DAGNode
from app.core.learning_system import learning_system

logger = logging.getLogger(__name__)

class WorkflowStatus(str, Enum):
    """Workflow execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRY = "retry"

class StepStatus(str, Enum):
    """Individual step status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRY = "retry"

@dataclass
class WorkflowStep:
    """Individual workflow step definition"""
    step_id: str
    action: str
    params: Dict[str, Any]
    depends_on: List[str] = None  # Step IDs this step depends on
    retry_count: int = 0
    max_retries: int = 3
    timeout_seconds: int = 300
    condition: Optional[str] = None  # Optional condition for execution
    
    def __post_init__(self):
        if self.depends_on is None:
            self.depends_on = []

@dataclass
class WorkflowDefinition:
    """Complete workflow definition"""
    workflow_id: str
    name: str
    description: str
    steps: List[WorkflowStep]
    created_by: Optional[str] = None
    created_at: Optional[str] = None
    timeout_minutes: int = 60
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()

class WorkflowOrchestrator:
    """Stateful workflow orchestrator that manages complex multi-step operations"""
    
    def __init__(self):
        self.running_workflows: Dict[str, str] = {}  # workflow_id -> status
        
    async def create_workflow_from_request(self, user_request: str, 
                                         workflow_name: str = "Generated Workflow",
                                         created_by: Optional[str] = None,
                                         use_learning: bool = True) -> WorkflowDefinition:
        """Create a workflow definition from a user request using Gemini DAG planner"""
        
        logger.info(f"🎯 Creating workflow from request: {user_request[:100]}...")
        
        try:
            # Phase 3: Task 3.1 - Use Gemini DAG planner
            dag = await gemini_planner.generate_dag_workflow(user_request)
            
            # Phase 3: Task 3.2 - Apply learning improvements
            if use_learning:
                improved_dag, improvements = await learning_system.improve_workflow_with_learning(
                    dag, user_request
                )
                if improvements:
                    logger.info(f"✨ Applied {len(improvements)} learning improvements")
                    dag = improved_dag
            
            # Convert DAG to WorkflowDefinition
            workflow = await self._convert_dag_to_workflow(dag, workflow_name, created_by)
            
            # Store workflow definition
            await self._store_workflow_definition(workflow)
            
            logger.info(f"✅ Created workflow {workflow.workflow_id} with {len(workflow.steps)} steps")
            return workflow
            
        except Exception as e:
            logger.error(f"❌ Failed to create workflow from request: {e}")
            # Fallback to simple plan
            return await self.create_workflow_from_plan(
                [{"action": "gemini_generate_response", "params": {"prompt": user_request}}],
                workflow_name,
                created_by
            )
    
    async def _convert_dag_to_workflow(self, dag: WorkflowDAG, workflow_name: str,
                                     created_by: Optional[str]) -> WorkflowDefinition:
        """Convert a WorkflowDAG to WorkflowDefinition"""
        
        steps = []
        for node in dag.nodes:
            step = WorkflowStep(
                step_id=node.node_id,
                action=node.action,
                params=node.params,
                depends_on=node.dependencies,
                max_retries=3,
                timeout_seconds=node.estimated_duration_seconds + 60  # Add buffer
            )
            steps.append(step)
        
        workflow = WorkflowDefinition(
            workflow_id=dag.dag_id,
            name=workflow_name or dag.name,
            description=dag.description,
            steps=steps,
            created_by=created_by,
            timeout_minutes=int(dag.estimated_total_duration_seconds / 60) + 10  # Add buffer
        )
        
        return workflow
    
    async def execute_workflow(self, workflow: WorkflowDefinition, 
                              auth_client: Any, 
                              execution_mode: bool = True,
                              original_request: str = "") -> Dict[str, Any]:
        """Execute a complete workflow"""
        
        workflow_id = workflow.workflow_id
        
        logger.info(f"🚀 Starting workflow execution: {workflow_id} ({workflow.name})")
        
        # Initialize workflow state
        execution_state = {
            "workflow_id": workflow_id,
            "workflow_name": workflow.name,
            "status": WorkflowStatus.RUNNING,
            "started_at": datetime.now().isoformat(),
            "execution_mode": execution_mode,
            "original_request": original_request,
            "total_steps": len(workflow.steps),
            "completed_steps": 0,
            "failed_steps": 0,
            "step_results": {},
            "step_states": {},
            "context": {},  # Shared context between steps
            "errors": []
        }
        
        # Store initial state
        await state_manager.create_workflow_session(workflow_id, execution_state)
        self.running_workflows[workflow_id] = WorkflowStatus.RUNNING
        
        # Emit workflow started event
        await event_bus.emit(
            EventType.WORKFLOW_STARTED,
            "orchestrator",
            {
                "workflow_id": workflow_id,
                "workflow_name": workflow.name,
                "total_steps": len(workflow.steps),
                "execution_mode": execution_mode
            }
        )
        
        try:
            # Execute steps
            for step_index, step in enumerate(workflow.steps):
                if not execution_mode:
                    # In suggestion mode, just return the plan
                    execution_state["status"] = WorkflowStatus.PENDING
                    execution_state["message"] = "Workflow plan created. Set execution=true to execute."
                    break
                
                # Check dependencies
                if not await self._check_step_dependencies(step, execution_state):
                    logger.warning(f"Step {step.step_id} dependencies not met, skipping")
                    execution_state["step_states"][step.step_id] = StepStatus.SKIPPED
                    continue
                
                # Execute step
                step_result = await self._execute_step(
                    step, auth_client, execution_state, step_index
                )
                
                # Update execution state
                execution_state["step_results"][step.step_id] = step_result
                execution_state["completed_steps"] += 1
                
                if step_result.get("success", False):
                    execution_state["step_states"][step.step_id] = StepStatus.COMPLETED
                    
                    # Update shared context with step results
                    await self._update_workflow_context(step, step_result, execution_state)
                    
                    # Emit step completed event
                    await event_bus.emit_workflow_step_completed(
                        "orchestrator",
                        workflow_id,
                        step_index,
                        step_result
                    )
                    
                else:
                    execution_state["step_states"][step.step_id] = StepStatus.FAILED
                    execution_state["failed_steps"] += 1
                    execution_state["errors"].append({
                        "step_id": step.step_id,
                        "error": step_result.get("error", "Unknown error"),
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    # Handle step failure
                    if step.retry_count < step.max_retries:
                        logger.info(f"Retrying step {step.step_id} (attempt {step.retry_count + 1})")
                        step.retry_count += 1
                        execution_state["step_states"][step.step_id] = StepStatus.RETRY
                        # Continue to retry
                    else:
                        logger.error(f"Step {step.step_id} failed after {step.max_retries} retries")
                        break
                
                # Update workflow state
                await state_manager.update_workflow_step(
                    workflow_id, step_index, step_result, WorkflowStatus.RUNNING
                )
            
            # Determine final status
            if execution_state["failed_steps"] > 0:
                final_status = WorkflowStatus.FAILED
            elif execution_mode:
                final_status = WorkflowStatus.COMPLETED
            else:
                final_status = WorkflowStatus.PENDING
                
            execution_state["status"] = final_status
            execution_state["completed_at"] = datetime.now().isoformat()
            
            # Complete workflow
            await state_manager.complete_workflow(workflow_id, execution_state)
            self.running_workflows[workflow_id] = final_status
            
            # Emit workflow completed event
            await event_bus.emit(
                EventType.WORKFLOW_COMPLETED if final_status == WorkflowStatus.COMPLETED else EventType.WORKFLOW_FAILED,
                "orchestrator",
                {
                    "workflow_id": workflow_id,
                    "final_status": final_status,
                    "total_steps": execution_state["total_steps"],
                    "completed_steps": execution_state["completed_steps"],
                    "failed_steps": execution_state["failed_steps"]
                }
            )
            
            logger.info(f"✅ Workflow {workflow_id} completed with status: {final_status}")
            
            # Phase 3: Task 3.2 - Record learning feedback
            try:
                if final_status == WorkflowStatus.COMPLETED:
                    # Record successful workflow execution for learning
                    await learning_system.record_success_feedback(
                        workflow_id=workflow_id,
                        original_request=execution_state.get("original_request", ""),
                        execution_result=execution_state,
                        performance_metrics={
                            "total_duration_seconds": (datetime.now() - datetime.fromisoformat(execution_state["started_at"])).total_seconds(),
                            "completed_steps": execution_state["completed_steps"],
                            "total_steps": execution_state["total_steps"],
                            "success_rate": execution_state["completed_steps"] / execution_state["total_steps"] if execution_state["total_steps"] > 0 else 0
                        }
                    )
                else:
                    # Record failed workflow execution for learning
                    await learning_system.record_failure_feedback(
                        workflow_id=workflow_id,
                        original_request=execution_state.get("original_request", ""),
                        error_details={
                            "final_status": final_status,
                            "errors": execution_state.get("errors", []),
                            "failed_steps": execution_state.get("failed_steps", 0)
                        },
                        execution_result=execution_state
                    )
            except Exception as learning_error:
                logger.warning(f"Failed to record learning feedback: {learning_error}")
            
            return execution_state
            
        except Exception as e:
            logger.error(f"❌ Workflow {workflow_id} failed with exception: {e}")
            
            execution_state["status"] = WorkflowStatus.FAILED
            execution_state["error"] = str(e)
            execution_state["completed_at"] = datetime.now().isoformat()
            
            await state_manager.complete_workflow(workflow_id, execution_state)
            self.running_workflows[workflow_id] = WorkflowStatus.FAILED
            
            return execution_state
    
    async def _execute_step(self, step: WorkflowStep, auth_client: Any, 
                           execution_state: Dict[str, Any], step_index: int) -> Dict[str, Any]:
        """Execute a single workflow step"""
        
        logger.info(f"🔄 Executing step {step.step_id}: {step.action}")
        
        # Emit step started event
        await event_bus.emit(
            EventType.ACTION_STARTED,
            "orchestrator",
            {
                "workflow_id": execution_state["workflow_id"],
                "step_id": step.step_id,
                "action": step.action,
                "step_index": step_index
            }
        )
        
        try:
            # Get action function
            action_function = ACTION_MAP.get(step.action)
            if not action_function:
                return {
                    "success": False,
                    "error": f"Action '{step.action}' not found in ACTION_MAP",
                    "step_id": step.step_id
                }
            
            # Prepare parameters (merge with workflow context)
            params = step.params.copy()
            
            # Substitute context variables
            params = await self._substitute_context_variables(params, execution_state["context"])
            
            # Execute action with timeout
            start_time = datetime.now()
            
            try:
                result = await asyncio.wait_for(
                    self._execute_action_async(action_function, auth_client, params),
                    timeout=step.timeout_seconds
                )
            except asyncio.TimeoutError:
                return {
                    "success": False,
                    "error": f"Step {step.step_id} timed out after {step.timeout_seconds} seconds",
                    "step_id": step.step_id
                }
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Process result
            return {
                "success": True,
                "result": result,
                "step_id": step.step_id,
                "action": step.action,
                "execution_time_seconds": execution_time,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error executing step {step.step_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "step_id": step.step_id,
                "action": step.action
            }
    
    async def _execute_action_async(self, action_function, auth_client, params) -> Any:
        """Execute action function asynchronously"""
        
        # Most action functions are synchronous, so run in thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, action_function, auth_client, params)
    
    async def _check_step_dependencies(self, step: WorkflowStep, 
                                      execution_state: Dict[str, Any]) -> bool:
        """Check if step dependencies are satisfied"""
        
        if not step.depends_on:
            return True
        
        for dep_step_id in step.depends_on:
            if dep_step_id not in execution_state["step_states"]:
                return False
            
            if execution_state["step_states"][dep_step_id] != StepStatus.COMPLETED:
                return False
        
        return True
    
    async def _update_workflow_context(self, step: WorkflowStep, step_result: Dict[str, Any],
                                      execution_state: Dict[str, Any]) -> None:
        """Update workflow context with step results"""
        
        try:
            # Extract useful data from step result
            result_data = step_result.get("result", {})
            
            # Store step-specific context
            context_key = f"{step.step_id}_result"
            execution_state["context"][context_key] = result_data
            
            # Extract common patterns (file IDs, URLs, etc.)
            if isinstance(result_data, dict):
                # File operations
                if "id" in result_data and step.action.startswith(("onedrive_", "sharepoint_")):
                    execution_state["context"]["last_file_id"] = result_data["id"]
                    execution_state["context"]["last_file_url"] = result_data.get("webUrl", "")
                
                # Contact operations
                if "id" in result_data and step.action.startswith("hubspot_"):
                    execution_state["context"]["last_contact_id"] = result_data["id"]
                
            logger.debug(f"Updated workflow context after step {step.step_id}")
            
        except Exception as e:
            logger.warning(f"Failed to update workflow context for step {step.step_id}: {e}")
    
    async def _substitute_context_variables(self, params: Dict[str, Any], 
                                           context: Dict[str, Any]) -> Dict[str, Any]:
        """Substitute context variables in parameters"""
        
        try:
            # Convert params to JSON string, substitute variables, and parse back
            params_str = json.dumps(params)
            
            # Simple variable substitution
            for key, value in context.items():
                placeholder = f"${{{key}}}"
                if placeholder in params_str:
                    params_str = params_str.replace(placeholder, str(value))
            
            return json.loads(params_str)
            
        except Exception as e:
            logger.warning(f"Failed to substitute context variables: {e}")
            return params
    
    async def _store_workflow_definition(self, workflow: WorkflowDefinition) -> None:
        """Store workflow definition in state manager"""
        
        workflow_data = {
            "workflow_id": workflow.workflow_id,
            "name": workflow.name,
            "description": workflow.description,
            "steps": [
                {
                    "step_id": step.step_id,
                    "action": step.action,
                    "params": step.params,
                    "depends_on": step.depends_on,
                    "max_retries": step.max_retries,
                    "timeout_seconds": step.timeout_seconds
                }
                for step in workflow.steps
            ],
            "created_by": workflow.created_by,
            "created_at": workflow.created_at,
            "timeout_minutes": workflow.timeout_minutes
        }
        
        await state_manager.set_state(
            f"workflow_def:{workflow.workflow_id}",
            workflow_data,
            ttl_seconds=86400  # 24 hours
        )
    
    async def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get current workflow status"""
        
        return await state_manager.get_workflow_state(workflow_id)
    
    async def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel a running workflow"""
        
        if workflow_id in self.running_workflows:
            self.running_workflows[workflow_id] = WorkflowStatus.CANCELLED
            
            # Update state
            workflow_state = await state_manager.get_workflow_state(workflow_id)
            if workflow_state:
                workflow_state["status"] = WorkflowStatus.CANCELLED
                workflow_state["cancelled_at"] = datetime.now().isoformat()
                await state_manager.set_state(f"workflow:{workflow_id}", workflow_state)
            
            logger.info(f"Workflow {workflow_id} cancelled")
            return True
        
        return False
    
    async def list_active_workflows(self) -> List[Dict[str, Any]]:
        """List all active workflows"""
        
        active_workflows = []
        
        for workflow_id, status in self.running_workflows.items():
            if status in [WorkflowStatus.RUNNING, WorkflowStatus.PENDING]:
                workflow_state = await state_manager.get_workflow_state(workflow_id)
                if workflow_state:
                    active_workflows.append(workflow_state)
        
        return active_workflows


# Global orchestrator instance
orchestrator = WorkflowOrchestrator()

# Convenience functions
async def execute_plan_as_workflow(plan: List[Dict[str, Any]], auth_client: Any,
                                  execution_mode: bool = True, workflow_name: str = "Generated Workflow") -> Dict[str, Any]:
    """Execute a plan as a workflow"""
    
    workflow = await orchestrator.create_workflow_from_plan(plan, workflow_name)
    return await orchestrator.execute_workflow(workflow, auth_client, execution_mode)

async def create_simple_workflow(actions: List[Tuple[str, Dict[str, Any]]], 
                                workflow_name: str = "Simple Workflow") -> WorkflowDefinition:
    """Create a simple sequential workflow"""
    
    steps = []
    for i, (action, params) in enumerate(actions):
        step = WorkflowStep(
            step_id=f"step_{i+1}",
            action=action,
            params=params,
            depends_on=[f"step_{i}"] if i > 0 else []
        )
        steps.append(step)
    
    workflow_id = f"wf_{uuid.uuid4().hex[:8]}"
    workflow = WorkflowDefinition(
        workflow_id=workflow_id,
        name=workflow_name,
        description=f"Simple workflow with {len(steps)} sequential steps",
        steps=steps
    )
    
    await orchestrator._store_workflow_definition(workflow)
    return workflow

# Phase 3: Enhanced convenience functions
async def create_intelligent_workflow(user_request: str, auth_client: Any,
                                     execution_mode: bool = True,
                                     workflow_name: str = "AI Generated Workflow") -> Dict[str, Any]:
    """Create and execute an intelligent workflow from user request using Gemini and learning"""
    
    workflow = await orchestrator.create_workflow_from_request(user_request, workflow_name)
    return await orchestrator.execute_workflow(workflow, auth_client, execution_mode, user_request)

async def get_workflow_suggestions(user_request: str) -> Dict[str, Any]:
    """Get intelligent suggestions for a user request"""
    
    try:
        # Get learning suggestions
        learning_suggestions = await learning_system.get_learning_suggestions(user_request)
        
        # Generate new DAG suggestion
        dag = await gemini_planner.generate_dag_workflow(user_request)
        
        return {
            "status": "success",
            "user_request": user_request,
            "learning_suggestions": learning_suggestions,
            "suggested_workflow": {
                "dag_id": dag.dag_id,
                "name": dag.name,
                "description": dag.description,
                "estimated_duration_seconds": dag.estimated_total_duration_seconds,
                "total_steps": len(dag.nodes),
                "parallel_groups": len(dag.parallel_groups),
                "actions_involved": [node.action for node in dag.nodes]
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get workflow suggestions: {e}")
        return {
            "status": "error",
            "error": str(e),
            "user_request": user_request
        }