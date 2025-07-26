"""
WebSocket connection manager for real-time updates
"""
import asyncio
import json
from typing import Dict, List, Optional, Any, Set
from fastapi import WebSocket, WebSocketDisconnect
import structlog
from datetime import datetime, timedelta

from backend.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class ConnectionManager:
    """Manages WebSocket connections and broadcasting"""
    
    def __init__(self):
        # Active connections: client_id -> WebSocket
        self.active_connections: Dict[str, WebSocket] = {}
        
        # Project subscriptions: project_id -> set of client_ids
        self.project_subscriptions: Dict[int, Set[str]] = {}
        
        # Agent run subscriptions: agent_run_id -> set of client_ids
        self.agent_run_subscriptions: Dict[int, Set[str]] = {}
        
        # Connection metadata
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
        
        # Heartbeat tracking
        self.last_heartbeat: Dict[str, datetime] = {}
        
        # Start heartbeat task
        asyncio.create_task(self._heartbeat_task())
    
    async def connect(self, websocket: WebSocket, client_id: str):
        """Accept a new WebSocket connection"""
        try:
            await websocket.accept()
            self.active_connections[client_id] = websocket
            self.connection_metadata[client_id] = {
                "connected_at": datetime.utcnow(),
                "subscriptions": {
                    "projects": set(),
                    "agent_runs": set()
                }
            }
            self.last_heartbeat[client_id] = datetime.utcnow()
            
            logger.info("WebSocket connection established", client_id=client_id)
            
            # Send welcome message
            await self.send_personal_message(client_id, {
                "type": "connection_established",
                "client_id": client_id,
                "timestamp": datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.error("Failed to establish WebSocket connection", client_id=client_id, error=str(e))
            raise
    
    def disconnect(self, client_id: str):
        """Remove a WebSocket connection"""
        try:
            # Remove from active connections
            if client_id in self.active_connections:
                del self.active_connections[client_id]
            
            # Remove from all subscriptions
            self._remove_from_all_subscriptions(client_id)
            
            # Clean up metadata
            if client_id in self.connection_metadata:
                del self.connection_metadata[client_id]
            
            if client_id in self.last_heartbeat:
                del self.last_heartbeat[client_id]
            
            logger.info("WebSocket connection closed", client_id=client_id)
            
        except Exception as e:
            logger.error("Error during WebSocket disconnect", client_id=client_id, error=str(e))
    
    def _remove_from_all_subscriptions(self, client_id: str):
        """Remove client from all subscriptions"""
        # Remove from project subscriptions
        for project_id, clients in self.project_subscriptions.items():
            clients.discard(client_id)
        
        # Remove from agent run subscriptions
        for agent_run_id, clients in self.agent_run_subscriptions.items():
            clients.discard(client_id)
        
        # Clean up empty subscription sets
        self.project_subscriptions = {
            k: v for k, v in self.project_subscriptions.items() if v
        }
        self.agent_run_subscriptions = {
            k: v for k, v in self.agent_run_subscriptions.items() if v
        }
    
    async def send_personal_message(self, client_id: str, message: Any):
        """Send a message to a specific client"""
        if client_id not in self.active_connections:
            logger.warning("Attempted to send message to disconnected client", client_id=client_id)
            return
        
        try:
            websocket = self.active_connections[client_id]
            
            # Convert message to JSON if it's not already a string
            if isinstance(message, dict):
                message_str = json.dumps(message, default=str)
            else:
                message_str = str(message)
            
            await websocket.send_text(message_str)
            
        except WebSocketDisconnect:
            logger.info("Client disconnected during message send", client_id=client_id)
            self.disconnect(client_id)
        except Exception as e:
            logger.error("Failed to send personal message", client_id=client_id, error=str(e))
            self.disconnect(client_id)
    
    async def broadcast_to_project(self, project_id: int, message: Any):
        """Broadcast a message to all clients subscribed to a project"""
        if project_id not in self.project_subscriptions:
            return
        
        clients = self.project_subscriptions[project_id].copy()
        
        # Add project_id to message
        if isinstance(message, dict):
            message["project_id"] = project_id
        
        await self._broadcast_to_clients(clients, message)
    
    async def broadcast_to_agent_run(self, agent_run_id: int, message: Any):
        """Broadcast a message to all clients subscribed to an agent run"""
        if agent_run_id not in self.agent_run_subscriptions:
            return
        
        clients = self.agent_run_subscriptions[agent_run_id].copy()
        
        # Add agent_run_id to message
        if isinstance(message, dict):
            message["agent_run_id"] = agent_run_id
        
        await self._broadcast_to_clients(clients, message)
    
    async def broadcast_to_all(self, message: Any):
        """Broadcast a message to all connected clients"""
        clients = set(self.active_connections.keys())
        await self._broadcast_to_clients(clients, message)
    
    async def _broadcast_to_clients(self, client_ids: Set[str], message: Any):
        """Broadcast message to specific set of clients"""
        if not client_ids:
            return
        
        # Convert message to JSON if needed
        if isinstance(message, dict):
            message_str = json.dumps(message, default=str)
        else:
            message_str = str(message)
        
        # Send to all clients concurrently
        tasks = []
        for client_id in client_ids:
            if client_id in self.active_connections:
                tasks.append(self._send_to_client(client_id, message_str))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _send_to_client(self, client_id: str, message_str: str):
        """Send message to a single client with error handling"""
        try:
            websocket = self.active_connections[client_id]
            await websocket.send_text(message_str)
        except WebSocketDisconnect:
            logger.info("Client disconnected during broadcast", client_id=client_id)
            self.disconnect(client_id)
        except Exception as e:
            logger.error("Failed to send broadcast message", client_id=client_id, error=str(e))
            self.disconnect(client_id)
    
    async def subscribe_to_project(self, client_id: str, project_id: int):
        """Subscribe a client to project updates"""
        if client_id not in self.active_connections:
            return False
        
        if project_id not in self.project_subscriptions:
            self.project_subscriptions[project_id] = set()
        
        self.project_subscriptions[project_id].add(client_id)
        
        # Update metadata
        if client_id in self.connection_metadata:
            self.connection_metadata[client_id]["subscriptions"]["projects"].add(project_id)
        
        logger.info("Client subscribed to project", client_id=client_id, project_id=project_id)
        
        # Send confirmation
        await self.send_personal_message(client_id, {
            "type": "subscription_confirmed",
            "subscription_type": "project",
            "project_id": project_id
        })
        
        return True
    
    async def unsubscribe_from_project(self, client_id: str, project_id: int):
        """Unsubscribe a client from project updates"""
        if project_id in self.project_subscriptions:
            self.project_subscriptions[project_id].discard(client_id)
            
            # Clean up empty subscription
            if not self.project_subscriptions[project_id]:
                del self.project_subscriptions[project_id]
        
        # Update metadata
        if client_id in self.connection_metadata:
            self.connection_metadata[client_id]["subscriptions"]["projects"].discard(project_id)
        
        logger.info("Client unsubscribed from project", client_id=client_id, project_id=project_id)
        
        # Send confirmation
        await self.send_personal_message(client_id, {
            "type": "unsubscription_confirmed",
            "subscription_type": "project",
            "project_id": project_id
        })
    
    async def subscribe_to_agent_run(self, client_id: str, agent_run_id: int):
        """Subscribe a client to agent run updates"""
        if client_id not in self.active_connections:
            return False
        
        if agent_run_id not in self.agent_run_subscriptions:
            self.agent_run_subscriptions[agent_run_id] = set()
        
        self.agent_run_subscriptions[agent_run_id].add(client_id)
        
        # Update metadata
        if client_id in self.connection_metadata:
            self.connection_metadata[client_id]["subscriptions"]["agent_runs"].add(agent_run_id)
        
        logger.info("Client subscribed to agent run", client_id=client_id, agent_run_id=agent_run_id)
        
        # Send confirmation
        await self.send_personal_message(client_id, {
            "type": "subscription_confirmed",
            "subscription_type": "agent_run",
            "agent_run_id": agent_run_id
        })
        
        return True
    
    async def handle_client_message(self, client_id: str, message: str):
        """Handle incoming message from client"""
        try:
            data = json.loads(message)
            message_type = data.get("type")
            
            if message_type == "heartbeat":
                await self._handle_heartbeat(client_id)
            elif message_type == "subscribe_project":
                project_id = data.get("project_id")
                if project_id:
                    await self.subscribe_to_project(client_id, project_id)
            elif message_type == "unsubscribe_project":
                project_id = data.get("project_id")
                if project_id:
                    await self.unsubscribe_from_project(client_id, project_id)
            elif message_type == "subscribe_agent_run":
                agent_run_id = data.get("agent_run_id")
                if agent_run_id:
                    await self.subscribe_to_agent_run(client_id, agent_run_id)
            else:
                logger.warning("Unknown message type", client_id=client_id, message_type=message_type)
                
        except json.JSONDecodeError:
            logger.error("Invalid JSON message from client", client_id=client_id)
        except Exception as e:
            logger.error("Error handling client message", client_id=client_id, error=str(e))
    
    async def _handle_heartbeat(self, client_id: str):
        """Handle heartbeat from client"""
        self.last_heartbeat[client_id] = datetime.utcnow()
        await self.send_personal_message(client_id, {
            "type": "heartbeat_ack",
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def _heartbeat_task(self):
        """Background task to check for stale connections"""
        while True:
            try:
                await asyncio.sleep(settings.websocket_heartbeat_interval)
                await self._cleanup_stale_connections()
            except Exception as e:
                logger.error("Error in heartbeat task", error=str(e))
    
    async def _cleanup_stale_connections(self):
        """Remove connections that haven't sent heartbeat recently"""
        cutoff_time = datetime.utcnow() - timedelta(seconds=settings.websocket_heartbeat_interval * 2)
        stale_clients = []
        
        for client_id, last_heartbeat in self.last_heartbeat.items():
            if last_heartbeat < cutoff_time:
                stale_clients.append(client_id)
        
        for client_id in stale_clients:
            logger.info("Removing stale WebSocket connection", client_id=client_id)
            self.disconnect(client_id)
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        return {
            "total_connections": len(self.active_connections),
            "project_subscriptions": {
                str(k): len(v) for k, v in self.project_subscriptions.items()
            },
            "agent_run_subscriptions": {
                str(k): len(v) for k, v in self.agent_run_subscriptions.items()
            },
            "connection_metadata": {
                client_id: {
                    "connected_at": metadata["connected_at"].isoformat(),
                    "project_subscriptions": len(metadata["subscriptions"]["projects"]),
                    "agent_run_subscriptions": len(metadata["subscriptions"]["agent_runs"])
                }
                for client_id, metadata in self.connection_metadata.items()
            }
        }


# Global connection manager instance
connection_manager = ConnectionManager()


def get_connection_manager() -> ConnectionManager:
    """Get global connection manager instance"""
    return connection_manager

