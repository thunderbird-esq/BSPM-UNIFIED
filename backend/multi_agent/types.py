"""
Pydantic v2 models for all data structures in the multi-agent system.

This module defines all type definitions used across the agent framework,
including task requests/responses, configurations, and workflow states.
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from uuid import uuid4


class AgentRole(str, Enum):
    """Role of an agent within a department"""
    EXECUTOR = "executor"  # Agent A - proposes solutions
    CRITIC = "critic"      # Agent B - reviews and improves


class TaskStatus(str, Enum):
    """Status of a task in the workflow"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    AWAITING_CRITIQUE = "awaiting_critique"
    IN_REVISION = "in_revision"
    APPROVED = "approved"
    NEEDS_HELP = "needs_help"
    FAILED = "failed"


class SeverityLevel(str, Enum):
    """Severity level for critiques"""
    MINOR = "minor"
    MODERATE = "moderate"
    CRITICAL = "critical"


class AgentConfig(BaseModel):
    """Configuration for a single studio agent"""
    model_config = ConfigDict(use_enum_values=True)

    name: str = Field(..., description="Agent name (e.g., 'Artist A')")
    department: str = Field(..., description="Department name (e.g., 'Art')")
    role: AgentRole = Field(..., description="Agent role: executor or critic")
    tools: List[str] = Field(default_factory=list, description="Available tools")
    llm_model: str = Field(default="claude-sonnet-4", description="LLM model to use")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or len(v.strip()) == 0:
            raise ValueError("Agent name cannot be empty")
        return v.strip()

    @field_validator('tools')
    @classmethod
    def validate_tools(cls, v: List[str]) -> List[str]:
        if not isinstance(v, list):
            raise ValueError("Tools must be a list")
        return v


class DepartmentConfig(BaseModel):
    """Configuration for a department with executor and critic agents"""
    model_config = ConfigDict(use_enum_values=True)

    name: str = Field(..., description="Department name")
    executor: AgentConfig = Field(..., description="Executor agent configuration")
    critic: AgentConfig = Field(..., description="Critic agent configuration")
    max_iterations: int = Field(default=3, description="Maximum critique-revision iterations")

    @field_validator('max_iterations')
    @classmethod
    def validate_max_iterations(cls, v: int) -> int:
        if v < 1 or v > 10:
            raise ValueError("max_iterations must be between 1 and 10")
        return v


class TaskRequest(BaseModel):
    """Request for a department to execute a task"""
    model_config = ConfigDict(use_enum_values=True)

    id: str = Field(default_factory=lambda: f"task_{uuid4().hex[:12]}")
    description: str = Field(..., description="Task description")
    tool: str = Field(..., description="Tool to use for the task")
    params: Dict[str, Any] = Field(default_factory=dict, description="Tool parameters")
    context: Optional[str] = Field(None, description="Additional context")
    priority: int = Field(default=0, description="Task priority (higher = more urgent)")
    created_at: datetime = Field(default_factory=datetime.now)

    @field_validator('description')
    @classmethod
    def validate_description(cls, v: str) -> str:
        if not v or len(v.strip()) < 5:
            raise ValueError("Task description must be at least 5 characters")
        return v.strip()


class TaskResponse(BaseModel):
    """Response from a department after task execution"""
    model_config = ConfigDict(use_enum_values=True)

    task_id: str = Field(..., description="Original task ID")
    status: TaskStatus = Field(..., description="Final task status")
    result: Optional[Any] = Field(None, description="Work artifact or result")
    iterations: int = Field(default=0, description="Number of critique-revision cycles")
    critique_history: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="History of all critiques"
    )
    total_time_seconds: float = Field(default=0.0, description="Total execution time")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    completed_at: datetime = Field(default_factory=datetime.now)


class WorkflowState(BaseModel):
    """State of a task workflow through the department"""
    model_config = ConfigDict(use_enum_values=True)

    task_id: str = Field(..., description="Task ID")
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    current_iteration: int = Field(default=0)
    max_iterations: int = Field(default=3)
    work_artifact: Optional[Any] = Field(None, description="Current work output")
    current_critique: Optional[Dict[str, Any]] = Field(None)
    history: List[Dict[str, Any]] = Field(default_factory=list)
    started_at: Optional[datetime] = Field(None)
    last_updated: datetime = Field(default_factory=datetime.now)

    def add_history_entry(self, entry_type: str, data: Dict[str, Any]) -> None:
        """Add an entry to the workflow history"""
        self.history.append({
            "type": entry_type,
            "timestamp": datetime.now().isoformat(),
            "data": data
        })
        self.last_updated = datetime.now()

    def increment_iteration(self) -> None:
        """Increment the iteration counter"""
        self.current_iteration += 1
        self.last_updated = datetime.now()

    def can_continue(self) -> bool:
        """Check if workflow can continue iterating"""
        return self.current_iteration < self.max_iterations


