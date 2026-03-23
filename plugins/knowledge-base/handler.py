"""
Knowledge Base — Fireside Tool Plugin.

Drop documents into folders → they get chunked, indexed, and searchable.
Like ChatGPT's "Custom GPTs" knowledge files, but local.

Supported formats: .txt, .md, .pdf, .csv, .json, .py, .js, .ts, .docx

How it works:
  1. User creates folders in ~/.valhalla/knowledge/ (e.g., "business", "recipes")
  2. Drops documents into them
  3. This plugin auto-scans and chunks them into searchable segments
  4. The AI uses `knowledge_search` tool to find relevant context before answering

Storage:
  - Chunks stored as JSON in ~/.valhalla/knowledge/_index/
  - Keyword-based retrieval (no GPU needed, works on any machine)
  - Optional sentence-transformers for semantic search if installed

Routes:
    POST /tools/knowledge/search — Search the knowledge base
    POST /tools/knowledge/ingest — Manually trigger re-indexing
    GET  /tools/knowledge/folders — List knowledge folders + stats
"""

import hashlib
import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Optional

log = logging.getLogger("valhalla.knowledge")

# Knowledge base lives in user's .valhalla directory
KB_ROOT = Path.home() / ".valhalla" / "knowledge"
INDEX_DIR = KB_ROOT / "_index"
KB_ROOT.mkdir(parents=True, exist_ok=True)
INDEX_DIR.mkdir(parents=True, exist_ok=True)

# Chunk settings
CHUNK_SIZE = 500       # ~500 words per chunk
CHUNK_OVERLAP = 50     # 50-word overlap between chunks
MAX_FILE_SIZE = 10_000_000  # 10MB max per file

SUPPORTED_EXTENSIONS = {
    ".txt", ".md", ".csv", ".json", ".py", ".js", ".ts", ".tsx",
    ".jsx", ".html", ".css", ".yaml", ".yml", ".toml", ".ini",
    ".log", ".sh", ".bat", ".ps1", ".sql", ".xml", ".env",
    ".pdf", ".docx",
}


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------

def _extract_text(filepath: Path) -> str:
    """Extract text from a file based on its extension."""
    ext = filepath.suffix.lower()

    if ext == ".pdf":
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(str(filepath))
            text = "\n\n".join(page.get_text() for page in doc)
            doc.close()
            return text
        except ImportError:
            try:
                # Fallback: pdfplumber
                import pdfplumber
                with pdfplumber.open(str(filepath)) as pdf:
                    return "\n\n".join(
                        page.extract_text() or "" for page in pdf.pages
                    )
            except ImportError:
                return f"[PDF file — install PyMuPDF or pdfplumber to read: {filepath.name}]"

    elif ext == ".docx":
        try:
            from docx import Document
            doc = Document(str(filepath))
            return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())
        except ImportError:
            return f"[DOCX file — install python-docx to read: {filepath.name}]"

    elif ext == ".csv":
        try:
            import csv
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.reader(f)
                rows = list(reader)
            # Include header + first 500 rows
            header = rows[0] if rows else []
            lines = [", ".join(header)]
            for row in rows[1:501]:
                lines.append(", ".join(str(v) for v in row))
            return "\n".join(lines)
        except Exception:
            pass

    elif ext == ".json":
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            return json.dumps(data, indent=2)[:50000]
        except Exception:
            pass

    # Default: read as text
    try:
        return filepath.read_text(encoding="utf-8", errors="replace")[:50000]
    except Exception as e:
        return f"[Error reading {filepath.name}: {e}]"


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def _chunk_text(text: str, source: str, folder: str) -> list[dict]:
    """Split text into overlapping chunks with metadata."""
    words = text.split()
    if not words:
        return []

    chunks = []
    i = 0
    chunk_num = 0

    while i < len(words):
        end = min(i + CHUNK_SIZE, len(words))
        chunk_words = words[i:end]
        chunk_text = " ".join(chunk_words)

        # Create a stable ID for deduplication
        chunk_id = hashlib.md5(
            f"{source}:{chunk_num}:{chunk_text[:100]}".encode()
        ).hexdigest()[:12]

        chunks.append({
            "id": chunk_id,
            "text": chunk_text,
            "source": source,
            "folder": folder,
            "chunk_num": chunk_num,
            "word_count": len(chunk_words),
        })

        chunk_num += 1
        i = end - CHUNK_OVERLAP if end < len(words) else end

    return chunks


