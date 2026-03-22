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
            {/* CSS in globals.css */}
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

// CSS migrated to globals.css