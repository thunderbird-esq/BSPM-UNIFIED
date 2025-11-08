"""
Regeneration Manager - Handle sprite regeneration with variations
Version: 3.2
Platform: Intel Mac (macOS Ventura) + Docker

Manages regeneration requests with different seeds and parameter adjustments.
"""

import logging
import hashlib
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
import random

logger = logging.getLogger(__name__)


@dataclass
class GenerationAttempt:
    """
    Record of a single generation attempt.
    
    Tracks parameters used and validation results for analysis.
    """
    attempt_id: str
    seed: int
    preset: str
    parameters: Dict[str, Any]
    timestamp: datetime
    validation_result: Optional[Dict[str, Any]] = None
    sprite_id: Optional[str] = None
    status: str = "pending"  # pending, completed, failed
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'attempt_id': self.attempt_id,
            'seed': self.seed,
            'preset': self.preset,
            'parameters': self.parameters,
            'timestamp': self.timestamp.isoformat(),
            'validation_result': self.validation_result,
            'sprite_id': self.sprite_id,
            'status': self.status
        }


@dataclass
class RegenerationSession:
    """
    Tracks multiple generation attempts for the same prompt.
    
    Allows user to regenerate with different parameters until satisfied.
    """
    session_id: str
    original_prompt: str
    base_plan: Dict[str, Any]
    attempts: List[GenerationAttempt] = field(default_factory=list)
    best_attempt_id: Optional[str] = None
    
    def add_attempt(self, attempt: GenerationAttempt):
        """Add a generation attempt to this session."""
        self.attempts.append(attempt)
        logger.info(
            f"Added attempt {attempt.attempt_id} to session {self.session_id}",
            extra={
                'session_id': self.session_id,
                'attempt_id': attempt.attempt_id,
                'total_attempts': len(self.attempts)
            }
        )
    
    def mark_best(self, attempt_id: str):
        """Mark an attempt as the best result."""
        if not any(a.attempt_id == attempt_id for a in self.attempts):
            raise ValueError(f"Attempt {attempt_id} not found in session")
        
        self.best_attempt_id = attempt_id
        logger.info(
            f"Marked attempt {attempt_id} as best in session {self.session_id}",
            extra={'session_id': self.session_id, 'best_attempt': attempt_id}
        )
    
    def get_attempt(self, attempt_id: str) -> Optional[GenerationAttempt]:
        """Get a specific attempt by ID."""
        for attempt in self.attempts:
            if attempt.attempt_id == attempt_id:
                return attempt
        return None
    
    def get_failed_attempts(self) -> List[GenerationAttempt]:
        """Get all failed attempts for analysis."""
        return [a for a in self.attempts if a.status == "failed"]
    
    def get_successful_attempts(self) -> List[GenerationAttempt]:
        """Get all successful attempts."""
        return [a for a in self.attempts if a.status == "completed"]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'session_id': self.session_id,
            'original_prompt': self.original_prompt,
            'base_plan': self.base_plan,
            'attempts': [a.to_dict() for a in self.attempts],
            'best_attempt_id': self.best_attempt_id,
            'total_attempts': len(self.attempts),
            'successful_attempts': len(self.get_successful_attempts()),
            'failed_attempts': len(self.get_failed_attempts())
        }


