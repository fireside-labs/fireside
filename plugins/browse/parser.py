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


# ---------------------------------------------------------------------------
# Interactive Parser — Pico Action Tree
# ---------------------------------------------------------------------------

# Tags that are actionable (the user can click/type/select)
INTERACTIVE_TAGS = ["a", "button", "input", "select", "textarea"]

# Input types we care about
USEFUL_INPUT_TYPES = [
    "text", "email", "password", "search", "tel", "url", "number",
    "date", "time", "datetime-local", "month", "week",
]


class InteractiveElement:
    """One actionable element on the page."""
    def __init__(self, idx: int, tag: str, role: str, text: str,
                 href: Optional[str] = None, input_type: Optional[str] = None,
                 value: Optional[str] = None, options: Optional[List[str]] = None,
                 name: Optional[str] = None, selector: Optional[str] = None):
        self.idx = idx
        self.tag = tag
        self.role = role        # "link", "button", "input", "select", "textarea"
        self.text = text        # visible label or placeholder
        self.href = href
        self.input_type = input_type
        self.value = value      # current value (for inputs)
        self.options = options   # dropdown options (for select)
        self.name = name        # form field name
        self.selector = selector  # CSS selector for Playwright targeting

    def to_line(self) -> str:
        """Compact single-line representation for the LLM."""
        if self.role == "link":
            return f"[{self.idx}] link \"{self.text}\""
        elif self.role == "button":
            return f"[{self.idx}] button \"{self.text}\""
        elif self.role == "input":
            val = f' value="{self.value}"' if self.value else ""
            return f"[{self.idx}] input[{self.input_type or 'text'}] \"{self.text}\"{val}"
        elif self.role == "select":
            opts = ", ".join(f'"{o}"' for o in (self.options or [])[:5])
            return f"[{self.idx}] select \"{self.text}\" options=[{opts}]"
        elif self.role == "textarea":
            return f"[{self.idx}] textarea \"{self.text}\""
        return f"[{self.idx}] {self.role} \"{self.text}\""


class InteractivePage:
    """The result of parsing a page for interactive elements."""
    def __init__(self, url: str, title: str = "", elements: Optional[list] = None,
                 page_text: str = ""):
        self.url = url
        self.title = title
        self.elements: List[InteractiveElement] = elements or []
        self.page_text = page_text  # brief content summary for context

    def to_action_text(self) -> str:
        """Generate the compact action tree for the LLM."""
        lines = []
        if self.title:
            lines.append(f"Page: {self.title}")
            lines.append(f"URL: {self.url}")
            lines.append("")

        if self.page_text:
            lines.append("Content summary:")
            lines.append(self.page_text[:500])
            lines.append("")

        lines.append(f"Interactive elements ({len(self.elements)}):")
        for el in self.elements:
            lines.append(el.to_line())

        return "\n".join(lines)

    def get_element(self, idx: int) -> Optional[InteractiveElement]:
        """Get element by index."""
        for el in self.elements:
            if el.idx == idx:
                return el
        return None

    def summary_stats(self) -> dict:
        return {
            "url": self.url,
            "title": self.title,
            "interactive_elements": len(self.elements),
            "buttons": sum(1 for e in self.elements if e.role == "button"),
            "inputs": sum(1 for e in self.elements if e.role == "input"),
            "links": sum(1 for e in self.elements if e.role == "link"),
            "selects": sum(1 for e in self.elements if e.role == "select"),
            "token_estimate": len(self.to_action_text().split()) * 1.3,
        }


