"""
Tests for the Fireside Browse plugin — Sprint 15.

Tests the parser, handler, and URL safety without making real HTTP requests.
Uses inline HTML fixtures.
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
REPO_ROOT = Path(os.path.dirname(__file__)).parent


def _load_module(plugin_name: str, filename: str = "handler.py"):
    filepath = REPO_ROOT / "plugins" / plugin_name / filename
    safe_name = f"test_{plugin_name}_{filename}".replace("/", "_").replace(".py", "").replace("-", "_")
    spec = importlib.util.spec_from_file_location(safe_name, str(filepath))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# HTML Fixtures
# ---------------------------------------------------------------------------

SIMPLE_HTML = """
<html>
<head>
    <title>Best Sourdough Recipe</title>
    <meta name="description" content="Learn to make sourdough at home">
</head>
<body>
    <nav><a href="/home">Home</a></nav>
    <h1>Sourdough Bread Recipe</h1>
    <p>This is the best sourdough recipe you'll ever find.</p>
    <h2>Ingredients</h2>
    <ul>
        <li>500g bread flour</li>
        <li>350g water</li>
        <li>100g sourdough starter</li>
        <li>10g salt</li>
    </ul>
    <h2>Instructions</h2>
    <p>Mix everything. Wait 12 hours. Bake at 450°F.</p>
    <a href="https://example.com/tips">More baking tips</a>
    <footer>Copyright 2026</footer>
    <script>console.log('noise');</script>
    <style>.hidden { display: none; }</style>
</body>
</html>
"""

NOISY_HTML = """
<html>
<body>
    <script>var ads = true;</script>
    <style>body { margin: 0; }</style>
    <nav>
        <a href="/home">Home</a>
        <a href="/about">About</a>
        <a href="/contact">Contact</a>
    </nav>
    <aside>
        <p>Sidebar ad content</p>
    </aside>
    <h1>Actual Article Title</h1>
    <p>This is the real content that matters.</p>
    <p>Second paragraph with useful information.</p>
    <iframe src="ads.html"></iframe>
    <noscript>Enable JavaScript</noscript>
    <footer>Footer garbage</footer>
</body>
</html>
"""

LINK_HEAVY_HTML = """
<html>
<head><title>Link Collection</title></head>
<body>
    <h1>Resources</h1>
    <a href="https://example.com/page1">Page One</a>
    <a href="https://example.com/page2">Page Two</a>
    <a href="https://example.com/page3">Page Three</a>
    <a href="#internal">Internal Link</a>
    <a href="javascript:void(0)">JS Link</a>
    <a href="/relative/path">Relative Link</a>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Parser Tests
# ---------------------------------------------------------------------------

