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
