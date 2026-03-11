# Plugin Marketplace

---

## How Plugins Work

A plugin is a folder with two files:

```
plugins/my-plugin/
├── plugin.yaml     # What it is
└── handler.py      # What it does
```

That's it. No build step. No package manager. Drop the folder in `plugins/`, Bifrost loads it on next start (or hot-reloads if already running).

### plugin.yaml

```yaml
name: scheduler
version: 1.0.0
description: Cron-based task scheduling for agents
author: your-username
license: MIT

routes:
  - method: POST
    path: /scheduler/create
  - method: GET
    path: /scheduler/jobs

events:
  - scheduler.job.completed
  - scheduler.job.failed

config_keys:
  - scheduler.timezone
  - scheduler.max_concurrent

category: automation
tags: [cron, scheduling, tasks]
```

### handler.py

```python
def register_routes(app, config):
    """Called at startup. Add your HTTP routes."""

    @app.route("/scheduler/create", methods=["POST"])
    async def create_job(request):
        # Your logic here
        pass

def on_event(event_name, payload, config):
    """Called when a subscribed event fires."""
    pass

def health_check():
    """Watchdog calls this. Return True if healthy."""
    return True
```

---

## Building a Plugin

```bash
# Scaffold
valhalla plugin create my-plugin

# Develop — edit handler.py, test locally
valhalla start    # hot-reloads plugins on file change

# Package for submission
valhalla plugin pack
# → my-plugin-1.0.0.tar.gz
```

**Local testing is instant.** Save `handler.py` → Bifrost reloads it → test your route. No restart cycle.

---

## The Marketplace (Dashboard)

The **Plugins** page has two views:

### Installed

Shows every loaded plugin with status, version, and an on/off toggle.

```
┌────────────────────────────────────────────────┐
│  🔌 Plugins             [ Installed ] [Browse] │
├────────────────────────────────────────────────┤
│                                                │
│  model-switch    v1.0.0    🟢 active    🏛️    │
│  watchdog        v1.0.0    🟢 active    🏛️    │
│  working-memory  v1.0.0    🟢 active    🏛️    │
│  scheduler       v1.0.0    🟢 active    ✔     │
│                                                │
└────────────────────────────────────────────────┘
```

### Browse

Searchable catalog. Each card shows name, description, install count, rating, verification badge.

```
┌────────────────────────────────────────────────┐
│  🔍 Search...             Category: [ All ▾ ]  │
│                                                │
│  ┌──────────────────────────────────────────┐  │
│  │  📊 Analytics              ⭐ Featured   │  │
│  │  Token usage, cost tracking, trends      │  │
│  │  ★★★★★  312 installs       v2.1.0       │  │
│  │                       [ Install → ]      │  │
│  └──────────────────────────────────────────┘  │
│                                                │
│  ┌──────────────────────────────────────────┐  │
│  │  🛡️ Rate Limiter           ✔ Verified    │  │
│  │  Per-route rate limiting with backoff    │  │
│  │  ★★★★☆  89 installs        v1.2.0       │  │
│  │                       [ Install → ]      │  │
│  └──────────────────────────────────────────┘  │
└────────────────────────────────────────────────┘
```

### Install Flow

1. Click **Install →**
2. Quick confirmation: routes it registers, config keys it adds, permissions
3. Bifrost downloads, extracts to `plugins/`, calls `register_routes()`
4. Plugin is live. No restart.

### Uninstall

Click plugin → **Uninstall**. Routes deregistered, folder removed. Config keys stay in `valhalla.yaml` (commented out) so reinstalling preserves settings.

---

## Submitting to the Marketplace

```bash
valhalla plugin submit
```

What happens:
1. **Automated checks run instantly:** lint, security scan (no outbound calls without declaration, no file access outside `plugins/`), dependency resolution
2. **Plugin enters review queue**
3. **Manual review within 3–5 days** (first submission) or **1 day** (verified authors)
4. **Published** — appears in Browse catalog

### Verification Tiers

| Badge | What It Means |
|---|---|
| (none) | Reviewed, no known issues |
| ✔ **Verified** | Extended security review, author identity confirmed |
| ⭐ **Featured** | Curated by Valhalla team |
| 🏛️ **Official** | Built by Valhalla core team |

### Review Criteria

- Does what it claims (no placeholders, no dead code)
- No outbound network calls without disclosure
- No file access outside plugin scope
- `health_check()` implemented
- README with usage examples
- `min_valhalla_version` is accurate

---

## Revenue Split

| Type | Author Gets | Valhalla Gets |
|---|---|---|
| **Free / open source** | — | — |
| **Paid** | 80% | 20% |
| **Sponsored listing** | 100% (pays $99/yr listing fee) | $99/yr |

Authors set their own pricing: one-time, subscription, or freemium. Payments handled by Valhalla — authors get monthly payouts.

---

## Enterprise / Air-Gapped

For networks that can't reach the public registry:

```bash
# Export a plugin as a portable archive
valhalla plugin pack scheduler
# → scheduler-1.0.0.tar.gz

# Install from archive on air-gapped node
valhalla plugin install ./scheduler-1.0.0.tar.gz

# Or run a private registry
valhalla registry serve --port 8800
```

---

## Security (Sprint 2)

Sprint 1 plugins run in-process. Sprint 2 adds:

- **Filesystem sandbox** — plugins can only touch `plugins/<name>/` and declared paths
- **Network sandbox** — outbound HTTP requires `allowed_hosts` in `plugin.yaml`
- **Resource limits** — CPU/memory caps per plugin
- **Signing** — verified authors GPG-sign packages, Bifrost verifies on install
