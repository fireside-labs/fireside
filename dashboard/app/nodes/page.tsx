"use client";

import { useState, useEffect } from "react";
import { getNodes, MeshNode, API_BASE } from "@/lib/api";

// Derive a friendly name from the node's properties or just capitalise the node name
function getFriendlyName(node: MeshNode): string {
    if (node.friendly_name) return node.friendly_name;
    return node.name.charAt(0).toUpperCase() + node.name.slice(1) + "'s Device";
}

const ROLE_MAP: Record<string, string> = {
    orchestrator: "Main AI",
    backend: "Helper",
    memory: "Memory Assistant",
    security: "Security Guard",
    worker: "Helper",
};

// Node-provided names used directly, no hardcoded mapping needed

const BRAIN_ALIASES: Record<string, string> = {
    "llama-3.1-8b": "Smart & Fast",
    "llama-3.1-70b": "Deep Thinker",
    "deepseek-r1": "Deep Thinker",
    "claude-3.5-sonnet": "Cloud Expert",
    "gpt-4o": "Cloud Expert",
};

// Parse uptime string like "4h 23m" to rough days
function uptimeToDays(uptime: string): number {
    const hours = uptime.match(/(\d+)h/);
    const days = uptime.match(/(\d+)d/);
    if (days) return parseInt(days[1]);
    if (hours) return Math.max(1, Math.round(parseInt(hours[1]) / 24));
    return 0;
}

export default function ConnectedDevicesPage() {
    const [nodes, setNodes] = useState<MeshNode[]>([]);
    const [loading, setLoading] = useState(true);
    const [showAdvanced, setShowAdvanced] = useState(false);

    useEffect(() => {
        getNodes().then((data) => {
            // F3: Override first node name with agent name from onboarding
            const agentName = localStorage.getItem("fireside_agent_name");
            if (agentName && data.length > 0 && data[0].name === "fireside") {
                data[0].friendly_name = agentName;
            }
            setNodes(data);
            setLoading(false);
        });
    }, []);

    return (
        <div className="max-w-3xl mx-auto">
            <div className="mb-6">
                <h1 className="text-2xl font-bold text-white flex items-center gap-2">
                    <span>📱</span> Connected Devices
                </h1>
                <p className="text-sm text-[var(--color-rune-dim)] mt-1">
                    Your AI runs on these devices.
                </p>
            </div>

            {loading ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {[1, 2, 3].map((i) => (
                        <div key={i} className="glass-card p-5 animate-pulse h-40" />
                    ))}
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                    {nodes.map((node) => {
                        const friendlyName = node.friendly_name || `${node.name}'s Device`;
                        const friendlyRole = ROLE_MAP[node.role] || node.role;
                        const days = uptimeToDays(node.uptime);

                        return (
                            <div key={node.name} className="glass-card p-5">
                                <div className="flex items-center justify-between mb-3">
                                    <div className="flex items-center gap-3">
                                        <span className="text-2xl">💻</span>
                                        <div>
                                            <h3 className="text-white font-semibold">{friendlyName}</h3>
                                            <p className="text-xs text-[var(--color-rune-dim)]">
                                                Running: {node.name} ({friendlyRole.toLowerCase()})
                                            </p>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <div className={node.status === "online" ? "status-online" : "status-offline"} />
                                        <span className="text-xs text-[var(--color-rune-dim)]">
                                            {node.status === "online" ? "Online" : "Offline"}
                                        </span>
                                    </div>
                                </div>
                                <div className="space-y-1.5 text-sm">
                                    {days > 0 && (
                                        <div className="flex justify-between">
                                            <span className="text-[var(--color-rune-dim)]">Connected since</span>
                                            <span className="text-[var(--color-rune)]">{days} day{days !== 1 ? "s" : ""}</span>
                                        </div>
                                    )}
                                    {node.current_model && (
                                        <div className="flex justify-between">
                                            <span className="text-[var(--color-rune-dim)]">Brain</span>
                                            <span className="text-[var(--color-rune)]">{BRAIN_ALIASES[node.current_model] || node.current_model}</span>
                                        </div>
                                    )}
                                </div>
                                {showAdvanced && (
                                    <div className="mt-3 pt-3 border-t border-[var(--color-glass-border)] text-xs text-[var(--color-rune-dim)]">
                                        <div className="flex justify-between"><span>Role</span><span>{node.role}</span></div>
                                        <div className="flex justify-between"><span>IP</span><span>{node.ip}:{node.port}</span></div>
                                        <div className="flex justify-between"><span>Uptime</span><span>{node.uptime}</span></div>
                                    </div>
                                )}
                            </div>
                        );
                    })}

                    {/* Add device CTA card */}
                    <div
                        className="glass-card p-5 flex flex-col items-center justify-center text-center cursor-pointer hover:border-[var(--color-neon)] transition-colors"
                        style={{ borderStyle: "dashed" }}
                        onClick={async () => {
                            try {
                                const res = await fetch(`${API_BASE}/mesh/join-token`, { method: "POST" });
                                if (res.ok) {
                                    const data = await res.json();
                                    const token = data.token || data.join_token || "N/A";
                                    window.prompt("Share this token with your other device to join the mesh:", token);
                                } else {
                                    alert("Could not generate a join token. Make sure the backend is running.");
                                }
                            } catch {
                                alert("Backend unreachable. Start Fireside on this computer first.");
                            }
                        }}
                    >
                        <span className="text-3xl mb-3">➕</span>
                        <h3 className="text-white font-semibold mb-1">Add another device</h3>
                        <p className="text-xs text-[var(--color-rune-dim)]">
                            Make your AI faster by adding a second computer.
                        </p>
                    </div>
                </div>
            )}

            <button
                onClick={() => setShowAdvanced(!showAdvanced)}
                className="text-xs text-[var(--color-rune-dim)] hover:text-[var(--color-rune)] transition-colors"
            >
                {showAdvanced ? "▾ Hide" : "▸ Show"} advanced details
            </button>
        </div>
    );
}
