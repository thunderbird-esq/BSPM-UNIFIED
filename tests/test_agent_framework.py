"""
Comprehensive tests for the multi-agent framework.

Tests cover:
- Agent initialization and configuration
- Message creation and communication
- Tool usage and execution
- Department coordination
- Critique-revision workflow
- Error handling and edge cases
"""

import pytest
import asyncio
from datetime import datetime
from typing import Dict, Any

# Import the multi-agent framework
from backend.multi_agent import (
    StudioAgent,
    Department,
    AgentRole,
    TaskStatus,
    SeverityLevel,
    MessageType,
    TaskRequest,
    TaskResponse,
    InternalThought,
    PeerMessage,
    Critique,
    ToolUsage,
    ToolResult,
    create_message,
    WorkflowState,
)


# Test 1: Agent Initialization
def test_agent_initialization():
    """Test that agents are initialized correctly with proper attributes."""
    agent = StudioAgent(
        name="Artist A",
        department="Art",
        role=AgentRole.EXECUTOR,
        tools=["comfyui", "aseprite_mcp"],
        llm_model="claude-sonnet-4"
    )

    assert agent.name == "Artist A"
    assert agent.department == "Art"
    assert agent.role == AgentRole.EXECUTOR
    assert "comfyui" in agent.tools
    assert "aseprite_mcp" in agent.tools
    assert agent.llm_model == "claude-sonnet-4"
    assert agent.partner is None
    assert len(agent.conversation_history) == 0
    assert agent.memory is None


# Test 2: Agent Think Creates Message
@pytest.mark.asyncio
async def test_agent_think_creates_message():
    """Test that agent.think() creates an internal thought message."""
    agent = StudioAgent(
        name="Artist A",
        department="Art",
        role=AgentRole.EXECUTOR,
        tools=["comfyui"]
    )

    reasoning = await agent.think("How should I approach this sprite?")

    # Check that reasoning was generated
    assert reasoning is not None
    assert len(reasoning) > 0

    # Check that message was logged
    assert len(agent.conversation_history) == 1
    message = agent.conversation_history[0]
    assert message["type"] == MessageType.INTERNAL_THOUGHT
    assert message["from_agent"] == "Artist A"
    assert message["department"] == "Art"


# Test 3: Agent Say to Partner
@pytest.mark.asyncio
async def test_agent_say_to_partner():
    """Test that agents can communicate with their partners."""
    executor = StudioAgent(
        name="Artist A",
        department="Art",
        role=AgentRole.EXECUTOR,
        tools=["comfyui"]
    )
    critic = StudioAgent(
        name="Artist B",
        department="Art",
        role=AgentRole.CRITIC,
        tools=[]
    )

    # Link agents as partners
    executor.partner = critic
    critic.partner = executor

    # Executor sends message to critic
    response = await executor.say_to_partner(
        "I've completed the sprite. Please review.",
        attachments=["sprite_001.png"],
        request_feedback=True
    )

    # Check response
    assert response["sent_to"] == "Artist B"
    assert response["message_id"] is not None
    assert response["response"] is not None

    # Check that message was logged
    assert len(executor.conversation_history) >= 1


# Test 4: Agent Critique - Executor Raises Error
@pytest.mark.asyncio
async def test_agent_critique_executor_raises_error():
    """Test that executor agents cannot critique (only critics can)."""
    executor = StudioAgent(
        name="Artist A",
        department="Art",
        role=AgentRole.EXECUTOR,
        tools=["comfyui"]
    )

    with pytest.raises(ValueError) as exc_info:
        await executor.critique({"work": "some_data"})

    assert "not a critic agent" in str(exc_info.value).lower()


