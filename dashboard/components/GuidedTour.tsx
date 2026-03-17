"use client";

/**
 * 🗺️ Guided Tour — Sprint 24 Redesign.
 *
 * NEVER locks tabs. Instead:
 * - Highlights the recommended next tab with a pulsing glow
 * - Shows a friendly tip bar at the bottom
 * - Auto-marks pages as visited when user navigates
 * - Completes when all key pages visited OR skip
 */
import { useState, useEffect, createContext, useContext, useCallback } from "react";
import { usePathname, useRouter } from "next/navigation";

interface TourState {
    active: boolean;
    currentStep: number;
    visitedPages: Set<string>;
}

interface TourContextType {
    tour: TourState;
    advanceTour: () => void;
    skipTour: () => void;
    isRecommended: (href: string) => boolean;
    isVisited: (href: string) => boolean;
}

// Tour steps mapped to sidebar hrefs
const TOUR_STEPS = [
    { href: "/", label: "Dashboard", icon: "🏠", description: "Your home — see your AI's status and start chatting." },
    { href: "/soul", label: "Personality", icon: "🎭", description: "Customize how your AI thinks, talks, and behaves." },
    { href: "/guildhall", label: "Guild Hall", icon: "🏰", description: "Watch your agents work. This is your command center." },
    { href: "/brains", label: "Brains", icon: "🧠", description: "Choose the AI model that powers your companion." },
    { href: "/store", label: "Store", icon: "🏪", description: "Get environment packs, skins, and themes." },
    { href: "/config", label: "Settings", icon: "⚙", description: "Tweak your setup. Advanced tab has everything." },
];

const TourContext = createContext<TourContextType>({
    tour: { active: false, currentStep: 0, visitedPages: new Set() },
    advanceTour: () => { },
    skipTour: () => { },
    isRecommended: () => false,
    isVisited: () => false,
});

export function useTour() {
    return useContext(TourContext);
}

export function TourProvider({ children }: { children: React.ReactNode }) {
    const [tour, setTour] = useState<TourState>({
        active: false,
        currentStep: 0,
        visitedPages: new Set(),
    });
    const pathname = usePathname();

    // Start tour after onboarding
    useEffect(() => {
        const done = localStorage.getItem("fireside_tour_done");
        if (done) return;

        const onboarded = localStorage.getItem("fireside_onboarded");
        if (onboarded) {
            setTour({ active: true, currentStep: 0, visitedPages: new Set(["/"]) });
            return;
        }

        const interval = setInterval(() => {
            const nowOnboarded = localStorage.getItem("fireside_onboarded");
            const nowDone = localStorage.getItem("fireside_tour_done");
            if (nowDone) { clearInterval(interval); return; }
            if (nowOnboarded) {
                clearInterval(interval);
                setTour({ active: true, currentStep: 0, visitedPages: new Set(["/"]) });
            }
        }, 500);

        return () => clearInterval(interval);
    }, []);

    // Auto-track page visits
    useEffect(() => {
        if (!tour.active || !pathname) return;

        setTour(prev => {
            if (prev.visitedPages.has(pathname)) return prev;

            const newVisited = new Set(prev.visitedPages);
            newVisited.add(pathname);

            // Find current step index
            const currentStepHref = TOUR_STEPS[prev.currentStep]?.href;

            // If user visited the recommended page, advance to next unvisited
            let nextStep = prev.currentStep;
            if (pathname === currentStepHref) {
                // Find next unvisited step
                for (let i = prev.currentStep + 1; i < TOUR_STEPS.length; i++) {
                    if (!newVisited.has(TOUR_STEPS[i].href)) {
                        nextStep = i;
                        break;
                    }
                    if (i === TOUR_STEPS.length - 1) nextStep = TOUR_STEPS.length; // all done
                }
            }

            // Check if all pages visited
            const allVisited = TOUR_STEPS.every(s => newVisited.has(s.href));
            if (allVisited) {
                localStorage.setItem("fireside_tour_done", "1");
                return { active: false, currentStep: TOUR_STEPS.length, visitedPages: newVisited };
            }

            return { active: true, currentStep: nextStep, visitedPages: newVisited };
        });
    }, [pathname, tour.active]);

    const advanceTour = useCallback(() => {
        setTour(prev => {
            if (!prev.active) return prev;

            const nextStep = prev.currentStep + 1;
            if (nextStep >= TOUR_STEPS.length) {
                localStorage.setItem("fireside_tour_done", "1");
                return { active: false, currentStep: nextStep, visitedPages: prev.visitedPages };
            }
            return { ...prev, currentStep: nextStep };
        });
    }, []);

    const skipTour = useCallback(() => {
        localStorage.setItem("fireside_tour_done", "1");
        setTour({ active: false, currentStep: TOUR_STEPS.length, visitedPages: new Set(TOUR_STEPS.map(s => s.href)) });
    }, []);

    const isRecommended = useCallback((href: string) => {
        if (!tour.active) return false;
        const step = TOUR_STEPS[tour.currentStep];
        return step?.href === href && !tour.visitedPages.has(href);
    }, [tour.active, tour.currentStep, tour.visitedPages]);

    const isVisited = useCallback((href: string) => {
        return tour.visitedPages.has(href);
    }, [tour.visitedPages]);

    return (
        <TourContext.Provider value={{ tour, advanceTour, skipTour, isRecommended, isVisited }}>
            {children}
        </TourContext.Provider>
    );
}

