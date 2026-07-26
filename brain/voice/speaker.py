"""Background speaker that listens to Brain events and speaks responses."""

import logging
import threading

from brain.event_bus import Event, EventType

logger = logging.getLogger(__name__)


class Speaker:
    """
    Subscribes to Brain response events and speaks them aloud.

    Automatically speaks every Brain response using the VoiceEngine.
    Publishes VOICE_SPEAKING and VOICE_IDLE events for face reactivity.
    """

    def __init__(self, voice_engine, event_bus, default_voice="default"):
        self.voice = voice_engine
        self.event_bus = event_bus
        self.default_voice = default_voice
        self._enabled = True

        # Subscribe to Brain response events
        self.event_bus.subscribe(
            EventType.BRAIN_RESPONDING, self._on_response
        )
        logger.info("Speaker initialized")

    def _on_response(self, event) -> None:
        """Handle Brain response events."""
        if not self._enabled:
            return

        response = event.data.get("response", "")
        if response:
            threading.Thread(
                target=self._speak,
                args=(response,),
                daemon=True,
            ).start()

    def _speak(self, text: str) -> None:
        """Speak text (runs in background thread)."""
        try:
            # Publish speaking event
            self.event_bus.publish(Event(
                type=EventType.VOICE_SPEAKING,
                source="speaker",
                data={"text": text[:100]},
            ))

            self.voice.speak(text, voice=self.default_voice)

        except Exception as e:
            logger.error(f"Speaking failed: {e}")
        finally:
            # Publish idle event
            self.event_bus.publish(Event(
                type=EventType.VOICE_IDLE,
                source="speaker",
            ))

    def enable(self) -> None:
        """Enable voice output."""
        self._enabled = True

    def disable(self) -> None:
        """Disable voice output."""
        self._enabled = False

    def toggle(self) -> bool:
        """Toggle voice output. Returns new state."""
        self._enabled = not self._enabled
        return self._enabled
