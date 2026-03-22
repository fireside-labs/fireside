"use client";

import { useState, useEffect, useCallback } from "react";
import { getNodes, MeshNode, API_BASE } from "@/lib/api";
import { useToast } from "@/components/Toast";

/* ═══════════════════════════════════════════════════════════════════
   Connected Devices — Mesh Node Management
   Shows current devices, join token flow, and node removal.
   ═══════════════════════════════════════════════════════════════════ */

const ROLE_MAP: Record<string, string> = {
    orchestrator: "Main AI",
    backend: "Helper",
    memory: "Memory",
    security: "Security",
    worker: "Worker",
    courier: "Courier",
};

function uptimeToDays(uptime: string): number {
    const days = uptime.match(/(\d+)d/);
    const hours = uptime.match(/(\d+)h/);
    if (days) return parseInt(days[1]);
    if (hours) return Math.max(1, Math.round(parseInt(hours[1]) / 24));
    return 0;
}

export default function ConnectedDevicesPage() {
    const { toast } = useToast();
    const [nodes, setNodes] = useState<MeshNode[]>([]);
    const [loading, setLoading] = useState(true);
    const [showAdvanced, setShowAdvanced] = useState(false);

    // Join token modal state
    const [showJoinModal, setShowJoinModal] = useState(false);
    const [joinCode, setJoinCode] = useState("");
    const [joinExpiry, setJoinExpiry] = useState(0);
    const [joinLoading, setJoinLoading] = useState(false);

    // Remove node confirm modal
    const [removeTarget, setRemoveTarget] = useState<string | null>(null);

    const loadNodes = useCallback(async () => {
        try {
            const data = await getNodes();
            const agentName = localStorage.getItem("fireside_agent_name");
            if (agentName && data.length > 0 && data[0].name === "fireside") {
                data[0].friendly_name = agentName;
            }
            setNodes(data);
        } catch {
            // Backend offline
        }
        setLoading(false);
    }, []);

    useEffect(() => { loadNodes(); }, [loadNodes]);

    // Generate join token
    const handleAddDevice = async () => {
        setJoinLoading(true);
        try {
            const res = await fetch(`${API_BASE}/api/v1/mesh/join-token`, { method: "POST" });
            if (res.ok) {
                const data = await res.json();
                // Build join code: TOKEN@IP:PORT
                const token = data.token || "N/A";
                const orch = data.orchestrator || "127.0.0.1:8765";
                setJoinCode(`${token}@${orch}`);
                setJoinExpiry(data.expires_in_seconds || 900);
                setShowJoinModal(true);
            } else {
                toast("Could not generate join token. Is the backend running?", "error");
            }
        } catch {
            toast("Backend unreachable. Start Fireside first.", "error");
        }
        setJoinLoading(false);
    };

    // Remove a node
    const handleRemoveNode = async (name: string) => {
        try {
            const res = await fetch(`${API_BASE}/api/v1/nodes/${name}`, { method: "DELETE" });
            if (res.ok) {
                toast(`${name} removed from mesh`, "success");
                setRemoveTarget(null);
                loadNodes();
            } else {
                const data = await res.json().catch(() => ({}));
                toast(data.detail || "Failed to remove node", "error");
            }
        } catch {
            toast("Backend unreachable", "error");
        }
    };

    // Copy to clipboard
    const copyToClipboard = (text: string) => {
        navigator.clipboard.writeText(text).then(() => {
            toast("Copied to clipboard!", "success");
        }).catch(() => {
            toast("Failed to copy", "error");
        });
    };

    const thisNode = nodes.find(n => n.is_self);
    const otherNodes = nodes.filter(n => !n.is_self);

    return (
        <div className="max-w-3xl mx-auto">
            {/* CSS in globals.css — class prefix: nd- */}

            <div className="mb-6">
                <h1 className="text-2xl font-bold text-white flex items-center gap-2">
                    <span>📱</span> Connected Devices
                </h1>
                <p className="text-sm text-[var(--color-rune-dim)] mt-1">
                    {nodes.length === 0
                        ? "Connect another device to make your AI faster."
                        : `Your AI runs on ${nodes.length} device${nodes.length !== 1 ? "s" : ""}.`}
                </p>
            </div>

            {loading ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {[1, 2].map((i) => (
                        <div key={i} className="glass-card p-5 animate-pulse h-40" />
                    ))}
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                    {/* This device */}
                    {thisNode && (
                        <div className="glass-card p-5" style={{ borderColor: "var(--color-neon)", borderWidth: 1 }}>
                            <div className="flex items-center justify-between mb-3">
                                <div className="flex items-center gap-3">
                                    <span className="text-2xl">💻</span>
                                    <div>
                                        <h3 className="text-white font-semibold">
                                            {thisNode.friendly_name || `${thisNode.name}`}
                                        </h3>
                                        <p className="text-xs text-[var(--color-rune-dim)]">
                                            This device · {ROLE_MAP[thisNode.role] || thisNode.role}
                                        </p>
                                    </div>
                                </div>
                                <div className="flex items-center gap-2">
                                    <div className="status-online" />
                                    <span className="text-xs text-[var(--color-neon)]">Online</span>
                                </div>
                            </div>
                            <div className="space-y-1.5 text-sm">
                                {thisNode.current_model && (
                                    <div className="flex justify-between">
                                        <span className="text-[var(--color-rune-dim)]">Brain</span>
                                        <span className="text-[var(--color-rune)]">{thisNode.current_model}</span>
                                    </div>
                                )}
                                {uptimeToDays(thisNode.uptime) > 0 && (
                                    <div className="flex justify-between">
                                        <span className="text-[var(--color-rune-dim)]">Connected</span>
                                        <span className="text-[var(--color-rune)]">{uptimeToDays(thisNode.uptime)} day{uptimeToDays(thisNode.uptime) !== 1 ? "s" : ""}</span>
                                    </div>
                                )}
                            </div>
                            {showAdvanced && (
                                <div className="mt-3 pt-3 border-t border-[var(--color-glass-border)] text-xs text-[var(--color-rune-dim)]">
                                    <div className="flex justify-between"><span>Role</span><span>{thisNode.role}</span></div>
                                    <div className="flex justify-between"><span>IP</span><span>{thisNode.ip}:{thisNode.port}</span></div>
                                    <div className="flex justify-between"><span>Uptime</span><span>{thisNode.uptime}</span></div>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Other devices */}
                    {otherNodes.map((node) => (
                        <div key={node.name} className="glass-card p-5">
                            <div className="flex items-center justify-between mb-3">
                                <div className="flex items-center gap-3">
                                    <span className="text-2xl">💻</span>
                                    <div>
                                        <h3 className="text-white font-semibold">{node.friendly_name || node.name}</h3>
                                        <p className="text-xs text-[var(--color-rune-dim)]">
                                            {ROLE_MAP[node.role] || node.role}
                                        </p>
                                    </div>
                                </div>
                                <div className="flex items-center gap-2">
                                    <div className={node.status === "online" ? "status-online" : "status-offline"} />
                                    <span className="text-xs text-[var(--color-rune-dim)]">
                                        {node.status === "online" ? "Online" : node.status === "offline" ? "Offline" : "Unknown"}
                                    </span>
                                </div>
                            </div>
                            <div className="space-y-1.5 text-sm">
                                {node.current_model && (
                                    <div className="flex justify-between">
                                        <span className="text-[var(--color-rune-dim)]">Brain</span>
                                        <span className="text-[var(--color-rune)]">{node.current_model}</span>
                                    </div>
                                )}
                            </div>
                            {showAdvanced && (
                                <div className="mt-3 pt-3 border-t border-[var(--color-glass-border)] text-xs text-[var(--color-rune-dim)]">
                                    <div className="flex justify-between"><span>Role</span><span>{node.role}</span></div>
                                    <div className="flex justify-between"><span>IP</span><span>{node.ip}:{node.port}</span></div>
                                </div>
                            )}
                            <button
                                className="mt-3 text-xs px-3 py-1 rounded border border-[var(--color-danger)] text-[var(--color-danger)] hover:bg-[rgba(255,68,102,0.12)] transition-colors"
                                onClick={() => setRemoveTarget(node.name)}
                            >
                                Remove
                            </button>
                        </div>
                    ))}

                    {/* Add device CTA card */}
                    <div
                        className="glass-card p-5 flex flex-col items-center justify-center text-center cursor-pointer hover:border-[var(--color-neon)] transition-colors"
                        style={{ borderStyle: "dashed" }}
                        onClick={handleAddDevice}
                    >
                        {joinLoading ? (
                            <span className="text-sm text-[var(--color-rune-dim)]">Generating token...</span>
                        ) : (
                            <>
                                <span className="text-3xl mb-3">➕</span>
                                <h3 className="text-white font-semibold mb-1">Add another device</h3>
                                <p className="text-xs text-[var(--color-rune-dim)]">
                                    Make your AI faster by adding a second computer.
                                </p>
                            </>
                        )}
                    </div>
                </div>
            )}

            <button
                onClick={() => setShowAdvanced(!showAdvanced)}
                className="text-xs text-[var(--color-rune-dim)] hover:text-[var(--color-rune)] transition-colors"
            >
                {showAdvanced ? "▾ Hide" : "▸ Show"} advanced details
            </button>

            {/* ── Join Token Modal ── */}
            {showJoinModal && (
                <div className="nd-modal-overlay" onClick={() => setShowJoinModal(false)}>
                    <div className="nd-modal" onClick={e => e.stopPropagation()}>
                        <h2 className="text-white text-lg font-semibold mb-2">🔗 Add Device</h2>
                        <p className="text-sm text-[var(--color-rune-dim)] mb-4">
                            On your other device, open Fireside and go to <strong className="text-white">Settings → Join Mesh</strong>, then paste this code:
                        </p>

                        <div className="nd-token-box">
                            <code className="nd-token-code">{joinCode}</code>
                            <button
                                className="nd-copy-btn"
                                onClick={() => copyToClipboard(joinCode)}
                            >
                                📋 Copy
                            </button>
                        </div>

                        <div className="nd-token-meta">
                            <span>Expires in {Math.round(joinExpiry / 60)} minutes</span>
                        </div>

                        <div className="nd-modal-actions">
                            <button
                                className="nd-modal-btn nd-btn-secondary"
                                onClick={() => setShowJoinModal(false)}
                            >
                                Done
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* ── Remove Node Confirm Modal ── */}
            {removeTarget && (
                <div className="nd-modal-overlay" onClick={() => setRemoveTarget(null)}>
                    <div className="nd-modal" onClick={e => e.stopPropagation()}>
                        <h2 className="text-white text-lg font-semibold mb-2">Remove Device</h2>
                        <p className="text-sm text-[var(--color-rune-dim)] mb-4">
                            Remove <strong className="text-white">{removeTarget}</strong> from the mesh?
                            This device will stop receiving tasks and updates.
                        </p>
                        <div className="nd-modal-actions">
                            <button
                                className="nd-modal-btn nd-btn-secondary"
                                onClick={() => setRemoveTarget(null)}
                            >
                                Cancel
                            </button>
                            <button
                                className="nd-modal-btn nd-btn-danger"
                                onClick={() => handleRemoveNode(removeTarget)}
                            >
                                Remove
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
