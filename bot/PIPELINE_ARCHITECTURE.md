# Pipeline Architecture — Valhalla Mesh v3

> Pushed: 2026-03-08 | Commit: 678d444

## Overview

Autonomous dev loop: **Plan → Build → Test → Fix → Ship → Learn**

```
POST /war-room/pipeline
       │
  Huginn (GLM 5, free NVIDIA NIM) → build spec + API contracts
       │
  ┌─ Thor (qwen3.5 Q6_K, llama-server) → backend + api.json
  └─ Freya (qwen3.5 Q6_K, llama-server) → frontend
       │
  Heimdall (qwen3.5, reasoning) → test ALL code
       │ FAIL?
  Huginn → "PROGRESS or REGRESS?"
       │ REGRESS → escalate to human
       │ PROGRESS → Huginn writes fix brief → builder fixes → retest
       │
  PASS → Muninn (Kimi 2.5) distills lessons → LanceDB
       │
  SHIP ✅ (next pipeline starts with accumulated wisdom)
```

## Node Configuration

Each node (5090, 32GB VRAM):

| Service | Port | Model | Purpose |
|---------|------|-------|---------|
| llama-server | 8080 | qwen3.5 Q6_K + Q8_0 KV cache | Dispatch tasks (183 tok/s) |
| Ollama | 11434 | nomic-embed-text | Embeddings for LanceDB |
| NVIDIA NIM | cloud | GLM 5 (Huginn) | Specs, regression analysis, dreams |
| NVIDIA NIM | cloud | Kimi 2.5 (Muninn) | Memory distillation |

### Required Config per Node

```json
{
  "cloud_model": "z-ai/glm5",
  "cloud_base_url": "https://integrate.api.nvidia.com/v1"
}
```

Plus `NVIDIA_API_KEY` in environment (free tier, each node gets own key).

## What Each Agent Needs To Do

### Freya
1. ✅ llama-server already running (183 tok/s)
2. Download Bartowski `qwen3.5-35B Q6_K` GGUF from HuggingFace (if not already using it)
3. Get own NVIDIA API key → set `NVIDIA_API_KEY` in environment
4. Set `cloud_model` and `cloud_base_url` in config
5. `git pull github main` to get new pipeline.py
6. Keep Ollama alive for nomic-embed-text embeddings only

### Thor
1. Same as Freya — install llama-server + Bartowski Q6_K GGUF
2. Get own NVIDIA API key
3. `git pull github main`

### Heimdall
1. ✅ Already has llama-server running
2. Verify NVIDIA API key is set
3. `git pull github main`

## Pipeline Features (pipeline.py)

| Feature | Status | Description |
|---------|--------|-------------|
| Parallel build stages | ✅ | Thor + Freya build simultaneously |
| Huginn build spec | ✅ | GLM 5 writes spec before first build |
| Huginn fix briefs | ✅ | Interprets QA failures into surgical fixes |
| Regression detection | ✅ | Huginn compares iterations: PROGRESS vs REGRESS |
| Muninn lesson distillation | ✅ | Kimi 2.5 compresses pipeline into lessons on ship |
| Memory recall at dispatch | ✅ | Past lessons injected into build context |
| Max iteration escalation | ✅ | Escalates to War Room after N failures |
| VERDICT keyword parsing | ✅ | PASS/FAIL/SHIP format enforced |

## Dream Architecture

Dreams use the **smartest models** since latency doesn't matter:

- Dreams, soul consolidation, hypothesis → **GLM 5 via NVIDIA NIM** (free, 744B MoE)
- Each node dreams independently (no bottleneck through Odin)
- Local model stays free for dispatch during dream cycles

## API

```bash
# Create a pipeline
curl -X POST http://127.0.0.1:8765/war-room/pipeline \
  -H 'Content-Type: application/json' \
  -d '{
    "title": "Tic-tac-toe game",
    "description": "Build a polished web game...",
    "stages": [
      {"name": "build", "parallel": [
        {"agent": "thor", "description": "Build game engine"},
        {"agent": "freya", "description": "Build UI"}
      ]},
      {"name": "test", "agent": "heimdall", "description": "Test everything"},
      {"name": "review", "agent": "heimdall", "description": "Final quality check"}
    ],
    "max_iterations": 3
  }'
```
