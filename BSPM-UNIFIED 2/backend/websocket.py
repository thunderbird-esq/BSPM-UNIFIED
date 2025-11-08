"""
WebSocket Manager - Real-time Progress Updates
Version: 3.3
Platform: Intel Mac (macOS Ventura) + Docker

Manages WebSocket connections for sending real-time progress updates
during sprite generation and other long-running tasks.
"""

import json
import logging
from typing import Dict, Set, Optional
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections for multiple clients

    Features:
    - Client identification via session_id
    - Broadcast to all clients or specific session
    - Graceful disconnection handling
    - Connection state tracking
    """

    def __init__(self):
        # Active connections: session_id -> Set[WebSocket]
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # WebSocket -> session_id mapping for cleanup
        self.ws_to_session: Dict[WebSocket, str] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        """
        Accept and register a new WebSocket connection

        Args:
            websocket: FastAPI WebSocket instance
            session_id: Client session identifier
        """
        await websocket.accept()

        if session_id not in self.active_connections:
            self.active_connections[session_id] = set()

        self.active_connections[session_id].add(websocket)
        self.ws_to_session[websocket] = session_id

        logger.info(
            f"WebSocket connected: session={session_id}, "
            f"total_connections={sum(len(conns) for conns in self.active_connections.values())}"
        )

    def disconnect(self, websocket: WebSocket):
        """
        Unregister a WebSocket connection

        Args:
            websocket: WebSocket instance to disconnect
        """
        session_id = self.ws_to_session.get(websocket)

        if session_id and session_id in self.active_connections:
            self.active_connections[session_id].discard(websocket)

            # Clean up empty session entries
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]

        if websocket in self.ws_to_session:
            del self.ws_to_session[websocket]

        logger.info(
            f"WebSocket disconnected: session={session_id}, "
            f"remaining_connections={sum(len(conns) for conns in self.active_connections.values())}"
        )

    async def send_personal_message(self, message: str, websocket: WebSocket):
        """
        Send message to specific WebSocket connection

        Args:
            message: Message to send (usually JSON string)
            websocket: Target WebSocket
        """
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Failed to send personal message: {e}")
            self.disconnect(websocket)

    async def send_to_session(self, message: Dict, session_id: str):
        """
        Send message to all connections for a specific session

        Args:
            message: Message dict (will be JSON-encoded)
            session_id: Target session identifier
        """
        if session_id not in self.active_connections:
            logger.debug(f"No active connections for session {session_id}")
            return

        message_text = json.dumps(message)

        # Send to all connections for this session
        disconnected = []
        for websocket in self.active_connections[session_id]:
            try:
                await websocket.send_text(message_text)
            except Exception as e:
                logger.error(f"Failed to send to session {session_id}: {e}")
                disconnected.append(websocket)

        # Clean up failed connections
        for ws in disconnected:
            self.disconnect(ws)

    async def broadcast(self, message: Dict):
        """
        Send message to all active connections

        Args:
            message: Message dict (will be JSON-encoded)
        """
        message_text = json.dumps(message)

        all_connections = [
            ws for conns in self.active_connections.values() for ws in conns
        ]

        disconnected = []
        for websocket in all_connections:
            try:
                await websocket.send_text(message_text)
            except Exception as e:
                logger.error(f"Failed to broadcast: {e}")
                disconnected.append(websocket)

        # Clean up failed connections
        for ws in disconnected:
            self.disconnect(ws)

    async def send_progress_update(
        self,
        session_id: str,
        task_id: str,
        progress: float,
        status: str,
        message: Optional[str] = None,
        **kwargs
    ):
        """
        Send progress update for a specific task

        Args:
            session_id: Target session
            task_id: Task identifier
            progress: Progress percentage (0-100)
            status: Task status (e.g., "processing", "completed", "failed")
            message: Optional status message
            **kwargs: Additional metadata
        """
        update = {
            "type": "progress",
            "task_id": task_id,
            "progress": progress,
            "status": status,
            "message": message,
            **kwargs
        }

        await self.send_to_session(update, session_id)

    async def send_generation_update(
        self,
        session_id: str,
        step: str,
        progress: float,
        details: Optional[Dict] = None
    ):
        """
        Send sprite generation progress update

        Args:
            session_id: Target session
            step: Current generation step (e.g., "workflow_build", "sampling", "post_process")
            progress: Progress percentage (0-100)
            details: Optional additional details
        """
        update = {
            "type": "generation_progress",
            "step": step,
            "progress": progress,
            "details": details or {}
        }

        await self.send_to_session(update, session_id)

    def get_connection_count(self) -> Dict[str, int]:
        """
        Get connection statistics

        Returns:
            Dict with total connections and sessions
        """
        return {
            "total_connections": sum(len(conns) for conns in self.active_connections.values()),
            "active_sessions": len(self.active_connections)
        }


# Global connection manager instance
manager = ConnectionManager()
