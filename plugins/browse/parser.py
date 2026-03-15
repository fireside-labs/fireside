"""
browse/parser.py — Accessibility-tree-inspired web page parser.

Inspired by PinchTab (https://github.com/pinchtab/pinchtab):
instead of sending the full DOM (50K–200K tokens)
to the brain, extract only meaningful content using the accessibility
tree pattern.  Result: ~2K–5K tokens.  90 % smaller.  Same information.

Usage:
    from plugins.browse.parser import fetch_and_parse, parse_html

    # Fetch + parse in one call
    result = fetch_and_parse("https://example.com")

    # Or parse raw HTML you already have
    result = parse_html(html_string, base_url="https://example.com")
"""
from __future__ import annotations

import logging
import re
from typing import Optional, List
from urllib.parse import urljoin

log = logging.getLogger("valhalla.browse.parser")

# ---------------------------------------------------------------------------
# Soft-import heavy deps so the module can be imported for introspection
# even when deps aren't installed yet.
# ---------------------------------------------------------------------------
try:
    import httpx
except ImportError:
    httpx = None  # type: ignore[assignment]

try:
    from bs4 import BeautifulSoup, Tag
except ImportError:
    BeautifulSoup = None  # type: ignore[assignment,misc]
    Tag = None

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Tags that are pure noise — remove entirely
NOISE_TAGS = [
    "script", "style", "noscript", "iframe", "svg", "canvas",
    "nav", "footer", "header", "aside", "form",
    "button", "input", "select", "textarea",
    "figure", "figcaption", "picture", "source",
    "meta", "link", "base",
]

