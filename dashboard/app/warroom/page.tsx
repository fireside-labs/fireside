"use client";

import { useState, useEffect } from "react";
import {
    getHypotheses,
    generateHypotheses,
    testHypothesis,
    getSelfModel,
    triggerReflect,
    getPredictions,
    getWisdom,
    rebuildWisdom,
    getBeliefShadows,
    Hypothesis,
    SelfModel as SelfModelType,
    PredictionScore,
    WisdomPrompt,
    BeliefShadow,
} from "@/lib/api";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useToast } from "@/components/Toast";
import HypothesisCard from "@/components/HypothesisCard";
import PredictionChart from "@/components/PredictionChart";
import SelfModelCard from "@/components/SelfModelCard";
import EventStream from "@/components/EventStream";
import WisdomViewer from "@/components/WisdomViewer";
import BeliefRadar from "@/components/BeliefRadar";

export default function WarRoomPage() {
    const [hypotheses, setHypotheses] = useState<Hypothesis[]>([]);
    const [selfModel, setSelfModel] = useState<SelfModelType | null>(null);
    const [predictions, setPredictions] = useState<PredictionScore[]>([]);
    const [wisdom, setWisdom] = useState<WisdomPrompt | null>(null);
    const [shadows, setShadows] = useState<BeliefShadow[]>([]);
    const [generating, setGenerating] = useState(false);
    const [reflecting, setReflecting] = useState(false);
    const { events, connected } = useWebSocket();
    const { toast } = useToast();

    useEffect(() => {
        getHypotheses().then(setHypotheses);
        getSelfModel().then(setSelfModel);
        getPredictions().then(setPredictions);
        getWisdom().then(setWisdom);
        getBeliefShadows().then(setShadows);
    }, []);

    const handleDreamCycle = async () => {
        setGenerating(true);
        try {
            const result = await generateHypotheses();
            toast("Dream cycle complete — " + result.count + " hypotheses generated", "success");
            const updated = await getHypotheses();
            setHypotheses(updated);
        } catch {
            toast("Dream cycle failed", "error");
        }
        setGenerating(false);
    };

    const handleTest = async (id: string, result: "confirmed" | "refuted") => {
        try {
            await testHypothesis(id, result);
            setHypotheses((prev) =>
                prev.map((h) => (h.id === id ? { ...h, status: result } : h))
            );
            toast("Hypothesis " + result, result === "confirmed" ? "success" : "warning");
        } catch {
            toast("Failed to update hypothesis", "error");
        }
    };

    const handleReflect = async () => {
        setReflecting(true);
        try {
            await triggerReflect();
            toast("Reflection cycle triggered", "success");
            const updated = await getSelfModel();
            setSelfModel(updated);
        } catch {
            toast("Reflection failed", "error");
        }
        setReflecting(false);
    };

    const handleRebuildWisdom = async () => {
        await rebuildWisdom();
        toast("Wisdom prompt rebuilding...", "info");
    };

    const activeCount = hypotheses.filter((h) => h.status === "active").length;
    const confirmedCount = hypotheses.filter((h) => h.status === "confirmed").length;

    return (
        <div className="page-enter">
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
                <div>
                    <h1 className="text-3xl font-bold mb-1">
                        <span className="text-[var(--color-neon)]">⚔</span> War Room
                    </h1>
                    <p className="text-sm text-[var(--color-rune-dim)]">
                        {activeCount} active hypotheses · {confirmedCount} confirmed · {events.length} events
                    </p>
                </div>
                <button
                    onClick={handleDreamCycle}
                    disabled={generating}
                    className="btn-neon text-sm"
                    style={{ opacity: generating ? 0.5 : 1 }}
                >
                    {generating ? "Dreaming..." : "🧪 Dream Cycle"}
                </button>
            </div>

            {/* Main Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
                {/* Left Column — Hypotheses */}
                <div className="lg:col-span-2 space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {hypotheses.map((h) => (
                            <HypothesisCard key={h.id} hypothesis={h} onTest={handleTest} />
                        ))}
                    </div>

                    {/* Predictions Chart */}
                    <PredictionChart data={predictions} />

                    {/* Wisdom Viewer (Sprint 4) */}
                    {wisdom && <WisdomViewer wisdom={wisdom} onRebuild={handleRebuildWisdom} />}
                </div>

                {/* Right Column — Self-Model + Belief Shadows + Event Stream */}
                <div className="space-y-4">
                    {selfModel && (
                        <SelfModelCard
                            model={selfModel}
                            onReflect={handleReflect}
                            reflecting={reflecting}
                        />
                    )}

                    {/* Belief Shadows (Sprint 4) */}
                    {shadows.length > 0 && <BeliefRadar shadows={shadows} />}

                    <EventStream events={events} connected={connected} />
                </div>
            </div>
        </div>
    );
}
