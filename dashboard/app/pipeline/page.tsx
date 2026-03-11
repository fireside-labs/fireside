"use client";

import { useEffect, useState } from "react";
import { getPipelines } from "@/lib/api";
import type { Pipeline } from "@/lib/api";
import TaskWizard from "@/components/TaskWizard";
import { useToast } from "@/components/Toast";

const STAGE_LABELS: Record<string, string> = {
    spec: "Planning...",
    build: "Working on it...",
    test: "Checking quality...",
    review: "Getting a second opinion...",
    complete: "Done!",
};

export default function TaskBuilderPage() {
    const [pipelines, setPipelines] = useState<Pipeline[]>([]);
    const [loading, setLoading] = useState(true);
    const [showWizard, setShowWizard] = useState(false);
    const { toast } = useToast();

    useEffect(() => {
        getPipelines().then((data) => {
            setPipelines(data);
            setLoading(false);
        });
    }, []);

    const active = pipelines.filter((p) => p.status === "running");
    const completed = pipelines.filter((p) => p.status === "completed");
    const needsHelp = pipelines.filter((p) => p.status === "escalated");

    const handleCreate = (task: { description: string; quality: number; notification: string }) => {
        toast(`Task started: "${task.description}"`, "success");
        setShowWizard(false);
    };

    return (
        <div className="max-w-3xl mx-auto">
            <div className="mb-6 flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-white flex items-center gap-2">
                        <span>📋</span> Task Builder
                    </h1>
                    <p className="text-sm text-[var(--color-rune-dim)] mt-1">
                        Give your AI a job. It&apos;ll work on it step by step.
                    </p>
                </div>
                <button onClick={() => setShowWizard(true)} className="btn-neon px-5 py-2.5 text-sm">
                    + Create New Task
                </button>
            </div>

            {showWizard && <TaskWizard onClose={() => setShowWizard(false)} onCreate={handleCreate} />}

            {loading ? (
                <div className="space-y-4">
                    {[1, 2, 3].map((i) => (
                        <div key={i} className="glass-card p-5 animate-pulse h-32" />
                    ))}
                </div>
            ) : (
                <div className="space-y-6">
                    {/* Needs Your Help */}
                    {needsHelp.length > 0 && (
                        <div>
                            <h3 className="text-sm text-[var(--color-warning)] font-semibold mb-3">⚠️ Needs Your Help</h3>
                            <div className="space-y-3">
                                {needsHelp.map((p) => (
                                    <div key={p.id} className="glass-card p-5" style={{ borderColor: "var(--color-warning)", borderWidth: 1 }}>
                                        <h4 className="text-white font-semibold mb-1">⚠️ &quot;{p.title}&quot;</h4>
                                        <p className="text-sm text-[var(--color-rune-dim)] mb-3">
                                            Your AI got stuck and needs guidance.
                                        </p>
                                        <div className="flex gap-2">
                                            <button className="btn-neon px-4 py-1.5 text-xs">Help Your AI</button>
                                            <button className="px-4 py-1.5 text-xs text-[var(--color-rune-dim)] hover:text-white border border-[var(--color-glass-border)] rounded-lg transition-colors">Cancel Task</button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Active */}
                    {active.length > 0 && (
                        <div>
                            <h3 className="text-sm text-[var(--color-rune-dim)] font-semibold mb-3">Active</h3>
                            <div className="space-y-3">
                                {active.map((p) => {
                                    const currentStep = p.iteration || 1;
                                    const totalSteps = p.max_iterations || 7;
                                    const progress = (currentStep / totalSteps) * 100;
                                    const statusText = p.current_stage ? (STAGE_LABELS[p.current_stage] || p.current_stage) : "Working...";

                                    return (
                                        <div key={p.id} className="glass-card p-5">
                                            <h4 className="text-white font-semibold mb-2">📝 &quot;{p.title}&quot;</h4>
                                            <div className="mb-2">
                                                <div className="flex justify-between text-xs text-[var(--color-rune-dim)] mb-1">
                                                    <span>Step {currentStep} of {totalSteps}</span>
                                                    <span>{statusText}</span>
                                                </div>
                                                <div className="h-2 rounded-full bg-[var(--color-glass)]">
                                                    <div className="h-2 rounded-full bg-[var(--color-neon)] transition-all" style={{ width: `${progress}%` }} />
                                                </div>
                                            </div>
                                            <div className="flex gap-2 mt-3">
                                                <a href={`/pipeline/${p.id}`} className="text-xs text-[var(--color-neon)] hover:underline">View Details</a>
                                                <button className="text-xs text-[var(--color-rune-dim)] hover:text-white transition-colors">Pause</button>
                                                <button className="text-xs text-[var(--color-rune-dim)] hover:text-white transition-colors">Cancel</button>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    )}

                    {/* Completed */}
                    {completed.length > 0 && (
                        <div>
                            <h3 className="text-sm text-[var(--color-rune-dim)] font-semibold mb-3">Completed</h3>
                            <div className="space-y-3">
                                {completed.map((p) => (
                                    <div key={p.id} className="glass-card p-5">
                                        <div className="flex items-center justify-between">
                                            <div>
                                                <h4 className="text-white font-semibold mb-1">✅ &quot;{p.title}&quot;</h4>
                                                <p className="text-xs text-[var(--color-rune-dim)]">
                                                    Finished · {p.iteration} steps
                                                </p>
                                                {p.lessons && p.lessons.length > 0 && (
                                                    <p className="text-xs text-[var(--color-neon)] mt-1 italic">
                                                        Lesson learned: &quot;{p.lessons[0]}&quot;
                                                    </p>
                                                )}
                                            </div>
                                            <a href={`/pipeline/${p.id}`} className="text-xs text-[var(--color-rune-dim)] hover:text-white border border-[var(--color-glass-border)] px-3 py-1.5 rounded-lg transition-colors">
                                                View
                                            </a>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Empty state */}
                    {pipelines.length === 0 && (
                        <div className="glass-card p-10 text-center">
                            <span className="text-4xl block mb-3">📋</span>
                            <h3 className="text-white font-semibold mb-1">No tasks yet</h3>
                            <p className="text-sm text-[var(--color-rune-dim)] mb-4">
                                Create your first task and watch your AI work through it step by step.
                            </p>
                            <button onClick={() => setShowWizard(true)} className="btn-neon px-5 py-2 text-sm">
                                Create New Task
                            </button>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
