"""
Session Manager - File-based Session Persistence
Version: 3.3
Platform: Intel Mac (macOS Ventura) + Docker

Manages user sessions with file-based persistence and automatic expiration.
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages user sessions with file-based persistence

    Features:
    - JSON file storage for session data
    - Automatic session expiration (24 hours)
    - Load sessions on startup
    - Save sessions on changes
    - Cleanup for expired sessions
    """

    def __init__(self, storage_path: str, expiration_hours: int = 24):
        """
        Initialize session manager

        Args:
            storage_path: Directory to store session files
            expiration_hours: Hours until session expires (default 24)
        """
        self.storage_path = Path(storage_path)
        self.expiration_hours = expiration_hours
        self.sessions: Dict[str, Dict[str, Any]] = {}

        # Create storage directory
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Load existing sessions
        self._load_sessions()

        # Clean up expired sessions
        self._cleanup_expired_sessions()

        logger.info(
            f"SessionManager initialized: {len(self.sessions)} active sessions, "
            f"storage={self.storage_path}, expiration={expiration_hours}h"
        )

    def _get_session_file_path(self, session_id: str) -> Path:
        """Get file path for session data"""
        # Sanitize session_id for filename
        safe_id = "".join(c for c in session_id if c.isalnum() or c in "-_")
        return self.storage_path / f"session_{safe_id}.json"

    def _load_sessions(self):
        """Load all session files from storage"""
        loaded_count = 0

        for session_file in self.storage_path.glob("session_*.json"):
            try:
                with open(session_file, 'r') as f:
                    session_data = json.load(f)

                session_id = session_data.get('session_id')
                if session_id:
                    self.sessions[session_id] = session_data
                    loaded_count += 1

            except Exception as e:
                logger.error(f"Failed to load session file {session_file}: {e}")

        logger.info(f"Loaded {loaded_count} sessions from storage")

    def _cleanup_expired_sessions(self):
        """Remove expired sessions from memory and storage"""
        now = datetime.now()
        expired_sessions = []

        for session_id, session_data in self.sessions.items():
            last_activity_str = session_data.get('last_activity')

            if last_activity_str:
                try:
                    last_activity = datetime.fromisoformat(last_activity_str)
                    age = now - last_activity

                    if age > timedelta(hours=self.expiration_hours):
                        expired_sessions.append(session_id)

                except ValueError:
                    # Invalid timestamp, consider expired
                    expired_sessions.append(session_id)

        # Remove expired sessions
        for session_id in expired_sessions:
            self._delete_session(session_id)

        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")

    def create_session(self, session_id: str, initial_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create a new session

        Args:
            session_id: Unique session identifier
            initial_data: Optional initial session data

        Returns:
            Session data dict
        """
        now = datetime.now().isoformat()

        session_data = {
            'session_id': session_id,
            'created_at': now,
            'last_activity': now,
            'data': initial_data or {}
        }

        self.sessions[session_id] = session_data
        self._save_session(session_id)

        logger.info(f"Created session: {session_id}")

        return session_data

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session data

        Args:
            session_id: Session identifier

        Returns:
            Session data dict or None if not found
        """
        session_data = self.sessions.get(session_id)

        if session_data:
            # Update last activity
            session_data['last_activity'] = datetime.now().isoformat()
            self._save_session(session_id)

        return session_data

    def update_session(self, session_id: str, data: Dict[str, Any]) -> bool:
        """
        Update session data

        Args:
            session_id: Session identifier
            data: Data to update (will be merged with existing)

        Returns:
            True if successful, False if session not found
        """
        if session_id not in self.sessions:
            # Auto-create session if it doesn't exist
            self.create_session(session_id, data)
            return True

        # Merge data
        self.sessions[session_id]['data'].update(data)
        self.sessions[session_id]['last_activity'] = datetime.now().isoformat()

        self._save_session(session_id)

        logger.debug(f"Updated session: {session_id}")

        return True

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session

        Args:
            session_id: Session identifier

        Returns:
            True if deleted, False if not found
        """
        return self._delete_session(session_id)

    def _delete_session(self, session_id: str) -> bool:
        """Internal delete method"""
        if session_id not in self.sessions:
            return False

        # Remove from memory
        del self.sessions[session_id]

        # Remove from storage
        session_file = self._get_session_file_path(session_id)
        if session_file.exists():
            try:
                session_file.unlink()
            except Exception as e:
                logger.error(f"Failed to delete session file {session_file}: {e}")

        logger.info(f"Deleted session: {session_id}")

        return True

    def _save_session(self, session_id: str):
        """Save session to file"""
        if session_id not in self.sessions:
            return

        session_file = self._get_session_file_path(session_id)

        try:
            with open(session_file, 'w') as f:
                json.dump(self.sessions[session_id], f, indent=2)

        except Exception as e:
            logger.error(f"Failed to save session {session_id}: {e}")

    def get_all_sessions(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all active sessions

        Returns:
            Dict of session_id -> session_data
        """
        return self.sessions.copy()

    def get_session_count(self) -> int:
        """Get number of active sessions"""
        return len(self.sessions)

    def cleanup(self):
        """Run cleanup of expired sessions (can be called periodically)"""
        self._cleanup_expired_sessions()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get session statistics

        Returns:
            Dict with session counts and info
        """
        now = datetime.now()
        recent_count = 0

        for session_data in self.sessions.values():
            last_activity_str = session_data.get('last_activity')
            if last_activity_str:
                try:
                    last_activity = datetime.fromisoformat(last_activity_str)
                    if now - last_activity < timedelta(hours=1):
                        recent_count += 1
                except ValueError:
                    pass

        return {
            'total_sessions': len(self.sessions),
            'recent_sessions_1h': recent_count,
            'storage_path': str(self.storage_path),
            'expiration_hours': self.expiration_hours
        }
