"""
Aseprite MCP Exception Classes
Custom exceptions for Aseprite integration error handling
"""


class AsepriteError(Exception):
    """Base exception for Aseprite MCP errors"""

    pass


class AsepriteConnectionError(AsepriteError):
    """Raised when connection to Aseprite MCP server fails"""

    def __init__(self, message: str = "Cannot connect to Aseprite MCP server"):
        self.message = message
        super().__init__(self.message)


class AsepriteToolError(AsepriteError):
    """Raised when Aseprite tool execution fails"""

    def __init__(self, tool_name: str, message: str):
        self.tool_name = tool_name
        self.message = f"Aseprite tool '{tool_name}' failed: {message}"
        super().__init__(self.message)


class AsepriteValidationError(AsepriteError):
    """Raised when validation fails"""

    def __init__(self, message: str, field: str = None, value: str = None):
        self.field = field
        self.value = value
        self.message = message
        super().__init__(self.message)


class AsepriteFileNotFoundError(AsepriteError):
    """Raised when a file is not found"""

    pass


class AsepriteExportError(AsepriteError):
    """Raised when export operation fails"""

    pass


class AsepritePaletteError(AsepriteError):
    """Raised when palette operation fails"""

    def __init__(self, message: str, palette_colors: list = None):
        self.palette_colors = palette_colors
        self.message = message
        super().__init__(self.message)


class AsepriteTimeoutError(AsepriteError):
    """Raised when operation times out"""

    pass