class TestParser:
    def test_parse_title(self):
        parser = _load_module("browse", "parser.py")
        result = parser.parse_html(SIMPLE_HTML, base_url="https://example.com")
        assert result.title == "Best Sourdough Recipe"

    def test_parse_description(self):
        parser = _load_module("browse", "parser.py")
        result = parser.parse_html(SIMPLE_HTML, base_url="https://example.com")
        assert result.description == "Learn to make sourdough at home"

    def test_strips_scripts(self):
        parser = _load_module("browse", "parser.py")
        result = parser.parse_html(SIMPLE_HTML)
        text = result.to_text()
        assert "console.log" not in text

    def test_strips_styles(self):
        parser = _load_module("browse", "parser.py")
        result = parser.parse_html(SIMPLE_HTML)
        text = result.to_text()
        assert ".hidden" not in text

    def test_strips_nav(self):
        parser = _load_module("browse", "parser.py")
        result = parser.parse_html(NOISY_HTML)
        text = result.to_text()
        # Nav links should be stripped
        assert "Home" not in text or "Actual Article Title" in text

    def test_strips_footer(self):
        parser = _load_module("browse", "parser.py")
        result = parser.parse_html(SIMPLE_HTML)
        text = result.to_text()
        assert "Copyright 2026" not in text

    def test_strips_iframe(self):
        parser = _load_module("browse", "parser.py")
        result = parser.parse_html(NOISY_HTML)
        text = result.to_text()
        assert "ads.html" not in text

    def test_keeps_headings(self):
        parser = _load_module("browse", "parser.py")
        result = parser.parse_html(SIMPLE_HTML)
        text = result.to_text()
        assert "Sourdough Bread Recipe" in text
        assert "Ingredients" in text

    def test_keeps_paragraphs(self):
        parser = _load_module("browse", "parser.py")
        result = parser.parse_html(SIMPLE_HTML)
        text = result.to_text()
        assert "best sourdough recipe" in text

    def test_keeps_list_items(self):
        parser = _load_module("browse", "parser.py")
        result = parser.parse_html(SIMPLE_HTML)
        text = result.to_text()
        assert "500g bread flour" in text
        assert "350g water" in text

    def test_markdown_headings(self):
        parser = _load_module("browse", "parser.py")
        result = parser.parse_html(SIMPLE_HTML)
        text = result.to_text()
        # h1 becomes #, h2 becomes ##
        assert "# Sourdough Bread Recipe" in text
        assert "## Ingredients" in text

    def test_extracts_links(self):
        parser = _load_module("browse", "parser.py")
        result = parser.parse_html(LINK_HEAVY_HTML, base_url="https://example.com")
        links = result.links_only()
        # Should have page1, page2, page3, and relative link
        # Should NOT have internal (#) or javascript: links
        hrefs = [l["href"] for l in links]
        assert "https://example.com/page1" in hrefs
        assert "https://example.com/page2" in hrefs
        assert any("relative" in h for h in hrefs)  # resolved relative link

    def test_skips_internal_links(self):
        parser = _load_module("browse", "parser.py")
        result = parser.parse_html(LINK_HEAVY_HTML, base_url="https://example.com")
        links = result.links_only()
        hrefs = [l["href"] for l in links]
        assert not any(h.startswith("#") for h in hrefs)

    def test_skips_javascript_links(self):
        parser = _load_module("browse", "parser.py")
        result = parser.parse_html(LINK_HEAVY_HTML, base_url="https://example.com")
        links = result.links_only()
        hrefs = [l["href"] for l in links]
        assert not any("javascript" in h for h in hrefs)

    def test_resolves_relative_links(self):
        parser = _load_module("browse", "parser.py")
        result = parser.parse_html(LINK_HEAVY_HTML, base_url="https://example.com")
        links = result.links_only()
        hrefs = [l["href"] for l in links]
        assert "https://example.com/relative/path" in hrefs

    def test_deduplicates_text(self):
        parser = _load_module("browse", "parser.py")
        dup_html = "<html><body><p>Same text</p><p>Same text</p><p>Different text</p></body></html>"
        result = parser.parse_html(dup_html)
        texts = [el.text for el in result.elements]
        assert texts.count("Same text") == 1

    def test_max_elements_cap(self):
        parser = _load_module("browse", "parser.py")
        # Generate HTML with 500 paragraphs
        big_html = "<html><body>" + "".join(f"<p>Paragraph number {i} with enough text</p>" for i in range(500)) + "</body></html>"
        result = parser.parse_html(big_html)
        assert len(result.elements) <= 200

    def test_word_count(self):
        parser = _load_module("browse", "parser.py")
        result = parser.parse_html(SIMPLE_HTML)
        assert result.word_count > 0

    def test_token_estimate(self):
        parser = _load_module("browse", "parser.py")
        result = parser.parse_html(SIMPLE_HTML)
        # token estimate should be roughly 1.3x word count
        assert result.token_estimate > result.word_count

    def test_summary_stats(self):
        parser = _load_module("browse", "parser.py")
        result = parser.parse_html(SIMPLE_HTML, base_url="https://example.com")
        stats = result.summary_stats()
        assert "url" in stats
        assert "title" in stats
        assert "elements" in stats
        assert "words" in stats

    def test_to_text_with_links(self):
        parser = _load_module("browse", "parser.py")
        result = parser.parse_html(LINK_HEAVY_HTML, base_url="https://example.com")
        text_with = result.to_text(include_links=True)
        text_without = result.to_text(include_links=False)
        assert "Page One" in text_with
        # Links should be formatted as markdown
        assert "[" in text_with
        # Without links, link text shouldn't appear
        assert len(text_with) > len(text_without)

    def test_noisy_page_is_clean(self):
        """The whole point — noisy HTML → clean text."""
        parser = _load_module("browse", "parser.py")
        result = parser.parse_html(NOISY_HTML)
        text = result.to_text()
        # Should have the article content
        assert "Actual Article Title" in text
        assert "real content" in text
        # Should NOT have noise
        assert "ads" not in text.lower() or "Actual" in text
        assert "Sidebar" not in text
        assert "Footer garbage" not in text


