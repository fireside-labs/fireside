"use client";

import { useState } from "react";

type SetupStep = "create" | "token" | "notifications" | "done";

const NOTIFICATION_OPTIONS = [
    { id: "task-complete", label: "Task completed", desc: "When your AI finishes a task", default: true },
    { id: "task-help", label: "Task needs help", desc: "When your AI gets stuck and needs guidance", default: true },
    { id: "learning", label: "Learning updates", desc: "When your AI discovers something new", default: false },
    { id: "system", label: "System alerts", desc: "If a device goes offline or there's an error", default: true },
];

export default function TelegramSetup() {
    const [step, setStep] = useState<SetupStep>("create");
    const [token, setToken] = useState("");
    const [verifying, setVerifying] = useState(false);
    const [verified, setVerified] = useState(false);
    const [notifications, setNotifications] = useState<string[]>(
        NOTIFICATION_OPTIONS.filter(n => n.default).map(n => n.id)
    );
    const [testSent, setTestSent] = useState(false);

    const toggleNotif = (id: string) => {
        setNotifications(prev => prev.includes(id) ? prev.filter(n => n !== id) : [...prev, id]);
    };

    const verifyToken = () => {
        if (!token.trim()) return;
        setVerifying(true);
        // Simulate verification
        setTimeout(() => {
            setVerifying(false);
            setVerified(true);
            setStep("notifications");
        }, 1500);
    };

    const sendTest = () => {
        setTestSent(true);
        setTimeout(() => setTestSent(false), 3000);
    };

    if (step === "done") {
        return (
            <div className="glass-card p-5">
                <div className="flex items-center justify-between mb-3">
                    <h3 className="text-white font-semibold flex items-center gap-2">
                        💬 Telegram
                    </h3>
                    <span className="text-xs px-2 py-1 rounded-full bg-[var(--color-neon-glow)] text-[var(--color-neon)]">
                        🟢 Connected
                    </span>
                </div>
                <p className="text-xs text-[var(--color-rune-dim)] mb-3">
                    Your AI sends notifications to Telegram and responds to messages there.
                </p>
                <div className="flex gap-2">
                    <button onClick={sendTest} className="text-xs text-[var(--color-neon)] hover:underline">
                        {testSent ? "✅ Test sent!" : "Send test message"}
                    </button>
                    <button
                        onClick={() => setStep("notifications")}
                        className="text-xs text-[var(--color-rune-dim)] hover:text-white transition-colors"
                    >
                        Edit notifications
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="glass-card p-5">
            <h3 className="text-white font-semibold mb-1 flex items-center gap-2">
                💬 Telegram
            </h3>
            <p className="text-xs text-[var(--color-rune-dim)] mb-4">
                Connect Telegram to chat with your AI and get push notifications.
            </p>

            {/* Step indicator */}
            <div className="flex items-center gap-2 mb-5">
                {["create", "token", "notifications"].map((s, i) => (
                    <div key={s} className="flex items-center gap-2">
                        <div
                            className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold"
                            style={{
                                background: step === s ? "var(--color-neon)" : (["create", "token", "notifications"].indexOf(step) > i ? "var(--color-neon-dim)" : "var(--color-glass)"),
                                color: step === s || ["create", "token", "notifications"].indexOf(step) > i ? "black" : "var(--color-rune-dim)",
                            }}
                        >
                            {["create", "token", "notifications"].indexOf(step) > i ? "✓" : i + 1}
                        </div>
                        {i < 2 && <div className="w-8 h-0.5 bg-[var(--color-glass-border)]" />}
                    </div>
                ))}
            </div>

            {/* Step 1: Create bot */}
            {step === "create" && (
                <div>
                    <h4 className="text-sm text-white font-medium mb-2">Step 1: Create a Telegram bot</h4>
                    <div className="bg-[var(--color-glass)] rounded-lg p-4 text-xs text-[var(--color-rune)] space-y-2 mb-4">
                        <p>1. Open Telegram and search for <strong className="text-white">@BotFather</strong></p>
                        <p>2. Send <code className="text-[var(--color-neon)] bg-[var(--color-void)] px-1.5 py-0.5 rounded">/newbot</code></p>
                        <p>3. Choose a name (e.g. &quot;My Valhalla AI&quot;)</p>
                        <p>4. Copy the bot token it gives you</p>
                    </div>
                    <button onClick={() => setStep("token")} className="btn-neon px-5 py-2 text-sm">
                        I have my token →
                    </button>
                </div>
            )}

            {/* Step 2: Paste token */}
            {step === "token" && (
                <div>
                    <h4 className="text-sm text-white font-medium mb-2">Step 2: Paste your bot token</h4>
                    <div className="flex gap-2 mb-3">
                        <input
                            value={token}
                            onChange={(e) => setToken(e.target.value)}
                            placeholder="123456789:ABCdefGHIjklMNOpqrsTUVwxyz..."
                            className="flex-1 px-4 py-2.5 rounded-lg bg-[var(--color-glass)] border border-[var(--color-glass-border)] text-white text-sm outline-none focus:border-[var(--color-neon)] transition-colors placeholder-[var(--color-rune-dim)] font-mono"
                        />
                        <button
                            onClick={verifyToken}
                            disabled={verifying || !token.trim()}
                            className="btn-neon px-5 py-2 text-sm disabled:opacity-50"
                        >
                            {verifying ? "Verifying..." : "Verify"}
                        </button>
                    </div>
                    <button
                        onClick={() => setStep("create")}
                        className="text-xs text-[var(--color-rune-dim)] hover:text-white transition-colors"
                    >
                        ← Back
                    </button>
                </div>
            )}

            {/* Step 3: Choose notifications */}
            {step === "notifications" && (
                <div>
                    <h4 className="text-sm text-white font-medium mb-3">Step 3: Choose notifications</h4>
                    <div className="space-y-3 mb-4">
                        {NOTIFICATION_OPTIONS.map((n) => (
                            <div key={n.id} className="flex items-center justify-between">
                                <div>
                                    <p className="text-sm text-white">{n.label}</p>
                                    <p className="text-xs text-[var(--color-rune-dim)]">{n.desc}</p>
                                </div>
                                <button
                                    onClick={() => toggleNotif(n.id)}
                                    role="switch"
                                    aria-checked={notifications.includes(n.id)}
                                    aria-label={n.label}
                                    className="w-12 h-6 rounded-full transition-all relative"
                                    style={{
                                        background: notifications.includes(n.id) ? "var(--color-neon)" : "var(--color-glass-border)",
                                    }}
                                >
                                    <div
                                        className="w-5 h-5 rounded-full bg-white absolute top-0.5 transition-all"
                                        style={{ left: notifications.includes(n.id) ? 26 : 2 }}
                                    />
                                </button>
                            </div>
                        ))}
                    </div>
                    <div className="flex gap-2">
                        <button onClick={() => setStep("done")} className="btn-neon px-5 py-2 text-sm">
                            Finish Setup
                        </button>
                        <button onClick={sendTest} className="px-5 py-2 text-sm text-[var(--color-rune-dim)] hover:text-white border border-[var(--color-glass-border)] rounded-lg transition-colors">
                            {testSent ? "✅ Sent!" : "Send test message"}
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
