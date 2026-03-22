"use client";

import { useState } from "react";
import { API_BASE } from "@/lib/api";

/* ═══════════════════════════════════════════════════════════════════
   Join Mesh — Device 2 enters the join code from Device 1
   ═══════════════════════════════════════════════════════════════════ */

export default function JoinMeshPage() {
    const [joinCode, setJoinCode] = useState("");
    const [status, setStatus] = useState<"idle" | "joining" | "success" | "error">("idle");
    const [message, setMessage] = useState("");
    const [deviceName, setDeviceName] = useState("");

    // Parse join code format: TOKEN@IP:PORT  or just TOKEN@IP
    const parseJoinCode = (code: string) => {
        // Format: TOKEN@IP:PORT  or  TOKEN@IP
        const match = code.trim().match(/^(.+)@([\d.]+)(?::(\d+))?$/);
        if (!match) return null;
        return {
            token: match[1],
            ip: match[2],
            port: parseInt(match[3] || "8765"),
        };
    };

    const handleJoin = async () => {
        const parsed = parseJoinCode(joinCode);
        if (!parsed) {
            setStatus("error");
            setMessage("Invalid join code. Paste the code shown on Device 1.");
            return;
        }

        setStatus("joining");
        setMessage(`Connecting to ${parsed.ip}:${parsed.port}...`);

        try {
            // Detect this device's name and info
            let myName = deviceName.trim().toLowerCase().replace(/\s+/g, "-") || "device-2";
            let gpu = null;
            let model = null;

            // Try to get local status for GPU info
            try {
                const localRes = await fetch(`${API_BASE}/api/v1/status`, { signal: AbortSignal.timeout(3000) });
                if (localRes.ok) {
                    const localData = await localRes.json();
                    gpu = localData.gpu?.name || null;
                    model = localData.model || null;
                    if (!deviceName) myName = localData.node || myName;
                }
            } catch {
                // Local backend not running — that's OK for now
            }

            // Call Device 1's announce endpoint
            const announceUrl = `http://${parsed.ip}:${parsed.port}/api/v1/mesh/announce`;
            const res = await fetch(announceUrl, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    name: myName,
                    ip: window.location.hostname === "localhost" ? "127.0.0.1" : window.location.hostname,
                    port: 8765,
                    role: "worker",
                    token: parsed.token,
                    gpu,
                    model,
                }),
            });

            if (res.ok) {
                const data = await res.json();
                setStatus("success");
                setMessage(
                    data.renamed
                        ? `Joined as "${data.name}" (renamed from "${data.original_name}"). ${data.message}`
                        : `${data.message} You're now part of the mesh as "${data.name}".`
                );
            } else {
                const err = await res.json().catch(() => ({ detail: "Connection failed" }));
                setStatus("error");
                setMessage(err.detail || "Failed to join mesh");
            }
        } catch (e: unknown) {
            setStatus("error");
            const errMsg = e instanceof Error ? e.message : "Unknown error";
            if (errMsg.includes("fetch") || errMsg.includes("network") || errMsg.includes("Failed")) {
                setMessage(`Can't reach Device 1 at that address. Make sure both devices are on the same network.`);
            } else {
                setMessage(errMsg);
            }
        }
    };

    return (
        <div className="max-w-md mx-auto mt-12">
            <div className="glass-card p-8">
                <div className="text-center mb-6">
                    <span className="text-4xl mb-3 block">🔗</span>
                    <h1 className="text-xl font-bold text-white">Join a Mesh</h1>
                    <p className="text-sm text-[var(--color-rune-dim)] mt-2">
                        Enter the join code from your other device.
                    </p>
                </div>

                {status === "success" ? (
                    <div className="text-center">
                        <span className="text-4xl block mb-3">✅</span>
                        <p className="text-[var(--color-neon)] font-semibold mb-2">Connected!</p>
                        <p className="text-sm text-[var(--color-rune-dim)]">{message}</p>
                        <a
                            href="/nodes"
                            className="inline-block mt-4 px-6 py-2 rounded-lg text-sm font-medium"
                            style={{
                                background: "var(--color-neon, #ff6b00)",
                                color: "black",
                            }}
                        >
                            View Devices
                        </a>
                    </div>
                ) : (
                    <>
                        <div className="space-y-4">
                            <div>
                                <label className="text-xs text-[var(--color-rune-dim)] block mb-1.5">
                                    Device name (optional)
                                </label>
                                <input
                                    type="text"
                                    value={deviceName}
                                    onChange={e => setDeviceName(e.target.value)}
                                    placeholder="e.g. gaming-pc, laptop"
                                    className="jm-input"
                                />
                            </div>
                            <div>
                                <label className="text-xs text-[var(--color-rune-dim)] block mb-1.5">
                                    Join code
                                </label>
                                <input
                                    type="text"
                                    value={joinCode}
                                    onChange={e => setJoinCode(e.target.value)}
                                    placeholder="Paste the code from Device 1"
                                    className="jm-input jm-input-mono"
                                    onKeyDown={e => e.key === "Enter" && handleJoin()}
                                />
                            </div>
                        </div>

                        {status === "error" && (
                            <div className="mt-3 p-3 rounded-lg text-sm" style={{ background: "rgba(255,68,102,0.1)", color: "#ff4466" }}>
                                {message}
                            </div>
                        )}

                        {status === "joining" && (
                            <div className="mt-3 p-3 rounded-lg text-sm text-[var(--color-rune-dim)]" style={{ background: "rgba(255,255,255,0.03)" }}>
                                ⏳ {message}
                            </div>
                        )}

                        <button
                            onClick={handleJoin}
                            disabled={!joinCode.trim() || status === "joining"}
                            className="jm-join-btn mt-5"
                        >
                            {status === "joining" ? "Connecting..." : "Join Mesh"}
                        </button>

                        <p className="text-xs text-center text-[var(--color-rune-dim)] mt-4">
                            On your main device, go to <strong className="text-[var(--color-rune)]">Devices → Add device</strong> to get a code.
                        </p>
                    </>
                )}
            </div>
        </div>
    );
}
