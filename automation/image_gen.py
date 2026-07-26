"""Image generation module using Pollinations AI.

Free, no API key needed, unlimited usage.
https://pollinations.ai
"""

import logging
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Optional
from urllib.parse import quote

import requests

logger = logging.getLogger(__name__)

POLLINATIONS_URL = "https://image.pollinations.ai/prompt/{prompt}"
DEFAULT_WIDTH = 1024
DEFAULT_HEIGHT = 1024


class ImageGenerator:
    """Generate images from text prompts using Pollinations AI."""

    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = output_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "generated_images"
        )
        os.makedirs(self.output_dir, exist_ok=True)
        self._session = requests.Session()
        self._session.timeout = 60

    def generate(
        self,
        prompt: str,
        width: int = DEFAULT_WIDTH,
        height: int = DEFAULT_HEIGHT,
        filename: Optional[str] = None,
        seed: Optional[int] = None,
    ) -> Optional[str]:
        """Generate an image from a text prompt.

        Args:
            prompt: Description of the image to generate.
            width: Image width in pixels.
            height: Image height in pixels.
            filename: Custom filename (without extension). Auto-generated if None.
            seed: Random seed for reproducibility.

        Returns:
            Path to the saved image file, or None on failure.
        """
        if not prompt or not prompt.strip():
            logger.error("Empty prompt")
            return None

        # Clean prompt for filename
        clean_prompt = re.sub(r'[^\w\s-]', '', prompt.strip())[:50]
        clean_prompt = re.sub(r'\s+', '_', clean_prompt)

        if not filename:
            timestamp = int(time.time())
            filename = f"{clean_prompt}_{timestamp}"

        # Ensure .png extension
        if not filename.endswith(('.png', '.jpg', '.jpeg', '.webp')):
            filename += '.png'

        filepath = os.path.join(self.output_dir, filename)

        try:
            # Build URL
            encoded_prompt = quote(prompt.strip())
            url = f"{POLLINATIONS_URL.format(prompt=encoded_prompt)}?width={width}&height={height}&nologo=true"
            if seed is not None:
                url += f"&seed={seed}"

            logger.info(f"Generating image: {prompt[:60]}...")
            response = self._session.get(url, stream=True)
            response.raise_for_status()

            # Save image
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            file_size = os.path.getsize(filepath)
            logger.info(f"Image saved: {filepath} ({file_size} bytes)")

            # Open in default viewer
            try:
                subprocess.Popen(
                    ["xdg-open", filepath],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            except Exception:
                pass

            return filepath

        except requests.exceptions.Timeout:
            logger.error("Image generation timed out")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Image generation request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            return None

    def generate_square(self, prompt: str, size: int = 1024) -> Optional[str]:
        """Generate a square image."""
        return self.generate(prompt, width=size, height=size)

    def generate_landscape(self, prompt: str) -> Optional[str]:
        """Generate a landscape image (16:9)."""
        return self.generate(prompt, width=1024, height=576)

    def generate_portrait(self, prompt: str) -> Optional[str]:
        """Generate a portrait image (9:16)."""
        return self.generate(prompt, width=576, height=1024)

    def list_generated(self) -> list:
        """List all generated images."""
        if not os.path.exists(self.output_dir):
            return []
        return [
            f for f in os.listdir(self.output_dir)
            if f.endswith(('.png', '.jpg', '.jpeg', '.webp'))
        ]

    def delete_image(self, filename: str) -> bool:
        """Delete a generated image."""
        filepath = os.path.join(self.output_dir, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            return True
        return False
