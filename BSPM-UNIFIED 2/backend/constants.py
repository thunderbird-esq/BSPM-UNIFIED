"""
Constants and Configuration Defaults
Version: 3.3
Platform: Intel Mac (macOS Ventura) + Docker

Centralized configuration values to eliminate magic numbers.
"""


class SpriteDefaults:
    """Default values for sprite generation."""

    # Sprite dimensions (Game Boy Color standard)
    WIDTH = 32
    HEIGHT = 32

    # Animation frames
    NUM_FRAMES = 8

    # Timeouts
    GENERATION_TIMEOUT = 360  # 6 minutes in seconds
    DEFAULT_TIMEOUT = 90  # 90 seconds for general operations

    # Validation
    MAX_MESSAGE_LENGTH = 1000  # Max length for user prompts


class ComfyUINodes:
    """ComfyUI workflow node identifiers."""

    # Frame output nodes (8 frames total)
    FRAME_START = 9
    FRAME_END = 17  # Exclusive, so range(9, 17) gives nodes 9-16 = 8 frames

    # Preview node
    PREVIEW_NODE = "18"

    # Execution settings
    POLL_INTERVAL = 2  # Seconds between status checks
    EXECUTION_TIMEOUT = 360  # 6 minutes max execution time


class ResourceLimits:
    """System resource thresholds for task queue monitoring."""

    # CPU settings
    CPU_THRESHOLD = 95.0  # Percent
    CPU_HIGH_COUNT_LIMIT = 6  # Consecutive checks (6 * 5s = 30 seconds)

    # Memory settings
    MEMORY_THRESHOLD = 85.0  # Percent

    # Disk settings
    DISK_THRESHOLD = 95.0  # Percent

    # Monitoring settings
    CHECK_INTERVAL = 5.0  # Seconds between resource checks

    # Task queue limits (Intel Mac optimized)
    MAX_CONCURRENT_TASKS = 1  # CPU generation, run 1 at a time
    MAX_EXECUTION_TIME = 600  # 10 minutes max per task
    TASK_POLL_TIMEOUT = 1.0  # Queue check timeout in seconds
    WORKER_SLEEP_INTERVAL = 1  # Seconds to sleep when queue is full
    GRACEFUL_SHUTDOWN_DELAY = 5  # Seconds to wait for tasks on shutdown


class LoggingDefaults:
    """Logging configuration defaults."""

    # Log file rotation
    MAX_BYTES = 10 * 1024 * 1024  # 10MB per log file
    BACKUP_COUNT = 5  # Keep 5 old log files

    # Default log level
    DEFAULT_LEVEL = "INFO"


class ServerDefaults:
    """Server configuration defaults."""

    # Uvicorn settings
    HOST = "0.0.0.0"
    PORT = 8000
    WORKERS = 2
    LOG_LEVEL = "info"

    # Health check settings
    HEALTH_CHECK_TIMEOUT = 3  # Seconds for service health checks


class Paths:
    """Default path constants (can be overridden by environment variables)."""

    # Application paths
    LOG_DIR = "/app/logs"
    PROJECT_FILES = "/app/project_files"
    TEMP_OUTPUTS = "/app/temp_outputs"
    VECTORSTORE = "/app/vectorstore"
    AGENT_MEMORY = "/app/agent_memory"
    PROJECT_DOCS = "/app/project_docs"

    # Workflow paths
    WORKFLOW_TEMPLATE = "/workflows/workflow_pixel_art.json"

    # Frontend
    FRONTEND_DIR = "/app/frontend"


class ServiceURLs:
    """Default service URLs (can be overridden by Settings)."""

    # Ollama endpoints
    OLLAMA_API = "http://ollama:11434/api/generate"
    OLLAMA_EMBEDDINGS = "http://ollama:11434/api/embeddings"
    OLLAMA_TAGS = "http://ollama:11434/api/tags"

    # ComfyUI endpoints
    COMFYUI_BASE = "http://comfyui:8188"
    COMFYUI_SYSTEM_STATS = "/system_stats"


class ModelDefaults:
    """Default AI model names."""

    PM_MODEL = "llama3"
    EMBEDDING_MODEL = "nomic-embed-text"


class SpriteTypes:
    """Valid sprite types for GBStudio projects."""

    ACTOR = "actor"
    ACTOR_ANIMATED = "actor_animated"
    STATIC = "static"
    UI = "ui"

    @classmethod
    def all_types(cls) -> list:
        """Return list of all valid sprite types."""
        return [cls.ACTOR, cls.ACTOR_ANIMATED, cls.STATIC, cls.UI]


class ExportFormats:
    """Valid sprite export formats."""

    GRID = "grid"  # Keep as 3x3 grid
    STRIP = "strip"  # Convert to horizontal strip
    INDIVIDUAL_FRAMES = "individual_frames"  # Export each frame separately

    @classmethod
    def all_formats(cls) -> list:
        """Return list of all valid export formats."""
        return [cls.GRID, cls.STRIP, cls.INDIVIDUAL_FRAMES]


class VariationTypes:
    """Valid sprite variation types for duplication."""

    HUE_SHIFT = "hue_shift"
    BRIGHTNESS = "brightness"
    CONTRAST = "contrast"

    @classmethod
    def all_types(cls) -> list:
        """Return list of all valid variation types."""
        return [cls.HUE_SHIFT, cls.BRIGHTNESS, cls.CONTRAST]
