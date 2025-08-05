# app/core/event_bus.py
"""
Task 1.2: Event Bus (Pub/Sub) System

This module provides a publish/subscribe event system for the EliteDynamicsAPI.
Key backend actions emit standardized events that can be consumed by listeners
for auditing, logging, and workflow coordination.
"""

import json
import logging
import asyncio
from typing import Any, Dict, List, Callable, Optional, Set
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import redis
from contextlib import asynccontextmanager

from app.core.config import settings

logger = logging.getLogger(__name__)

class EventType(str, Enum):
    """Standard event types in the system"""
    # File operations
    FILE_CREATED = "file.created"
    FILE_UPLOADED = "file.uploaded"
    FILE_DOWNLOADED = "file.downloaded"
    FILE_DELETED = "file.deleted"
    FILE_SHARED = "file.shared"
    
    # Contact/CRM operations
    CONTACT_CREATED = "contact.created"
    CONTACT_UPDATED = "contact.updated"
    CONTACT_DELETED = "contact.deleted"
    
    # Workflow operations
    WORKFLOW_STARTED = "workflow.started"
    WORKFLOW_STEP_COMPLETED = "workflow.step_completed"
    WORKFLOW_COMPLETED = "workflow.completed"
    WORKFLOW_FAILED = "workflow.failed"
    
    # Action operations
    ACTION_STARTED = "action.started"
    ACTION_COMPLETED = "action.completed"
    ACTION_FAILED = "action.failed"
    
    # System operations
    SYSTEM_ERROR = "system.error"
    SYSTEM_WARNING = "system.warning"
    SYSTEM_INFO = "system.info"

@dataclass
class Event:
    """Standard event structure"""
    event_name: str
    source: str
    timestamp: str
    data: Dict[str, Any]
    event_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    correlation_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        """Create event from dictionary"""
        return cls(**data)

