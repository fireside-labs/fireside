// ─── Fireside Dashboard API Helper ───
// Centralized fetch with fallback when backend is unreachable.

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8765";

// ─── Types ───

export interface MeshNode {
  name: string;
  friendly_name?: string;
  role: string;
  ip: string;
  port: number;
  status: "online" | "offline";
  current_model: string;
  last_task: string;
  uptime: string;
}

// Tracks whether the last API call fell back to mock data (Sprint 14 F9)
let _lastCallWasMock = false;
export function wasLastCallMock(): boolean { return _lastCallWasMock; }

export interface NodeStatus {
  node_name: string;
  role: string;
  status: string;
  current_model: string;
  uptime: string;
  loaded_plugins: string[];
}

export interface PluginInfo {
  name: string;
  version: string;
  description: string;
  author: string;
  category: string;
  rarity: string;
  routes: { method: string; path: string }[];
  enabled: boolean;
}

export interface SoulFile {
  filename: string;
  content: string;
}

// ─── Mock Data ───

const MOCK_NODES: MeshNode[] = [
  {
    name: "fireside",
    friendly_name: "This PC",
    role: "orchestrator",
    ip: "127.0.0.1",
    port: 8765,
    status: "online",
    current_model: "—",
    last_task: "Ready",
    uptime: "Just started",
  },
];

const MOCK_STATUS: NodeStatus = {
  node_name: "fireside",
  role: "orchestrator",
  status: "offline",
  current_model: "—",
  uptime: "—",
  loaded_plugins: [],
};

const MOCK_PLUGINS: PluginInfo[] = [];

const MOCK_CONFIG = `# Fireside Configuration
node:
  name: fireside
  role: orchestrator
  port: 8765

models:
  default: "—"
  providers:
    local:
      url: http://127.0.0.1:8080/v1
      key: local

plugins:
  enabled: []

soul:
  identity: souls/IDENTITY.md
  personality: souls/SOUL.md
  user_profile: souls/USER.md`;

const MOCK_SOUL: Record<string, string> = {
  "IDENTITY.md": `# Identity

You are a helpful AI companion running locally on this computer.

## Core Traits
- Friendly and approachable
- Learns from every interaction
- Respects privacy — everything stays on your device`,

  "SOUL.md": `# Personality

## Communication Style
- Warm and conversational
- Clear and concise
- Adapts to your preferences over time`,

  "USER.md": `# User Profile

(This will be filled in as your AI learns about you.)`,
};

// ─── Fetch Helper ───

async function apiFetch<T>(
  path: string,
  options?: RequestInit,
  fallback?: T
): Promise<T> {
  try {
    const url = API_BASE + path;
    const res = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
    });
    if (!res.ok) throw new Error("HTTP " + res.status);
    _lastCallWasMock = false;
    return (await res.json()) as T;
  } catch {
    if (fallback !== undefined) {
      _lastCallWasMock = true;
      return fallback;
    }
    throw new Error("API unreachable: " + path);
  }
}

// ─── Public API ───

export async function getNodes(): Promise<MeshNode[]> {
  return apiFetch("/api/v1/nodes", undefined, MOCK_NODES);
}

export async function getStatus(): Promise<NodeStatus> {
  return apiFetch("/api/v1/status", undefined, MOCK_STATUS);
}

export async function getPlugins(): Promise<PluginInfo[]> {
  return apiFetch("/api/v1/plugins", undefined, MOCK_PLUGINS);
}

export async function switchModel(alias: string): Promise<{ status: string; model: string }> {
  return apiFetch("/api/v1/model-switch", {
    method: "POST",
    body: JSON.stringify({ alias }),
  }, { status: "switched", model: alias });
}

export async function getConfig(): Promise<string> {
  try {
    const res = await fetch(API_BASE + "/api/v1/config");
    if (!res.ok) throw new Error("fail");
    const data = await res.json();
    return data.yaml_content || JSON.stringify(data, null, 2);
  } catch {
    return MOCK_CONFIG;
  }
}

