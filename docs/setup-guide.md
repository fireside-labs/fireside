# Setup Guide

> **Goal:** From zero to chatting with your AI in under 5 minutes on any platform.

---

## Quick Start (Impatient Version)

```bash
# One line. That's it.
curl -fsSL https://get.valhalla.ai | bash
```

This detects your hardware, installs dependencies, downloads a brain, starts the dashboard, and opens `http://localhost:3000` where the onboarding wizard takes over.

**Total time:** ~3 minutes on good internet.

---

## Platform-Specific Instructions

### macOS (Apple Silicon — M1, M2, M3, M4)

**Prerequisites:** None. The installer handles everything.

**What the installer does:**
1. Installs Homebrew (if missing)
2. Installs Python 3.10+ via Homebrew
3. Installs Node.js 18+ via Homebrew
4. Clones the Valhalla repo
5. Installs Python and Node dependencies
6. Detects your Apple Silicon GPU + unified memory
7. Generates `valhalla.yaml` with recommended settings
8. Starts Bifrost (backend) + dashboard (frontend)
9. Opens `http://localhost:3000`

**What happens next:**
- The onboarding wizard asks your name and preferred personality
- It recommends **oMLX** as your inference runtime (native Metal acceleration)
- You click "Install Brain" → downloads and starts the model
- You're chatting within ~3 minutes

**Manual install (if you prefer):**
```bash
# Clone
git clone https://github.com/yourusername/valhalla-mesh-v2.git
cd valhalla-mesh-v2

# Backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Dashboard
cd dashboard
npm install
cd ..

# Start
python -m bifrost &
cd dashboard && npm run dev &
open http://localhost:3000
```

---

### Linux (Ubuntu / Debian)

**Prerequisites:** None (installer uses `apt`).

**What the installer does:**
1. Installs Python 3.10+ and Node.js 18+ via `apt`
2. Detects NVIDIA GPU via `nvidia-smi` (if present)
3. If NVIDIA GPU found → installs `llama-server` (llama.cpp) for maximum speed
4. If no GPU → configures cloud-only mode (NVIDIA NIM free tier)
5. Everything else same as Mac

**Manual install:**
```bash
sudo apt update && sudo apt install -y python3 python3-venv nodejs npm
git clone https://github.com/yourusername/valhalla-mesh-v2.git
cd valhalla-mesh-v2
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cd dashboard && npm install && cd ..
python -m bifrost &
cd dashboard && npm run dev &
```

**NVIDIA GPU users:**
The brain installer page in the dashboard handles everything — detects your GPU, downloads the model, and starts `llama-server` with optimal settings. No manual CUDA setup needed.

---

### Windows 10/11

**Prerequisites:** None. The installer runs natively — no WSL needed.

**Quick start (PowerShell):**
```powershell
# In PowerShell
irm https://get.valhalla.ai/win | iex
```

**What the installer does:**
1. Installs Python 3.10+ (winget or python.org)
2. Installs Node.js 18+ (winget)
3. Clones the Valhalla repo
4. Installs Python and Node dependencies
5. Detects NVIDIA GPU via `nvidia-smi`
6. Downloads pre-built `llama-server.exe` from llama.cpp releases (native Windows + CUDA)
7. Starts Bifrost + dashboard
8. Opens `http://localhost:3000`

**NVIDIA GPU:** `llama-server` runs natively on Windows with full CUDA support — same performance as Linux. No WSL needed.

**No NVIDIA GPU:** The installer configures cloud-only mode (NVIDIA NIM free tier). Paste an API key and you're running.

**Manual install:**
```powershell
git clone https://github.com/yourusername/valhalla-mesh-v2.git
cd valhalla-mesh-v2

python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

cd dashboard
npm install
cd ..

# Start (two terminal windows)
python -m bifrost          # Terminal 1
cd dashboard; npm run dev  # Terminal 2
# Open http://localhost:3000
```

**Auto-start on boot:** The installer creates a scheduled task (`Valhalla Inference`) that starts `llama-server.exe` at login.

---

## "I Already Have..." Fast Paths

### I already have Ollama running

Valhalla detects existing Ollama installations automatically. In Settings → Brain, you'll see an "Ollama (detected)" option. Select it and Valhalla routes inference through your existing Ollama server.

**No changes needed to your Ollama setup.** Valhalla just points at `http://localhost:11434`.

> [!NOTE]
> Valhalla doesn't install Ollama by default. We prefer oMLX (Mac) and llama-server (Linux/Windows) for better performance. But if you already have Ollama, we use it.

