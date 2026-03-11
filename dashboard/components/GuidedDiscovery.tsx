"use client";

import { useState } from "react";
import Link from "next/link";

interface Suggestion {
    icon: string;
    title: string;
    description: string;
    href: string;
}

const SUGGESTIONS: Suggestion[] = [
    {
        icon: "🧬",
        title: "Give your agent a personality",
        description: "Soul Editor →",
        href: "/soul",
    },
    {
        icon: "⚡",
        title: "Switch to a bigger model",
        description: "Models →",
        href: "/models",
    },
    {
        icon: "🌐",
        title: "Add a second machine to your mesh",
        description: "Add Node →",
        href: "/nodes",
    },
];

export default function GuidedDiscovery() {
    const [dismissed, setDismissed] = useState(false);

    if (dismissed) return null;

    return (
        <div className="guided-discovery">
            <div className="flex items-center justify-between mb-3">
                <h3 className="text-white text-sm font-semibold">What&apos;s next?</h3>
                <button
                    onClick={() => setDismissed(true)}
                    className="text-[var(--color-rune-dim)] hover:text-white text-xs transition-colors"
                >
                    ✕
                </button>
            </div>
            <div className="space-y-2">
                {SUGGESTIONS.map((s) => (
                    <Link key={s.href} href={s.href}>
                        <div className="guided-suggestion">
                            <span className="text-lg">{s.icon}</span>
                            <div>
                                <p className="text-sm text-white font-medium">{s.title}</p>
                                <p className="text-xs text-[var(--color-neon)]">{s.description}</p>
                            </div>
                        </div>
                    </Link>
                ))}
            </div>
        </div>
    );
}
