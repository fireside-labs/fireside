"use client";

/**
 * 🗺️ Guided Tour — RPG Zone Discovery.
 *
 * After onboarding, the companion guides the user through each tab:
 * - Bottom tip bar with companion voice + progress
 * - Pulsing sidebar glow on recommended next tab
 * - "NEW" badges on unvisited tabs
 * - Per-page first-visit discovery cards via useFirstVisit hook
 * - Auto-marks pages as visited when user navigates
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
    companionName: string;
    companionEmoji: string;
}

// ── Species → emoji map ──
const SPECIES_EMOJI: Record<string, string> = {
    cat: "🐱", dog: "🐶", penguin: "🐧", fox: "🦊", owl: "🦉", dragon: "🐉",
};

// ── Tour steps — matches current sidebar nav ──
const TOUR_STEPS = [
    {
        href: "/",
        label: "The Hearth",
        icon: "🔥",
        description: "This is home base. Your status, recent activity, and quick actions — all in one place.",
        companionLine: "Welcome to the hearth. Everything starts here.",
    },
    {
        href: "/pipeline",
        label: "The Forge",
        icon: "⚡",
        description: "Run multi-step AI pipelines. Give me a task and I'll break it down.",
        companionLine: "The Forge is where we build. Describe what you need — I'll figure out the steps.",
    },
    {
        href: "/brains",
        label: "Brain Lab",
        icon: "🧠",
        description: "Choose and manage the AI model that powers me.",
        companionLine: "This is my brain. You can upgrade it, swap models, or check what's running.",
    },
    {
        href: "/skills",
        label: "Skill Tree",
        icon: "✦",
        description: "My abilities. The more skills I have, the more I can do for you.",
        companionLine: "Each skill unlocks new things I can do. Browse what's available.",
    },
    {
        href: "/personality",
        label: "Soul Mirror",
        icon: "🎭",
        description: "Shape who I am — my tone, quirks, and how I communicate.",
        companionLine: "This is where you shape my personality. Make me yours.",
    },
    {
        href: "/config",
        label: "Deep Config",
        icon: "⚙",
        description: "Connections, API keys, advanced settings. Power-user territory.",
        companionLine: "The deep config. Most people won't need this often, but it's here when you do.",
    },
];

const TourContext = createContext<TourContextType>({
    tour: { active: false, currentStep: 0, visitedPages: new Set() },
    advanceTour: () => { },
    skipTour: () => { },
    isRecommended: () => false,
    isVisited: () => false,
    companionName: "Ember",
    companionEmoji: "🦊",
});

export function useTour() {
    return useContext(TourContext);
}

// ── First-visit hook for per-page discovery cards ──
export function useFirstVisit(pageKey: string) {
    const storageKey = `fireside_visited_${pageKey.replace(/\//g, "_")}`;
    const [isFirstVisit, setIsFirstVisit] = useState(false);

    useEffect(() => {
        const visited = localStorage.getItem(storageKey);
        if (!visited) {
            setIsFirstVisit(true);
        }
    }, [storageKey]);

    const dismiss = useCallback(() => {
        localStorage.setItem(storageKey, "1");
        setIsFirstVisit(false);
    }, [storageKey]);

    return { isFirstVisit, dismiss };
}

// ── Discovery card data per page ──
export const DISCOVERY_CARDS: Record<string, {
    title: string;
    icon: string;
    companionLine: string;
    features: string[];
}> = {
    "/": {
        title: "The Hearth",
        icon: "🔥",
        companionLine: "This is where we live. Your dashboard, your status, your command center.",
        features: [
            "See your AI's status at a glance",
            "Quick-start a pipeline or open chat",
            "Track recent activity and agent status",
        ],
    },
    "/pipeline": {
        title: "The Forge",
        icon: "⚡",
        companionLine: "Describe a task and I'll break it into steps. Each step runs through my brain.",
        features: [
            "Type any task — I'll auto-detect the right approach",
            "Watch stages execute in real-time",
            "Review outputs at each stage",
        ],
    },
    "/brains": {
        title: "Brain Lab",
        icon: "🧠",
        companionLine: "This is what makes me think. You can swap brains, download new ones, or check what's loaded.",
        features: [
            "See which model is currently active",
            "Download or switch AI models",
            "Monitor VRAM usage and performance",
        ],
    },
    "/skills": {
        title: "Skill Tree",
        icon: "✦",
        companionLine: "Skills are my abilities. Each one lets me do something new for you.",
        features: [
            "Browse available skills",
            "Enable or disable capabilities",
            "See what tools I can use in pipelines",
        ],
    },
    "/personality": {
        title: "Soul Mirror",
        icon: "🎭",
        companionLine: "Shape who I am. My voice, my style, my quirks — it's all here.",
        features: [
            "Adjust my communication style",
            "Set personality traits and tone",
            "Preview how I'll respond",
        ],
    },
    "/config": {
        title: "Deep Config",
        icon: "⚙",
        companionLine: "Power-user territory. Connections, API keys, and everything under the hood.",
        features: [
            "Manage network and API connections",
            "Configure advanced AI settings",
            "Export or import your setup",
        ],
    },
};

export function TourProvider({ children }: { children: React.ReactNode }) {
    const [tour, setTour] = useState<TourState>({
        active: false,
        currentStep: 0,
        visitedPages: new Set(),
    });
    const [companionName, setCompanionName] = useState("Ember");
    const [companionEmoji, setCompanionEmoji] = useState("🦊");
    const pathname = usePathname();

    // Load companion info
    useEffect(() => {
        const name = localStorage.getItem("fireside_companion_name") || localStorage.getItem("fireside_agent_name");
        const species = localStorage.getItem("fireside_companion_species");
        if (name) setCompanionName(name);
        if (species && SPECIES_EMOJI[species]) setCompanionEmoji(SPECIES_EMOJI[species]);
    }, []);

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

            const currentStepHref = TOUR_STEPS[prev.currentStep]?.href;
            let nextStep = prev.currentStep;

            if (pathname === currentStepHref) {
                for (let i = prev.currentStep + 1; i < TOUR_STEPS.length; i++) {
                    if (!newVisited.has(TOUR_STEPS[i].href)) {
                        nextStep = i;
                        break;
                    }
                    if (i === TOUR_STEPS.length - 1) nextStep = TOUR_STEPS.length;
                }
            }

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
        <TourContext.Provider value={{ tour, advanceTour, skipTour, isRecommended, isVisited, companionName, companionEmoji }}>
            {children}
        </TourContext.Provider>
    );
}

/**
 * Tour Overlay — companion-voiced bottom bar.
 */