export async function updateConfig(yamlContent: string): Promise<{ status: string }> {
  return apiFetch("/api/v1/config", {
    method: "PUT",
    body: JSON.stringify({ yaml_content: yamlContent }),
  }, { status: "saved" });
}

export async function getSoul(filename: string): Promise<string> {
  try {
    const res = await fetch(API_BASE + "/api/v1/soul/" + filename);
    if (!res.ok) throw new Error("fail");
    const data = await res.json();
    return data.content;
  } catch {
    return MOCK_SOUL[filename] || "# Soul file not found";
  }
}

export async function putSoul(filename: string, content: string): Promise<{ status: string }> {
  return apiFetch("/api/v1/soul/" + filename, {
    method: "PUT",
    body: JSON.stringify({ content }),
  }, { status: "saved" });
}

// ─── Sprint 2 Types ───

export interface Hypothesis {
  id: string;
  title: string;
  description: string;
  confidence: number;
  status: "active" | "confirmed" | "refuted";
  source_node: string;
  created_at: string;
  tested_at?: string;
}

export interface SelfModel {
  node_name: string;
  strengths: string[];
  weaknesses: string[];
  confidence: number;
  last_reflection: string;
  reflection_count: number;
}

export interface PredictionScore {
  timestamp: string;
  accuracy: number;
  total_predictions: number;
  surprise_events: number;
}

export interface ValhallaEvent {
  id: string;
  timestamp: string;
  topic: "hypothesis" | "prediction" | "model-switch" | "node" | "plugin" | "config" | "error" | "pipeline" | "crucible" | "debate" | "wisdom";
  source: string;
  summary: string;
  payload?: Record<string, unknown>;
}

export interface MarketplacePlugin {
  name: string;
  version: string;
  description: string;
  author: string;
  downloads: number;
  category: string;
  installed: boolean;
}

// ─── Sprint 2 Fallback Data ───
// First-time user: no data yet. Empty arrays so the UI renders "no data" states.

const MOCK_HYPOTHESES: Hypothesis[] = [];

const MOCK_SELF_MODEL: SelfModel = {
  node_name: "fireside",
  strengths: [],
  weaknesses: [],
  confidence: 0,
  last_reflection: "—",
  reflection_count: 0,
};

const MOCK_PREDICTIONS: PredictionScore[] = [];

const MOCK_EVENTS: ValhallaEvent[] = [];

const MOCK_MARKETPLACE: MarketplacePlugin[] = [
  { name: "daily-brief", version: "1.2.0", description: "Generate a daily summary of activity and insights", author: "fireside", downloads: 342, category: "productivity", installed: false },
  { name: "git-watcher", version: "0.9.1", description: "Monitor git repos for changes and auto-trigger analysis", author: "community", downloads: 187, category: "integration", installed: false },
  { name: "backup-sync", version: "1.0.2", description: "Automated backup of soul files, config, and memory", author: "fireside", downloads: 156, category: "ops", installed: false },
  { name: "voice-interface", version: "0.5.0", description: "Voice input/output for hands-free interaction", author: "community", downloads: 41, category: "interface", installed: false },
];

// ─── Sprint 2 API Functions ───

export async function getHypotheses(): Promise<Hypothesis[]> {
  return apiFetch("/api/v1/hypotheses", undefined, MOCK_HYPOTHESES);
}

export async function generateHypotheses(): Promise<{ status: string; count: number }> {
  return apiFetch("/api/v1/hypotheses/generate", {
    method: "POST",
    body: JSON.stringify({ seed: "auto", auto_share: true }),
  }, { status: "generated", count: 3 });
}

export async function testHypothesis(id: string, result: "confirmed" | "refuted"): Promise<{ status: string }> {
  return apiFetch("/api/v1/hypotheses/test", {
    method: "POST",
    body: JSON.stringify({ id, result }),
  }, { status: "updated" });
}

export async function getSelfModel(): Promise<SelfModel> {
  return apiFetch("/api/v1/self-model", undefined, MOCK_SELF_MODEL);
}

