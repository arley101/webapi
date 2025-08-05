# app/api/routes/ai_workflows.py
"""
Enhanced AI-powered workflow endpoints for Phase 3
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.core.orchestrator import create_intelligent_workflow, get_workflow_suggestions, orchestrator
from app.core.gemini_planner import gemini_planner, analyze_user_intent
from app.core.learning_system import (
    learning_system, 
    record_user_workflow_correction,
    get_learning_suggestions_for_request
)
from app.core.state_manager import state_manager
from app.shared.helpers.http_client import AuthenticatedHttpClient
from azure.identity import DefaultAzureCredential

logger = logging.getLogger(__name__)
router = APIRouter()

class AIWorkflowRequest(BaseModel):
    """Request for AI-powered workflow generation"""
    request: str = Field(..., description="Natural language description of what you want to accomplish")
    execution_mode: bool = Field(default=False, description="Whether to execute immediately or just plan")
    workflow_name: Optional[str] = Field(default=None, description="Custom name for the workflow")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context information")
    user_id: Optional[str] = Field(default=None, description="User ID for personalization")

class WorkflowCorrectionRequest(BaseModel):
    """Request for recording user corrections to workflows"""
    workflow_id: str = Field(..., description="ID of the workflow that was corrected")
    original_request: str = Field(..., description="Original user request")
    original_plan: Dict[str, Any] = Field(..., description="Original workflow plan")
    corrected_plan: Dict[str, Any] = Field(..., description="User-corrected workflow plan")
    correction_reason: Optional[str] = Field(default=None, description="Reason for the correction")

@router.post(
    "/ai-workflow",
    summary="Create and optionally execute an AI-powered workflow",
    description="Generate an intelligent workflow from natural language using Gemini AI and learning system. "
                "Can create complex DAG workflows with parallel execution and learned optimizations.",
    responses={
        200: {"description": "Workflow created/executed successfully"},
        400: {"description": "Invalid request"},
        500: {"description": "Internal server error"}
    }
)
async def create_ai_workflow(
    request: Request,
    ai_request: AIWorkflowRequest,
    background_tasks: BackgroundTasks
):
    """Create and optionally execute an AI-powered workflow"""
    
    logger.info(f"🧠 AI Workflow request: {ai_request.request[:100]}...")
    
    try:
        # Setup authentication
        credential = DefaultAzureCredential()
        auth_client = AuthenticatedHttpClient(credential=credential)
        
        # Generate workflow name if not provided
        workflow_name = ai_request.workflow_name or f"AI Workflow {ai_request.request[:50]}..."
        
        # Create and execute intelligent workflow
        result = await create_intelligent_workflow(
            user_request=ai_request.request,
            auth_client=auth_client,
            execution_mode=ai_request.execution_mode,
            workflow_name=workflow_name
        )
        
        # Add metadata
        result["ai_features"] = {
            "gemini_planning": True,
            "learning_optimization": True,
            "dag_execution": True,
            "parallel_processing": True
        }
        
        result["request_metadata"] = {
            "original_request": ai_request.request,
            "execution_mode": ai_request.execution_mode,
            "user_id": ai_request.user_id
        }
        
        return JSONResponse(content=result, status_code=200)
        
    except Exception as e:
        logger.error(f"❌ AI Workflow failed: {e}")
        return JSONResponse(
            content={
                "status": "error",
                "message": "Failed to create AI workflow",
                "error": str(e),
                "request": ai_request.request
            },
            status_code=500
        )

@router.post(
    "/workflow-suggestions",
    summary="Get intelligent workflow suggestions",
    description="Get AI-powered suggestions for accomplishing a task, including learned patterns "
                "and optimized approaches from previous successful workflows.",
    responses={
        200: {"description": "Suggestions generated successfully"},
        400: {"description": "Invalid request"},
        500: {"description": "Internal server error"}
    }
)
async def get_workflow_suggestions_endpoint(
    request: Request,
    ai_request: AIWorkflowRequest
):
    """Get intelligent workflow suggestions without execution"""
    
    logger.info(f"💡 Workflow suggestions for: {ai_request.request[:100]}...")
    
    try:
        # Get intelligent suggestions
        suggestions = await get_workflow_suggestions(ai_request.request)
        
        # Get learning-based suggestions
        learning_suggestions = await get_learning_suggestions_for_request(ai_request.request)
        
        # Analyze user intent
        intent_analysis = await analyze_user_intent(ai_request.request)
        
        result = {
            "status": "success",
            "user_request": ai_request.request,
            "intent_analysis": intent_analysis,
            "workflow_suggestions": suggestions,
            "learning_suggestions": learning_suggestions,
            "ai_capabilities": {
                "can_create_dag": True,
                "can_parallel_execute": True,
                "has_learned_patterns": len(learning_suggestions) > 0,
                "confidence_score": max([s.get("confidence", 0) for s in learning_suggestions] + [0.5])
            }
        }
        
        return JSONResponse(content=result, status_code=200)
        
    except Exception as e:
        logger.error(f"❌ Failed to get workflow suggestions: {e}")
        return JSONResponse(
            content={
                "status": "error",
                "message": "Failed to generate suggestions",
                "error": str(e),
                "request": ai_request.request
            },
            status_code=500
        )

@router.post(
    "/workflow-correction",
    summary="Record user correction to improve learning",
    description="Record when a user corrects or improves a workflow suggestion. "
                "This helps the AI learn better approaches for similar requests in the future.",
    responses={
        200: {"description": "Correction recorded successfully"},
        400: {"description": "Invalid request"},
        500: {"description": "Internal server error"}
    }
)
async def record_workflow_correction(
    request: Request,
    correction: WorkflowCorrectionRequest
):
    """Record user correction to improve future suggestions"""
    
    logger.info(f"📝 Recording workflow correction for: {correction.workflow_id}")
    
    try:
        # Record the correction for learning
        feedback_id = await record_user_workflow_correction(
            workflow_id=correction.workflow_id,
            original_request=correction.original_request,
            original_plan=correction.original_plan,
            corrected_plan=correction.corrected_plan
        )
        
        result = {
            "status": "success",
            "message": "Workflow correction recorded successfully",
            "feedback_id": feedback_id,
            "workflow_id": correction.workflow_id,
            "learning_impact": {
                "will_improve_future_suggestions": True,
                "pattern_confidence_increase": 0.1,
                "applies_to_similar_requests": True
            }
        }
        
        return JSONResponse(content=result, status_code=200)
        
    except Exception as e:
        logger.error(f"❌ Failed to record workflow correction: {e}")
        return JSONResponse(
            content={
                "status": "error", 
                "message": "Failed to record correction",
                "error": str(e),
                "workflow_id": correction.workflow_id
            },
            status_code=500
        )

@router.get(
    "/learning-metrics",
    summary="Get learning system metrics",
    description="Get metrics about the learning system performance, patterns learned, "
                "and improvement statistics.",
    responses={
        200: {"description": "Metrics retrieved successfully"},
        500: {"description": "Internal server error"}
    }
)
async def get_learning_metrics():
    """Get learning system metrics"""
    
    try:
        metrics = await learning_system.get_learning_metrics()
        
        # Add additional system metrics
        system_metrics = {
            "ai_components": {
                "gemini_planner": "active",
                "learning_system": "active",
                "state_manager": "active",
                "event_bus": "active"
            },
            "capabilities": {
                "dag_generation": True,
                "parallel_execution": True,
                "learning_optimization": True,
                "user_feedback_integration": True
            }
        }
        
        result = {
            "status": "success",
            "learning_metrics": metrics,
            "system_metrics": system_metrics,
            "timestamp": "2025-08-05T06:47:18.000Z"
        }
        
        return JSONResponse(content=result, status_code=200)
        
    except Exception as e:
        logger.error(f"❌ Failed to get learning metrics: {e}")
        return JSONResponse(
            content={
                "status": "error",
                "message": "Failed to retrieve metrics",
                "error": str(e)
            },
            status_code=500
        )

@router.get(
    "/workflow-status/{workflow_id}",
    summary="Get workflow execution status",
    description="Get detailed status of a running or completed workflow, including step progress "
                "and performance metrics.",
    responses={
        200: {"description": "Status retrieved successfully"},
        404: {"description": "Workflow not found"},
        500: {"description": "Internal server error"}
    }
)
async def get_workflow_status(workflow_id: str):
    """Get workflow execution status"""
    
    try:
        status = await orchestrator.get_workflow_status(workflow_id)
        
        if not status:
            return JSONResponse(
                content={
                    "status": "error",
                    "message": "Workflow not found",
                    "workflow_id": workflow_id
                },
                status_code=404
            )
        
        return JSONResponse(content=status, status_code=200)
        
    except Exception as e:
        logger.error(f"❌ Failed to get workflow status: {e}")
        return JSONResponse(
            content={
                "status": "error",
                "message": "Failed to retrieve workflow status",
                "error": str(e),
                "workflow_id": workflow_id
            },
            status_code=500
        )