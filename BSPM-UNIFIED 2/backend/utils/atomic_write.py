"""
Atomic File Write Utility
Version: 1.0
Platform: Linux/macOS/Windows

Provides atomic write operations to prevent data corruption from partial writes.
Uses write-to-temp → fsync → rename pattern for atomic file updates.
"""

import os
import json
import tempfile
from typing import Any, Dict, List
from pathlib import Path


def atomic_write_json(
    filepath: str,
    data: Any,
    indent: int = 2,
    ensure_ascii: bool = False
) -> None:
    """
    Atomically write JSON data to file

    Process:
    1. Write data to temporary file in same directory
    2. Flush and fsync to ensure data is on disk
    3. Atomically rename temp file to target (OS-level atomic operation)

    This prevents partial writes and ensures file is either fully updated
    or left in original state if operation fails.

    Args:
        filepath: Target file path
        data: Python object to serialize as JSON
        indent: JSON indentation (default 2)
        ensure_ascii: Whether to escape non-ASCII characters

    Raises:
        OSError: If write or rename fails
        TypeError: If data is not JSON-serializable

    Example:
        atomic_write_json('/app/config.json', {'setting': 'value'})
    """
    filepath = Path(filepath)

    # Ensure parent directory exists
    filepath.parent.mkdir(parents=True, exist_ok=True)

    # Create temporary file in same directory as target
    # This ensures temp file is on same filesystem for atomic rename
    fd, temp_path = tempfile.mkstemp(
        dir=str(filepath.parent),
        prefix=f'.{filepath.name}.',
        suffix='.tmp'
    )

    try:
        # Write JSON to temp file
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii)
            f.flush()

            # Force write to disk (critical for durability)
            os.fsync(f.fileno())

        # Atomically replace target file with temp file
        # On Unix: rename is atomic
        # On Windows: os.replace is atomic (Python 3.3+)
        os.replace(temp_path, str(filepath))

    except Exception as e:
        # Clean up temp file on error
        try:
            os.unlink(temp_path)
        except:
            pass
        raise OSError(f"Failed to atomically write {filepath}: {e}") from e


def atomic_write_jsonl(
    filepath: str,
    data: List[Dict[str, Any]],
    append: bool = False
) -> None:
    """
    Atomically write JSONL (JSON Lines) data to file

    Each dict in data list is written as one line of JSON.

    Args:
        filepath: Target file path
        data: List of dicts to write as JSONL
        append: If True, append to existing file (default False)

    Raises:
        OSError: If write or rename fails
        TypeError: If data contains non-JSON-serializable objects

    Example:
        atomic_write_jsonl('/app/logs.jsonl', [
            {'event': 'start', 'ts': 123},
            {'event': 'stop', 'ts': 456}
        ])
    """
    filepath = Path(filepath)

    # Ensure parent directory exists
    filepath.parent.mkdir(parents=True, exist_ok=True)

    # If appending, read existing data first
    existing_lines = []
    if append and filepath.exists():
        with open(filepath, 'r', encoding='utf-8') as f:
            existing_lines = f.readlines()

    # Create temporary file in same directory
    fd, temp_path = tempfile.mkstemp(
        dir=str(filepath.parent),
        prefix=f'.{filepath.name}.',
        suffix='.tmp'
    )

    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            # Write existing lines if appending
            if existing_lines:
                f.writelines(existing_lines)

            # Write new data
            for item in data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')

            f.flush()
            os.fsync(f.fileno())

        # Atomically replace
        os.replace(temp_path, str(filepath))

    except Exception as e:
        # Clean up temp file on error
        try:
            os.unlink(temp_path)
        except:
            pass
        raise OSError(f"Failed to atomically write JSONL {filepath}: {e}") from e


def atomic_append_jsonl(
    filepath: str,
    item: Dict[str, Any]
) -> None:
    """
    Atomically append single item to JSONL file

    More efficient than atomic_write_jsonl for single-item appends.

    Args:
        filepath: Target JSONL file
        item: Dict to append as JSON line

    Raises:
        OSError: If write fails
        TypeError: If item is not JSON-serializable

    Example:
        atomic_append_jsonl('/app/events.jsonl', {
            'event': 'user_action',
            'timestamp': time.time()
        })
    """
    filepath = Path(filepath)

    # Ensure parent directory exists
    filepath.parent.mkdir(parents=True, exist_ok=True)

    # Read existing content
    existing_lines = []
    if filepath.exists():
        with open(filepath, 'r', encoding='utf-8') as f:
            existing_lines = f.readlines()

    # Create temporary file
    fd, temp_path = tempfile.mkstemp(
        dir=str(filepath.parent),
        prefix=f'.{filepath.name}.',
        suffix='.tmp'
    )

    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            # Write existing content
            if existing_lines:
                f.writelines(existing_lines)

            # Append new item
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

            f.flush()
            os.fsync(f.fileno())

        # Atomically replace
        os.replace(temp_path, str(filepath))

    except Exception as e:
        # Clean up temp file on error
        try:
            os.unlink(temp_path)
        except:
            pass
        raise OSError(f"Failed to atomically append to {filepath}: {e}") from e


def atomic_write_text(
    filepath: str,
    content: str,
    encoding: str = 'utf-8'
) -> None:
    """
    Atomically write text content to file

    Args:
        filepath: Target file path
        content: Text content to write
        encoding: Text encoding (default utf-8)

    Raises:
        OSError: If write or rename fails

    Example:
        atomic_write_text('/app/config.txt', 'setting=value\\n')
    """
    filepath = Path(filepath)

    # Ensure parent directory exists
    filepath.parent.mkdir(parents=True, exist_ok=True)

    # Create temporary file
    fd, temp_path = tempfile.mkstemp(
        dir=str(filepath.parent),
        prefix=f'.{filepath.name}.',
        suffix='.tmp'
    )

    try:
        with os.fdopen(fd, 'w', encoding=encoding) as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())

        # Atomically replace
        os.replace(temp_path, str(filepath))

    except Exception as e:
        # Clean up temp file on error
        try:
            os.unlink(temp_path)
        except:
            pass
        raise OSError(f"Failed to atomically write text to {filepath}: {e}") from e


# Example usage
if __name__ == "__main__":
    import time

    # Test atomic JSON write
    test_json = "/tmp/test_atomic.json"
    data = {
        "timestamp": time.time(),
        "status": "active",
        "config": {
            "setting1": "value1",
            "setting2": 42
        }
    }

    print(f"Writing to {test_json}")
    atomic_write_json(test_json, data)
    print("Write successful")

    # Verify
    with open(test_json, 'r') as f:
        loaded = json.load(f)
        assert loaded == data
        print("Verification successful")

    # Test atomic JSONL write
    test_jsonl = "/tmp/test_atomic.jsonl"
    events = [
        {"event": "start", "ts": time.time()},
        {"event": "process", "ts": time.time()},
        {"event": "stop", "ts": time.time()}
    ]

    print(f"\nWriting to {test_jsonl}")
    atomic_write_jsonl(test_jsonl, events)
    print("Write successful")

    # Test append
    print("\nAppending to JSONL")
    atomic_append_jsonl(test_jsonl, {"event": "append", "ts": time.time()})
    print("Append successful")

    # Verify
    with open(test_jsonl, 'r') as f:
        lines = f.readlines()
        assert len(lines) == 4
        print(f"Verification successful: {len(lines)} lines")