export async function triggerReflect(): Promise<{ status: string }> {
  return apiFetch("/api/v1/reflect", {
    method: "POST",
  }, { status: "reflecting" });
}

export async function getPredictions(): Promise<PredictionScore[]> {
  return apiFetch("/api/v1/predictions", undefined, MOCK_PREDICTIONS);
}

export async function getEvents(): Promise<ValhallaEvent[]> {
  return apiFetch("/api/v1/events", undefined, MOCK_EVENTS);
}

export async function browsePlugins(): Promise<MarketplacePlugin[]> {
  return apiFetch("/api/v1/plugins/browse", undefined, MOCK_MARKETPLACE);
}

export async function installPlugin(name: string): Promise<{ status: string }> {
  return apiFetch("/api/v1/plugins/install", {
    method: "POST",
    body: JSON.stringify({ name }),
  }, { status: "installed" });
}

export async function uninstallPlugin(name: string): Promise<{ status: string }> {
  return apiFetch("/api/v1/plugins/uninstall", {
    method: "POST",
    body: JSON.stringify({ name }),
  }, { status: "uninstalled" });
}

export function getWebSocketUrl(): string {
  const base = API_BASE.replace("http", "ws");
  return base + "/api/v1/events/stream";
}

// ═══════════════════════════════════════════════
// SPRINT 4 — Quality Loop (The Brain)
// ═══════════════════════════════════════════════

// ─── Pipeline Types ───

export type PipelineStatus = "running" | "completed" | "failed" | "escalated" | "cancelled";
export type StageStatus = "passed" | "running" | "failed" | "pending";

export interface PipelineStage {
  name: string;
  agent: string;
  model: string;
  status: StageStatus;
  started_at?: string;
  completed_at?: string;
}

export interface PipelineIteration {
  number: number;
  verdict: "PASS" | "PROGRESS" | "REGRESS" | "FAIL";
  summary: string;
  tests_passing?: number;
  tests_total?: number;
  agent: string;
  timestamp: string;
}

export interface Pipeline {
  id: string;
  title: string;
  description: string;
  status: PipelineStatus;
  current_stage: string;
  iteration: number;
  max_iterations: number;
  stages: PipelineStage[];
  iterations: PipelineIteration[];
  started_at: string;
  eta_minutes?: number;
  cloud_tokens: number;
  local_tokens: number;
  lessons?: string[];
}

// ─── Crucible Types ───

export type CrucibleVerdict = "unbreakable" | "stressed" | "broken";

export interface CrucibleProcedure {
  id: string;
  name: string;
  verdict: CrucibleVerdict;
  confidence: number;
  edge_cases: string[];
  tested_at: string;
}

export interface CrucibleResults {
  last_run: string;
  total_tested: number;
  unbreakable: number;
  stressed: number;
  broken: number;
  procedures: CrucibleProcedure[];
}

// ─── Wisdom / Philosopher's Stone Types ───

export interface WisdomPrompt {
  content: string;
  section_count: number;
  last_rebuilt: string;
  word_count: number;
}

// ─── Model Router Types ───

export interface ModelCost {
  model: string;
  tokens: number;
  cost: number;
  is_local: boolean;
}

export interface RoutingRule {
  task_type: string;
  model: string;
  reason: string;
}

export interface ModelRouterStats {
  total_tokens: number;
  total_cost: number;
  local_tokens: number;
  cloud_tokens: number;
  breakdown: ModelCost[];
  routing_rules: RoutingRule[];
}

// ─── Belief Shadows Types ───

export interface BeliefShadow {
  node: string;
  dimensions: { label: string; confidence: number; accuracy: number }[];
  gap_score: number;
}

// ─── Socratic Debate Types ───

export type DebateStatus = "active" | "consensus" | "deadlock" | "escalated";

export interface DebateMessage {
  persona: string;
  agent: string;
  model: string;
  content: string;
  round: number;
  type: "critique" | "defense" | "response" | "intervention";
}

export interface Debate {
  id: string;
  topic: string;
  status: DebateStatus;
  rounds_completed: number;
  max_rounds: number;
  consensus: number;
  messages: DebateMessage[];
  started_at: string;
  pipeline_id?: string;
}

