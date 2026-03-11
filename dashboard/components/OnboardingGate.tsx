"use client";

import { useState, useEffect } from "react";
import dynamic from "next/dynamic";

const OnboardingWizard = dynamic(() => import("@/components/OnboardingWizard"), { ssr: false });

export function OnboardingGate() {
    const [showWizard, setShowWizard] = useState(false);

    useEffect(() => {
        const onboarded = localStorage.getItem("valhalla_onboarded");
        if (!onboarded) {
            setShowWizard(true);
        }
    }, []);

    if (!showWizard) return null;

    return <OnboardingWizard onComplete={() => setShowWizard(false)} />;
}
