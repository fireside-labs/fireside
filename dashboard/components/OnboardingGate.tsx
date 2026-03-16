"use client";

/**
 * 🚪 Onboarding Gate — Sprint 13 update.
 *
 * Routes new users to the correct wizard:
 *   • Tauri desktop (window.__TAURI__) → InstallerWizard (full setup)
 *   • Browser → OnboardingWizard (connect-to-existing-PC flow)
 */
import { useState, useEffect } from "react";
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
                    const res = await fetch("http://127.0.0.1:8765/api/v1/system/onboarding");
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