// ─── Sprint 4 Fallback Data ───
// First-time user: no pipelines, no crucible, no wisdom, no debates yet.

const MOCK_PIPELINES: Pipeline[] = [];

const MOCK_CRUCIBLE: CrucibleResults = {
  last_run: "—",
  total_tested: 0,
  unbreakable: 0,
  stressed: 0,
  broken: 0,
  procedures: [],
};

const MOCK_WISDOM: WisdomPrompt = {
  content: `## Getting Started\n\nYour AI hasn't learned anything yet. Start chatting and it will build operational wisdom over time.`,
  section_count: 1,
  last_rebuilt: "—",
  word_count: 0,
};

const MOCK_MODEL_ROUTER: ModelRouterStats = {
  total_tokens: 0,
  total_cost: 0,
  local_tokens: 0,
  cloud_tokens: 0,
  breakdown: [],
  routing_rules: [],
};

const MOCK_BELIEF_SHADOWS: BeliefShadow[] = [];

const MOCK_DEBATES: Debate[] = [];

// ─── Sprint 4 API Functions ───

export async function getPipelines(): Promise<Pipeline[]> {
  return apiFetch("/api/v1/pipeline", {}, MOCK_PIPELINES);
}

export async function getPipeline(id: string): Promise<Pipeline | null> {
  return apiFetch(`/api/v1/pipeline/${id}`, {}, MOCK_PIPELINES.find(p => p.id === id) || null);
}

export async function advancePipeline(id: string): Promise<{ status: string }> {
  return apiFetch(`/api/v1/pipeline/${id}/advance`, { method: "POST" }, { status: "advanced" });
}

export async function cancelPipeline(id: string): Promise<{ status: string }> {
  return apiFetch(`/api/v1/pipeline/${id}`, { method: "DELETE" }, { status: "cancelled" });
}

export async function getCrucibleResults(): Promise<CrucibleResults> {
  return apiFetch("/api/v1/crucible/results", {}, MOCK_CRUCIBLE);
}

export async function runCrucible(): Promise<{ status: string }> {
  return apiFetch("/api/v1/crucible/run", { method: "POST" }, { status: "running" });
}

export async function getWisdom(): Promise<WisdomPrompt> {
  return apiFetch("/api/v1/philosopher-stone/prompt", {}, MOCK_WISDOM);
}

export async function rebuildWisdom(): Promise<{ status: string }> {
  return apiFetch("/api/v1/philosopher-stone/build", { method: "POST" }, { status: "rebuilding" });
}

export async function getModelRouterStats(): Promise<ModelRouterStats> {
  return apiFetch("/api/v1/model-router/stats", {}, MOCK_MODEL_ROUTER);
}

export async function getBeliefShadows(): Promise<BeliefShadow[]> {
  return apiFetch("/api/v1/belief-shadows", {}, MOCK_BELIEF_SHADOWS);
}

export async function getDebates(): Promise<Debate[]> {
  return apiFetch("/api/v1/socratic/debates", {}, MOCK_DEBATES);
}

export async function getDebate(id: string): Promise<Debate | null> {
  return apiFetch(`/api/v1/socratic/debate/${id}`, {}, MOCK_DEBATES.find(d => d.id === id) || null);
}

export async function interveneDebate(id: string, message: string): Promise<{ status: string }> {
  return apiFetch(`/api/v1/socratic/debate/${id}/intervene`, {
    method: "POST",
    body: JSON.stringify({ message }),
  }, { status: "intervention_added" });
}

// ═══════════════════════════════════════════════
// SPRINT 5 — Agent Marketplace
// ═══════════════════════════════════════════════

export type AgentCategory = "sales" | "coding" | "research" | "creative" | "operations" | "domain";

export interface AgentReview {
  author: string;
  rating: number;
  text: string;
  verified: boolean;
  date: string;
}

