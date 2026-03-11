"use client";

import PersonalityForm from "@/components/PersonalityForm";
import { useToast } from "@/components/Toast";

export default function PersonalityPage() {
    const { toast } = useToast();

    const handleSave = (values: { name: string; role: string; tone: string; skills: string[]; boundaries: string[] }) => {
        console.log("Personality saved:", values);
        toast("Personality saved! Your AI will use these settings.", "success");
    };

    return (
        <div className="max-w-xl mx-auto">
            <div className="mb-6">
                <h1 className="text-2xl font-bold text-white flex items-center gap-2">
                    <span>🧠</span> Personality
                </h1>
                <p className="text-sm text-[var(--color-rune-dim)] mt-1">
                    Change how your AI talks and what it&apos;s good at.
                </p>
            </div>

            <PersonalityForm onSave={handleSave} />
        </div>
    );
}
