"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { API_BASE } from "@/lib/api";

/* ═══════════════════════════════════════════════════════════════════
   Join Mesh — Device 2 auto-discovers Device 1 and pairs with a PIN
   Like Bluetooth pairing: find → enter 6-digit PIN → connected.
   ═══════════════════════════════════════════════════════════════════ */

interface DiscoveredNode {
    name: string;
    ip: string;
    port: number;
}

type JoinStep = "scanning" | "found" | "pin" | "joining" | "success" | "error" | "manual";

export default function JoinMeshPage() {
    const [step, setStep] = useState<JoinStep>("scanning");
    const [discovered, setDiscovered] = useState<DiscoveredNode[]>([]);
    const [selected, setSelected] = useState<DiscoveredNode | null>(null);
    const [pin, setPin] = useState(["", "", "", "", "", ""]);
    const [deviceName, setDeviceName] = useState("");
    const [message, setMessage] = useState("");
    const [assignedName, setAssignedName] = useState("");
    const pinRefs = useRef<(HTMLInputElement | null)[]>([]);

    // Auto-scan LAN on mount
    const scanLan = useCallback(async () => {
        setStep("scanning");
        setMessage("Looking for Fireside on your network...");
        try {
            const res = await fetch(`${API_BASE}/api/v1/mesh/discover`);
            if (res.ok) {
                const data = await res.json();
                if (data.nodes && data.nodes.length > 0) {
                    setDiscovered(data.nodes);
                    if (data.nodes.length === 1) {
                        setSelected(data.nodes[0]);
                        setStep("pin");
                    } else {
                        setStep("found");
                    }
                } else {
                    setStep("manual");
                    setMessage("No devices found. Make sure both are on the same WiFi.");
                }
            } else {
                setStep("manual");
                setMessage("Discovery failed. You can enter the IP manually.");
            }
        } catch {
            setStep("manual");
            setMessage("Backend not running. Start Fireside first.");
        }
    }, []);

    useEffect(() => { scanLan(); }, [scanLan]);

    // Select a discovered node
    const selectNode = (node: DiscoveredNode) => {
        setSelected(node);
        setStep("pin");
        setTimeout(() => pinRefs.current[0]?.focus(), 100);
    };

    // PIN input handlers
    const handlePinChange = (index: number, value: string) => {
        if (!/^\d?$/.test(value)) return; // only digits
        const newPin = [...pin];
        newPin[index] = value;
        setPin(newPin);
        // Auto-advance to next input
        if (value && index < 5) {
            pinRefs.current[index + 1]?.focus();
        }
        // Auto-submit when all 6 digits entered
        if (value && index === 5 && newPin.every(d => d)) {
            handleJoin(newPin.join(""));
        }
    };

    const handlePinKeyDown = (index: number, e: React.KeyboardEvent) => {
        if (e.key === "Backspace" && !pin[index] && index > 0) {
            pinRefs.current[index - 1]?.focus();
        }
        if (e.key === "Enter") {
            const fullPin = pin.join("");
            if (fullPin.length === 6) handleJoin(fullPin);
        }
    };

    // Paste handler — fill all 6 digits at once
    const handlePaste = (e: React.ClipboardEvent) => {
        const text = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, 6);
        if (text.length === 6) {
            e.preventDefault();
            const newPin = text.split("");
            setPin(newPin);
            handleJoin(text);
        }
    };

    // Join the mesh
    const handleJoin = async (pinCode: string) => {
        if (!selected) return;
        setStep("joining");
        setMessage(`Connecting to ${selected.name}...`);

        try {
            const myName = deviceName.trim().toLowerCase().replace(/\s+/g, "-") || "device-2";

            // Detect our own LAN IP
            let myIp = "0.0.0.0";
            try {
                const statusRes = await fetch(`${API_BASE}/api/v1/status`, { signal: AbortSignal.timeout(2000) });
                if (statusRes.ok) {
                    const statusData = await statusRes.json();
                    // Use the status endpoint's detected info
                    if (statusData.node) myIp = "0.0.0.0"; // Will be detected by remote
                }
            } catch { /* ok */ }

            const announceUrl = `http://${selected.ip}:${selected.port}/api/v1/mesh/announce`;
            const res = await fetch(announceUrl, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    name: myName,
                    ip: myIp,
                    port: 8765,
                    role: "worker",
                    token: pinCode,
                }),
            });

            if (res.ok) {
                const data = await res.json();
                setAssignedName(data.name || myName);
                setStep("success");
                setMessage(data.message || "Connected!");
            } else {
                const err = await res.json().catch(() => ({ detail: "Connection failed" }));
                setStep("pin");
                setMessage(err.detail || "Wrong PIN or expired. Try again.");
                setPin(["", "", "", "", "", ""]);
                setTimeout(() => pinRefs.current[0]?.focus(), 100);
            }
        } catch {
            setStep("error");
            setMessage(`Can't reach ${selected.name}. Make sure both devices are on the same network.`);
        }
    };

    return (
        <div className="max-w-md mx-auto mt-12">
            <div className="glass-card p-8">

                {/* ── Scanning ── */}
                {step === "scanning" && (
                    <div className="text-center">
                        <div className="jm-pulse-ring mb-4">
                            <span className="text-3xl">📡</span>
                        </div>
                        <h1 className="text-xl font-bold text-white mb-2">Scanning Network</h1>
                        <p className="text-sm text-[var(--color-rune-dim)]">{message}</p>
                    </div>
                )}

                {/* ── Found multiple devices ── */}
                {step === "found" && (
                    <div className="text-center">
                        <h1 className="text-xl font-bold text-white mb-1">Devices Found</h1>
                        <p className="text-sm text-[var(--color-rune-dim)] mb-4">
                            Select the device you want to join.
                        </p>
                        <div className="space-y-2">
                            {discovered.map(node => (
                                <button
                                    key={node.ip}
                                    onClick={() => selectNode(node)}
                                    className="w-full p-3 rounded-lg text-left transition-all hover:border-[var(--color-neon)]"
                                    style={{
                                        background: "rgba(255,255,255,0.04)",
                                        border: "1px solid var(--color-glass-border)",
                                    }}
                                >
                                    <div className="flex items-center gap-3">
                                        <span className="text-xl">💻</span>
                                        <div>
                                            <div className="text-white font-medium">{node.name}</div>
                                            <div className="text-xs text-[var(--color-rune-dim)]">{node.ip}</div>
                                        </div>
                                    </div>
                                </button>
                            ))}
                        </div>
                    </div>
                )}

                {/* ── PIN entry ── */}
                {step === "pin" && (
                    <div className="text-center">
                        <span className="text-3xl block mb-3">🔐</span>
                        <h1 className="text-xl font-bold text-white mb-1">Enter PIN</h1>
                        <p className="text-sm text-[var(--color-rune-dim)] mb-5">
                            Enter the 6-digit PIN shown on <strong className="text-white">{selected?.name}</strong>
                        </p>

                        <div className="jm-pin-row" onPaste={handlePaste}>
                            {pin.map((digit, i) => (
                                <span key={i} className="contents">
                                    {i === 3 && <span className="jm-pin-dash">—</span>}
                                    <input
                                        ref={el => { pinRefs.current[i] = el; }}
                                        type="text"
                                        inputMode="numeric"
                                        maxLength={1}
                                        value={digit}
                                        onChange={e => handlePinChange(i, e.target.value)}
                                        onKeyDown={e => handlePinKeyDown(i, e)}
                                        className="jm-pin-input"
                                        autoFocus={i === 0}
                                    />
                                </span>
                            ))}
                        </div>

                        {message && (
                            <div className="mt-3 text-sm" style={{ color: "#ff4466" }}>
                                {message}
                            </div>
                        )}

                        <div className="mt-4">
                            <label className="text-xs text-[var(--color-rune-dim)] block mb-1">
                                Name this device (optional)
                            </label>
                            <input
                                type="text"
                                value={deviceName}
                                onChange={e => setDeviceName(e.target.value)}
                                placeholder="e.g. gaming-pc"
                                className="jm-input text-center"
                                style={{ maxWidth: 200, margin: "0 auto" }}
                            />
                        </div>
                    </div>
                )}

                {/* ── Joining ── */}
                {step === "joining" && (
                    <div className="text-center">
                        <div className="jm-pulse-ring mb-4">
                            <span className="text-3xl">🔗</span>
                        </div>
                        <h1 className="text-xl font-bold text-white mb-2">Connecting</h1>
                        <p className="text-sm text-[var(--color-rune-dim)]">{message}</p>
                    </div>
                )}

                {/* ── Success ── */}
                {step === "success" && (
                    <div className="text-center">
                        <span className="text-4xl block mb-3">✅</span>
                        <h1 className="text-xl font-bold text-[var(--color-neon)] mb-2">Connected!</h1>
                        <p className="text-sm text-[var(--color-rune-dim)] mb-1">{message}</p>
                        <p className="text-sm text-[var(--color-rune)]">
                            This device is now <strong>{assignedName}</strong> in the mesh.
                        </p>
                        <a
                            href="/nodes"
                            className="inline-block mt-5 px-6 py-2.5 rounded-lg text-sm font-medium"
                            style={{ background: "var(--color-neon)", color: "black" }}
                        >
                            View Devices
                        </a>
                    </div>
                )}

                {/* ── Error ── */}
                {step === "error" && (
                    <div className="text-center">
                        <span className="text-4xl block mb-3">❌</span>
                        <h1 className="text-xl font-bold text-white mb-2">Connection Failed</h1>
                        <p className="text-sm text-[var(--color-rune-dim)] mb-4">{message}</p>
                        <button onClick={scanLan} className="jm-join-btn" style={{ maxWidth: 200, margin: "0 auto" }}>
                            Try Again
                        </button>
                    </div>
                )}

                {/* ── Manual fallback ── */}
                {step === "manual" && (
                    <div className="text-center">
                        <span className="text-3xl block mb-3">🔧</span>
                        <h1 className="text-xl font-bold text-white mb-2">Manual Setup</h1>
                        <p className="text-sm text-[var(--color-rune-dim)] mb-4">{message}</p>
                        <button onClick={scanLan} className="jm-join-btn mb-3" style={{ maxWidth: 200, margin: "0 auto" }}>
                            🔄 Scan Again
                        </button>
                        <p className="text-xs text-[var(--color-rune-dim)]">
                            Make sure Fireside is running on both devices and they&apos;re on the same WiFi network.
                        </p>
                    </div>
                )}
            </div>
        </div>
    );
}
