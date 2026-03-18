"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import BrainSelectScreen from "@/components/BrainSelectScreen";

export default function BrainsPage() {
    const router = useRouter();
    const [detectedVram, setDetectedVram] = useState(0);
    const [currentBrain, setCurrentBrain] = useState("");

    useEffect(() => {
        const vram = parseFloat(localStorage.getItem("fireside_vram") || "0");
        setDetectedVram(vram);
        const brain = localStorage.getItem("fireside_brain_label") || "";
        setCurrentBrain(brain);
    }, []);

    return (
        <div style={{ minHeight: '100vh', background: '#080810' }}>
            {currentBrain && (
                <div style={{
                    padding: '12px 24px',
                    background: 'rgba(245,158,11,0.06)',
                    borderBottom: '1px solid rgba(245,158,11,0.1)',
                    fontSize: 12, color: '#7A6A5A',
                    display: 'flex', alignItems: 'center', gap: 8,
                }}>
                    <span>🧠</span>
                    <span>Current brain: <strong style={{ color: '#F0DCC8' }}>{currentBrain}</strong></span>
                </div>
            )}
            <BrainSelectScreen
                onSelect={(modelId, label, size, quant) => {
                    localStorage.setItem("fireside_brain", modelId);
                    localStorage.setItem("fireside_brain_label", label);
                    localStorage.setItem("fireside_brain_quant", quant);
                    setCurrentBrain(label);
                }}
                detectedVram={detectedVram}
                onBack={() => router.push('/')}
                fullscreen
            />
        </div>
    );
}
