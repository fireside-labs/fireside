"""
browse/handler.py — Fireside Browse API routes.

Routes:
    POST /browse         — Fetch + parse a URL, return clean text
    POST /browse/summarize — Fetch + parse + summarize via brain
    POST /browse/compare — Compare two URLs side by side
    POST /browse/links   — Extract all links from a URL

All browsing happens locally (httpx).  No data is sent to any cloud.
The orchestrator and companion can both use these routes.
"""
from __future__ import annotations

import logging
import time
import hashlib
import re
from typing import Optional

log = logging.getLogger("valhalla.browse")

# Soft-imports
try:
    from plugins.browse.parser import fetch_and_parse, fetch_and_parse_sync, parse_html, ParsedPage
except ImportError:
    from parser import fetch_and_parse, fetch_and_parse_sync, parse_html, ParsedPage

# ---------------------------------------------------------------------------
# URL Safety
# ---------------------------------------------------------------------------

# Block private networks, localhost, metadata endpoints
BLOCKED_PATTERNS = [
    re.compile(r"^https?://localhost", re.I),
    re.compile(r"^https?://127\.", re.I),
    re.compile(r"^https?://0\.", re.I),
    re.compile(r"^https?://10\.", re.I),
    re.compile(r"^https?://172\.(1[6-9]|2[0-9]|3[01])\.", re.I),
    re.compile(r"^https?://192\.168\.", re.I),
    re.compile(r"^https?://169\.254\.", re.I),  # AWS metadata
    re.compile(r"^https?://\[", re.I),          # IPv6
    re.compile(r"^file://", re.I),              # local files
    re.compile(r"^ftp://", re.I),               # FTP
]

MAX_URL_LEN = 2048
MAX_RESPONSE_SIZE = 5_000_000  # 5MB max page size


def _validate_url(url: str) -> tuple[bool, str]:
    """Validate a URL is safe to fetch."""
    if not url:
        return False, "URL is required"

    if len(url) > MAX_URL_LEN:
        return False, f"URL too long ({len(url)} chars, max {MAX_URL_LEN})"

    if not url.startswith(("http://", "https://")):
        return False, "Only http:// and https:// URLs are allowed"

    for pattern in BLOCKED_PATTERNS:
        if pattern.match(url):
            return False, "Cannot browse private/local network addresses"

    return True, "ok"


# ---------------------------------------------------------------------------
# Core browse function
# ---------------------------------------------------------------------------

async def browse(url: str) -> dict:
    """
    Fetch and parse a URL.  Returns the parsed result or an error.

    This is the main entry point — used by both the companion and
    the orchestrator/brain.
    """
    valid, reason = _validate_url(url)
    if not valid:
        return {"ok": False, "error": reason}

    try:
        start = time.time()
        page = await fetch_and_parse(url)
        elapsed = round(time.time() - start, 2)

        log.info("[browse] Parsed %s → %d elements, %d words, ~%d tokens in %.2fs",
                 url, len(page.elements), page.word_count, page.token_estimate, elapsed)

        return {
            "ok": True,
            "url": page.url,
            "title": page.title,
            "description": page.description,
            "text": page.to_text(include_links=False),
            "stats": page.summary_stats(),
            "elapsed_seconds": elapsed,
        }

    except Exception as exc:
        log.warning("[browse] Failed to fetch %s: %s", url, exc)
        return {"ok": False, "error": str(exc), "url": url}


def browse_sync(url: str) -> dict:
    """Synchronous version for non-async callers."""
    valid, reason = _validate_url(url)
    if not valid:
        return {"ok": False, "error": reason}

    try:
        start = time.time()
        page = fetch_and_parse_sync(url)
        elapsed = round(time.time() - start, 2)

        return {
            "ok": True,
            "url": page.url,
            "title": page.title,
            "description": page.description,
            "text": page.to_text(include_links=False),
            "stats": page.summary_stats(),
            "elapsed_seconds": elapsed,
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc), "url": url}


# ---------------------------------------------------------------------------
# Summarize (for brain/companion integration)
# ---------------------------------------------------------------------------

async def browse_and_summarize(url: str, question: Optional[str] = None) -> dict:
    """
    Fetch a URL, parse it, and prepare a prompt for the brain to summarize.

    Returns the clean text + a ready-to-use prompt.  The caller sends this
    to the brain API and gets back a personality-flavored summary.
    """
    result = await browse(url)
    if not result["ok"]:
        return result

    prompt_parts = [
        "Summarize this web page concisely. Keep it under 150 words.",
        f"Page title: {result['title']}",
        f"Page URL: {result['url']}",
        "",
        "--- PAGE CONTENT ---",
        result["text"],
        "--- END ---",
    ]

    if question:
        prompt_parts.insert(1, f"The user specifically asked: {question}")

    return {
        "ok": True,
        "url": result["url"],
        "title": result["title"],
        "prompt": "\n".join(prompt_parts),
        "stats": result["stats"],
        "elapsed_seconds": result["elapsed_seconds"],
    }


