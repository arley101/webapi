# app/core/gemini_planner.py
"""
Task 3.1: Integrate Gemini as DAG Planner

This module enhances Gemini integration to generate Directed Acyclic Graphs (DAGs)
for workflow execution, enabling parallel execution of non-dependent tasks and
sophisticated workflow planning.
"""

import json
import logging
import re
from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime
from dataclasses import dataclass
import requests

from app.core.config import settings
from app.core.action_mapper import ACTION_MAP
from app.core.state_manager import state_manager
from app.core.event_bus import event_bus, EventType

logger = logging.getLogger(__name__)

@dataclass
class DAGNode:
    """Represents a node in the workflow DAG"""
    node_id: str
    action: str
    params: Dict[str, Any]
    dependencies: List[str] = None
    parallel_group: Optional[str] = None
    estimated_duration_seconds: int = 60
    priority: int = 1  # 1 = high, 5 = low
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []

@dataclass
class WorkflowDAG:
    """Represents a complete workflow as a DAG"""
    dag_id: str
    name: str
    description: str
    nodes: List[DAGNode]
    created_at: str
    estimated_total_duration_seconds: int = 0
    parallel_groups: Dict[str, List[str]] = None
    
    def __post_init__(self):
        if self.parallel_groups is None:
            self.parallel_groups = {}