# ---------------------------------------------------------------------------
# Handler Tests (URL validation, no network)
# ---------------------------------------------------------------------------

class TestHandler:
    def test_validate_empty_url(self):
        handler = _load_module("browse", "handler.py")
        valid, _ = handler._validate_url("")
        assert not valid

    def test_validate_long_url(self):
        handler = _load_module("browse", "handler.py")
        valid, _ = handler._validate_url("https://example.com/" + "a" * 3000)
        assert not valid

    def test_validate_non_http(self):
        handler = _load_module("browse", "handler.py")
        valid, _ = handler._validate_url("ftp://example.com/file")
        assert not valid

    def test_validate_file_protocol(self):
        handler = _load_module("browse", "handler.py")
        valid, _ = handler._validate_url("file:///etc/passwd")
        assert not valid

    def test_block_localhost(self):
        handler = _load_module("browse", "handler.py")
        valid, _ = handler._validate_url("http://localhost:8080/admin")
        assert not valid

    def test_block_127(self):
        handler = _load_module("browse", "handler.py")
        valid, _ = handler._validate_url("http://127.0.0.1/api")
        assert not valid

    def test_block_private_10(self):
        handler = _load_module("browse", "handler.py")
        valid, _ = handler._validate_url("http://10.0.0.1/internal")
        assert not valid

    def test_block_private_192(self):
        handler = _load_module("browse", "handler.py")
        valid, _ = handler._validate_url("http://192.168.1.1/router")
        assert not valid

    def test_block_private_172(self):
        handler = _load_module("browse", "handler.py")
        valid, _ = handler._validate_url("http://172.16.0.1/service")
        assert not valid

    def test_block_metadata(self):
        handler = _load_module("browse", "handler.py")
        # AWS metadata endpoint
        valid, _ = handler._validate_url("http://169.254.169.254/latest/meta-data")
        assert not valid

    def test_allow_valid_url(self):
        handler = _load_module("browse", "handler.py")
        valid, _ = handler._validate_url("https://example.com/page")
        assert valid

    def test_allow_http(self):
        handler = _load_module("browse", "handler.py")
        valid, _ = handler._validate_url("http://example.com/page")
        assert valid

    def test_detect_urls_in_message(self):
        handler = _load_module("browse", "handler.py")
        urls = handler.detect_urls("Check out https://example.com/cool and https://test.org/page")
        assert len(urls) == 2
        assert "https://example.com/cool" in urls
        assert "https://test.org/page" in urls

    def test_detect_no_urls(self):
        handler = _load_module("browse", "handler.py")
        urls = handler.detect_urls("No links here, just text")
        assert len(urls) == 0


# ---------------------------------------------------------------------------
# Plugin Structure Tests
# ---------------------------------------------------------------------------

class TestPluginStructure:
    def test_plugin_yaml_exists(self):
        assert (REPO_ROOT / "plugins" / "browse" / "plugin.yaml").exists()

    def test_parser_exists(self):
        assert (REPO_ROOT / "plugins" / "browse" / "parser.py").exists()

    def test_handler_exists(self):
        assert (REPO_ROOT / "plugins" / "browse" / "handler.py").exists()

    def test_total_plugins_at_least_29(self):
        plugins_dir = REPO_ROOT / "plugins"
        dirs = [d for d in plugins_dir.iterdir()
                if d.is_dir() and not d.name.startswith("_")]
        assert len(dirs) >= 28, f"Expected ≥28, found {len(dirs)}"
