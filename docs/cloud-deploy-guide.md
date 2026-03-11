# Cloud Deploy Guide — Fireside

> **For users who don't have a GPU or want Fireside always-on from any device.**

---

## Overview

Fireside is designed to run on your own hardware — but not everyone has a GPU. For those users, a cloud instance gives the same private experience for $15-30/month.

**Important:** Even on cloud, it's YOUR instance. Your data stays on YOUR server. We never see it.

---

## Option 1: DigitalOcean GPU Droplet

**Cost:** ~$16/month (GPU Droplet, 1x A4000)
**Best for:** Easiest setup, good dashboard

### Steps

1. Create a DigitalOcean account at [digitalocean.com](https://digitalocean.com)
2. Click **Create → Droplets → GPU Droplets**
3. Select:
   - **Image:** Ubuntu 22.04
   - **Plan:** GPU Basic ($16/mo) — 1x NVIDIA A4000, 16GB VRAM
   - **Region:** Closest to you
4. Under **User data**, paste:

```bash
#!/bin/bash
curl -fsSL https://getfireside.ai/install | bash
```

5. Click **Create Droplet**
6. Wait ~5 minutes for setup
7. Open `http://YOUR_DROPLET_IP:3000` in your browser
8. Complete onboarding wizard

### After Setup

- Bookmark the URL — it's your Fireside
- Connect Telegram from the Settings page for mobile access
- Everything persists across reboots

---

## Option 2: AWS Lightsail

**Cost:** ~$25/month (g5.xlarge equivalent)
**Best for:** Users already on AWS

### Steps

1. Go to [lightsail.aws.amazon.com](https://lightsail.aws.amazon.com)
2. Click **Create Instance**
3. Select:
   - **Platform:** Linux/Unix
   - **Blueprint:** Ubuntu 22.04
   - **Plan:** GPU ($25/mo)
4. Under **Launch script**, paste:

```bash
#!/bin/bash
curl -fsSL https://getfireside.ai/install | bash
```

5. Click **Create Instance**
6. Open Networking tab → add port `3000` and `8337` to firewall
7. Open `http://INSTANCE_IP:3000`

---

## Option 3: Hetzner Cloud (Europe)

**Cost:** ~€15/month (cheapest GPU option in EU)
**Best for:** European users, best price/performance

### Steps

1. Create account at [hetzner.com/cloud](https://hetzner.com/cloud)
2. Create Server:
   - **Image:** Ubuntu 22.04
   - **Type:** GPU (GEX44)
   - **Location:** Closest EU datacenter
3. Under **Cloud config**, paste:

```yaml
#cloud-config
runcmd:
  - curl -fsSL https://getfireside.ai/install | bash
```

4. Create server
5. Open firewall: allow TCP 3000, 8337
6. Open `http://SERVER_IP:3000`

---

## Option 4: No GPU? Use Cloud Brains

If you don't want to rent a GPU server, you can run Fireside on ANY cheap server and use a **cloud brain** (OpenAI, Anthropic, Google) instead of a local model.

**Cost:** ~$5/month server + pay-per-use API costs

1. Get a $5/month VPS (DigitalOcean, Hetzner, Linode — any will work)
2. Install Fireside: `curl -fsSL https://getfireside.ai/install | bash`
3. In Settings → Brain, select "Cloud" and paste your API key
4. Your AI runs on the cheap server, intelligence comes from the cloud API
5. Fireside's personality, memory, and learning loop still work — the brain is just remote

**Trade-off:** You lose the "zero cloud" privacy guarantee for the AI responses (your messages go to OpenAI/Anthropic). But your memory, personality, and learning data still stay on YOUR server.

---

## Security for Cloud Instances

| Concern | How to Handle |
|---|---|
| Open to internet | Set up a firewall — only allow YOUR IP |
| No HTTPS | Use Cloudflare Tunnel (free) or Let's Encrypt |
| SSH access | Use SSH keys, disable password auth |
| Data backup | Automated snapshots ($2/mo on most providers) |
| Updates | `git pull && npm run build` — or wait for auto-updater |

### Quick Cloudflare Tunnel (Recommended)

```bash
# Install cloudflared
curl -fsSL https://pkg.cloudflare.com/cloudflared-linux-amd64.deb -o cf.deb
sudo dpkg -i cf.deb

# Create tunnel (free Cloudflare account required)
cloudflared tunnel login
cloudflared tunnel create fireside
cloudflared tunnel route dns fireside my-fireside.mydomain.com

# Run tunnel
cloudflared tunnel --url http://localhost:3000 run fireside
```

Now access your Fireside at `https://my-fireside.mydomain.com` — HTTPS, no open ports.

---

## Cloud vs Local — Which One?

```
┌──────────────────────────────────────────────────────┐
│                                                      │
│   🏠 LOCAL (Free)              ☁️ CLOUD ($15-30/mo)  │
│                                                      │
│   ✅ Completely free            ✅ No GPU needed      │
│   ✅ Maximum privacy            ✅ Always on          │
│   ✅ No monthly cost            ✅ Access from anywhere│
│   ✅ Works offline              ✅ Same features       │
│                                                      │
│   ⚠️ Need a GPU (6+ GB)        ⚠️ Monthly cost       │
│   ⚠️ Off when PC is off        ⚠️ Data on your server│
│                                                      │
│           Both options: YOUR data, YOUR AI.          │
│           We never see it. We never touch it.        │
│                                                      │
└──────────────────────────────────────────────────────┘
```

---

## FAQ

**Q: Can I start on cloud and move to local later?**
A: Yes. Export your data (`~/.valhalla/`), install locally, copy data over. Everything transfers — personality, memory, achievements, everything.

**Q: Is cloud as private as local?**
A: Almost. Your data lives on YOUR server (not ours). But the server provider (DigitalOcean, etc.) technically has physical access to the hardware. For maximum privacy, run locally.

**Q: Can I share my cloud instance with family?**
A: Yes — multiple people can access the same URL. Each gets the same AI. For separate personalities, run separate instances.

**Q: What if I stop paying?**
A: Your server shuts down. Your data is preserved in snapshots for ~30 days. Restart anytime, or download your data before canceling.
