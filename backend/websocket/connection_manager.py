"""
WebSocket connection manager for real-time updates
"""
from fastapi import WebSocket
from typing import Dict, List
import json
import asyncio

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.project_subscribers: Dict[int, List[str]] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        print(f"Client {client_id} connected")
    
    def disconnect(self, client_id: str):
        """Remove a WebSocket connection"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            
        # Remove from project subscriptions
        for project_id, subscribers in self.project_subscribers.items():
            if client_id in subscribers:
                subscribers.remove(client_id)
        
        print(f"Client {client_id} disconnected")
    
    async def send_personal_message(self, message: str, client_id: str):
        """Send a message to a specific client"""
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_text(message)
            except Exception as e:
                print(f"Error sending message to {client_id}: {e}")
                self.disconnect(client_id)
    
    async def send_json_message(self, data: dict, client_id: str):
        """Send JSON data to a specific client"""
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_json(data)
            except Exception as e:
                print(f"Error sending JSON to {client_id}: {e}")
                self.disconnect(client_id)
    
    async def broadcast_to_project(self, message: dict, project_id: int):
        """Broadcast a message to all clients subscribed to a project"""
        if project_id in self.project_subscribers:
            subscribers = self.project_subscribers[project_id].copy()
            for client_id in subscribers:
                await self.send_json_message(message, client_id)
    
    def subscribe_to_project(self, client_id: str, project_id: int):
        """Subscribe a client to project updates"""
        if project_id not in self.project_subscribers:
            self.project_subscribers[project_id] = []
        
        if client_id not in self.project_subscribers[project_id]:
            self.project_subscribers[project_id].append(client_id)
            print(f"Client {client_id} subscribed to project {project_id}")
    
    def unsubscribe_from_project(self, client_id: str, project_id: int):
        """Unsubscribe a client from project updates"""
        if project_id in self.project_subscribers:
            if client_id in self.project_subscribers[project_id]:
                self.project_subscribers[project_id].remove(client_id)
                print(f"Client {client_id} unsubscribed from project {project_id}")
    
    async def send_agent_run_update(self, agent_run_data: dict):
        """Send agent run update to subscribed clients"""
        project_id = agent_run_data.get("project_id")
        if project_id:
            message = {
                "type": "agent_run_update",
                "data": agent_run_data
            }
            await self.broadcast_to_project(message, project_id)
    
    async def send_validation_update(self, validation_data: dict):
        """Send validation update to subscribed clients"""
        project_id = validation_data.get("project_id")
        if project_id:
            message = {
                "type": "validation_update",
                "data": validation_data
            }
            await self.broadcast_to_project(message, project_id)
    
    async def send_pr_notification(self, pr_data: dict):
        """Send PR notification to subscribed clients"""
        project_id = pr_data.get("project_id")
        if project_id:
            message = {
                "type": "pr_notification",
                "data": pr_data
            }
            await self.broadcast_to_project(message, project_id)
