"""
Batch Sprite Generator - Generate multiple sprites from templates
Version: 3.2
Platform: Intel Mac (macOS Ventura) + Docker

Supports CSV import, character set generation, and project templates.
"""

import logging
import csv
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from pathlib import Path
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class BatchRequest:
    """Single sprite in a batch generation request."""
    character: str
    action: str
    style: str
    priority: int = 2  # 0=urgent, 1=high, 2=normal, 3=low
    
    def to_prompt(self) -> str:
        """Convert to natural language prompt."""
        return f"{self.character} {self.action}, {self.style} style"


class BatchGenerator:
    """
    Generate multiple sprites in batch from templates.
    
    Features:
    - CSV import: Load batch requests from CSV file
    - Character sets: Generate full animation set for characters
    - Project templates: Pre-defined sprite collections
    """
    
    def __init__(self, task_queue):
        """
        Initialize batch generator.
        
        Args:
            task_queue: TaskQueue instance for job submission
        """
        self.task_queue = task_queue
    
    async def process_csv(
        self,
        csv_path: str,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Process CSV file with batch sprite requests.
        
        CSV Format:
            character,action,style,priority
            knight,idle,pixel art,normal
            wizard,attack,pixel art,normal
            archer,walk,pixel art,low
        
        Args:
            csv_path: Path to CSV file
            session_id: Session ID for all requests
        
        Returns:
            Dictionary with batch summary
        """
        requests = self._parse_csv(csv_path)
        
        logger.info(
            f"Processing batch CSV with {len(requests)} requests",
            extra={'csv_path': csv_path, 'num_requests': len(requests)}
        )
        
        # Submit all requests to task queue
        task_ids = []
        for req in requests:
            task_id = await self._submit_batch_request(req, session_id)
            task_ids.append(task_id)
        
        return {
            'batch_id': f"batch_{session_id}",
            'total_requests': len(requests),
            'task_ids': task_ids,
            'status': 'queued'
        }
    
    def _parse_csv(self, csv_path: str) -> List[BatchRequest]:
        """Parse CSV file into batch requests."""
        requests = []
        
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                # Map priority string to int
                priority_map = {
                    'urgent': 0,
                    'high': 1,
                    'normal': 2,
                    'low': 3
                }
                priority_str = row.get('priority', 'normal').lower()
                priority = priority_map.get(priority_str, 2)
                
                req = BatchRequest(
                    character=row['character'].strip(),
                    action=row['action'].strip(),
                    style=row['style'].strip(),
                    priority=priority
                )
                requests.append(req)
        
        return requests
    
    async def _submit_batch_request(
        self,
        request: BatchRequest,
        session_id: str
    ) -> str:
        """Submit single batch request to task queue."""
        from backend.task_queue import Priority
        
        # Map int priority to enum
        priority_map = {
            0: Priority.URGENT,
            1: Priority.HIGH,
            2: Priority.NORMAL,
            3: Priority.LOW
        }
        priority = priority_map.get(request.priority, Priority.NORMAL)
        
        # Create generation plan
        plan = {
            'department': 'Art',
            'task': f'Generate {request.character} sprite',
            'prompt': request.to_prompt(),
            'style': request.style
        }
        
        # Submit to queue (async function placeholder)
        # In real implementation, this would call the actual generation function
        task_id = await self.task_queue.submit(
            func=self._generate_sprite_placeholder,
            session_id=session_id,
            plan=plan,
            priority=priority
        )
        
        return task_id
    
    async def _generate_sprite_placeholder(self):
        """Placeholder for actual generation function."""
        # This would be replaced with actual ComfyUI generation call
        await asyncio.sleep(0.1)
        return {'status': 'completed'}
    
    async def generate_character_set(
        self,
        character_name: str,
        style: str,
        session_id: str,
        include_actions: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Generate complete animation set for a character.
        
        Standard character set includes:
        - Idle (1 frame repeated 8 times)
        - Walk (4-frame cycle)
        - Attack (2 frames)
        - Hurt (1 frame)
        - Jump (optional)
        - Crouch (optional)
        
        Args:
            character_name: Character description (e.g., "knight in armor")
            style: Art style (e.g., "pixel art")
            session_id: Session ID
            include_actions: Custom action list (uses defaults if None)
        
        Returns:
            Dictionary with batch summary
        """
        if include_actions is None:
            include_actions = ['idle', 'walk', 'attack', 'hurt']
        
        requests = []
        for action in include_actions:
            req = BatchRequest(
                character=character_name,
                action=action,
                style=style,
                priority=2
            )
            requests.append(req)
        
        logger.info(
            f"Generating character set for '{character_name}': {include_actions}",
            extra={
                'character': character_name,
                'actions': include_actions,
                'num_sprites': len(requests)
            }
        )
        
        # Submit all requests
        task_ids = []
        for req in requests:
            task_id = await self._submit_batch_request(req, session_id)
            task_ids.append(task_id)
        
        return {
            'batch_id': f"charset_{session_id}",
            'character': character_name,
            'actions': include_actions,
            'total_sprites': len(requests),
            'task_ids': task_ids,
            'status': 'queued'
        }
    
    async def apply_project_template(
        self,
        template_name: str,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Generate sprites from a project template.
        
        Available Templates:
        - platformer: Standard platformer game sprites
        - rpg: RPG character and enemy sprites
        - shooter: Top-down shooter sprites
        
        Args:
            template_name: Template identifier
            session_id: Session ID
        
        Returns:
            Dictionary with batch summary
        
        Raises:
            ValueError: If template not found
        """
        templates = {
            'platformer': [
                BatchRequest('player character', 'idle', 'pixel art', 1),
                BatchRequest('player character', 'walk', 'pixel art', 1),
                BatchRequest('player character', 'jump', 'pixel art', 1),
                BatchRequest('player character', 'attack', 'pixel art', 1),
                BatchRequest('enemy slime', 'idle', 'pixel art', 2),
                BatchRequest('enemy bat', 'fly', 'pixel art', 2),
                BatchRequest('collectible coin', 'spin', 'pixel art', 3),
                BatchRequest('health heart', 'idle', 'pixel art', 3),
            ],
            
            'rpg': [
                BatchRequest('hero knight', 'idle', 'pixel art', 1),
                BatchRequest('hero knight', 'walk', 'pixel art', 1),
                BatchRequest('hero knight', 'attack', 'pixel art', 1),
                BatchRequest('hero knight', 'hurt', 'pixel art', 1),
                BatchRequest('npc villager', 'idle', 'pixel art', 2),
                BatchRequest('npc merchant', 'idle', 'pixel art', 2),
                BatchRequest('enemy goblin', 'idle', 'pixel art', 2),
                BatchRequest('enemy skeleton', 'walk', 'pixel art', 2),
            ],
            
            'shooter': [
                BatchRequest('player ship', 'idle', 'pixel art', 1),
                BatchRequest('player ship', 'move left', 'pixel art', 1),
                BatchRequest('player ship', 'move right', 'pixel art', 1),
                BatchRequest('enemy ship small', 'idle', 'pixel art', 2),
                BatchRequest('enemy ship large', 'idle', 'pixel art', 2),
                BatchRequest('projectile bullet', 'idle', 'pixel art', 3),
                BatchRequest('explosion small', 'animate', 'pixel art', 3),
                BatchRequest('powerup shield', 'idle', 'pixel art', 3),
            ]
        }
        
        if template_name not in templates:
            raise ValueError(
                f"Unknown template: {template_name}. "
                f"Available: {list(templates.keys())}"
            )
        
        requests = templates[template_name]
        
        logger.info(
            f"Applying project template '{template_name}' with {len(requests)} sprites",
            extra={'template': template_name, 'num_sprites': len(requests)}
        )
        
        # Submit all requests
        task_ids = []
        for req in requests:
            task_id = await self._submit_batch_request(req, session_id)
            task_ids.append(task_id)
        
        return {
            'batch_id': f"template_{template_name}_{session_id}",
            'template': template_name,
            'total_sprites': len(requests),
            'task_ids': task_ids,
            'status': 'queued'
        }
    
    def get_batch_status(self, task_ids: List[str]) -> Dict[str, Any]:
        """
        Get status of a batch generation request.
        
        Args:
            task_ids: List of task IDs from batch
        
        Returns:
            Dictionary with batch progress
        """
        statuses = []
        for task_id in task_ids:
            status = self.task_queue.get_task_status(task_id)
            if status:
                statuses.append(status)
        
        # Calculate summary
        total = len(statuses)
        pending = sum(1 for s in statuses if s['status'] == 'pending')
        running = sum(1 for s in statuses if s['status'] == 'running')
        completed = sum(1 for s in statuses if s['status'] == 'completed')
        failed = sum(1 for s in statuses if s['status'] in ['failed', 'timeout'])
        
        return {
            'total': total,
            'pending': pending,
            'running': running,
            'completed': completed,
            'failed': failed,
            'progress_percent': (completed / total * 100) if total > 0 else 0,
            'tasks': statuses
        }


def create_batch_generator(task_queue) -> BatchGenerator:
    """Create BatchGenerator instance."""
    return BatchGenerator(task_queue)
