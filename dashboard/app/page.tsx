"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import SpriteCharacter, { COMPANION_SHEETS } from "@/components/SpriteCharacter";

interface CompanionState {
    species: string;
    name: string;
    owner: string;
}

const SPECIES_EMOJI: Record<string, string> = {
    cat: "🐱", dog: "🐶", penguin: "🐧", fox: "🦊", owl: "🦉", dragon: "🐉",
};

const SUGGESTED_PROMPTS = [
    { text: "Take me for a walk", icon: "🌿" },
    { text: "Remember: I like my coffee black", icon: "☕" },
    { text: "Translate 'good morning' to Japanese", icon: "🌸" },
];

export default function ChatHomePage() {
    const [message, setMessage] = useState("");
    const [userName, setUserName] = useState("");
    const [agentName, setAgentName] = useState("Atlas");
    const [companion, setCompanion] = useState<CompanionState | null>(null);
    const [chatHistory, setChatHistory] = useState<{ role: string; content: string }[]>([]);
    const [hasBrain, setHasBrain] = useState(true);
    const [isTyping, setIsTyping] = useState(false);
    const chatEndRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const name = localStorage.getItem("fireside_user_name") || "";
        const agent = localStorage.getItem("fireside_agent_name") || "Atlas";
        setUserName(name);
        setAgentName(agent);
        try {
            const stored = localStorage.getItem("fireside_companion");
            if (stored) setCompanion(JSON.parse(stored));
        } catch { /* no companion yet */ }
        const model = localStorage.getItem("fireside_model");
        setHasBrain(!!model);
    }, []);

    useEffect(() => {
        chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [chatHistory]);

    const handleSend = async () => {
        if (!message.trim() || !hasBrain) return;
        const userMessage = message.trim();
        setChatHistory(prev => [...prev, { role: "user", content: userMessage }]);
        setMessage("");
        setIsTyping(true);

        try {
            const res = await fetch("http://127.0.0.1:8765/api/v1/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: userMessage, stream: false }),
            });
            if (!res.ok) throw new Error(`API error: ${res.status}`);
            const data = await res.json();
            setChatHistory(prev => [...prev, {
                role: "assistant",
                content: data.response || data.content || "I received your message but couldn't generate a response.",
            }]);
        } catch {
            setChatHistory(prev => [...prev, {
                role: "assistant",
                content: "I'm not connected right now. Check that your brain is running in Settings.",
            }]);
        } finally {
            setIsTyping(false);
        }
    };

    const companionSheet = companion ? (COMPANION_SHEETS[companion.species] || COMPANION_SHEETS.fox) : null;
    const companionEmoji = companion ? (SPECIES_EMOJI[companion.species] || "🦊") : "🔥";
    const hasHistory = chatHistory.length > 0;

    return (
        <div className="fireside-dashboard">
            <style>{dashboardCSS}</style>

            {/* ── Ambient atmosphere (ported from installer) ── */}
            <div className="fireside-ambient" />
            <div className="fireside-particles" />
            <div className="fireside-vignette" />

            {/* ══════════════════════════════════════════════════════ */}
            {/* HERO STATE — no chat history                          */}
            {/* ══════════════════════════════════════════════════════ */}
            {!hasHistory && (
                <div className="fireside-hero">
                    {/* Companion — center stage */}
                    <div className="fireside-hero-companion">
                        {companionSheet ? (
                            <SpriteCharacter sheet={companionSheet} action="idle" scale={5} />
                        ) : (
                            <span className="fireside-hero-emoji">{companionEmoji}</span>
                        )}
                        {companion && (
                            <p className="fireside-companion-name">{companion.name}</p>
                        )}
                    </div>

                    {/* Greeting */}
                    <h1 className="fireside-greeting">
                        Hi{userName ? ` ${userName}` : " there"} <span className="fireside-fire">🔥</span>
                    </h1>
                    <p className="fireside-status">
                        {hasBrain
                            ? `${agentName} is at the fireside`
                            : "Almost there — download a brain to begin"
                        }
                    </p>

                    {/* No brain → download button */}
                    {!hasBrain && (
                        <Link href="/brains">
                            <button className="fireside-btn-primary">
                                Download Brain →
                            </button>
                        </Link>
                    )}

                    {/* Has brain → input + suggestions */}
                    {hasBrain && (
                        <div className="fireside-hero-input-area">
                            {/* Suggested prompts as floating pills */}
                            <div className="fireside-pills">
                                {SUGGESTED_PROMPTS.map((p) => (
                                    <button
                                        key={p.text}
                                        className="fireside-pill"
                                        onClick={() => { setMessage(p.text); }}
                                    >
                                        <span>{p.icon}</span> {p.text}
                                    </button>
                                ))}
                            </div>

                            {/* Glowing input */}
                            <div className="fireside-input-wrap">
                                <input
                                    value={message}
                                    onChange={(e) => setMessage(e.target.value)}
                                    onKeyDown={(e) => e.key === "Enter" && handleSend()}
                                    placeholder={`Say something to ${agentName}...`}
                                    className="fireside-input"
                                    autoFocus
                                />
                                <button
                                    onClick={handleSend}
                                    disabled={!message.trim()}
                                    className="fireside-send"
                                >
                                    ↑
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* ══════════════════════════════════════════════════════ */}
            {/* CHAT STATE — has messages                             */}
            {/* ══════════════════════════════════════════════════════ */}
            {hasHistory && (
                <div className="fireside-chat">
                    {/* Compact header */}
                    <div className="fireside-chat-header">
                        <div className="fireside-chat-companion-small">
                            {companionSheet ? (
                                <SpriteCharacter sheet={companionSheet} action="idle" scale={2} />
                            ) : (
                                <span style={{ fontSize: 28 }}>{companionEmoji}</span>
                            )}
                        </div>
                        <div>
                            <p className="fireside-chat-title">{agentName}</p>
                            <p className="fireside-chat-subtitle">{companion ? `${companion.name} is listening` : "at the fireside"}</p>
                        </div>
                    </div>

                    {/* Messages */}
                    <div className="fireside-messages">
                        {chatHistory.map((msg, i) => (
                            <div
                                key={i}
                                className={`fireside-msg ${msg.role === "user" ? "fireside-msg-user" : "fireside-msg-ai"}`}
                                style={{ animationDelay: `${Math.min(i * 0.05, 0.3)}s` }}
                            >
                                {msg.role === "assistant" && (
                                    <span className="fireside-msg-avatar">{companionEmoji}</span>
                                )}
                                <div className={`fireside-bubble ${msg.role === "user" ? "fireside-bubble-user" : "fireside-bubble-ai"}`}>
                                    {msg.content}
                                </div>
                            </div>
                        ))}
                        {isTyping && (
                            <div className="fireside-msg fireside-msg-ai">
                                <span className="fireside-msg-avatar">{companionEmoji}</span>
                                <div className="fireside-bubble fireside-bubble-ai fireside-typing">
                                    <span className="fireside-dot" /><span className="fireside-dot" /><span className="fireside-dot" />
                                </div>
                            </div>
                        )}
                        <div ref={chatEndRef} />
                    </div>

                    {/* Chat input — pinned bottom */}
                    <div className="fireside-chat-input-bar">
                        <div className="fireside-input-wrap">
                            <input
                                value={message}
                                onChange={(e) => setMessage(e.target.value)}
                                onKeyDown={(e) => e.key === "Enter" && handleSend()}
                                placeholder={`Message ${agentName}...`}
                                className="fireside-input"
                                autoFocus
                            />
                            <button
                                onClick={handleSend}
                                disabled={!message.trim()}
                                className="fireside-send"
                            >
                                ↑
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

// ─── Embedded CSS — fireside design language ─────────────────────────────────

const dashboardCSS = `
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

  .fireside-dashboard {
    position: relative;
    min-height: calc(100vh - 60px);
    display: flex;
    flex-direction: column;
    font-family: 'Inter', var(--font-family-body), sans-serif;
    overflow: hidden;
  }

  /* ── Ambient glow (from installer) ── */
  .fireside-ambient {
    position: fixed; inset: 0; pointer-events: none; z-index: 0;
    background:
      radial-gradient(ellipse 600px 400px at 50% 80%, rgba(217,119,6,0.10) 0%, transparent 70%),
      radial-gradient(ellipse 300px 300px at 30% 20%, rgba(245,158,11,0.05) 0%, transparent 60%),
      radial-gradient(ellipse 200px 200px at 75% 30%, rgba(146,64,14,0.06) 0%, transparent 60%);
    animation: ambientPulse 8s ease-in-out infinite alternate;
  }
  @keyframes ambientPulse {
    0% { opacity: 0.6; transform: scale(1); }
    100% { opacity: 1; transform: scale(1.05); }
  }

  /* ── Fire particles ── */
  .fireside-particles {
    position: fixed; bottom: 0; left: 0; right: 0; height: 300px;
    pointer-events: none; z-index: 0; opacity: 0.25;
    background:
      radial-gradient(2px 2px at 20% 90%, #F59E0B, transparent),
      radial-gradient(2px 2px at 40% 85%, #D97706, transparent),
      radial-gradient(2px 2px at 60% 92%, #F59E0B, transparent),
      radial-gradient(2px 2px at 80% 88%, #D97706, transparent),
      radial-gradient(3px 3px at 10% 95%, #F59E0B, transparent),
      radial-gradient(3px 3px at 50% 80%, #92400E, transparent),
      radial-gradient(2px 2px at 70% 93%, #F59E0B, transparent),
      radial-gradient(1px 1px at 25% 75%, #F59E0B, transparent),
      radial-gradient(1px 1px at 55% 70%, #D97706, transparent),
      radial-gradient(1px 1px at 85% 78%, #F59E0B, transparent);
    background-size: 100% 100%;
    animation: particleRise 4s ease-in-out infinite;
  }
  @keyframes particleRise {
    0% { transform: translateY(0) scaleY(1); opacity: 0.25; }
    50% { transform: translateY(-30px) scaleY(1.1); opacity: 0.4; }
    100% { transform: translateY(0) scaleY(1); opacity: 0.25; }
  }

  /* ── Vignette ── */
  .fireside-vignette {
    position: fixed; inset: 0; pointer-events: none; z-index: 0;
    background: radial-gradient(ellipse at center, transparent 50%, rgba(0,0,0,0.5) 100%);
  }

  /* ═══════════════════════════════════ */
  /* HERO STATE                          */
  /* ═══════════════════════════════════ */
  .fireside-hero {
    flex: 1; display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    padding: 40px 24px 32px;
    position: relative; z-index: 5;
    animation: heroEnter 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards;
  }
  @keyframes heroEnter {
    from { opacity: 0; transform: translateY(30px) scale(0.97); filter: blur(6px); }
    to { opacity: 1; transform: translateY(0) scale(1); filter: blur(0); }
  }

  .fireside-hero-companion {
    margin-bottom: 24px;
    animation: companionFloat 4s ease-in-out infinite;
    filter: drop-shadow(0 8px 32px rgba(245,158,11,0.2));
  }
  @keyframes companionFloat {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-8px); }
  }
  .fireside-hero-emoji {
    font-size: 96px; display: block;
    filter: drop-shadow(0 0 40px rgba(245,158,11,0.4));
  }
  .fireside-companion-name {
    text-align: center; font-size: 12px; font-weight: 600;
    color: #7A6A5A; letter-spacing: 2px; text-transform: uppercase;
    margin-top: 8px;
  }

  .fireside-greeting {
    font-size: 42px; font-weight: 900; color: #F0DCC8;
    text-align: center; margin-bottom: 8px; letter-spacing: -0.5px;
    text-shadow: 0 2px 20px rgba(245,158,11,0.15);
  }
  .fireside-fire {
    display: inline-block;
    animation: fireGlow 2s ease-in-out infinite;
  }
  @keyframes fireGlow {
    0%, 100% { filter: drop-shadow(0 0 8px rgba(245,158,11,0.5)); transform: scale(1); }
    50% { filter: drop-shadow(0 0 16px rgba(245,158,11,0.8)); transform: scale(1.1); }
  }
  .fireside-status {
    font-size: 14px; color: #7A6A5A; text-align: center;
    letter-spacing: 1px; text-transform: uppercase; font-weight: 500;
    margin-bottom: 32px;
  }

  /* Primary button (from installer) */
  .fireside-btn-primary {
    padding: 16px 48px; border-radius: 14px; border: none; cursor: pointer;
    background: linear-gradient(135deg, #D97706, #F59E0B);
    color: #0A0A0A; font-size: 16px; font-weight: 800; letter-spacing: 1px;
    text-transform: uppercase;
    box-shadow: 0 4px 24px rgba(245,158,11,0.3), inset 0 1px 0 rgba(255,255,255,0.2);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative; overflow: hidden;
  }
  .fireside-btn-primary:hover {
    transform: translateY(-2px) scale(1.02);
    box-shadow: 0 8px 32px rgba(245,158,11,0.5), inset 0 1px 0 rgba(255,255,255,0.3);
  }

  /* ── Suggested prompts — floating glass pills ── */
  .fireside-hero-input-area {
    width: 100%; max-width: 560px;
    display: flex; flex-direction: column; align-items: center; gap: 16px;
  }
  .fireside-pills {
    display: flex; flex-wrap: wrap; gap: 8px; justify-content: center;
  }
  .fireside-pill {
    display: flex; align-items: center; gap: 6px;
    padding: 10px 18px; border-radius: 100px;
    background: rgba(26,26,26,0.6);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255,255,255,0.06);
    color: #A09080; font-size: 13px; font-weight: 500;
    cursor: pointer; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    white-space: nowrap;
  }
  .fireside-pill:hover {
    border-color: rgba(217,119,6,0.3);
    color: #F0DCC8;
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(0,0,0,0.3);
  }

  /* ── Input (from installer) ── */
  .fireside-input-wrap {
    width: 100%; position: relative;
  }
  .fireside-input {
    width: 100%; padding: 16px 52px 16px 20px;
    border-radius: 16px;
    background: rgba(26,26,26,0.7);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255,255,255,0.06);
    color: #F0DCC8; font-size: 15px; font-weight: 500;
    outline: none;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  }
  .fireside-input:focus {
    border-color: rgba(217,119,6,0.4);
    box-shadow: 0 0 24px rgba(245,158,11,0.12), inset 0 0 20px rgba(217,119,6,0.03);
  }
  .fireside-input::placeholder { color: #3A3028; }
  .fireside-send {
    position: absolute; right: 6px; top: 50%; transform: translateY(-50%);
    width: 36px; height: 36px; border-radius: 10px;
    background: linear-gradient(135deg, #D97706, #F59E0B);
    border: none; cursor: pointer;
    color: #0A0A0A; font-size: 18px; font-weight: 900;
    display: flex; align-items: center; justify-content: center;
    transition: all 0.2s;
    opacity: 0.8;
  }
  .fireside-send:hover:not(:disabled) { opacity: 1; transform: translateY(-50%) scale(1.05); }
  .fireside-send:disabled { opacity: 0.2; cursor: default; }

  /* ═══════════════════════════════════ */
  /* CHAT STATE                          */
  /* ═══════════════════════════════════ */
  .fireside-chat {
    flex: 1; display: flex; flex-direction: column;
    position: relative; z-index: 5;
    max-width: 680px; width: 100%; margin: 0 auto;
    padding: 0 16px;
    animation: heroEnter 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards;
  }

  .fireside-chat-header {
    display: flex; align-items: center; gap: 12px;
    padding: 16px 0; border-bottom: 1px solid rgba(255,255,255,0.04);
  }
  .fireside-chat-companion-small {
    filter: drop-shadow(0 2px 8px rgba(245,158,11,0.2));
  }
  .fireside-chat-title {
    font-size: 16px; font-weight: 700; color: #F0DCC8; margin: 0;
  }
  .fireside-chat-subtitle {
    font-size: 11px; color: #7A6A5A; margin: 0; letter-spacing: 0.5px;
  }

  /* ── Messages ── */
  .fireside-messages {
    flex: 1; overflow-y: auto; padding: 20px 0;
    display: flex; flex-direction: column; gap: 12px;
    max-height: calc(100vh - 220px);
  }

  .fireside-msg {
    display: flex; gap: 10px;
    animation: msgSlideIn 0.4s cubic-bezier(0.16, 1, 0.3, 1) both;
  }
  @keyframes msgSlideIn {
    from { opacity: 0; transform: translateY(12px); filter: blur(2px); }
    to { opacity: 1; transform: translateY(0); filter: blur(0); }
  }
  .fireside-msg-user { justify-content: flex-end; }
  .fireside-msg-ai { justify-content: flex-start; align-items: flex-start; }
  .fireside-msg-avatar {
    font-size: 20px; flex-shrink: 0;
    width: 32px; height: 32px;
    display: flex; align-items: center; justify-content: center;
    background: rgba(245,158,11,0.08);
    border-radius: 10px; margin-top: 2px;
  }

  .fireside-bubble {
    max-width: 75%; padding: 12px 16px;
    border-radius: 18px; font-size: 14px; line-height: 1.5;
  }
  .fireside-bubble-user {
    background: rgba(217,119,6,0.12);
    border: 1px solid rgba(245,158,11,0.15);
    color: #F0DCC8;
    border-bottom-right-radius: 6px;
  }
  .fireside-bubble-ai {
    background: rgba(26,26,26,0.6);
    backdrop-filter: blur(8px);
    border: 1px solid rgba(255,255,255,0.04);
    color: #C0B0A0;
    border-bottom-left-radius: 6px;
  }

  /* Typing indicator */
  .fireside-typing {
    display: flex; gap: 4px; align-items: center;
    padding: 14px 18px;
  }
  .fireside-dot {
    width: 6px; height: 6px; border-radius: 50%;
    background: #7A6A5A;
    animation: typingBounce 1.4s ease-in-out infinite;
  }
  .fireside-dot:nth-child(2) { animation-delay: 0.2s; }
  .fireside-dot:nth-child(3) { animation-delay: 0.4s; }
  @keyframes typingBounce {
    0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
    30% { transform: translateY(-4px); opacity: 1; }
  }

  /* ── Chat input bar ── */
  .fireside-chat-input-bar {
    padding: 12px 0 20px;
    border-top: 1px solid rgba(255,255,255,0.04);
  }

  /* ── Scrollbar ── */
  .fireside-messages::-webkit-scrollbar { width: 4px; }
  .fireside-messages::-webkit-scrollbar-track { background: transparent; }
  .fireside-messages::-webkit-scrollbar-thumb { background: rgba(245,158,11,0.15); border-radius: 2px; }
`;
