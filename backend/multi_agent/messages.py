"""
Message types and schemas for inter-agent communication.

This module defines all message types used in the multi-agent system,
including internal thoughts, peer messages, critiques, and tool usage.
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from enum import Enum
from uuid import uuid4

from .types import SeverityLevel


class MessageType(str, Enum):
    """Types of messages in the system"""
    INTERNAL_THOUGHT = "internal_thought"
    PEER_MESSAGE = "peer_message"
    CRITIQUE = "critique"
    TOOL_USAGE = "tool_usage"
    TOOL_RESULT = "tool_result"
    APPROVAL = "approval"
    PM_FEEDBACK = "pm_feedback"
    USER_FEEDBACK = "user_feedback"


class BaseMessage(BaseModel):
    """Base message model for all communication"""
    model_config = ConfigDict(use_enum_values=True)

    id: str = Field(default_factory=lambda: f"msg_{uuid4().hex[:12]}")
    type: MessageType
    from_agent: str = Field(..., description="Name of sending agent")
    department: str = Field(..., description="Department of sending agent")
    timestamp: datetime = Field(default_factory=datetime.now)
    visible_to: List[str] = Field(
        default_factory=lambda: ["user", "pm_agent"],
        description="Who can see this message"
    )

    @field_validator('from_agent')
    @classmethod
    def validate_from_agent(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("from_agent cannot be empty")
        return v.strip()

    @field_validator('department')
    @classmethod
    def validate_department(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("department cannot be empty")
        return v.strip()

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for serialization"""
        return {
            "id": self.id,
            "type": self.type,
            "from_agent": self.from_agent,
            "department": self.department,
            "timestamp": self.timestamp.isoformat(),
            "visible_to": self.visible_to,
        }


class InternalThought(BaseMessage):
    """Agent's internal reasoning - visible to user and PM Agent"""
    type: MessageType = MessageType.INTERNAL_THOUGHT
    content: str = Field(..., description="Reasoning or thought content")
    context: Optional[str] = Field(None, description="Context for the thought")
    reasoning_steps: Optional[List[str]] = Field(None, description="Step-by-step reasoning")

    @field_validator('content')
    @classmethod
    def validate_content(cls, v: str) -> str:
        if not v or len(v.strip()) < 3:
            raise ValueError("Thought content must be at least 3 characters")
        return v.strip()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        base = super().to_dict()
        base.update({
            "content": self.content,
            "context": self.context,
            "reasoning_steps": self.reasoning_steps,
        })
        return base


