"use client";

import { useState, useEffect } from "react";

interface QRAuthProps {
    className?: string;
}

export default function QRAuth({ className }: QRAuthProps) {
    const [token] = useState(() => Math.random().toString(36).substring(2, 15));
    const [scanned, setScanned] = useState(false);
    const [timeLeft, setTimeLeft] = useState(300); // 5 minutes

    useEffect(() => {
        if (scanned) return;
        const interval = setInterval(() => {
            setTimeLeft((t) => {
                if (t <= 1) {
                    clearInterval(interval);
                    return 0;
                }
                return t - 1;
            });
        }, 1000);
        return () => clearInterval(interval);
    }, [scanned]);

    // Simulate scan after some time (for demo)
    const simulateScan = () => {
        setScanned(true);
    };

    if (scanned) {
        return (
            <div className={`glass-card p-6 text-center ${className || ""}`}>
                <span className="text-5xl block mb-3">✅</span>
                <h3 className="text-white font-semibold mb-1">Phone Connected!</h3>
                <p className="text-xs text-[var(--color-rune-dim)]">
                    Your phone is now connected. You can chat with your AI from anywhere.
                </p>
            </div>
        );
    }

    if (timeLeft === 0) {
        return (
            <div className={`glass-card p-6 text-center ${className || ""}`}>
                <span className="text-5xl block mb-3">⏰</span>
                <h3 className="text-white font-semibold mb-1">QR Code Expired</h3>
                <p className="text-xs text-[var(--color-rune-dim)] mb-3">
                    The QR code has expired for security.
                </p>
                <button
                    onClick={() => setTimeLeft(300)}
                    className="btn-neon px-5 py-2 text-sm"
                >
                    Generate New Code
                </button>
            </div>
        );
    }

    const minutes = Math.floor(timeLeft / 60);
    const seconds = timeLeft % 60;

    return (
        <div className={`glass-card p-6 text-center ${className || ""}`}>
            <h3 className="text-white font-semibold mb-1">📱 Connect Your Phone</h3>
            <p className="text-xs text-[var(--color-rune-dim)] mb-4">
                Scan this QR code with your phone&apos;s camera to connect.
            </p>

            {/* QR Code (simulated with CSS pattern) */}
            <div className="mx-auto w-48 h-48 rounded-xl bg-white p-3 mb-4">
                <div className="w-full h-full rounded-lg relative overflow-hidden" style={{ background: "#fff" }}>
                    {/* Simulated QR pattern */}
                    <svg viewBox="0 0 100 100" className="w-full h-full">
                        {/* Corner squares */}
                        <rect x="5" y="5" width="20" height="20" fill="none" stroke="black" strokeWidth="4" />
                        <rect x="10" y="10" width="10" height="10" fill="black" />
                        <rect x="75" y="5" width="20" height="20" fill="none" stroke="black" strokeWidth="4" />
                        <rect x="80" y="10" width="10" height="10" fill="black" />
                        <rect x="5" y="75" width="20" height="20" fill="none" stroke="black" strokeWidth="4" />
                        <rect x="10" y="80" width="10" height="10" fill="black" />
                        {/* Random data pattern */}
                        {Array.from({ length: 40 }, (_, i) => {
                            const x = 30 + (i % 8) * 6;
                            const y = 30 + Math.floor(i / 8) * 6;
                            return token.charCodeAt(i % token.length) % 2 === 0 ? (
                                <rect key={i} x={x} y={y} width="5" height="5" fill="black" />
                            ) : null;
                        })}
                        {/* Valhalla logo in center */}
                        <circle cx="50" cy="50" r="8" fill="white" />
                        <text x="50" y="53" textAnchor="middle" fontSize="10">⚡</text>
                    </svg>
                </div>
            </div>

            <p className="text-xs text-[var(--color-rune-dim)] mb-2">
                Expires in <span className="text-white font-mono">{minutes}:{seconds.toString().padStart(2, "0")}</span>
            </p>

            {/* Demo button */}
            <button
                onClick={simulateScan}
                className="text-xs text-[var(--color-neon)] hover:underline"
            >
                Simulate scan (demo)
            </button>
        </div>
    );
}