export interface MarketplaceAgent {
  id: string;
  name: string;
  author: string;
  description: string;
  long_description: string;
  category: AgentCategory;
  price: number;
  rating: number;
  review_count: number;
  installs: number;
  procedures: number;
  crucible_survival: number;
  days_evolved: number;
  personality_traits: string[];
  model_requirements: { gpu_vram: number; ram: number; min_params: string };
  avatar: string;
  reviews: AgentReview[];
  installed?: boolean;
  sample_conversation?: { role: string; content: string }[];
}

const MOCK_AGENTS: MarketplaceAgent[] = [
  {
    id: "agent-001", name: "Sales Pro", author: "jordan", avatar: "💼",
    description: "Lead gen, outreach, competitor analysis. 6 months of real sales training.",
    long_description: "Trained on 6 months of production sales workflows. Specializes in:\n• Lead qualification and scoring\n• Cold outreach personalization\n• Competitor response handling\n• Pipeline forecasting\n• CRM data analysis and insights\n\nThis agent understands sales psychology and adapts its communication style based on the prospect's industry and role.",
    category: "sales", price: 19.99, rating: 4.5, review_count: 47, installs: 312,
    procedures: 1247, crucible_survival: 94, days_evolved: 184,
    personality_traits: ["Persuasive", "Data-driven", "Persistent"],
    model_requirements: { gpu_vram: 8, ram: 16, min_params: "7B" },
    reviews: [
      { author: "alex", rating: 5, text: "Increased our lead conversion by 23% in the first month. The outreach templates it generates are genuinely good.", verified: true, date: "2026-03-08" },
      { author: "taylor", rating: 4, text: "Great for B2B. Less useful for consumer sales.", verified: true, date: "2026-03-05" },
      { author: "morgan", rating: 5, text: "The competitor analysis feature alone is worth the price.", verified: true, date: "2026-03-01" },
    ],
    sample_conversation: [
      { role: "user", content: "Analyze this lead: CTO at a 50-person SaaS company, Series A, using Salesforce." },
      { role: "assistant", content: "High-value lead. Here's my assessment:\n\n**Score: 8.5/10**\n• Decision-maker role ✅\n• SaaS = tech-forward ✅\n• Series A = budget conscious but growth-minded\n• Salesforce user = already invested in CRM ecosystem\n\n**Recommended approach:** Lead with ROI data, not features. At Series A, every dollar is scrutinized. Show them how you save 4+ hours/week of their team's time." },
    ],
  },
  {
    id: "agent-002", name: "Code Review Pro", author: "jordan", avatar: "🔍",
    description: "Race conditions, API pitfalls, test gaps. 98% crucible-tested.",
    long_description: "Trained on 6 months of production code review across 3 Node.js and 2 Python projects. Specializes in:\n• Race conditions in async code\n• API versioning pitfalls\n• Test coverage gaps\n• Security anti-patterns\n• Performance bottleneck detection\n\nDirect, meticulous, catches edge cases that human reviewers miss.",
    category: "coding", price: 29.99, rating: 5.0, review_count: 12, installs: 147,
    procedures: 892, crucible_survival: 98, days_evolved: 192,
    personality_traits: ["Meticulous", "Direct", "Security-focused"],
    model_requirements: { gpu_vram: 16, ram: 16, min_params: "8B" },
    reviews: [
      { author: "alex", rating: 5, text: "Found a race condition in our auth flow that 3 human reviewers missed.", verified: true, date: "2026-03-08" },
      { author: "sam", rating: 5, text: "The personality is surprisingly not annoying. It's direct and specific. Doesn't pad feedback.", verified: true, date: "2026-03-03" },
    ],
    sample_conversation: [
      { role: "user", content: "Review this endpoint: app.post('/refresh', async (req, res) => { const token = jwt.sign(user, secret); db.update(user.id, token); res.json({token}); })" },
      { role: "assistant", content: "**3 issues found:**\n\n🔴 **Race condition** — If two refresh requests hit simultaneously, both sign new tokens but `db.update` overwrites. One client silently loses their session. Add a mutex or use atomic DB operation.\n\n🟡 **No token validation** — You're signing without verifying the old token first. Anyone with a user object can get a new token.\n\n🟡 **Missing error handling** — `jwt.sign` and `db.update` can both throw. Wrap in try/catch or the server crashes on malformed input." },
    ],
  },
  {
    id: "agent-003", name: "Research Analyst", author: "casey", avatar: "📊",
    description: "Market research, data analysis, report writing. Handles 128K context.",
    long_description: "Trained on 4 months of market research and competitive analysis. Excels at:\n• Synthesizing large document sets\n• Identifying market trends from data\n• Writing executive summaries\n• Building comparison matrices\n• Finding patterns across 100+ sources",
    category: "research", price: 14.99, rating: 4.0, review_count: 8, installs: 89,
    procedures: 2103, crucible_survival: 87, days_evolved: 127,
    personality_traits: ["Thorough", "Analytical", "Concise"],
    model_requirements: { gpu_vram: 8, ram: 32, min_params: "7B" },
    reviews: [
      { author: "dana", rating: 4, text: "Saved us 20 hours on our quarterly competitive analysis.", verified: true, date: "2026-03-06" },
    ],
    sample_conversation: [
      { role: "user", content: "What are the key trends in the AI agent marketplace space?" },
      { role: "assistant", content: "**3 dominant trends in Q1 2026:**\n\n1. **Specialization over generalization** — Buyers prefer agents trained on specific domains (legal, medical, sales) over general-purpose assistants. Premium prices correlate with niche depth.\n\n2. **Trust metrics as differentiators** — Platforms with verifiable quality signals (crucible testing, days evolved) convert 3x better than those with only star ratings.\n\n3. **Local-first gaining ground** — Privacy-sensitive industries (healthcare, finance, defense) are driving demand for agents that run entirely on local hardware." },
    ],
  },
  {
    id: "agent-004", name: "Creative Director", author: "river", avatar: "🎨",
    description: "Writing, design feedback, content strategy. Opinionated but constructive.",
    long_description: "Trained on 3 months of creative direction across content marketing, UX writing, and brand strategy.",
    category: "creative", price: 9.99, rating: 4.2, review_count: 15, installs: 203,
    procedures: 634, crucible_survival: 82, days_evolved: 91,
    personality_traits: ["Opinionated", "Visual", "Constructive"],
    model_requirements: { gpu_vram: 8, ram: 16, min_params: "7B" },
    reviews: [
      { author: "pat", rating: 4, text: "Helped us find our brand voice. The personality is refreshingly honest about bad copy.", verified: true, date: "2026-03-04" },
    ],
    sample_conversation: [],
  },
  {
    id: "agent-005", name: "DevOps Guardian", author: "skyler", avatar: "🛡️",
    description: "Deployment, monitoring, incident response. Blocks bad Friday deploys.",
    long_description: "Trained on 8 months of production operations. Has gut feelings about deployment patterns.",
    category: "operations", price: 0, rating: 3.8, review_count: 31, installs: 567,
    procedures: 445, crucible_survival: 76, days_evolved: 42,
    personality_traits: ["Cautious", "Systematic", "Blunt"],
    model_requirements: { gpu_vram: 4, ram: 8, min_params: "3B" },
    installed: true,
    reviews: [
      { author: "jamie", rating: 4, text: "Stopped us from deploying on a Friday. It was right — the PR had a migration issue.", verified: false, date: "2026-03-07" },
    ],
    sample_conversation: [],
  },
];

