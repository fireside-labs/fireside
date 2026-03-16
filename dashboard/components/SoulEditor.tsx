"use client";

import { useState, useEffect, useCallback } from "react";
import { getSoul, putSoul } from "@/lib/api";

const SOUL_TABS = [
    { key: "IDENTITY.md", label: "Identity", icon: "⚡" },
    { key: "SOUL.md", label: "Soul", icon: "🜂" },
    { key: "USER.md", label: "User", icon: "👤" },
];

interface SoulEditorProps {
    initialTab?: string;
}

export function SoulEditor({ initialTab }: SoulEditorProps) {
    const [activeTab, setActiveTab] = useState(initialTab || SOUL_TABS[0].key);
    const [content, setContent] = useState("");
    const [original, setOriginal] = useState("");
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);

    const loadSoul = useCallback(async (filename: string) => {
        setLoading(true);
        const data = await getSoul(filename);
        setContent(data);
        setOriginal(data);
        setLoading(false);
    }, []);

    useEffect(() => {
        loadSoul(activeTab);
    }, [activeTab, loadSoul]);

    async function handleSave() {
        setSaving(true);
        try {
            await putSoul(activeTab, content);
            setOriginal(content);
            showToast("Soul file saved", "success");
        } catch {
            showToast("Failed to save", "error");
        } finally {
            setSaving(false);
        }
    }

    function showToast(message: string, type: "success" | "error") {
        setToast({ message, type });
        setTimeout(() => setToast(null), 3000);
    }

    const hasChanges = content !== original;

    return (
        <div>
            {/* ─── Tabs ─── */}
            <div className="flex gap-1 mb-6">
                {SOUL_TABS.map((tab) => (
                    <button
                        key={tab.key}
                        onClick={() => setActiveTab(tab.key)}
                        className={`
              px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 cursor-pointer
              ${activeTab === tab.key
                                ? "bg-[var(--color-neon-glow)] text-[var(--color-neon)] border border-[rgba(0,255,136,0.15)]"
                                : "text-[var(--color-rune)] hover:text-white hover:bg-[var(--color-glass-hover)]"
                            }
            `}
                    >
                        {tab.icon} {tab.label}
                    </button>
                ))}

                <div className="ml-auto flex items-center gap-3">
                    {hasChanges && (
                        <span className="text-xs text-[var(--color-warning)]">● Unsaved changes</span>
                    )}
                    <button
                        onClick={handleSave}
                        disabled={saving || !hasChanges}
                        className={`btn-neon text-xs ${!hasChanges ? "opacity-40 cursor-not-allowed" : ""}`}
                    >
                        {saving ? "Saving..." : "Save"}
                    </button>
                </div>
            </div>

            {/* ─── Split Pane ─── */}
            {loading ? (
                <div className="text-center py-20 text-[var(--color-rune-dim)]">Loading soul file...</div>
            ) : (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 min-h-[500px]">
                    {/* Editor */}
                    <div className="flex flex-col">
                        <div className="text-xs text-[var(--color-rune-dim)] mb-2 font-medium uppercase tracking-wider">
                            Edit
                        </div>
                        <textarea
                            value={content}
                            onChange={(e) => setContent(e.target.value)}
                            className="code-editor flex-1 min-h-[500px]"
                            spellCheck={false}
                        />
                    </div>

                    {/* Preview */}
                    <div className="flex flex-col">
                        <div className="text-xs text-[var(--color-rune-dim)] mb-2 font-medium uppercase tracking-wider">
                            Preview
                        </div>
                        <div className="glass-card p-6 flex-1 overflow-auto markdown-preview">
                            <MarkdownPreview content={content} />
                        </div>
                    </div>
                </div>
            )}

            {/* ─── Toast ─── */}
            {toast && (
                <div className={`toast toast-${toast.type}`}>
                    {toast.type === "success" ? "✓" : "✗"} {toast.message}
                </div>
            )}
        </div>
    );
}

// Simple markdown to HTML renderer (no external dep needed for preview)
function MarkdownPreview({ content }: { content: string }) {
    const html = content
        // Headers
        .replace(/^### (.+)$/gm, '<h3>$1</h3>')
        .replace(/^## (.+)$/gm, '<h2>$1</h2>')
        .replace(/^# (.+)$/gm, '<h1>$1</h1>')
        // Bold & italic
        .replace(/\*\*(.+?)\*\*/g, '<strong class="text-white">$1</strong>')
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        // Code
        .replace(/`(.+?)`/g, '<code>$1</code>')
        // Lists
        .replace(/^- (.+)$/gm, '<li>$1</li>')
        // Paragraphs (double newline)
        .replace(/\n\n/g, '</p><p>')
        // Single newlines
        .replace(/\n/g, '<br/>');

    return (
        <div
            className="markdown-preview leading-relaxed"
            dangerouslySetInnerHTML={{ __html: `<p>${html}</p>` }}
        />
    );
}
