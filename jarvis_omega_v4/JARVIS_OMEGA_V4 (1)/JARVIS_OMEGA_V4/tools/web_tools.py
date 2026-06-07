"""
tools/web_tools.py — Free web search using DuckDuckGo
No API key required.
"""

import re
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus

logger = logging.getLogger("JARVIS.WEB")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
}


def web_search(query: str, max_results: int = 8) -> dict:
    """Search DuckDuckGo and return structured results."""
    if not query.strip():
        return {"type": "error", "error": "Empty query"}
    try:
        results = _ddg_search(query, max_results)
        if not results:
            results = _ddg_html_search(query, max_results)
        return {"type": "web_results", "query": query, "results": results}
    except Exception as exc:
        logger.error("Web search failed: %s", exc)
        return {"type": "error", "error": f"Search failed: {exc}"}


def _ddg_search(query: str, max_results: int) -> list:
    """DuckDuckGo HTML search."""
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        for result in soup.select(".result__body")[:max_results]:
            title_tag = result.select_one(".result__title a")
            snippet_tag = result.select_one(".result__snippet")
            if not title_tag:
                continue
            title = title_tag.get_text(strip=True)
            href = title_tag.get("href", "")
            # Extract real URL from DuckDuckGo redirect
            url_match = re.search(r"uddg=([^&]+)", href)
            real_url = requests.utils.unquote(url_match.group(1)) if url_match else href
            snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""
            if title:
                results.append({"title": title, "url": real_url, "snippet": snippet})
        return results
    except Exception as exc:
        logger.warning("DuckDuckGo search failed: %s", exc)
        return []


def _ddg_html_search(query: str, max_results: int) -> list:
    """Fallback: DuckDuckGo lite."""
    url = f"https://lite.duckduckgo.com/lite/?q={quote_plus(query)}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        for a in soup.find_all("a", class_="result-link")[:max_results]:
            title = a.get_text(strip=True)
            href  = a.get("href", "")
            if title and href:
                results.append({"title": title, "url": href, "snippet": ""})
        return results
    except Exception as exc:
        logger.warning("Fallback search failed: %s", exc)
        return []


def fetch_page_text(url: str, max_chars: int = 3000) -> str:
    """Fetch and extract main text content from a webpage."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        # Remove scripts and styles
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        # Clean up
        lines = [l.strip() for l in text.splitlines() if l.strip() and len(l.strip()) > 20]
        return "\n".join(lines)[:max_chars]
    except Exception as exc:
        logger.warning("Page fetch failed [%s]: %s", url, exc)
        return ""
