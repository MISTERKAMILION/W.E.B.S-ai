"""Puter.js provider - free Gemini API access via Node.js bridge.

NOTE: Puter.js requires browser authentication. To use from CLI:
  1. Log in to https://puter.com
  2. Get your auth token from browser dev tools (Application > Cookies)
  3. Set PUTER_AUTH_TOKEN env var
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional


class PuterProvider:
    """Communicates with Gemini via Puter.js (free with Puter account)."""

    name = "puter"

    AVAILABLE_MODELS = [
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
        "gemini-2.5-flash",
        "gemini-2.5-pro",
    ]

    def __init__(
        self,
        model: str = "gemini-2.0-flash",
        bridge_path: Optional[str] = None,
        timeout: int = 60,
    ) -> None:
        self.model = model
        self.timeout = timeout
        self.bridge_path = bridge_path or self._find_bridge()
        self.auth_token = os.environ.get("PUTER_AUTH_TOKEN", "")
        self._ensure_deps()

    def _find_bridge(self) -> str:
        candidates = [
            Path(__file__).parent / "puter_bridge.js",
        ]
        for p in candidates:
            if p.exists():
                return str(p)
        raise FileNotFoundError("puter_bridge.js not found")

    def _ensure_deps(self):
        bridge_dir = Path(self.bridge_path).parent
        pkg = bridge_dir / "package.json"
        if not pkg.exists():
            with open(pkg, "w") as f:
                json.dump(
                    {
                        "name": "puter-bridge",
                        "version": "1.0.0",
                        "dependencies": {"@heyputer/puter.js": "^2.0.0"},
                    },
                    f,
                    indent=2,
                )
        if not (bridge_dir / "node_modules").exists():
            subprocess.run(
                ["npm", "install"],
                cwd=str(bridge_dir),
                capture_output=True,
                timeout=120,
            )

    @property
    def available(self) -> bool:
        if not self.auth_token:
            return False
        try:
            result = self._call("generate", "ping", timeout=10)
            return result.get("success", False)
        except Exception:
            return False

    def _call(self, command: str, input_data: Any, **kwargs: Any) -> Dict[str, Any]:
        env = {**os.environ}
        if self.auth_token:
            env["PUTER_AUTH_TOKEN"] = self.auth_token

        cmd = [
            "node",
            self.bridge_path,
            command,
            json.dumps(input_data),
            json.dumps({"model": self.model, **kwargs}),
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=kwargs.get("timeout", self.timeout),
            env=env,
        )
        if result.returncode != 0:
            return {"success": False, "error": result.stderr.strip()}
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return {"success": False, "error": f"Bad response: {result.stdout[:200]}"}

    def generate(self, messages: List[Dict[str, str]]) -> str:
        if not self.auth_token:
            return "Puter requires auth. Set PUTER_AUTH_TOKEN env var."
        result = self._call("chat", messages)
        if result.get("success"):
            return result.get("content", "")
        return f"Puter error: {result.get('error', 'unknown')}"