def parse_interactive(html: str, base_url: str = "") -> InteractivePage:
    """
    Parse HTML for INTERACTIVE elements only — buttons, inputs, links, selects.

    This is the Pico action tree: instead of 200K tokens of DOM, the LLM gets
    a compact numbered list of ~20-50 actionable elements in ~500 tokens.
    """
    if BeautifulSoup is None:
        raise ImportError("beautifulsoup4 is required: pip install beautifulsoup4")

    soup = BeautifulSoup(html, "html.parser")

    # Title
    title = ""
    title_tag = soup.find("title")
    if title_tag:
        title = _clean_text(title_tag.get_text())

    # Remove script/style/hidden (still noise)
    for tag_name in ["script", "style", "noscript", "svg"]:
        for tag in soup.find_all(tag_name):
            tag.decompose()
    for tag in soup.find_all(attrs={"hidden": True}):
        tag.decompose()
    for tag in soup.find_all(attrs={"aria-hidden": "true"}):
        tag.decompose()

    # Brief content summary (first few paragraphs for context)
    content_parts = []
    for p in soup.find_all(["h1", "h2", "h3", "p"], limit=10):
        text = _clean_text(p.get_text())
        if text and len(text) > 4:
            content_parts.append(text)
    page_text = "\n".join(content_parts[:8])

    # Extract interactive elements
    elements: List[InteractiveElement] = []
    seen_texts: set = set()
    idx = 0

    for el in soup.find_all(INTERACTIVE_TAGS):
        tag_name = el.name if hasattr(el, "name") else ""

        # Build a CSS selector for Playwright targeting
        el_id = el.get("id", "")
        el_class = el.get("class", [])
        el_name = el.get("name", "")

        if el_id:
            selector = f"#{el_id}"
        elif el_name:
            selector = f'{tag_name}[name="{el_name}"]'
        elif el_class:
            cls = ".".join(el_class) if isinstance(el_class, list) else el_class
            selector = f"{tag_name}.{cls}"
        else:
            selector = None  # will fall back to nth-of-type

        if tag_name == "a":
            text = _clean_text(el.get_text())
            href = el.get("href", "")
            if not text or len(text) < 2:
                continue
            if href and href.startswith(("#", "javascript:")):
                continue
            if text in seen_texts:
                continue
            seen_texts.add(text)
            if base_url and href and not href.startswith(("http://", "https://")):
                href = urljoin(base_url, href)
            elements.append(InteractiveElement(
                idx=idx, tag="a", role="link", text=text[:80],
                href=href, selector=selector,
            ))
            idx += 1

        elif tag_name == "button":
            text = _clean_text(el.get_text())
            if not text or len(text) < 1:
                text = el.get("aria-label", el.get("title", "button"))
            if text in seen_texts:
                continue
            seen_texts.add(text)
            elements.append(InteractiveElement(
                idx=idx, tag="button", role="button", text=text[:80],
                selector=selector,
            ))
            idx += 1

        elif tag_name == "input":
            input_type = (el.get("type", "text") or "text").lower()
            if input_type in ("hidden", "submit", "image", "reset"):
                if input_type == "submit":
                    text = el.get("value", "Submit")
                    elements.append(InteractiveElement(
                        idx=idx, tag="input", role="button", text=text[:80],
                        selector=selector,
                    ))
                    idx += 1
                continue
            if input_type not in USEFUL_INPUT_TYPES:
                continue
            text = (el.get("placeholder", "")
                    or el.get("aria-label", "")
                    or el.get("name", "")
                    or input_type)
            value = el.get("value", "")
            elements.append(InteractiveElement(
                idx=idx, tag="input", role="input", text=text[:80],
                input_type=input_type, value=value,
                name=el_name, selector=selector,
            ))
            idx += 1

        elif tag_name == "select":
            text = (el.get("aria-label", "")
                    or el.get("name", "")
                    or "dropdown")
            options = []
            for opt in el.find_all("option", limit=10):
                opt_text = _clean_text(opt.get_text())
                if opt_text:
                    options.append(opt_text)
            elements.append(InteractiveElement(
                idx=idx, tag="select", role="select", text=text[:80],
                options=options, name=el_name, selector=selector,
            ))
            idx += 1

        elif tag_name == "textarea":
            text = (el.get("placeholder", "")
                    or el.get("aria-label", "")
                    or el.get("name", "")
                    or "text area")
            elements.append(InteractiveElement(
                idx=idx, tag="textarea", role="textarea", text=text[:80],
                name=el_name, selector=selector,
            ))
            idx += 1

        if idx >= MAX_ELEMENTS:
            break

    return InteractivePage(
        url=base_url,
        title=title,
        elements=elements,
        page_text=page_text,
    )

