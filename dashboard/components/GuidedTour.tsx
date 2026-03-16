"use client";

/**
 * 🗺️ Guided Tour — Sprint 15 F1.
 *
 * Locks sidebar tabs until user visits each section in order.
 * Steps: Dashboard → Brains → Chat → Done (unlock all).
 * "Next" button advances. "Skip Tour" for power users.
 */
import { useState, useEffect, createContext, useContext, useCallback } from "react";
import { usePathname } from "next/navigation";

interface TourState {
    active: boolean;
    currentStep: number;
    completedSteps: string[];
}

interface TourContextType {
    tour: TourState;
    advanceTour: () => void;
    skipTour: () => void;
    isLocked: (href: string) => boolean;
}

// Tour steps mapped to sidebar hrefs
const TOUR_STEPS = [
    { href: "/", label: "Dashboard", icon: "🏠", description: "This is your home — see your AI's status at a glance." },
    { href: "/brains", label: "Brains", icon: "🧠", description: "Choose and manage AI models that power your companion." },
    { href: "/", label: "Chat", icon: "💬", description: "Talk to your AI — it learns from every conversation." },
];

// Hrefs unlocked at each step (cumulative)
const UNLOCKED_AT_STEP: string[][] = [
    ["/"],                                                      // Step 0: Chat only
    ["/", "/brains", "/soul"],                                  // Step 1: + Brains, Personality
    ["/", "/brains", "/soul", "/guildhall", "/store", "/config"], // Step 2: Everything
];

const TourContext = createContext<TourContextType>({
    tour: { active: false, currentStep: 0, completedSteps: [] },
    advanceTour: () => { },
    skipTour: () => { },
    isLocked: () => false,
});

export function useTour() {
    return useContext(TourContext);
}

export function TourProvider({ children }: { children: React.ReactNode }) {
    const [tour, setTour] = useState<TourState>({
        active: false,
        currentStep: 0,
        completedSteps: [],
    });

    useEffect(() => {
        const done = localStorage.getItem("fireside_tour_done");
        if (done) return;

        // Check immediately
        const onboarded = localStorage.getItem("fireside_onboarded");
        if (onboarded) {
            setTour({ active: true, currentStep: 0, completedSteps: [] });
            return;
        }

        // Onboarding might not be done yet — poll until it is
        const interval = setInterval(() => {
            const nowOnboarded = localStorage.getItem("fireside_onboarded");
            const nowDone = localStorage.getItem("fireside_tour_done");
            if (nowDone) {
                clearInterval(interval);
                return;
            }
            if (nowOnboarded) {
                clearInterval(interval);
                setTour({ active: true, currentStep: 0, completedSteps: [] });
            }
        }, 500);

        return () => clearInterval(interval);
    }, []);

    const advanceTour = useCallback(() => {
        setTour((prev) => {
            if (!prev.active) return prev;
            const step = TOUR_STEPS[prev.currentStep];
            if (!step) return prev;

            const newCompleted = [...prev.completedSteps, step.href];
            const nextStep = prev.currentStep + 1;

            if (nextStep >= TOUR_STEPS.length) {
                localStorage.setItem("fireside_tour_done", "1");
                return { active: false, currentStep: nextStep, completedSteps: newCompleted };
            }
            return { active: true, currentStep: nextStep, completedSteps: newCompleted };
        });
    }, []);

    const skipTour = useCallback(() => {
        localStorage.setItem("fireside_tour_done", "1");
        setTour({ active: false, currentStep: TOUR_STEPS.length, completedSteps: TOUR_STEPS.map(s => s.href) });
    }, []);

    const isLocked = useCallback((href: string) => {
        if (!tour.active) return false;
        const step = Math.min(tour.currentStep, TOUR_STEPS.length - 1);
        const currentStepHref = TOUR_STEPS[step]?.href;

        // Always allow the current step's target
        if (href === currentStepHref) return false;

        const unlocked = UNLOCKED_AT_STEP[step] || ["/"];
        return !unlocked.includes(href);
    }, [tour.active, tour.currentStep]);

    return (
        <TourContext.Provider value={{ tour, advanceTour, skipTour, isLocked }}>
            {children}
        </TourContext.Provider>
    );
}

