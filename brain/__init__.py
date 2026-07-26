"""Brain package for W.E.B.S AI - reasoning and orchestration."""

from .brain import Brain
from .providers.model_manager import ModelManager
from .providers.online import OnlineProvider
from .providers.offline import OfflineProvider
from .providers.dummy import DummyProvider
from .session import SessionManager, Session, SessionStatus
from .tools import ToolRegistry, Tool, ToolCategory
from .event_bus import EventBus, Event, EventType
from .state import StateManager, SystemState, StateChange
from .prompt_manager import PromptManager
from .cache import Cache, CacheKey, CacheStats
from .learner import UsageLearner
from .suggestions import suggest_followup, Suggestion
from .dispatcher import Dispatcher, Dispatch, TaskStatus
from .evolution import TemplateEvolver
from .routing import classify_message, is_casual, MessageType
from .actions import detect_actions, ActionType, DetectedAction
from .memory_sqlite import SQLiteMemory

__all__ = [
    # Core
    "Brain",
    # Providers
    "ModelManager",
    "OnlineProvider",
    "OfflineProvider",
    "DummyProvider",
    # Session
    "SessionManager",
    "Session",
    "SessionStatus",
    # Tools
    "ToolRegistry",
    "Tool",
    "ToolCategory",
    # Events
    "EventBus",
    "Event",
    "EventType",
    # State
    "StateManager",
    "SystemState",
    "StateChange",
    # Prompts
    "PromptManager",
    # Cache
    "Cache",
    "CacheKey",
    "CacheStats",
    # JARVIS-inspired
    "UsageLearner",
    "suggest_followup",
    "Suggestion",
    "Dispatcher",
    "Dispatch",
    "TaskStatus",
    "TemplateEvolver",
    "classify_message",
    "is_casual",
    "MessageType",
    # Actions
    "detect_actions",
    "ActionType",
    "DetectedAction",
    # SQLite Memory
    "SQLiteMemory",
]
