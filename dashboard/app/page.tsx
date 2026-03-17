"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import EmberParticles from "@/components/EmberParticles";
import { playWhoosh, playTick } from "@/components/FiresideSounds";

/* ═══════════════════════════════════════════════════════════════════
   Campfire Hub — Pixel Art Scene v2
   Uses standalone companion images + CSS campfire
   ═══════════════════════════════════════════════════════════════════ */

const SPECIES_EMOJI: Record<string, string> = {
  cat: "🐱", dog: "🐶", penguin: "🐧", fox: "🦊", owl: "🦉", dragon: "🐉",
};

const NAV_ITEMS = [
  { id: "chat",      icon: "/hub/icon_chat.png", label: "Chat",      href: null },
  { id: "brains",    icon: "/hub/icon_brain.png", label: "Brains",    href: "/brains" },
  { id: "settings",  icon: "/hub/icon_settings.png", label: "Settings",  href: "/config" },
  { id: "companion", icon: "/hub/icon_companion.png", label: "Companion", href: "/companion" },
];

const GREETINGS = [
  "What should we talk about?",
  "I'm ready when you are!",
  "The fire's warm tonight...",
  "Got any questions for me?",
  "Pull up a log and let's chat!",
];

export default function CampfireHub() {
  const [message, setMessage] = useState("");
  const [userName, setUserName] = useState("");
  const [agentName, setAgentName] = useState("Atlas");
  const [species, setSpecies] = useState("fox");
  const [companionName, setCompanionName] = useState("");
  const [chatHistory, setChatHistory] = useState<{ role: string; content: string }[]>([]);
  const [hasBrain, setHasBrain] = useState(true);
  const [isTyping, setIsTyping] = useState(false);
  const [activeView, setActiveView] = useState<"hub" | "chat">("hub");
  const [greeting] = useState(() => GREETINGS[Math.floor(Math.random() * GREETINGS.length)]);
  const [showBubble, setShowBubble] = useState(true);
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
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatHistory]);

  const handleSend = async () => {
    if (!message.trim()) return;
    const userMessage = message.trim();
    setChatHistory(prev => [...prev, { role: "user", content: userMessage }]);
    setMessage("");
    setIsTyping(true);
    setShowBubble(false);

    if (activeView !== "chat") {
      setActiveView("chat");
      playWhoosh();
    }

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
        content: data.response || data.content || "I received your message.",
      }]);
    } catch {
      setChatHistory(prev => [...prev, {
        role: "assistant",
        content: "I'm not connected right now. Check that your brain is running.",
      }]);
    } finally {
      setIsTyping(false);
    }
  };

  const companionImg = `/companions/${species}_happy.png`;
  const displayName = companionName || agentName;

  return (
    <div className="cfh-root">
      <style>{hubCSS}</style>
      <EmberParticles intensity={25} className="cfh-embers" />

      {/* ═══════ HUB SCENE ═══════ */}
      {activeView === "hub" && (
        <div className="cfh-scene">
          {/* Stars */}
          <div className="cfh-stars">
            {Array.from({ length: 40 }).map((_, i) => (
              <div key={i} className="cfh-star" style={{
                left: `${Math.random() * 100}%`,
                top: `${Math.random() * 65}%`,
                animationDelay: `${Math.random() * 5}s`,
                animationDuration: `${2 + Math.random() * 3}s`,
              }} />
            ))}
          </div>

          {/* Nav icons arranged in semi-circle */}
          <div className="cfh-nav-ring">
            {NAV_ITEMS.map((item, i) => {
              const btn = (
                <button
                  className="cfh-nav-btn"
                  onClick={() => {
                    playTick();
                    if (item.id === "chat") inputRef.current?.focus();
                  }}
                  style={{ animationDelay: `${0.3 + i * 0.12}s` }}
                >
                  <div className="cfh-nav-orb">
                    <img src={item.icon} alt={item.label} className="cfh-nav-icon-img" />
                  </div>
                  <span className="cfh-nav-label">{item.label}</span>
                </button>
              );
              if (item.href) {
                return (
                  <Link key={item.id} href={item.href} onClick={() => playWhoosh()}>
                    {btn}
                  </Link>
                );
              }
              return <div key={item.id}>{btn}</div>;
            })}
          </div>

          {/* Campfire + Companion scene */}
          <div className="cfh-scene-center">
            {/* Campfire art */}
            <div className="cfh-fire-container">
              <img src="/hub/campfire.png" alt="Campfire" className="cfh-campfire-img" />
              <div className="cfh-fire-glow" />
            </div>

            {/* Companion image */}
            <div className="cfh-companion-area">
              <img
                src="/hub/fox.png"
                alt={species}
                className="cfh-companion-img"
              />
              {/* Speech bubble */}
              {showBubble && (
                <div className="cfh-bubble">
                  <p className="cfh-bubble-text">
                    Hey{userName ? ` ${userName}` : ""}! {greeting}
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* No brain warning */}
          {!hasBrain && (
            <div className="cfh-no-brain">
              <Link href="/brains">
                <button className="cfh-btn-gold" onClick={() => playWhoosh()}>
                  Set Up Brain →
                </button>
              </Link>
            </div>
          )}

          {/* Chat input */}
          <div className="cfh-input-area">
            <div className="cfh-input-wrap">
              <input
                ref={inputRef}
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSend()}
                placeholder="Message your companion..."
                className="cfh-input"
                onFocus={() => setShowBubble(false)}
              />
              <button onClick={handleSend} disabled={!message.trim()} className="cfh-send">
                ▶
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ═══════ CHAT SCENE ═══════ */}
      {activeView === "chat" && (
        <div className="cfh-chat">
          <div className="cfh-chat-header">
            <button className="cfh-chat-back" onClick={() => { playWhoosh(); setActiveView("hub"); }}>
              ← Hub
            </button>
            <img src={companionImg} alt={species} className="cfh-chat-avatar"
              onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} />
            <div>
              <p className="cfh-chat-name">{displayName}</p>
              <p className="cfh-chat-status">{isTyping ? "thinking..." : "at the fireside"}</p>
            </div>
          </div>

          <div className="cfh-messages">
            {chatHistory.map((msg, i) => (
              <div key={i} className={`cfh-msg ${msg.role === "user" ? "cfh-msg-user" : "cfh-msg-ai"}`}>
                {msg.role === "assistant" && (
                  <img src={companionImg} alt="" className="cfh-msg-av"
                    onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} />
                )}
                <div className={`cfh-bbl ${msg.role === "user" ? "cfh-bbl-user" : "cfh-bbl-ai"}`}>
                  {msg.content}
                </div>
              </div>
            ))}
            {isTyping && (
              <div className="cfh-msg cfh-msg-ai">
                <img src={companionImg} alt="" className="cfh-msg-av" />
                <div className="cfh-bbl cfh-bbl-ai cfh-typing">
                  <span className="cfh-dot" /><span className="cfh-dot" /><span className="cfh-dot" />
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          <div className="cfh-chat-input-bar">
            <div className="cfh-input-wrap">
              <input
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSend()}
                placeholder={`Message ${displayName}...`}
                className="cfh-input"
                autoFocus
              />
              <button onClick={handleSend} disabled={!message.trim()} className="cfh-send">▶</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ════════════════════════════════════════════════════════════════════
// CSS
// ════════════════════════════════════════════════════════════════════

const hubCSS = `
  .cfh-root {
    min-height: 100vh; width: 100%;
    background: #080810;
    font-family: 'Outfit', 'Inter', system-ui, sans-serif;
    color: #F0DCC8;
    position: relative; overflow: hidden;
  }
  .cfh-embers { position: fixed !important; inset: 0 !important; z-index: 1 !important; }

  /* ── Stars ── */
  .cfh-stars { position: fixed; inset: 0; z-index: 0; pointer-events: none; }
  .cfh-star {
    position: absolute; width: 2px; height: 2px;
    background: #FFF; border-radius: 50%;
    animation: twinkle ease-in-out infinite alternate;
    opacity: 0.3;
  }
  @keyframes twinkle {
    0% { opacity: 0.1; transform: scale(0.5); }
    100% { opacity: 0.6; transform: scale(1.3); }
  }

  /* ══ HUB SCENE ══ */
  .cfh-scene {
    min-height: 100vh; width: 100%;
    display: flex; flex-direction: column;
    align-items: center; justify-content: flex-end;
    position: relative; z-index: 5;
    padding-bottom: 28px;
    animation: fadeUp 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards;
  }
  @keyframes fadeUp {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
  }

  /* ── Nav ring ── */
  .cfh-nav-ring {
    display: flex; gap: 40px;
    justify-content: center;
    margin-bottom: 20px;
    z-index: 10;
  }
  .cfh-nav-ring a { text-decoration: none; }
  .cfh-nav-btn {
    display: flex; flex-direction: column;
    align-items: center; gap: 8px;
    background: none; border: none; cursor: pointer;
    animation: navPop 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) both;
    transition: transform 0.3s, filter 0.3s;
  }
  .cfh-nav-btn:hover {
    transform: translateY(-8px) scale(1.08);
    filter: brightness(1.3);
  }
  @keyframes navPop {
    from { opacity: 0; transform: translateY(30px) scale(0.5); }
    to { opacity: 1; transform: translateY(0) scale(1); }
  }
  .cfh-nav-orb {
    width: 72px; height: 72px;
    border-radius: 50%;
    background: radial-gradient(circle at 30% 30%,
      rgba(251,191,36,0.15) 0%,
      rgba(217,119,6,0.06) 50%,
      rgba(10,10,15,0.8) 100%);
    border: 1.5px solid rgba(251,191,36,0.15);
    display: flex; align-items: center; justify-content: center;
    box-shadow:
      0 0 30px rgba(251,191,36,0.08),
      inset 0 0 20px rgba(251,191,36,0.05);
    transition: all 0.3s;
    animation: orbFloat 5s ease-in-out infinite;
  }
  .cfh-nav-btn:nth-child(1) .cfh-nav-orb { animation-delay: 0s; }
  .cfh-nav-btn:nth-child(2) .cfh-nav-orb { animation-delay: 1.2s; }
  .cfh-nav-btn:nth-child(3) .cfh-nav-orb { animation-delay: 2.5s; }
  .cfh-nav-btn:nth-child(4) .cfh-nav-orb { animation-delay: 3.8s; }
  @keyframes orbFloat {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-6px); }
  }
  .cfh-nav-btn:hover .cfh-nav-orb {
    border-color: rgba(251,191,36,0.4);
    box-shadow: 0 0 40px rgba(251,191,36,0.2), inset 0 0 30px rgba(251,191,36,0.1);
  }

  .cfh-nav-label {
    font-size: 11px; font-weight: 700; color: #7A6A5A;
    text-transform: uppercase; letter-spacing: 1.5px;
    transition: color 0.2s;
  }
  .cfh-nav-btn:hover .cfh-nav-label { color: #FBBF24; }

  /* ── Fire + Companion scene center ── */
  .cfh-scene-center {
    display: flex; align-items: flex-end; justify-content: center;
    gap: 0; position: relative;
    margin-bottom: 24px; z-index: 5;
  }

  /* Campfire art image */
  .cfh-fire-container {
    position: relative;
    width: 180px; height: 180px;
    display: flex; align-items: center; justify-content: center;
  }
  .cfh-campfire-img {
    width: 160px; height: 160px;
    object-fit: contain;
    animation: fireBreath 3s ease-in-out infinite;
    filter: drop-shadow(0 0 30px rgba(251,191,36,0.3));
  }
  @keyframes fireBreath {
    0%, 100% { transform: scale(1); filter: drop-shadow(0 0 30px rgba(251,191,36,0.3)); }
    50% { transform: scale(1.03); filter: drop-shadow(0 0 40px rgba(251,191,36,0.45)); }
  }
  .cfh-fire-glow {
    position: absolute; bottom: -20px; left: 50%; transform: translateX(-50%);
    width: 300px; height: 150px;
    background: radial-gradient(ellipse,
      rgba(251,191,36,0.12) 0%,
      rgba(217,119,6,0.05) 40%,
      transparent 70%);
    pointer-events: none;
    animation: glowPulse 3s ease-in-out infinite alternate;
  }
  @keyframes glowPulse {
    0% { opacity: 0.7; } 100% { opacity: 1; }
  }
  .cfh-nav-icon-img {
    width: 40px; height: 40px;
    object-fit: contain;
    filter: drop-shadow(0 0 8px rgba(251,191,36,0.15));
  }

  /* Companion */
  .cfh-companion-area {
    position: relative;
    display: flex; flex-direction: column;
    align-items: center;
    margin-left: -10px;
  }
  .cfh-companion-img {
    width: 130px; height: 130px;
    image-rendering: pixelated;
    object-fit: contain;
    filter: drop-shadow(0 0 20px rgba(251,191,36,0.15));
    animation: companionBob 4s ease-in-out infinite;
  }
  @keyframes companionBob {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-5px); }
  }

  /* Speech bubble */
  .cfh-bubble {
    position: absolute; top: -50px; right: -100px;
    background: rgba(18,18,26,0.92);
    backdrop-filter: blur(16px);
    border: 1.5px solid rgba(251,191,36,0.2);
    border-radius: 14px;
    padding: 10px 14px;
    max-width: 200px;
    z-index: 15;
    animation: bubIn 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) 1s both;
    box-shadow: 0 8px 32px rgba(0,0,0,0.5);
  }
  .cfh-bubble::after {
    content: ''; position: absolute; bottom: 8px; left: -6px;
    width: 10px; height: 10px;
    background: rgba(18,18,26,0.92);
    border-left: 1.5px solid rgba(251,191,36,0.2);
    border-bottom: 1.5px solid rgba(251,191,36,0.2);
    transform: rotate(45deg);
  }
  @keyframes bubIn {
    from { opacity: 0; transform: scale(0.6) translateY(8px); }
    to { opacity: 1; transform: scale(1) translateY(0); }
  }
  .cfh-bubble-text { font-size: 12px; color: #D0C0A8; margin: 0; line-height: 1.4; }

  /* No brain */
  .cfh-no-brain { margin-bottom: 12px; z-index: 10; }
  .cfh-btn-gold {
    padding: 12px 36px; border-radius: 12px; border: none; cursor: pointer;
    background: linear-gradient(135deg, #D97706, #F59E0B);
    color: #0A0A0A; font-size: 14px; font-weight: 800;
    box-shadow: 0 4px 24px rgba(245,158,11,0.25);
    transition: all 0.3s;
  }
  .cfh-btn-gold:hover { transform: translateY(-2px); box-shadow: 0 8px 32px rgba(245,158,11,0.4); }

  /* Input */
  .cfh-input-area { width: 100%; max-width: 480px; padding: 0 24px; z-index: 10; }
  .cfh-input-wrap { width: 100%; position: relative; }
  .cfh-input {
    width: 100%; padding: 14px 48px 14px 18px;
    border-radius: 14px;
    background: rgba(18,18,26,0.7);
    backdrop-filter: blur(12px);
    border: 1.5px solid rgba(255,255,255,0.06);
    color: #F0DCC8; font-size: 14px; font-weight: 500; outline: none;
    transition: all 0.3s;
  }
  .cfh-input:focus {
    border-color: rgba(217,119,6,0.3);
    box-shadow: 0 0 20px rgba(245,158,11,0.08);
  }
  .cfh-input::placeholder { color: rgba(240,220,200,0.2); }
  .cfh-send {
    position: absolute; right: 5px; top: 50%; transform: translateY(-50%);
    width: 34px; height: 34px; border-radius: 10px;
    background: linear-gradient(135deg, #D97706, #F59E0B);
    border: none; cursor: pointer;
    color: #0A0A0A; font-size: 14px; font-weight: 900;
    display: flex; align-items: center; justify-content: center;
    transition: all 0.2s; opacity: 0.7;
  }
  .cfh-send:hover:not(:disabled) { opacity: 1; transform: translateY(-50%) scale(1.05); }
  .cfh-send:disabled { opacity: 0.15; cursor: default; }

  /* ══ CHAT SCENE ══ */
  .cfh-chat {
    min-height: 100vh; width: 100%;
    display: flex; flex-direction: column;
    max-width: 640px; margin: 0 auto; padding: 0 16px;
    position: relative; z-index: 5;
    animation: fadeUp 0.5s ease forwards;
  }
  .cfh-chat-header {
    display: flex; align-items: center; gap: 12px;
    padding: 16px 0; border-bottom: 1px solid rgba(255,255,255,0.04);
  }
  .cfh-chat-back {
    background: none; border: 1px solid rgba(255,255,255,0.06);
    color: #7A6A5A; font-size: 12px; font-weight: 600; cursor: pointer;
    padding: 6px 14px; border-radius: 8px; transition: all 0.2s;
  }
  .cfh-chat-back:hover { color: #F0DCC8; border-color: rgba(217,119,6,0.3); }
  .cfh-chat-avatar {
    width: 36px; height: 36px; border-radius: 10px;
    image-rendering: pixelated; object-fit: contain;
    background: rgba(251,191,36,0.06);
  }
  .cfh-chat-name { font-size: 15px; font-weight: 700; color: #F0DCC8; margin: 0; }
  .cfh-chat-status { font-size: 10px; color: #5A4D40; margin: 0; }

  .cfh-messages {
    flex: 1; overflow-y: auto; padding: 20px 0;
    display: flex; flex-direction: column; gap: 12px;
    max-height: calc(100vh - 160px);
  }
  .cfh-messages::-webkit-scrollbar { width: 3px; }
  .cfh-messages::-webkit-scrollbar-thumb { background: rgba(245,158,11,0.15); border-radius: 2px; }

  .cfh-msg {
    display: flex; gap: 10px;
    animation: msgSlide 0.3s cubic-bezier(0.16, 1, 0.3, 1) both;
  }
  @keyframes msgSlide { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
  .cfh-msg-user { justify-content: flex-end; }
  .cfh-msg-ai { justify-content: flex-start; align-items: flex-start; }
  .cfh-msg-av {
    width: 28px; height: 28px; border-radius: 8px; flex-shrink: 0;
    image-rendering: pixelated; object-fit: contain;
    background: rgba(245,158,11,0.06); margin-top: 2px;
  }
  .cfh-bbl {
    max-width: 75%; padding: 10px 14px;
    border-radius: 14px; font-size: 13px; line-height: 1.5;
  }
  .cfh-bbl-user {
    background: rgba(217,119,6,0.1); border: 1px solid rgba(245,158,11,0.1);
    color: #F0DCC8; border-bottom-right-radius: 4px;
  }
  .cfh-bbl-ai {
    background: rgba(18,18,26,0.6); backdrop-filter: blur(8px);
    border: 1px solid rgba(255,255,255,0.03);
    color: #B0A090; border-bottom-left-radius: 4px;
  }
  .cfh-typing { display: flex; gap: 4px; align-items: center; padding: 14px 18px; }
  .cfh-dot {
    width: 5px; height: 5px; border-radius: 50%; background: #5A4D40;
    animation: dotPulse 1.4s ease-in-out infinite;
  }
  .cfh-dot:nth-child(2) { animation-delay: 0.2s; }
  .cfh-dot:nth-child(3) { animation-delay: 0.4s; }
  @keyframes dotPulse { 0%, 60%, 100% { transform: translateY(0); opacity: 0.4; } 30% { transform: translateY(-3px); opacity: 1; } }
  .cfh-chat-input-bar { padding: 12px 0 20px; border-top: 1px solid rgba(255,255,255,0.04); }
`;
