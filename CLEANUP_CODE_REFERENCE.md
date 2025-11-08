# Background Cleanup - Quick Code Reference

## 1. RegenerationManager Cleanup Method

**File:** `/home/user/BSPM-UNIFIED/BSPM-UNIFIED 2/backend/regeneration_manager.py`

```python
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
```

---

## 2. RateLimiter Cleanup Method

**File:** `/home/user/BSPM-UNIFIED/BSPM-UNIFIED 2/backend/security.py`

```python
def cleanup_stale_buckets(self, max_age_seconds: int = 3600):
    """
    Remove buckets for IPs not seen in max_age_seconds.

    Args:
        max_age_seconds: Maximum age in seconds for keeping buckets

    Returns:
        Number of buckets removed
    """
    # Alias for cleanup_old_buckets to match the requirement
    return self.cleanup_old_buckets(max_age=max_age_seconds)

def cleanup_old_buckets(self, max_age: float = 3600):
    """Remove buckets that haven't been used in max_age seconds."""
    current_time = time.time()
    to_remove = [
        bucket_id
        for bucket_id, (_, last_refill) in self.buckets.items()
        if current_time - last_refill > max_age
    ]

    for bucket_id in to_remove:
        del self.buckets[bucket_id]

    if to_remove:
        logger.debug(f"Cleaned up {len(to_remove)} old rate limit buckets")

    return len(to_remove)
```

---

## 3. TaskQueue Cleanup Method

**File:** `/home/user/BSPM-UNIFIED/BSPM-UNIFIED 2/backend/task_queue.py`

```python
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
```

---

## 4. Conversation Cleanup Function

**File:** `/home/user/BSPM-UNIFIED/BSPM-UNIFIED 2/backend/cleanup.py`

```python
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
                # Delete the file
                try:
                    os.remove(file_path)
                    removed_count += 1
                    logger.info(
                        f"Removed old conversation file: {filename}",
                        extra={
                            'filename': filename,
                            'age_days': age_seconds / (24 * 3600)
                        }
                    )
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
```

---

## 5. Background Cleanup Task

**File:** `/home/user/BSPM-UNIFIED/BSPM-UNIFIED 2/backend/cleanup.py`

```python
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
```

---

## 6. Integration in Main.py

**File:** `/home/user/BSPM-UNIFIED/BSPM-UNIFIED 2/backend/main.py`

### Import Statement (Line 85)
```python
from cleanup import cleanup_task
```

### Startup Event (Lines 324-333)
```python
@app.on_event("startup")
async def startup_event():
    """Start background services on application startup"""
    await task_queue.start()
    logger.info("Task queue started")

    # Initialize knowledge base
    from memory.knowledge_base import initialize_kb
    initialize_kb(
        vectorstore_path=settings.vectorstore_path,
        embedding_url=settings.ollama_embeddings_url,
        embedding_model=settings.embedding_model
    )
    logger.info("Knowledge base initialized")

    # Start background cleanup task
    conversations_dir = os.path.join(settings.agent_memory_path, "conversations")
    asyncio.create_task(cleanup_task(
        regeneration_manager=regeneration_manager,
        rate_limiter=rate_limiter,
        task_queue=task_queue,
        conversations_dir=conversations_dir,
        cleanup_interval_seconds=3600  # Run every hour
    ))
    logger.info("Background cleanup task started")

    logger.info("GBStudio Automation Hub v3.3 started")
```

---

## Usage Examples

### Manual Cleanup (for testing)

```python
# Test regeneration cleanup
from regeneration_manager import regeneration_manager
count = regeneration_manager.cleanup_old_sessions(max_age_hours=24)
print(f"Removed {count} regeneration sessions")

# Test rate limiter cleanup
from security import rate_limiter
count = rate_limiter.cleanup_stale_buckets(max_age_seconds=3600)
print(f"Removed {count} rate limiter buckets")

# Test task queue cleanup
from task_queue import task_queue
count = task_queue.prune_history(max_items=1000)
print(f"Removed {count} tasks from history")

# Test conversation cleanup
from cleanup import cleanup_old_conversations
import os
conversations_dir = "/app/agent_memory/conversations"
count = cleanup_old_conversations(conversations_dir, max_age_days=30)
print(f"Removed {count} conversation files")
```

### Adjusting Cleanup Intervals

To run cleanup every 30 minutes instead of 1 hour:

```python
asyncio.create_task(cleanup_task(
    regeneration_manager=regeneration_manager,
    rate_limiter=rate_limiter,
    task_queue=task_queue,
    conversations_dir=conversations_dir,
    cleanup_interval_seconds=1800  # 30 minutes
))
```

### Adjusting Retention Policies

Edit the values in `cleanup.py` cleanup_task function:

```python
# Keep regeneration sessions for 48 hours instead of 24
sessions_removed = regeneration_manager.cleanup_old_sessions(max_age_hours=48)

# Keep rate limiter buckets for 2 hours instead of 1
buckets_removed = rate_limiter.cleanup_stale_buckets(max_age_seconds=7200)

# Keep 5000 tasks instead of 1000
tasks_removed = task_queue.prune_history(max_items=5000)

# Keep conversations for 60 days instead of 30
conversations_removed = cleanup_old_conversations(conversations_dir, max_age_days=60)
```

---

## File Locations

All files are located in: `/home/user/BSPM-UNIFIED/BSPM-UNIFIED 2/backend/`

- `regeneration_manager.py` - Line 438: cleanup_old_sessions()
- `security.py` - Line 172: cleanup_stale_buckets()
- `task_queue.py` - Line 413: prune_history()
- `cleanup.py` - NEW FILE (complete)
- `main.py` - Line 85 (import), Lines 324-333 (startup)
