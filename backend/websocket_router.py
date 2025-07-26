"""
WebSocket router for real-time communication
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from typing import Dict, Any
import json
import uuid
import logging

from backend.websocket.connection_manager import ConnectionManager
from backend.auth import get_current_user_or_api_key, User

logger = logging.getLogger(__name__)

# Create WebSocket router
websocket_router = APIRouter()

# Global connection manager instance
manager = ConnectionManager()


@websocket_router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """
    WebSocket endpoint for real-time communication
    
    Args:
        websocket: WebSocket connection
        client_id: Unique client identifier
    """
    await manager.connect(websocket, client_id)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                await handle_websocket_message(client_id, message)
                
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON received from client {client_id}: {data}")
                await manager.send_json_message({
                    "type": "error",
                    "message": "Invalid JSON format"
                }, client_id)
                
            except Exception as e:
                logger.error(f"Error handling message from client {client_id}: {e}")
                await manager.send_json_message({
                    "type": "error",
                    "message": "Internal server error"
                }, client_id)
                
    except WebSocketDisconnect:
        manager.disconnect(client_id)
        logger.info(f"Client {client_id} disconnected")
    except Exception as e:
        logger.error(f"WebSocket error for client {client_id}: {e}")
        manager.disconnect(client_id)


async def handle_websocket_message(client_id: str, message: Dict[str, Any]):
    """
    Handle incoming WebSocket messages
    
    Args:
        client_id: Client identifier
        message: Message data
    """
    message_type = message.get("type")
    
    if message_type == "subscribe_project":
        # Subscribe to project updates
        project_id = message.get("project_id")
        if project_id:
            manager.subscribe_to_project(client_id, project_id)
            await manager.send_json_message({
                "type": "subscription_confirmed",
                "project_id": project_id
            }, client_id)
        else:
            await manager.send_json_message({
                "type": "error",
                "message": "project_id is required for subscription"
            }, client_id)
    
    elif message_type == "unsubscribe_project":
        # Unsubscribe from project updates
        project_id = message.get("project_id")
        if project_id:
            manager.unsubscribe_from_project(client_id, project_id)
            await manager.send_json_message({
                "type": "unsubscription_confirmed",
                "project_id": project_id
            }, client_id)
    
    elif message_type == "ping":
        # Heartbeat/ping message
        await manager.send_json_message({
            "type": "pong",
            "timestamp": message.get("timestamp")
        }, client_id)
    
    elif message_type == "get_status":
        # Get current connection status
        await manager.send_json_message({
            "type": "status",
            "client_id": client_id,
            "connected": True,
            "subscriptions": list(manager.project_subscribers.keys())
        }, client_id)
    
    else:
        logger.warning(f"Unknown message type from client {client_id}: {message_type}")
        await manager.send_json_message({
            "type": "error",
            "message": f"Unknown message type: {message_type}"
        }, client_id)


# Utility functions for broadcasting updates
async def broadcast_agent_run_update(agent_run_data: Dict[str, Any]):
    """Broadcast agent run update to subscribed clients"""
    await manager.send_agent_run_update(agent_run_data)


async def broadcast_validation_update(validation_data: Dict[str, Any]):
    """Broadcast validation update to subscribed clients"""
    await manager.send_validation_update(validation_data)


async def broadcast_pr_notification(pr_data: Dict[str, Any]):
    """Broadcast PR notification to subscribed clients"""
    await manager.send_pr_notification(pr_data)


async def broadcast_project_update(project_data: Dict[str, Any]):
    """Broadcast general project update to subscribed clients"""
    project_id = project_data.get("project_id")
    if project_id:
        message = {
            "type": "project_update",
            "data": project_data
        }
        await manager.broadcast_to_project(message, project_id)


async def send_personal_notification(client_id: str, notification_data: Dict[str, Any]):
    """Send personal notification to a specific client"""
    message = {
        "type": "notification",
        "data": notification_data
    }
    await manager.send_json_message(message, client_id)


# Health check for WebSocket connections
@websocket_router.get("/ws/health")
async def websocket_health():
    """WebSocket health check endpoint"""
    return {
        "status": "healthy",
        "active_connections": len(manager.active_connections),
        "project_subscriptions": len(manager.project_subscribers),
        "total_subscribers": sum(len(subs) for subs in manager.project_subscribers.values())
    }


# Get connection statistics
@websocket_router.get("/ws/stats")
async def websocket_stats():
    """Get WebSocket connection statistics"""
    return {
        "active_connections": len(manager.active_connections),
        "project_subscriptions": {
            project_id: len(subscribers) 
            for project_id, subscribers in manager.project_subscribers.items()
        },
        "total_subscribers": sum(len(subs) for subs in manager.project_subscribers.values())
    }