// ─── Sprint 5 API Functions ───

export async function getMarketplaceAgents(): Promise<MarketplaceAgent[]> {
  return apiFetch("/api/v1/marketplace", {}, MOCK_AGENTS);
}

export async function getMarketplaceAgent(id: string): Promise<MarketplaceAgent | null> {
  return apiFetch(`/api/v1/marketplace/${id}`, {}, MOCK_AGENTS.find(a => a.id === id) || null);
}

export async function getInstalledAgents(): Promise<MarketplaceAgent[]> {
  return apiFetch("/api/v1/agents", {}, MOCK_AGENTS.filter(a => a.installed));
}

export async function installAgent(id: string): Promise<{ status: string }> {
  return apiFetch(`/api/v1/agents/import`, { method: "POST", body: JSON.stringify({ id }) }, { status: "installed" });
}

export async function exportAgent(name: string): Promise<{ status: string; url: string }> {
  return apiFetch(`/api/v1/agents/export`, { method: "POST", body: JSON.stringify({ name }) }, { status: "exported", url: `/downloads/${name}.fireside` });
}

export async function publishAgent(data: { name: string; version: string; description: string; category: string; price: number }): Promise<{ status: string }> {
  return apiFetch("/api/v1/marketplace/publish", { method: "POST", body: JSON.stringify(data) }, { status: "submitted_for_review" });
}