# Test 5: Agent Critique Success
@pytest.mark.asyncio
async def test_agent_critique_success():
    """Test that critic agents can successfully critique work."""
    critic = StudioAgent(
        name="Artist B",
        department="Art",
        role=AgentRole.CRITIC,
        tools=[]
    )

    work_data = {"sprite": "boss_sprite.png", "resolution": "64x64"}
    critique_result = await critic.critique(work_data, work_reference="work_001")

    # Check critique result structure
    assert "approved" in critique_result
    assert "feedback" in critique_result
    assert "suggestions" in critique_result
    assert isinstance(critique_result["approved"], bool)
    assert isinstance(critique_result["feedback"], str)
    assert isinstance(critique_result["suggestions"], list)

    # Check that critique was logged
    assert len(critic.conversation_history) >= 1
    logged = critic.conversation_history[-1]
    assert logged["type"] == MessageType.CRITIQUE


# Test 6: Agent Use Tool - Not Available
@pytest.mark.asyncio
async def test_agent_use_tool_not_available():
    """Test that using unavailable tools raises an error."""
    agent = StudioAgent(
        name="Artist A",
        department="Art",
        role=AgentRole.EXECUTOR,
        tools=["comfyui"]
    )

    with pytest.raises(ValueError) as exc_info:
        await agent.use_tool("nonexistent_tool", param1="value1")

    assert "doesn't have access" in str(exc_info.value).lower()
    assert "nonexistent_tool" in str(exc_info.value)


# Test 7: Agent Use Tool Success
@pytest.mark.asyncio
async def test_agent_use_tool_success():
    """Test successful tool execution by an agent."""
    # Mock tool executor
    async def mock_tool_executor(tool_name: str, **kwargs) -> Dict[str, Any]:
        return {
            "status": "success",
            "tool": tool_name,
            "output": "generated_sprite.png",
            "params": kwargs
        }

    agent = StudioAgent(
        name="Artist A",
        department="Art",
        role=AgentRole.EXECUTOR,
        tools=["comfyui"],
        tool_executor=mock_tool_executor
    )

    result = await agent.use_tool("comfyui", prompt="fantasy boss", style="pixel_art")

    # Check result
    assert result["status"] == "success"
    assert result["tool"] == "comfyui"
    assert result["output"] == "generated_sprite.png"

    # Check that tool usage was logged
    tool_usage_msgs = [
        msg for msg in agent.conversation_history
        if msg.get("type") == MessageType.TOOL_USAGE
    ]
    assert len(tool_usage_msgs) >= 1

    tool_result_msgs = [
        msg for msg in agent.conversation_history
        if msg.get("type") == MessageType.TOOL_RESULT
    ]
    assert len(tool_result_msgs) >= 1


# Test 8: Department Links Agents
def test_department_link_agents():
    """Test that department correctly links executor and critic as partners."""
    executor = StudioAgent(
        name="Artist A",
        department="Art",
        role=AgentRole.EXECUTOR,
        tools=["comfyui"]
    )
    critic = StudioAgent(
        name="Artist B",
        department="Art",
        role=AgentRole.CRITIC,
        tools=[]
    )

    department = Department("Art", executor, critic, max_iterations=3)

    # Check that agents are linked
    assert executor.partner is critic
    assert critic.partner is executor
    assert department.executor is executor
    assert department.critic is critic
    assert department.max_iterations == 3


# Test 9: Department Execute Task - One Iteration
@pytest.mark.asyncio
async def test_department_execute_task_one_iteration():
    """Test department workflow with work approved on first iteration."""
    # Create agents with mock tool executor
    async def mock_tool_executor(tool_name: str, **kwargs) -> Dict[str, Any]:
        return {"status": "success", "output": "sprite.png"}

    executor = StudioAgent(
        name="Artist A",
        department="Art",
        role=AgentRole.EXECUTOR,
        tools=["comfyui"],
        tool_executor=mock_tool_executor
    )

    critic = StudioAgent(
        name="Artist B",
        department="Art",
        role=AgentRole.CRITIC,
        tools=[]
    )

    # Override critic's critique to approve immediately
    original_critique = critic._generate_critique
    async def mock_critique(*args, **kwargs):
        return {
            "approved": True,
            "feedback": "Excellent work!",
            "suggestions": [],
            "severity": SeverityLevel.MINOR,
            "confidence": 1.0
        }
    critic._generate_critique = mock_critique

    department = Department("Art", executor, critic, max_iterations=3)

    task = TaskRequest(
        description="Create boss sprite",
        tool="comfyui",
        params={"style": "pixel_art"}
    )

    response = await department.execute_task(task)

    # Check response
    assert response.status == TaskStatus.APPROVED
    assert response.iterations == 0  # Approved immediately, no revisions
    assert response.result is not None
    assert response.error_message is None


