"""
Research — Fireside Tool Plugin.

Web search + scrape + summarize pipeline.
When the AI needs to research a topic before answering, it calls this
plugin to search DuckDuckGo, scrape the top results, and compile
a research brief.

Routes:
    POST /tools/research — Search + scrape + summarize a topic

This uses the existing browse plugin for fetching/parsing, and the
brain for summarization.
"""

import logging
import time
from typing import Optional

log = logging.getLogger("valhalla.research")


async def research(query: str, depth: int = 3, question: Optional[str] = None) -> dict:
    """
    Research a topic by:
    1. Searching DuckDuckGo for the query
    2. Fetching the top N results
    3. Extracting key information from each
    4. Compiling a research brief

    Args:
        query: What to search for
        depth: Number of results to fetch (1-5)
        question: Optional specific question to answer

    Returns:
        A research brief with sources, key facts, and a summary prompt
    """
    try:
        from plugins.browse.handler import web_search, browse
    except ImportError:
        return {"ok": False, "error": "Browse plugin not available"}

    depth = min(max(depth, 1), 5)
    start = time.time()

    # Step 1: Search
    search_result = await web_search(query, max_results=depth)
    if not search_result.get("ok"):
        return {"ok": False, "error": f"Search failed: {search_result.get('error')}"}

    results = search_result.get("results", [])
    if not results:
        return {
            "ok": False,
            "error": "No search results found",
            "query": query,
            "raw_text": search_result.get("raw_text", ""),
        }

    # Step 2: Fetch each result page
    sources = []
    for r in results[:depth]:
        try:
            page = await browse(r["url"])
            if page.get("ok"):
                # Take first ~1500 chars of each page
                text = page.get("text", "")[:1500]
                sources.append({
                    "title": r.get("title", page.get("title", "")),
                    "url": r["url"],
                    "snippet": r.get("snippet", ""),
                    "text": text,
                    "word_count": page.get("stats", {}).get("words", 0),
                })
            else:
                sources.append({
                    "title": r.get("title", ""),
                    "url": r["url"],
                    "snippet": r.get("snippet", ""),
                    "text": r.get("snippet", ""),
                    "error": page.get("error"),
                })
        except Exception as exc:
            sources.append({
                "title": r.get("title", ""),
                "url": r["url"],
                "snippet": r.get("snippet", ""),
                "text": r.get("snippet", ""),
                "error": str(exc),
            })

    elapsed = round(time.time() - start, 2)

    # Step 3: Compile research brief prompt
    brief_parts = [
        "Based on web research, here is what I found:",
        f"Query: {query}",
    ]
    if question:
        brief_parts.append(f"Specific question: {question}")

    brief_parts.append("")

    for i, src in enumerate(sources, 1):
        brief_parts.append(f"--- Source {i}: {src['title']} ({src['url']}) ---")
        brief_parts.append(src.get("text", src.get("snippet", "")))
        brief_parts.append("")

    brief_parts.append("--- END OF RESEARCH ---")
    brief_parts.append("")
    brief_parts.append(
        "Using the sources above, provide a comprehensive answer. "
        "Cite sources by number [1], [2], etc. "
        "If sources conflict, note the disagreement. "
        "Be concise but thorough."
    )

    brief = "\n".join(brief_parts)

    log.info("[research] Researched '%s' — %d sources in %.2fs",
             query[:50], len(sources), elapsed)

    return {
        "ok": True,
        "query": query,
        "sources": [
            {"title": s["title"], "url": s["url"], "snippet": s.get("snippet", "")}
            for s in sources
        ],
        "brief": brief,
        "source_count": len(sources),
        "elapsed_seconds": elapsed,
    }


# ---------------------------------------------------------------------------
# FastAPI route registration
# ---------------------------------------------------------------------------

def register_routes(app, config: dict = None):
    """Register research routes."""
    from pydantic import BaseModel

    class ResearchRequest(BaseModel):
        query: str
        depth: int = 3
        question: str | None = None

    @app.post("/tools/research")
    async def handle_research(req: ResearchRequest):
        return await research(req.query, req.depth, req.question)

    log.info("[research] Routes registered: /tools/research")
