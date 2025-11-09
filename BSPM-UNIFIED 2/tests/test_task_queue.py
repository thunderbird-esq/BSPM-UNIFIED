"""
Test Suite: Task Queue
Version: 3.2
Platform: Intel Mac (macOS Ventura) + Docker

Tests for priority queue and resource management.
"""

import pytest
import asyncio
from datetime import datetime
from backend.task_queue import (
    Task, TaskQueue, Priority, TaskStatus, ResourceMonitor
)
from tests.mocks import MockTaskFunction
from unittest.mock import Mock, patch, AsyncMock


class TestTask:
    """Test Task dataclass."""

    def test_task_creation(self):
        """Create task with default values."""
        task = Task(
            priority=Priority.NORMAL.value,
            submitted_at=datetime.now()
        )

        assert task.priority == Priority.NORMAL.value
        assert task.status == TaskStatus.PENDING
        assert task.task_id is not None

    def test_task_with_data(self):
        """Create task with plan and session."""
        plan = {'action': 'generate', 'sprite': 'knight'}
        task = Task(
            priority=Priority.HIGH.value,
            submitted_at=datetime.now(),
            session_id='test_session',
            plan=plan
        )

        assert task.session_id == 'test_session'
        assert task.plan == plan

    def test_task_ordering_by_priority(self):
        """Tasks are ordered by priority."""
        now = datetime.now()
        task_urgent = Task(priority=Priority.URGENT.value, submitted_at=now)
        task_high = Task(priority=Priority.HIGH.value, submitted_at=now)
        task_normal = Task(priority=Priority.NORMAL.value, submitted_at=now)
        task_low = Task(priority=Priority.LOW.value, submitted_at=now)

        tasks = [task_low, task_normal, task_urgent, task_high]
        sorted_tasks = sorted(tasks)

        assert sorted_tasks[0] == task_urgent
        assert sorted_tasks[1] == task_high
        assert sorted_tasks[2] == task_normal
        assert sorted_tasks[3] == task_low


class TestResourceMonitor:
    """Test ResourceMonitor class."""

    @pytest.mark.asyncio
    async def test_resources_available(self, mock_psutil):
        """Resources available when usage is low."""
        monitor = ResourceMonitor(
            cpu_threshold=95.0,
            memory_threshold=85.0,
            disk_threshold=95.0
        )

        # Mock shows healthy usage
        mock_psutil['cpu'].return_value = 50.0

        available = await monitor.check_resources()

        assert available is True
        assert monitor.is_overloaded is False

    @pytest.mark.asyncio
    async def test_cpu_overload_sustained(self, mock_psutil):
        """CPU overload detected after sustained high usage."""
        monitor = ResourceMonitor(
            cpu_threshold=95.0,
            memory_threshold=85.0,
            disk_threshold=95.0
        )

        # Simulate sustained high CPU
        mock_psutil['cpu'].return_value = 96.0

        # Need 6 consecutive high readings
        for i in range(5):
            available = await monitor.check_resources()
            assert available is True  # Not overloaded yet

        # 6th check should trigger overload
        available = await monitor.check_resources()
        assert available is False
        assert monitor.is_overloaded is True

    @pytest.mark.asyncio
    async def test_memory_overload_immediate(self, mock_psutil):
        """Memory overload detected immediately."""
        monitor = ResourceMonitor(
            cpu_threshold=95.0,
            memory_threshold=85.0,
            disk_threshold=95.0
        )

        mock_mem_obj = Mock()
        mock_mem_obj.percent = 90.0  # Above 85% threshold
        mock_psutil['memory'].return_value = mock_mem_obj

        available = await monitor.check_resources()

        assert available is False
        assert monitor.is_overloaded is True

    @pytest.mark.asyncio
    async def test_disk_overload_immediate(self, mock_psutil):
        """Disk overload detected immediately."""
        monitor = ResourceMonitor(
            cpu_threshold=95.0,
            memory_threshold=85.0,
            disk_threshold=95.0
        )

        mock_disk_obj = Mock()
        mock_disk_obj.percent = 96.0  # Above 95% threshold
        mock_psutil['disk'].return_value = mock_disk_obj

        available = await monitor.check_resources()

        assert available is False
        assert monitor.is_overloaded is True

    @pytest.mark.asyncio
    async def test_recovery_from_overload(self, mock_psutil):
        """System recovers from overload state."""
        monitor = ResourceMonitor(
            cpu_threshold=95.0,
            memory_threshold=85.0
        )

        # Trigger memory overload
        mock_mem_obj = Mock()
        mock_mem_obj.percent = 90.0
        mock_psutil['memory'].return_value = mock_mem_obj

        available = await monitor.check_resources()
        assert available is False

        # Memory usage drops
        mock_mem_obj.percent = 70.0
        available = await monitor.check_resources()

        assert available is True
        assert monitor.is_overloaded is False


