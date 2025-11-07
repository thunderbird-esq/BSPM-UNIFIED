"""
Aseprite MCP Client
Provides high-level interface to Aseprite MCP server
"""

import os
from typing import Any, Dict

import requests

from backend.aseprite.exceptions import (AsepriteConnectionError,
                                         AsepriteToolError)


class AsepriteClient:
    """Client for interacting with Aseprite MCP server"""

    def __init__(
        self, base_url: str = "http://aseprite-mcp:8189", timeout: float = 300.0
    ):
        """
        Initialize Aseprite MCP client

        Args:
            base_url: Base URL for Aseprite MCP server
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def health_check(self) -> Dict[str, Any]:
        """
        Check Aseprite MCP server health

        Returns:
            Dict with health status

        Raises:
            AsepriteConnectionError: If server is unreachable
        """
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5.0)
            response.raise_for_status()
            return {
                "status": "healthy",
                "server": self.base_url,
                "response": response.json(),
            }
        except requests.exceptions.RequestException as e:
            raise AsepriteConnectionError(f"Health check failed: {str(e)}")

    def create_sprite_from_png(
        self, png_path: str, width: int = 16, height: int = 16
    ) -> Dict[str, Any]:
        """
        Import PNG file into Aseprite format

        Args:
            png_path: Path to source PNG file
            width: Sprite width in pixels
            height: Sprite height in pixels

        Returns:
            Dict with .aseprite file path and metadata

        Raises:
            FileNotFoundError: If PNG file doesn't exist
            AsepriteConnectionError: If server is unreachable
            AsepriteToolError: If import fails
        """
        if not os.path.exists(png_path):
            raise FileNotFoundError(f"PNG file not found: {png_path}")

        response = None
        try:
            response = requests.post(
                f"{self.base_url}/api/import",
                json={"png_path": png_path, "width": width, "height": height},
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            if response is not None and response.status_code >= 500:
                raise AsepriteConnectionError(f"Server error: {str(e)}")
            else:
                raise AsepriteToolError("import_png", str(e))

    def export_for_gbstudio(
        self, aseprite_path: str, output_dir: str = "project_files/sprites"
    ) -> Dict[str, Any]:
        """
        Export .aseprite file to GBStudio-compatible PNG

        Args:
            aseprite_path: Path to .aseprite file
            output_dir: Output directory for exported PNG

        Returns:
            Dict with exported PNG path

        Raises:
            FileNotFoundError: If .aseprite file doesn't exist
            AsepriteConnectionError: If server is unreachable
            AsepriteToolError: If export fails
        """
        if not os.path.exists(aseprite_path):
            raise FileNotFoundError(f"Aseprite file not found: {aseprite_path}")

        response = None
        try:
            response = requests.post(
                f"{self.base_url}/api/export",
                json={"aseprite_path": aseprite_path, "output_dir": output_dir},
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            if response is not None and response.status_code >= 500:
                raise AsepriteConnectionError(f"Server error: {str(e)}")
            else:
                raise AsepriteToolError("export_gbstudio", str(e))

    def list_files(self, workspace: str = "temp_outputs") -> Dict[str, Any]:
        """
        List all .aseprite files in workspace

        Args:
            workspace: Workspace directory to scan

        Returns:
            Dict with list of .aseprite files and metadata

        Raises:
            AsepriteConnectionError: If server is unreachable
            AsepriteToolError: If listing fails
        """
        response = None
        try:
            response = requests.get(
                f"{self.base_url}/api/files",
                params={"workspace": workspace},
                timeout=10.0,
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            if response is not None and response.status_code >= 500:
                raise AsepriteConnectionError(f"Server error: {str(e)}")
            else:
                raise AsepriteToolError("list_files", str(e))

    def add_animation_frame(self, aseprite_path: str) -> Dict[str, Any]:
        """
        Add new animation frame to .aseprite file

        Args:
            aseprite_path: Path to .aseprite file

        Returns:
            Dict with success status and frame count

        Raises:
            FileNotFoundError: If .aseprite file doesn't exist
            AsepriteConnectionError: If server is unreachable
            AsepriteToolError: If frame addition fails
        """
        if not os.path.exists(aseprite_path):
            raise FileNotFoundError(f"Aseprite file not found: {aseprite_path}")

        response = None
        try:
            response = requests.post(
                f"{self.base_url}/api/frame",
                json={"aseprite_path": aseprite_path},
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            if response is not None and response.status_code >= 500:
                raise AsepriteConnectionError(f"Server error: {str(e)}")
            else:
                raise AsepriteToolError("add_frame", str(e))
