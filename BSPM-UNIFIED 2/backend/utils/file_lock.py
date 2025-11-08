"""
Cross-platform File Locking Utility
Version: 1.0
Platform: Linux/macOS/Windows

Provides file-level locking to prevent concurrent write corruption.
Uses fcntl.flock() on Unix systems and msvcrt.locking() on Windows.
"""

import os
import sys
import time
from typing import Optional
from pathlib import Path


# Import platform-specific locking modules
if sys.platform == 'win32':
    import msvcrt
else:
    import fcntl


class FileLock:
    """
    Cross-platform file locking context manager

    Ensures exclusive access to files during read/write operations.
    Prevents race conditions and data corruption in concurrent environments.

    Usage:
        with FileLock('/path/to/file.json') as lock:
            # Perform file operations
            with open('/path/to/file.json', 'w') as f:
                json.dump(data, f)

    Attributes:
        path: Path to file to lock
        timeout: Maximum seconds to wait for lock (0 = non-blocking)
        check_interval: Seconds between lock acquisition attempts
    """

    def __init__(
        self,
        path: str,
        timeout: float = 10.0,
        check_interval: float = 0.1
    ):
        """
        Initialize file lock

        Args:
            path: Path to file to lock
            timeout: Maximum seconds to wait for lock (0 for non-blocking)
            check_interval: Seconds between lock attempts

        Raises:
            ValueError: If timeout or check_interval are negative
        """
        if timeout < 0:
            raise ValueError("timeout must be non-negative")
        if check_interval <= 0:
            raise ValueError("check_interval must be positive")

        self.path = Path(path)
        self.lock_path = Path(str(path) + '.lock')
        self.timeout = timeout
        self.check_interval = check_interval
        self._lock_file: Optional[int] = None

    def acquire(self) -> bool:
        """
        Acquire file lock

        Returns:
            True if lock acquired, False if timeout

        Raises:
            OSError: If lock file cannot be created
        """
        start_time = time.time()

        # Ensure parent directory exists
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)

        while True:
            try:
                # Create lock file (or open if exists)
                # Use O_CREAT | O_EXCL | O_WRONLY for atomic creation on Unix
                # On Windows, this will raise FileExistsError if file exists
                if sys.platform == 'win32':
                    # Windows: use exclusive creation
                    try:
                        fd = os.open(
                            str(self.lock_path),
                            os.O_CREAT | os.O_EXCL | os.O_WRONLY
                        )
                        # Lock the file
                        msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                        self._lock_file = fd
                        return True
                    except (OSError, IOError):
                        # File exists or lock failed, try again
                        pass
                else:
                    # Unix: use fcntl.flock()
                    fd = os.open(
                        str(self.lock_path),
                        os.O_CREAT | os.O_WRONLY,
                        0o644
                    )
                    try:
                        # Try non-blocking lock
                        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        self._lock_file = fd
                        return True
                    except (IOError, OSError):
                        # Lock failed, close and retry
                        os.close(fd)

                # Check timeout
                if self.timeout > 0:
                    elapsed = time.time() - start_time
                    if elapsed >= self.timeout:
                        return False

                    # Wait before retry
                    time.sleep(self.check_interval)
                else:
                    # Non-blocking mode
                    return False

            except Exception as e:
                # Unexpected error
                if self._lock_file is not None:
                    try:
                        os.close(self._lock_file)
                    except:
                        pass
                    self._lock_file = None
                raise OSError(f"Failed to acquire lock on {self.lock_path}: {e}")

    def release(self):
        """
        Release file lock

        Safe to call multiple times (idempotent).
        """
        if self._lock_file is None:
            return

        try:
            if sys.platform == 'win32':
                # Windows: unlock and close
                try:
                    msvcrt.locking(self._lock_file, msvcrt.LK_UNLCK, 1)
                except:
                    pass
                os.close(self._lock_file)
            else:
                # Unix: unlock and close
                try:
                    fcntl.flock(self._lock_file, fcntl.LOCK_UN)
                except:
                    pass
                os.close(self._lock_file)

            # Remove lock file
            try:
                self.lock_path.unlink(missing_ok=True)
            except:
                pass

        finally:
            self._lock_file = None

    def __enter__(self):
        """Context manager entry"""
        if not self.acquire():
            raise TimeoutError(
                f"Failed to acquire lock on {self.lock_path} "
                f"within {self.timeout} seconds"
            )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.release()
        return False

    def __del__(self):
        """Cleanup on deletion"""
        self.release()


def with_file_lock(path: str, timeout: float = 10.0):
    """
    Decorator for functions that need file locking

    Args:
        path: Path to file to lock
        timeout: Lock timeout in seconds

    Usage:
        @with_file_lock('/path/to/file.json')
        def write_config(data):
            with open('/path/to/file.json', 'w') as f:
                json.dump(data, f)
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            with FileLock(path, timeout=timeout):
                return func(*args, **kwargs)
        return wrapper
    return decorator


# Example usage
if __name__ == "__main__":
    import json

    # Test file locking
    test_file = "/tmp/test_lock.json"

    print(f"Testing file lock on {test_file}")

    with FileLock(test_file, timeout=5.0) as lock:
        print("Lock acquired")

        # Perform file operation
        data = {"test": "data", "timestamp": time.time()}
        with open(test_file, 'w') as f:
            json.dump(data, f)

        print("File written")

    print("Lock released")