class GeminiDAGPlanner:
    """Enhanced Gemini integration for DAG-based workflow planning"""
    
    def __init__(self):
        self.model = settings.GEMINI_MODEL
        self.api_key = settings.GEMINI_API_KEY
        self.api_base = "https://generativelanguage.googleapis.com/v1"
        
    def _get_api_url(self) -> str:
        """Get Gemini API URL"""
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not configured")
        return f"{self.api_base}/models/{self.model}:generateContent?key={self.api_key}"
    
    async def generate_dag_workflow(self, user_request: str, 
                                   context: Optional[Dict[str, Any]] = None) -> WorkflowDAG:
        """Generate a DAG-based workflow from user request"""
        
        logger.info(f"🧠 Generating DAG workflow for request: {user_request[:100]}...")
        
        # Build enhanced prompt for DAG generation
        prompt = self._build_dag_prompt(user_request, context)
        
        try:
            # Get Gemini response
            response = await self._make_gemini_request(prompt)
            
            # Parse response into DAG
            dag = await self._parse_gemini_response_to_dag(response, user_request)
            
            # Validate and optimize DAG
            validated_dag = await self._validate_and_optimize_dag(dag)
            
            # Store DAG for learning
            await self._store_dag_for_learning(user_request, validated_dag)
            
            logger.info(f"✅ Generated DAG with {len(validated_dag.nodes)} nodes and {len(validated_dag.parallel_groups)} parallel groups")
            
            return validated_dag
            
        except Exception as e:
            logger.error(f"❌ Failed to generate DAG workflow: {e}")
            # Fallback to simple sequential workflow
            return await self._create_fallback_workflow(user_request, context)
    
    def _build_dag_prompt(self, user_request: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Build enhanced prompt for DAG generation"""
        
        # Get available actions summary
        action_categories = self._get_action_categories_summary()
        
        # Build context information
        context_info = ""
        if context:
            context_info = f"\nCurrent context:\n{json.dumps(context, indent=2)}\n"
        
        prompt = f"""
You are an expert workflow planner for the EliteDynamicsAPI system. Your task is to create a Directed Acyclic Graph (DAG) workflow plan that can execute tasks in parallel when possible.

USER REQUEST: {user_request}
{context_info}
AVAILABLE ACTION CATEGORIES:
{action_categories}

IMPORTANT INSTRUCTIONS:
1. Generate a workflow as a JSON DAG structure
2. Identify tasks that can run in parallel (no dependencies between them)
3. Use actual action names from the available categories
4. Include realistic parameter structures
5. Estimate execution time for each step
6. Group parallel tasks with parallel_group identifiers
7. Ensure dependencies are correctly specified

RESPONSE FORMAT (JSON only):
{{
    "dag_id": "generated_dag_id",
    "name": "Workflow Name",
    "description": "Brief description of what this workflow accomplishes",
    "nodes": [
        {{
            "node_id": "step_1",
            "action": "action_name",
            "params": {{"param1": "value1"}},
            "dependencies": [],
            "parallel_group": null,
            "estimated_duration_seconds": 30,
            "priority": 1
        }},
        {{
            "node_id": "step_2a",
            "action": "action_name_2",
            "params": {{"param1": "value1"}},
            "dependencies": ["step_1"],
            "parallel_group": "group_1",
            "estimated_duration_seconds": 45,
            "priority": 1
        }},
        {{
            "node_id": "step_2b",
            "action": "action_name_3",
            "params": {{"param1": "value1"}},
            "dependencies": ["step_1"],
            "parallel_group": "group_1",
            "estimated_duration_seconds": 60,
            "priority": 2
        }}
    ]
}}

Focus on creating efficient parallel execution paths while maintaining logical dependencies.
Return ONLY the JSON structure, no explanations.
"""
        
        return prompt
    
    def _get_action_categories_summary(self) -> str:
        """Get a summary of available action categories"""
        
        categories = {
            "SharePoint": ["sharepoint_upload_document", "sharepoint_list_files", "sharepoint_create_folder"],
            "OneDrive": ["onedrive_upload_file", "onedrive_list_items", "onedrive_get_sharing_link"],
            "HubSpot": ["hubspot_create_contact", "hubspot_get_contacts", "hubspot_create_deal"],
            "Notion": ["notion_create_page", "notion_query_database", "notion_update_page"],
            "Google Ads": ["googleads_get_campaigns", "googleads_create_campaign", "googleads_get_performance"],
            "Meta Ads": ["metaads_get_campaigns", "metaads_create_ad", "metaads_get_insights"],
            "Email": ["correo_send_email", "correo_list_messages", "correo_create_rule"],
            "Calendar": ["calendario_create_event", "calendario_list_events", "calendario_update_event"],
            "Teams": ["teams_send_message", "teams_create_channel", "teams_list_members"],
            "Power BI": ["powerbi_get_reports", "powerbi_refresh_dataset", "powerbi_export_report"],
            "YouTube": ["youtube_upload_video", "youtube_get_analytics", "youtube_update_video"],
            "WordPress": ["wp_create_post", "wp_get_posts", "wp_update_post"],
            "Web Research": ["webresearch_search_google", "webresearch_extract_content", "webresearch_analyze_page"]
        }
        
        summary = []
        for category, actions in categories.items():
            summary.append(f"{category}: {', '.join(actions[:3])}...")
        
        return "\n".join(summary)
    
    async def _make_gemini_request(self, prompt: str) -> Dict[str, Any]:
        """Make request to Gemini API"""
        
        url = self._get_api_url()
        
        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "temperature": 0.3,  # Lower temperature for more consistent structured output
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 8192
            }
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        
        return response.json()
    
    async def _parse_gemini_response_to_dag(self, response: Dict[str, Any], 
                                           original_request: str) -> WorkflowDAG:
        """Parse Gemini response into WorkflowDAG"""
        
        try:
            # Extract text from Gemini response
            content = response.get("candidates", [{}])[0].get("content", {})
            text = content.get("parts", [{}])[0].get("text", "")
            
            # Clean up the JSON (remove markdown formatting if present)
            json_text = re.sub(r'```json\s*|\s*```', '', text.strip())
            
            # Parse JSON
            dag_data = json.loads(json_text)
            
            # Create DAG nodes
            nodes = []
            for node_data in dag_data.get("nodes", []):
                node = DAGNode(
                    node_id=node_data.get("node_id", f"step_{len(nodes) + 1}"),
                    action=node_data.get("action", "unknown"),
                    params=node_data.get("params", {}),
                    dependencies=node_data.get("dependencies", []),
                    parallel_group=node_data.get("parallel_group"),
                    estimated_duration_seconds=node_data.get("estimated_duration_seconds", 60),
                    priority=node_data.get("priority", 1)
                )
                nodes.append(node)
            
            # Build parallel groups mapping
            parallel_groups = {}
            for node in nodes:
                if node.parallel_group:
                    if node.parallel_group not in parallel_groups:
                        parallel_groups[node.parallel_group] = []
                    parallel_groups[node.parallel_group].append(node.node_id)
            
            # Calculate estimated total duration
            estimated_duration = self._calculate_dag_duration(nodes, parallel_groups)
            
            dag = WorkflowDAG(
                dag_id=dag_data.get("dag_id", f"dag_{datetime.now().strftime('%Y%m%d_%H%M%S')}"),
                name=dag_data.get("name", "Generated Workflow"),
                description=dag_data.get("description", f"Workflow for: {original_request[:100]}"),
                nodes=nodes,
                created_at=datetime.now().isoformat(),
                estimated_total_duration_seconds=estimated_duration,
                parallel_groups=parallel_groups
            )
            
            return dag
            
        except Exception as e:
            logger.error(f"Failed to parse Gemini response to DAG: {e}")
            raise ValueError(f"Invalid DAG structure in Gemini response: {e}")
    
    def _calculate_dag_duration(self, nodes: List[DAGNode], 
                               parallel_groups: Dict[str, List[str]]) -> int:
        """Calculate estimated total duration considering parallel execution"""
        
        try:
            # Build dependency graph
            node_map = {node.node_id: node for node in nodes}
            
            # Calculate critical path (simplified version)
            # In a real implementation, this would use proper critical path algorithm
            max_duration = 0
            
            # Group nodes by parallel groups
            grouped_nodes = {"sequential": []}
            for node in nodes:
                if node.parallel_group:
                    if node.parallel_group not in grouped_nodes:
                        grouped_nodes[node.parallel_group] = []
                    grouped_nodes[node.parallel_group].append(node)
                else:
                    grouped_nodes["sequential"].append(node)
            
            # Estimate duration (simplified)
            total_duration = 0
            
            # Sequential nodes
            for node in grouped_nodes["sequential"]:
                total_duration += node.estimated_duration_seconds
            
            # Parallel groups - take max duration in each group
            for group_name, group_nodes in grouped_nodes.items():
                if group_name != "sequential":
                    group_max = max(node.estimated_duration_seconds for node in group_nodes)
                    total_duration += group_max
            
            return total_duration
            
        except Exception:
            # Fallback to sum of all durations
            return sum(node.estimated_duration_seconds for node in nodes)
    
    async def _validate_and_optimize_dag(self, dag: WorkflowDAG) -> WorkflowDAG:
        """Validate DAG structure and optimize for execution"""
        
        # Validate actions exist
        valid_nodes = []
        for node in dag.nodes:
            if node.action in ACTION_MAP:
                valid_nodes.append(node)
            else:
                logger.warning(f"Invalid action {node.action} in DAG, skipping node {node.node_id}")
        
        # Check for circular dependencies (simplified)
        if self._has_circular_dependencies(valid_nodes):
            logger.warning("Circular dependencies detected, converting to sequential")
            valid_nodes = self._make_sequential(valid_nodes)
        
        # Update DAG
        dag.nodes = valid_nodes
        dag.estimated_total_duration_seconds = self._calculate_dag_duration(
            valid_nodes, dag.parallel_groups
        )
        
        return dag
    
    def _has_circular_dependencies(self, nodes: List[DAGNode]) -> bool:
        """Check for circular dependencies (simplified check)"""
        # Simplified implementation - in production this would use proper cycle detection
        node_deps = {node.node_id: set(node.dependencies) for node in nodes}
        
        # Check for obvious circular references
        for node_id, deps in node_deps.items():
            if node_id in deps:
                return True
        
        return False
    
    def _make_sequential(self, nodes: List[DAGNode]) -> List[DAGNode]:
        """Convert nodes to sequential execution"""
        for i, node in enumerate(nodes):
            if i == 0:
                node.dependencies = []
            else:
                node.dependencies = [nodes[i-1].node_id]
            node.parallel_group = None
        
        return nodes
    
    async def _create_fallback_workflow(self, user_request: str, 
                                       context: Optional[Dict[str, Any]] = None) -> WorkflowDAG:
        """Create a simple fallback workflow"""
        
        # Create a basic single-action workflow
        fallback_node = DAGNode(
            node_id="fallback_1",
            action="gemini_generate_response",
            params={"prompt": user_request, "context": context or {}},
            dependencies=[],
            estimated_duration_seconds=30
        )
        
        return WorkflowDAG(
            dag_id=f"fallback_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            name="Fallback Workflow",
            description=f"Fallback workflow for: {user_request[:100]}",
            nodes=[fallback_node],
            created_at=datetime.now().isoformat(),
            estimated_total_duration_seconds=30
        )
    
    async def _store_dag_for_learning(self, user_request: str, dag: WorkflowDAG) -> None:
        """Store DAG for learning and improvement"""
        
        learning_data = {
            "user_request": user_request,
            "dag_id": dag.dag_id,
            "dag_structure": {
                "name": dag.name,
                "description": dag.description,
                "node_count": len(dag.nodes),
                "parallel_groups": len(dag.parallel_groups),
                "estimated_duration": dag.estimated_total_duration_seconds
            },
            "created_at": dag.created_at,
            "actions_used": [node.action for node in dag.nodes]
        }
        
        # Store in state manager for learning
        await state_manager.set_state(
            f"learning:dag:{dag.dag_id}",
            learning_data,
            ttl_seconds=2592000  # 30 days
        )
        
        # Emit learning event
        await event_bus.emit(
            "dag.generated",
            "gemini_planner",
            learning_data
        )
        
        logger.info(f"Stored DAG {dag.dag_id} for learning")


# Global planner instance
gemini_planner = GeminiDAGPlanner()

# Convenience functions
async def generate_workflow_dag(user_request: str, 
                               context: Optional[Dict[str, Any]] = None) -> WorkflowDAG:
    """Generate a workflow DAG from user request"""
    return await gemini_planner.generate_dag_workflow(user_request, context)

async def analyze_user_intent(user_request: str) -> Dict[str, Any]:
    """Analyze user intent and suggest workflow approach"""
    
    prompt = f"""
Analyze this user request and categorize it:

REQUEST: {user_request}

Provide a JSON response with:
{{
    "intent_category": "automation|reporting|data_management|content_creation|analysis",
    "complexity": "simple|medium|complex",
    "estimated_steps": 3,
    "requires_parallel_execution": true,
    "suggested_actions": ["action1", "action2"],
    "data_flow_pattern": "linear|fan_out|fan_in|mixed"
}}

Return only JSON, no explanations.
"""
    
    try:
        response = await gemini_planner._make_gemini_request(prompt)
        content = response.get("candidates", [{}])[0].get("content", {})
        text = content.get("parts", [{}])[0].get("text", "{}")
        
        # Clean and parse JSON
        json_text = re.sub(r'```json\s*|\s*```', '', text.strip())
        return json.loads(json_text)
        
    except Exception as e:
        logger.error(f"Failed to analyze user intent: {e}")
        return {
            "intent_category": "unknown",
            "complexity": "medium",
            "estimated_steps": 3,
            "requires_parallel_execution": False,
            "suggested_actions": [],
            "data_flow_pattern": "linear"
        }