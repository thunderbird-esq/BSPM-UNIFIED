"""
Task Queue with Resource Management
Version: 3.2
Platform: Intel Mac (macOS Ventura) + Docker

Manages concurrent sprite generation with resource limits and prioritization.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid
import psutil

logger = logging.getLogger(__name__)


class Priority(Enum):
    """Task priority levels."""
    LOW = 3
    NORMAL = 2
    HIGH = 1
    URGENT = 0


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass(order=True)
class Task:
    """
    Queued task for sprite generation.
    
    Tasks are ordered by:
    1. Priority (urgent > high > normal > low)
    2. Submission time (FIFO within same priority)
    """
    
    # Priority for sorting (lower = higher priority)
    priority: int = field(compare=True)
    
    # Submission time for FIFO within priority
    submitted_at: datetime = field(compare=True)
    
    # Task data (not used for comparison)
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()), compare=False)
    session_id: str = field(default="", compare=False)
    plan: Dict[str, Any] = field(default_factory=dict, compare=False)
    func: Optional[Callable] = field(default=None, compare=False)
    status: TaskStatus = field(default=TaskStatus.PENDING, compare=False)
    started_at: Optional[datetime] = field(default=None, compare=False)
    completed_at: Optional[datetime] = field(default=None, compare=False)
    result: Any = field(default=None, compare=False)
    error: Optional[str] = field(default=None, compare=False)


class ResourceMonitor:
    """
    Monitors system resources to prevent overload.
    
    Pauses new task execution if:
    - CPU > 95% for 30 seconds
    - Memory > 85%
    - Disk > 95%
    """
    
    def __init__(
        self,
        cpu_threshold: float = 95.0,
        memory_threshold: float = 85.0,
        disk_threshold: float = 95.0,
        check_interval: float = 5.0
    ):
        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold
        self.disk_threshold = disk_threshold
        self.check_interval = check_interval
        
        self.is_overloaded = False
        self.high_cpu_count = 0  # Number of consecutive high CPU readings
    
    async def check_resources(self) -> bool:
        """
        Check if system has resources available for new tasks.
        
        Returns:
            True if resources available, False if overloaded
        """
        cpu_percent = psutil.cpu_percent(interval=1)
        memory_percent = psutil.virtual_memory().percent
        disk_percent = psutil.disk_usage('/').percent
        
        # Check CPU (must be high for 30s = 6 consecutive checks)
        if cpu_percent > self.cpu_threshold:
            self.high_cpu_count += 1
            if self.high_cpu_count >= 6:
                if not self.is_overloaded:
                    logger.warning(
                        "System overloaded: CPU sustained above threshold",
                        extra={
                            'cpu_percent': cpu_percent,
                            'threshold': self.cpu_threshold
                        }
                    )
                self.is_overloaded = True
                return False
        else:
            self.high_cpu_count = 0
        
        # Check memory (immediate)
        if memory_percent > self.memory_threshold:
            if not self.is_overloaded:
                logger.warning(
                    "System overloaded: Memory above threshold",
                    extra={
                        'memory_percent': memory_percent,
                        'threshold': self.memory_threshold
                    }
                )
            self.is_overloaded = True
            return False
        
        # Check disk (immediate)
        if disk_percent > self.disk_threshold:
            if not self.is_overloaded:
                logger.warning(
                    "System overloaded: Disk above threshold",
                    extra={
                        'disk_percent': disk_percent,
                        'threshold': self.disk_threshold
                    }
                )
            self.is_overloaded = True
            return False
        
        # All checks passed
        if self.is_overloaded:
            logger.info("System resources recovered, resuming task execution")
        self.is_overloaded = False
        return True


class TaskQueue:
    """
    Priority queue for sprite generation tasks with resource management.
    
    Features:
    - Priority-based execution (urgent > high > normal > low)
    - Configurable concurrency limit (default: 1 for Intel Mac CPU)
    - Resource monitoring (pause if CPU/memory/disk overloaded)
    - Timeout handling (kill jobs after max_execution_time)
    - Task cancellation
    """
    
    def __init__(
        self,
        max_concurrent: int = 1,
        max_execution_time: float = 600,  # 10 minutes
        enable_resource_monitoring: bool = True
    ):
        self.max_concurrent = max_concurrent
        self.max_execution_time = max_execution_time
        
        self.queue: asyncio.PriorityQueue[Task] = asyncio.PriorityQueue()
        self.running_tasks: Dict[str, Task] = {}
        self.completed_tasks: Dict[str, Task] = {}
        self.failed_tasks: Dict[str, Task] = {}
        
        self.resource_monitor = ResourceMonitor() if enable_resource_monitoring else None
        self.is_running = False
        self.worker_task: Optional[asyncio.Task] = None
        
        logger.info(
            "Task queue initialized",
            extra={
                'max_concurrent': max_concurrent,
                'max_execution_time': max_execution_time,
                'resource_monitoring': enable_resource_monitoring
            }
        )
    
    async def submit(
        self,
        func: Callable,
        session_id: str,
        plan: Dict[str, Any],
        priority: Priority = Priority.NORMAL
    ) -> str:
        """
        Submit a task to the queue.
        
        Args:
            func: Async function to execute
            session_id: Session ID for the task
            plan: Generation plan
            priority: Task priority
        
        Returns:
            Task ID
        """
        task = Task(
            priority=priority.value,
            submitted_at=datetime.now(),
            session_id=session_id,
            plan=plan,
            func=func
        )
        
        await self.queue.put(task)
        
        logger.info(
            f"Task {task.task_id} submitted to queue",
            extra={
                'task_id': task.task_id,
                'session_id': session_id,
                'priority': priority.name,
                'queue_size': self.queue.qsize()
            }
        )
        
        return task.task_id
    
    async def start(self):
        """Start processing tasks from the queue."""
        if self.is_running:
            logger.warning("Task queue already running")
            return
        
        self.is_running = True
        self.worker_task = asyncio.create_task(self._worker())
        logger.info("Task queue started")
    
    async def stop(self):
        """Stop processing tasks (wait for running tasks to complete)."""
        self.is_running = False
        
        if self.worker_task:
            await self.worker_task
        
        # Wait for running tasks to complete
        if self.running_tasks:
            logger.info(
                f"Waiting for {len(self.running_tasks)} running tasks to complete"
            )
            await asyncio.sleep(5)  # Grace period
        
        logger.info("Task queue stopped")
    
    async def _worker(self):
        """Worker loop that processes tasks from the queue."""
        while self.is_running:
            try:
                # Check if we can start new tasks
                if len(self.running_tasks) >= self.max_concurrent:
                    await asyncio.sleep(1)
                    continue
                
                # Check system resources
                if self.resource_monitor:
                    resources_available = await self.resource_monitor.check_resources()
                    if not resources_available:
                        logger.debug("System overloaded, pausing task execution")
                        await asyncio.sleep(self.resource_monitor.check_interval)
                        continue
                
                # Get next task (with timeout to check is_running periodically)
                try:
                    task = await asyncio.wait_for(
                        self.queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                # Execute task
                asyncio.create_task(self._execute_task(task))
                
            except Exception as e:
                logger.error(
                    "Error in task queue worker",
                    exc_info=True,
                    extra={'exception': str(e)}
                )
                await asyncio.sleep(1)
    
    async def _execute_task(self, task: Task):
        """Execute a single task with timeout handling."""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        self.running_tasks[task.task_id] = task
        
        logger.info(
            f"Executing task {task.task_id}",
            extra={
                'task_id': task.task_id,
                'session_id': task.session_id,
                'wait_time_seconds': (task.started_at - task.submitted_at).total_seconds()
            }
        )
        
        try:
            # Execute with timeout
            task.result = await asyncio.wait_for(
                task.func(),
                timeout=self.max_execution_time
            )
            
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            self.completed_tasks[task.task_id] = task
            
            execution_time = (task.completed_at - task.started_at).total_seconds()
            logger.info(
                f"Task {task.task_id} completed successfully",
                extra={
                    'task_id': task.task_id,
                    'execution_time_seconds': execution_time
                }
            )
            
        except asyncio.TimeoutError:
            task.status = TaskStatus.TIMEOUT
            task.error = f"Task exceeded max execution time ({self.max_execution_time}s)"
            task.completed_at = datetime.now()
            self.failed_tasks[task.task_id] = task
            
            logger.error(
                f"Task {task.task_id} timed out",
                extra={
                    'task_id': task.task_id,
                    'max_execution_time': self.max_execution_time
                }
            )
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.now()
            self.failed_tasks[task.task_id] = task
            
            logger.error(
                f"Task {task.task_id} failed",
                exc_info=True,
                extra={
                    'task_id': task.task_id,
                    'exception': str(e)
                }
            )
            
        finally:
            # Remove from running tasks
            self.running_tasks.pop(task.task_id, None)
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a task by ID."""
        # Check running tasks
        if task_id in self.running_tasks:
            task = self.running_tasks[task_id]
            return {
                'task_id': task.task_id,
                'status': task.status.value,
                'submitted_at': task.submitted_at.isoformat(),
                'started_at': task.started_at.isoformat() if task.started_at else None
            }
        
        # Check completed tasks
        if task_id in self.completed_tasks:
            task = self.completed_tasks[task_id]
            return {
                'task_id': task.task_id,
                'status': task.status.value,
                'submitted_at': task.submitted_at.isoformat(),
                'started_at': task.started_at.isoformat() if task.started_at else None,
                'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                'result': task.result
            }
        
        # Check failed tasks
        if task_id in self.failed_tasks:
            task = self.failed_tasks[task_id]
            return {
                'task_id': task.task_id,
                'status': task.status.value,
                'submitted_at': task.submitted_at.isoformat(),
                'started_at': task.started_at.isoformat() if task.started_at else None,
                'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                'error': task.error
            }
        
        return None
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        return {
            'pending': self.queue.qsize(),
            'running': len(self.running_tasks),
            'completed': len(self.completed_tasks),
            'failed': len(self.failed_tasks),
            'max_concurrent': self.max_concurrent,
            'resource_overload': self.resource_monitor.is_overloaded if self.resource_monitor else False
        }

    def prune_history(self, max_items: int = 1000):
        """
        Prune task history to keep only the most recent max_items tasks.

        Removes oldest completed and failed tasks to prevent unbounded memory growth.

        Args:
            max_items: Maximum number of tasks to keep in history (combined completed + failed)

        Returns:
            Number of tasks removed
        """
        total_history = len(self.completed_tasks) + len(self.failed_tasks)

        if total_history <= max_items:
            return 0

        # Combine all historical tasks with their completion times
        all_tasks = []

        for task_id, task in self.completed_tasks.items():
            all_tasks.append((task_id, task.completed_at, 'completed'))

        for task_id, task in self.failed_tasks.items():
            all_tasks.append((task_id, task.completed_at, 'failed'))

        # Sort by completion time (oldest first)
        all_tasks.sort(key=lambda x: x[1] if x[1] else datetime.min)

        # Calculate how many to remove
        to_remove_count = total_history - max_items
        tasks_to_remove = all_tasks[:to_remove_count]

        # Remove old tasks
        removed_count = 0
        for task_id, _, task_type in tasks_to_remove:
            if task_type == 'completed' and task_id in self.completed_tasks:
                del self.completed_tasks[task_id]
                removed_count += 1
            elif task_type == 'failed' and task_id in self.failed_tasks:
                del self.failed_tasks[task_id]
                removed_count += 1

        if removed_count > 0:
            logger.info(
                f"Pruned {removed_count} old tasks from history",
                extra={
                    'removed_count': removed_count,
                    'max_items': max_items,
                    'remaining_completed': len(self.completed_tasks),
                    'remaining_failed': len(self.failed_tasks)
                }
            )

        return removed_count


# Global task queue instance
task_queue = TaskQueue(
    max_concurrent=1,  # Intel Mac: 1 concurrent generation
    max_execution_time=600,  # 10 minutes
    enable_resource_monitoring=True
)