# Tags whose text content we want to keep
CONTENT_TAGS = ["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "td", "th", "blockquote", "pre", "code", "span", "div", "a"]

# Max elements to return (prevents absurdly large pages)
MAX_ELEMENTS = 200

# Max text length per element
MAX_TEXT_LEN = 500

# Request timeout
FETCH_TIMEOUT = 15

# User agent (polite crawler)
USER_AGENT = "Fireside/1.0 (local AI companion; +https://getfireside.ai)"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

class ParsedElement:
    """One meaningful element from the page."""
    def __init__(self, role: str, text: str, href: Optional[str] = None, depth: int = 0):
        self.role = role
        self.text = text
        self.href = href
        self.depth = depth


class ParsedPage:
    """The result of parsing a web page."""
    def __init__(self, url: str, title: str = "", description: str = "",
                 elements: Optional[list] = None, link_count: int = 0,
                 word_count: int = 0, token_estimate: int = 0):
        self.url = url
        self.title = title
        self.description = description
        self.elements = elements or []
        self.link_count = link_count
        self.word_count = word_count
        self.token_estimate = token_estimate

    def to_text(self, include_links: bool = False) -> str:
        """Convert to clean text for the brain."""
        lines: list[str] = []

        if self.title:
            lines.append(f"# {self.title}")
            lines.append("")

        if self.description:
            lines.append(f"> {self.description}")
            lines.append("")

        for el in self.elements:
            if el.role.startswith("h"):
                depth = el.depth or 1
                lines.append(f"{'#' * depth} {el.text}")
            elif el.role == "link" and include_links:
                lines.append(f"- [{el.text}]({el.href})")
            elif el.role == "link":
                continue  # skip links in summary mode
            elif el.role == "li":
                lines.append(f"- {el.text}")
            elif el.role == "blockquote":
                lines.append(f"> {el.text}")
            elif el.role == "code":
                lines.append(f"`{el.text}`")
            else:
                lines.append(el.text)

        return "\n".join(lines)

    def links_only(self) -> list[dict]:
        """Return just the links."""
        return [
            {"text": el.text, "href": el.href}
            for el in self.elements
            if el.role == "link" and el.href
        ]

    def summary_stats(self) -> dict:
        """Quick stats about the page."""
        return {
            "url": self.url,
            "title": self.title,
            "elements": len(self.elements),
            "links": self.link_count,
            "words": self.word_count,
            "estimated_tokens": self.token_estimate,
        }


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def _clean_text(text: str) -> str:
    """Clean extracted text — collapse whitespace, strip."""
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > MAX_TEXT_LEN:
        text = text[:MAX_TEXT_LEN] + "…"
    return text


def parse_html(html: str, base_url: str = "") -> ParsedPage:
    """
    Parse raw HTML into a clean ParsedPage using accessibility-tree pattern.

    This strips all noise (scripts, styles, nav, footer, etc.) and keeps
    only content-bearing elements (headings, paragraphs, list items, links).
    """
    if BeautifulSoup is None:
        raise ImportError("beautifulsoup4 is required: pip install beautifulsoup4")

    soup = BeautifulSoup(html, "html.parser")

    # Extract metadata
    title = ""
    title_tag = soup.find("title")
    if title_tag:
        title = _clean_text(title_tag.get_text())

    description = ""
    meta_desc = soup.find("meta", attrs={"name": "description"})
    if meta_desc and meta_desc.get("content"):
        description = _clean_text(meta_desc["content"])

    # Remove noise tags
    for tag_name in NOISE_TAGS:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    # Remove hidden elements
    for tag in soup.find_all(attrs={"hidden": True}):
        tag.decompose()
    for tag in soup.find_all(attrs={"aria-hidden": "true"}):
        tag.decompose()
    for tag in soup.find_all(style=re.compile(r"display\s*:\s*none", re.I)):
        tag.decompose()

    # Extract content elements
    elements: list[ParsedElement] = []
    seen_texts: set[str] = set()  # deduplicate
    link_count = 0

    for el in soup.find_all(CONTENT_TAGS):
        text = _clean_text(el.get_text())

        # Skip empty or tiny text
        if not text or len(text) < 4:
            continue

        # Skip duplicates
        if text in seen_texts:
            continue
        seen_texts.add(text)

        # Determine role
        tag_name = el.name if hasattr(el, "name") else "p"

        if tag_name == "a":
            href = el.get("href", "")
            if href and not href.startswith("#") and not href.startswith("javascript:"):
                if base_url and not href.startswith(("http://", "https://")):
                    href = urljoin(base_url, href)
                elements.append(ParsedElement(role="link", text=text, href=href))
                link_count += 1
        elif tag_name.startswith("h") and len(tag_name) == 2:
            depth = int(tag_name[1])
            elements.append(ParsedElement(role=tag_name, text=text, depth=depth))
        elif tag_name in ("blockquote", "pre", "code"):
            elements.append(ParsedElement(role=tag_name, text=text))
        elif tag_name == "li":
            elements.append(ParsedElement(role="li", text=text))
        else:
            # p, div, span, td, th → generic paragraph
            elements.append(ParsedElement(role="p", text=text))

        if len(elements) >= MAX_ELEMENTS:
            break

    # Calculate stats
    all_text = " ".join(el.text for el in elements)
    word_count = len(all_text.split())
    token_estimate = int(word_count * 1.3)  # rough: 1 word ≈ 1.3 tokens

    return ParsedPage(
        url=base_url,
        title=title,
        description=description,
        elements=elements,
        link_count=link_count,
        word_count=word_count,
        token_estimate=token_estimate,
    )


# ---------------------------------------------------------------------------
# Fetcher
# ---------------------------------------------------------------------------

async def fetch_and_parse(url: str) -> ParsedPage:
    """Fetch a URL and parse it into a clean ParsedPage."""
    if httpx is None:
        raise ImportError("httpx is required: pip install httpx")

    async with httpx.AsyncClient(
        timeout=FETCH_TIMEOUT,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
    ) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return parse_html(resp.text, base_url=url)


def fetch_and_parse_sync(url: str) -> ParsedPage:
    """Synchronous version for non-async contexts."""
    if httpx is None:
        raise ImportError("httpx is required: pip install httpx")

    with httpx.Client(
        timeout=FETCH_TIMEOUT,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
    ) as client:
        resp = client.get(url)
        resp.raise_for_status()
        return parse_html(resp.text, base_url=url)
