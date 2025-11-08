"""
Task Memory - Episodic memory for generation attempts
Version: 3.1
Platform: Intel Mac (macOS Ventura) + Docker

Tracks all generation tasks with metrics for learning from failures
"""

import os
import json
from enum import Enum
from datetime import datetime
from typing import List, Dict, Optional
from uuid import uuid4
from pydantic import BaseModel


class TaskStatus(str, Enum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(str, Enum):
    SPRITE_GENERATION = "sprite_generation"
    BACKGROUND_GENERATION = "background_generation"
    SCRIPT_GENERATION = "script_generation"


class Task(BaseModel):
    task_id: str
    session_id: str
    task_type: TaskType
    status: TaskStatus
    description: str
    
    # Timestamps
    proposed_at: datetime
    approved_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Agent details
    assigned_department: str
    original_prompt: str
    refined_prompt: Optional[str] = None
    
    # Results
    artifacts: List[str] = []
    error_message: Optional[str] = None
    
    # Performance metrics
    generation_time_seconds: Optional[float] = None
    retry_count: int = 0


class TaskMemory:
    """Persistent task tracking with failure pattern analysis"""
    
    def __init__(self, db_path: str = "/app/agent_memory/tasks.json"):
        self.db_path = db_path
        self.tasks: Dict[str, Task] = {}
        self._load_tasks()
    
    def _load_tasks(self):
        """Load tasks from JSON file"""
        if os.path.exists(self.db_path):
            with open(self.db_path, 'r') as f:
                tasks_data = json.load(f)
                self.tasks = {
                    tid: Task(**data)
                    for tid, data in tasks_data.items()
                }
    
    def _save_tasks(self):
        """Persist tasks to JSON file"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with open(self.db_path, 'w') as f:
            tasks_data = {
                tid: task.dict()
                for tid, task in self.tasks.items()
            }
            json.dump(tasks_data, f, indent=2, default=str)
    
    def create_task(
        self,
        session_id: str,
        task_type: TaskType,
        description: str,
        department: str,
        original_prompt: str
    ) -> Task:
        """Create new task"""
        task = Task(
            task_id=str(uuid4()),
            session_id=session_id,
            task_type=task_type,
            status=TaskStatus.PROPOSED,
            description=description,
            proposed_at=datetime.utcnow(),
            assigned_department=department,
            original_prompt=original_prompt
        )
        
        self.tasks[task.task_id] = task
        self._save_tasks()
        
        return task
    
    def update_status(
        self,
        task_id: str,
        status: TaskStatus,
        **kwargs
    ) -> Task:
        """Update task status with optional fields"""
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        task.status = status
        
        # Set timestamps
        if status == TaskStatus.APPROVED:
            task.approved_at = datetime.utcnow()
        elif status == TaskStatus.IN_PROGRESS:
            task.started_at = datetime.utcnow()
        elif status == TaskStatus.COMPLETED:
            task.completed_at = datetime.utcnow()
            if task.started_at:
                task.generation_time_seconds = (
                    task.completed_at - task.started_at
                ).total_seconds()
        
        # Update additional fields
        for key, value in kwargs.items():
            if hasattr(task, key):
                setattr(task, key, value)
        
        self._save_tasks()
        return task
    
    def get_performance_stats(self, task_type: Optional[TaskType] = None) -> Dict:
        """Get performance metrics for completed tasks"""
        completed = [
            task for task in self.tasks.values()
            if task.status == TaskStatus.COMPLETED
            and task.generation_time_seconds is not None
        ]
        
        if task_type:
            completed = [t for t in completed if t.task_type == task_type]
        
        if not completed:
            return {"error": "No completed tasks found"}
        
        times = [t.generation_time_seconds for t in completed]
        
        return {
            "total_completed": len(completed),
            "avg_generation_time_seconds": sum(times) / len(times),
            "min_generation_time_seconds": min(times),
            "max_generation_time_seconds": max(times),
            "total_artifacts_generated": sum(len(t.artifacts) for t in completed)
        }
