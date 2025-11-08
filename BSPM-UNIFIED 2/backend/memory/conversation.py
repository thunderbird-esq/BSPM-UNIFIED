"""
Conversation Memory - Session-based conversation tracking
Version: 3.1
Platform: Intel Mac (macOS Ventura) + Docker

Stores conversation history with metadata for context retrieval
"""

import os
import json
import hashlib
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class ConversationTurn(BaseModel):
    """Single conversation turn with metadata"""
    turn_id: str
    session_id: str
    timestamp: datetime
    user_message: str
    pm_response: str
    action_taken: Optional[str] = None
    plan_approved: bool = False
    artifacts_generated: List[str] = []
    correlation_id: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ConversationMemory:
    """Manages conversation history for a session"""
    
    def __init__(self, session_id: str, storage_path: str = "/app/agent_memory/conversations"):
        self.session_id = session_id
        self.storage_path = storage_path
        self.turns: List[ConversationTurn] = []
        self.short_term_window = 6
        
        os.makedirs(storage_path, exist_ok=True)
        self._load_existing_turns()
    
    def _load_existing_turns(self):
        """Load existing conversation from JSONL file"""
        filepath = os.path.join(self.storage_path, f"{self.session_id}.jsonl")
        
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        turn = ConversationTurn(**data)
                        self.turns.append(turn)
                    except json.JSONDecodeError:
                        continue
    
    def add_turn(
        self,
        user_message: str,
        pm_response: str,
        **kwargs
    ) -> ConversationTurn:
        """
        Add conversation turn and persist
        
        Args:
            user_message: User's input
            pm_response: PM agent's response
            **kwargs: Additional metadata
        
        Returns:
            ConversationTurn instance
        """
        turn = ConversationTurn(
            turn_id=self._generate_turn_id(user_message),
            session_id=self.session_id,
            timestamp=datetime.utcnow(),
            user_message=user_message,
            pm_response=pm_response,
            **kwargs
        )
        
        self.turns.append(turn)
        self._persist_turn(turn)
        
        return turn
    
    def get_recent_context(self, window: Optional[int] = None) -> str:
        """
        Get formatted recent conversation for LLM context
        
        Args:
            window: Number of recent turns (default: self.short_term_window)
        
        Returns:
            Formatted conversation string
        """
        window = window or self.short_term_window
        recent_turns = self.turns[-window:]
        
        context_parts = []
        for turn in recent_turns:
            context_parts.append(f"User: {turn.user_message}")
            context_parts.append(f"PM: {turn.pm_response}")
            if turn.action_taken:
                context_parts.append(f"Action: {turn.action_taken}")
        
        return "\n".join(context_parts) if context_parts else "No previous conversation."
    
    def get_turn_summary(self) -> dict:
        """Get session statistics"""
        return {
            "total_turns": len(self.turns),
            "plans_approved": sum(1 for t in self.turns if t.plan_approved),
            "artifacts_generated": sum(len(t.artifacts_generated) for t in self.turns),
            "session_duration_minutes": self._calculate_duration()
        }
    
    def _generate_turn_id(self, message: str) -> str:
        """Generate deterministic turn ID"""
        content = f"{message}{datetime.utcnow().isoformat()}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _persist_turn(self, turn: ConversationTurn):
        """Append turn to JSONL file"""
        filepath = os.path.join(self.storage_path, f"{self.session_id}.jsonl")
        
        with open(filepath, 'a') as f:
            f.write(turn.json() + '\n')
    
    def _calculate_duration(self) -> int:
        """Calculate session duration in minutes"""
        if not self.turns:
            return 0
        
        first = self.turns[0].timestamp
        last = self.turns[-1].timestamp
        return int((last - first).total_seconds() / 60)
