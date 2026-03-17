"use client";

import { useState, useEffect, useRef } from "react";
import { API_BASE } from "../lib/api";
import AvatarSprite from "@/components/AvatarSprite";
import CompanionConnectionAnim from "@/components/CompanionConnectionAnim";
import type { PetSpecies } from "@/components/CompanionSim";
import type { ConnectionState } from "@/components/CompanionConnectionAnim";

interface CompanionChatProps {
    species: PetSpecies;
    petName: string;
    mood: number;
}

interface Message {
    role: "user" | "pet";
    content: string;
}

// Mood affects response style
function getMoodPrefix(species: PetSpecies, mood: number): string {
    if (mood > 70) {
        const happy: Record<PetSpecies, string> = {
            cat: "*purrs* ", dog: "*tail wagging* ", penguin: "*adjusts bowtie* ",
            fox: "*grins* ", owl: "*eyes bright* ", dragon: "*smoke rings* ",
        };
        return happy[species];
    }
    if (mood < 30) {
        const sad: Record<PetSpecies, string> = {
            cat: "*yawns* ", dog: "*whimpers* ", penguin: "*sighs formally* ",
            fox: "*ears flat* ", owl: "*drowsy* ", dragon: "*smoke fizzles* ",
        };
        return sad[species];
    }
    return "";
}

const PET_RESPONSES: Record<PetSpecies, string[]> = {
    cat: [
        "I suppose I can answer that. Don't expect enthusiasm.",
        "Fine. The answer is probably what you already thought. You're welcome.",
        "I could help with that... or I could nap. Let me think.",
        "That's a simple one. Even a kitten could figure it out.",
        "Interesting. Not really, but I'll humor you.",
    ],
    dog: [
        "OH WOW GREAT QUESTION!! Let me think... YES! I can help!!",
        "You're the BEST for asking me! Here's what I think!!",
        "I LOVE this question!! Almost as much as walks!!",
        "OH OH OH I KNOW THIS ONE!! Let me tell you!!",
        "This is SO FUN!! Okay okay okay, here's my answer:",
    ],
    penguin: [
        "A reasonable inquiry. Allow me to consult my records.",
        "Per established protocol, the answer would be as follows.",
        "I have reviewed this matter. My assessment is forthcoming.",
        "An astute question. I shall respond with appropriate formality.",
        "Noted. Processing. One moment, if you please.",
    ],
    fox: [
        "Ooh, now that's an interesting one... let me think about this sideways.",
        "I know the obvious answer, but what if we tried something sneakier?",
        "Ha! I was hoping you'd ask something like this. Picture this...",
        "The straightforward answer is boring. Here's the clever one:",
        "Between you and me? Here's what I'd actually do...",
    ],
    owl: [
        "Before I answer, let me ask — why do you want to know?",
        "Hmm. There are layers to this question. Let us examine them.",
        "I've pondered this before, actually. Here's what wisdom suggests.",
        "A good question reveals more about the asker than the answer.",
        "Let me think on this carefully. The obvious answer is rarely the true one.",
    ],
    dragon: [
        "THE ANSWER IS CLEAR! Allow me to ILLUMINATE it for you!",
        "HA! A worthy question! I shall respond with APPROPRIATE GRANDEUR!",
        "OBVIOUSLY I know the answer. I am a DRAGON. We know everything.",
        "By fire and scale, here is the DEFINITIVE answer!",
        "Such questions are BENEATH me but I shall answer ANYWAY because I'm generous!",
    ],
};

// Phone tasks the companion can help with
const PHONE_TASKS = [
    "📸 Clean up photos", "📱 Organize apps", "📝 Draft a text",
    "⏰ Set a reminder", "🧮 Quick math", "🌤️ What should I wear?",
];

