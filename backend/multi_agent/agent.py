"""
StudioAgent base class for all 12 studio agents.

This module defines the core agent class that enables AI agents to think,
communicate, use tools, and remember their work.
"""

from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
import asyncio
import logging
from uuid import uuid4

from .types import (
    AgentRole,
    SeverityLevel,
)
from .messages import (
    InternalThought,
    PeerMessage,
    Critique,
    ToolUsage,
    ToolResult,
    MessageType,
)

# Configure logging
logger = logging.getLogger(__name__)


class StudioAgent:
    """
    Base class for all 12 studio agents.
    Each agent can think, communicate, use tools, and remember.

    The agent operates in a collaborative environment with a partner agent
    (executor-critic pairs) and can interact with the PM Agent and user.

    Attributes:
        name: Agent's name (e.g., "Artist A")
        department: Department name (e.g., "Art")
        role: Agent role (EXECUTOR or CRITIC)
        tools: List of available tool names
        llm_model: LLM model identifier
        partner: Partner agent in the same department
        conversation_history: All messages sent/received
        memory: Memory system interface (set externally)
    """

    def __init__(
        self,
        name: str,
        department: str,
        role: AgentRole,
        tools: List[str],
        llm_model: str = "claude-sonnet-4",
        llm_client: Optional[Any] = None,
        tool_executor: Optional[Callable] = None,
    ):
        """
        Initialize a studio agent.

        Args:
            name: Agent name
            department: Department name
            role: Agent role (EXECUTOR or CRITIC)
            tools: List of available tools
            llm_model: LLM model to use
            llm_client: Optional LLM client for making API calls
            tool_executor: Optional function to execute tools
        """
        self.name = name
        self.department = department
        self.role = role
        self.tools = tools
        self.llm_model = llm_model
        self.llm_client = llm_client
        self.tool_executor = tool_executor

        self.partner: Optional['StudioAgent'] = None
        self.conversation_history: List[Dict[str, Any]] = []
        self.memory = None

        # Message queue for async communication
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._listeners: List[Callable] = []

        logger.info(f"Initialized agent: {name} ({department} - {role.value})")

    async def think(self, prompt: str, context: Optional[str] = None) -> str:
        """
        Internal reasoning - visible to user and PM Agent.

        The agent processes the prompt using its LLM to generate reasoning.
        This creates an internal_thought message that is logged and broadcasted.

        Args:
            prompt: The thought prompt or question
            context: Optional additional context

        Returns:
            The agent's reasoning as a string

        Example:
            >>> reasoning = await agent.think("How should I approach this sprite design?")
            >>> print(reasoning)
            "I should consider the pixel art style, color palette constraints..."
        """
        logger.debug(f"{self.name} thinking about: {prompt[:100]}...")

        # Generate reasoning using LLM (if available)
        reasoning = await self._generate_reasoning(prompt, context)

        # Create and log internal thought message
        thought = InternalThought(
            from_agent=self.name,
            department=self.department,
            content=reasoning,
            context=context,
        )

        message_id = self.log_message(**thought.to_dict())
        logger.info(f"{self.name} created thought {message_id}")

        return reasoning

    async def say_to_partner(
        self,
        message: str,
        attachments: Optional[List[str]] = None,
        request_feedback: bool = False
    ) -> Dict[str, Any]:
        """
        Send message to partner agent in the same department.

        Creates a peer_message and delivers it to the partner agent.
        Optionally waits for a response if request_feedback is True.

        Args:
            message: Message content
            attachments: Optional file paths or IDs
            request_feedback: Whether to wait for partner's response

        Returns:
            Dictionary containing partner's response (if requested) or confirmation

        Raises:
            ValueError: If no partner is set

        Example:
            >>> response = await executor.say_to_partner(
            ...     "I've created the sprite. What do you think?",
            ...     attachments=["sprite_001.png"],
            ...     request_feedback=True
            ... )
        """
        if not self.partner:
            raise ValueError(f"{self.name} has no partner agent set")

        logger.debug(f"{self.name} sending message to {self.partner.name}")

        # Create peer message
        peer_msg = PeerMessage(
            from_agent=self.name,
            department=self.department,
            to_agent=self.partner.name,
            content=message,
            attachments=attachments,
            request_feedback=request_feedback,
        )

        # Log the message
        message_id = self.log_message(**peer_msg.to_dict())

        # Deliver to partner
        response = await self.partner.receive_message(peer_msg.to_dict())

        logger.info(f"{self.name} sent message {message_id} to {self.partner.name}")

        return {
            "message_id": message_id,
            "sent_to": self.partner.name,
            "response": response if request_feedback else None,
        }

    async def critique(self, work: Any, work_reference: Optional[str] = None) -> Dict[str, Any]:
        """
        Provide critique on partner's work (CRITIC role only).

        Analyzes the work and provides structured feedback with approval status,
        feedback, and specific suggestions for improvement.

        Args:
            work: The work artifact to critique
            work_reference: Optional reference ID for the work

        Returns:
            Dictionary with critique result:
            {
                "approved": bool,
                "feedback": str,
                "suggestions": List[str],
                "severity": str,
                "confidence": float
            }

        Raises:
            ValueError: If called by non-critic agent

        Example:
            >>> result = await critic.critique(sprite_data, work_reference="sprite_001")
            >>> if not result["approved"]:
            ...     print(f"Issues found: {result['feedback']}")
        """
        if self.role != AgentRole.CRITIC:
            raise ValueError(f"{self.name} is not a critic agent and cannot critique")

        logger.debug(f"{self.name} critiquing work: {work_reference}")

        # Generate critique using LLM
        critique_result = await self._generate_critique(work, work_reference)

        # Create critique message
        critique_msg = Critique(
            from_agent=self.name,
            department=self.department,
            to_agent=self.partner.name if self.partner else "unknown",
            approved=critique_result["approved"],
            feedback=critique_result["feedback"],
            suggestions=critique_result["suggestions"],
            severity=critique_result.get("severity", SeverityLevel.MINOR),
            work_reference=work_reference,
            confidence=critique_result.get("confidence", 1.0),
        )

        # Log the critique
        self.log_message(**critique_msg.to_dict())

        logger.info(
            f"{self.name} critiqued work {work_reference}: "
            f"approved={critique_result['approved']}"
        )

        return critique_result

    async def use_tool(self, tool_name: str, **kwargs) -> Any:
        """
        Execute a tool and log the usage.

        Creates a tool_usage message, executes the tool, and logs the result.

        Args:
            tool_name: Name of the tool to execute
            **kwargs: Tool-specific parameters

        Returns:
            Tool execution result

        Raises:
            ValueError: If tool is not available to this agent

        Example:
            >>> result = await agent.use_tool(
            ...     "comfyui",
            ...     prompt="fantasy boss character",
            ...     style="pixel_art"
            ... )
        """
        if tool_name not in self.tools:
            raise ValueError(
                f"Agent {self.name} doesn't have access to tool '{tool_name}'. "
                f"Available tools: {', '.join(self.tools)}"
            )

        logger.debug(f"{self.name} using tool: {tool_name}")

        # Create tool usage message
        tool_usage = ToolUsage(
            from_agent=self.name,
            department=self.department,
            tool_name=tool_name,
            parameters=kwargs,
            purpose=kwargs.pop("purpose", None),
        )

        self.log_message(**tool_usage.to_dict())

        # Execute the tool
        start_time = datetime.now()
        try:
            if self.tool_executor:
                result = await self.tool_executor(tool_name, **kwargs)
                success = True
                error = None
            else:
                # Mock execution if no executor provided
                result = {"status": "mock", "tool": tool_name, "params": kwargs}
                success = True
                error = None
        except Exception as e:
            result = None
            success = False
            error = str(e)
            logger.error(f"{self.name} tool execution failed: {e}")

        execution_time = (datetime.now() - start_time).total_seconds()

        # Create tool result message
        tool_result = ToolResult(
            from_agent=self.name,
            department=self.department,
            tool_name=tool_name,
            request_id=tool_usage.request_id,
            success=success,
            result=result,
            error=error,
            execution_time_seconds=execution_time,
        )

        self.log_message(**tool_result.to_dict())

        logger.info(
            f"{self.name} executed tool {tool_name}: "
            f"success={success}, time={execution_time:.2f}s"
        )

        if not success:
            raise RuntimeError(f"Tool execution failed: {error}")

        return result

    async def revise(self, work: Any, critique: Dict[str, Any]) -> Any:
        """
        Revise work based on critique suggestions.

        Takes the original work and critique feedback, then generates
        an improved version addressing the suggestions.

        Args:
            work: Original work artifact
            critique: Critique dictionary with feedback and suggestions

        Returns:
            Revised work artifact

        Example:
            >>> revised_work = await executor.revise(
            ...     original_sprite,
            ...     critique_result
            ... )
        """
        logger.debug(f"{self.name} revising work based on critique")

        # Log revision intent as internal thought
        await self.think(
            f"Revising work based on feedback: {critique.get('feedback', 'N/A')}",
            context=f"Suggestions: {', '.join(critique.get('suggestions', []))}"
        )

        # Generate revised work using LLM or tool
        revised_work = await self._generate_revision(work, critique)

        logger.info(f"{self.name} completed revision")

        return revised_work

    def log_message(self, **kwargs) -> str:
        """
        Log message to conversation history and broadcast to UI.

        Args:
            **kwargs: Message data

        Returns:
            Message ID

        Example:
            >>> msg_id = agent.log_message(
            ...     type="internal_thought",
            ...     content="Processing task..."
            ... )
        """
        # Ensure message has an ID
        if "id" not in kwargs:
            kwargs["id"] = f"msg_{uuid4().hex[:12]}"

        # Ensure timestamp
        if "timestamp" not in kwargs:
            kwargs["timestamp"] = datetime.now()

        # Add to conversation history
        self.conversation_history.append(kwargs)

        # Broadcast to listeners (e.g., WebSocket connections)
        self._broadcast_message(kwargs)

        logger.debug(f"{self.name} logged message {kwargs['id']}")

        return kwargs["id"]

    async def receive_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle incoming message from partner or PM Agent.

        Processes the message and generates an appropriate response.

        Args:
            message: Message dictionary

        Returns:
            Response dictionary

        Example:
            >>> response = await agent.receive_message({
            ...     "type": "peer_message",
            ...     "from_agent": "Artist B",
            ...     "content": "What's the status?"
            ... })
        """
        logger.debug(f"{self.name} received message from {message.get('from_agent')}")

        # Add to message queue
        await self._message_queue.put(message)

        # Log receipt
        self.conversation_history.append({
            "id": f"rcv_{uuid4().hex[:12]}",
            "type": "message_received",
            "timestamp": datetime.now(),
            "message": message,
        })

        # Generate response based on message type
        message_type = message.get("type")

        if message_type == MessageType.PEER_MESSAGE:
            response_content = await self._handle_peer_message(message)
        elif message_type == MessageType.PM_FEEDBACK:
            response_content = await self._handle_pm_feedback(message)
        elif message_type == MessageType.CRITIQUE:
            response_content = await self._handle_critique_message(message)
        else:
            response_content = "Message received"

        return {
            "status": "received",
            "from": self.name,
            "response": response_content,
        }

    async def recall_from_memory(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Query agent's memory for relevant past work.

        Searches the memory system for content related to the query.

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of relevant memory entries

        Example:
            >>> memories = await agent.recall_from_memory(
            ...     "sprite designs with fire effects",
            ...     limit=3
            ... )
        """
        if not self.memory:
            logger.warning(f"{self.name} has no memory system configured")
            return []

        logger.debug(f"{self.name} querying memory: {query}")

        try:
            results = await self.memory.query_knowledge(
                query=query,
                agent_name=self.name,
                limit=limit,
            )
            logger.info(f"{self.name} found {len(results)} memory entries")
            return results
        except Exception as e:
            logger.error(f"{self.name} memory query failed: {e}")
            return []

    def add_listener(self, callback: Callable) -> None:
        """
        Add a listener for message broadcasts.

        Args:
            callback: Function to call with each broadcasted message
        """
        self._listeners.append(callback)

    def _broadcast_message(self, message: Dict[str, Any]) -> None:
        """
        Broadcast message to all listeners.

        Args:
            message: Message to broadcast
        """
        for listener in self._listeners:
            try:
                listener(message)
            except Exception as e:
                logger.error(f"Listener error: {e}")

    async def _generate_reasoning(self, prompt: str, context: Optional[str] = None) -> str:
        """
        Generate reasoning using LLM.

        Args:
            prompt: Reasoning prompt
            context: Optional context

        Returns:
            Generated reasoning
        """
        if self.llm_client:
            # TODO: Implement actual LLM call
            # For now, return a structured mock response
            return f"[{self.name} reasoning] Analyzing: {prompt}"
        else:
            return f"[Mock reasoning for {self.name}] {prompt}"

    async def _generate_critique(
        self,
        work: Any,
        work_reference: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate critique using LLM.

        Args:
            work: Work to critique
            work_reference: Work reference ID

        Returns:
            Critique result dictionary
        """
        if self.llm_client:
            # TODO: Implement actual LLM call for critique
            # For now, return a mock critique
            return {
                "approved": True,
                "feedback": "Work looks good with minor improvements needed.",
                "suggestions": ["Consider adding more detail", "Adjust color balance"],
                "severity": SeverityLevel.MINOR,
                "confidence": 0.9,
            }
        else:
            # Mock critique for testing
            return {
                "approved": False,
                "feedback": "Mock critique - work needs revision.",
                "suggestions": ["Mock suggestion 1", "Mock suggestion 2"],
                "severity": SeverityLevel.MODERATE,
                "confidence": 1.0,
            }

    async def _generate_revision(self, work: Any, critique: Dict[str, Any]) -> Any:
        """
        Generate revised work based on critique.

        Args:
            work: Original work
            critique: Critique result

        Returns:
            Revised work
        """
        # TODO: Implement actual revision logic
        # For now, return modified work indicating revision
        if isinstance(work, dict):
            revised = work.copy()
            revised["revised"] = True
            revised["revision_notes"] = critique.get("suggestions", [])
            return revised
        else:
            return work

    async def _handle_peer_message(self, message: Dict[str, Any]) -> str:
        """Handle peer message from partner agent"""
        content = message.get("content", "")
        return f"Acknowledged: {content[:50]}..."

    async def _handle_pm_feedback(self, message: Dict[str, Any]) -> str:
        """Handle feedback from PM Agent"""
        feedback = message.get("content", "")
        await self.think(f"Processing PM feedback: {feedback}")
        return "PM feedback acknowledged and incorporated"

    async def _handle_critique_message(self, message: Dict[str, Any]) -> str:
        """Handle critique from partner"""
        if message.get("approved"):
            return "Thank you for the approval!"
        else:
            return "I'll work on the suggested improvements"

    def get_stats(self) -> Dict[str, Any]:
        """
        Get agent statistics.

        Returns:
            Dictionary with agent statistics
        """
        return {
            "name": self.name,
            "department": self.department,
            "role": self.role.value,
            "tools": self.tools,
            "message_count": len(self.conversation_history),
            "has_partner": self.partner is not None,
            "has_memory": self.memory is not None,
        }
