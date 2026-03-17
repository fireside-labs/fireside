"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useEffect } from "react";
import { ThemeToggle } from "@/components/ThemeToggle";
import SystemStatus from "@/components/SystemStatus";
import AgentSidebarList from "@/components/AgentSidebarList";
import { useTour } from "@/components/GuidedTour";

interface NavItem { href: string; label: string; icon: string }
interface NavSection { title: string; items: NavItem[] }

const NAV_SECTIONS: NavSection[] = [
    {
        title: "Your AI",
        items: [
            { href: "/", label: "Hub", icon: "🔥" },
            { href: "/chat", label: "Chat", icon: "💬" },
            { href: "/brains", label: "Brain", icon: "🧠" },
            { href: "/skills", label: "Skills", icon: "✦" },
            { href: "/personality", label: "Personality", icon: "🦊" },
        ],
    },
    {
        title: "System",
        items: [
            { href: "/config", label: "Settings", icon: "⚙" },
        ],
    },
];

export function Sidebar() {
    const pathname = usePathname();
    const [mobileOpen, setMobileOpen] = useState(false);
    const [aiName, setAiName] = useState("My AI");
    const { tour, isRecommended, isVisited } = useTour();

    // Close sidebar on nav + load name
    useEffect(() => {
        setMobileOpen(false);
    }, [pathname]);

    useEffect(() => {
        const agentName = localStorage.getItem("fireside_agent_name");
        if (agentName) {
            setAiName(agentName);
        } else {
            const name = localStorage.getItem("fireside_user_name");
            if (name) setAiName(name + "'s AI");
        }
    }, []);

    return (
        <>
            {/* ─── Mobile Hamburger ─── */}
            <button
                className="mobile-hamburger"
                onClick={() => setMobileOpen(true)}
                aria-label="Open menu"
            >
                ☰
            </button>

            {/* ─── Backdrop ─── */}
            <div
                className={"sidebar-backdrop" + (mobileOpen ? " active" : "")}
                onClick={() => setMobileOpen(false)}
            />

            {/* ─── Sidebar ─── */}
            <aside className={"sidebar fixed left-0 top-0 bottom-0 w-64 bg-[var(--color-void-light)] border-r border-[var(--color-glass-border)] flex flex-col z-50" + (mobileOpen ? " sidebar-open" : "")}>
                {/* ─── Header ─── */}
                <div className="p-6 border-b border-[var(--color-glass-border)]">
                    <Link href="/" className="block">
                        <h1 className="text-xl font-bold font-[var(--font-family-heading)] tracking-tight">
                            <span className="text-[var(--color-neon)]">🔥</span> Fireside
                        </h1>
                    </Link>
                </div>

                {/* ─── Agent Status ─── */}
                <div className="px-6 py-4 border-b border-[var(--color-glass-border)]">
                    <div className="flex items-center gap-2">
                        <span className="text-sm text-[var(--color-rune-dim)]">Your AI:</span>
                        <span className="text-sm font-medium text-white">{aiName}</span>
                        <div className="status-online" />
                        <span className="text-xs text-[var(--color-neon)] ml-auto">Online</span>
                    </div>
                </div>

                {/* ─── Navigation (Grouped) ─── */}
                <nav className="flex-1 px-3 py-3 overflow-y-auto">
                    {NAV_SECTIONS.map((section) => (
                        <div key={section.title} className="mb-3">
                            <p className="px-4 py-1 text-[10px] uppercase tracking-widest text-[var(--color-rune-dim)] font-semibold">
                                {section.title}
                            </p>
                            <div className="space-y-0.5">
                                {section.items.map((item) => {
                                    const isActive =
                                        (item.href === "/" && pathname === "/") ||
                                        (item.href !== "/" && pathname?.startsWith(item.href));
                                    const recommended = isRecommended(item.href);
                                    const showNewBadge = tour.active && !isVisited(item.href) && !isActive;

                                    return (
                                        <Link
                                            key={item.href}
                                            href={item.href}
                                            className={`
                                                flex items-center gap-3 px-4 py-2 rounded-lg text-sm font-medium
                                                transition-all duration-200
                                                ${isActive
                                                    ? "sidebar-item-active"
                                                    : recommended
                                                        ? "sidebar-item-recommend text-[var(--color-neon)]"
                                                        : "text-[var(--color-rune)] hover:text-white hover:bg-[var(--color-glass-hover)]"
                                                }
                                            `}
                                        >
                                            <span className="text-lg w-6 text-center">{item.icon}</span>
                                            {item.label}
                                            {showNewBadge && <span className="tour-new-badge">NEW</span>}
                                        </Link>
                                    );
                                })}
                            </div>
                        </div>
                    ))}

                    {/* ─── Your Team ─── */}
                    <div className="mb-3">
                        <p className="px-4 py-1 text-[10px] uppercase tracking-widest text-[var(--color-rune-dim)] font-semibold">
                            Your Team
                        </p>
                        <AgentSidebarList />
                    </div>
                </nav>

                {/* ─── Footer ─── */}
                <div className="p-4 border-t border-[var(--color-glass-border)]">
                    <SystemStatus className="mb-2" />
                    <div className="flex items-center justify-between">
                        <p className="text-xs text-[var(--color-rune-dim)]">
                            Fireside v2.0
                        </p>
                        <ThemeToggle />
                    </div>
                </div>
            </aside>
        </>
    );
}