export default function CompanionChat({ species, petName, mood }: CompanionChatProps) {
    const [messages, setMessages] = useState<Message[]>([
        { role: "pet", content: `${getMoodPrefix(species, mood)}Hey! I'm ${petName}. What's up?` },
    ]);
    const [input, setInput] = useState("");
    const [typing, setTyping] = useState(false);
    const [isOnline, setIsOnline] = useState(true);
    const [connectionState, setConnectionState] = useState<ConnectionState>("connected");
    const chatRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (chatRef.current) chatRef.current.scrollTop = chatRef.current.scrollHeight;
    }, [messages]);

    // Detect online/offline
    useEffect(() => {
        const goOnline = () => { setIsOnline(true); setConnectionState("connected"); };
        const goOffline = () => { setIsOnline(false); setConnectionState("offline"); };
        window.addEventListener("online", goOnline);
        window.addEventListener("offline", goOffline);
        setIsOnline(navigator.onLine);
        if (!navigator.onLine) setConnectionState("offline");
        return () => { window.removeEventListener("online", goOnline); window.removeEventListener("offline", goOffline); };
    }, []);

    const handleSend = async () => {
        if (!input.trim() || typing) return;
        const userMsg = input.trim();
        setMessages((prev) => [...prev, { role: "user", content: userMsg }]);
        setInput("");
        setTyping(true);

        const prefix = getMoodPrefix(species, mood);

        try {
            // Try real backend first
            const res = await fetch(`${API_BASE}/api/v1/chat`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: userMsg, species, mood }),
            });

            if (res.ok) {
                const data = await res.json();
                const reply = prefix + (data.response || data.content || "...");
                setMessages((prev) => [...prev, { role: "pet", content: reply }]);
                setTyping(false);
                return;
            }
        } catch {
            // Backend unreachable — use canned responses
        }

        // Fallback to canned responses
        await new Promise((r) => setTimeout(r, 800 + Math.random() * 800));
        const responses = PET_RESPONSES[species];
        const response = prefix + responses[Math.floor(Math.random() * responses.length)];
        setMessages((prev) => [...prev, { role: "pet", content: response }]);
        setTyping(false);
    };

    return (
        <div className="glass-card p-0 overflow-hidden flex flex-col" style={{ maxHeight: 480 }}>
            {/* Header */}
            <div className="p-3 border-b border-[var(--color-glass-border)] flex items-center gap-3">
                <AvatarSprite
                    config={{ style: "emoji", emoji: undefined, hairStyle: 0, hairColor: "#333", skinTone: "#fad7a0", outfit: species, accessory: "none" }}
                    size={36}
                />
                <div className="flex-1">
                    <p className="text-sm text-white font-medium">{petName}</p>
                    <p className="text-[9px] text-[var(--color-rune-dim)]">
                        {isOnline ? "🟢 Home PC connected" : "✈️ Offline — using local brain"}
                    </p>
                </div>
                {mood < 30 && <span className="text-xs" title="Your companion is unhappy!">😢</span>}
            </div>

            {/* Connection state */}
            <div className="px-3 pt-2">
                <CompanionConnectionAnim species={species} petName={petName} connectionState={connectionState} />
            </div>

            {/* Messages */}
            <div ref={chatRef} className="flex-1 overflow-y-auto p-3 space-y-2">
                {messages.map((msg, i) => (
                    <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                        <div className={`max-w-[80%] rounded-2xl px-3 py-2 text-xs ${msg.role === "user"
                            ? "bg-[var(--color-neon-glow)] text-[var(--color-neon)] border border-[rgba(0,255,136,0.15)]"
                            : "glass-card text-[var(--color-rune)]"
                            }`}>
                            {msg.role === "pet" && <span className="text-[9px] text-[var(--color-rune-dim)] block mb-0.5">{petName}</span>}
                            <p className="leading-relaxed">{msg.content}</p>
                        </div>
                    </div>
                ))}
                {typing && (
                    <div className="flex justify-start">
                        <div className="glass-card rounded-2xl px-3 py-2">
                            <div className="flex gap-1">
                                <span className="typing-dot" /><span className="typing-dot" style={{ animationDelay: "0.15s" }} /><span className="typing-dot" style={{ animationDelay: "0.3s" }} />
                            </div>
                        </div>
                    </div>
                )}
            </div>

            {/* Quick phone tasks */}
            {messages.length <= 2 && (
                <div className="px-3 pb-1">
                    <p className="text-[9px] text-[var(--color-rune-dim)] mb-1">📱 Quick tasks I can do on your phone:</p>
                    <div className="flex flex-wrap gap-1">
                        {PHONE_TASKS.map((task) => (
                            <button
                                key={task}
                                onClick={() => setInput(task.slice(2))}
                                className="text-[9px] px-2 py-1 rounded-full bg-[var(--color-glass)] text-[var(--color-rune-dim)] hover:text-white hover:bg-[var(--color-glass-hover)] transition-colors"
                            >
                                {task}
                            </button>
                        ))}
                    </div>
                </div>
            )}

            {/* Input */}
            <div className="p-3 border-t border-[var(--color-glass-border)] flex gap-2">
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleSend()}
                    placeholder={`Talk to ${petName}...`}
                    className="flex-1 bg-transparent text-white placeholder-[var(--color-rune-dim)] text-sm outline-none"
                    disabled={typing}
                />
                <button onClick={handleSend} disabled={!input.trim() || typing} className="btn-neon text-xs px-3 py-1.5" style={{ opacity: !input.trim() || typing ? 0.4 : 1 }}>
                    {typing ? "⏳" : "Send"}
                </button>
            </div>
        </div>
    );
}