/**
 * Tour Overlay — C5: Premium, unmissable tour bar.
 * Shows current step, progress dots, pulse animation on Next.
 */
export function TourOverlay() {
    const { tour, advanceTour, skipTour } = useTour();
    const pathname = usePathname();

    if (!tour.active) return null;

    const step = TOUR_STEPS[tour.currentStep];
    if (!step) return null;

    const isOnCorrectPage = pathname === step.href;
    const isFirstStep = tour.currentStep === 0;

    return (
        <div
            style={{
                position: "fixed",
                bottom: 20,
                left: "50%",
                transform: "translateX(-50%)",
                zIndex: 9000,
                background: "rgba(10, 10, 15, 0.97)",
                border: "2px solid rgba(245, 158, 11, 0.4)",
                borderRadius: 16,
                padding: "18px 32px",
                display: "flex",
                alignItems: "center",
                gap: 20,
                backdropFilter: "blur(16px)",
                boxShadow: "0 12px 48px rgba(0,0,0,0.6), 0 0 30px rgba(245,158,11,0.1)",
                maxWidth: 640,
                width: "90vw",
            }}
        >
            {/* Step icon */}
            <div style={{
                fontSize: 28,
                background: "rgba(245,158,11,0.15)",
                borderRadius: 12,
                width: 48,
                height: 48,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
            }}>
                {step.icon}
            </div>

            {/* Content */}
            <div style={{ flex: 1, minWidth: 0 }}>
                {isFirstStep && (
                    <div style={{ fontSize: 11, color: "#F59E0B", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 4 }}>
                        Welcome to your AI! Let&apos;s show you around 👋
                    </div>
                )}
                <div style={{ fontSize: 14, color: "#fff", fontWeight: 700, marginBottom: 3 }}>
                    {step.label}
                </div>
                <div style={{ fontSize: 12, color: "#8585a0", lineHeight: 1.4 }}>
                    {step.description}
                </div>

                {/* Progress dots */}
                <div style={{ display: "flex", gap: 6, marginTop: 10 }}>
                    {TOUR_STEPS.map((_, i) => (
                        <div
                            key={i}
                            style={{
                                width: i === tour.currentStep ? 20 : 8,
                                height: 8,
                                borderRadius: 4,
                                background: i <= tour.currentStep ? "#F59E0B" : "rgba(255,255,255,0.15)",
                                transition: "all 0.3s ease",
                            }}
                        />
                    ))}
                </div>
            </div>

            {/* Action area */}
            <div style={{ display: "flex", flexDirection: "column", gap: 8, flexShrink: 0 }}>
                {isOnCorrectPage ? (
                    <button
                        onClick={advanceTour}
                        style={{
                            background: "#F59E0B",
                            border: "none",
                            color: "#0a0a0f",
                            fontSize: 14,
                            fontWeight: 700,
                            padding: "10px 24px",
                            borderRadius: 10,
                            cursor: "pointer",
                            whiteSpace: "nowrap",
                            animation: "pulse 2s ease-in-out infinite",
                            boxShadow: "0 0 20px rgba(245,158,11,0.4)",
                        }}
                    >
                        {tour.currentStep < TOUR_STEPS.length - 1 ? "Next →" : "Done ✓"}
                    </button>
                ) : (
                    <div style={{
                        fontSize: 13,
                        color: "#F59E0B",
                        whiteSpace: "nowrap",
                        fontWeight: 600,
                        textAlign: "center",
                    }}>
                        👆 Go to {step.label}
                    </div>
                )}
                <button
                    onClick={skipTour}
                    style={{
                        background: "transparent",
                        border: "1px solid rgba(245, 158, 11, 0.12)",
                        color: "#55556a",
                        fontSize: 11,
                        padding: "5px 12px",
                        borderRadius: 8,
                        cursor: "pointer",
                        whiteSpace: "nowrap",
                    }}
                >
                    Skip Tour
                </button>
            </div>
        </div>
    );
}
