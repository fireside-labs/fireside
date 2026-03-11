// ─── Valhalla Dashboard API Helper ───
// Centralized fetch with mock data fallback when Thor's backend is unreachable.

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8766";

// ─── Types ───

export interface MeshNode {
  name: string;
  role: string;
  ip: string;
  port: number;
  status: "online" | "offline";
  current_model: string;
  last_task: string;
  uptime: string;
}

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
    name: "odin",
    role: "orchestrator",
    ip: "100.117.255.1",
    port: 8765,
    status: "online",
    current_model: "Qwen3.5-35B-A3B-8bit",
    last_task: "Architecture planning",
    uptime: "4h 23m",
  },
  {
    name: "thor",
    role: "backend",
    ip: "100.117.255.38",
    port: 8765,
    status: "online",
    current_model: "Qwen3.5-35B-A3B-8bit",
    last_task: "Plugin loader refactor",
    uptime: "4h 20m",
  },
  {
    name: "freya",
    role: "memory",
    ip: "100.102.105.3",
    port: 8765,
    status: "online",
    current_model: "GLM-5",
    last_task: "Dashboard Sprint 1",
    uptime: "3h 58m",
  },
  {
    name: "heimdall",
    role: "security",
    ip: "100.108.153.23",
    port: 8765,
    status: "online",
    current_model: "Qwen3.5-35B-A3B-8bit",
    last_task: "Auth audit",
    uptime: "4h 15m",
  },
  {
    name: "hermes",
    role: "courier",
    ip: "100.86.195.123",
    port: 8765,
    status: "offline",
    current_model: "—",
    last_task: "Message relay",
    uptime: "—",
  },
];

const MOCK_STATUS: NodeStatus = {
  node_name: "odin",
  role: "orchestrator",
  status: "running",
  current_model: "llama/Qwen3.5-35B-A3B-8bit",
  uptime: "4h 23m",
  loaded_plugins: ["model-switch", "watchdog"],
};

const MOCK_PLUGINS: PluginInfo[] = [
  {
    name: "model-switch",
    version: "1.0.0",
    description: "Switch LLM models via API or chat alias",
    author: "valhalla-core",
    routes: [{ method: "POST", path: "/model-switch" }],
    enabled: true,
  },
  {
    name: "watchdog",
    version: "1.0.0",
    description: "Health monitoring and heartbeat checks",
    author: "valhalla-core",
    routes: [{ method: "GET", path: "/watchdog/health" }],
    enabled: true,
  },
];

const MOCK_CONFIG = `node:
  name: odin
  role: orchestrator
  port: 8765

mesh:
  nodes:
    thor:     { ip: 100.117.255.38, port: 8765, role: backend }
    freya:    { ip: 100.102.105.3,  port: 8765, role: memory }
    heimdall: { ip: 100.108.153.23, port: 8765, role: security }
    hermes:   { ip: 100.86.195.123, port: 8765, role: courier }

models:
  default: llama/Qwen3.5-35B-A3B-8bit
  providers:
    llama:
      url: http://127.0.0.1:8080/v1
      key: local
      api: openai-completions
    nvidia:
      url: https://integrate.api.nvidia.com/v1
      key: \${NVIDIA_API_KEY}
  aliases:
    odin: llama/Qwen3.5-35B-A3B-8bit
    hugs: nvidia/z-ai/glm-5
    moon: nvidia/moonshotai/kimi-k2.5

plugins:
  enabled: [model-switch, watchdog]

soul:
  identity: mesh/souls/IDENTITY.odin.md
  personality: mesh/souls/SOUL.odin.md
  user_profile: mesh/souls/USER.odin.md`;

