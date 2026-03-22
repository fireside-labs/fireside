"use client";

import { useState } from "react";
import Link from "next/link";
import dynamic from "next/dynamic";
import ErrorBoundary from "@/components/ErrorBoundary";
import VoiceSettings from "@/components/VoiceSettings";
import { API_BASE } from "@/lib/api";
import { useToast } from "@/components/Toast";
import { DiscoveryCard } from "@/components/GuidedTour";

const NodesPage = dynamic(() => import("@/app/nodes/page"), {
    ssr: false,
    loading: () => <div style={{ padding: 20, color: '#5A4D40', fontSize: 13 }}>Loading devices...</div>,
});

type SettingsTab = "general" | "apikeys" | "advanced";

const TABS: { id: SettingsTab; label: string; icon: string }[] = [
    { id: "general", label: "General", icon: "⚙" },
    { id: "apikeys", label: "API Keys", icon: "🔑" },
    { id: "advanced", label: "Advanced", icon: "🔧" },
];

interface ApiProvider {
    id: string; name: string; icon: string; color: string;
    placeholder: string; hint: string;
}

const API_PROVIDERS: ApiProvider[] = [
    { id: "openai", name: "OpenAI", icon: "🤖", color: "#10B981", placeholder: "sk-...", hint: "For GPT-4o cloud fallback" },
    { id: "anthropic", name: "Anthropic", icon: "🧠", color: "#A78BFA", placeholder: "sk-ant-...", hint: "For Claude cloud fallback" },
    { id: "nvidia", name: "NVIDIA NIM", icon: "🟢", color: "#76B900", placeholder: "nvapi-...", hint: "Free tier for cloud models" },
    { id: "telegram", name: "Telegram Bot", icon: "✈", color: "#2AABEE", placeholder: "123456:ABC-...", hint: "From @BotFather" },
    { id: "elevenlabs", name: "ElevenLabs", icon: "🔊", color: "#F472B6", placeholder: "xi-...", hint: "For premium voice synthesis" },
];

