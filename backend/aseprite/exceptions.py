"""
Aseprite MCP Exception Classes
Custom exceptions for Aseprite integration error handling
"""


class AsepriteError(Exception):
    """Base exception for Aseprite MCP errors"""

    pass


class AsepriteConnectionError(AsepriteError):
    """Raised when connection to Aseprite MCP server fails."""

    def __init__(self, message: str, url: str = None):
        self.url = url
        super().__init__(message)


class AsepriteToolError(AsepriteError):
    """Raised when an MCP tool execution fails."""

    def __init__(self, message: str, tool_name: str = None, details: dict = None):
        self.tool_name = tool_name
        self.details = details or {}
        super().__init__(message)


class AsepriteValidationError(AsepriteError):
    """Raised when validation fails"""

    def __init__(self, message: str, field: str = None, value: str = None):
        self.field = field
        self.value = value
        self.message = message
        super().__init__(self.message)


class AsepriteFileNotFoundError(AsepriteError):
    """Raised when an Aseprite file is not found."""

    def __init__(self, message: str, filename: str = None):
        self.filename = filename
        super().__init__(message)


class AsepriteExportError(AsepriteError):
    """Raised when sprite export operation fails."""

    def __init__(self, message: str, source_file: str = None, target_format: str = None):
        self.source_file = source_file
        self.target_format = target_format
        super().__init__(message)


class AsepritePaletteError(AsepriteError):
    """Raised when palette operation fails"""

    def __init__(self, message: str, palette_colors: list = None):
        self.palette_colors = palette_colors
        self.message = message
        super().__init__(self.message)


class AsepriteTimeoutError(AsepriteError):
    """Raised when an operation times out."""

    def __init__(self, message: str, timeout_seconds: float = None):
        self.timeout_seconds = timeout_seconds
        super().__init__(message)
