"""Network automation for downloads, requests, and connectivity.

Capabilities:
- Downloads
- HTTP requests
- Connectivity checks

Uses Python requests library for HTTP operations instead of CLI tools,
reserving terminal execution for when there's no suitable Python API.
"""

import os
from pathlib import Path
from typing import Optional

from .exceptions import NetworkAutomationError

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


class NetworkAutomation:
    """Network operations and download automation."""

    def __init__(self):
        """Initialize network automation."""
        if not HAS_REQUESTS:
            raise NetworkAutomationError(
                "requests library not installed. Install with: pip install requests"
            )

    # ============= DOWNLOADS =============

    def download(self, url: str, destination: str) -> None:
        """Download a file from a URL.
        
        Args:
            url: The URL to download from.
            destination: The destination file path.
            
        Raises:
            NetworkAutomationError: If download fails.
        """
        try:
            dest_path = Path(destination)
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()

            with open(dest_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        except Exception as e:
            raise NetworkAutomationError(f"Failed to download {url}: {e}")

    # ============= HTTP REQUESTS =============

    def request(self, url: str, method: str = "GET", data: Optional[str] = None) -> str:
        """Make an HTTP request.
        
        Args:
            url: The URL to request.
            method: HTTP method (GET, POST, etc.).
            data: Optional data for POST/PUT requests.
            
        Returns:
            Response body.
            
        Raises:
            NetworkAutomationError: If request fails.
        """
        try:
            if method == "GET":
                response = requests.get(url, timeout=30)
            else:
                kwargs = {"timeout": 30}
                if data:
                    kwargs["data"] = data
                response = requests.request(method, url, **kwargs)

            response.raise_for_status()
            return response.text
        except Exception as e:
            raise NetworkAutomationError(f"Failed to request {url}: {e}")

    def get(self, url: str) -> str:
        """Make a GET request.
        
        Args:
            url: The URL to request.
            
        Returns:
            Response body.
            
        Raises:
            NetworkAutomationError: If request fails.
        """
        return self.request(url, "GET")

    def post(self, url: str, data: str) -> str:
        """Make a POST request.
        
        Args:
            url: The URL to request.
            data: Data to post.
            
        Returns:
            Response body.
            
        Raises:
            NetworkAutomationError: If request fails.
        """
        return self.request(url, "POST", data)

    # ============= CONNECTIVITY =============

    def check_connection(self, host: str = "8.8.8.8", timeout: int = 5) -> bool:
        """Check network connectivity via ping.
        
        Args:
            host: Host to ping (default: Google DNS).
            timeout: Timeout in seconds.
            
        Returns:
            True if connection is available, False otherwise.
        """
        try:
            import subprocess
            
            result = subprocess.run(
                f"ping -c 1 -W {timeout} {host}",
                shell=True,
                capture_output=True,
                timeout=timeout + 2,
            )
            return result.returncode == 0
        except Exception:
            return False

    def get_ip(self) -> str:
        """Get local IP address by making a request to a service.
        
        Returns:
            Local IP address.
            
        Raises:
            NetworkAutomationError: If getting IP fails.
        """
        try:
            response = requests.get("https://api.ipify.org?format=text", timeout=10)
            response.raise_for_status()
            return response.text.strip()
        except Exception as e:
            raise NetworkAutomationError(f"Failed to get IP address: {e}")
