"use client";

import { useState, useEffect, useRef, useMemo } from "react";
import { API_BASE } from "../lib/api";
import Link from "next/link";
import EmberParticles from "@/components/EmberParticles";
import { playWhoosh, playTick } from "@/components/FiresideSounds";
import { DiscoveryCard } from "@/components/GuidedTour";

/* ═══════════════════════════════════════════════════════════════════
   Fireside — Hub + Chat
   Split layout hub (campfire scene left, 3 nav cards right)
   Transitions to premium chat view with conversation sidebar
   ═══════════════════════════════════════════════════════════════════ */

const GREETINGS = [
  "What shall we work on today?",
  "Ready when you are!",
  "The fire's warm tonight...",
  "Got any questions for me?",
  "Pull up a log and let's chat!",
];

// Mock conversation history for the sidebar
interface Conversation {
  id: string;
  title: string;
  preview: string;
  date: Date;
  folder?: string;
  pinned?: boolean;
}

const MOCK_CONVERSATIONS: Conversation[] = [
  { id: "1", title: "Analytics Report Progress", preview: "Let's continue with the competitor analysis...", date: new Date("2026-03-17T09:14:00"), pinned: true },
  { id: "2", title: "Pricing Strategy Brainstorm", preview: "I think the three-tier model works best because...", date: new Date("2026-03-16T15:30:00") },
  { id: "3", title: "Product Launch Checklist", preview: "Here's what we still need to prepare...", date: new Date("2026-03-16T10:00:00") },
  { id: "4", title: "Code Review: API Routes", preview: "The middleware chain looks solid, but...", date: new Date("2026-03-15T18:45:00"), folder: "Dev" },
  { id: "5", title: "Morning Brief — March 15", preview: "Good morning! Here's what happened overnight...", date: new Date("2026-03-15T09:00:00") },
  { id: "6", title: "Model Comparison Notes", preview: "Qwen 2.5 14B vs Llama 3.1 8B for our use case...", date: new Date("2026-03-14T14:20:00"), folder: "Dev" },
  { id: "7", title: "Weekend Planning", preview: "I can help organize your tasks for the weekend...", date: new Date("2026-03-14T09:00:00") },
];

