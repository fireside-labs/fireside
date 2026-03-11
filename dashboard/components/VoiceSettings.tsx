"use client";

import { useState } from "react";

interface Voice {
    id: string;
    name: string;
    accent: string;
    preview: string; // simulated
}

const VOICES: Voice[] = [
    { id: "aria", name: "Aria", accent: "American", preview: "Hi, I'm Aria. I can help you with anything." },
    { id: "nova", name: "Nova", accent: "British", preview: "Hello, I'm Nova. Shall we get started?" },
    { id: "kai", name: "Kai", accent: "Neutral", preview: "Hey, I'm Kai. What are you working on?" },
    { id: "luna", name: "Luna", accent: "Australian", preview: "G'day, I'm Luna. Let's get cracking." },
    { id: "zephyr", name: "Zephyr", accent: "Calm", preview: "Hi there, I'm Zephyr. Take your time." },
];

export default function VoiceSettings() {
    const [enabled, setEnabled] = useState(false);
    const [selectedVoice, setSelectedVoice] = useState("aria");
    const [volume, setVolume] = useState(80);
    const [speed, setSpeed] = useState(100);
    const [playing, setPlaying] = useState<string | null>(null);
    const [testing, setTesting] = useState(false);

    const playPreview = (voiceId: string) => {
        setPlaying(voiceId);
        setTimeout(() => setPlaying(null), 2000);
    };

    const testVoice = () => {
        setTesting(true);
        setTimeout(() => setTesting(false), 3000);
    };

    return (
        <div className="glass-card p-5">
            <div className="flex items-center justify-between mb-4">
                <h3 className="text-white font-semibold flex items-center gap-2">
                    🎤 Voice
                </h3>
                <div className="flex items-center gap-2">
                    {enabled && (
                        <span className="text-[10px] text-[var(--color-warning)]">~1.5 GB AI Memory</span>
                    )}
                    <button
                        onClick={() => setEnabled(!enabled)}
                        role="switch"
                        aria-checked={enabled}
                        aria-label="Enable voice"
                        className="w-12 h-6 rounded-full transition-all relative"
                        style={{ background: enabled ? "var(--color-neon)" : "var(--color-glass-border)" }}
                    >
                        <div
                            className="w-5 h-5 rounded-full bg-white absolute top-0.5 transition-all"
                            style={{ left: enabled ? 26 : 2 }}
                        />
                    </button>
                </div>
            </div>

            {!enabled && (
                <p className="text-xs text-[var(--color-rune-dim)]">
                    Enable voice to talk to your AI using your microphone and hear spoken responses.
                    Uses ~1.5 GB of AI memory for speech recognition.
                </p>
            )}

            {enabled && (
                <div className="space-y-4">
                    {/* Voice picker */}
                    <div>
                        <p className="text-xs text-[var(--color-rune-dim)] mb-2">Choose a voice:</p>
                        <div className="space-y-1.5">
                            {VOICES.map((v) => (
                                <div
                                    key={v.id}
                                    className="flex items-center justify-between p-2.5 rounded-lg cursor-pointer transition-colors"
                                    role="radio"
                                    aria-checked={selectedVoice === v.id}
                                    tabIndex={0}
                                    onClick={() => setSelectedVoice(v.id)}
                                    onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setSelectedVoice(v.id); } }}
                                    style={{
                                        background: selectedVoice === v.id ? "var(--color-neon-glow)" : "transparent",
                                        borderLeft: selectedVoice === v.id ? "2px solid var(--color-neon)" : "2px solid transparent",
                                    }}
                                >
                                    <div>
                                        <span className="text-sm text-white font-medium">{v.name}</span>
                                        <span className="text-xs text-[var(--color-rune-dim)] ml-2">{v.accent}</span>
                                    </div>
                                    <button
                                        onClick={(e) => { e.stopPropagation(); playPreview(v.id); }}
                                        className="text-xs text-[var(--color-neon)] hover:underline"
                                    >
                                        {playing === v.id ? "🔊 Playing..." : "▶ Preview"}
                                    </button>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Volume */}
                    <div>
                        <label htmlFor="voice-volume" className="text-xs text-[var(--color-rune-dim)] block mb-1">
                            Volume: {volume}%
                        </label>
                        <input
                            id="voice-volume"
                            type="range"
                            min="0"
                            max="100"
                            value={volume}
                            onChange={(e) => setVolume(Number(e.target.value))}
                            className="w-full h-1.5 rounded-full appearance-none bg-[var(--color-glass)] accent-[var(--color-neon)]"
                        />
                    </div>

                    {/* Speed */}
                    <div>
                        <label htmlFor="voice-speed" className="text-xs text-[var(--color-rune-dim)] block mb-1">
                            Speed: {speed}%
                        </label>
                        <input
                            id="voice-speed"
                            type="range"
                            min="50"
                            max="200"
                            value={speed}
                            onChange={(e) => setSpeed(Number(e.target.value))}
                            className="w-full h-1.5 rounded-full appearance-none bg-[var(--color-glass)] accent-[var(--color-neon)]"
                        />
                    </div>

                    {/* Test */}
                    <button
                        onClick={testVoice}
                        className="text-sm text-[var(--color-neon)] hover:underline"
                    >
                        {testing ? "🔊 Speaking..." : "🔊 Test voice"}
                    </button>
                </div>
            )}
        </div>
    );
}