export function TourOverlay() {
    const { tour, advanceTour, skipTour, companionName, companionEmoji } = useTour();
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
                maxWidth: 620,
                width: "90vw",
            }}
        >
            {/* Companion avatar */}
            <div style={{
                fontSize: 28,
                background: "rgba(251,191,36,0.12)",
                borderRadius: 12,
                width: 48,
                height: 48,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
            }}>
                {companionEmoji}
            </div>

            {/* Content */}
            <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 13, color: "#fff", fontWeight: 700, marginBottom: 2 }}>
                    {isOnRecommendedPage
                        ? `${step.icon} ${step.label}`
                        : `${companionName}: "Let me show you ${step.label}"`
                    }
                </div>
                <div style={{ fontSize: 11, color: "#8585a0", lineHeight: 1.4 }}>
                    {isOnRecommendedPage ? step.companionLine : step.description}
                </div>

                {/* Progress dots */}
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

/**
 * DiscoveryCard — a one-time glassmorphism card shown on first visit to a page.
 * Usage: <DiscoveryCard pageKey="/pipeline" />
 */
export function DiscoveryCard({ pageKey }: { pageKey: string }) {
    const { isFirstVisit, dismiss } = useFirstVisit(pageKey);
    const { companionName, companionEmoji } = useTour();

    const card = DISCOVERY_CARDS[pageKey];
    if (!isFirstVisit || !card) return null;

    return (
        <div
            style={{
                background: "rgba(251, 191, 36, 0.04)",
                border: "1px solid rgba(251, 191, 36, 0.15)",
                borderRadius: 16,
                padding: "20px 24px",
                marginBottom: 20,
                backdropFilter: "blur(12px)",
                position: "relative",
                animation: "fadeIn 0.4s ease-out",
            }}
        >
            {/* Dismiss */}
            <button
                onClick={dismiss}
                style={{
                    position: "absolute",
                    top: 12,
                    right: 16,
                    background: "transparent",
                    border: "none",
                    color: "rgba(255,255,255,0.3)",
                    fontSize: 16,
                    cursor: "pointer",
                    padding: "4px 8px",
                    lineHeight: 1,
                }}
                aria-label="Dismiss"
            >
                ✕
            </button>

            {/* Header */}
            <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 12 }}>
                <span style={{
                    fontSize: 28,
                    background: "rgba(251,191,36,0.12)",
                    borderRadius: 10,
                    width: 44,
                    height: 44,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                }}>
                    {card.icon}
                </span>
                <div>
                    <div style={{ fontSize: 16, fontWeight: 700, color: "#fff" }}>
                        {card.title}
                    </div>
                    <div style={{ fontSize: 11, color: "rgba(251,191,36,0.7)" }}>
                        First time here!
                    </div>
                </div>
            </div>

            {/* Companion speech */}
            <div style={{
                display: "flex",
                alignItems: "flex-start",
                gap: 10,
                background: "rgba(255,255,255,0.03)",
                borderRadius: 10,
                padding: "12px 14px",
                marginBottom: 14,
            }}>
                <span style={{ fontSize: 20, flexShrink: 0 }}>{companionEmoji}</span>
                <div>
                    <span style={{ fontSize: 11, fontWeight: 600, color: "rgba(251,191,36,0.8)" }}>{companionName}:</span>
                    <p style={{ fontSize: 13, color: "#c0c0d0", margin: "4px 0 0", lineHeight: 1.5 }}>
                        &ldquo;{card.companionLine}&rdquo;
                    </p>
                </div>
            </div>

            {/* Feature list */}
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {card.features.map((f, i) => (
                    <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, color: "#8585a0" }}>
                        <span style={{ color: "#FBBF24", fontSize: 10 }}>◆</span>
                        {f}
                    </div>
                ))}
            </div>

            {/* Dismiss CTA */}
            <button
                onClick={dismiss}
                style={{
                    marginTop: 16,
                    background: "rgba(251,191,36,0.1)",
                    border: "1px solid rgba(251,191,36,0.2)",
                    color: "#FBBF24",
                    fontSize: 12,
                    fontWeight: 600,
                    padding: "8px 20px",
                    borderRadius: 8,
                    cursor: "pointer",
                    width: "100%",
                }}
            >
                Got it — let me explore {card.icon}
            </button>
        </div>
    );
}