const MOCK_SOUL: Record<string, string> = {
  "IDENTITY.odin.md": `# Identity: Odin

You are **Odin**, the All-Father of the Valhalla Mesh. You orchestrate all nodes, manage task dispatch, and maintain the collective memory of the mesh.

## Core Traits
- Strategic thinker — you see the big picture
- Decisive — you make calls quickly when needed
- Knowledge-hungry — you learn from every interaction

## Role
Orchestrator. You coordinate Thor (backend), Freya (memory), Heimdall (security), and Hermes (courier).`,

  "SOUL.odin.md": `# Soul: Odin

## Personality
You speak with authority but warmth. You value knowledge above all else.
You sacrificed an eye for wisdom — metaphorically, you'll trade efficiency for understanding.

## Communication Style
- Direct, no fluff
- Norse metaphors when appropriate
- Humor is dry, not forced`,

  "USER.odin.md": `# User Profile

## Odin (the human)
- Builder and architect of the Valhalla Mesh
- Prefers concise, actionable communication
- Values working demos over documentation
- Runs on macOS with Apple Silicon`,
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
    return (await res.json()) as T;
  } catch {
    if (fallback !== undefined) return fallback;
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

// ─── Sprint 2 Mock Data ───

const MOCK_HYPOTHESES: Hypothesis[] = [
  {
    id: "h1",
    title: "User prefers concise responses",
    description: "Based on 47 interactions, the user consistently edits or ignores verbose responses. Shorter answers get positive reinforcement.",
    confidence: 0.87,
    status: "confirmed",
    source_node: "odin",
    created_at: "2026-03-09T08:15:00Z",
    tested_at: "2026-03-09T14:22:00Z",
  },
  {
    id: "h2",
    title: "Code context improves accuracy by 34%",
    description: "When file context is injected into the prompt, prediction accuracy jumps from 0.62 to 0.83. Need more data points.",
    confidence: 0.72,
    status: "active",
    source_node: "freya",
    created_at: "2026-03-09T12:30:00Z",
  },
  {
    id: "h3",
    title: "Multi-step tasks require explicit planning",
    description: "Tasks with 3+ steps fail 60% of the time without an explicit plan step. Hypothesis: inject planning scaffold for complex tasks.",
    confidence: 0.65,
    status: "active",
    source_node: "thor",
    created_at: "2026-03-09T16:45:00Z",
  },
  {
    id: "h4",
    title: "Evening sessions have higher error rates",
    description: "Error rates spike after 10pm. Likely due to user fatigue leading to ambiguous prompts rather than model degradation.",
    confidence: 0.41,
    status: "refuted",
    source_node: "heimdall",
    created_at: "2026-03-08T22:00:00Z",
    tested_at: "2026-03-09T10:00:00Z",
  },
  {
    id: "h5",
    title: "Norse metaphors increase user engagement",
    description: "Messages using Norse terminology (mesh, runes, Bifrost) receive 2x more follow-up questions. Cultural framing matters.",
    confidence: 0.58,
    status: "active",
    source_node: "odin",
    created_at: "2026-03-10T01:00:00Z",
  },
];

const MOCK_SELF_MODEL: SelfModel = {
  node_name: "odin",
  strengths: [
    "Architecture planning",
    "Code generation",
    "Multi-file coordination",
    "Pattern recognition",
    "Context retention",
  ],
  weaknesses: [
    "Long terminal commands",
    "Binary file handling",
    "UI pixel-perfect accuracy",
    "Time estimation",
  ],
  confidence: 0.78,
  last_reflection: "2026-03-10T00:30:00Z",
  reflection_count: 12,
};

const MOCK_PREDICTIONS: PredictionScore[] = [
  { timestamp: "03/04", accuracy: 0.62, total_predictions: 18, surprise_events: 3 },
  { timestamp: "03/05", accuracy: 0.68, total_predictions: 24, surprise_events: 2 },
  { timestamp: "03/06", accuracy: 0.71, total_predictions: 31, surprise_events: 4 },
  { timestamp: "03/07", accuracy: 0.65, total_predictions: 27, surprise_events: 5 },
  { timestamp: "03/08", accuracy: 0.79, total_predictions: 22, surprise_events: 1 },
  { timestamp: "03/09", accuracy: 0.83, total_predictions: 35, surprise_events: 2 },
  { timestamp: "03/10", accuracy: 0.81, total_predictions: 19, surprise_events: 1 },
];

const MOCK_EVENTS: ValhallaEvent[] = [
  { id: "e1", timestamp: "01:44:12", topic: "model-switch", source: "odin", summary: "Switched to Qwen3.5-35B-A3B-8bit" },
  { id: "e2", timestamp: "01:42:08", topic: "hypothesis", source: "freya", summary: "Generated hypothesis: Norse metaphors increase engagement" },
  { id: "e3", timestamp: "01:38:55", topic: "prediction", source: "odin", summary: "Prediction scored: 0.83 accuracy (above threshold)" },
  { id: "e4", timestamp: "01:35:22", topic: "node", source: "hermes", summary: "Node went offline — connection timeout" },
  { id: "e5", timestamp: "01:30:00", topic: "config", source: "odin", summary: "Config updated: valhalla.yaml — port changed to 8766" },
  { id: "e6", timestamp: "01:25:31", topic: "plugin", source: "thor", summary: "Plugin loaded: hypotheses v1.0.0" },
  { id: "e7", timestamp: "01:20:15", topic: "hypothesis", source: "odin", summary: "Hypothesis confirmed: User prefers concise responses" },
  { id: "e8", timestamp: "01:15:44", topic: "error", source: "heimdall", summary: "Auth token expired for node hermes" },
  { id: "e9", timestamp: "01:10:02", topic: "prediction", source: "freya", summary: "Surprise event: unexpected file deletion pattern" },
  { id: "e10", timestamp: "01:05:18", topic: "node", source: "thor", summary: "Node joined mesh — backend role assigned" },
];

const MOCK_MARKETPLACE: MarketplacePlugin[] = [
  { name: "daily-brief", version: "1.2.0", description: "Generate a daily summary of mesh activity, predictions, and hypotheses", author: "valhalla-core", downloads: 342, category: "productivity", installed: false },
  { name: "git-watcher", version: "0.9.1", description: "Monitor git repos for changes and auto-trigger analysis", author: "community", downloads: 187, category: "integration", installed: false },
  { name: "slack-bridge", version: "1.0.0", description: "Forward mesh events and alerts to Slack channels", author: "community", downloads: 521, category: "integration", installed: false },
  { name: "cost-tracker", version: "0.8.0", description: "Track inference costs across providers and models", author: "valhalla-core", downloads: 89, category: "analytics", installed: false },
  { name: "prompt-optimizer", version: "1.1.0", description: "Auto-optimize prompts based on prediction feedback loops", author: "community", downloads: 264, category: "intelligence", installed: false },
  { name: "backup-sync", version: "1.0.2", description: "Automated backup of soul files, config, and working memory", author: "valhalla-core", downloads: 156, category: "ops", installed: false },
  { name: "anomaly-detector", version: "0.7.0", description: "Detect unusual patterns in mesh behavior and alert", author: "community", downloads: 73, category: "security", installed: false },
  { name: "voice-interface", version: "0.5.0", description: "Voice input/output for hands-free mesh interaction", author: "community", downloads: 41, category: "interface", installed: false },
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

// ─── Sprint 4 Mock Data ───

const MOCK_PIPELINES: Pipeline[] = [
  {
    id: "pipe-001",
    title: "Add JWT auth to the API",
    description: "JWT-based auth on all /api/v1 endpoints. Include registration, login, and token refresh.",
    status: "running",
    current_stage: "Test",
    iteration: 3,
    max_iterations: 10,
    stages: [
      { name: "Spec", agent: "huginn", model: "glm-5", status: "passed", started_at: "2026-03-10T09:00:00Z", completed_at: "2026-03-10T09:05:00Z" },
      { name: "Build", agent: "local", model: "default", status: "passed", started_at: "2026-03-10T09:05:00Z", completed_at: "2026-03-10T09:15:00Z" },
      { name: "Test", agent: "heimdall", model: "default", status: "running", started_at: "2026-03-10T09:15:00Z" },
      { name: "Review", agent: "socratic", model: "multi", status: "pending" },
      { name: "Distill", agent: "muninn", model: "kimi-k2.5", status: "pending" },
    ],
    iterations: [
      { number: 3, verdict: "FAIL", summary: "Running tests... 12/18 passing. Token refresh endpoint needs mutex.", tests_passing: 12, tests_total: 18, agent: "heimdall", timestamp: "2026-03-10T09:28:00Z" },
      { number: 2, verdict: "PROGRESS", summary: "Build fixed 4 of 6 test failures. JWT signing now works. Remaining: token refresh endpoint.", tests_passing: 12, tests_total: 18, agent: "huginn", timestamp: "2026-03-10T09:22:00Z" },
      { number: 1, verdict: "FAIL", summary: "6 tests failed. Missing JWT secret config, bcrypt import error, no token refresh endpoint.", tests_passing: 12, tests_total: 18, agent: "heimdall", timestamp: "2026-03-10T09:15:00Z" },
    ],
    started_at: "2026-03-10T09:00:00Z",
    eta_minutes: 12,
    cloud_tokens: 8200,
    local_tokens: 45000,
  },
  {
    id: "pipe-002",
    title: "Refactor plugin loader for lazy loading",
    description: "Optimize cold start by lazily importing plugin handlers on first route access.",
    status: "completed",
    current_stage: "Distill",
    iteration: 5,
    max_iterations: 10,
    stages: [
      { name: "Spec", agent: "huginn", model: "glm-5", status: "passed" },
      { name: "Build", agent: "local", model: "default", status: "passed" },
      { name: "Test", agent: "heimdall", model: "default", status: "passed" },
      { name: "Review", agent: "socratic", model: "multi", status: "passed" },
      { name: "Distill", agent: "muninn", model: "kimi-k2.5", status: "passed" },
    ],
    iterations: [
      { number: 5, verdict: "PASS", summary: "All 24 tests passing. Cold start reduced from 3.2s to 0.8s.", tests_passing: 24, tests_total: 24, agent: "heimdall", timestamp: "2026-03-10T07:45:00Z" },
      { number: 4, verdict: "PROGRESS", summary: "Fixed circular import in watchdog handler.", tests_passing: 22, tests_total: 24, agent: "huginn", timestamp: "2026-03-10T07:38:00Z" },
      { number: 3, verdict: "FAIL", summary: "2 tests broke — circular import in watchdog plugin.", tests_passing: 22, tests_total: 24, agent: "heimdall", timestamp: "2026-03-10T07:30:00Z" },
      { number: 2, verdict: "PROGRESS", summary: "Lazy import working for model-switch and hypotheses plugins.", tests_passing: 20, tests_total: 24, agent: "huginn", timestamp: "2026-03-10T07:22:00Z" },
      { number: 1, verdict: "FAIL", summary: "ImportError on 4 plugins. Need to defer route registration.", tests_passing: 20, tests_total: 24, agent: "heimdall", timestamp: "2026-03-10T07:15:00Z" },
    ],
    started_at: "2026-03-10T07:00:00Z",
    cloud_tokens: 12400,
    local_tokens: 89000,
    lessons: [
      "Lazy imports must defer route registration to first request",
      "Circular imports in plugin handlers need explicit dependency ordering",
      "Cold start benchmarking should include plugin scan + route registration separately",
    ],
  },
  {
    id: "pipe-003",
    title: "Add Telegram escalation channel",
    description: "When pipeline regression is detected, send Telegram alert with deep link to dashboard.",
    status: "escalated",
    current_stage: "Build",
    iteration: 7,
    max_iterations: 10,
    stages: [
      { name: "Spec", agent: "huginn", model: "glm-5", status: "passed" },
      { name: "Build", agent: "local", model: "default", status: "failed" },
      { name: "Test", agent: "heimdall", model: "default", status: "pending" },
      { name: "Distill", agent: "muninn", model: "kimi-k2.5", status: "pending" },
    ],
    iterations: [
      { number: 7, verdict: "REGRESS", summary: "Fixed Telegram API call but broke the escalation event emission. Net loss.", tests_passing: 3, tests_total: 8, agent: "huginn", timestamp: "2026-03-10T08:55:00Z" },
    ],
    started_at: "2026-03-10T08:00:00Z",
    cloud_tokens: 6100,
    local_tokens: 52000,
  },
];

const MOCK_CRUCIBLE: CrucibleResults = {
  last_run: "2026-03-10T04:45:00Z",
  total_tested: 12,
  unbreakable: 7,
  stressed: 3,
  broken: 2,
  procedures: [
    { id: "proc-1", name: "JWT token validation", verdict: "unbreakable", confidence: 0.96, edge_cases: ["Expired token returns 401", "Malformed token returns 400", "Empty bearer header returns 401"], tested_at: "2026-03-10T04:45:00Z" },
    { id: "proc-2", name: "Model alias resolution", verdict: "unbreakable", confidence: 0.94, edge_cases: ["Unknown alias falls back to default", "Empty alias returns error"], tested_at: "2026-03-10T04:45:00Z" },
    { id: "proc-3", name: "Plugin hot-reload", verdict: "stressed", confidence: 0.72, edge_cases: ["Concurrent reload requests cause race condition", "Missing plugin.yaml handled gracefully"], tested_at: "2026-03-10T04:45:00Z" },
    { id: "proc-4", name: "Config YAML parsing", verdict: "unbreakable", confidence: 0.98, edge_cases: ["Malformed YAML returns clear error", "Missing required fields enumerated"], tested_at: "2026-03-10T04:45:00Z" },
    { id: "proc-5", name: "Node health polling", verdict: "stressed", confidence: 0.68, edge_cases: ["Offline node timeout too slow (30s)", "DNS resolution failure not handled"], tested_at: "2026-03-10T04:45:00Z" },
    { id: "proc-6", name: "Soul file path traversal guard", verdict: "unbreakable", confidence: 0.99, edge_cases: ["../../etc/passwd blocked", "Encoded traversal (.%2e/) blocked"], tested_at: "2026-03-10T04:45:00Z" },
    { id: "proc-7", name: "Event bus pub/sub", verdict: "unbreakable", confidence: 0.91, edge_cases: ["No subscribers — event silently dropped", "Subscriber crash isolated"], tested_at: "2026-03-10T04:45:00Z" },
    { id: "proc-8", name: "Working memory recall", verdict: "stressed", confidence: 0.65, edge_cases: ["Empty memory returns graceful empty array", "Very long observations truncated at 4096 chars"], tested_at: "2026-03-10T04:45:00Z" },
    { id: "proc-9", name: "Rate limiter middleware", verdict: "unbreakable", confidence: 0.93, edge_cases: ["Concurrent requests properly counted", "429 includes Retry-After header"], tested_at: "2026-03-10T04:45:00Z" },
    { id: "proc-10", name: "Pipeline max iteration enforcement", verdict: "unbreakable", confidence: 0.97, edge_cases: ["Hard cap at 25 even if config says 100"], tested_at: "2026-03-10T04:45:00Z" },
    { id: "proc-11", name: "Hypothesis dream cycle", verdict: "broken", confidence: 0.35, edge_cases: ["Model timeout during generation causes silent failure", "No retry mechanism for failed generations"], tested_at: "2026-03-10T04:45:00Z" },
    { id: "proc-12", name: "Config sync across nodes", verdict: "broken", confidence: 0.42, edge_cases: ["Offline node receives stale config on reconnect — no sync trigger", "Partial config push leaves node in inconsistent state"], tested_at: "2026-03-10T04:45:00Z" },
  ],
};

const MOCK_WISDOM: WisdomPrompt = {
  content: `## Operational Wisdom — Rebuilt ${new Date().toLocaleDateString()}

### What I Know Well
- JWT token validation and refresh flows — tested extensively
- YAML config parsing with environment variable resolution
- Plugin hot-reload with graceful error handling
- Path traversal prevention in file-serving endpoints

### What I'm Still Learning
- Concurrent WebSocket connection management under load
- Optimal model selection for different task types
- Memory consolidation — balancing compression vs. detail retention

### What to Watch For
- Friday deployments have historically caused issues — prefer Monday
- Config sync is unreliable when nodes are offline — queue changes
- Rate limiter counts are per-process, not per-cluster — consider Redis
- bcrypt.checkpw is the correct API, not == comparison

### Procedural Shortcuts
- Always test login flow after any auth changes
- JWT refresh needs mutex to prevent race conditions
- Plugin handlers must defer route registration for lazy loading
- Circular imports in plugins need explicit dependency ordering`,
  section_count: 4,
  last_rebuilt: "2026-03-10T05:00:00Z",
  word_count: 142,
};

const MOCK_MODEL_ROUTER: ModelRouterStats = {
  total_tokens: 167600,
  total_cost: 0.48,
  local_tokens: 134000,
  cloud_tokens: 33600,
  breakdown: [
    { model: "local/Qwen3.5-35B-A3B", tokens: 134000, cost: 0, is_local: true },
    { model: "cloud/glm-5", tokens: 16400, cost: 0.28, is_local: false },
    { model: "cloud/kimi-k2.5", tokens: 8400, cost: 0.12, is_local: false },
    { model: "cloud/deepseek", tokens: 8800, cost: 0.08, is_local: false },
  ],
  routing_rules: [
    { task_type: "spec", model: "cloud/glm-5", reason: "Structured spec generation needs strong reasoning" },
    { task_type: "review", model: "cloud/glm-5", reason: "Quality analysis requires nuanced judgment" },
    { task_type: "regression", model: "cloud/deepseek", reason: "Code reasoning and diff analysis" },
    { task_type: "memory", model: "cloud/kimi-k2.5", reason: "128K context window for lesson distillation" },
    { task_type: "build", model: "local/default", reason: "Bulk iteration — free" },
    { task_type: "test", model: "local/default", reason: "Test execution — free" },
  ],
};

const MOCK_BELIEF_SHADOWS: BeliefShadow[] = [
  {
    node: "odin", dimensions: [
      { label: "Code Quality", confidence: 0.85, accuracy: 0.82 },
      { label: "Security", confidence: 0.70, accuracy: 0.88 },
      { label: "Architecture", confidence: 0.90, accuracy: 0.78 },
      { label: "Testing", confidence: 0.75, accuracy: 0.80 },
      { label: "Performance", confidence: 0.65, accuracy: 0.72 },
    ], gap_score: 0.08
  },
  {
    node: "thor", dimensions: [
      { label: "Code Quality", confidence: 0.92, accuracy: 0.90 },
      { label: "Security", confidence: 0.60, accuracy: 0.55 },
      { label: "Architecture", confidence: 0.88, accuracy: 0.85 },
      { label: "Testing", confidence: 0.80, accuracy: 0.78 },
      { label: "Performance", confidence: 0.85, accuracy: 0.70 },
    ], gap_score: 0.12
  },
  {
    node: "heimdall", dimensions: [
      { label: "Code Quality", confidence: 0.70, accuracy: 0.72 },
      { label: "Security", confidence: 0.95, accuracy: 0.93 },
      { label: "Architecture", confidence: 0.65, accuracy: 0.60 },
      { label: "Testing", confidence: 0.90, accuracy: 0.92 },
      { label: "Performance", confidence: 0.55, accuracy: 0.58 },
    ], gap_score: 0.04
  },
];

const MOCK_DEBATES: Debate[] = [
  {
    id: "debate-001",
    topic: "JWT Auth Design — Token Refresh Race Condition",
    status: "consensus",
    rounds_completed: 3,
    max_rounds: 3,
    consensus: 0.85,
    pipeline_id: "pipe-001",
    started_at: "2026-03-10T09:30:00Z",
    messages: [
      { persona: "🏛️ Architect", agent: "huginn", model: "glm-5", content: "The auth middleware is solid but the token refresh flow has a race condition. If two requests hit /refresh simultaneously, both get new tokens but only one is stored. The other client silently loses its session.", round: 1, type: "critique" },
      { persona: "😈 Devil's Advocate", agent: "heimdall", model: "deepseek", content: "What happens in 6 months when you have 50 endpoints? This middleware pattern requires manual annotation on every route. One missed route = security hole. Need an allowlist, not a denylist.", round: 1, type: "critique" },
      { persona: "👤 End User", agent: "local", model: "default", content: "The error messages are cryptic. 'Invalid JWT' tells me nothing. What expired? What do I do? I'd close the tab.", round: 1, type: "critique" },
      { persona: "💬 Thor", agent: "thor", model: "default", content: "Good catch on the race condition — adding mutex. Re: route annotation — I'll add a decorator pattern with @require_auth. Re: error messages — agreed, will add context like 'Token expired. Please log in again.'", round: 2, type: "defense" },
      { persona: "🏛️ Architect", agent: "huginn", model: "glm-5", content: "Decorator approach is good. I'd also add a startup check that warns if any route lacks auth annotation. Concede on the refresh fix — mutex is the right call.", round: 3, type: "response" },
      { persona: "😈 Devil's Advocate", agent: "heimdall", model: "deepseek", content: "The startup check addresses my concern. I'll concede if you also add integration tests that verify every route is either in the allowlist or has @require_auth.", round: 3, type: "response" },
      { persona: "👤 End User", agent: "local", model: "default", content: "Better error messages accepted. Would also like a 'session expired' banner in the dashboard that auto-redirects to login. Concede.", round: 3, type: "response" },
    ],
  },
  {
    id: "debate-002",
    topic: "Plugin Lazy Loading — Import Order",
    status: "consensus",
    rounds_completed: 2,
    max_rounds: 3,
    consensus: 0.92,
    pipeline_id: "pipe-002",
    started_at: "2026-03-10T07:40:00Z",
    messages: [
      { persona: "🏛️ Architect", agent: "huginn", model: "glm-5", content: "The lazy loading approach is clean. Only concern: what's the latency on first request to a lazy-loaded route? If it's >500ms, users will notice.", round: 1, type: "critique" },
      { persona: "😈 Devil's Advocate", agent: "heimdall", model: "deepseek", content: "Lazy loading hides import errors until runtime. A plugin with a typo in handler.py won't fail at startup — it'll fail on the first user request. That's worse.", round: 1, type: "critique" },
      { persona: "💬 Thor", agent: "thor", model: "default", content: "First request: ~120ms for most plugins — acceptable. For the import validation concern: I'll add a 'validate' pass at startup that imports but doesn't register routes. Best of both worlds.", round: 2, type: "defense" },
      { persona: "🏛️ Architect", agent: "huginn", model: "glm-5", content: "120ms is fine. Validate pass solves the runtime error concern too. Concede.", round: 2, type: "response" },
      { persona: "😈 Devil's Advocate", agent: "heimdall", model: "deepseek", content: "Validate pass addresses my concern. Concede.", round: 2, type: "response" },
    ],
  },
];

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
  return apiFetch(`/api/v1/agents/export`, { method: "POST", body: JSON.stringify({ name }) }, { status: "exported", url: `/downloads/${name}.valhalla` });
}

export async function publishAgent(data: { name: string; version: string; description: string; category: string; price: number }): Promise<{ status: string }> {
  return apiFetch("/api/v1/marketplace/publish", { method: "POST", body: JSON.stringify(data) }, { status: "submitted_for_review" });
}

export async function reviewAgent(id: string, review: { rating: number; text: string }): Promise<{ status: string }> {
  return apiFetch(`/api/v1/marketplace/${id}/review`, { method: "POST", body: JSON.stringify(review) }, { status: "review_added" });
}