export default function SettingsPage() {
    const { toast } = useToast();
    const [tab, setTab] = useState<SettingsTab>("general");
    const [apiKeys, setApiKeys] = useState<Record<string, string>>({});

    const [aiName, setAiName] = useState(() =>
        typeof window !== "undefined" ? localStorage.getItem("fireside_agent_name") || "Atlas" : "Atlas"
    );

    const saveGeneral = () => {
        const trimmed = aiName.trim();
        if (!trimmed) { toast("AI name can't be empty", "error"); return; }
        if (trimmed.length > 40) { toast("Name must be 40 characters or less", "error"); return; }
        setAiName(trimmed);
        localStorage.setItem("fireside_agent_name", trimmed);
        toast("Settings saved!", "success");
    };

    const saveApiKey = async (providerId: string) => {
        const key = apiKeys[providerId];
        if (!key) { toast("Enter a key first", "error"); return; }
        try {
            await fetch(`${API_BASE}/api/v1/config/keys`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ provider: providerId, key }),
            });
            toast(`${API_PROVIDERS.find(p => p.id === providerId)?.name} key saved`, "success");
        } catch {
            toast("Failed to save — is the backend running?", "error");
        }
    };

    return (
        <div className="max-w-2xl mx-auto">
            {/* CSS in globals.css */}

            <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '14px 0', marginBottom: 12, borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                <Link href="/" style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '8px 16px', borderRadius: 10, fontSize: 13, fontWeight: 800, color: '#C4A882', textDecoration: 'none', background: 'rgba(245,158,11,0.06)', border: '1px solid rgba(245,158,11,0.12)', fontFamily: "'Outfit', system-ui" }}>🔥 Hub</Link>
                <span style={{ fontSize: 12, color: '#3A3530', fontWeight: 600, textTransform: 'uppercase' as const, letterSpacing: 1 }}>Settings</span>
            </div>
            <DiscoveryCard pageKey="/config" />
            <div className="mb-6">
                <h1 className="text-2xl font-bold text-white flex items-center gap-2"><span>⚙</span> Settings</h1>
                <p className="text-sm text-[var(--color-rune-dim)] mt-1">API keys, voice, devices, and advanced tools.</p>
            </div>

            <div className="stab-strip">
                {TABS.map((t) => (
                    <button key={t.id} onClick={() => setTab(t.id)}
                        className={`stab-btn ${tab === t.id ? "stab-active" : ""}`}>
                        <span>{t.icon}</span> {t.label}
                    </button>
                ))}
            </div>

            {/* ═══ GENERAL ═══ */}
            {tab === "general" && (
                <div className="space-y-6">
                    <div className="glass-card p-5">
                        <h3 className="text-white font-semibold mb-4">Your AI</h3>
                        <div>
                            <label htmlFor="settings-name" className="text-xs text-[var(--color-rune-dim)] mb-1 block">Name</label>
                            <input id="settings-name" value={aiName} onChange={(e) => setAiName(e.target.value)}
                                className="w-full px-4 py-2.5 rounded-lg bg-[var(--color-glass)] border border-[var(--color-glass-border)] text-white text-sm outline-none focus:border-[var(--color-neon)] transition-colors" />
                        </div>
                    </div>
                    <VoiceSettings />
                    <div className="glass-card p-6">
                        <h2 className="text-lg font-semibold text-white mb-2 flex items-center gap-2"><span>📱</span> Connect Your Phone</h2>
                        <p className="text-sm text-[var(--color-rune-dim)] mb-4">Take your AI companion on the go.</p>
                        <div className="flex items-center gap-4 p-4 rounded-xl bg-[var(--color-void)] border border-[var(--color-glass-border)]">
                            <div className="w-16 h-16 rounded-xl bg-[var(--color-neon-glow)] flex items-center justify-center text-3xl border border-[var(--color-neon)]/20">🔥</div>
                            <div className="flex-1">
                                <p className="text-sm text-white font-medium">Fireside for Mobile</p>
                                <p className="text-xs text-[var(--color-rune-dim)] mt-1">Available on iOS &amp; Android. Syncs automatically.</p>
                            </div>
                        </div>
                    </div>
                    <button className="btn-neon px-6 py-3 text-sm w-full" onClick={saveGeneral}>Save</button>
                </div>
            )}

            {/* ═══ API KEYS ═══ */}
            {tab === "apikeys" && (
                <div className="space-y-5">
                    <p className="text-sm text-[var(--color-rune-dim)]">
                        Add API keys to connect cloud services. Keys are stored locally — never sent anywhere.
                    </p>
                    {API_PROVIDERS.map(provider => (
                        <div key={provider.id} className="ak-card" style={{ "--ak-color": provider.color } as React.CSSProperties}>
                            <div className="ak-header">
                                <span className="ak-icon">{provider.icon}</span>
                                <div><div className="ak-name">{provider.name}</div><div className="ak-hint">{provider.hint}</div></div>
                                {apiKeys[provider.id] && <span className="ak-connected">✓ Connected</span>}
                            </div>
                            <div className="ak-input-row">
                                <input type="password" className="ak-input" placeholder={provider.placeholder}
                                    value={apiKeys[provider.id] || ""}
                                    onChange={(e) => setApiKeys(prev => ({ ...prev, [provider.id]: e.target.value }))} />
                                <button className="ak-save" onClick={() => saveApiKey(provider.id)}>Save</button>
                            </div>
                        </div>
                    ))}
                    <div className="ak-note"><p>🔒 All keys stored locally in your Fireside config.</p></div>
                </div>
            )}

            {/* ═══ ADVANCED ═══ */}
            {tab === "advanced" && (
                <div className="space-y-8">
                    <div>
                        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2"><span>📱</span> Connected Devices</h2>
                        <ErrorBoundary>
                            <NodesPage />
                        </ErrorBoundary>
                    </div>
                    <div className="glass-card p-6">
                        <h2 className="text-lg font-semibold text-white mb-2 flex items-center gap-2"><span>🛠</span> Developer Tools</h2>
                        <p className="text-sm text-[var(--color-rune-dim)] mb-4">Advanced tools for debugging and pipeline management.</p>
                        <div className="grid grid-cols-2 gap-3">
                            {[
                                { label: "War Room", icon: "⚔", href: "/warroom", desc: "Diagnostics" },
                                { label: "Pipeline", icon: "🔗", href: "/pipeline", desc: "Task chains" },
                                { label: "Agents", icon: "👤", href: "/agents/thor", desc: "Mesh agents" },
                                { label: "Debate", icon: "💬", href: "/debate", desc: "Agent debates" },
                            ].map(tool => (
                                <Link key={tool.href} href={tool.href} className="dev-tool-card">
                                    <span className="dev-tool-icon">{tool.icon}</span>
                                    <span className="dev-tool-label">{tool.label}</span>
                                    <span className="dev-tool-desc">{tool.desc}</span>
                                </Link>
                            ))}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

// CSS migrated to globals.css