"""
Shared Dependencies
Common dependencies and utilities used across multiple routers.
"""

import os
import time
from pathlib import Path
from typing import Dict, Any
from pydantic_settings import BaseSettings
from pydantic import validator

# Import shared instances
from backend.security import check_rate_limit, verify_api_key, api_key_manager, rate_limiter
from backend.task_queue import task_queue, Priority
from backend.metrics import metrics
from backend.logging_config import setup_logging

# Setup logger
logger = setup_logging(
    log_dir="/app/logs",
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    max_bytes=10 * 1024 * 1024,
    backup_count=5
)


class Settings(BaseSettings):
    """Application configuration with validation"""

    # Service URLs
    ollama_api_url: str = "http://ollama:11434/api/generate"
    ollama_embeddings_url: str = "http://ollama:11434/api/embeddings"
    ollama_tags_url: str = "http://ollama:11434/api/tags"
    comfyui_api_url: str = "http://comfyui:8188"

    # Paths
    project_files_path: str = "/app/project_files"
    workflow_template_path: str = "/workflows/workflow_pixel_art.json"
    temp_outputs_path: str = "/app/temp_outputs"
    vectorstore_path: str = "/app/vectorstore"
    agent_memory_path: str = "/app/agent_memory"
    gbstudio_project_path: str = "/app/project_files/MyGBCGame.gbsproj"
    project_docs_dir: str = "/app/project_docs"

    # Agent configuration
    pm_model: str = "llama3"
    embedding_model: str = "nomic-embed-text"
    default_timeout: int = 90

    # Generation parameters
    sprite_width: int = 32
    sprite_height: int = 32
    num_frames: int = 8
    generation_timeout: int = 360  # 6 minutes

    @validator("project_files_path")
    def path_must_exist(cls, v):
        if not os.path.exists(v):
            logger.warning(f"Path does not exist: {v}, will be created")
            os.makedirs(v, exist_ok=True)
        return v

    class Config:
        env_prefix = "GBSTUDIO_"
        case_sensitive = False


# Singleton settings instance
settings = Settings()

# Create required directories
os.makedirs(settings.temp_outputs_path, exist_ok=True)
os.makedirs(settings.vectorstore_path, exist_ok=True)
os.makedirs(settings.agent_memory_path, exist_ok=True)
os.makedirs(os.path.join(settings.agent_memory_path, "conversations"), exist_ok=True)
os.makedirs(settings.project_docs_dir, exist_ok=True)

# Application state
app_state: Dict[str, Any] = {
    "start_time": time.time(),
    "request_count": 0,
}


def get_settings() -> Settings:
    """Dependency function to get settings."""
    return settings


def get_app_state() -> Dict[str, Any]:
    """Dependency function to get application state."""
    return app_state
