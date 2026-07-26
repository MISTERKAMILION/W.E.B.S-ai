"""Live web + news search for up-to-date brain context.

Fetches current headlines and search snippets so the online LLM
is not stuck on its training cutoff (2023, etc.).
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from html import unescape
from typing import Dict, List, Optional
from urllib.parse import quote_plus

import requests

logger = logging.getLogger(__name__)

_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

# Questions that need fresh data (not model memory)
_LIVE_PATTERNS = [
    r"\b(news|headline|headlines|breaking)\b",
    r"\b(today|tonight|this\s+(morning|afternoon|evening|week|month|year))\b",
    r"\b(latest|current|recent|now|update|updates)\b",
    r"\b(who\s+won|score|election|weather|stock|price|crypto)\b",
    r"\b(what\s+happened|going\s+on|happening)\b",
    r"\b(202[4-9]|203\d|20[3-9]\d)\b",  # years from 2024 onward
    r"\b(president|prime\s+minister|ceo)\s+(of|is)\b",
    r"\b(release|released|announced|launch)\b",
]


def needs_live_context(text: str) -> bool:
    """Return True if the query likely needs up-to-date information."""
    lower = (text or "").lower()
    if not lower.strip():
        return False
    for pat in _LIVE_PATTERNS:
        if re.search(pat, lower):
            return True
    return False


def current_datetime_str() -> str:
    """Human-readable UTC + local-ish date string."""
    now = datetime.now(timezone.utc)
    local = datetime.now().astimezone()
    return (
        f"UTC: {now.strftime('%A, %d %B %Y %H:%M')} UTC | "
        f"Local: {local.strftime('%A, %d %B %Y %H:%M %Z')}"
    )


class LiveSearch:
    """Fetch live news and web snippets without paid API keys."""

    def __init__(self, timeout: int = 12):
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": _UA, "Accept-Language": "en-US,en;q=0.9"})

    def search_news(self, query: str, limit: int = 8) -> List[Dict[str, str]]:
        """Google News RSS search — always current."""
        url = (
            "https://news.google.com/rss/search?"
            f"q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"
        )
        return self._parse_rss(url, limit=limit)

    def top_headlines(self, limit: int = 10) -> List[Dict[str, str]]:
        """Top world/US headlines from Google News."""
        url = "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en"
        return self._parse_rss(url, limit=limit)

    def search_web(self, query: str, limit: int = 5) -> List[Dict[str, str]]:
        """DuckDuckGo HTML results as a free web fallback."""
        url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        try:
            resp = self._session.get(url, timeout=self.timeout)
            resp.raise_for_status()
            html = resp.text
            # Result blocks
            results: List[Dict[str, str]] = []
            # Titles + snippets
            titles = re.findall(
                r'class="result__a"[^>]*>(.*?)</a>',
                html,
                flags=re.DOTALL | re.IGNORECASE,
            )
            snippets = re.findall(
                r'class="result__snippet"[^>]*>(.*?)</(?:a|td|div)',
                html,
                flags=re.DOTALL | re.IGNORECASE,
            )
            for i, title in enumerate(titles[:limit]):
                clean_title = _strip_html(title)
                snippet = _strip_html(snippets[i]) if i < len(snippets) else ""
                if clean_title:
                    results.append({"title": clean_title, "snippet": snippet, "source": "web"})
            return results
        except Exception as e:
            logger.warning(f"DuckDuckGo search failed: {e}")
            return []

    def briefing(self, query: str, include_top: bool = True) -> str:
        """Build a text briefing the LLM can ground answers on."""
        lines = [
            "=== LIVE WORLD CONTEXT (fetched just now) ===",
            f"Date/time: {current_datetime_str()}",
            f"Query: {query}",
            "",
        ]

        news = self.search_news(query, limit=8)
        if news:
            lines.append("News results:")
            for i, item in enumerate(news, 1):
                when = f" ({item['date']})" if item.get("date") else ""
                lines.append(f"  {i}. {item['title']}{when}")
                if item.get("source"):
                    lines.append(f"     source: {item['source']}")
            lines.append("")

        web = self.search_web(query, limit=5)
        if web:
            lines.append("Web results:")
            for i, item in enumerate(web, 1):
                lines.append(f"  {i}. {item['title']}")
                if item.get("snippet"):
                    lines.append(f"     {item['snippet'][:220]}")
            lines.append("")

        if include_top and not news:
            top = self.top_headlines(limit=8)
            if top:
                lines.append("Top headlines right now:")
                for i, item in enumerate(top, 1):
                    lines.append(f"  {i}. {item['title']}")
                lines.append("")

        if len(lines) <= 5:
            lines.append("(No live results returned — say so honestly if unsure.)")

        lines.append(
            "INSTRUCTIONS: Base your answer on this live context. "
            "Prefer these facts over your training memory. "
            "If results are thin, say what you found and what is uncertain. "
            "Never claim your knowledge stops in 2023."
        )
        lines.append("=== END LIVE CONTEXT ===")
        return "\n".join(lines)

    def _parse_rss(self, url: str, limit: int = 10) -> List[Dict[str, str]]:
        try:
            resp = self._session.get(url, timeout=self.timeout)
            resp.raise_for_status()
            text = resp.text
            items = re.findall(r"<item>(.*?)</item>", text, flags=re.DOTALL | re.IGNORECASE)
            out: List[Dict[str, str]] = []
            for block in items[:limit]:
                title = _rss_tag(block, "title")
                link = _rss_tag(block, "link")
                pub = _rss_tag(block, "pubDate")
                source = _rss_tag(block, "source")
                if not title:
                    continue
                out.append(
                    {
                        "title": title,
                        "link": link,
                        "date": pub,
                        "source": source or "Google News",
                    }
                )
            return out
        except Exception as e:
            logger.warning(f"RSS fetch failed ({url}): {e}")
            return []


def _rss_tag(block: str, tag: str) -> str:
    m = re.search(rf"<{tag}[^>]*><!\[CDATA\[(.*?)\]\]></{tag}>", block, re.DOTALL | re.I)
    if not m:
        m = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", block, re.DOTALL | re.I)
    if not m:
        return ""
    return _strip_html(m.group(1))


def _strip_html(text: str) -> str:
    text = unescape(text or "")
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# Module-level helper used by Brain
_live: Optional[LiveSearch] = None


def get_live_search() -> LiveSearch:
    global _live
    if _live is None:
        _live = LiveSearch()
    return _live


def build_live_context(query: str, force: bool = False) -> str:
    """Return live briefing text, or empty if not needed."""
    if not force and not needs_live_context(query):
        # Still always provide the clock — cheap and useful
        return (
            f"Current date/time: {current_datetime_str()}\n"
            "You have live-search tools. For anything time-sensitive, "
            "rely on fetched context when provided — never invent recent events."
        )
    try:
        return get_live_search().briefing(query, include_top=True)
    except Exception as e:
        logger.error(f"Live context failed: {e}")
        return f"Current date/time: {current_datetime_str()}\n(Live search error: {e})"
