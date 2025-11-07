"""
API Routers Package
Organized endpoints by feature domain for better maintainability.
"""

from . import health, chat, generation, sprites, batch, admin

__all__ = ["health", "chat", "generation", "sprites", "batch", "admin"]
