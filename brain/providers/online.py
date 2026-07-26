"""Online provider - uses Groq API for fast inference."""

from __future__ import annotations

import os
from typing import Dict, List

import requests


class OnlineProvider:
    """Communicates with Groq API (OpenAI-compatible)."""

    name = "groq"

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str = "llama-3.3-70b-versatile",
        host: str = "https://api.groq.com/openai/v1",
        timeout: int = 30,
    ) -> None:
        self.api_key = api_key or os.environ.get("GROQ_API_KEY", "")
        self.model_name = model_name
        self.host = host.rstrip("/")
        self.timeout = timeout
        self.chat_url = f"{self.host}/chat/completions"

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def generate(self, messages: List[Dict[str, str]]) -> str:
        if not self.api_key:
            return "Error: GROQ_API_KEY not set."

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1024,
        }

        try:
            response = requests.post(
                self.chat_url, json=payload, headers=headers, timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except requests.exceptions.HTTPError as exc:
            error_detail = ""
            try:
                error_detail = exc.response.json().get("error", {}).get("message", "")
            except Exception:
                error_detail = exc.response.text[:200]
            return f"API error: {error_detail or exc}"
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
            return f"Connection error: {exc}"
        except Exception as exc:
            return f"Error: {exc}"