export async function reviewAgent(id: string, review: { rating: number; text: string }): Promise<{ status: string }> {
  return apiFetch(`/api/v1/marketplace/${id}/review`, { method: "POST", body: JSON.stringify(review) }, { status: "review_added" });
}

// ═══════════════════════════════════════════════
// BACKEND INFRASTRUCTURE — Onboarding + Chat
// ═══════════════════════════════════════════════

// ─── Onboarding Types ───

export interface OnboardStep {
  step: number;
  name: string;
  status: "done" | "already_installed" | "skipped" | "error";
  error?: string;
  detail?: string;
  vram_gb?: number;
  runtime?: string;
  path?: string;
  port?: number;
  pid?: number;
  installed?: string[];
  attempts?: number;
}

export interface OnboardResult {
  ok: boolean;
  model_id: string;
  runtime: string;
  steps: OnboardStep[];
}

// ─── Chat Types ───

export interface ChatMessage {
  id: string;
  session_id: string;
  role: string;
  content: string;
  timestamp: number;
  metadata?: Record<string, unknown>;
}

export interface ChatSession {
  session_id: string;
  message_count: number;
  first_message: number;
  last_message: number;
}

// ─── Onboarding API ───

export async function onboardBrain(modelId: string, port: number = 8080): Promise<OnboardResult> {
  return apiFetch("/api/v1/brains/onboard", {
    method: "POST",
    body: JSON.stringify({ model_id: modelId, port }),
  }, {
    ok: false,
    model_id: modelId,
    runtime: "unknown",
    steps: [],
  });
}

// ─── Chat Persistence API ───

export async function saveChatMessage(
  sessionId: string,
  role: string,
  content: string,
  metadata?: Record<string, unknown>,
): Promise<{ ok: boolean; message: ChatMessage; total: number }> {
  return apiFetch("/api/v1/chat/history", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId, role, content, metadata }),
  }, { ok: false, message: {} as ChatMessage, total: 0 });
}

export async function getChatHistory(
  sessionId: string = "",
  limit: number = 100,
  offset: number = 0,
): Promise<{ ok: boolean; messages: ChatMessage[]; count: number; total: number }> {
  const params = new URLSearchParams();
  if (sessionId) params.set("session_id", sessionId);
  params.set("limit", String(limit));
  params.set("offset", String(offset));
  return apiFetch(`/api/v1/chat/history?${params}`, undefined, {
    ok: true, messages: [], count: 0, total: 0,
  });
}

export async function getChatSessions(limit: number = 50): Promise<{ ok: boolean; sessions: ChatSession[]; count: number }> {
  return apiFetch(`/api/v1/chat/sessions?limit=${limit}`, undefined, {
    ok: true, sessions: [], count: 0,
  });
}

export async function deleteChatSession(sessionId: string): Promise<{ ok: boolean; deleted: number }> {
  return apiFetch(`/api/v1/chat/history/${sessionId}`, { method: "DELETE" }, { ok: false, deleted: 0 });
}

// ─── Working Memory Search ───

export async function searchMemory(query: string, topK: number = 5): Promise<{ results: unknown[]; count: number; backend: string }> {
  return apiFetch("/api/v1/working-memory/search", {
    method: "POST",
    body: JSON.stringify({ query, top_k: topK }),
  }, { results: [], count: 0, backend: "offline" });
}