export default function CampfireHub() {
  const [message, setMessage] = useState("");
  const [userName, setUserName] = useState("");
  const [agentName, setAgentName] = useState("Atlas");
  const [species, setSpecies] = useState("fox");
  const [companionName, setCompanionName] = useState("");
  const [brainLabel, setBrainLabel] = useState("");
  const [brainQuant, setBrainQuant] = useState("");
  const mascotSrc = `/hub/mascot_${species}.png`;
  const [chatHistory, setChatHistory] = useState<{ role: string; content: string; memory?: string; skills?: string[]; ts?: Date }[]>(() => {
    if (typeof window === "undefined") return [];
    try {
      const saved = sessionStorage.getItem("fireside_chat_session");
      return saved ? JSON.parse(saved) : [];
    } catch { return []; }
  });
  const [hasBrain, setHasBrain] = useState(true);
  const [isTyping, setIsTyping] = useState(false);
  const [thinkingEnabled, setThinkingEnabled] = useState(true);
  const [activeView, setActiveView] = useState<"hub" | "chat">("hub");
  const [greeting] = useState(() => GREETINGS[Math.floor(Math.random() * GREETINGS.length)]);

  // Persist chat history to sessionStorage on every change
  useEffect(() => {
    if (chatHistory.length > 0) {
      sessionStorage.setItem("fireside_chat_session", JSON.stringify(chatHistory));
    }
  }, [chatHistory]);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [activeConvo, setActiveConvo] = useState<string | null>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const name = localStorage.getItem("fireside_user_name") || "";
    const agent = localStorage.getItem("fireside_agent_name") || "Atlas";
    setUserName(name);
    setAgentName(agent);
    try {
      const stored = localStorage.getItem("fireside_companion");
      if (stored) {
        const c = JSON.parse(stored);
        setSpecies(c.species || "fox");
        setCompanionName(c.name || "");
      }
    } catch { /* no companion yet */ }
    const model = localStorage.getItem("fireside_model");
    setHasBrain(!!model);
    setBrainLabel(localStorage.getItem("fireside_brain_label") || localStorage.getItem("fireside_model") || "");
    setBrainQuant(localStorage.getItem("fireside_brain_quant") || "");
    // Global thinking mode setting
    const thinking = localStorage.getItem("fireside_thinking_enabled");
    if (thinking !== null) setThinkingEnabled(thinking === "true");
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatHistory]);

  // ═══ Smart Chat Compaction ═══
  const estimateTokens = (text: string) => Math.ceil(text.length / 4);

  const getContextLimit = () => {
    const ctx = parseInt(localStorage.getItem("fireside_ctx_size") || "8192");
    return Math.floor(ctx * 0.6); // compact at 60% of context
  };

  const getResponseLimit = () => {
    const preset = localStorage.getItem("fireside_response_length") || "normal";
    const limits: Record<string, number | undefined> = {
      short: 256, normal: 1024, long: 4096, unlimited: undefined,
    };
    return limits[preset];
  };

  const saveMemory = (summary: string) => {
    try {
      const memories = JSON.parse(localStorage.getItem("fireside_memories") || "[]");
      memories.push({ summary, timestamp: new Date().toISOString() });
      // Keep last 50 memories
      if (memories.length > 50) memories.splice(0, memories.length - 50);
      localStorage.setItem("fireside_memories", JSON.stringify(memories));
    } catch { /* ignore */ }
  };

  const recallMemories = (currentMessage: string): string => {
    try {
      const memories = JSON.parse(localStorage.getItem("fireside_memories") || "[]");
      if (memories.length === 0) return "";
      // Simple keyword matching — find memories relevant to current message
      const words = currentMessage.toLowerCase().split(/\s+/).filter(w => w.length > 3);
      const relevant = memories.filter((m: { summary: string }) =>
        words.some(w => m.summary.toLowerCase().includes(w))
      ).slice(-3); // max 3 recalled memories
      if (relevant.length === 0) {
        // If no keyword match, return the most recent memory for continuity
        const recent = memories.slice(-1);
        return recent.map((m: { summary: string }) => m.summary).join(" | ");
      }
      return relevant.map((m: { summary: string }) => m.summary).join(" | ");
    } catch { return ""; }
  };

  const compactHistory = async (history: typeof chatHistory): Promise<typeof chatHistory> => {
    const totalTokens = history.reduce((sum, m) => sum + estimateTokens(m.content), 0);
    const limit = getContextLimit();

    if (totalTokens <= limit || history.length <= 4) return history;

    // Split: keep the last 4 messages, summarize the rest
    const toSummarize = history.slice(0, -4);
    const toKeep = history.slice(-4);

    const convoText = toSummarize.map(m => `${m.role}: ${m.content}`).join("\n");

    try {
      const res = await fetch("http://127.0.0.1:8080/v1/chat/completions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: "local",
          messages: [
            { role: "system", content: "Summarize this conversation in 2-3 sentences. Focus on decisions made, key facts, and what the user wants. Be concise." },
            { role: "user", content: convoText },
          ],
          temperature: 0.3,
          max_tokens: 256,
        }),
      });
      if (!res.ok) return history; // fallback: don't compact
      const data = await res.json();
      const summary = data.choices?.[0]?.message?.content || "";
      if (!summary) return history;

      // Save to long-term memory
      saveMemory(summary);

      // Replace old messages with a summary message
      return [
        { role: "system" as const, content: `[Previous conversation summary] ${summary}`, ts: new Date() },
        ...toKeep,
      ];
    } catch {
      return history; // Network error — don't compact
    }
  };

  const displayName = companionName || agentName;

  const handleSend = async () => {
    if (!message.trim()) return;
    const userMessage = message.trim();
    setChatHistory(prev => [...prev, { role: "user", content: userMessage, ts: new Date() }]);
    setMessage("");
    setIsTyping(true);

    if (activeView !== "chat") {
      setActiveView("chat");
      playWhoosh();
    }

    try {
      // Try Python backend first (port 8765)
      let responseText = "";

      // Recall relevant memories
      const recalled = recallMemories(userMessage);
      const memoryContext = recalled ? `\n\n[Remembered from past conversations] ${recalled}` : "";
      const maxTokens = getResponseLimit();

      try {
        const res = await fetch(`${API_BASE}/api/v1/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: userMessage, stream: false }),
        });
        if (!res.ok) throw new Error(`API error: ${res.status}`);
        const data = await res.json();
        responseText = data.response || data.content || "";
      } catch {
        // Fallback: try llama-server directly (port 8080, OpenAI-compatible)
        try {
          // Build system prompt — use personality from localStorage if available
          const soulIdentity = typeof window !== "undefined" ? localStorage.getItem("fireside_soul_identity") : null;
          const systemPrompt = soulIdentity
            ? `${soulIdentity}\n\nYour name is ${displayName}.${memoryContext}`
            : `You are a helpful AI companion named ${displayName}. Be friendly, concise, and helpful.${memoryContext}`;
          const thinkingEnabled = typeof window !== "undefined" ? localStorage.getItem("fireside_thinking_enabled") !== "false" : true;
          const payload: Record<string, unknown> = {
            model: "local",
            messages: [
              { role: "system", content: systemPrompt },
              ...chatHistory.map(m => ({ role: m.role, content: m.content })),
              { role: "user", content: userMessage },
            ],
            temperature: parseFloat(localStorage.getItem("fireside_temperature") || "0.7"),
          };
          if (maxTokens) payload.max_tokens = maxTokens;
          if (!thinkingEnabled) payload.reasoning_effort = "none";
          const res = await fetch("http://127.0.0.1:8080/v1/chat/completions", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
          });
          if (!res.ok) throw new Error(`llama-server error: ${res.status}`);
          const data = await res.json();
          const msg = data.choices?.[0]?.message;
          // Show content first; fall back to reasoning_content
          let raw = msg?.content || (msg?.reasoning_content || "");
          // Strip leaked template tokens (ChatML, Llama, think tags, etc.)
          raw = raw
            .replace(/<\/?think>/g, "")
            .replace(/<\|im_start\|>[^\n]*/g, "")
            .replace(/<\|im_end\|>/g, "")
            .replace(/<\|end\|>/g, "")
            .replace(/<\|eot_id\|>/g, "")
            .replace(/<\|start_header_id\|>[^<]*<\|end_header_id\|>/g, "")
            .replace(/\[INST\]|\[\/INST\]/g, "")
            .trim();
          responseText = raw;
        } catch {
          throw new Error("No backend available");
        }
      }
      setChatHistory(prev => [...prev, {
        role: "assistant",
        content: responseText || "I received your message.",
        ts: new Date(),
      }]);
    } catch {
      setChatHistory(prev => [...prev, {
        role: "assistant",
        content: "I'm not connected right now. Check that your brain is running.",
        ts: new Date(),
      }]);
    } finally {
      setIsTyping(false);
      // Auto-compact history after response (non-blocking, fire-and-forget)
      setTimeout(async () => {
        try {
          const current = chatHistory;
          const compacted = await compactHistory(current);
          if (compacted.length < current.length) {
            setChatHistory(compacted);
          }
        } catch { /* compaction is best-effort */ }
      }, 0);
    }
  };

  // Group conversations by date
  const groupedConvos = useMemo(() => {
    const filtered = MOCK_CONVERSATIONS.filter(c =>
      !searchQuery || c.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.preview.toLowerCase().includes(searchQuery.toLowerCase())
    );
    const pinned = filtered.filter(c => c.pinned);
    const today = filtered.filter(c => !c.pinned && isToday(c.date));
    const yesterday = filtered.filter(c => !c.pinned && isYesterday(c.date));
    const older = filtered.filter(c => !c.pinned && !isToday(c.date) && !isYesterday(c.date));
    return { pinned, today, yesterday, older };
  }, [searchQuery]);

  return (
    <div className="fs-root">
      <style>{pageCSS}</style>
      <EmberParticles intensity={activeView === "hub" ? 25 : 12} className="fs-embers" />

      {/* ═══ Stars ═══ */}
      <div className="fs-stars">
        {Array.from({ length: 50 }).map((_, i) => (
          <div key={i} className="fs-star" style={{
            left: `${Math.random() * 100}%`,
            top: `${Math.random() * 100}%`,
            animationDelay: `${Math.random() * 5}s`,
            animationDuration: `${2 + Math.random() * 4}s`,
            width: `${1 + Math.random() * 1.5}px`,
            height: `${1 + Math.random() * 1.5}px`,
          }} />
        ))}
      </div>

      {/* ═══════════ HUB VIEW ═══════════ */}
      {activeView === "hub" && (
        <div className="fs-hub">
          <DiscoveryCard pageKey="/" />
          <div className="fs-ambient" />

          {/* LEFT: Campfire Scene */}
          <div className="fs-left">
            <h1 className="fs-title">Fireside</h1>
            <p className="fs-subtitle">Your AI Companion</p>

            <div className="fs-scene">
              <div className="fs-speech">
                <p>
                  {userName ? `Hey ${userName}! ` : "Hey! "}
                  {greeting}
                </p>
              </div>
              <img className="fs-fox" src={mascotSrc} alt={species} />
              <img className="fs-campfire" src="/hub/campfire.png" alt="Campfire" />
            </div>

            <div className="fs-model-badge">
              {brainLabel ? (
                <>Active: <strong>{brainLabel}</strong>{brainQuant ? ` · ${brainQuant}` : ''} · 🟢 Ready</>
              ) : (
                <>⚠ No brain installed · <Link href="/brains" style={{color:'#F59E0B'}}>Set up →</Link></>
              )}
            </div>
          </div>

          {/* RIGHT: Nav Cards */}
          <div className="fs-right">
            <button className="fs-nav-card fs-c1" onClick={() => { playTick(); setActiveView("chat"); }}>
              <div className="fs-nc-icon"><img src="/hub/nav_chat.png" alt="Chat" /></div>
              <div className="fs-nc-text">
                <div className="fs-nc-title">Chat</div>
                <div className="fs-nc-desc">Talk with your AI — ask anything, anytime</div>
              </div>
              <span className="fs-nc-arrow">→</span>
            </button>

            <Link href="/brains" onClick={() => playWhoosh()}>
              <div className="fs-nav-card fs-c2" style={{ animationDelay: "0.4s" }}>
                <div className="fs-nc-icon"><img src="/hub/nav_brain.png" alt="Brain" /></div>
                <div className="fs-nc-text">
                  <div className="fs-nc-title">Brain</div>
                  <div className="fs-nc-desc">Switch models, adjust quality, or download new ones</div>
                </div>
                <span className="fs-nc-arrow">→</span>
              </div>
            </Link>

            <Link href="/skills" onClick={() => playWhoosh()}>
              <div className="fs-nav-card fs-c3" style={{ animationDelay: "0.5s" }}>
                <div className="fs-nc-icon"><img src="/hub/nav_skills.png" alt="Skills" /></div>
                <div className="fs-nc-text">
                  <div className="fs-nc-title">Skills</div>
                  <div className="fs-nc-desc">Equip abilities — memory, voice, browsing, and more</div>
                </div>
                <span className="fs-nc-arrow">→</span>
              </div>
            </Link>

            <Link href="/personality" onClick={() => playWhoosh()}>
              <div className="fs-nav-card fs-c4" style={{ animationDelay: "0.6s" }}>
                <div className="fs-nc-icon"><img src="/hub/nav_personality.png" alt="Personality" /></div>
                <div className="fs-nc-text">
                  <div className="fs-nc-title">Personality</div>
                  <div className="fs-nc-desc">Define who your AI is — traits, style, and soul</div>
                </div>
                <span className="fs-nc-arrow">→</span>
              </div>
            </Link>

            <Link href="/config" onClick={() => playWhoosh()}>
              <div className="fs-nav-card fs-c5" style={{ animationDelay: "0.7s" }}>
                <div className="fs-nc-icon"><img src="/hub/nav_settings.png" alt="Settings" /></div>
                <div className="fs-nc-text">
                  <div className="fs-nc-title">Settings</div>
                  <div className="fs-nc-desc">API keys, connected devices, and advanced options</div>
                </div>
                <span className="fs-nc-arrow">→</span>
              </div>
            </Link>

            <Link href="/pipeline" onClick={() => playWhoosh()}>
              <div className="fs-nav-card fs-c6" style={{ animationDelay: "0.8s" }}>
                <div className="fs-nc-icon"><img src="/hub/nav_tasks.png" alt="Tasks" /></div>
                <div className="fs-nc-text">
                  <div className="fs-nc-title">Tasks</div>
                  <div className="fs-nc-desc">Set up multi-step workflows your AI runs for you</div>
                </div>
                <span className="fs-nc-arrow">→</span>
              </div>
            </Link>

            {!hasBrain && (
              <Link href="/brains">
                <button className="fs-btn-gold" onClick={() => playWhoosh()}>Set Up Brain →</button>
              </Link>
            )}
          </div>
        </div>
      )}

      {/* ═══════════ CHAT VIEW ═══════════ */}
      {activeView === "chat" && (
        <div className="fs-chat-layout">
          {/* Fire ambient glow at bottom */}
          <div className="fs-chat-fire-glow" />

          {/* ── Conversation Sidebar ── */}
          <div className={`fs-convo-sidebar ${sidebarOpen ? "open" : "closed"}`}>
            <div className="fs-convo-header">
              <button className="fs-back-hub" onClick={() => { setActiveView("hub"); playWhoosh(); }} title="Back to Hub">🔥 Hub</button>
              <span className="fs-convo-title">Conversations</span>
              <button className="fs-new-chat" onClick={() => { setChatHistory([]); setActiveConvo(null); sessionStorage.removeItem("fireside_chat_session"); }} title="New chat">＋</button>
            </div>

            <div className="fs-convo-search-wrap">
              <input
                className="fs-convo-search"
                placeholder="Search chats..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>

            <div className="fs-convo-list">
              {groupedConvos.pinned.length > 0 && (
                <div className="fs-convo-group">
                  <div className="fs-convo-group-label">📌 Pinned</div>
                  {groupedConvos.pinned.map(c => (
                    <button key={c.id} className={`fs-convo-item ${activeConvo === c.id ? "active" : ""}`} onClick={() => setActiveConvo(c.id)}>
                      <div className="fs-convo-item-title">{c.title}</div>
                      <div className="fs-convo-item-preview">{c.preview}</div>
                      {c.folder && <span className="fs-convo-folder">{c.folder}</span>}
                    </button>
                  ))}
                </div>
              )}
              {groupedConvos.today.length > 0 && (
                <div className="fs-convo-group">
                  <div className="fs-convo-group-label">Today</div>
                  {groupedConvos.today.map(c => (
                    <button key={c.id} className={`fs-convo-item ${activeConvo === c.id ? "active" : ""}`} onClick={() => setActiveConvo(c.id)}>
                      <div className="fs-convo-item-title">{c.title}</div>
                      <div className="fs-convo-item-preview">{c.preview}</div>
                      {c.folder && <span className="fs-convo-folder">{c.folder}</span>}
                    </button>
                  ))}
                </div>
              )}
              {groupedConvos.yesterday.length > 0 && (
                <div className="fs-convo-group">
                  <div className="fs-convo-group-label">Yesterday</div>
                  {groupedConvos.yesterday.map(c => (
                    <button key={c.id} className={`fs-convo-item ${activeConvo === c.id ? "active" : ""}`} onClick={() => setActiveConvo(c.id)}>
                      <div className="fs-convo-item-title">{c.title}</div>
                      <div className="fs-convo-item-preview">{c.preview}</div>
                      {c.folder && <span className="fs-convo-folder">{c.folder}</span>}
                    </button>
                  ))}
                </div>
              )}
              {groupedConvos.older.length > 0 && (
                <div className="fs-convo-group">
                  <div className="fs-convo-group-label">Older</div>
                  {groupedConvos.older.map(c => (
                    <button key={c.id} className={`fs-convo-item ${activeConvo === c.id ? "active" : ""}`} onClick={() => setActiveConvo(c.id)}>
                      <div className="fs-convo-item-title">{c.title}</div>
                      <div className="fs-convo-item-preview">{c.preview}</div>
                      {c.folder && <span className="fs-convo-folder">{c.folder}</span>}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* ── Main Chat Area ── */}
          <div className="fs-chat">
            {/* Header */}
            <div className="fs-chat-header">
              <button className="fs-chat-back" onClick={() => { playWhoosh(); setActiveView("hub"); }}>
                ← Hub
              </button>
              <button className="fs-sidebar-toggle" onClick={() => setSidebarOpen(!sidebarOpen)} title="Toggle conversations">
                {sidebarOpen ? "◀" : "▶"}
              </button>
              <img className="fs-chat-avatar" src={mascotSrc} alt={species} />
              <div className="fs-chat-info">
                <p className="fs-chat-name">{displayName}</p>
                <p className="fs-chat-status">
                  <span className="fs-status-dot" />
                  {isTyping ? "thinking..." : "Online · at the fireside"}
                </p>
              </div>
              <span className="fs-chat-model">{brainLabel || 'No model'}{brainQuant ? ` · ${brainQuant}` : ''}</span>
            </div>

            {/* Messages */}
            <div className="fs-messages">
              {chatHistory.length === 0 && (
                <div className="fs-empty-state">
                  <div className="fs-empty-fire">🔥</div>
                  <img src={mascotSrc} alt="" className="fs-empty-fox" />
                  <p className="fs-empty-text">Start a conversation with {displayName}</p>
                  <p className="fs-empty-sub">Your AI remembers everything · always private · always local</p>
                  <div className="fs-empty-suggestions">
                    <button className="fs-suggestion" onClick={() => { setMessage("What can you help me with?"); }}>💡 What can you do?</button>
                    <button className="fs-suggestion" onClick={() => { setMessage("Tell me about yourself"); }}>🦊 Who are you?</button>
                    <button className="fs-suggestion" onClick={() => { setMessage("Help me brainstorm an idea"); }}>✨ Brainstorm</button>
                  </div>
                </div>
              )}
              {chatHistory.map((msg, i) => (
                <div key={i} className={`fs-msg ${msg.role === "user" ? "fs-msg-user" : "fs-msg-ai"}`}>
                  {msg.role === "assistant" && (
                    <img src={mascotSrc} alt="" className="fs-msg-avatar" />
                  )}
                  <div>
                    {msg.memory && (
                      <div className="fs-memory-pill">🧠 Recalled: {msg.memory}</div>
                    )}
                    <div className={`fs-bubble ${msg.role === "user" ? "fs-bubble-user" : "fs-bubble-ai"}`}>
                      {msg.content}
                      {msg.skills && msg.skills.length > 0 && (
                        <div className="fs-skill-tag">✦ {msg.skills.join(" · ")}</div>
                      )}
                    </div>
                    {msg.ts && (
                      <div className={`fs-msg-time ${msg.role === "user" ? "fs-time-right" : ""}`}>
                        {msg.ts.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {isTyping && (
                <div className="fs-msg fs-msg-ai">
                  <img src={mascotSrc} alt="" className="fs-msg-avatar" />
                  <div className="fs-bubble fs-bubble-ai fs-typing">
                    <span className="fs-dot" /><span className="fs-dot" /><span className="fs-dot" />
                  </div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>

            {/* Input Bar */}
            <div className="fs-input-bar">
              <div className="fs-input-wrap">
                <button className="fs-voice-btn" title="Voice mode">🎙</button>
                <button
                  className={`fs-think-btn ${thinkingEnabled ? 'active' : ''}`}
                  onClick={() => {
                    setThinkingEnabled(v => {
                      const next = !v;
                      localStorage.setItem('fireside_thinking_enabled', String(next));
                      return next;
                    });
                  }}
                  title={thinkingEnabled ? 'Thinking mode ON — model reasons before responding (global)' : 'Thinking mode OFF — direct responses (global)'}
                >
                  🧠
                </button>
                <input
                  ref={inputRef}
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSend()}
                  placeholder={`Message ${displayName}...`}
                  className="fs-chat-input"
                  autoFocus
                />
                <button onClick={handleSend} disabled={!message.trim()} className="fs-send-btn">▶</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Helpers
function isToday(date: Date) {
  const t = new Date(); return date.toDateString() === t.toDateString();
}
function isYesterday(date: Date) {
  const y = new Date(); y.setDate(y.getDate() - 1); return date.toDateString() === y.toDateString();
}

// ════════════════════════════════════════════════════════════════════
// CSS — Fireside Hub + Chat
// ════════════════════════════════════════════════════════════════════

const pageCSS = `
  .fs-root {
    min-height: 100vh; width: 100%;
    background: #060609;
    font-family: 'Outfit', 'Inter', system-ui, sans-serif;
    color: #F0DCC8;
    position: relative; overflow: hidden;
  }
  .fs-embers { position: fixed !important; inset: 0 !important; z-index: 1 !important; }

  /* ── Stars ── */
  .fs-stars { position: fixed; inset: 0; z-index: 0; pointer-events: none; }
  .fs-star {
    position: absolute; background: #fff; border-radius: 50%;
    animation: fsTwinkle ease-in-out infinite alternate; opacity: 0.15;
  }
  @keyframes fsTwinkle { 0% { opacity: 0.05; } 100% { opacity: 0.35; } }

  /* ══════════════════════════════════ */
  /* ── HUB VIEW ── */
  /* ══════════════════════════════════ */
  .fs-hub {
    min-height: 100vh; width: 100%;
    display: flex; align-items: center; justify-content: center;
    position: relative; z-index: 5;
    padding: 0 40px; gap: 60px;
    max-width: 1100px; margin: 0 auto;
    animation: fsFadeUp 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards;
  }
  @keyframes fsFadeUp {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
  }

  .fs-ambient {
    position: fixed; inset: 0; z-index: 0; pointer-events: none;
    background:
      radial-gradient(ellipse 700px 500px at 30% 65%, rgba(245,158,11,0.06) 0%, transparent 55%),
      radial-gradient(ellipse 500px 350px at 25% 75%, rgba(217,119,6,0.04) 0%, transparent 45%);
    animation: fsAmbient 4s ease-in-out infinite alternate;
  }
  @keyframes fsAmbient { 0% { opacity: 0.7; } 100% { opacity: 1; } }

  .fs-left {
    flex: 0 0 420px;
    display: flex; flex-direction: column; align-items: center;
  }
  .fs-title {
    font-size: 42px; font-weight: 900;
    background: linear-gradient(135deg, #F0DCC8 0%, #FBBF24 50%, #D97706 100%);
    -webkit-background-clip: text; background-clip: text;
    -webkit-text-fill-color: transparent;
    animation: fsFadeUp 0.8s ease both; margin-bottom: 2px;
  }
  .fs-subtitle {
    font-size: 14px; color: #4A3D30;
    margin-bottom: 24px; animation: fsFadeUp 0.8s 0.15s ease both;
  }
  .fs-scene { position: relative; width: 400px; height: 320px; margin-bottom: 20px; }

  .fs-campfire {
    position: absolute; bottom: 0; left: 50%; transform: translateX(-50%);
    width: 380px; height: 300px; object-fit: contain;
    mix-blend-mode: screen;
    -webkit-mask-image: radial-gradient(ellipse 65% 70% at 50% 55%, white 30%, transparent 65%);
    mask-image: radial-gradient(ellipse 65% 70% at 50% 55%, white 30%, transparent 65%);
    filter: drop-shadow(0 0 40px rgba(245,158,11,0.3));
    animation: fsFireGlow 3s ease-in-out infinite alternate;
  }
  @keyframes fsFireGlow {
    0% { filter: drop-shadow(0 0 30px rgba(245,158,11,0.2)) brightness(0.95); }
    100% { filter: drop-shadow(0 0 50px rgba(245,158,11,0.4)) brightness(1.05); }
  }

  .fs-fox {
    position: absolute; bottom: 10px; left: 10px;
    width: 150px; height: 150px; object-fit: contain;
    mix-blend-mode: screen;
    -webkit-mask-image: radial-gradient(ellipse 70% 70% at center, white 40%, transparent 72%);
    mask-image: radial-gradient(ellipse 70% 70% at center, white 40%, transparent 72%);
    animation: fsFoxBob 4s ease-in-out infinite;
  }
  @keyframes fsFoxBob { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-5px); } }

  .fs-speech {
    position: absolute; top: 55px; left: 120px;
    background: rgba(15,13,22,0.90); border: 1px solid rgba(245,158,11,0.12);
    border-radius: 14px 14px 14px 4px;
    padding: 12px 16px; max-width: 210px;
    font-size: 12px; color: #C4A882; line-height: 1.6;
    box-shadow: 0 4px 24px rgba(0,0,0,0.4);
    animation: fsBubIn 0.5s 1.2s ease both;
  }
  .fs-speech::after {
    content: ''; position: absolute; bottom: -10px; left: 20px;
    border: 6px solid transparent; border-top-color: rgba(15,13,22,0.90);
  }
  @keyframes fsBubIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }

  .fs-model-badge {
    padding: 8px 22px; border-radius: 10px;
    background: rgba(245,158,11,0.05); border: 1px solid rgba(245,158,11,0.12);
    font-size: 11px; color: #6A5A4A; font-weight: 600;
    animation: fsFadeUp 0.8s 1s ease both;
  }
  .fs-model-badge strong { color: #F59E0B; }

  /* RIGHT: Nav Cards */
  .fs-right { flex: 1; display: flex; flex-direction: column; gap: 14px; }
  .fs-right a { text-decoration: none; }

  .fs-nav-card {
    display: flex; align-items: center; gap: 20px;
    padding: 22px 28px; border-radius: 18px;
    cursor: pointer; width: 100%; text-align: left;
    background: linear-gradient(135deg, rgba(255,255,255,0.03), rgba(255,255,255,0.012));
    border: 1.5px solid rgba(255,255,255,0.06);
    backdrop-filter: blur(8px);
    transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
    animation: fsCardIn 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) both;
    position: relative; overflow: hidden;
    font-family: 'Outfit', system-ui, sans-serif;
  }
  .fs-nav-card:nth-child(1) { animation-delay: 0.3s; }
  .fs-nav-card:nth-child(2) { animation-delay: 0.4s; }
  .fs-nav-card:nth-child(3) { animation-delay: 0.5s; }
  @keyframes fsCardIn { from { opacity: 0; transform: translateX(30px); } to { opacity: 1; transform: translateX(0); } }

  .fs-nav-card::before {
    content: ''; position: absolute; left: 0; top: 15%; bottom: 15%; width: 3px;
    border-radius: 0 3px 3px 0;
    background: var(--nc); box-shadow: 0 0 12px var(--nc), 0 0 4px var(--nc);
    opacity: 0.6; transition: opacity 0.3s;
  }
  .fs-nav-card:hover {
    transform: translateX(8px);
    border-color: color-mix(in srgb, var(--nc) 35%, transparent);
    background: linear-gradient(135deg, color-mix(in srgb, var(--nc) 4%, transparent), rgba(255,255,255,0.015));
    box-shadow: 0 8px 40px color-mix(in srgb, var(--nc) 8%, transparent), 0 0 25px color-mix(in srgb, var(--nc) 4%, transparent);
  }
  .fs-nav-card:hover::before { opacity: 1; }

  .fs-c1 { --nc: #F59E0B; }
  .fs-c2 { --nc: #A78BFA; }
  .fs-c3 { --nc: #FBBF24; }
  .fs-c4 { --nc: #FB923C; }
  .fs-c5 { --nc: #60A5FA; }
  .fs-c6 { --nc: #2DD4BF; }

  .fs-nc-icon { width: 56px; height: 56px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
  .fs-nc-icon img {
    width: 64px; height: 64px; mix-blend-mode: screen;
    -webkit-mask-image: radial-gradient(circle, white 35%, transparent 65%);
    mask-image: radial-gradient(circle, white 35%, transparent 65%);
    filter: drop-shadow(0 0 10px var(--nc)); transition: transform 0.3s;
  }
  .fs-nav-card:hover .fs-nc-icon img { transform: scale(1.15); filter: drop-shadow(0 0 18px var(--nc)); }

  .fs-nc-text { flex: 1; }
  .fs-nc-title {
    font-size: 16px; font-weight: 800; color: var(--nc);
    text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 3px;
  }
  .fs-nc-desc { font-size: 12px; color: #5A4D40; line-height: 1.4; }
  .fs-nc-arrow { font-size: 16px; color: #3A3530; transition: all 0.3s; }
  .fs-nav-card:hover .fs-nc-arrow { color: var(--nc); transform: translateX(4px); }

  .fs-nc-notif {
    position: absolute; top: 12px; right: 12px;
    padding: 2px 8px; border-radius: 10px;
    font-size: 9px; font-weight: 800; color: #fff;
    background: #EF4444; box-shadow: 0 0 8px rgba(239,68,68,0.4);
    animation: fsDotPulse 2s ease-in-out infinite;
  }
  @keyframes fsDotPulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.7; } }

  .fs-btn-gold {
    padding: 12px 36px; border-radius: 12px; border: none; cursor: pointer;
    background: linear-gradient(135deg, #D97706, #F59E0B);
    color: #0A0A0A; font-size: 14px; font-weight: 800;
    box-shadow: 0 4px 24px rgba(245,158,11,0.25); transition: all 0.3s;
    font-family: 'Outfit', system-ui;
  }
  .fs-btn-gold:hover { transform: translateY(-2px); box-shadow: 0 8px 32px rgba(245,158,11,0.4); }

  /* ══════════════════════════════════ */
  /* ── CHAT VIEW ── */
  /* ══════════════════════════════════ */
  .fs-chat-layout {
    height: 100vh; width: 100%;
    display: flex; position: relative; z-index: 5;
    animation: fsFadeUp 0.5s ease forwards;
  }

  /* Fire glow at bottom of chat */
  .fs-chat-fire-glow {
    position: fixed; bottom: 0; left: 0; right: 0; height: 250px; z-index: 0;
    pointer-events: none;
    background:
      radial-gradient(ellipse 60% 100% at 50% 100%, rgba(245,158,11,0.06) 0%, transparent 50%),
      radial-gradient(ellipse 40% 80% at 50% 100%, rgba(217,119,6,0.04) 0%, transparent 40%);
    animation: fsFireGlow 3s ease-in-out infinite alternate;
  }

  /* ── Conversation Sidebar ── */
  .fs-convo-sidebar {
    width: 280px; flex-shrink: 0;
    background: rgba(8,8,14,0.92); backdrop-filter: blur(20px);
    border-right: 1px solid rgba(255,255,255,0.04);
    display: flex; flex-direction: column;
    transition: width 0.3s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.3s;
    overflow: hidden; z-index: 15;
  }
  .fs-convo-sidebar.closed { width: 0; opacity: 0; }

  .fs-convo-header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 16px 18px; border-bottom: 1px solid rgba(255,255,255,0.04);
  }
  .fs-convo-title { font-size: 14px; font-weight: 800; color: #C4A882; }
  .fs-new-chat {
    width: 28px; height: 28px; border-radius: 8px;
    background: rgba(245,158,11,0.08); border: 1px solid rgba(245,158,11,0.15);
    color: #F59E0B; font-size: 16px; cursor: pointer;
    display: flex; align-items: center; justify-content: center;
    transition: all 0.2s;
  }
  .fs-new-chat:hover { background: rgba(245,158,11,0.15); transform: scale(1.05); }
  .fs-back-hub {
    padding: 5px 12px; border-radius: 8px; font-size: 12px; font-weight: 800;
    background: rgba(245,158,11,0.06); border: 1px solid rgba(245,158,11,0.12);
    color: #C4A882; cursor: pointer; transition: all 0.2s; font-family: 'Outfit';
  }
  .fs-back-hub:hover { background: rgba(245,158,11,0.12); color: #F59E0B; border-color: rgba(245,158,11,0.25); }

  .fs-convo-search-wrap { padding: 10px 14px; }
  .fs-convo-search {
    width: 100%; padding: 8px 12px; border-radius: 10px;
    background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06);
    color: #C4A882; font-size: 12px; outline: none;
    font-family: 'Outfit'; transition: all 0.2s;
  }
  .fs-convo-search:focus { border-color: rgba(245,158,11,0.2); }
  .fs-convo-search::placeholder { color: rgba(200,180,160,0.25); }

  .fs-convo-list {
    flex: 1; overflow-y: auto; padding: 4px 8px;
  }
  .fs-convo-list::-webkit-scrollbar { width: 2px; }
  .fs-convo-list::-webkit-scrollbar-thumb { background: rgba(245,158,11,0.1); }

  .fs-convo-group { margin-bottom: 12px; }
  .fs-convo-group-label {
    font-size: 10px; font-weight: 800; color: #4A3D30;
    text-transform: uppercase; letter-spacing: 1.5px;
    padding: 8px 10px 4px; margin-bottom: 2px;
  }

  .fs-convo-item {
    width: 100%; text-align: left; padding: 10px 12px;
    border-radius: 10px; cursor: pointer;
    background: transparent; border: 1px solid transparent;
    transition: all 0.2s; display: block; position: relative;
    font-family: 'Outfit';
  }
  .fs-convo-item:hover {
    background: rgba(245,158,11,0.04);
    border-color: rgba(245,158,11,0.08);
  }
  .fs-convo-item.active {
    background: rgba(245,158,11,0.08);
    border-color: rgba(245,158,11,0.15);
  }
  .fs-convo-item-title {
    font-size: 12px; font-weight: 700; color: #C4A882;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    margin-bottom: 2px;
  }
  .fs-convo-item-preview {
    font-size: 10px; color: #4A3D30; line-height: 1.4;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }
  .fs-convo-folder {
    position: absolute; top: 8px; right: 8px;
    font-size: 8px; font-weight: 800; color: #A78BFA;
    padding: 1px 6px; border-radius: 4px;
    background: rgba(167,139,250,0.08); border: 1px solid rgba(167,139,250,0.12);
    text-transform: uppercase; letter-spacing: 0.5px;
  }

  /* ── Main Chat ── */
  .fs-chat {
    flex: 1; display: flex; flex-direction: column;
    position: relative; z-index: 5;
    min-width: 0;
  }

  .fs-chat-header {
    display: flex; align-items: center; gap: 12px;
    padding: 12px 24px;
    background: rgba(8,8,14,0.85); backdrop-filter: blur(20px);
    border-bottom: 1px solid rgba(255,255,255,0.04); z-index: 20;
  }
  .fs-chat-back {
    background: none; border: 1px solid rgba(255,255,255,0.08);
    color: #5A4D40; font-size: 12px; font-weight: 700; cursor: pointer;
    padding: 6px 14px; border-radius: 10px; transition: all 0.2s;
    font-family: 'Outfit';
  }
  .fs-chat-back:hover { color: #F0DCC8; border-color: rgba(245,158,11,0.25); }

  .fs-sidebar-toggle {
    background: none; border: 1px solid rgba(255,255,255,0.06);
    color: #3A3530; font-size: 10px; cursor: pointer;
    padding: 5px 8px; border-radius: 6px; transition: all 0.2s;
  }
  .fs-sidebar-toggle:hover { color: #F59E0B; border-color: rgba(245,158,11,0.2); }

  .fs-chat-avatar {
    width: 36px; height: 36px; border-radius: 12px; object-fit: contain;
    background: rgba(245,158,11,0.06); border: 1px solid rgba(245,158,11,0.1);
  }
  .fs-chat-info { flex: 1; }
  .fs-chat-name { font-size: 15px; font-weight: 800; color: #F0DCC8; margin: 0; }
  .fs-chat-status { font-size: 11px; color: #4A3D30; margin: 0; display: flex; align-items: center; gap: 5px; }
  .fs-status-dot { width: 6px; height: 6px; border-radius: 50%; background: #34D399; box-shadow: 0 0 6px rgba(52,211,153,0.4); }
  .fs-chat-model {
    font-size: 10px; color: #3A3530; padding: 3px 10px;
    background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.05);
    border-radius: 8px; font-weight: 600;
  }

  /* Messages area */
  .fs-messages {
    flex: 1; overflow-y: auto; padding: 20px 24px;
    display: flex; flex-direction: column; gap: 8px;
    max-width: 760px; width: 100%; margin: 0 auto;
  }
  .fs-messages::-webkit-scrollbar { width: 3px; }
  .fs-messages::-webkit-scrollbar-thumb { background: rgba(245,158,11,0.1); border-radius: 2px; }

  .fs-msg { display: flex; gap: 10px; animation: fsMsgIn 0.35s cubic-bezier(0.16, 1, 0.3, 1) both; }
  .fs-msg-user { justify-content: flex-end; }
  .fs-msg-ai { justify-content: flex-start; align-items: flex-start; }
  @keyframes fsMsgIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

  .fs-msg-avatar {
    width: 32px; height: 32px; border-radius: 10px; flex-shrink: 0;
    object-fit: contain; margin-top: 2px;
    background: rgba(245,158,11,0.04); border: 1px solid rgba(245,158,11,0.08);
  }

  .fs-bubble {
    max-width: 70%; padding: 12px 16px;
    font-size: 14px; line-height: 1.65; font-weight: 500;
  }
  .fs-bubble-user {
    background: linear-gradient(135deg, rgba(217,119,6,0.15), rgba(245,158,11,0.08));
    border: 1px solid rgba(245,158,11,0.12);
    color: #F0DCC8; border-radius: 18px 18px 4px 18px;
  }
  .fs-bubble-ai {
    background: rgba(15,13,22,0.7); backdrop-filter: blur(12px);
    border: 1px solid rgba(255,255,255,0.05);
    color: #C4B098; border-radius: 18px 18px 18px 4px;
  }

  .fs-msg-time {
    font-size: 9px; color: #2A2520; margin-top: 3px; padding: 0 4px;
  }
  .fs-time-right { text-align: right; }

  .fs-memory-pill {
    display: inline-flex; align-items: center; gap: 5px;
    font-size: 10px; color: #6A5A8A; padding: 3px 10px;
    background: rgba(167,139,250,0.06); border: 1px solid rgba(167,139,250,0.1);
    border-radius: 20px; margin-bottom: 4px;
  }
  .fs-skill-tag {
    display: inline-flex; align-items: center; gap: 4px;
    font-size: 9px; color: #34D399; padding: 2px 8px;
    background: rgba(52,211,153,0.06); border: 1px solid rgba(52,211,153,0.1);
    border-radius: 6px; margin-top: 6px; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.5px;
  }

  .fs-typing { display: flex; gap: 5px; align-items: center; padding: 16px 20px; }
  .fs-dot {
    width: 6px; height: 6px; border-radius: 50%; background: #5A4D40;
    animation: fsDotBounce 1.4s ease-in-out infinite;
  }
  .fs-dot:nth-child(2) { animation-delay: 0.15s; }
  .fs-dot:nth-child(3) { animation-delay: 0.3s; }
  @keyframes fsDotBounce { 0%, 60%, 100% { transform: translateY(0); opacity: 0.4; } 30% { transform: translateY(-4px); opacity: 1; } }

  /* Empty state */
  .fs-empty-state {
    flex: 1; display: flex; flex-direction: column;
    align-items: center; justify-content: center; gap: 10px;
    padding-bottom: 60px;
  }
  .fs-empty-fire {
    font-size: 48px; margin-bottom: 4px;
    animation: fsFirePulse 2s ease-in-out infinite;
  }
  @keyframes fsFirePulse {
    0%, 100% { transform: scale(1); filter: brightness(0.9); }
    50% { transform: scale(1.1); filter: brightness(1.2); text-shadow: 0 0 30px rgba(245,158,11,0.5); }
  }
  .fs-empty-fox {
    width: 80px; height: 80px; object-fit: contain;
    mix-blend-mode: screen;
    filter: drop-shadow(0 0 20px rgba(245,158,11,0.2));
    animation: fsFoxBob 4s ease-in-out infinite;
  }
  .fs-empty-text { font-size: 18px; font-weight: 700; color: #8A7A6A; margin-top: 4px; }
  .fs-empty-sub { font-size: 12px; color: #4A3D30; margin-bottom: 16px; }

  .fs-empty-suggestions {
    display: flex; gap: 10px; flex-wrap: wrap; justify-content: center;
  }
  .fs-suggestion {
    padding: 8px 16px; border-radius: 20px;
    background: rgba(245,158,11,0.05); border: 1px solid rgba(245,158,11,0.1);
    color: #8A7A6A; font-size: 12px; font-weight: 600; cursor: pointer;
    transition: all 0.2s; font-family: 'Outfit';
  }
  .fs-suggestion:hover {
    background: rgba(245,158,11,0.1); border-color: rgba(245,158,11,0.25);
    color: #F59E0B; transform: translateY(-2px);
  }

  /* Input bar */
  .fs-input-bar {
    padding: 12px 24px 20px;
    background: rgba(8,8,14,0.85); backdrop-filter: blur(20px);
    border-top: 1px solid rgba(255,255,255,0.04);
    z-index: 20; display: flex; justify-content: center;
  }
  .fs-input-wrap {
    display: flex; align-items: center; gap: 10px;
    width: 100%; max-width: 760px;
  }
  .fs-voice-btn {
    width: 42px; height: 42px; border-radius: 12px;
    background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06);
    color: #4A3D40; font-size: 18px; cursor: pointer;
    display: flex; align-items: center; justify-content: center;
    transition: all 0.2s; flex-shrink: 0;
  }
  .fs-voice-btn:hover { color: #F59E0B; border-color: rgba(245,158,11,0.2); background: rgba(245,158,11,0.05); }

  .fs-think-btn {
    width: 42px; height: 42px; border-radius: 12px;
    background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06);
    color: #4A3D40; font-size: 18px; cursor: pointer;
    display: flex; align-items: center; justify-content: center;
    transition: all 0.3s; flex-shrink: 0; opacity: 0.4;
  }
  .fs-think-btn:hover { opacity: 0.7; }
  .fs-think-btn.active {
    opacity: 1; color: #F59E0B;
    border-color: rgba(245,158,11,0.3);
    background: rgba(245,158,11,0.08);
    box-shadow: 0 0 12px rgba(245,158,11,0.15);
  }

  .fs-chat-input {
    flex: 1; padding: 12px 18px; border-radius: 14px;
    background: rgba(18,16,26,0.7); backdrop-filter: blur(12px);
    border: 1.5px solid rgba(255,255,255,0.06);
    color: #F0DCC8; font-size: 14px; font-weight: 500; outline: none;
    font-family: 'Outfit'; transition: all 0.3s;
  }
  .fs-chat-input:focus {
    border-color: rgba(245,158,11,0.25);
    box-shadow: 0 0 20px rgba(245,158,11,0.06);
  }
  .fs-chat-input::placeholder { color: rgba(240,220,200,0.2); }

  .fs-send-btn {
    width: 42px; height: 42px; border-radius: 12px;
    background: linear-gradient(135deg, #D97706, #F59E0B);
    border: none; cursor: pointer; flex-shrink: 0;
    color: #0A0A0A; font-size: 16px; font-weight: 900;
    display: flex; align-items: center; justify-content: center;
    transition: all 0.2s; box-shadow: 0 2px 12px rgba(245,158,11,0.2);
  }
  .fs-send-btn:hover { transform: scale(1.05); box-shadow: 0 4px 20px rgba(245,158,11,0.3); }
  .fs-send-btn:disabled { opacity: 0.2; cursor: default; transform: none; }
`;
