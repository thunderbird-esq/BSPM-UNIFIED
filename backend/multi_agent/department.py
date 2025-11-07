"""
Department class for managing agent pair collaboration.

This module defines the Department class that coordinates two agents
(executor and critic) working together through an iterative workflow.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio
import logging

from .agent import StudioAgent
from .types import (
    TaskRequest,
    TaskResponse,
    TaskStatus,
    WorkflowState,
    AgentRole,
)

# Configure logging
logger = logging.getLogger(__name__)


class Department:
    """
    Contains 2 agents that collaborate on tasks.
    Manages workflow: propose → critique → revise → approve

    The department coordinates the interaction between an executor agent
    (who does the work) and a critic agent (who reviews and provides feedback).
    This creates an iterative improvement loop until work is approved or
    escalated to the PM Agent.

    Attributes:
        name: Department name (e.g., "Art", "Music", "Narrative")
        executor: Agent A who executes tasks
        critic: Agent B who critiques work
        max_iterations: Maximum critique-revision cycles before escalation
        workflow_history: History of all task workflows
    """

    def __init__(
        self,
        name: str,
        executor: StudioAgent,
        critic: StudioAgent,
        max_iterations: int = 3,
    ):
        """
        Initialize a department with executor and critic agents.

        Args:
            name: Department name
            executor: Executor agent (Agent A)
            critic: Critic agent (Agent B)
            max_iterations: Maximum iteration cycles (default: 3)

        Raises:
            ValueError: If agents have wrong roles or same department mismatch
        """
        # Validate agent roles
        if executor.role != AgentRole.EXECUTOR:
            raise ValueError(f"Executor agent must have EXECUTOR role, got {executor.role}")
        if critic.role != AgentRole.CRITIC:
            raise ValueError(f"Critic agent must have CRITIC role, got {critic.role}")

        # Validate department alignment
        if executor.department != name or critic.department != name:
            raise ValueError(
                f"Agent departments must match department name '{name}'. "
                f"Got executor: {executor.department}, critic: {critic.department}"
            )

        self.name = name
        self.executor = executor
        self.critic = critic
        self.max_iterations = max_iterations

        # Link agents together as partners
        executor.partner = critic
        critic.partner = executor

        # Workflow tracking
        self.workflow_history: List[Dict[str, Any]] = []
        self.active_tasks: Dict[str, WorkflowState] = {}

        logger.info(
            f"Initialized department '{name}' with executor '{executor.name}' "
            f"and critic '{critic.name}' (max_iterations={max_iterations})"
        )

    async def execute_task(self, task: TaskRequest) -> TaskResponse:
        """
        Main workflow for department collaboration.

        Process:
        1. Executor thinks about task
        2. Executor does work
        3. Executor shows to Critic
        4. Critic thinks and critiques
        5. Iteration loop (max iterations):
           - If not approved: Executor revises
           - Critic reviews again
        6. Return approved work or escalate to PM

        Args:
            task: Task request with id, description, tool, params

        Returns:
            TaskResponse with status, result, iterations, critique_history

        Example:
            >>> task = TaskRequest(
            ...     description="Create boss sprite",
            ...     tool="comfyui",
            ...     params={"style": "pixel_art"}
            ... )
            >>> response = await dept.execute_task(task)
            >>> print(f"Status: {response.status}, Iterations: {response.iterations}")
        """
        logger.info(f"Department '{self.name}' starting task {task.id}: {task.description}")

        start_time = datetime.now()

        # Initialize workflow state
        workflow = WorkflowState(
            task_id=task.id,
            status=TaskStatus.IN_PROGRESS,
            max_iterations=self.max_iterations,
            started_at=start_time,
        )
        self.active_tasks[task.id] = workflow

        try:
            # Step 1: Executor thinks about the task
            await self._executor_think_phase(task, workflow)

            # Step 2: Executor does the work
            work_result = await self._executor_work_phase(task, workflow)
            workflow.work_artifact = work_result

            # Step 3 & 4: Show to critic and get initial critique
            critique = await self._critic_review_phase(work_result, workflow)

            # Step 5: Iteration loop - revise until approved or max iterations
            while not critique["approved"] and workflow.can_continue():
                workflow.increment_iteration()
                workflow.status = TaskStatus.IN_REVISION

                logger.info(
                    f"Task {task.id} iteration {workflow.current_iteration}/{self.max_iterations}"
                )

                # Executor revises based on critique
                work_result = await self._executor_revise_phase(work_result, critique, workflow)
                workflow.work_artifact = work_result

                # Critic reviews the revision
                critique = await self._critic_review_phase(work_result, workflow)

            # Step 6: Determine final status
            if critique["approved"]:
                workflow.status = TaskStatus.APPROVED
                logger.info(f"Task {task.id} approved after {workflow.current_iteration} iterations")
            else:
                workflow.status = TaskStatus.NEEDS_HELP
                logger.warning(
                    f"Task {task.id} needs help - max iterations reached without approval"
                )

            # Calculate execution time
            total_time = (datetime.now() - start_time).total_seconds()

            # Build response
            response = TaskResponse(
                task_id=task.id,
                status=workflow.status,
                result=workflow.work_artifact,
                iterations=workflow.current_iteration,
                critique_history=self._extract_critique_history(workflow),
                total_time_seconds=total_time,
            )

            # Record in history
            self._record_workflow(task, workflow, response)

            logger.info(
                f"Task {task.id} completed: status={response.status}, "
                f"iterations={response.iterations}, time={total_time:.2f}s"
            )

            return response

        except Exception as e:
            logger.error(f"Task {task.id} failed with error: {e}", exc_info=True)

            # Mark as failed
            workflow.status = TaskStatus.FAILED
            total_time = (datetime.now() - start_time).total_seconds()

            response = TaskResponse(
                task_id=task.id,
                status=TaskStatus.FAILED,
                result=None,
                iterations=workflow.current_iteration,
                critique_history=self._extract_critique_history(workflow),
                total_time_seconds=total_time,
                error_message=str(e),
            )

            self._record_workflow(task, workflow, response)

            return response

        finally:
            # Clean up active task
            if task.id in self.active_tasks:
                del self.active_tasks[task.id]

    async def handle_pm_feedback(
        self,
        feedback: str,
        task_id: Optional[str] = None,
        feedback_type: str = "guidance"
    ) -> None:
        """
        Process feedback from PM Agent.

        Distributes the feedback to both agents so they can incorporate
        it into their future work.

        Args:
            feedback: Feedback content from PM
            task_id: Optional task ID this feedback relates to
            feedback_type: Type of feedback (guidance, correction, etc.)

        Example:
            >>> await dept.handle_pm_feedback(
            ...     "Great work! Consider using warmer colors next time.",
            ...     task_id="task_123",
            ...     feedback_type="praise"
            ... )
        """
        logger.info(f"Department '{self.name}' received PM feedback for task {task_id}")

        # Both agents think about the feedback
        await asyncio.gather(
            self.executor.think(
                f"PM feedback received: {feedback}",
                context=f"Task: {task_id}, Type: {feedback_type}"
            ),
            self.critic.think(
                f"PM feedback received: {feedback}",
                context=f"Task: {task_id}, Type: {feedback_type}"
            )
        )

        logger.debug(f"PM feedback distributed to {self.executor.name} and {self.critic.name}")

    async def _executor_think_phase(self, task: TaskRequest, workflow: WorkflowState) -> None:
        """
        Phase 1: Executor thinks about the task.

        Args:
            task: Task to execute
            workflow: Current workflow state
        """
        thinking = await self.executor.think(
            f"Analyzing task: {task.description}",
            context=f"Tool: {task.tool}, Params: {task.params}"
        )

        workflow.add_history_entry("executor_thinking", {
            "agent": self.executor.name,
            "thought": thinking,
        })

    async def _executor_work_phase(self, task: TaskRequest, workflow: WorkflowState) -> Any:
        """
        Phase 2: Executor does the work.

        Args:
            task: Task to execute
            workflow: Current workflow state

        Returns:
            Work artifact result
        """
        logger.debug(f"Executor {self.executor.name} working on task {task.id}")

        # Execute the tool
        work_result = await self.executor.use_tool(
            task.tool,
            purpose=task.description,
            **task.params
        )

        workflow.add_history_entry("executor_work", {
            "agent": self.executor.name,
            "tool": task.tool,
            "result": work_result,
        })

        workflow.status = TaskStatus.AWAITING_CRITIQUE

        return work_result

    async def _critic_review_phase(
        self,
        work_result: Any,
        workflow: WorkflowState
    ) -> Dict[str, Any]:
        """
        Phase 3 & 4: Critic thinks about and critiques the work.

        Args:
            work_result: Work to critique
            workflow: Current workflow state

        Returns:
            Critique result dictionary
        """
        logger.debug(f"Critic {self.critic.name} reviewing work for task {workflow.task_id}")

        # Critic thinks about the work
        thinking = await self.critic.think(
            "Reviewing work from partner",
            context=f"Task: {workflow.task_id}, Iteration: {workflow.current_iteration}"
        )

        workflow.add_history_entry("critic_thinking", {
            "agent": self.critic.name,
            "thought": thinking,
        })

        # Critic provides critique
        critique = await self.critic.critique(
            work_result,
            work_reference=workflow.task_id
        )

        workflow.current_critique = critique
        workflow.add_history_entry("critique", {
            "agent": self.critic.name,
            "critique": critique,
        })

        return critique

    async def _executor_revise_phase(
        self,
        work_result: Any,
        critique: Dict[str, Any],
        workflow: WorkflowState
    ) -> Any:
        """
        Phase 5: Executor revises work based on critique.

        Args:
            work_result: Original work
            critique: Critique to address
            workflow: Current workflow state

        Returns:
            Revised work artifact
        """
        logger.debug(
            f"Executor {self.executor.name} revising work for task {workflow.task_id} "
            f"(iteration {workflow.current_iteration})"
        )

        # Executor revises the work
        revised_work = await self.executor.revise(work_result, critique)

        workflow.add_history_entry("revision", {
            "agent": self.executor.name,
            "iteration": workflow.current_iteration,
            "changes": critique.get("suggestions", []),
        })

        return revised_work

    def _extract_critique_history(self, workflow: WorkflowState) -> List[Dict[str, Any]]:
        """
        Extract critique history from workflow.

        Args:
            workflow: Workflow state

        Returns:
            List of critique entries
        """
        critiques = []
        for entry in workflow.history:
            if entry["type"] == "critique":
                critiques.append(entry["data"])
        return critiques

    def _record_workflow(
        self,
        task: TaskRequest,
        workflow: WorkflowState,
        response: TaskResponse
    ) -> None:
        """
        Record completed workflow in history.

        Args:
            task: Original task
            workflow: Workflow state
            response: Task response
        """
        self.workflow_history.append({
            "task": task.model_dump(),
            "workflow": {
                "task_id": workflow.task_id,
                "status": workflow.status,
                "iterations": workflow.current_iteration,
                "history": workflow.history,
            },
            "response": response.model_dump(),
            "recorded_at": datetime.now(),
        })

    def get_stats(self) -> Dict[str, Any]:
        """
        Get department statistics.

        Returns:
            Dictionary with department statistics
        """
        total_tasks = len(self.workflow_history)
        approved_tasks = sum(
            1 for entry in self.workflow_history
            if entry["response"]["status"] == TaskStatus.APPROVED
        )
        failed_tasks = sum(
            1 for entry in self.workflow_history
            if entry["response"]["status"] == TaskStatus.FAILED
        )
        needs_help_tasks = sum(
            1 for entry in self.workflow_history
            if entry["response"]["status"] == TaskStatus.NEEDS_HELP
        )

        total_iterations = sum(
            entry["response"]["iterations"]
            for entry in self.workflow_history
        )
        avg_iterations = total_iterations / total_tasks if total_tasks > 0 else 0.0

        total_time = sum(
            entry["response"]["total_time_seconds"]
            for entry in self.workflow_history
        )
        avg_time = total_time / total_tasks if total_tasks > 0 else 0.0

        return {
            "name": self.name,
            "executor": self.executor.name,
            "critic": self.critic.name,
            "max_iterations": self.max_iterations,
            "total_tasks": total_tasks,
            "approved_tasks": approved_tasks,
            "failed_tasks": failed_tasks,
            "needs_help_tasks": needs_help_tasks,
            "active_tasks": len(self.active_tasks),
            "average_iterations": round(avg_iterations, 2),
            "average_time_seconds": round(avg_time, 2),
        }

    async def get_active_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of an active task.

        Args:
            task_id: Task ID to query

        Returns:
            Task status dictionary or None if not found
        """
        if task_id not in self.active_tasks:
            return None

        workflow = self.active_tasks[task_id]
        return {
            "task_id": workflow.task_id,
            "status": workflow.status,
            "current_iteration": workflow.current_iteration,
            "max_iterations": workflow.max_iterations,
            "can_continue": workflow.can_continue(),
            "started_at": workflow.started_at.isoformat() if workflow.started_at else None,
            "last_updated": workflow.last_updated.isoformat(),
        }