# Test 10: Department Execute Task - Multiple Iterations
@pytest.mark.asyncio
async def test_department_execute_task_multiple_iterations():
    """Test department workflow with multiple critique-revision cycles."""
    iteration_count = 0

    async def mock_tool_executor(tool_name: str, **kwargs) -> Dict[str, Any]:
        return {"status": "success", "output": f"sprite_v{iteration_count}.png"}

    executor = StudioAgent(
        name="Artist A",
        department="Art",
        role=AgentRole.EXECUTOR,
        tools=["comfyui"],
        tool_executor=mock_tool_executor
    )

    critic = StudioAgent(
        name="Artist B",
        department="Art",
        role=AgentRole.CRITIC,
        tools=[]
    )

    # Mock critique that approves after 2 iterations
    original_critique = critic._generate_critique
    async def mock_critique(*args, **kwargs):
        nonlocal iteration_count
        iteration_count += 1
        if iteration_count >= 2:
            return {
                "approved": True,
                "feedback": "Much better!",
                "suggestions": [],
                "severity": SeverityLevel.MINOR,
                "confidence": 1.0
            }
        else:
            return {
                "approved": False,
                "feedback": "Needs improvement",
                "suggestions": ["Add more detail", "Improve shading"],
                "severity": SeverityLevel.MODERATE,
                "confidence": 0.9
            }
    critic._generate_critique = mock_critique

    department = Department("Art", executor, critic, max_iterations=3)

    task = TaskRequest(
        description="Create boss sprite",
        tool="comfyui",
        params={"style": "pixel_art"}
    )

    response = await department.execute_task(task)

    # Check response
    assert response.status == TaskStatus.APPROVED
    assert response.iterations == 1  # One revision cycle
    assert len(response.critique_history) >= 2  # Initial critique + revision critique


# Test 11: Department Execute Task - Escalation
@pytest.mark.asyncio
async def test_department_execute_task_escalation():
    """Test department workflow escalates after max iterations."""
    async def mock_tool_executor(tool_name: str, **kwargs) -> Dict[str, Any]:
        return {"status": "success", "output": "sprite.png"}

    executor = StudioAgent(
        name="Artist A",
        department="Art",
        role=AgentRole.EXECUTOR,
        tools=["comfyui"],
        tool_executor=mock_tool_executor
    )

    critic = StudioAgent(
        name="Artist B",
        department="Art",
        role=AgentRole.CRITIC,
        tools=[]
    )

    # Mock critique that never approves
    async def mock_critique(*args, **kwargs):
        return {
            "approved": False,
            "feedback": "Still needs work",
            "suggestions": ["Try again"],
            "severity": SeverityLevel.CRITICAL,
            "confidence": 1.0
        }
    critic._generate_critique = mock_critique

    department = Department("Art", executor, critic, max_iterations=3)

    task = TaskRequest(
        description="Create boss sprite",
        tool="comfyui",
        params={"style": "pixel_art"}
    )

    response = await department.execute_task(task)

    # Check that task needs help after max iterations
    assert response.status == TaskStatus.NEEDS_HELP
    assert response.iterations == 3  # Hit max iterations
    assert len(response.critique_history) >= 3


