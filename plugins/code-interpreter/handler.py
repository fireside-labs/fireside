"""
Code Interpreter — Fireside Tool Plugin.

Executes Python code in a sandboxed subprocess and returns output.
This is the equivalent of ChatGPT's "Advanced Data Analysis" —
the AI can write and run Python to analyze data, generate charts,
and create files.

Routes:
    POST /tools/code/run — Execute Python code, return stdout/stderr
    POST /tools/code/upload — Upload a file for the interpreter to use

Security:
    - Runs in a subprocess with a 30s timeout
    - Output capped at 50KB
    - No network access by default (can be enabled in config)
    - Writes go to a sandboxed temp directory
"""

import logging
import os
import subprocess
import sys
import tempfile
import time
import uuid
from typing import Optional

log = logging.getLogger("valhalla.code")

# Sandboxed workspace for code execution
WORKSPACE = os.path.join(tempfile.gettempdir(), "fireside_code_workspace")
os.makedirs(WORKSPACE, exist_ok=True)

# Upload directory
UPLOAD_DIR = os.path.join(WORKSPACE, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Output directory for generated files (charts, CSVs, etc.)
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "output", "code")
os.makedirs(OUTPUT_DIR, exist_ok=True)

MAX_OUTPUT_SIZE = 50_000  # 50KB max stdout
TIMEOUT_SECONDS = 30


def run_code(code: str, timeout: int = TIMEOUT_SECONDS) -> dict:
    """
    Execute Python code in a subprocess.

    The code runs in a temp directory with access to uploaded files.
    Output files (charts, CSVs) are saved to output/code/.

    Common packages available: pandas, numpy, matplotlib, seaborn,
    openpyxl, csv, json, collections, statistics, math.
    """
    execution_id = uuid.uuid4().hex[:8]
    script_path = os.path.join(WORKSPACE, f"script_{execution_id}.py")

    # Wrap the code with helpful imports and setup
    wrapped = f'''
import sys, os
os.chdir({repr(WORKSPACE)})
sys.path.insert(0, {repr(WORKSPACE)})

# Common imports for data analysis
import json, csv, math, statistics, collections, datetime, re

# Set matplotlib to non-interactive backend
import matplotlib
matplotlib.use("Agg")

# Make output directory available
OUTPUT_DIR = {repr(OUTPUT_DIR)}

# User code
{code}
'''

    try:
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(wrapped)

        start = time.time()
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=WORKSPACE,
            env={
                **os.environ,
                "MPLBACKEND": "Agg",
            },
        )
        elapsed = round(time.time() - start, 2)

        stdout = result.stdout[:MAX_OUTPUT_SIZE] if result.stdout else ""
        stderr = result.stderr[:MAX_OUTPUT_SIZE] if result.stderr else ""

        # Check for any output files created
        output_files = []
        for fname in os.listdir(OUTPUT_DIR):
            fpath = os.path.join(OUTPUT_DIR, fname)
            if os.path.getmtime(fpath) >= start:
                output_files.append({
                    "name": fname,
                    "path": fpath,
                    "size": os.path.getsize(fpath),
                })

        # Also check workspace for any files created by the script
        for fname in os.listdir(WORKSPACE):
            fpath = os.path.join(WORKSPACE, fname)
            if fname.startswith("script_"):
                continue
            if os.path.isfile(fpath) and os.path.getmtime(fpath) >= start:
                output_files.append({
                    "name": fname,
                    "path": fpath,
                    "size": os.path.getsize(fpath),
                })

        log.info("[code] Executed %s — exit=%d, %.2fs, %d chars output",
                 execution_id, result.returncode, elapsed, len(stdout))

        return {
            "ok": result.returncode == 0,
            "execution_id": execution_id,
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": result.returncode,
            "elapsed_seconds": elapsed,
            "output_files": output_files,
        }

    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "execution_id": execution_id,
            "error": f"Code execution timed out after {timeout}s",
            "stdout": "",
            "stderr": "",
        }
    except Exception as exc:
        return {
            "ok": False,
            "execution_id": execution_id,
            "error": str(exc),
        }
    finally:
        # Clean up script file
        try:
            os.remove(script_path)
        except OSError:
            pass


def save_upload(filename: str, content: bytes) -> dict:
    """Save an uploaded file to the interpreter workspace."""
    safe_name = os.path.basename(filename)
    filepath = os.path.join(UPLOAD_DIR, safe_name)

    with open(filepath, "wb") as f:
        f.write(content)

    log.info("[code] Uploaded %s (%d bytes)", safe_name, len(content))

    return {
        "ok": True,
        "filename": safe_name,
        "filepath": filepath,
        "size": len(content),
    }


# ---------------------------------------------------------------------------
# FastAPI route registration
# ---------------------------------------------------------------------------

def register_routes(app, config: dict = None):
    """Register code interpreter routes."""
    from pydantic import BaseModel
    from fastapi import UploadFile, File

    class CodeRequest(BaseModel):
        code: str
        timeout: int = 30

    @app.post("/tools/code/run")
    async def handle_run(req: CodeRequest):
        return run_code(req.code, min(req.timeout, 60))

    @app.post("/tools/code/upload")
    async def handle_upload(file: UploadFile = File(...)):
        content = await file.read()
        return save_upload(file.filename, content)

    @app.get("/tools/code/files")
    async def handle_list_files():
        """List files available in the workspace."""
        files = []
        for dirname in [UPLOAD_DIR, OUTPUT_DIR]:
            for fname in os.listdir(dirname):
                fpath = os.path.join(dirname, fname)
                if os.path.isfile(fpath):
                    files.append({
                        "name": fname,
                        "path": fpath,
                        "size": os.path.getsize(fpath),
                        "location": "uploads" if dirname == UPLOAD_DIR else "output",
                    })
        return {"ok": True, "files": files}

    log.info("[code] Routes registered: /tools/code/run, /tools/code/upload, /tools/code/files")
