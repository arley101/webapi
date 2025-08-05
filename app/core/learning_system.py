# app/core/learning_system.py
"""
Task 3.2: Implement Feedback Loop for Learning

This module implements a learning system that captures workflow results,
user corrections, and system performance to improve future planning
and execution decisions.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib

from app.core.config import settings
from app.core.state_manager import state_manager
from app.core.event_bus import event_bus, EventType
from app.core.gemini_planner import WorkflowDAG, DAGNode

logger = logging.getLogger(__name__)

class FeedbackType(str, Enum):
    """Types of feedback the system can receive"""
    SUCCESS = "success"
    FAILURE = "failure"
    USER_CORRECTION = "user_correction"
    PERFORMANCE_ISSUE = "performance_issue"
    IMPROVEMENT_SUGGESTION = "improvement_suggestion"

class LearningCategory(str, Enum):
    """Categories of learning patterns"""
    WORKFLOW_OPTIMIZATION = "workflow_optimization"
    ACTION_SEQUENCING = "action_sequencing"
    PARAMETER_PATTERNS = "parameter_patterns"
    ERROR_PREVENTION = "error_prevention"
    PERFORMANCE_TUNING = "performance_tuning"

@dataclass
class FeedbackRecord:
    """Represents a piece of feedback about system performance"""
    feedback_id: str
    feedback_type: FeedbackType
    category: LearningCategory
    original_request: str
    workflow_id: str
    timestamp: str
    user_id: Optional[str] = None
    
    # Original execution data
    original_plan: Dict[str, Any] = None
    execution_result: Dict[str, Any] = None
    
    # Feedback data
    user_correction: Optional[Dict[str, Any]] = None
    performance_metrics: Optional[Dict[str, Any]] = None
    error_details: Optional[Dict[str, Any]] = None
    
    # Learning insights
    improvement_suggestion: Optional[str] = None
    confidence_score: float = 0.0
    
    def __post_init__(self):
        if self.original_plan is None:
            self.original_plan = {}
        if self.execution_result is None:
            self.execution_result = {}

@dataclass
class LearningPattern:
    """Represents a learned pattern from feedback"""
    pattern_id: str
    category: LearningCategory
    pattern_data: Dict[str, Any]
    confidence_score: float
    usage_count: int
    success_rate: float
    created_at: str
    updated_at: str
    
    # Pattern matching
    triggers: List[str] = None  # Keywords or conditions that trigger this pattern
    context_requirements: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.triggers is None:
            self.triggers = []
        if self.context_requirements is None:
            self.context_requirements = {}

class LearningSystem:
    """System for capturing feedback and learning from user interactions"""
    
    def __init__(self):
        self.learning_enabled = True
        self.max_patterns_per_category = 100
        
    async def record_workflow_feedback(self, feedback: FeedbackRecord) -> str:
        """Record feedback about a workflow execution"""
        
        logger.info(f"📝 Recording feedback: {feedback.feedback_type} for workflow {feedback.workflow_id}")
        
        try:
            # Store feedback record
            feedback_key = f"feedback:{feedback.feedback_id}"
            await state_manager.set_state(
                feedback_key,
                asdict(feedback),
                ttl_seconds=7776000  # 90 days
            )
            
            # Process feedback for learning
            patterns = await self._analyze_feedback_for_patterns(feedback)
            
            # Update existing patterns or create new ones
            for pattern in patterns:
                await self._update_or_create_pattern(pattern)
            
            # Emit learning event
            await event_bus.emit(
                "learning.feedback_recorded",
                "learning_system",
                {
                    "feedback_id": feedback.feedback_id,
                    "feedback_type": feedback.feedback_type,
                    "workflow_id": feedback.workflow_id,
                    "patterns_identified": len(patterns)
                }
            )
            
            logger.info(f"✅ Recorded feedback {feedback.feedback_id} and identified {len(patterns)} patterns")
            return feedback.feedback_id
            
        except Exception as e:
            logger.error(f"❌ Failed to record feedback: {e}")
            raise
    
    async def record_success_feedback(self, workflow_id: str, original_request: str,
                                     execution_result: Dict[str, Any], 
                                     performance_metrics: Dict[str, Any],
                                     user_id: Optional[str] = None) -> str:
        """Record successful workflow execution"""
        
        feedback_id = f"success_{workflow_id}_{int(datetime.now().timestamp())}"
        
        feedback = FeedbackRecord(
            feedback_id=feedback_id,
            feedback_type=FeedbackType.SUCCESS,
            category=LearningCategory.WORKFLOW_OPTIMIZATION,
            original_request=original_request,
            workflow_id=workflow_id,
            timestamp=datetime.now().isoformat(),
            user_id=user_id,
            execution_result=execution_result,
            performance_metrics=performance_metrics,
            confidence_score=1.0
        )
        
        return await self.record_workflow_feedback(feedback)
    
    async def record_failure_feedback(self, workflow_id: str, original_request: str,
                                     error_details: Dict[str, Any],
                                     execution_result: Dict[str, Any],
                                     user_id: Optional[str] = None) -> str:
        """Record failed workflow execution"""
        
        feedback_id = f"failure_{workflow_id}_{int(datetime.now().timestamp())}"
        
        feedback = FeedbackRecord(
            feedback_id=feedback_id,
            feedback_type=FeedbackType.FAILURE,
            category=LearningCategory.ERROR_PREVENTION,
            original_request=original_request,
            workflow_id=workflow_id,
            timestamp=datetime.now().isoformat(),
            user_id=user_id,
            execution_result=execution_result,
            error_details=error_details,
            confidence_score=1.0
        )
        
        return await self.record_workflow_feedback(feedback)
    
    async def record_user_correction(self, workflow_id: str, original_request: str,
                                    original_plan: Dict[str, Any],
                                    corrected_plan: Dict[str, Any],
                                    user_id: Optional[str] = None) -> str:
        """Record user correction to a workflow plan"""
        
        feedback_id = f"correction_{workflow_id}_{int(datetime.now().timestamp())}"
        
        feedback = FeedbackRecord(
            feedback_id=feedback_id,
            feedback_type=FeedbackType.USER_CORRECTION,
            category=LearningCategory.ACTION_SEQUENCING,
            original_request=original_request,
            workflow_id=workflow_id,
            timestamp=datetime.now().isoformat(),
            user_id=user_id,
            original_plan=original_plan,
            user_correction={
                "original_plan": original_plan,
                "corrected_plan": corrected_plan,
                "correction_reason": "User provided better approach"
            },
            confidence_score=0.9  # User corrections are high confidence
        )
        
        return await self.record_workflow_feedback(feedback)
    
    async def get_learning_suggestions(self, user_request: str, 
                                      context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Get learning-based suggestions for a user request"""
        
        try:
            # Find similar past requests
            similar_patterns = await self._find_similar_patterns(user_request, context)
            
            suggestions = []
            for pattern in similar_patterns:
                suggestion = {
                    "pattern_id": pattern.pattern_id,
                    "confidence": pattern.confidence_score,
                    "success_rate": pattern.success_rate,
                    "suggestion": pattern.pattern_data.get("suggested_approach", ""),
                    "usage_count": pattern.usage_count,
                    "category": pattern.category
                }
                suggestions.append(suggestion)
            
            # Sort by confidence and success rate
            suggestions.sort(key=lambda x: (x["confidence"] * x["success_rate"]), reverse=True)
            
            return suggestions[:5]  # Return top 5 suggestions
            
        except Exception as e:
            logger.error(f"Failed to get learning suggestions: {e}")
            return []
    
    async def improve_workflow_with_learning(self, dag: WorkflowDAG, 
                                           user_request: str) -> Tuple[WorkflowDAG, List[str]]:
        """Improve a workflow DAG using learned patterns"""
        
        improvements = []
        improved_dag = dag
        
        try:
            # Get relevant patterns
            patterns = await self._find_applicable_patterns(user_request, dag)
            
            for pattern in patterns:
                if pattern.category == LearningCategory.WORKFLOW_OPTIMIZATION:
                    improved_dag, improvement = await self._apply_workflow_optimization(
                        improved_dag, pattern
                    )
                    if improvement:
                        improvements.append(improvement)
                
                elif pattern.category == LearningCategory.ACTION_SEQUENCING:
                    improved_dag, improvement = await self._apply_sequencing_optimization(
                        improved_dag, pattern
                    )
                    if improvement:
                        improvements.append(improvement)
                
                elif pattern.category == LearningCategory.PARAMETER_PATTERNS:
                    improved_dag, improvement = await self._apply_parameter_optimization(
                        improved_dag, pattern
                    )
                    if improvement:
                        improvements.append(improvement)
            
            if improvements:
                logger.info(f"✨ Applied {len(improvements)} learning-based improvements to workflow")
            
            return improved_dag, improvements
            
        except Exception as e:
            logger.error(f"Failed to improve workflow with learning: {e}")
            return dag, []
    
    async def _analyze_feedback_for_patterns(self, feedback: FeedbackRecord) -> List[LearningPattern]:
        """Analyze feedback to identify learning patterns"""
        
        patterns = []
        
        try:
            if feedback.feedback_type == FeedbackType.SUCCESS:
                # Learn from successful patterns
                pattern = await self._create_success_pattern(feedback)
                if pattern:
                    patterns.append(pattern)
            
            elif feedback.feedback_type == FeedbackType.USER_CORRECTION:
                # Learn from user corrections
                pattern = await self._create_correction_pattern(feedback)
                if pattern:
                    patterns.append(pattern)
            
            elif feedback.feedback_type == FeedbackType.FAILURE:
                # Learn from failures
                pattern = await self._create_failure_pattern(feedback)
                if pattern:
                    patterns.append(pattern)
            
            return patterns
            
        except Exception as e:
            logger.error(f"Failed to analyze feedback for patterns: {e}")
            return []
    
    async def _create_success_pattern(self, feedback: FeedbackRecord) -> Optional[LearningPattern]:
        """Create a learning pattern from successful execution"""
        
        try:
            # Extract keywords from request
            keywords = self._extract_keywords(feedback.original_request)
            
            # Create pattern data
            pattern_data = {
                "request_keywords": keywords,
                "execution_metrics": feedback.performance_metrics,
                "successful_actions": self._extract_successful_actions(feedback.execution_result),
                "suggested_approach": "Follow this successful pattern",
                "optimization_tips": []
            }
            
            pattern_id = self._generate_pattern_id(feedback.original_request, "success")
            
            pattern = LearningPattern(
                pattern_id=pattern_id,
                category=LearningCategory.WORKFLOW_OPTIMIZATION,
                pattern_data=pattern_data,
                confidence_score=0.8,
                usage_count=1,
                success_rate=1.0,
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
                triggers=keywords
            )
            
            return pattern
            
        except Exception as e:
            logger.error(f"Failed to create success pattern: {e}")
            return None
    
    async def _create_correction_pattern(self, feedback: FeedbackRecord) -> Optional[LearningPattern]:
        """Create a learning pattern from user correction"""
        
        try:
            correction = feedback.user_correction
            if not correction:
                return None
            
            # Analyze the difference between original and corrected plans
            original_plan = correction.get("original_plan", {})
            corrected_plan = correction.get("corrected_plan", {})
            
            keywords = self._extract_keywords(feedback.original_request)
            
            pattern_data = {
                "request_keywords": keywords,
                "original_approach": original_plan,
                "corrected_approach": corrected_plan,
                "correction_type": "user_improvement",
                "suggested_approach": "Apply user-corrected pattern",
                "optimization_tips": ["User preferred this approach over system suggestion"]
            }
            
            pattern_id = self._generate_pattern_id(feedback.original_request, "correction")
            
            pattern = LearningPattern(
                pattern_id=pattern_id,
                category=LearningCategory.ACTION_SEQUENCING,
                pattern_data=pattern_data,
                confidence_score=0.9,  # User corrections are high confidence
                usage_count=1,
                success_rate=1.0,
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
                triggers=keywords
            )
            
            return pattern
            
        except Exception as e:
            logger.error(f"Failed to create correction pattern: {e}")
            return None
    
    async def _create_failure_pattern(self, feedback: FeedbackRecord) -> Optional[LearningPattern]:
        """Create a learning pattern from failure"""
        
        try:
            keywords = self._extract_keywords(feedback.original_request)
            
            pattern_data = {
                "request_keywords": keywords,
                "error_details": feedback.error_details,
                "failed_approach": feedback.execution_result,
                "prevention_strategy": "Avoid this pattern",
                "alternative_approach": "Consider different action sequence"
            }
            
            pattern_id = self._generate_pattern_id(feedback.original_request, "failure")
            
            pattern = LearningPattern(
                pattern_id=pattern_id,
                category=LearningCategory.ERROR_PREVENTION,
                pattern_data=pattern_data,
                confidence_score=0.7,
                usage_count=1,
                success_rate=0.0,
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
                triggers=keywords
            )
            
            return pattern
            
        except Exception as e:
            logger.error(f"Failed to create failure pattern: {e}")
            return None
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text for pattern matching"""
        
        import re
        
        # Simple keyword extraction (in production, use more sophisticated NLP)
        words = re.findall(r'\b\w+\b', text.lower())
        
        # Filter out common words
        stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during', 'before', 'after', 'above', 'below', 'between', 'among', 'throughout', 'instead'}
        
        keywords = [word for word in words if word not in stopwords and len(word) > 2]
        
        # Return unique keywords
        return list(set(keywords))
    
    def _extract_successful_actions(self, execution_result: Dict[str, Any]) -> List[str]:
        """Extract actions that executed successfully"""
        
        actions = []
        try:
            step_results = execution_result.get("step_results", {})
            for step_id, result in step_results.items():
                if result.get("success", False):
                    action = result.get("action")
                    if action:
                        actions.append(action)
        except Exception:
            pass
        
        return actions
    
    def _generate_pattern_id(self, request: str, pattern_type: str) -> str:
        """Generate a unique pattern ID"""
        
        # Create hash from request and timestamp
        content = f"{request}_{pattern_type}_{datetime.now().isoformat()}"
        hash_obj = hashlib.md5(content.encode())
        return f"{pattern_type}_{hash_obj.hexdigest()[:8]}"
    
    async def _find_similar_patterns(self, user_request: str, 
                                    context: Optional[Dict[str, Any]] = None) -> List[LearningPattern]:
        """Find patterns similar to the current request"""
        
        try:
            # Extract keywords from current request
            request_keywords = set(self._extract_keywords(user_request))
            
            # Get all patterns (in production, this would be more efficient)
            patterns = await self._get_all_patterns()
            
            # Score patterns by similarity
            scored_patterns = []
            for pattern in patterns:
                similarity_score = self._calculate_similarity(request_keywords, pattern)
                if similarity_score > 0.3:  # Minimum similarity threshold
                    scored_patterns.append((pattern, similarity_score))
            
            # Sort by similarity and success rate
            scored_patterns.sort(key=lambda x: x[1] * x[0].success_rate, reverse=True)
            
            return [pattern for pattern, score in scored_patterns[:10]]
            
        except Exception as e:
            logger.error(f"Failed to find similar patterns: {e}")
            return []
    
    def _calculate_similarity(self, request_keywords: Set[str], pattern: LearningPattern) -> float:
        """Calculate similarity between request and pattern"""
        
        try:
            pattern_keywords = set(pattern.triggers)
            
            if not pattern_keywords:
                return 0.0
            
            # Jaccard similarity
            intersection = len(request_keywords.intersection(pattern_keywords))
            union = len(request_keywords.union(pattern_keywords))
            
            if union == 0:
                return 0.0
            
            return intersection / union
            
        except Exception:
            return 0.0
    
    async def _get_all_patterns(self) -> List[LearningPattern]:
        """Get all learning patterns (simplified implementation)"""
        
        # In production, this would be more efficient with proper indexing
        patterns = []
        
        try:
            # This is a placeholder - in a real implementation,
            # we'd have proper pattern storage and retrieval
            pass
        except Exception as e:
            logger.error(f"Failed to get all patterns: {e}")
        
        return patterns
    
    async def _find_applicable_patterns(self, user_request: str, dag: WorkflowDAG) -> List[LearningPattern]:
        """Find patterns applicable to improving the current DAG"""
        
        return await self._find_similar_patterns(user_request)
    
    async def _apply_workflow_optimization(self, dag: WorkflowDAG, 
                                          pattern: LearningPattern) -> Tuple[WorkflowDAG, Optional[str]]:
        """Apply workflow optimization pattern"""
        
        # Placeholder for workflow optimization logic
        return dag, None
    
    async def _apply_sequencing_optimization(self, dag: WorkflowDAG, 
                                           pattern: LearningPattern) -> Tuple[WorkflowDAG, Optional[str]]:
        """Apply action sequencing optimization"""
        
        # Placeholder for sequencing optimization logic
        return dag, None
    
    async def _apply_parameter_optimization(self, dag: WorkflowDAG, 
                                          pattern: LearningPattern) -> Tuple[WorkflowDAG, Optional[str]]:
        """Apply parameter optimization pattern"""
        
        # Placeholder for parameter optimization logic
        return dag, None
    
    async def _update_or_create_pattern(self, pattern: LearningPattern) -> None:
        """Update existing pattern or create new one"""
        
        try:
            # Store pattern in state manager
            pattern_key = f"pattern:{pattern.pattern_id}"
            
            # Check if pattern exists
            existing_pattern_data = await state_manager.get_state(pattern_key)
            
            if existing_pattern_data:
                # Update existing pattern
                existing_pattern = LearningPattern(**existing_pattern_data)
                existing_pattern.usage_count += 1
                existing_pattern.updated_at = datetime.now().isoformat()
                
                # Update confidence based on new data
                existing_pattern.confidence_score = min(
                    existing_pattern.confidence_score + 0.1, 1.0
                )
                
                pattern = existing_pattern
            
            # Store updated pattern
            await state_manager.set_state(
                pattern_key,
                asdict(pattern),
                ttl_seconds=7776000  # 90 days
            )
            
            logger.debug(f"Updated/created pattern {pattern.pattern_id}")
            
        except Exception as e:
            logger.error(f"Failed to update/create pattern: {e}")
    
    async def get_learning_metrics(self) -> Dict[str, Any]:
        """Get metrics about the learning system"""
        
        try:
            # In production, this would query actual metrics
            return {
                "total_patterns": 0,
                "patterns_by_category": {},
                "average_confidence": 0.0,
                "success_rate": 0.0,
                "learning_enabled": self.learning_enabled,
                "feedback_records_count": 0
            }
            
        except Exception as e:
            logger.error(f"Failed to get learning metrics: {e}")
            return {"error": str(e)}


# Global learning system instance
learning_system = LearningSystem()

# Convenience functions
async def record_workflow_success(workflow_id: str, original_request: str,
                                 execution_result: Dict[str, Any],
                                 performance_metrics: Dict[str, Any]) -> str:
    """Record successful workflow execution"""
    return await learning_system.record_success_feedback(
        workflow_id, original_request, execution_result, performance_metrics
    )

async def record_workflow_failure(workflow_id: str, original_request: str,
                                 error_details: Dict[str, Any],
                                 execution_result: Dict[str, Any]) -> str:
    """Record failed workflow execution"""
    return await learning_system.record_failure_feedback(
        workflow_id, original_request, error_details, execution_result
    )

async def record_user_workflow_correction(workflow_id: str, original_request: str,
                                         original_plan: Dict[str, Any],
                                         corrected_plan: Dict[str, Any]) -> str:
    """Record user correction to workflow"""
    return await learning_system.record_user_correction(
        workflow_id, original_request, original_plan, corrected_plan
    )

async def get_learning_suggestions_for_request(user_request: str) -> List[Dict[str, Any]]:
    """Get learning-based suggestions for a user request"""
    return await learning_system.get_learning_suggestions(user_request)