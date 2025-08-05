# app/core/state_manager.py
"""
Task 1.1: Centralized State Manager with Redis

This module provides a centralized state management system to replace 
the unreliable ecosystem_state.json approach. Stores:
- Intermediate results
- Resource IDs
- Conversation context
- Workflow execution state
"""

import json
import logging
import asyncio
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta
import redis
from contextlib import asynccontextmanager
import threading

from app.core.config import settings

logger = logging.getLogger(__name__)

class StateManager:
    """Centralized Redis-based state manager for the EliteDynamicsAPI system"""
    
    def __init__(self):
        self._redis: Optional[redis.Redis] = None
        self._connection_pool: Optional[redis.ConnectionPool] = None
        self._lock = threading.Lock()
        
    async def initialize(self) -> None:
        """Initialize Redis connection"""
        try:
            # Parse Redis URL
            import urllib.parse
            parsed = urllib.parse.urlparse(settings.REDIS_URL)
            
            self._connection_pool = redis.ConnectionPool(
                host=parsed.hostname or settings.REDIS_HOST,
                port=parsed.port or settings.REDIS_PORT,
                db=int(parsed.path.lstrip('/')) if parsed.path else settings.REDIS_DB,
                password=parsed.password or settings.REDIS_PASSWORD,
                decode_responses=True,
                retry_on_timeout=True,
                max_connections=20
            )
            self._redis = redis.Redis(connection_pool=self._connection_pool)
            
            # Test connection
            await self._run_sync(self._redis.ping)
            logger.info("✅ State Manager initialized successfully with Redis")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize State Manager: {e}")
            # Fallback to in-memory storage for development
            self._redis = None
            logger.warning("🔄 Falling back to in-memory state storage")
            
    async def close(self) -> None:
        """Close Redis connections"""
        if self._redis:
            await self._run_sync(self._redis.close)
        if self._connection_pool:
            await self._run_sync(self._connection_pool.disconnect)
    
    async def _run_sync(self, func, *args, **kwargs):
        """Run synchronous Redis operations in thread pool"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func, *args, **kwargs)
            
    def _encode_value(self, value: Any) -> str:
        """Encode value for Redis storage"""
        if isinstance(value, (dict, list)):
            return json.dumps(value, default=str)
        return str(value)
        
    def _decode_value(self, value: str) -> Any:
        """Decode value from Redis storage"""
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value
    
    # Core State Management Methods
    
    async def set_state(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        """Set state value with optional TTL"""
        try:
            if not self._redis:
                return False
                
            encoded_value = self._encode_value(value)
            
            if ttl_seconds:
                await self._run_sync(self._redis.setex, key, ttl_seconds, encoded_value)
            else:
                await self._run_sync(self._redis.set, key, encoded_value)
                
            logger.debug(f"State set: {key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set state {key}: {e}")
            return False
    
    async def get_state(self, key: str, default: Any = None) -> Any:
        """Get state value"""
        try:
            if not self._redis:
                return default
                
            value = await self._run_sync(self._redis.get, key)
            if value is None:
                return default
                
            return self._decode_value(value)
            
        except Exception as e:
            logger.error(f"Failed to get state {key}: {e}")
            return default
    
    async def delete_state(self, key: str) -> bool:
        """Delete state value"""
        try:
            if not self._redis:
                return False
                
            result = await self._run_sync(self._redis.delete, key)
            logger.debug(f"State deleted: {key}")
            return result > 0
            
        except Exception as e:
            logger.error(f"Failed to delete state {key}: {e}")
            return False
    
    # Workflow State Management
    
    async def create_workflow_session(self, session_id: str, workflow_data: Dict[str, Any]) -> bool:
        """Create a new workflow session"""
        workflow_state = {
            "session_id": session_id,
            "status": "initialized",
            "created_at": datetime.now().isoformat(),
            "current_step": 0,
            "total_steps": len(workflow_data.get("steps", [])),
            "workflow_data": workflow_data,
            "intermediate_results": {},
            "errors": []
        }
        
        key = f"workflow:{session_id}"
        return await self.set_state(key, workflow_state, ttl_seconds=3600)  # 1 hour TTL
    
    async def update_workflow_step(self, session_id: str, step_index: int, 
                                   step_result: Any, status: str = "running") -> bool:
        """Update workflow step result"""
        key = f"workflow:{session_id}"
        workflow_state = await self.get_state(key)
        
        if not workflow_state:
            logger.error(f"Workflow session {session_id} not found")
            return False
            
        workflow_state["current_step"] = step_index
        workflow_state["status"] = status
        workflow_state["updated_at"] = datetime.now().isoformat()
        workflow_state["intermediate_results"][f"step_{step_index}"] = step_result
        
        return await self.set_state(key, workflow_state, ttl_seconds=3600)
    
    async def get_workflow_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get complete workflow state"""
        key = f"workflow:{session_id}"
        return await self.get_state(key)
    
    async def complete_workflow(self, session_id: str, final_result: Any) -> bool:
        """Mark workflow as completed"""
        key = f"workflow:{session_id}"
        workflow_state = await self.get_state(key)
        
        if not workflow_state:
            return False
            
        workflow_state["status"] = "completed"
        workflow_state["completed_at"] = datetime.now().isoformat()
        workflow_state["final_result"] = final_result
        
        return await self.set_state(key, workflow_state, ttl_seconds=86400)  # 24 hours TTL
    
    # Resource Management
    
    async def store_resource_id(self, resource_type: str, resource_id: str, 
                               metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Store resource ID for later reference"""
        key = f"resource:{resource_type}:{resource_id}"
        resource_data = {
            "resource_id": resource_id,
            "resource_type": resource_type,
            "created_at": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        return await self.set_state(key, resource_data, ttl_seconds=86400)  # 24 hours TTL
    
    async def get_resource_id(self, resource_type: str, resource_id: str) -> Optional[Dict[str, Any]]:
        """Get resource information by ID"""
        key = f"resource:{resource_type}:{resource_id}"
        return await self.get_state(key)
    
    async def list_resources(self, resource_type: str) -> List[Dict[str, Any]]:
        """List all resources of a specific type"""
        try:
            if not self._redis:
                return []
                
            pattern = f"resource:{resource_type}:*"
            keys = await self._run_sync(self._redis.keys, pattern)
            
            resources = []
            for key in keys:
                resource_data = await self.get_state(key)
                if resource_data:
                    resources.append(resource_data)
                    
            return resources
            
        except Exception as e:
            logger.error(f"Failed to list resources of type {resource_type}: {e}")
            return []
    
    # Conversation Context Management
    
    async def set_conversation_context(self, user_id: str, context: Dict[str, Any]) -> bool:
        """Set conversation context for a user"""
        key = f"context:{user_id}"
        context["updated_at"] = datetime.now().isoformat()
        return await self.set_state(key, context, ttl_seconds=7200)  # 2 hours TTL
    
    async def get_conversation_context(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation context for a user"""
        key = f"context:{user_id}"
        return await self.get_state(key)
    
    # Cache Management
    
    async def cache_action_result(self, action_name: str, params_hash: str, 
                                 result: Any, ttl_seconds: int = 3600) -> bool:
        """Cache action result for performance"""
        key = f"cache:action:{action_name}:{params_hash}"
        cache_data = {
            "action_name": action_name,
            "params_hash": params_hash,
            "result": result,
            "cached_at": datetime.now().isoformat()
        }
        
        return await self.set_state(key, cache_data, ttl_seconds=ttl_seconds)
    
    async def get_cached_result(self, action_name: str, params_hash: str) -> Optional[Any]:
        """Get cached action result"""
        key = f"cache:action:{action_name}:{params_hash}"
        cache_data = await self.get_state(key)
        
        if cache_data:
            return cache_data.get("result")
        return None
    
    # Health Check
    
    async def health_check(self) -> Dict[str, Any]:
        """Check state manager health"""
        try:
            if not self._redis:
                return {
                    "status": "degraded",
                    "backend": "in-memory",
                    "message": "Using fallback in-memory storage"
                }
            
            # Test Redis connection
            start_time = datetime.now()
            await self._run_sync(self._redis.ping)
            response_time = (datetime.now() - start_time).total_seconds()
            
            # Get Redis info
            info = await self._run_sync(self._redis.info)
            
            return {
                "status": "healthy",
                "backend": "redis",
                "response_time_seconds": response_time,
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_human": info.get("used_memory_human", "unknown"),
                "redis_version": info.get("redis_version", "unknown")
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "backend": "redis",
                "error": str(e)
            }


# Global state manager instance
state_manager = StateManager()

# Context manager for automatic cleanup
@asynccontextmanager
async def get_state_manager():
    """Context manager to get initialized state manager"""
    if not state_manager._redis:
        await state_manager.initialize()
    
    try:
        yield state_manager
    finally:
        # Don't close here as it's a global instance
        pass

# Convenience functions
async def set_state(key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
    """Convenience function to set state"""
    async with get_state_manager() as sm:
        return await sm.set_state(key, value, ttl_seconds)

async def get_state(key: str, default: Any = None) -> Any:
    """Convenience function to get state"""
    async with get_state_manager() as sm:
        return await sm.get_state(key, default)

async def delete_state(key: str) -> bool:
    """Convenience function to delete state"""
    async with get_state_manager() as sm:
        return await sm.delete_state(key)