### I already have llama-server or llama.cpp

Point Valhalla at it in Settings:
```yaml
# In valhalla.yaml (or use the Settings form)
models:
  default: "local"
  providers:
    local:
      type: openai
      base_url: "http://localhost:8080/v1"
```

Or in the dashboard: Settings → Brain → "I already have a brain running" → paste your server URL.

### I already have an NVIDIA NIM / OpenAI API key

In the dashboard onboarding or Settings → Brain → Cloud Expert → paste your API key. Valhalla validates it immediately and shows "✅ Connected."

---

## After Install

### What's running?

| Process | Port | What it does |
|---|---|---|
| Bifrost | 8444 | Python backend — plugins, API, WebSocket |
| Dashboard | 3000 | Next.js frontend — the dashboard UI |
| Inference | 8080 | Your AI brain (oMLX, llama-server, or cloud) |

### Where are files?

| Path | What's there |
|---|---|
| `valhalla.yaml` | All configuration |
| `mesh/souls/` | Agent personality files (SOUL.md, IDENTITY.md, USER.md) |
| `plugins/` | All plugins (add-ons) |
| `~/.valhalla/credentials` | API keys (encrypted, never in git) |
| `~/.cache/huggingface/` | Downloaded model files |

### How to stop everything

```bash
# Or just close the terminal windows
pkill -f bifrost
pkill -f "npm run dev"
pkill -f llama-server  # if using local inference
```

### How to start again

```bash
cd valhalla-mesh-v2
python -m bifrost &
cd dashboard && npm run dev &
```

Or if installed via `install.sh`, it created a launch agent — just restart your computer and everything starts automatically.

---

## Troubleshooting

### "Port 3000 is already in use"

Something else is using port 3000 (common if you have another dev server running).

```bash
# Find what's using it
lsof -i :3000
# Kill it
kill -9 <PID>
# Or use a different port
cd dashboard && PORT=3001 npm run dev
```

### "No GPU detected" (but I have one)

**Mac:** All Apple Silicon Macs have a GPU. If the installer says "No GPU," you're probably on an Intel Mac — cloud mode is recommended.

**Linux/Windows:** Make sure NVIDIA drivers are installed:
```bash
nvidia-smi
# If this doesn't work, install drivers:
sudo apt install nvidia-driver-535
```

### "Model download is slow"

Model files are 4-8 GB. On slow internet:
- Use the "Cloud Expert" brain instead (no download needed, just an API key)
- Download overnight and come back
- The progress bar in the dashboard shows real-time speed

### "pip install fails"

```bash
# Make sure you're in the virtual environment
source .venv/bin/activate
# Upgrade pip
pip install --upgrade pip
# Try again
pip install -r requirements.txt
```

### "npm install fails"

```bash
# Clear cache and retry
rm -rf node_modules package-lock.json
npm install
```

### "Bifrost/backend won't start"

```bash
# Check if valhalla.yaml exists and is valid
python -c "import yaml; yaml.safe_load(open('valhalla.yaml'))"
# If it fails, the YAML has a syntax error. 
# Reset to defaults:
cp valhalla.yaml.example valhalla.yaml
```

### "I can't connect from another device"

By default, Valhalla only listens on `localhost` (this computer). To access from your phone or another computer on the same network:

```yaml
# In valhalla.yaml
node:
  host: "0.0.0.0"  # Listen on all interfaces
```

Then access via `http://<your-computer-ip>:3000` from the other device.

> [!WARNING]
> Only do this on trusted networks. Anyone on the same network can access the dashboard.

---

## Uninstall

```bash
# Remove the app
rm -rf valhalla-mesh-v2

# Remove model cache (optional — frees 4-8 GB)
rm -rf ~/.cache/huggingface/hub/models--*

# Remove credentials
rm -rf ~/.valhalla

# Remove launch agent (macOS)
rm ~/Library/LaunchAgents/ai.valhalla.*.plist

# Remove systemd service (Linux)
systemctl --user disable valhalla-inference
rm ~/.config/systemd/user/valhalla-*.service
```

**Windows (PowerShell):**
```powershell
# Remove the app
Remove-Item -Recurse valhalla-mesh-v2

# Remove model cache
Remove-Item -Recurse "$env:USERPROFILE\.cache\huggingface\hub\models--*"

# Remove credentials
Remove-Item -Recurse "$env:USERPROFILE\.valhalla"

# Remove scheduled task
Unregister-ScheduledTask -TaskName "Valhalla Inference" -Confirm:$false
```
