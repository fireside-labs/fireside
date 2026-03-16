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
    ["/"],                          // Step 0: Dashboard (Start)
    ["/", "/brains"],               // Step 1: Brains
    ["/", "/brains", "/nodes", "/companion"], // Step 2: Chat + others
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
        if (!done) {
            const onboarded = localStorage.getItem("fireside_onboarded");
            if (onboarded) {
                setTour({ active: true, currentStep: 0, completedSteps: [] });
            }
        }
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
 * Tour Overlay — fixed bar at the bottom during active tour.
 * Shows current step info + Next button + Skip Tour.
 */
export function TourOverlay() {
    const { tour, advanceTour, skipTour } = useTour();
    const pathname = usePathname();

    if (!tour.active) return null;

    const step = TOUR_STEPS[tour.currentStep];
    if (!step) return null;

    // Only show Next when user is on the correct page
    const isOnCorrectPage = pathname === step.href;

    return (
        <div
            style={{
                position: "fixed",
                bottom: 24,
                left: "50%",
                transform: "translateX(-50%)",
                zIndex: 9000,
                background: "rgba(15, 15, 15, 0.95)",
                border: "1px solid rgba(245, 158, 11, 0.3)",
                borderRadius: 14,
                padding: "14px 28px",
                display: "flex",
                alignItems: "center",
                gap: 16,
                backdropFilter: "blur(12px)",
                boxShadow: "0 8px 32px rgba(0,0,0,0.4)",
                maxWidth: 600,
            }}
        >
            <span style={{ fontSize: 20 }}>{step.icon}</span>
            <div style={{ flex: 1 }}>
                <div style={{ fontSize: 13, color: "#F59E0B", fontWeight: 600, marginBottom: 2 }}>
                    Step {tour.currentStep + 1} of {TOUR_STEPS.length} — {step.label}
                </div>
                <div style={{ fontSize: 12, color: "#8585a0" }}>
                    {step.description}
                </div>
            </div>
            {isOnCorrectPage ? (
                <button
                    onClick={advanceTour}
                    style={{
                        background: "#F59E0B",
                        border: "none",
                        color: "#0a0a0f",
                        fontSize: 13,
                        fontWeight: 600,
                        padding: "8px 20px",
                        borderRadius: 8,
                        cursor: "pointer",
                        whiteSpace: "nowrap",
                    }}
                >
                    {tour.currentStep < TOUR_STEPS.length - 1 ? "Next →" : "Done ✓"}
                </button>
            ) : (
                <span style={{ fontSize: 12, color: "#F59E0B", whiteSpace: "nowrap" }}>
                    Navigate to {step.label} ↑
                </span>
            )}
            <button
                onClick={skipTour}
                style={{
                    background: "transparent",
                    border: "1px solid rgba(245, 158, 11, 0.15)",
                    color: "#6a6a80",
                    fontSize: 11,
                    padding: "6px 12px",
                    borderRadius: 8,
                    cursor: "pointer",
                    whiteSpace: "nowrap",
                }}
            >
                Skip
            </button>
        </div>
    );
}