class TestTaskQueue:
    """Test TaskQueue class."""

    @pytest.mark.asyncio
    async def test_submit_task(self):
        """Submit task to queue."""
        queue = TaskQueue(max_concurrent=1, enable_resource_monitoring=False)

        mock_func = MockTaskFunction()
        task_id = await queue.submit(
            func=mock_func,
            session_id='test_session',
            plan={'action': 'test'},
            priority=Priority.NORMAL
        )

        assert task_id is not None
        assert queue.queue.qsize() == 1

    @pytest.mark.asyncio
    @pytest.mark.timeout(5)
    async def test_execute_task(self):
        """Execute task from queue."""
        queue = TaskQueue(max_concurrent=1, enable_resource_monitoring=False)

        mock_func = MockTaskFunction(return_value="Task result")
        task_id = await queue.submit(
            func=mock_func,
            session_id='test_session',
            plan={'action': 'test'},
            priority=Priority.NORMAL
        )

        await queue.start()
        await asyncio.sleep(0.2)  # Wait for execution
        await queue.stop()

        # Check task completed
        status = queue.get_task_status(task_id)
        assert status is not None
        assert status['status'] == TaskStatus.COMPLETED.value
        assert status['result'] == "Task result"

    @pytest.mark.asyncio
    @pytest.mark.timeout(5)
    async def test_priority_ordering(self):
        """Tasks execute in priority order."""
        queue = TaskQueue(max_concurrent=1, enable_resource_monitoring=False)

        execution_order = []

        async def tracked_task(name):
            execution_order.append(name)
            return name

        # Submit in reverse priority order
        await queue.submit(
            func=lambda: tracked_task('low'),
            session_id='test',
            plan={},
            priority=Priority.LOW
        )
        await queue.submit(
            func=lambda: tracked_task('urgent'),
            session_id='test',
            plan={},
            priority=Priority.URGENT
        )
        await queue.submit(
            func=lambda: tracked_task('normal'),
            session_id='test',
            plan={},
            priority=Priority.NORMAL
        )

        await queue.start()
        await asyncio.sleep(0.3)
        await queue.stop()

        # Should execute in priority order
        assert execution_order[0] == 'urgent'
        assert execution_order[1] == 'normal'
        assert execution_order[2] == 'low'

    @pytest.mark.asyncio
    @pytest.mark.timeout(5)
    async def test_task_timeout(self):
        """Task times out after max_execution_time."""
        queue = TaskQueue(
            max_concurrent=1,
            max_execution_time=0.2,
            enable_resource_monitoring=False
        )

        # Task that takes too long
        mock_func = MockTaskFunction(delay=1.0)
        task_id = await queue.submit(
            func=mock_func,
            session_id='test',
            plan={},
            priority=Priority.NORMAL
        )

        await queue.start()
        await asyncio.sleep(0.5)
        await queue.stop()

        status = queue.get_task_status(task_id)
        assert status['status'] == TaskStatus.TIMEOUT.value

    @pytest.mark.asyncio
    @pytest.mark.timeout(5)
    async def test_task_failure(self):
        """Task failure is recorded."""
        queue = TaskQueue(max_concurrent=1, enable_resource_monitoring=False)

        mock_func = MockTaskFunction(raise_exception=ValueError("Task failed"))
        task_id = await queue.submit(
            func=mock_func,
            session_id='test',
            plan={},
            priority=Priority.NORMAL
        )

        await queue.start()
        await asyncio.sleep(0.2)
        await queue.stop()

        status = queue.get_task_status(task_id)
        assert status['status'] == TaskStatus.FAILED.value
        assert 'Task failed' in status['error']

    @pytest.mark.asyncio
    async def test_get_queue_stats(self):
        """Get queue statistics."""
        queue = TaskQueue(max_concurrent=2, enable_resource_monitoring=False)

        # Submit some tasks
        await queue.submit(
            func=MockTaskFunction(delay=0.5),
            session_id='test',
            plan={},
            priority=Priority.NORMAL
        )
        await queue.submit(
            func=MockTaskFunction(delay=0.5),
            session_id='test',
            plan={},
            priority=Priority.NORMAL
        )

        stats = queue.get_queue_stats()

        assert 'pending' in stats
        assert 'running' in stats
        assert 'completed' in stats
        assert 'failed' in stats
        assert stats['max_concurrent'] == 2

    @pytest.mark.asyncio
    @pytest.mark.timeout(5)
    async def test_concurrent_task_limit(self):
        """Respects max_concurrent limit."""
        queue = TaskQueue(max_concurrent=2, enable_resource_monitoring=False)

        # Track concurrent executions
        concurrent_count = 0
        max_concurrent = 0

        async def concurrent_task():
            nonlocal concurrent_count, max_concurrent
            concurrent_count += 1
            max_concurrent = max(max_concurrent, concurrent_count)
            await asyncio.sleep(0.1)
            concurrent_count -= 1

        # Submit 5 tasks
        for i in range(5):
            await queue.submit(
                func=concurrent_task,
                session_id='test',
                plan={},
                priority=Priority.NORMAL
            )

        await queue.start()
        await asyncio.sleep(0.5)
        await queue.stop()

        # Should never exceed max_concurrent
        assert max_concurrent <= 2

    @pytest.mark.asyncio
    @pytest.mark.timeout(5)
    async def test_resource_monitoring_pauses_execution(self, mock_psutil):
        """Task execution pauses when resources unavailable."""
        queue = TaskQueue(max_concurrent=1, enable_resource_monitoring=True)

        # Simulate overloaded system
        mock_mem_obj = Mock()
        mock_mem_obj.percent = 90.0  # Above threshold
        mock_psutil['memory'].return_value = mock_mem_obj

        mock_func = MockTaskFunction()
        await queue.submit(
            func=mock_func,
            session_id='test',
            plan={},
            priority=Priority.NORMAL
        )

        await queue.start()
        await asyncio.sleep(0.2)

        # Task should not have executed due to resource constraints
        assert mock_func.call_count == 0

        await queue.stop()


# Run with: pytest tests/test_task_queue.py -v
# Run with coverage: pytest tests/test_task_queue.py --cov=backend.task_queue
