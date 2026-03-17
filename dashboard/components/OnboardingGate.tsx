"use client";

/**
 * 🚪 Onboarding Gate — Sprint 13 update.
 *
 * Routes new users to the correct wizard:
 *   • Tauri desktop (window.__TAURI__) → InstallerWizard (full setup)
 *   • Browser → OnboardingWizard (connect-to-existing-PC flow)
 */
import { useState, useEffect } from "react";
import { API_BASE } from "../lib/api";
import dynamic from "next/dynamic";

const OnboardingWizard = dynamic(() => import("./OnboardingWizard"), { ssr: false });
const InstallerWizard = dynamic(() => import("./InstallerWizard"), { ssr: false });

function isTauri(): boolean {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    return typeof window !== "undefined" && !!(window as any).__TAURI__;
}

export default function OnboardingGate({ children }: { children: React.ReactNode }) {
    const [showWizard, setShowWizard] = useState<"none" | "installer" | "browser">("none");
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        // Dev mode: ?dev=1 bypasses onboarding and seeds demo data
        if (typeof window !== "undefined") {
            const params = new URLSearchParams(window.location.search);
            if (params.get("dev") === "1" && !localStorage.getItem("fireside_onboarded")) {
                localStorage.setItem("fireside_onboarded", "1");
                localStorage.setItem("fireside_user_name", "Developer");
                localStorage.setItem("fireside_agent_name", "Atlas");
                localStorage.setItem("fireside_agent_style", "analytical");
                localStorage.setItem("fireside_companion_species", "fox");
                localStorage.setItem("fireside_companion_name", "Ember");
                localStorage.setItem("fireside_companion", JSON.stringify({ name: "Ember", species: "fox" }));
                localStorage.setItem("fireside_brain", "fast");
                localStorage.setItem("fireside_model", "llama-3.1-8b-q6");
                setLoading(false);
                return;
            }
        }

        // Fast path: already onboarded
        const onboarded = localStorage.getItem("fireside_onboarded");
        if (onboarded) {
            setLoading(false);
            return;
        }

        // Tauri IPC bridge may not be injected yet when useEffect fires.
        // Retry a few times before falling back to browser wizard.
        let attempts = 0;
        const maxAttempts = 10; // 10 × 200ms = 2 seconds max wait

        const checkTauri = () => {
            if (isTauri()) {
                setShowWizard("installer");
                setLoading(false);
                return;
            }

            attempts++;
            if (attempts < maxAttempts) {
                setTimeout(checkTauri, 200);
                return;
            }

            // After 2s, Tauri is definitely not available — try backend, then browser wizard
            (async () => {
                try {
                    const res = await fetch(`${API_BASE}/api/v1/system/onboarding`);
                    if (res.ok) {
                        const data = await res.json();
                        if (data.onboarded) {
                            localStorage.setItem("fireside_onboarded", "1");
                            if (data.user_name) localStorage.setItem("fireside_user_name", data.user_name);
                            if (data.personality) localStorage.setItem("fireside_personality", data.personality);
                            if (data.companion) localStorage.setItem("fireside_companion", JSON.stringify(data.companion));
                            setLoading(false);
                            return;
                        }
                    }
                } catch {
                    // Backend not reachable
                }
                setShowWizard("browser");
                setLoading(false);
            })();
        };

        checkTauri();
    }, []);

    if (loading) return null;

    if (showWizard === "installer") {
        return <InstallerWizard onComplete={() => setShowWizard("none")} />;
    }

    if (showWizard === "browser") {
        return <OnboardingWizard onComplete={() => setShowWizard("none")} />;
    }

    return <>{children}</>;
}