class EventBus:
    """Redis-based publish/subscribe event bus"""
    
    def __init__(self):
        self._redis: Optional[redis.Redis] = None
        self._pubsub: Optional[redis.client.PubSub] = None
        self._subscribers: Dict[str, List[Callable]] = {}
        self._running = False
        self._listener_task: Optional[asyncio.Task] = None
        
    async def initialize(self) -> None:
        """Initialize event bus with Redis"""
        try:
            # Parse Redis URL 
            import urllib.parse
            parsed = urllib.parse.urlparse(settings.REDIS_URL)
            
            self._redis = redis.Redis(
                host=parsed.hostname or settings.REDIS_HOST,
                port=parsed.port or settings.REDIS_PORT,
                db=int(parsed.path.lstrip('/')) if parsed.path else settings.REDIS_DB,
                password=parsed.password or settings.REDIS_PASSWORD,
                decode_responses=True,
                retry_on_timeout=True
            )
            
            # Test connection
            await self._run_sync(self._redis.ping)
            self._pubsub = self._redis.pubsub()
            
            logger.info("✅ Event Bus initialized successfully with Redis")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Event Bus: {e}")
            # Keep _redis as None for fallback behavior
            
    async def close(self) -> None:
        """Close event bus connections"""
        self._running = False
        
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
                
        if self._pubsub:
            await self._run_sync(self._pubsub.close)
            
        if self._redis:
            await self._run_sync(self._redis.close)
    
    async def _run_sync(self, func, *args, **kwargs):
        """Run synchronous Redis operations in thread pool"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func, *args, **kwargs)
    
    async def start_listening(self) -> None:
        """Start listening for events"""
        if not self._redis or not self._pubsub:
            logger.warning("Event Bus not initialized, cannot start listening")
            return
            
        self._running = True
        self._listener_task = asyncio.create_task(self._listen_loop())
        logger.info("🔊 Event Bus listener started")
    
    async def _listen_loop(self) -> None:
        """Main event listening loop"""
        try:
            while self._running:
                try:
                    message = await self._run_sync(self._pubsub.get_message, timeout=1.0)
                    if message and message['type'] == 'message':
                        await self._handle_message(message)
                except Exception as e:
                    if self._running:  # Only log if still running
                        logger.error(f"Error in event listener loop: {e}")
                    await asyncio.sleep(1)
                    
        except asyncio.CancelledError:
            logger.info("Event listener loop cancelled")
        except Exception as e:
            logger.error(f"Event listener loop failed: {e}")
    
    async def _handle_message(self, message: Dict[str, Any]) -> None:
        """Handle incoming event message"""
        try:
            channel = message['channel']
            data = json.loads(message['data'])
            event = Event.from_dict(data)
            
            # Call registered subscribers
            if channel in self._subscribers:
                for callback in self._subscribers[channel]:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(event)
                        else:
                            callback(event)
                    except Exception as e:
                        logger.error(f"Error in event subscriber for {channel}: {e}")
                        
        except Exception as e:
            logger.error(f"Error handling event message: {e}")
    
    # Publishing methods
    
    async def publish(self, event: Event) -> bool:
        """Publish an event"""
        try:
            if not self._redis:
                # Log for debugging when Redis is not available
                logger.debug(f"Event (no Redis): {event.event_name} from {event.source}")
                return False
                
            # Use event_name as channel
            channel = event.event_name
            message = json.dumps(event.to_dict(), default=str)
            
            await self._run_sync(self._redis.publish, channel, message)
            logger.debug(f"Event published: {event.event_name} from {event.source}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish event {event.event_name}: {e}")
            return False
    
    async def emit(self, event_name: str, source: str, data: Dict[str, Any],
                   user_id: Optional[str] = None, session_id: Optional[str] = None,
                   correlation_id: Optional[str] = None) -> bool:
        """Emit an event with automatic timestamp and ID generation"""
        event = Event(
            event_name=event_name,
            source=source,
            timestamp=datetime.now().isoformat(),
            data=data,
            event_id=f"{event_name}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
            user_id=user_id,
            session_id=session_id,
            correlation_id=correlation_id
        )
        
        return await self.publish(event)
    
    # Subscription methods
    
    async def subscribe(self, event_name: str, callback: Callable) -> bool:
        """Subscribe to an event"""
        try:
            if not self._redis or not self._pubsub:
                logger.warning(f"Cannot subscribe to {event_name}: Event Bus not initialized")
                return False
                
            # Add to Redis pubsub
            await self._run_sync(self._pubsub.subscribe, event_name)
            
            # Add to local subscribers
            if event_name not in self._subscribers:
                self._subscribers[event_name] = []
            self._subscribers[event_name].append(callback)
            
            logger.info(f"Subscribed to event: {event_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to subscribe to {event_name}: {e}")
            return False
    
    async def unsubscribe(self, event_name: str, callback: Optional[Callable] = None) -> bool:
        """Unsubscribe from an event"""
        try:
            if callback:
                # Remove specific callback
                if event_name in self._subscribers:
                    self._subscribers[event_name] = [
                        cb for cb in self._subscribers[event_name] if cb != callback
                    ]
                    if not self._subscribers[event_name]:
                        del self._subscribers[event_name]
                        if self._pubsub:
                            await self._run_sync(self._pubsub.unsubscribe, event_name)
            else:
                # Remove all callbacks for event
                if event_name in self._subscribers:
                    del self._subscribers[event_name]
                    if self._pubsub:
                        await self._run_sync(self._pubsub.unsubscribe, event_name)
                        
            logger.info(f"Unsubscribed from event: {event_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unsubscribe from {event_name}: {e}")
            return False
    
    # Convenience methods for common events
    
    async def emit_file_created(self, source: str, file_id: str, file_name: str,
                               file_url: Optional[str] = None, **kwargs) -> bool:
        """Emit file created event"""
        data = {
            "file_id": file_id,
            "file_name": file_name,
            "file_url": file_url,
            **kwargs
        }
        return await self.emit(EventType.FILE_CREATED, source, data, **kwargs)
    
    async def emit_contact_created(self, source: str, contact_id: str, 
                                  contact_data: Dict[str, Any], **kwargs) -> bool:
        """Emit contact created event"""
        data = {
            "contact_id": contact_id,
            "contact_data": contact_data,
            **kwargs
        }
        return await self.emit(EventType.CONTACT_CREATED, source, data, **kwargs)
    
    async def emit_action_completed(self, source: str, action_name: str,
                                   action_params: Dict[str, Any], 
                                   action_result: Any, **kwargs) -> bool:
        """Emit action completed event"""
        data = {
            "action_name": action_name,
            "action_params": action_params,
            "action_result": action_result,
            **kwargs
        }
        return await self.emit(EventType.ACTION_COMPLETED, source, data, **kwargs)
    
    async def emit_action_failed(self, source: str, action_name: str,
                                action_params: Dict[str, Any], 
                                error: str, **kwargs) -> bool:
        """Emit action failed event"""
        data = {
            "action_name": action_name,
            "action_params": action_params,
            "error": error,
            **kwargs
        }
        return await self.emit(EventType.ACTION_FAILED, source, data, **kwargs)
    
    async def emit_workflow_step_completed(self, source: str, workflow_id: str,
                                          step_index: int, step_result: Any, **kwargs) -> bool:
        """Emit workflow step completed event"""
        data = {
            "workflow_id": workflow_id,
            "step_index": step_index,
            "step_result": step_result,
            **kwargs
        }
        return await self.emit(EventType.WORKFLOW_STEP_COMPLETED, source, data, **kwargs)
    
    # Health check
    
    async def health_check(self) -> Dict[str, Any]:
        """Check event bus health"""
        try:
            if not self._redis:
                return {
                    "status": "degraded",
                    "backend": "disabled",
                    "message": "Event bus not initialized"
                }
            
            # Test Redis connection
            start_time = datetime.now()
            await self._run_sync(self._redis.ping)
            response_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "status": "healthy",
                "backend": "redis",
                "response_time_seconds": response_time,
                "running": self._running,
                "active_subscriptions": len(self._subscribers),
                "subscribed_events": list(self._subscribers.keys())
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "backend": "redis",
                "error": str(e)
            }


# Global event bus instance
event_bus = EventBus()

# Context manager for automatic cleanup
@asynccontextmanager
async def get_event_bus():
    """Context manager to get initialized event bus"""
    if not event_bus._redis:
        await event_bus.initialize()
    
    try:
        yield event_bus
    finally:
        # Don't close here as it's a global instance
        pass

# Convenience functions
async def emit_event(event_name: str, source: str, data: Dict[str, Any], **kwargs) -> bool:
    """Convenience function to emit an event"""
    async with get_event_bus() as eb:
        return await eb.emit(event_name, source, data, **kwargs)

async def subscribe_to_event(event_name: str, callback: Callable) -> bool:
    """Convenience function to subscribe to an event"""
    async with get_event_bus() as eb:
        return await eb.subscribe(event_name, callback)

# Default audit event listener
async def audit_event_listener(event: Event) -> None:
    """Default audit event listener that logs all events"""
    logger.info(f"AUDIT: {event.event_name} from {event.source} at {event.timestamp}")
    if event.data:
        logger.debug(f"AUDIT DATA: {json.dumps(event.data, default=str)}")

# Setup default listeners
async def setup_default_listeners() -> None:
    """Setup default event listeners for system auditing"""
    try:
        # Subscribe to all action events for auditing
        await subscribe_to_event(EventType.ACTION_COMPLETED, audit_event_listener)
        await subscribe_to_event(EventType.ACTION_FAILED, audit_event_listener)
        await subscribe_to_event(EventType.FILE_CREATED, audit_event_listener)
        await subscribe_to_event(EventType.CONTACT_CREATED, audit_event_listener)
        
        logger.info("✅ Default event listeners setup completed")
        
    except Exception as e:
        logger.error(f"Failed to setup default event listeners: {e}")