/**
 * Tour Overlay — gentle, helpful bottom bar.
 */
export function TourOverlay() {
    const { tour, advanceTour, skipTour } = useTour();
    const pathname = usePathname();
    const router = useRouter();

    if (!tour.active) return null;

    const step = TOUR_STEPS[tour.currentStep];
    if (!step) return null;

    const isOnRecommendedPage = pathname === step.href;
    const visitedCount = tour.visitedPages.size;
    const totalSteps = TOUR_STEPS.length;

    return (
        <div
            style={{
                position: "fixed",
                bottom: 20,
                left: "50%",
                transform: "translateX(-50%)",
                zIndex: 9000,
                background: "rgba(10, 10, 15, 0.95)",
                border: "1px solid rgba(251, 191, 36, 0.25)",
                borderRadius: 16,
                padding: "16px 28px",
                display: "flex",
                alignItems: "center",
                gap: 18,
                backdropFilter: "blur(16px)",
                boxShadow: "0 12px 48px rgba(0,0,0,0.6), 0 0 20px rgba(251,191,36,0.08)",
                maxWidth: 580,
                width: "90vw",
            }}
        >
            {/* Step icon */}
            <div style={{
                fontSize: 24,
                background: "rgba(251,191,36,0.12)",
                borderRadius: 10,
                width: 44,
                height: 44,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
            }}>
                {step.icon}
            </div>

            {/* Content */}
            <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 13, color: "#fff", fontWeight: 700, marginBottom: 2 }}>
                    {isOnRecommendedPage ? `You're here! ${step.label}` : `Try: ${step.label}`}
                </div>
                <div style={{ fontSize: 11, color: "#8585a0", lineHeight: 1.4 }}>
                    {step.description}
                </div>

                {/* Progress — visited count */}
                <div style={{ display: "flex", gap: 5, marginTop: 8, alignItems: "center" }}>
                    {TOUR_STEPS.map((s, i) => (
                        <div
                            key={i}
                            style={{
                                width: tour.visitedPages.has(s.href) ? 16 : 8,
                                height: 6,
                                borderRadius: 3,
                                background: tour.visitedPages.has(s.href)
                                    ? "#FBBF24"
                                    : i === tour.currentStep
                                        ? "rgba(251,191,36,0.4)"
                                        : "rgba(255,255,255,0.1)",
                                transition: "all 0.3s ease",
                            }}
                        />
                    ))}
                    <span style={{ fontSize: 10, color: "#55556a", marginLeft: 6 }}>
                        {visitedCount}/{totalSteps}
                    </span>
                </div>
            </div>

            {/* Actions */}
            <div style={{ display: "flex", flexDirection: "column", gap: 6, flexShrink: 0 }}>
                {isOnRecommendedPage ? (
                    <button
                        onClick={advanceTour}
                        style={{
                            background: "#FBBF24",
                            border: "none",
                            color: "#0a0a0f",
                            fontSize: 13,
                            fontWeight: 700,
                            padding: "8px 20px",
                            borderRadius: 8,
                            cursor: "pointer",
                            whiteSpace: "nowrap",
                        }}
                    >
                        {tour.currentStep < TOUR_STEPS.length - 1 ? "Next →" : "Done ✓"}
                    </button>
                ) : (
                    <button
                        onClick={() => router.push(step.href)}
                        style={{
                            background: "rgba(251,191,36,0.12)",
                            border: "1px solid rgba(251,191,36,0.3)",
                            color: "#FBBF24",
                            fontSize: 13,
                            fontWeight: 700,
                            padding: "8px 20px",
                            borderRadius: 8,
                            cursor: "pointer",
                            whiteSpace: "nowrap",
                        }}
                    >
                        Go →
                    </button>
                )}
                <button
                    onClick={skipTour}
                    style={{
                        background: "transparent",
                        border: "none",
                        color: "#44445a",
                        fontSize: 10,
                        padding: "3px 8px",
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
