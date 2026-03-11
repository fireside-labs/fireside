# Add a Node — One Button, One Command, Done

---

## The Flow

```
Dashboard: click "Add Node"
         ↓
Dashboard: shows a one-line command
         ↓
User: pastes command on second machine
         ↓
Dashboard: node appears live (< 30 seconds)
         ↓
Dashboard: user picks role, model, soul
         ↓
Done. Node is working.
```

No config files. No IP addresses. No SSH. No YAML editing.

---

## Step 1 — Click "Add Node"

The Nodes page has a `+ Add Node` button. First-time single-node users also get a card:

```
┌────────────────────────────────────────┐
│  🌐 Running solo.                     │
│                                        │
│  Add a second machine and your agents  │
│  start collaborating. One command.     │
│                                        │
│  [ Add Node → ]                        │
└────────────────────────────────────────┘
```

---

## Step 2 — Get the Join Command

A modal appears with a single copyable command:

```
┌────────────────────────────────────────────────┐
│  🌐 Add a Node                                │
│                                                │
│  Run this on your second machine:              │
│                                                │
│  ┌──────────────────────────────────────────┐  │
│  │ valhalla join odin@100.117.255.38  📋   │  │
│  └──────────────────────────────────────────┘  │
│                                                │
│  ⏱ Expires in 15 minutes                      │
│                                                │
│  Need to install first?                        │
│  brew install valhalla                         │
│                                                │
│                          [ Waiting... 🔄 ]     │
└────────────────────────────────────────────────┘
```

**What's happening under the hood:**
- `POST /api/v1/mesh/join-token` generates an HMAC-signed, single-use token baked into the command
- Token contains: orchestrator address, encrypted mesh secret, 15-minute expiry
- The modal polls `/api/v1/nodes` every 2 seconds, waiting for the new node

**Design rules:**
- The command is SHORT. No `--token vk_abc123def456ghi789...` visible. The token is embedded in a short code (`odin@100.117.255.38` resolves to `odin@100.117.255.38:8765?t=<short_token>`)
- One click to copy
- If they don't have Valhalla installed, the install command is right there — no "see docs"

---

## Step 3 — Run the Command

On the second machine:

```bash
valhalla join odin@100.117.255.38
```

```
⚡ Joining mesh...

  ✔ Connected to odin
  ✔ GPU: RTX 4090 (24 GB)
  ✔ Inference: Ollama detected (llama3.1:8b)
  ✔ Config written: valhalla.yaml
  ✔ Bifrost started
  ✔ Announced to mesh

  This node is live. Configure it from odin's dashboard.
```

**What's happening:**
1. CLI hits the orchestrator, validates the token
2. Orchestrator sends back mesh config (auth secret, peer list)
3. CLI auto-detects GPU and inference engine — same as `valhalla init`
4. Writes a local `valhalla.yaml` with auto-generated node name (hostname)
5. Starts Bifrost
6. Announces to the mesh via `POST /api/v1/mesh/announce`

**Total time: 15–30 seconds.**

---

## Step 4 — Node Appears in Dashboard

The modal on the orchestrator's dashboard transitions:

```
┌────────────────────────────────────────────────┐
│  ✔ thor-desktop connected!                    │
│                                                │
│  Role:                                         │
│    ● backend       Deep reasoning, code exec   │
│    ○ memory        RAG, dream cycles           │
│    ○ security      Threat detection, immune    │
│    ○ worker        General purpose             │
│                                                │
│  Model:                                        │
│    llama3.1:8b (auto-detected)      [ Change ] │
│                                                │
│  Soul:                                         │
│    ○ Generate new personality                  │
│    ● Clone from odin                           │
│                                                │
│            [ Skip ]     [ Activate → ]         │
└────────────────────────────────────────────────┘
```

Click **Activate** → the node card appears on the Nodes page with a green pulse and a "🆕" badge.

Click **Skip** → node joins as a generic worker. User can configure later.

---

## Error States

Every error tells the user exactly what to do. No "check the docs."

**Token expired:**
```
✗ This join link expired.
  Go back to the dashboard and click "Add Node" for a new one.
```

**Can't reach orchestrator:**
```
✗ Can't reach odin@100.117.255.38:8765

  Check:
  1. Is Valhalla running on odin?  →  valhalla status
  2. Same network or Tailnet?      →  ping 100.117.255.38
  3. Firewall blocking 8765?       →  sudo ufw allow 8765
```

**Name conflict:**
```
⚠ "thor-desktop" already exists in this mesh.
  Joining as "thor-desktop-2" instead.
  Rename from the dashboard anytime.
```

**No GPU:**
```
⚠ No GPU detected. Inference will use CPU (slow).
  Recommended: install Ollama with a small model (phi3:mini)
  or connect a cloud provider from the dashboard.

  Continue anyway? [Y/n]
```

**Node goes offline after joining:**
The node card switches to a red indicator with "Last seen: 2m ago." Auto-reconnect runs every 30 seconds. When it reconnects, missed events sync via gossip.

---

## Removing a Node

From the dashboard: click the node card → **Remove Node** → confirm.

- Node's auth is revoked instantly
- Removal event broadcasts to all peers
- Config keys are preserved on the removed machine (commented out in YAML) so rejoining is trivial

---

## API Surface (for Thor to implement)

| Endpoint | Method | What It Does |
|---|---|---|
| `/api/v1/mesh/join-token` | POST | Generate time-limited join link |
| `/api/v1/mesh/announce` | POST | New node announces itself |
| `/api/v1/nodes` | GET | All nodes + status |
| `/api/v1/nodes/{name}/config` | PUT | Push role/model/soul config to a node |
| `/api/v1/nodes/{name}` | DELETE | Remove a node, revoke auth |
