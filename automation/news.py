"""News automation module.

Fetches headlines from multiple sources and opens news sites.
"""

import logging
import subprocess
import json
from typing import Dict, List, Optional
from urllib.parse import quote

import requests

logger = logging.getLogger(__name__)

NEWS_SITES = {
    "bbc": "https://www.bbc.com/news",
    "cnn": "https://www.cnn.com",
    "reuters": "https://www.reuters.com",
    "guardian": "https://www.theguardian.com",
    "al jazeera": "https://www.aljazeera.com",
    "nytimes": "https://www.nytimes.com",
    "techcrunch": "https://techcrunch.com",
    "verge": "https://www.theverge.com",
    "ars technica": "https://arstechnica.com",
    "hacker news": "https://news.ycombinator.com",
    "google news": "https://news.google.com",
    "fox news": "https://www.foxnews.com",
    "sky news": "https://news.sky.com",
}

NEWS_SEARCH_URL = "https://news.google.com/search?q={query}&hl=en-US&gl=US&ceid=US:en"


class NewsAutomation:
    """News fetching and browsing automation."""

    def __init__(self):
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
        })

    def open_news(self, site: str = "google news") -> str:
        """Open a news website."""
        site_lower = site.lower().strip()
        url = NEWS_SITES.get(site_lower)
        if not url:
            # Try partial match
            for name, news_url in NEWS_SITES.items():
                if site_lower in name or name in site_lower:
                    url = news_url
                    break
        if not url:
            url = f"https://news.google.com/search?q={quote(site)}"

        try:
            subprocess.Popen(
                ["xdg-open", url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return f"Opened {site}: {url}"
        except Exception as e:
            return f"Error: {e}"

    def search_news(self, query: str) -> str:
        """Search for news on a topic — fetch live headlines, then open browser."""
        briefing = ""
        try:
            from automation.live_search import get_live_search

            items = get_live_search().search_news(query, limit=8)
            if items:
                lines = [f"Latest news for '{query}':"]
                for i, h in enumerate(items, 1):
                    lines.append(f"  {i}. {h['title']}")
                briefing = "\n".join(lines)
        except Exception as e:
            logger.warning(f"Live news fetch failed: {e}")

        url = NEWS_SEARCH_URL.format(query=quote(query))
        try:
            subprocess.Popen(
                ["xdg-open", url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            opened = f"Opened news search: {query}"
        except Exception as e:
            opened = f"Could not open browser: {e}"

        return f"{briefing}\n{opened}".strip() if briefing else opened

    def get_headlines(self, source: str = "bbc") -> List[Dict[str, str]]:
        """Fetch headlines from a news source (RSS)."""
        rss_urls = {
            "bbc": "http://feeds.bbci.co.uk/news/rss.xml",
            "cnn": "http://rss.cnn.com/rss/edition.rss",
            "reuters": "https://www.reutersagency.com/feed/",
            "guardian": "https://www.theguardian.com/world/rss",
            "techcrunch": "https://techcrunch.com/feed/",
            "verge": "https://www.theverge.com/rss/index.xml",
            "hacker news": "https://hnrss.org/frontpage",
        }

        rss_url = rss_urls.get(source.lower())
        if not rss_url:
            return []

        try:
            resp = self._session.get(rss_url, timeout=10)
            # Simple XML parsing for titles
            import re
            titles = re.findall(r'<title><!\[CDATA\[(.*?)\]\]></title>', resp.text)
            if not titles:
                titles = re.findall(r'<title>(.*?)</title>', resp.text)
            return [{"title": t.strip()} for t in titles[1:11]]  # Top 10
        except Exception as e:
            logger.error(f"Failed to fetch headlines: {e}")
            return []

    def list_sources(self) -> str:
        """List available news sources."""
        return "\n".join(f"  {name}: {url}" for name, url in NEWS_SITES.items())