# ---------------------------------------------------------------------------
# Compare two URLs
# ---------------------------------------------------------------------------

async def browse_and_compare(url_a: str, url_b: str) -> dict:
    """
    Fetch two URLs, parse both, and prepare a comparison prompt.
    """
    result_a = await browse(url_a)
    result_b = await browse(url_b)

    if not result_a["ok"]:
        return {"ok": False, "error": f"Failed to fetch URL A: {result_a.get('error')}"}
    if not result_b["ok"]:
        return {"ok": False, "error": f"Failed to fetch URL B: {result_b.get('error')}"}

    prompt = "\n".join([
        "Compare these two web pages side by side. Create a concise comparison table.",
        "Focus on key differences: price, features, specs, pros/cons.",
        "Keep it under 200 words.",
        "",
        f"--- PAGE A: {result_a['title']} ({url_a}) ---",
        result_a["text"],
        "",
        f"--- PAGE B: {result_b['title']} ({url_b}) ---",
        result_b["text"],
        "--- END ---",
    ])

    return {
        "ok": True,
        "url_a": url_a,
        "url_b": url_b,
        "title_a": result_a["title"],
        "title_b": result_b["title"],
        "prompt": prompt,
        "stats_a": result_a["stats"],
        "stats_b": result_b["stats"],
    }


# ---------------------------------------------------------------------------
# Extract links
# ---------------------------------------------------------------------------

async def browse_links(url: str) -> dict:
    """Fetch a URL and return just the links."""
    valid, reason = _validate_url(url)
    if not valid:
        return {"ok": False, "error": reason}

    try:
        page = await fetch_and_parse(url)
        links = page.links_only()

        return {
            "ok": True,
            "url": url,
            "title": page.title,
            "links": links,
            "count": len(links),
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc), "url": url}


# ---------------------------------------------------------------------------
# Morning news digest helper
# ---------------------------------------------------------------------------

async def fetch_headlines(urls: list[str], max_per_source: int = 5) -> dict:
    """
    Fetch headlines from multiple news sources.
    Returns a combined list of headline-link pairs.

    Used by the morning briefing to include news.
    """
    all_headlines: list[dict] = []

    for url in urls[:5]:  # max 5 sources
        try:
            page = await fetch_and_parse(url)
            # Headlines are usually h2s or h3s on news sites
            headlines = [
                {"text": el.text, "source": page.title, "url": url}
                for el in page.elements
                if el.role in ("h2", "h3") and len(el.text) > 10
            ][:max_per_source]
            all_headlines.extend(headlines)
        except Exception as exc:
            log.warning("[browse] Failed to fetch headlines from %s: %s", url, exc)

    return {
        "ok": True,
        "headlines": all_headlines,
        "sources": len(urls),
    }


# ---------------------------------------------------------------------------
# Chat integration: detect URLs in messages
# ---------------------------------------------------------------------------

URL_PATTERN = re.compile(
    r"(https?://[^\s<>\"')\]]+)",
    re.IGNORECASE,
)


def detect_urls(text: str) -> list[str]:
    """Extract URLs from a chat message."""
    return URL_PATTERN.findall(text)


async def auto_browse_message(message: str) -> Optional[dict]:
    """
    If a chat message contains a URL, auto-browse it and return context.
    Returns None if no URLs found.
    """
    urls = detect_urls(message)
    if not urls:
        return None

    # Browse the first URL found
    url = urls[0]
    result = await browse(url)

    if not result["ok"]:
        return None

    return {
        "url": url,
        "title": result["title"],
        "text": result["text"][:1000],  # first 1000 chars for context
        "stats": result["stats"],
    }


# ---------------------------------------------------------------------------
# FastAPI route registration (called by plugin loader)
# ---------------------------------------------------------------------------

def register_routes(app):
    """Register browse routes with the FastAPI app."""
    from pydantic import BaseModel

    class BrowseRequest(BaseModel):
        url: str
        question: str | None = None

    class CompareRequest(BaseModel):
        url_a: str
        url_b: str

    class HeadlinesRequest(BaseModel):
        urls: list[str]
        max_per_source: int = 5

    @app.post("/browse")
    async def handle_browse(req: BrowseRequest):
        return await browse(req.url)

    @app.post("/browse/summarize")
    async def handle_summarize(req: BrowseRequest):
        return await browse_and_summarize(req.url, req.question)

    @app.post("/browse/compare")
    async def handle_compare(req: CompareRequest):
        return await browse_and_compare(req.url_a, req.url_b)

    @app.post("/browse/links")
    async def handle_links(req: BrowseRequest):
        return await browse_links(req.url)

    @app.post("/browse/headlines")
    async def handle_headlines(req: HeadlinesRequest):
        return await fetch_headlines(req.urls, req.max_per_source)

    log.info("[browse] Routes registered: /browse, /browse/summarize, /browse/compare, /browse/links, /browse/headlines")