class RegenerationManager:
    """
    Manages sprite regeneration with parameter variations.
    
    Features:
    - Automatic seed variation for regeneration
    - Parameter adjustment based on validation failures
    - History tracking for comparison
    - Best result selection
    """
    
    def __init__(self):
        self.sessions: Dict[str, RegenerationSession] = {}
    
    def create_session(
        self,
        session_id: str,
        original_prompt: str,
        base_plan: Dict[str, Any]
    ) -> RegenerationSession:
        """
        Create a new regeneration session.
        
        Args:
            session_id: Unique session identifier
            original_prompt: User's original prompt
            base_plan: Base generation plan
        
        Returns:
            RegenerationSession instance
        """
        session = RegenerationSession(
            session_id=session_id,
            original_prompt=original_prompt,
            base_plan=base_plan
        )
        
        self.sessions[session_id] = session
        logger.info(
            f"Created regeneration session {session_id}",
            extra={'session_id': session_id, 'prompt': original_prompt}
        )
        
        return session
    
    def regenerate_with_new_seed(
        self,
        session_id: str,
        preset: Optional[str] = None
    ) -> GenerationAttempt:
        """
        Create a new generation attempt with different seed.
        
        Args:
            session_id: Regeneration session ID
            preset: Optional style preset (uses original if not provided)
        
        Returns:
            GenerationAttempt with new seed
        
        Raises:
            ValueError: If session not found
        """
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")
        
        session = self.sessions[session_id]
        
        # Generate new seed (avoid collisions with previous attempts)
        existing_seeds = {a.seed for a in session.attempts}
        while True:
            new_seed = random.randint(1, 2**31 - 1)
            if new_seed not in existing_seeds:
                break
        
        # Create attempt
        attempt_id = self._generate_attempt_id(session_id, new_seed)
        
        attempt = GenerationAttempt(
            attempt_id=attempt_id,
            seed=new_seed,
            preset=preset or session.base_plan.get('preset', 'clean_pixel_art'),
            parameters=session.base_plan.copy(),
            timestamp=datetime.now()
        )
        
        session.add_attempt(attempt)
        
        logger.info(
            f"Created regeneration attempt with seed {new_seed}",
            extra={
                'session_id': session_id,
                'attempt_id': attempt_id,
                'seed': new_seed,
                'preset': attempt.preset
            }
        )
        
        return attempt
    
    def regenerate_with_adjusted_parameters(
        self,
        session_id: str,
        validation_failure: Dict[str, Any]
    ) -> GenerationAttempt:
        """
        Create regeneration attempt with parameters adjusted based on validation failure.
        
        Args:
            session_id: Regeneration session ID
            validation_failure: Validation result with failure details
        
        Returns:
            GenerationAttempt with adjusted parameters
        
        Adjustment Logic:
            - Low palette similarity → Increase CFG (stronger prompt adherence)
            - Blank frames → Increase steps (more detail generation)
            - Inconsistent motion → Add motion-specific negative prompts
        """
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")
        
        session = self.sessions[session_id]
        base_params = session.base_plan.copy()
        
        # Analyze failure and adjust parameters
        adjustments = self._calculate_parameter_adjustments(validation_failure)
        
        # Apply adjustments
        adjusted_params = base_params.copy()
        for key, value in adjustments.items():
            adjusted_params[key] = value
        
        # New seed
        new_seed = random.randint(1, 2**31 - 1)
        attempt_id = self._generate_attempt_id(session_id, new_seed)
        
        attempt = GenerationAttempt(
            attempt_id=attempt_id,
            seed=new_seed,
            preset=adjusted_params.get('preset', 'clean_pixel_art'),
            parameters=adjusted_params,
            timestamp=datetime.now()
        )
        
        session.add_attempt(attempt)
        
        logger.info(
            f"Created adjusted regeneration attempt",
            extra={
                'session_id': session_id,
                'attempt_id': attempt_id,
                'adjustments': adjustments,
                'failure_reason': validation_failure.get('errors', [])
            }
        )
        
        return attempt
    
    def _calculate_parameter_adjustments(
        self,
        validation_failure: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculate parameter adjustments based on validation failure.
        
        Args:
            validation_failure: Validation result
        
        Returns:
            Dictionary of parameter adjustments
        """
        adjustments = {}
        errors = validation_failure.get('errors', [])
        metrics = validation_failure.get('metrics', {})
        
        # Low palette similarity → Increase CFG
        if metrics.get('palette_similarity', 1.0) < 0.85:
            adjustments['cfg'] = min(12.0, adjustments.get('cfg', 8.0) + 1.0)
            adjustments['negative_prompt_boost'] = (
                "inconsistent colors, different palettes, "
                "varying tones, mismatched shading"
            )
            logger.debug("Adjusted CFG for palette consistency")
        
        # Blank frames → Increase steps
        if any('blank' in str(e).lower() for e in errors):
            adjustments['steps'] = min(30, adjustments.get('steps', 20) + 5)
            adjustments['positive_prompt_boost'] = (
                "detailed sprite, visible character, "
                "clear features, well-defined"
            )
            logger.debug("Increased steps for blank frame issue")
        
        # Motion issues → Add motion constraints
        motion_range = metrics.get('motion_range', [0, 0])
        if len(motion_range) == 2 and (motion_range[1] > 0.5 or motion_range[0] < 0.01):
            adjustments['negative_prompt_boost'] = (
                "static frames, no movement, "
                "identical poses, frozen animation"
            )
            logger.debug("Added motion constraints")
        
        return adjustments
    
    def record_validation_result(
        self,
        session_id: str,
        attempt_id: str,
        validation_result: Dict[str, Any],
        sprite_id: Optional[str] = None
    ):
        """
        Record validation result for an attempt.
        
        Args:
            session_id: Regeneration session ID
            attempt_id: Attempt ID
            validation_result: Validation result dictionary
            sprite_id: Generated sprite ID (if successful)
        """
        session = self.sessions.get(session_id)
        if not session:
            logger.warning(f"Session {session_id} not found")
            return
        
        attempt = session.get_attempt(attempt_id)
        if not attempt:
            logger.warning(f"Attempt {attempt_id} not found in session {session_id}")
            return
        
        attempt.validation_result = validation_result
        attempt.sprite_id = sprite_id
        attempt.status = "completed" if validation_result.get('valid') else "failed"
        
        logger.info(
            f"Recorded validation result for attempt {attempt_id}",
            extra={
                'session_id': session_id,
                'attempt_id': attempt_id,
                'valid': validation_result.get('valid'),
                'sprite_id': sprite_id
            }
        )
    
    def get_session(self, session_id: str) -> Optional[RegenerationSession]:
        """Get regeneration session by ID."""
        return self.sessions.get(session_id)
    
    def _generate_attempt_id(self, session_id: str, seed: int) -> str:
        """Generate unique attempt ID."""
        content = f"{session_id}_{seed}_{datetime.now().isoformat()}"
        return f"attempt_{hashlib.sha256(content.encode()).hexdigest()[:12]}"
    
    def get_comparison_data(self, session_id: str) -> Dict[str, Any]:
        """
        Get data for A/B comparison UI.
        
        Args:
            session_id: Regeneration session ID
        
        Returns:
            Dictionary with all attempts and their results for comparison
        """
        session = self.sessions.get(session_id)
        if not session:
            return {}
        
        return {
            'session_id': session_id,
            'original_prompt': session.original_prompt,
            'attempts': [
                {
                    'attempt_id': a.attempt_id,
                    'seed': a.seed,
                    'preset': a.preset,
                    'status': a.status,
                    'validation_score': self._calculate_validation_score(a.validation_result),
                    'sprite_id': a.sprite_id,
                    'is_best': a.attempt_id == session.best_attempt_id
                }
                for a in session.get_successful_attempts()
            ],
            'best_attempt_id': session.best_attempt_id
        }
    
    def _calculate_validation_score(self, validation_result: Optional[Dict[str, Any]]) -> float:
        """
        Calculate a score (0-100) from validation metrics.
        
        Used for ranking attempts in comparison UI.
        """
        if not validation_result or not validation_result.get('valid'):
            return 0.0
        
        metrics = validation_result.get('metrics', {})
        
        # Weighted score
        palette_score = metrics.get('palette_similarity', 0) * 40
        motion_score = self._score_motion_range(metrics.get('motion_range', [0, 0])) * 30
        color_variance_score = min(1.0, metrics.get('color_variance', 0) / 0.5) * 30
        
        return palette_score + motion_score + color_variance_score
    
    def _score_motion_range(self, motion_range: List[float]) -> float:
        """Score motion range (0-1). Ideal is 0.05-0.3."""
        if len(motion_range) != 2:
            return 0.0

        min_motion, max_motion = motion_range

        # Ideal range
        if 0.05 <= min_motion <= 0.3 and 0.05 <= max_motion <= 0.3:
            return 1.0

        # Acceptable range
        if 0.01 <= min_motion <= 0.5 and 0.01 <= max_motion <= 0.5:
            return 0.7

        # Outside acceptable range
        return 0.3

    def cleanup_old_sessions(self, max_age_hours: int = 24):
        """
        Clean up regeneration sessions older than max_age_hours.

        Args:
            max_age_hours: Maximum age in hours for keeping sessions

        Returns:
            Number of sessions removed
        """
        if not self.sessions:
            return 0

        current_time = datetime.now()
        sessions_to_remove = []

        for session_id, session in self.sessions.items():
            # Check the timestamp of the most recent attempt
            if session.attempts:
                latest_attempt = max(session.attempts, key=lambda a: a.timestamp)
                age_hours = (current_time - latest_attempt.timestamp).total_seconds() / 3600

                if age_hours > max_age_hours:
                    sessions_to_remove.append(session_id)
            else:
                # Session with no attempts - remove it
                sessions_to_remove.append(session_id)

        # Remove old sessions
        for session_id in sessions_to_remove:
            del self.sessions[session_id]

        if sessions_to_remove:
            logger.info(
                f"Cleaned up {len(sessions_to_remove)} old regeneration sessions",
                extra={
                    'removed_count': len(sessions_to_remove),
                    'max_age_hours': max_age_hours,
                    'remaining_sessions': len(self.sessions)
                }
            )

        return len(sessions_to_remove)


# Global regeneration manager instance
regeneration_manager = RegenerationManager()
