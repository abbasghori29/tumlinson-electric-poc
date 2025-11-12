"""WebSocket connection manager for real-time updates"""
from typing import Dict, Set
from fastapi import WebSocket
from app.utils.logger import get_logger
import json

logger = get_logger(__name__)


class WebSocketManager:
    """Manages WebSocket connections for real-time updates"""
    
    def __init__(self):
        # Map of client_id -> WebSocket connection
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        """Accept and store a WebSocket connection"""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"WebSocket connected: {client_id}")
    
    def disconnect(self, client_id: str):
        """Remove a WebSocket connection"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"WebSocket disconnected: {client_id}")
    
    async def send_message(self, client_id: str, message: dict):
        """Send a message to a specific client"""
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_json(message)
            except Exception as e:
                logger.error(f"Error sending message to {client_id}: {e}")
                self.disconnect(client_id)
    
    async def send_progress(self, client_id: str, message: str, progress: int = None, data: dict = None):
        """
        Send a progress update to a client
        
        Args:
            client_id: Client identifier
            message: Progress message to display
            progress: Optional progress percentage (0-100)
            data: Optional additional data
        """
        payload = {
            "type": "progress",
            "message": message,
        }
        
        if progress is not None:
            payload["progress"] = progress
        
        if data:
            payload["data"] = data
        
        await self.send_message(client_id, payload)
    
    async def send_complete(self, client_id: str, message: str, data: dict = None):
        """
        Send a completion message to a client
        
        Args:
            client_id: Client identifier
            message: Completion message
            data: Optional result data
        """
        payload = {
            "type": "complete",
            "message": message,
        }
        
        if data:
            payload["data"] = data
        
        await self.send_message(client_id, payload)
    
    async def send_error(self, client_id: str, message: str, error: str = None):
        """
        Send an error message to a client
        
        Args:
            client_id: Client identifier
            message: Error message
            error: Optional error details
        """
        payload = {
            "type": "error",
            "message": message,
        }
        
        if error:
            payload["error"] = error
        
        await self.send_message(client_id, payload)


# Global WebSocket manager instance
ws_manager = WebSocketManager()