# ---------------------------------------------------------------------------
# Smart gist extraction (for memory internalization)
# ---------------------------------------------------------------------------

def _extract_gist(text: str, filename: str = "", max_words: int = 400) -> str:
    """
    Extract a representative gist from a document by sampling from
    multiple sections — not just the top. Mimics how humans internalize:
    they remember the intro, key headings, important points throughout,
    and the conclusion.
    """
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if not lines:
        return f"Document: {filename} (empty)"

    words_all = text.split()
    total_words = len(words_all)

    parts = []
    budget = max_words

    # 1. Key lines: headings, bold text, lines starting with bullets/numbers
    key_lines = []
    for line in lines:
        is_heading = (
            line.startswith("#") or
            line.startswith("**") or
            line.isupper() and len(line) > 5 or
            re.match(r'^\d+\.\s', line) or
            line.startswith("- ") or line.startswith("• ")
        )
        if is_heading and len(line.split()) < 30:
            key_lines.append(line.lstrip("#•-* ").strip())
    if key_lines:
        key_text = "; ".join(key_lines[:15])
        key_words = key_text.split()
        alloc = min(len(key_words), budget // 3)
        parts.append("Key points: " + " ".join(key_words[:alloc]))
        budget -= alloc

    # 2. Intro: first meaningful paragraph (first ~100 words)
    intro_words = []
    for line in lines[:10]:
        if line.startswith("#") or len(line.split()) < 3:
            continue
        intro_words.extend(line.split())
        if len(intro_words) >= 100:
            break
    if intro_words:
        alloc = min(len(intro_words), budget // 3)
        parts.append("Intro: " + " ".join(intro_words[:alloc]))
        budget -= alloc

    # 3. Middle sample: grab content from ~40% and ~70% through
    if total_words > 300:
        for pct in [0.4, 0.7]:
            start = int(total_words * pct)
            sample = " ".join(words_all[start:start + 60])
            alloc = min(60, budget // 2)
            parts.append(" ".join(sample.split()[:alloc]))
            budget -= alloc

    # 4. Conclusion: last ~80 words
    if total_words > 200:
        end_words = words_all[-80:]
        alloc = min(len(end_words), max(budget, 40))
        parts.append("End: " + " ".join(end_words[:alloc]))

    gist = " | ".join(parts) if parts else " ".join(words_all[:max_words])
    return gist[:2000]  # hard cap


# ---------------------------------------------------------------------------
# Indexing
# ---------------------------------------------------------------------------

def _get_index_path(folder: str) -> Path:
    return INDEX_DIR / f"{folder}.json"


def _load_index(folder: str) -> list[dict]:
    path = _get_index_path(folder)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def _save_index(folder: str, chunks: list[dict]):
    path = _get_index_path(folder)
    path.write_text(json.dumps(chunks, indent=2), encoding="utf-8")


def ingest_folder(folder_name: str) -> dict:
    """Scan a knowledge folder and index all documents."""
    folder_path = KB_ROOT / folder_name
    if not folder_path.exists() or not folder_path.is_dir():
        return {"ok": False, "error": f"Folder not found: {folder_name}"}

    if folder_name.startswith("_"):
        return {"ok": False, "error": "Cannot index system folders"}

    all_chunks = []
    files_processed = 0
    errors = []

    for filepath in sorted(folder_path.rglob("*")):
        if not filepath.is_file():
            continue
        if filepath.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        if filepath.stat().st_size > MAX_FILE_SIZE:
            errors.append(f"{filepath.name}: too large (>{MAX_FILE_SIZE//1_000_000}MB)")
            continue

        try:
            text = _extract_text(filepath)
            if text.strip():
                # Use relative path from KB_ROOT as source identifier
                source = str(filepath.relative_to(KB_ROOT))
                chunks = _chunk_text(text, source, folder_name)
                all_chunks.extend(chunks)
                files_processed += 1
        except Exception as e:
            errors.append(f"{filepath.name}: {e}")

    _save_index(folder_name, all_chunks)

    # ── Internalize: push document summaries into long-term memory ──
    # Like how humans "know" what's in their docs without re-reading them.
    # We sample from throughout the document (not just the top) to capture
    # the intro, key points, and conclusion.
    memories_stored = 0
    try:
        import orchestrator as orch_mod
        for filepath in sorted(folder_path.rglob("*")):
            if not filepath.is_file():
                continue
            if filepath.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue
            try:
                text = _extract_text(filepath)
                if not text.strip():
                    continue
                gist = _extract_gist(text, filepath.name)
                memory = (
                    f"[Knowledge: {folder_name}/{filepath.name}] "
                    f"{gist}"
                )
                orch_mod.observe(memory, importance=0.7, source=f"knowledge:{folder_name}")
                memories_stored += 1
            except Exception:
                pass
        if memories_stored:
            log.info("[knowledge] Internalized %d files from '%s' into long-term memory",
                     memories_stored, folder_name)
    except ImportError:
        log.debug("[knowledge] orchestrator not available — skipping memory internalization")
    except Exception as e:
        log.warning("[knowledge] Memory internalization failed: %s", e)

    log.info("[knowledge] Indexed folder '%s': %d files, %d chunks",
             folder_name, files_processed, len(all_chunks))

    return {
        "ok": True,
        "folder": folder_name,
        "files_processed": files_processed,
        "chunks": len(all_chunks),
        "memories_stored": memories_stored,
        "errors": errors if errors else None,
    }


def ingest_all() -> dict:
    """Re-index all knowledge folders."""
    results = {}
    for item in KB_ROOT.iterdir():
        if item.is_dir() and not item.name.startswith("_"):
            results[item.name] = ingest_folder(item.name)
    return {"ok": True, "folders": results}


# ---------------------------------------------------------------------------
# Search (keyword-based, fast, no GPU required)
# ---------------------------------------------------------------------------

def _score_chunk(chunk: dict, query_words: set[str]) -> float:
    """Score a chunk's relevance to query using keyword overlap + TF."""
    text_lower = chunk["text"].lower()
    text_words = set(text_lower.split())

    # Direct word overlap
    overlap = query_words & text_words
    if not overlap:
        return 0.0

    # Score based on: overlap ratio × term frequency boost
    base_score = len(overlap) / max(len(query_words), 1)

    # Bonus for multi-word phrase matches
    phrase_bonus = 0.0
    query_str = " ".join(sorted(query_words))
    if query_str in text_lower:
        phrase_bonus = 0.3

    # Bonus for query words appearing multiple times
    tf_bonus = 0.0
    for w in overlap:
        count = text_lower.count(w)
        if count > 1:
            tf_bonus += min(count * 0.02, 0.1)

    return base_score + phrase_bonus + tf_bonus


def search(query: str, folder: Optional[str] = None, top_k: int = 5) -> dict:
    """
    Search the knowledge base for relevant chunks.

    Args:
        query: What to search for
        folder: Optional folder to limit search to (None = all folders)
        top_k: Number of results to return
    """
    if not query.strip():
        return {"ok": False, "error": "Empty query"}

    # Normalize query
    query_words = set(
        w.lower() for w in re.split(r'\W+', query)
        if len(w) > 2  # skip very short words
    )

    if not query_words:
        return {"ok": False, "error": "Query too short"}

    # Auto-ingest if needed (check if any folder has been modified since last index)
    _auto_ingest()

    # Load all relevant indices
    all_chunks = []
    if folder:
        all_chunks = _load_index(folder)
    else:
        for idx_file in INDEX_DIR.glob("*.json"):
            folder_name = idx_file.stem
            all_chunks.extend(_load_index(folder_name))

    if not all_chunks:
        return {
            "ok": True,
            "results": [],
            "message": "Knowledge base is empty. Add documents to ~/.valhalla/knowledge/<folder>/",
        }

    # Score and rank
    scored = []
    for chunk in all_chunks:
        score = _score_chunk(chunk, query_words)
        if score > 0:
            scored.append((score, chunk))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:top_k]

    results = []
    for score, chunk in top:
        results.append({
            "text": chunk["text"],
            "source": chunk["source"],
            "folder": chunk["folder"],
            "score": round(score, 3),
        })

    return {
        "ok": True,
        "query": query,
        "results": results,
        "total_chunks_searched": len(all_chunks),
    }


def _auto_ingest():
    """Re-index folders that have been modified since last indexing."""
    for item in KB_ROOT.iterdir():
        if not item.is_dir() or item.name.startswith("_"):
            continue
        idx_path = _get_index_path(item.name)
        # Check if any file in folder is newer than the index
        if not idx_path.exists():
            ingest_folder(item.name)
            continue
        idx_mtime = idx_path.stat().st_mtime
        for f in item.rglob("*"):
            if f.is_file() and f.stat().st_mtime > idx_mtime:
                ingest_folder(item.name)
                break


# ---------------------------------------------------------------------------
# List folders
# ---------------------------------------------------------------------------

def list_folders() -> dict:
    """List all knowledge folders with stats."""
    folders = []
    for item in sorted(KB_ROOT.iterdir()):
        if not item.is_dir() or item.name.startswith("_"):
            continue
        files = [f for f in item.rglob("*") if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS]
        chunks = _load_index(item.name)
        folders.append({
            "name": item.name,
            "files": len(files),
            "chunks": len(chunks),
            "path": str(item),
        })
    return {
        "ok": True,
        "folders": folders,
        "root": str(KB_ROOT),
    }


# ---------------------------------------------------------------------------
# FastAPI route registration
# ---------------------------------------------------------------------------

def register_routes(app, config: dict = None):
    """Register knowledge base routes."""
    from pydantic import BaseModel

    class SearchRequest(BaseModel):
        query: str
        folder: str | None = None
        top_k: int = 5

    class IngestRequest(BaseModel):
        folder: str | None = None

    @app.post("/tools/knowledge/search")
    async def handle_search(req: SearchRequest):
        return search(req.query, req.folder, req.top_k)

    @app.post("/tools/knowledge/ingest")
    async def handle_ingest(req: IngestRequest):
        if req.folder:
            return ingest_folder(req.folder)
        return ingest_all()

    @app.get("/tools/knowledge/folders")
    async def handle_folders():
        return list_folders()

    @app.post("/tools/knowledge/upload")
    async def handle_upload(folder: str = "general", file: "UploadFile" = None):
        """Upload a file to a knowledge folder via the dashboard UI."""
        from fastapi import UploadFile, File as FastFile
        # Import here to avoid circular
        if file is None:
            from fastapi import Request
            # Handle multipart form manually
            return {"ok": False, "error": "No file provided"}

        # Create folder if needed
        folder_path = KB_ROOT / folder
        folder_path.mkdir(parents=True, exist_ok=True)

        # Save file
        safe_name = os.path.basename(file.filename)
        dest = folder_path / safe_name
        content = await file.read()
        dest.write_bytes(content)

        # Re-index the folder
        result = ingest_folder(folder)
        result["uploaded"] = safe_name
        result["size"] = len(content)
        return result

    # Also support the simpler multipart upload
    from fastapi import UploadFile, File as FastFile, Form

    @app.post("/tools/knowledge/upload-file")
    async def handle_upload_file(
        file: UploadFile = FastFile(...),
        folder: str = Form(default="general"),
    ):
        """Upload a file to a knowledge folder (multipart form)."""
        folder_path = KB_ROOT / folder
        folder_path.mkdir(parents=True, exist_ok=True)

        safe_name = os.path.basename(file.filename)
        dest = folder_path / safe_name
        content = await file.read()
        dest.write_bytes(content)

        result = ingest_folder(folder)
        result["uploaded"] = safe_name
        result["size"] = len(content)
        return result

    log.info("[knowledge] Routes registered. KB root: %s", KB_ROOT)
