"""
Cache module for W.E.B.S.

Short-term memory for the Collector.
Stores KnowledgeResults to avoid repeated expensive operations.

Every request passes through this cache before doing any work.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Generic, TypeVar
import time
import threading
import hashlib
import logging
from datetime import datetime

# Setup logging
logger = logging.getLogger(__name__)

# Generic type for stored values
T = TypeVar('T')


# ==========================================================
# Data Models
# ==========================================================

@dataclass(slots=True)
class CacheEntry(Generic[T]):
    """Individual cache entry with metadata."""
    
    value: T
    created_at: float = field(default_factory=time.time)
    expires_at: float = 0.0
    last_access: float = field(default_factory=time.time)
    access_count: int = 0
    
    def __post_init__(self):
        if self.expires_at == 0.0:
            self.expires_at = float('inf')
    
    @property
    def is_expired(self) -> bool:
        if self.expires_at == float('inf'):
            return False
        return time.time() >= self.expires_at
    
    @property
    def age_seconds(self) -> float:
        return time.time() - self.created_at
    
    def access(self) -> None:
        self.last_access = time.time()
        self.access_count += 1


@dataclass(slots=True)
class CacheStats:
    """Cache statistics."""
    
    size: int = 0
    hits: int = 0
    misses: int = 0
    expired_removed: int = 0
    evictions: int = 0
    
    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "size": self.size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": self.hit_rate,
            "expired_removed": self.expired_removed,
            "evictions": self.evictions
        }


# ==========================================================
# Cache
# ==========================================================

class Cache(Generic[T]):
    """
    In-memory cache with TTL and LRU eviction.
    
    Simple, fast, thread-safe.
    
    Usage:
        cache = Cache(max_size=500, ttl_seconds=3600)
        
        # Store
        cache.set("key", value)
        
        # Retrieve
        value = cache.get("key")
        if value is None:
            value = fetch_data()
            cache.set("key", value)
        
        # Check
        if cache.has("key"):
            # Key exists and is not expired
        
        # Delete
        cache.delete("key")
        
        # Clear all
        cache.clear()
        
        # Stats
        stats = cache.get_stats()
    """
    
    def __init__(self, max_size: int = 500, ttl_seconds: int = 3600):
        """
        Initialize the cache.
        
        Args:
            max_size: Maximum number of entries.
            ttl_seconds: Time to live for entries (seconds).
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        
        self._cache: Dict[str, CacheEntry[T]] = {}
        self._lock = threading.RLock()
        self.stats = CacheStats()
        
        logger.info(f"Cache initialized (max_size={max_size}, ttl={ttl_seconds}s)")
    
    # ==========================================================
    # Core Methods
    # ==========================================================
    
    def get(self, key: str) -> Optional[T]:
        """
        Retrieve a value from the cache.
        
        Returns:
            Value or None if not found or expired.
        """
        if not key:
            return None
        
        with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                self.stats.misses += 1
                return None
            
            if entry.is_expired:
                self._remove(key)
                self.stats.misses += 1
                self.stats.expired_removed += 1
                return None
            
            entry.access()
            self.stats.hits += 1
            return entry.value
    
    def set(self, key: str, value: T, ttl_seconds: Optional[int] = None) -> None:
        """
        Store a value in the cache.
        
        Args:
            key: Cache key.
            value: Value to store.
            ttl_seconds: Optional custom TTL (uses default if None).
        """
        if not key:
            return
        
        ttl = ttl_seconds or self.ttl_seconds
        
        with self._lock:
            # Remove existing if present
            if key in self._cache:
                self._remove(key)
            
            # Evict if full
            if len(self._cache) >= self.max_size:
                self._evict_one()
            
            # Store
            entry = CacheEntry(
                value=value,
                expires_at=time.time() + ttl
            )
            self._cache[key] = entry
    
    def has(self, key: str) -> bool:
        """Check if a key exists and is not expired."""
        if not key:
            return False
        
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return False
            
            if entry.is_expired:
                self._remove(key)
                return False
            
            return True
    
    def delete(self, key: str) -> bool:
        """Delete a key from the cache."""
        if not key:
            return False
        
        with self._lock:
            if key in self._cache:
                self._remove(key)
                return True
            return False
    
    def clear(self) -> None:
        """Clear all entries from the cache."""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            logger.debug(f"Cache cleared ({count} entries)")
    
    # ==========================================================
    # Batch Operations
    # ==========================================================
    
    def get_many(self, keys: list) -> Dict[str, Optional[T]]:
        """Retrieve multiple values at once."""
        result = {}
        for key in keys:
            result[key] = self.get(key)
        return result
    
    def set_many(self, items: Dict[str, T], ttl_seconds: Optional[int] = None) -> None:
        """Store multiple values at once."""
        for key, value in items.items():
            self.set(key, value, ttl_seconds)
    
    # ==========================================================
    # Maintenance
    # ==========================================================
    
    def cleanup(self) -> int:
        """Remove all expired entries. Returns count removed."""
        with self._lock:
            expired = [key for key, entry in self._cache.items() if entry.is_expired]
            for key in expired:
                self._remove(key)
            self.stats.expired_removed += len(expired)
            return len(expired)
    
    def _evict_one(self) -> None:
        """Evict the least recently used entry."""
        if not self._cache:
            return
        
        # Find least recently used
        victim = min(self._cache.values(), key=lambda e: e.last_access)
        self._remove(victim.key)
        self.stats.evictions += 1
    
    def _remove(self, key: str) -> None:
        """Internal remove (no lock)."""
        if key in self._cache:
            del self._cache[key]
    
    # ==========================================================
    # Statistics
    # ==========================================================
    
    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        with self._lock:
            self.stats.size = len(self._cache)
            return self.stats
    
    def reset_stats(self) -> None:
        """Reset statistics to zero."""
        with self._lock:
            self.stats = CacheStats()
    
    def get_detailed_stats(self) -> Dict[str, Any]:
        """Get detailed cache statistics."""
        with self._lock:
            ages = [entry.age_seconds for entry in self._cache.values()]
            
            return {
                "stats": self.stats.to_dict(),
                "config": {
                    "max_size": self.max_size,
                    "ttl_seconds": self.ttl_seconds
                },
                "entries": {
                    "total": len(self._cache),
                    "keys": list(self._cache.keys())[:10]
                },
                "age": {
                    "min": min(ages) if ages else 0,
                    "max": max(ages) if ages else 0,
                    "avg": sum(ages) / len(ages) if ages else 0
                }
            }


# ==========================================================
# Cache Key Generator
# ==========================================================

class CacheKey:
    """Utility for generating consistent cache keys."""
    
    @staticmethod
    def search(query: str, content_type: str = "general") -> str:
        """Generate a search cache key."""
        return f"search:{content_type}:{query.lower().strip()}"
    
    @staticmethod
    def url(url: str) -> str:
        """Generate a URL cache key."""
        return f"url:{url.strip()}"
    
    @staticmethod
    def hash(*args, **kwargs) -> str:
        """Generate a hash-based cache key."""
        import hashlib
        import json
        content = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True)
        return f"hash:{hashlib.md5(content.encode()).hexdigest()}"
    
    @staticmethod
    def prefixed(prefix: str, *args) -> str:
        """Generate a prefixed cache key."""
        return ":".join([prefix] + [str(a) for a in args])
