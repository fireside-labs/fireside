"use client";

import { useState, useEffect } from "react";
import dynamic from "next/dynamic";

const OnboardingWizard = dynamic(() => import("./OnboardingWizard"), { ssr: false });

export default function OnboardingGate({ children }: { children: React.ReactNode }) {
    const [showWizard, setShowWizard] = useState(false);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        // Check localStorage first (fast path)
        const onboarded = localStorage.getItem("fireside_onboarded");
        if (onboarded) {
            setLoading(false);
            return;
        }

        // Check if install.sh already completed onboarding (via backend API)
        (async () => {
            try {
                const res = await fetch("http://127.0.0.1:8765/api/v1/system/onboarding");
                if (res.ok) {
                    const data = await res.json();
                    if (data.onboarded) {
                        // Sync install.sh data to localStorage so dashboard has it
                        localStorage.setItem("fireside_onboarded", "1");
                        if (data.user_name) localStorage.setItem("fireside_user_name", data.user_name);
                        if (data.personality) localStorage.setItem("fireside_personality", data.personality);
                        if (data.companion) localStorage.setItem("fireside_companion", JSON.stringify(data.companion));
                        setLoading(false);
                        return;
                    }
                }
            } catch {
                // Backend not reachable — fall through to wizard
            }
            setShowWizard(true);
            setLoading(false);
        })();
    }, []);

    if (loading) return null;

    if (showWizard) {
        return <OnboardingWizard onComplete={() => setShowWizard(false)} />;
    }

    return <>{children}</>;
}