class PeerMessage(BaseMessage):
    """Message between department agents"""
    type: MessageType = MessageType.PEER_MESSAGE
    to_agent: str = Field(..., description="Name of receiving agent")
    content: str = Field(..., description="Message content")
    attachments: Optional[List[str]] = Field(None, description="Attached file paths or IDs")
    request_feedback: bool = Field(default=False, description="Whether feedback is requested")

    @field_validator('to_agent')
    @classmethod
    def validate_to_agent(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("to_agent cannot be empty")
        return v.strip()

    @field_validator('content')
    @classmethod
    def validate_content(cls, v: str) -> str:
        if not v or len(v.strip()) < 1:
            raise ValueError("Message content cannot be empty")
        return v.strip()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        base = super().to_dict()
        base.update({
            "to_agent": self.to_agent,
            "content": self.content,
            "attachments": self.attachments,
            "request_feedback": self.request_feedback,
        })
        return base


class Critique(BaseMessage):
    """Critic agent's feedback on work"""
    type: MessageType = MessageType.CRITIQUE
    to_agent: str = Field(..., description="Agent receiving the critique")
    approved: bool = Field(..., description="Whether work is approved")
    feedback: str = Field(..., description="Overall feedback")
    suggestions: List[str] = Field(default_factory=list, description="Specific suggestions")
    severity: SeverityLevel = Field(default=SeverityLevel.MINOR, description="Issue severity")
    work_reference: Optional[str] = Field(None, description="Reference to work being critiqued")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence in critique")

    @field_validator('to_agent')
    @classmethod
    def validate_to_agent(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("to_agent cannot be empty")
        return v.strip()

    @field_validator('feedback')
    @classmethod
    def validate_feedback(cls, v: str) -> str:
        if not v or len(v.strip()) < 3:
            raise ValueError("Feedback must be at least 3 characters")
        return v.strip()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        base = super().to_dict()
        base.update({
            "to_agent": self.to_agent,
            "approved": self.approved,
            "feedback": self.feedback,
            "suggestions": self.suggestions,
            "severity": self.severity,
            "work_reference": self.work_reference,
            "confidence": self.confidence,
        })
        return base


class ToolUsage(BaseMessage):
    """Record of tool usage by an agent"""
    type: MessageType = MessageType.TOOL_USAGE
    tool_name: str = Field(..., description="Name of tool being used")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Tool parameters")
    purpose: Optional[str] = Field(None, description="Purpose of using this tool")
    request_id: str = Field(default_factory=lambda: f"tool_{uuid4().hex[:12]}")

    @field_validator('tool_name')
    @classmethod
    def validate_tool_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("tool_name cannot be empty")
        return v.strip()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        base = super().to_dict()
        base.update({
            "tool_name": self.tool_name,
            "parameters": self.parameters,
            "purpose": self.purpose,
            "request_id": self.request_id,
        })
        return base


class ToolResult(BaseMessage):
    """Result from tool execution"""
    type: MessageType = MessageType.TOOL_RESULT
    tool_name: str = Field(..., description="Name of tool executed")
    request_id: str = Field(..., description="Original tool request ID")
    success: bool = Field(..., description="Whether execution succeeded")
    result: Optional[Any] = Field(None, description="Tool output")
    error: Optional[str] = Field(None, description="Error message if failed")
    execution_time_seconds: float = Field(default=0.0, description="Execution duration")

    @field_validator('tool_name')
    @classmethod
    def validate_tool_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("tool_name cannot be empty")
        return v.strip()

    @field_validator('request_id')
    @classmethod
    def validate_request_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("request_id cannot be empty")
        return v.strip()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        base = super().to_dict()
        base.update({
            "tool_name": self.tool_name,
            "request_id": self.request_id,
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "execution_time_seconds": self.execution_time_seconds,
        })
        return base


class Approval(BaseMessage):
    """Approval message from critic agent"""
    type: MessageType = MessageType.APPROVAL
    to_agent: str = Field(..., description="Agent receiving approval")
    work_reference: str = Field(..., description="Reference to approved work")
    final_comments: Optional[str] = Field(None, description="Final comments")
    quality_rating: Optional[int] = Field(None, ge=1, le=5, description="Quality rating 1-5")

    @field_validator('to_agent')
    @classmethod
    def validate_to_agent(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("to_agent cannot be empty")
        return v.strip()

    @field_validator('work_reference')
    @classmethod
    def validate_work_reference(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("work_reference cannot be empty")
        return v.strip()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        base = super().to_dict()
        base.update({
            "to_agent": self.to_agent,
            "work_reference": self.work_reference,
            "final_comments": self.final_comments,
            "quality_rating": self.quality_rating,
        })
        return base


class PMFeedback(BaseMessage):
    """Feedback from PM Agent to department agents"""
    type: MessageType = MessageType.PM_FEEDBACK
    to_agents: List[str] = Field(..., description="Agents receiving feedback")
    feedback_type: Literal["guidance", "correction", "escalation", "praise"] = Field(
        ..., description="Type of feedback"
    )
    content: str = Field(..., description="Feedback content")
    action_required: bool = Field(default=False, description="Whether action is required")
    priority: int = Field(default=0, description="Feedback priority")

    @field_validator('to_agents')
    @classmethod
    def validate_to_agents(cls, v: List[str]) -> List[str]:
        if not v or len(v) == 0:
            raise ValueError("Must specify at least one recipient")
        return [agent.strip() for agent in v if agent.strip()]

    @field_validator('content')
    @classmethod
    def validate_content(cls, v: str) -> str:
        if not v or len(v.strip()) < 5:
            raise ValueError("Feedback content must be at least 5 characters")
        return v.strip()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        base = super().to_dict()
        base.update({
            "to_agents": self.to_agents,
            "feedback_type": self.feedback_type,
            "content": self.content,
            "action_required": self.action_required,
            "priority": self.priority,
        })
        return base


class UserFeedback(BaseMessage):
    """Feedback from user to agents"""
    type: MessageType = MessageType.USER_FEEDBACK
    to_agents: List[str] = Field(..., description="Agents receiving feedback")
    content: str = Field(..., description="Feedback content")
    rating: Optional[int] = Field(None, ge=1, le=5, description="Rating 1-5")
    work_reference: Optional[str] = Field(None, description="Reference to work being reviewed")

    @field_validator('to_agents')
    @classmethod
    def validate_to_agents(cls, v: List[str]) -> List[str]:
        if not v or len(v) == 0:
            raise ValueError("Must specify at least one recipient")
        return [agent.strip() for agent in v if agent.strip()]

    @field_validator('content')
    @classmethod
    def validate_content(cls, v: str) -> str:
        if not v or len(v.strip()) < 1:
            raise ValueError("Feedback content cannot be empty")
        return v.strip()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        base = super().to_dict()
        base.update({
            "to_agents": self.to_agents,
            "content": self.content,
            "rating": self.rating,
            "work_reference": self.work_reference,
        })
        return base


# Message factory for creating messages from dictionaries
def create_message(message_dict: Dict[str, Any]) -> BaseMessage:
    """
    Factory function to create the appropriate message type from a dictionary.

    Args:
        message_dict: Dictionary containing message data with 'type' key

    Returns:
        Appropriate message instance

    Raises:
        ValueError: If message type is unknown
    """
    message_type = message_dict.get("type")

    type_map = {
        MessageType.INTERNAL_THOUGHT: InternalThought,
        MessageType.PEER_MESSAGE: PeerMessage,
        MessageType.CRITIQUE: Critique,
        MessageType.TOOL_USAGE: ToolUsage,
        MessageType.TOOL_RESULT: ToolResult,
        MessageType.APPROVAL: Approval,
        MessageType.PM_FEEDBACK: PMFeedback,
        MessageType.USER_FEEDBACK: UserFeedback,
    }

    message_class = type_map.get(message_type)
    if not message_class:
        raise ValueError(f"Unknown message type: {message_type}")

    return message_class(**message_dict)
