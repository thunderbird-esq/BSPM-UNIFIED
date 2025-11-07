"""
Multi-Agent System for BSPM-UNIFIED Game Studio.

This module provides the foundational infrastructure for a collaborative
multi-agent system where 12 AI agents work together in departments to
create game content.

Main Components:
    - StudioAgent: Base class for all agents
    - Department: Coordinates executor-critic agent pairs
    - Message types: Structured communication between agents
    - Type definitions: Pydantic models for all data structures

Example:
    >>> from backend.multi_agent import StudioAgent, Department, AgentRole
    >>> from backend.multi_agent import TaskRequest
    >>>
    >>> # Create agents
    >>> executor = StudioAgent(
    ...     name="Artist A",
    ...     department="Art",
    ...     role=AgentRole.EXECUTOR,
    ...     tools=["comfyui", "aseprite_mcp"]
    ... )
    >>> critic = StudioAgent(
    ...     name="Artist B",
    ...     department="Art",
    ...     role=AgentRole.CRITIC,
    ...     tools=[]
    ... )
    >>>
    >>> # Create department
    >>> art_dept = Department("Art", executor, critic)
    >>>
    >>> # Execute task
    >>> task = TaskRequest(
    ...     description="Create boss sprite",
    ...     tool="comfyui",
    ...     params={"style": "pixel_art"}
    ... )
    >>> response = await art_dept.execute_task(task)
"""

from .agent import StudioAgent
from .department import Department
from .messages import (
    MessageType,
    BaseMessage,
    InternalThought,
    PeerMessage,
    Critique,
    ToolUsage,
    ToolResult,
    Approval,
    PMFeedback,
    UserFeedback,
    create_message,
)
from .types import (
    AgentRole,
    TaskStatus,
    SeverityLevel,
    AgentConfig,
    DepartmentConfig,
    TaskRequest,
    TaskResponse,
    WorkflowState,
    CritiqueResult,
    ToolExecutionRequest,
    ToolExecutionResult,
    MemoryQuery,
    MemoryEntry,
    ConversationEntry,
    SystemMetrics,
)

# Memory system imports (commented out until dependencies are installed)
# from .memory import AgentMemory
# from .shared_memory import SharedMemory
# from .embeddings import (
#     create_embedding,
#     cosine_similarity,
#     batch_embeddings,
#     semantic_search,
#     get_embedding_model,
# )

__version__ = "0.1.0"

__all__ = [
    # Core classes
    "StudioAgent",
    "Department",

    # Memory system (commented out until dependencies are installed)
    # "AgentMemory",
    # "SharedMemory",
    # "create_embedding",
    # "cosine_similarity",
    # "batch_embeddings",
    # "semantic_search",
    # "get_embedding_model",

    # Enums
    "AgentRole",
    "TaskStatus",
    "SeverityLevel",
    "MessageType",

    # Message types
    "BaseMessage",
    "InternalThought",
    "PeerMessage",
    "Critique",
    "ToolUsage",
    "ToolResult",
    "Approval",
    "PMFeedback",
    "UserFeedback",
    "create_message",

    # Type definitions
    "AgentConfig",
    "DepartmentConfig",
    "TaskRequest",
    "TaskResponse",
    "WorkflowState",
    "CritiqueResult",
    "ToolExecutionRequest",
    "ToolExecutionResult",
    "MemoryQuery",
    "MemoryEntry",
    "ConversationEntry",
    "SystemMetrics",
]
