"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import BrainSelectScreen from "@/components/BrainSelectScreen";
import BrainControlPanel from "@/components/BrainControlPanel";
import { DiscoveryCard } from "@/components/GuidedTour";
import { API_BASE } from "@/lib/api";

export default function BrainsPage() {
    const router = useRouter();
    const [detectedVram, setDetectedVram] = useState(0);
    const [currentBrain, setCurrentBrain] = useState("");
    const [switching, setSwitching] = useState(false);

    useEffect(() => {
        // Fetch real VRAM from backend
        fetch(`${API_BASE}/api/v1/status`)
            .then(r => r.json())
            .then(data => {
                const vram = data.gpu?.vram_total_gb || 0;
                setDetectedVram(vram);
                localStorage.setItem("fireside_vram", String(vram));
            })
            .catch(() => {
                const vram = parseFloat(localStorage.getItem("fireside_vram") || "0");
                setDetectedVram(vram);
            });

        const brain = localStorage.getItem("fireside_brain_label") || "";
        setCurrentBrain(brain);
    }, []);

    const handleSelect = async (modelId: string, label: string, size: string, quant: string) => {
        // Save to localStorage (UI state)
        localStorage.setItem("fireside_brain", modelId);
        localStorage.setItem("fireside_brain_label", label);
        localStorage.setItem("fireside_brain_quant", quant);
        setCurrentBrain(label);
        setSwitching(true);

        // Call backend to trigger download + auto-start
        try {
            const res = await fetch(`${API_BASE}/api/v1/brains/install`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ model_id: modelId === "llama-3.1-8b" ? "fast" : "deep" }),
            });
            const data = await res.json();
            console.log("[BrainLab] Install response:", data);
        } catch (e) {
            console.warn("[BrainLab] Backend call failed:", e);
        } finally {
            setSwitching(false);
        }
    };

    return (
        <div style={{ minHeight: '100vh', background: '#080810' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '14px 16px', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                <Link href="/" style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '8px 16px', borderRadius: 10, fontSize: 13, fontWeight: 800, color: '#C4A882', textDecoration: 'none', background: 'rgba(245,158,11,0.06)', border: '1px solid rgba(245,158,11,0.12)', fontFamily: "'Outfit', system-ui" }}>🔥 Hub</Link>
                <span style={{ fontSize: 12, color: '#3A3530', fontWeight: 600, textTransform: 'uppercase' as const, letterSpacing: 1 }}>Brain Lab</span>
            </div>
            <DiscoveryCard pageKey="/brains" />

            {/* ─── Brain Control Panel (live status + controls) ─── */}
            <div style={{ paddingTop: 16 }}>
                <BrainControlPanel />
            </div>

            {switching && (
                <div style={{
                    padding: '12px 24px',
                    background: 'rgba(59,130,246,0.06)',
                    borderBottom: '1px solid rgba(59,130,246,0.1)',
                    fontSize: 12, color: '#3B82F6', fontWeight: 600,
                    display: 'flex', alignItems: 'center', gap: 8,
                    animation: 'bcpPulse 1.5s ease-in-out infinite',
                }}>
                    <span>⏳</span>
                    <span>Downloading and switching brain...</span>
                </div>
            )}

            {/* ─── Existing RPG Brain Selector ─── */}
            <BrainSelectScreen
                onSelect={handleSelect}
                detectedVram={detectedVram}
                onBack={() => router.push('/')}
                fullscreen={false}
            />
        </div>
    );
}
