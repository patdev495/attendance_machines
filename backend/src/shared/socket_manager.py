from fastapi import WebSocket
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"New WebSocket client connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket client disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Send message to all connected clients."""
        print(f"DEBUG: WebSocket Broadcast starting for {len(self.active_connections)} clients")
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
                print("DEBUG: WebSocket message sent successfully")
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                print(f"DEBUG: WebSocket send error: {e}")
                pass

# Global instance
manager = ConnectionManager()