# Test 12: Message Serialization
def test_message_serialization():
    """Test that messages can be serialized to dictionaries."""
    thought = InternalThought(
        from_agent="Artist A",
        department="Art",
        content="Analyzing the task requirements",
        context="Initial task planning"
    )

    thought_dict = thought.to_dict()

    # Check serialization
    assert thought_dict["type"] == MessageType.INTERNAL_THOUGHT
    assert thought_dict["from_agent"] == "Artist A"
    assert thought_dict["department"] == "Art"
    assert thought_dict["content"] == "Analyzing the task requirements"
    assert thought_dict["context"] == "Initial task planning"
    assert "id" in thought_dict
    assert "timestamp" in thought_dict


# Test 13: Message Validation
def test_message_validation():
    """Test that message validation works correctly."""
    # Valid peer message
    peer_msg = PeerMessage(
        from_agent="Artist A",
        department="Art",
        to_agent="Artist B",
        content="Here's the sprite for review"
    )
    assert peer_msg.from_agent == "Artist A"
    assert peer_msg.to_agent == "Artist B"

    # Invalid critique (empty feedback)
    with pytest.raises(Exception):  # Pydantic validation error
        Critique(
            from_agent="Artist B",
            department="Art",
            to_agent="Artist A",
            approved=False,
            feedback="",  # Too short
            suggestions=[]
        )


# Test 14: Workflow State Transitions
def test_workflow_state_transitions():
    """Test that workflow state transitions work correctly."""
    workflow = WorkflowState(
        task_id="task_123",
        status=TaskStatus.PENDING,
        max_iterations=3
    )

    # Check initial state
    assert workflow.status == TaskStatus.PENDING
    assert workflow.current_iteration == 0
    assert workflow.can_continue() is True

    # Add history and increment iteration
    workflow.add_history_entry("test_event", {"data": "test"})
    assert len(workflow.history) == 1

    workflow.increment_iteration()
    assert workflow.current_iteration == 1
    assert workflow.can_continue() is True

    # Increment to max
    workflow.increment_iteration()
    workflow.increment_iteration()
    assert workflow.current_iteration == 3
    assert workflow.can_continue() is False  # At max iterations


# Test 15: Agent Stats
def test_agent_stats():
    """Test that agent statistics are correctly tracked."""
    agent = StudioAgent(
        name="Artist A",
        department="Art",
        role=AgentRole.EXECUTOR,
        tools=["comfyui", "aseprite_mcp"]
    )

    # Log some messages
    agent.log_message(
        type=MessageType.INTERNAL_THOUGHT,
        from_agent=agent.name,
        department=agent.department,
        content="Test thought"
    )

    stats = agent.get_stats()

    assert stats["name"] == "Artist A"
    assert stats["department"] == "Art"
    assert stats["role"] == "executor"
    assert stats["message_count"] >= 1
    assert stats["has_partner"] is False
    assert stats["has_memory"] is False


# Test 16: Department Stats
@pytest.mark.asyncio
async def test_department_stats():
    """Test that department statistics are correctly tracked."""
    async def mock_tool_executor(tool_name: str, **kwargs) -> Dict[str, Any]:
        return {"status": "success", "output": "sprite.png"}

    executor = StudioAgent(
        name="Artist A",
        department="Art",
        role=AgentRole.EXECUTOR,
        tools=["comfyui"],
        tool_executor=mock_tool_executor
    )

    critic = StudioAgent(
        name="Artist B",
        department="Art",
        role=AgentRole.CRITIC,
        tools=[]
    )

    # Mock critique to approve
    async def mock_critique(*args, **kwargs):
        return {
            "approved": True,
            "feedback": "Good work",
            "suggestions": [],
            "severity": SeverityLevel.MINOR,
            "confidence": 1.0
        }
    critic._generate_critique = mock_critique

    department = Department("Art", executor, critic)

    # Execute a task
    task = TaskRequest(
        description="Create sprite",
        tool="comfyui",
        params={}
    )
    await department.execute_task(task)

    stats = department.get_stats()

    assert stats["name"] == "Art"
    assert stats["executor"] == "Artist A"
    assert stats["critic"] == "Artist B"
    assert stats["total_tasks"] == 1
    assert stats["approved_tasks"] >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
