"""
Background Cleanup Module - Memory Leak Prevention
Version: 1.0
Platform: Intel Mac (macOS Ventura) + Docker

Provides background cleanup tasks to prevent memory leaks from:
- Regeneration sessions that accumulate indefinitely
- Rate limiter buckets for inactive IPs
- Task history that grows unbounded
- Old conversation files
"""

import os
import time
import asyncio
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def cleanup_old_conversations(conversations_dir: str, max_age_days: int = 30) -> int:
    """
    Archive/delete conversation files older than max_age_days.

    Args:
        conversations_dir: Path to conversations directory
        max_age_days: Maximum age in days for keeping conversation files

    Returns:
        Number of files cleaned up
    """
    if not os.path.exists(conversations_dir):
        return 0

    current_time = time.time()
    max_age_seconds = max_age_days * 24 * 3600
    removed_count = 0

    try:
        for filename in os.listdir(conversations_dir):
            if not filename.endswith('.jsonl'):
                continue

            file_path = os.path.join(conversations_dir, filename)

            # Check file modification time
            file_mtime = os.path.getmtime(file_path)
            age_seconds = current_time - file_mtime

            if age_seconds > max_age_seconds:
                # Archive or delete the file
                try:
                    # Option 1: Delete the file
                    os.remove(file_path)
                    removed_count += 1
                    logger.info(
                        f"Removed old conversation file: {filename}",
                        extra={
                            'filename': filename,
                            'age_days': age_seconds / (24 * 3600)
                        }
                    )

                    # Option 2 (commented): Move to archive directory
                    # archive_dir = os.path.join(os.path.dirname(conversations_dir), "conversations_archive")
                    # os.makedirs(archive_dir, exist_ok=True)
                    # archive_path = os.path.join(archive_dir, filename)
                    # os.rename(file_path, archive_path)
                    # removed_count += 1

                except Exception as e:
                    logger.error(f"Failed to remove conversation file {filename}: {e}")

        if removed_count > 0:
            logger.info(
                f"Cleaned up {removed_count} old conversation files",
                extra={
                    'removed_count': removed_count,
                    'max_age_days': max_age_days
                }
            )

    except Exception as e:
        logger.error(f"Error during conversation cleanup: {e}", exc_info=True)

    return removed_count


async def cleanup_task(
    regeneration_manager,
    rate_limiter,
    task_queue,
    conversations_dir: str,
    cleanup_interval_seconds: int = 3600
):
    """
    Background cleanup task to prevent memory leaks.

    Runs periodically to clean up:
    - Regeneration sessions older than 24 hours
    - Rate limiter buckets for IPs not seen in 1 hour
    - Task history limited to last 1000 tasks
    - Conversation files older than 30 days

    Args:
        regeneration_manager: RegenerationManager instance
        rate_limiter: RateLimiter instance
        task_queue: TaskQueue instance
        conversations_dir: Path to conversations directory
        cleanup_interval_seconds: How often to run cleanup (default: 3600 = 1 hour)
    """
    logger.info("Background cleanup task started")

    while True:
        try:
            await asyncio.sleep(cleanup_interval_seconds)

            logger.info("Running background cleanup...")

            # Clean regeneration sessions
            sessions_removed = regeneration_manager.cleanup_old_sessions(max_age_hours=24)
            logger.debug(f"Cleanup: Removed {sessions_removed} old regeneration sessions")

            # Clean rate limiter
            buckets_removed = rate_limiter.cleanup_stale_buckets(max_age_seconds=3600)
            logger.debug(f"Cleanup: Removed {buckets_removed} stale rate limiter buckets")

            # Clean task queue history
            tasks_removed = task_queue.prune_history(max_items=1000)
            logger.debug(f"Cleanup: Removed {tasks_removed} old tasks from history")

            # Archive old conversations
            conversations_removed = cleanup_old_conversations(
                conversations_dir=conversations_dir,
                max_age_days=30
            )
            logger.debug(f"Cleanup: Removed {conversations_removed} old conversation files")

            # Log summary
            total_cleaned = sessions_removed + buckets_removed + tasks_removed + conversations_removed
            logger.info(
                "Background cleanup completed",
                extra={
                    'sessions_removed': sessions_removed,
                    'buckets_removed': buckets_removed,
                    'tasks_removed': tasks_removed,
                    'conversations_removed': conversations_removed,
                    'total_items_cleaned': total_cleaned
                }
            )

        except Exception as e:
            logger.error(f"Error in background cleanup task: {e}", exc_info=True)
            # Continue running despite errors
            await asyncio.sleep(60)  # Wait a minute before retrying