class CritiqueResult(BaseModel):
    """Structured critique from a critic agent"""
    model_config = ConfigDict(use_enum_values=True)

    approved: bool = Field(..., description="Whether work is approved")
    feedback: str = Field(..., description="Overall feedback message")
    suggestions: List[str] = Field(default_factory=list, description="Specific improvement suggestions")
    severity: SeverityLevel = Field(default=SeverityLevel.MINOR, description="Severity of issues")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence in critique")
    reasoning: Optional[str] = Field(None, description="Detailed reasoning for the critique")

    @field_validator('feedback')
    @classmethod
    def validate_feedback(cls, v: str) -> str:
        if not v or len(v.strip()) < 3:
            raise ValueError("Feedback must be at least 3 characters")
        return v.strip()

    @field_validator('suggestions')
    @classmethod
    def validate_suggestions(cls, v: List[str]) -> List[str]:
        return [s.strip() for s in v if s and s.strip()]


class ToolExecutionRequest(BaseModel):
    """Request to execute a tool"""
    model_config = ConfigDict(use_enum_values=True)

    id: str = Field(default_factory=lambda: f"tool_{uuid4().hex[:12]}")
    tool_name: str = Field(..., description="Name of the tool to execute")
    agent_name: str = Field(..., description="Agent requesting the tool")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Tool parameters")
    context: Optional[str] = Field(None, description="Execution context")
    timeout_seconds: int = Field(default=300, description="Execution timeout")
    created_at: datetime = Field(default_factory=datetime.now)

    @field_validator('tool_name')
    @classmethod
    def validate_tool_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Tool name cannot be empty")
        return v.strip()

    @field_validator('timeout_seconds')
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        if v < 1 or v > 3600:
            raise ValueError("Timeout must be between 1 and 3600 seconds")
        return v


class ToolExecutionResult(BaseModel):
    """Result from tool execution"""
    model_config = ConfigDict(use_enum_values=True)

    request_id: str = Field(..., description="Original request ID")
    success: bool = Field(..., description="Whether execution succeeded")
    result: Optional[Any] = Field(None, description="Tool output")
    error: Optional[str] = Field(None, description="Error message if failed")
    execution_time_seconds: float = Field(..., description="Execution duration")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    completed_at: datetime = Field(default_factory=datetime.now)


class MemoryQuery(BaseModel):
    """Query to agent's memory system"""
    model_config = ConfigDict(use_enum_values=True)

    query: str = Field(..., description="Search query")
    agent_name: Optional[str] = Field(None, description="Filter by agent")
    department: Optional[str] = Field(None, description="Filter by department")
    limit: int = Field(default=5, description="Maximum results")
    min_relevance: float = Field(default=0.5, ge=0.0, le=1.0, description="Minimum relevance score")

    @field_validator('query')
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v or len(v.strip()) < 2:
            raise ValueError("Query must be at least 2 characters")
        return v.strip()


class MemoryEntry(BaseModel):
    """Entry in agent's memory"""
    model_config = ConfigDict(use_enum_values=True)

    id: str = Field(default_factory=lambda: f"mem_{uuid4().hex[:12]}")
    agent_name: str = Field(..., description="Agent that created the memory")
    department: str = Field(..., description="Department")
    content: str = Field(..., description="Memory content")
    content_type: str = Field(..., description="Type of content (thought, work, critique, etc.)")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    embedding: Optional[List[float]] = Field(None, description="Vector embedding")
    created_at: datetime = Field(default_factory=datetime.now)
    relevance_score: float = Field(default=0.0, description="Relevance to current query")

    @field_validator('content')
    @classmethod
    def validate_content(cls, v: str) -> str:
        if not v or len(v.strip()) < 1:
            raise ValueError("Memory content cannot be empty")
        return v.strip()


class ConversationEntry(BaseModel):
    """Entry in conversation history"""
    model_config = ConfigDict(use_enum_values=True)

    id: str = Field(default_factory=lambda: f"conv_{uuid4().hex[:12]}")
    message_type: str = Field(..., description="Type of message")
    from_agent: str = Field(..., description="Sending agent")
    to_agent: Optional[str] = Field(None, description="Receiving agent (if applicable)")
    content: str = Field(..., description="Message content")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)


class SystemMetrics(BaseModel):
    """System-wide metrics for monitoring"""
    model_config = ConfigDict(use_enum_values=True)

    total_tasks: int = Field(default=0)
    completed_tasks: int = Field(default=0)
    failed_tasks: int = Field(default=0)
    total_iterations: int = Field(default=0)
    average_iterations: float = Field(default=0.0)
    total_tool_calls: int = Field(default=0)
    average_task_time_seconds: float = Field(default=0.0)
    active_departments: int = Field(default=0)
    timestamp: datetime = Field(default_factory=datetime.now)
