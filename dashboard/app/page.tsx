"use client";

import { useState, useEffect, useRef, useMemo } from "react";
import { API_BASE } from "../lib/api";
import Link from "next/link";
import EmberParticles from "@/components/EmberParticles";
import { playWhoosh, playTick } from "@/components/FiresideSounds";
import ReactMarkdown from "react-markdown";

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

// Conversation persistence
interface Conversation {
  id: string;
  title: string;
  preview: string;
  date: string; // ISO string for serialization
  folder?: string;
  pinned?: boolean;
  messages: { role: string; content: string; memory?: string; skills?: string[]; ts?: string }[];
}

function loadConversations(): Conversation[] {
  if (typeof window === "undefined") return [];
  try {
    return JSON.parse(localStorage.getItem("fireside_conversations") || "[]");
  } catch { return []; }
}

function saveConversations(convos: Conversation[]) {
  localStorage.setItem("fireside_conversations", JSON.stringify(convos));
}

function generateTitle(messages: { role: string; content: string }[]): string {
  const first = messages.find(m => m.role === "user");
  if (!first) return "New conversation";
  const text = first.content.substring(0, 60);
  return text.length < first.content.length ? text + "..." : text;
}

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
      if (!saved) return [];
      // Rehydrate ts strings back to Date objects (JSON.parse loses Date type)
      return JSON.parse(saved).map((m: { role: string; content: string; memory?: string; skills?: string[]; ts?: string }) => ({
        ...m,
        ts: m.ts ? new Date(m.ts) : undefined,
      }));
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
  const [conversations, setConversations] = useState<Conversation[]>(loadConversations);

  // ── Chat management ──
  const [selectMode, setSelectMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  // ── File upload ──
  const [attachedFiles, setAttachedFiles] = useState<File[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // ── Knowledge Base ──
  const [kbOpen, setKbOpen] = useState(false);
  const [kbFolders, setKbFolders] = useState<{name:string;files:number;chunks:number}[]>([]);
  const [kbNewFolder, setKbNewFolder] = useState("");
  const [kbUploading, setKbUploading] = useState(false);
  const kbFileRef = useRef<HTMLInputElement>(null);
  const [kbSelectedFolder, setKbSelectedFolder] = useState("general");

  const fetchKbFolders = async () => {
    try {
      const r = await fetch(`${API_BASE}/tools/knowledge/folders`);
      const d = await r.json();
      if (d.ok) setKbFolders(d.folders || []);
    } catch {}
  };
  const uploadKbFile = async (file: File, folder: string) => {
    setKbUploading(true);
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("folder", folder);
      await fetch(`${API_BASE}/tools/knowledge/upload-file`, { method: "POST", body: form });
      await fetchKbFolders();
    } catch {} finally { setKbUploading(false); }
  };
  const createKbFolder = async () => {
    if (!kbNewFolder.trim()) return;
    // Creating a folder is done by uploading — but we can also just ingest
    try {
      await fetch(`${API_BASE}/tools/knowledge/ingest`, {
        method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ folder: kbNewFolder.trim() }),
      });
      setKbNewFolder("");
      await fetchKbFolders();
    } catch {}
  };

  const toggleSelect = (id: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const deleteConvo = (id: string) => {
    if (activeConvo === id) {
      setChatHistory([]);
      setActiveConvo(null);
      sessionStorage.removeItem("fireside_chat_session");
    }
    setConversations(prev => {
      const updated = prev.filter(c => c.id !== id);
      saveConversations(updated);
      return updated;
    });
  };

  const deleteSelected = () => {
    if (selectedIds.size === 0) return;
    if (activeConvo && selectedIds.has(activeConvo)) {
      setChatHistory([]);
      setActiveConvo(null);
      sessionStorage.removeItem("fireside_chat_session");
    }
    setConversations(prev => {
      const updated = prev.filter(c => !selectedIds.has(c.id));
      saveConversations(updated);
      return updated;
    });
    setSelectedIds(new Set());
    setSelectMode(false);
  };

  const clearAllConvos = () => {
    if (!confirm("Delete ALL conversations? This cannot be undone.")) return;
    setChatHistory([]);
    setActiveConvo(null);
    sessionStorage.removeItem("fireside_chat_session");
    setConversations([]);
    saveConversations([]);
    setSelectMode(false);
    setSelectedIds(new Set());
  };

  const handleFileSelect = (files: FileList | null) => {
    if (!files) return;
    setAttachedFiles(prev => [...prev, ...Array.from(files)].slice(0, 5));
  };

  const removeFile = (index: number) => {
    setAttachedFiles(prev => prev.filter((_, i) => i !== index));
  };

  // Ref to always have latest chatHistory (avoids stale closure in onClick handlers)
  const chatHistoryRef = useRef(chatHistory);
  chatHistoryRef.current = chatHistory;
  const activeConvoRef = useRef(activeConvo);
  activeConvoRef.current = activeConvo;

  // Save current chat to a conversation (create or update)
  const saveCurrentChat = () => {
    const history = chatHistoryRef.current;
    const convoId = activeConvoRef.current;
    console.log("[Fireside] saveCurrentChat called", { historyLen: history.length, convoId });
    if (history.length === 0) {
      console.log("[Fireside] saveCurrentChat skipped -- no messages");
      return;
    }
    const id = convoId || `conv_${Date.now()}`;
    const title = generateTitle(history);
    const preview = history[history.length - 1]?.content?.substring(0, 80) || "";
    console.log("[Fireside] saving conversation", { id, title: generateTitle(history), messageCount: history.length });
    const convo: Conversation = {
      id, title, preview,
      date: new Date().toISOString(),
      messages: history.map(m => ({ ...m, ts: m.ts ? new Date(m.ts).toISOString() : undefined })),
    };
    setConversations(prev => {
      const filtered = prev.filter(c => c.id !== id);
      const updated = [convo, ...filtered].slice(0, 50); // keep last 50
      saveConversations(updated);
      return updated;
    });
    if (!convoId) setActiveConvo(id);
  };

  // Load a conversation from the sidebar
  const loadConvo = (id: string) => {
    saveCurrentChat(); // save current first
    const convo = conversations.find(c => c.id === id);
    if (convo) {
      setChatHistory(convo.messages.map(m => ({ ...m, ts: m.ts ? new Date(m.ts) : undefined })));
      setActiveConvo(id);
    }
  };

  // Auto-save conversation after each assistant response
  useEffect(() => {
    if (chatHistory.length > 0 && chatHistory[chatHistory.length - 1]?.role === "assistant") {
      saveCurrentChat();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chatHistory.length]);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

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

    // Auto-detect brain from API if localStorage doesn't have it
    if (!model) {
      fetch(`${API_BASE}/api/v1/status`).then(r => r.json()).then(data => {
        if (data.model || data.status === "ready") {
          const detected = data.model || "Local Model";
          setHasBrain(true);
          setBrainLabel(detected);
          localStorage.setItem("fireside_model", detected);
          if (data.quant) {
            setBrainQuant(data.quant);
            localStorage.setItem("fireside_brain_quant", data.quant);
          }
        }
      }).catch(() => { /* backend not running yet */ });
    }
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

    // Add a placeholder assistant message that we stream into
    const streamIndex = chatHistory.length + 1; // +1 for user msg just added
    setChatHistory(prev => [...prev, { role: "assistant", content: "", ts: new Date() }]);

    // Helper: append tokens to the last assistant message
    const appendToken = (token: string) => {
      setChatHistory(prev => {
        const updated = [...prev];
        const last = updated[updated.length - 1];
        if (last && last.role === "assistant") {
          updated[updated.length - 1] = { ...last, content: last.content + token };
        }
        return updated;
      });
    };

    // Helper: finalize the last assistant message (strip artifacts, set final content)
    const finalizeMessage = (fullText: string) => {
      const clean = fullText
        .replace(/<\/?think>/g, "")
        .replace(/Thinking Process[\s\S]*?(?=\n\n|\n[A-Z]|$)/i, "")
        .replace(/Thought Process[\s\S]*?(?=\n\n|\n[A-Z]|$)/i, "")
        .replace(/<\|im_start\|>[^\n]*/g, "")
        .replace(/<\|im_end\|>/g, "")
        .replace(/<\|end\|>/g, "")
        .replace(/<\|eot_id\|>/g, "")
        .replace(/<\|start_header_id\|>[^<]*<\|end_header_id\|>/g, "")
        .replace(/\[INST\]|\[\/INST\]/g, "")
        .trim();

      setChatHistory(prev => {
        const updated = [...prev];
        const last = updated[updated.length - 1];
        if (last && last.role === "assistant") {
          updated[updated.length - 1] = { ...last, content: clean || "I received your message." };
        }
        return updated;
      });
    };

    // Helper: parse SSE stream (used by both backends)
    const readSSEStream = async (response: Response): Promise<string> => {
      const reader = response.body?.getReader();
      if (!reader) return "";
      const decoder = new TextDecoder();
      let fullText = "";
      setIsTyping(false); // stop dots once streaming starts

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          const chunk = decoder.decode(value, { stream: true });
          // Parse SSE format: "data: {...}\n\n"
          const lines = chunk.split("\n");
          for (const line of lines) {
            if (line.startsWith("data: ")) {
              const data = line.slice(6).trim();
              if (data === "[DONE]") continue;
              try {
                const parsed = JSON.parse(data);
                // OpenAI-compatible streaming format
                const token = parsed.choices?.[0]?.delta?.content
                  || parsed.choices?.[0]?.text
                  || parsed.token?.text
                  || parsed.content
                  || "";
                if (token) {
                  fullText += token;
                  appendToken(token);
                }
              } catch { /* skip non-JSON lines */ }
            }
          }
        }
      } catch { /* stream interrupted */ }
      return fullText;
    };

    try {
      let fullText = "";
      const recalled = recallMemories(userMessage);
      const memoryContext = recalled ? `\n\n[Remembered from past conversations] ${recalled}` : "";
      const maxTokens = getResponseLimit();

      // Try Python backend first (port 8765) with streaming
      try {
        const res = await fetch(`${API_BASE}/api/v1/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            message: userMessage,
            stream: true,
            history: chatHistory.map(m => ({ role: m.role, content: m.content })),
          }),
        });
        if (!res.ok) throw new Error(`API error: ${res.status}`);

        // Check if response is streaming (SSE) or JSON
        const contentType = res.headers.get("content-type") || "";
        if (contentType.includes("text/event-stream") || contentType.includes("text/plain")) {
          fullText = await readSSEStream(res);
        } else {
          // Fallback: non-streaming JSON response
          const data = await res.json();
          fullText = data.response || data.content || "";
          setIsTyping(false);
        }
      } catch {
        // Fallback: try llama-server directly (port 8080, OpenAI-compatible streaming)
        try {
          const soulIdentity = typeof window !== "undefined" ? localStorage.getItem("fireside_soul_identity") : null;
          const systemPrompt = soulIdentity
            ? `${soulIdentity}\n\nYour name is ${displayName}.${memoryContext}`
            : `You are a helpful AI companion named ${displayName}. Be friendly, concise, and helpful.${memoryContext}`;
          const thinkingOn = typeof window !== "undefined" ? localStorage.getItem("fireside_thinking_enabled") !== "false" : true;
          const payload: Record<string, unknown> = {
            model: "local",
            stream: true,
            messages: [
              { role: "system", content: systemPrompt },
              ...chatHistory.slice(0, -1).map(m => ({ role: m.role, content: m.content })), // exclude the empty placeholder
              { role: "user", content: userMessage },
            ],
            temperature: parseFloat(localStorage.getItem("fireside_temperature") || "0.7"),
          };
          if (maxTokens) payload.max_tokens = maxTokens;
          if (!thinkingOn) payload.reasoning_effort = "none";

          const res = await fetch("http://127.0.0.1:8080/v1/chat/completions", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
          });
          if (!res.ok) throw new Error(`llama-server error: ${res.status}`);

          fullText = await readSSEStream(res);
        } catch {
          throw new Error("No backend available");
        }
      }

      // Clean up template artifacts in the final text
      finalizeMessage(fullText);

    } catch {
      setChatHistory(prev => {
        const updated = [...prev];
        const last = updated[updated.length - 1];
        if (last && last.role === "assistant") {
          updated[updated.length - 1] = {
            ...last,
            content: "I'm not connected right now. Check that your brain is running.",
          };
        }
        return updated;
      });
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
    const filtered = conversations.filter(c =>
      !searchQuery || c.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.preview.toLowerCase().includes(searchQuery.toLowerCase())
    );
    const pinned = filtered.filter(c => c.pinned);
    const today = filtered.filter(c => !c.pinned && isToday(new Date(c.date)));
    const yesterday = filtered.filter(c => !c.pinned && isYesterday(new Date(c.date)));
    const older = filtered.filter(c => !c.pinned && !isToday(new Date(c.date)) && !isYesterday(new Date(c.date)));
    return { pinned, today, yesterday, older };
  }, [searchQuery, conversations]);

  return (
    <div className="fs-root">
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
              <div style={{ display: "flex", gap: 4 }}>
                <button
                  className="fs-new-chat"
                  onClick={() => { setSelectMode(!selectMode); setSelectedIds(new Set()); }}
                  title={selectMode ? "Cancel select" : "Select chats"}
                  style={{ opacity: selectMode ? 1 : 0.5, fontSize: 13 }}
                >
                  {selectMode ? "✕" : "☑"}
                </button>
                <button className="fs-new-chat" onClick={() => { saveCurrentChat(); setChatHistory([]); setActiveConvo(null); sessionStorage.removeItem("fireside_chat_session"); }} title="New chat">＋</button>
              </div>
            </div>

            {/* Bulk actions bar */}
            {selectMode && (
              <div style={{
                display: "flex", gap: 6, padding: "6px 12px",
                borderBottom: "1px solid rgba(255,255,255,0.06)",
              }}>
                <button
                  onClick={deleteSelected}
                  disabled={selectedIds.size === 0}
                  style={{
                    flex: 1, padding: "6px 0", borderRadius: 6,
                    background: selectedIds.size > 0 ? "rgba(239,68,68,0.2)" : "rgba(255,255,255,0.05)",
                    color: selectedIds.size > 0 ? "#EF4444" : "#666",
                    border: "1px solid rgba(239,68,68,0.2)",
                    cursor: selectedIds.size > 0 ? "pointer" : "default",
                    fontSize: 12, fontWeight: 600,
                  }}
                >
                  🗑 Delete ({selectedIds.size})
                </button>
                <button
                  onClick={clearAllConvos}
                  style={{
                    padding: "6px 10px", borderRadius: 6,
                    background: "rgba(239,68,68,0.08)",
                    color: "#EF4444", border: "1px solid rgba(239,68,68,0.15)",
                    cursor: "pointer", fontSize: 12, fontWeight: 600,
                  }}
                >
                  Clear All
                </button>
              </div>
            )}

            <div className="fs-convo-search-wrap">
              <input
                className="fs-convo-search"
                placeholder="Search chats..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>

            <div className="fs-convo-list">
              {(["pinned", "today", "yesterday", "older"] as const).map(group => {
                const items = groupedConvos[group];
                if (items.length === 0) return null;
                const label = group === "pinned" ? "📌 Pinned" : group.charAt(0).toUpperCase() + group.slice(1);
                return (
                  <div key={group} className="fs-convo-group">
                    <div className="fs-convo-group-label">{label}</div>
                    {items.map(c => (
                      <div key={c.id} className={`fs-convo-item ${activeConvo === c.id ? "active" : ""}`}
                        style={{ display: "flex", alignItems: "center", gap: 8 }}
                      >
                        {selectMode && (
                          <input
                            type="checkbox"
                            checked={selectedIds.has(c.id)}
                            onChange={() => toggleSelect(c.id)}
                            style={{ accentColor: "#E8712C", flexShrink: 0, cursor: "pointer" }}
                          />
                        )}
                        <button
                          style={{ flex: 1, textAlign: "left", background: "none", border: "none", color: "inherit", padding: 0, cursor: "pointer" }}
                          onClick={() => selectMode ? toggleSelect(c.id) : loadConvo(c.id)}
                        >
                          <div className="fs-convo-item-title">{c.title}</div>
                          <div className="fs-convo-item-preview">{c.preview}</div>
                          {c.folder && <span className="fs-convo-folder">{c.folder}</span>}
                        </button>
                        {!selectMode && (
                          <button
                            onClick={(e) => { e.stopPropagation(); deleteConvo(c.id); }}
                            title="Delete chat"
                            className="fs-convo-delete"
                          >
                            🗑
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                );
              })}
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
              <button
                onClick={() => { setKbOpen(!kbOpen); if (!kbOpen) fetchKbFolders(); }}
                title="Knowledge Base"
                style={{
                  background: kbOpen ? "rgba(167,139,250,0.15)" : "rgba(255,255,255,0.03)",
                  border: `1px solid ${kbOpen ? "rgba(167,139,250,0.3)" : "rgba(255,255,255,0.06)"}`,
                  color: kbOpen ? "#A78BFA" : "#4A3D40",
                  borderRadius: 8, padding: "4px 10px", cursor: "pointer",
                  fontSize: 14, fontFamily: "Outfit", transition: "all 0.2s",
                }}
              >
                📚
              </button>
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
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
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
            <div
              className={`fs-input-bar ${isDragging ? 'fs-dragging' : ''}`}
              onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={(e) => {
                e.preventDefault();
                setIsDragging(false);
                handleFileSelect(e.dataTransfer.files);
              }}
            >
              {/* Attached files preview */}
              {attachedFiles.length > 0 && (
                <div style={{
                  display: "flex", gap: 6, padding: "8px 16px 0",
                  flexWrap: "wrap",
                }}>
                  {attachedFiles.map((f, i) => (
                    <div key={i} style={{
                      display: "flex", alignItems: "center", gap: 6,
                      background: "rgba(232,113,44,0.12)",
                      border: "1px solid rgba(232,113,44,0.25)",
                      borderRadius: 8, padding: "4px 10px", fontSize: 12,
                      color: "#E8712C",
                    }}>
                      <span>📎 {f.name.length > 20 ? f.name.slice(0, 18) + '...' : f.name}</span>
                      <span style={{ fontSize: 10, opacity: 0.6 }}>({(f.size / 1024).toFixed(0)}KB)</span>
                      <button onClick={() => removeFile(i)} style={{
                        background: "none", border: "none", color: "#EF4444",
                        cursor: "pointer", fontSize: 14, padding: 0,
                      }}>✕</button>
                    </div>
                  ))}
                </div>
              )}

              {isDragging && (
                <div style={{
                  position: "absolute", inset: 0, borderRadius: 16,
                  background: "rgba(232,113,44,0.08)",
                  border: "2px dashed rgba(232,113,44,0.4)",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  color: "#E8712C", fontSize: 14, fontWeight: 600,
                  zIndex: 10, pointerEvents: "none",
                }}>
                  📎 Drop files here
                </div>
              )}

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
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="fs-voice-btn"
                  title="Attach file"
                  style={{ fontSize: 16 }}
                >
                  📎
                </button>
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  style={{ display: "none" }}
                  onChange={(e) => handleFileSelect(e.target.files)}
                  accept=".txt,.pdf,.csv,.xlsx,.xls,.json,.py,.js,.ts,.md,.pptx,.docx,.png,.jpg,.jpeg,.gif,.webp"
                />
                <textarea
                  ref={inputRef}
                  value={message}
                  onChange={(e) => {
                    setMessage(e.target.value);
                    e.target.style.height = "auto";
                    e.target.style.height = Math.min(e.target.scrollHeight, 200) + "px";
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      handleSend();
                    }
                  }}
                  placeholder={attachedFiles.length > 0 ? `${attachedFiles.length} file(s) attached — add a message...` : `Message ${displayName}...`}
                  className="fs-chat-input"
                  autoFocus
                  rows={1}
                />
                <button onClick={handleSend} disabled={!message.trim() && attachedFiles.length === 0} className="fs-send-btn">▶</button>
              </div>
            </div>
          </div>

          {/* ── Knowledge Base Panel ── */}
          {kbOpen && (
            <div style={{
              width: 320, flexShrink: 0,
              background: "rgba(8,8,14,0.95)", backdropFilter: "blur(20px)",
              borderLeft: "1px solid rgba(255,255,255,0.04)",
              display: "flex", flexDirection: "column",
              animation: "bsSlideIn 0.3s ease",
              overflow: "hidden",
            }}>
              <div style={{
                padding: "16px 18px", borderBottom: "1px solid rgba(255,255,255,0.06)",
                display: "flex", alignItems: "center", justifyContent: "space-between",
              }}>
                <span style={{ fontSize: 14, fontWeight: 800, color: "#A78BFA" }}>📚 Knowledge Base</span>
                <button onClick={() => setKbOpen(false)} style={{
                  background: "none", border: "none", color: "#4A3D30",
                  cursor: "pointer", fontSize: 16,
                }}>✕</button>
              </div>

              {/* Upload area */}
              <div style={{ padding: 14 }}>
                <div style={{
                  border: "2px dashed rgba(167,139,250,0.15)",
                  borderRadius: 12, padding: "20px 16px",
                  textAlign: "center", cursor: "pointer",
                  background: "rgba(167,139,250,0.03)",
                  transition: "all 0.2s",
                }} onClick={() => kbFileRef.current?.click()}>
                  <div style={{ fontSize: 28, marginBottom: 6 }}>{kbUploading ? "⏳" : "📄"}</div>
                  <div style={{ fontSize: 12, color: "#A78BFA", fontWeight: 700 }}>
                    {kbUploading ? "Uploading & indexing..." : "Click to upload documents"}
                  </div>
                  <div style={{ fontSize: 10, color: "#4A3D30", marginTop: 4 }}>
                    PDF, DOCX, CSV, TXT, MD, JSON
                  </div>
                </div>
                <input
                  ref={kbFileRef}
                  type="file"
                  multiple
                  style={{ display: "none" }}
                  accept=".txt,.pdf,.csv,.json,.md,.docx,.xlsx,.py,.js,.ts,.yaml,.yml,.html,.xml"
                  onChange={async (e) => {
                    if (!e.target.files) return;
                    for (const f of Array.from(e.target.files)) {
                      await uploadKbFile(f, kbSelectedFolder);
                    }
                    e.target.value = "";
                  }}
                />

                {/* Folder selector */}
                <div style={{ marginTop: 10, display: "flex", gap: 6 }}>
                  <select
                    value={kbSelectedFolder}
                    onChange={(e) => setKbSelectedFolder(e.target.value)}
                    style={{
                      flex: 1, padding: "6px 10px", borderRadius: 8,
                      background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)",
                      color: "#C4A882", fontSize: 12, fontFamily: "Outfit",
                    }}
                  >
                    <option value="general">📁 general</option>
                    {kbFolders.filter(f => f.name !== "general").map(f => (
                      <option key={f.name} value={f.name}>📁 {f.name}</option>
                    ))}
                  </select>
                </div>

                {/* Create new folder */}
                <div style={{ marginTop: 8, display: "flex", gap: 6 }}>
                  <input
                    value={kbNewFolder}
                    onChange={(e) => setKbNewFolder(e.target.value)}
                    placeholder="New folder name..."
                    onKeyDown={(e) => e.key === "Enter" && createKbFolder()}
                    style={{
                      flex: 1, padding: "6px 10px", borderRadius: 8,
                      background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)",
                      color: "#C4A882", fontSize: 11, fontFamily: "Outfit", outline: "none",
                    }}
                  />
                  <button onClick={createKbFolder} style={{
                    padding: "6px 12px", borderRadius: 8,
                    background: "rgba(167,139,250,0.1)", border: "1px solid rgba(167,139,250,0.2)",
                    color: "#A78BFA", fontSize: 11, fontWeight: 700, cursor: "pointer",
                    fontFamily: "Outfit",
                  }}>+ Add</button>
                </div>
              </div>

              {/* Folder list */}
              <div style={{ flex: 1, overflowY: "auto", padding: "0 14px 14px" }}>
                <div style={{
                  fontSize: 10, fontWeight: 800, color: "#4A3D30",
                  textTransform: "uppercase", letterSpacing: 1.5, marginBottom: 8,
                }}>Your Folders</div>
                {kbFolders.length === 0 ? (
                  <div style={{ fontSize: 11, color: "#3A3530", padding: 12, textAlign: "center" }}>
                    No folders yet. Upload a document to get started!
                  </div>
                ) : kbFolders.map(f => (
                  <div key={f.name} style={{
                    padding: "10px 12px", borderRadius: 10, marginBottom: 6,
                    background: kbSelectedFolder === f.name
                      ? "rgba(167,139,250,0.08)" : "rgba(255,255,255,0.02)",
                    border: `1px solid ${kbSelectedFolder === f.name
                      ? "rgba(167,139,250,0.15)" : "rgba(255,255,255,0.04)"}`,
                    cursor: "pointer", transition: "all 0.2s",
                  }} onClick={() => setKbSelectedFolder(f.name)}>
                    <div style={{ fontSize: 13, fontWeight: 700, color: "#C4A882" }}>
                      📁 {f.name}
                    </div>
                    <div style={{ fontSize: 10, color: "#4A3D30", marginTop: 3 }}>
                      {f.files} file{f.files !== 1 ? "s" : ""} · {f.chunks} chunks indexed
                    </div>
                  </div>
                ))}
              </div>

              <div style={{
                padding: "10px 14px", borderTop: "1px solid rgba(255,255,255,0.04)",
                fontSize: 10, color: "#3A3530", textAlign: "center",
              }}>
                Documents are indexed locally & stored in memory
              </div>
            </div>
          )}
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

// CSS for Hub + Chat lives in globals.css (migrated from inline styles)

// CSS for Hub + Chat lives in globals.css (migrated from inline styles)
