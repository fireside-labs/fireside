# Sprint 9 — THOR (Backend: Rich Actions + Cross-Context Search)

// turbo-all — auto-run every command without asking for approval

**Your role:** Backend engineer. Python, FastAPI.
**Working directory:** `C:\Users\Jorda\OneDrive\Documents\Analytics Trends\valhalla-mesh-github`

> [!CAUTION]
> **GATE FILE IS MANDATORY.** When all tasks below are complete, you MUST create the file
> `sprints/current/gates/gate_thor.md` using your **file creation tool** (write_to_file).

---

## Context

This is the final sprint before the app goes on a real iPhone. The backend needs to return richer responses that the mobile app can render as visual cards, and add a cross-context search that lets users search across all the companion's knowledge.

---

## Your Tasks

### Task 1 — Rich Action Responses
Currently, when the user sends a message and Odin routes it through browse/pipeline, the response comes back as plain text. Add structured metadata to responses so the mobile app can render rich cards.

Update the `/ask` or `/mobile/sync` response to include an optional `action` field:

```json
{
  "response": "I found the quarterly report. Here's a summary...",
  "action": {
    "type": "browse_result",
    "title": "Quarterly Report Analysis",
    "url": "https://example.com/report",
    "summary": "Revenue up 23%, customer acquisition cost down...",
    "key_points": ["Revenue: $4.2M (+23%)", "CAC: $45 (-12%)", "Churn: 2.1%"],
    "timestamp": "2026-03-15T15:00:00Z"
  }
}
```

Action types to support:
- `browse_result` — URL summary with title, summary, key_points
- `pipeline_status` — task progress with name, stage, percent, estimated_completion
- `pipeline_complete` — finished multi-stage task with results
- `memory_recall` — when the companion remembers something relevant (source, content, date)
- `translation_result` — translation with source_lang, target_lang, original, translated

If no special action is needed (regular chat), omit the `action` field entirely.

### Task 2 — Cross-Context Search
Create `POST /api/v1/companion/query`:

```json
// Request:
{ "query": "marketing strategy" }

// Response:
{
  "results": [
    {
      "source": "working_memory",
      "content": "On March 10, you mentioned wanting to focus on developer marketing...",
      "relevance": 0.92,
      "date": "2026-03-10"
    },
    {
      "source": "taught_facts",
      "content": "You taught me: 'Our target market is developers who self-host'",
      "relevance": 0.85,
      "date": "2026-03-08"
    },
    {
      "source": "chat_history",
      "content": "In conversation: 'I think we should focus on Reddit and HN for launch...'",
      "relevance": 0.73,
      "date": "2026-03-05"
    }
  ],
  "total": 3
}
```

Search across:
1. **Working memory** — the top-10 high-importance memories (`plugins/working-memory/`)
2. **Taught facts** — everything from TeachMe (companion state)
3. **Chat history** — search recent conversations
4. **Hypotheses** — any active beliefs/hypotheses (`plugins/hypotheses/`)

Use simple keyword matching for MVP. If the LLM is available, use it to rank relevance. Cap at 10 results.

### Task 3 — Update Privacy Policy Contact
Replace `privacy@valhalla.local` with the real email the owner provides. For now, use `hello@fablefur.com` as placeholder that actually works.

### Task 4 — Drop Your Gate

---

## Rework Loop
- 🔴 HIGH → automatic FAIL, gate deleted → fix and re-drop
