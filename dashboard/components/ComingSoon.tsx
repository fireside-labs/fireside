"use client";

/**
 * 🚧 Coming Soon Page — Sprint 15 F5.
 * Reusable component for pages that aren't wired to real data yet.
 */

interface ComingSoonProps {
    title: string;
    icon: string;
    description?: string;
}

export default function ComingSoon({ title, icon, description }: ComingSoonProps) {
    return (
        <div className="max-w-2xl mx-auto mt-16 text-center">
            <div className="glass-card p-12">
                <span className="text-5xl block mb-4">{icon}</span>
                <h2 className="text-xl font-bold text-white mb-2">{title}</h2>
                <p className="text-sm text-[var(--color-rune-dim)] mb-6">
                    {description || "This feature is coming soon. Start using your AI and this page will fill with real data."}
                </p>
                <div
                    style={{
                        display: "inline-block",
                        padding: "6px 16px",
                        borderRadius: 8,
                        background: "rgba(245, 158, 11, 0.1)",
                        border: "1px solid rgba(245, 158, 11, 0.2)",
                        color: "#F59E0B",
                        fontSize: 12,
                        fontWeight: 600,
                    }}
                >
                    🚧 Coming Soon
                </div>
            </div>
        </div>
    );
}
