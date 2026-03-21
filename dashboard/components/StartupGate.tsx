"use client";

/**
 * 🔥 Startup Gate — blocks app interaction until bifrost (port 8765) is healthy.
 *
 * Shows a warm loading screen while waiting for the backend. Once /health returns 200,
 * the gate lifts and children render. Non-technical users never see error messages —
 * just a natural "warming up" experience.
 */
import { useState, useEffect, useRef } from "react";
import { API_BASE } from "@/lib/api";

interface Props {
    children: React.ReactNode;
}

export default function StartupGate({ children }: Props) {
    const [ready, setReady] = useState(false);
    const [dots, setDots] = useState("");
    const [hint, setHint] = useState("");
    const attempts = useRef(0);

    useEffect(() => {
        let cancelled = false;
        let dotTimer: ReturnType<typeof setInterval>;

        // Animate the dots
        dotTimer = setInterval(() => {
            setDots(prev => prev.length >= 3 ? "" : prev + ".");
        }, 500);

        const poll = async () => {
            while (!cancelled) {
                attempts.current++;
                try {
                    const res = await fetch(`${API_BASE}/health`, {
                        signal: AbortSignal.timeout(3000),
                    });
                    if (res.ok) {
                        setReady(true);
                        return;
                    }
                } catch {
                    // Backend not ready yet
                }

                // Friendly hints based on wait duration
                if (attempts.current >= 15) {
                    setHint("Almost there — your AI brain is loading into memory");
                } else if (attempts.current >= 8) {
                    setHint("Setting up your companion's abilities");
                } else if (attempts.current >= 4) {
                    setHint("Preparing your fireside experience");
                }

                await new Promise(r => setTimeout(r, 2000));
            }
        };

        poll();

        return () => {
            cancelled = true;
            clearInterval(dotTimer);
        };
    }, []);

    if (ready) return <>{children}</>;

    return (
        <div style={styles.root}>
            <style>{gateCSS}</style>
            <div className="sg-container">
                <div className="sg-fire">🔥</div>
                <h1 className="sg-title">Fireside</h1>
                <div className="sg-loading">
                    <div className="sg-bar">
                        <div className="sg-bar-fill" />
                    </div>
                    <p className="sg-status">Warming up{dots}</p>
                    {hint && <p className="sg-hint">{hint}</p>}
                </div>
            </div>
        </div>
    );
}

const styles: Record<string, React.CSSProperties> = {
    root: {
        position: "fixed",
        inset: 0,
        zIndex: 99999,
        background: "#060609",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "'Outfit', 'Inter', system-ui, sans-serif",
    },
};

const gateCSS = `
    .sg-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 16px;
        animation: sgFadeIn 0.8s ease both;
    }
    @keyframes sgFadeIn {
        from { opacity: 0; transform: scale(0.95); }
        to { opacity: 1; transform: scale(1); }
    }

    .sg-fire {
        font-size: 64px;
        animation: sgFlicker 2s ease-in-out infinite alternate;
        filter: drop-shadow(0 0 30px rgba(245,158,11,0.4));
    }
    @keyframes sgFlicker {
        0% { transform: scale(1); filter: drop-shadow(0 0 20px rgba(245,158,11,0.3)); }
        100% { transform: scale(1.05); filter: drop-shadow(0 0 40px rgba(245,158,11,0.5)); }
    }

    .sg-title {
        font-size: 36px;
        font-weight: 900;
        background: linear-gradient(135deg, #F0DCC8, #FBBF24, #D97706);
        -webkit-background-clip: text;
        background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
    }

    .sg-loading {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 12px;
        margin-top: 12px;
        width: 240px;
    }

    .sg-bar {
        width: 100%;
        height: 4px;
        border-radius: 2px;
        background: rgba(245,158,11,0.08);
        overflow: hidden;
    }
    .sg-bar-fill {
        height: 100%;
        border-radius: 2px;
        background: linear-gradient(90deg, #D97706, #F59E0B, #FBBF24);
        box-shadow: 0 0 10px rgba(245,158,11,0.3);
        animation: sgBarPulse 1.5s ease-in-out infinite;
        width: 40%;
    }
    @keyframes sgBarPulse {
        0% { transform: translateX(-100%); }
        100% { transform: translateX(350%); }
    }

    .sg-status {
        font-size: 14px;
        font-weight: 600;
        color: #6A5A4A;
        margin: 0;
        letter-spacing: 0.5px;
    }
    .sg-hint {
        font-size: 11px;
        color: #4A3D30;
        margin: 0;
        animation: sgFadeIn 0.5s ease both;
        text-align: center;
        max-width: 220px;
    }
`;
