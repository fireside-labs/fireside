"use client";

/**
 * 🗺️ Guided Tour — Sprint 14 F10.
 *
 * Locks sidebar tabs until user visits each section in order.
 * Steps: Companion → Chat → Brains → Unlock all.
 * "Skip Tour" for power users.
 */
import { useState, useEffect, createContext, useContext } from "react";

interface TourState {
    active: boolean;
    currentStep: number;
    completedSteps: string[];
}

interface TourContextType {
    tour: TourState;
    advanceTour: (section: string) => void;
    skipTour: () => void;
    isLocked: (section: string) => boolean;
}

const TOUR_STEPS = ["companion", "chat", "brains"];

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
            setTour({ active: true, currentStep: 0, completedSteps: [] });
        }
    }, []);

    const advanceTour = (section: string) => {
        if (!tour.active) return;
        const stepIndex = TOUR_STEPS.indexOf(section);
        if (stepIndex === -1 || stepIndex !== tour.currentStep) return;

        const newCompleted = [...tour.completedSteps, section];
        const nextStep = tour.currentStep + 1;

        if (nextStep >= TOUR_STEPS.length) {
            // Tour complete
            localStorage.setItem("fireside_tour_done", "1");
            setTour({ active: false, currentStep: nextStep, completedSteps: newCompleted });
        } else {
            setTour({ active: true, currentStep: nextStep, completedSteps: newCompleted });
        }
    };

    const skipTour = () => {
        localStorage.setItem("fireside_tour_done", "1");
        setTour({ active: false, currentStep: TOUR_STEPS.length, completedSteps: TOUR_STEPS });
    };

    const isLocked = (section: string) => {
        if (!tour.active) return false;
        const stepIndex = TOUR_STEPS.indexOf(section);
        if (stepIndex === -1) return tour.currentStep < TOUR_STEPS.length;
        return stepIndex > tour.currentStep;
    };

    return (
        <TourContext.Provider value={{ tour, advanceTour, skipTour, isLocked }}>
            {children}
        </TourContext.Provider>
    );
}

/**
 * Tour Overlay — shows at the bottom of screen during active tour.
 * Displays current step and "Skip Tour" button.
 */
export function TourOverlay() {
    const { tour, skipTour } = useTour();

    if (!tour.active) return null;

    const step = TOUR_STEPS[tour.currentStep];
    const stepLabels: Record<string, string> = {
        companion: "👋 First, visit your Companion",
        chat: "💬 Now try the Chat",
        brains: "🧠 Check out your Brains",
    };

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
                padding: "12px 24px",
                display: "flex",
                alignItems: "center",
                gap: 16,
                backdropFilter: "blur(12px)",
                boxShadow: "0 8px 32px rgba(0,0,0,0.4)",
            }}
        >
            <span style={{ fontSize: 14, color: "#F59E0B", fontWeight: 600 }}>
                Step {tour.currentStep + 1}/{TOUR_STEPS.length}
            </span>
            <span style={{ fontSize: 14, color: "#A08264" }}>
                {stepLabels[step] || "Explore this section"}
            </span>
            <button
                onClick={skipTour}
                style={{
                    background: "transparent",
                    border: "1px solid rgba(245, 158, 11, 0.2)",
                    color: "#8585a0",
                    fontSize: 12,
                    padding: "6px 14px",
                    borderRadius: 8,
                    cursor: "pointer",
                    marginLeft: 8,
                }}
            >
                Skip Tour
            </button>
        </div>
    );
}
