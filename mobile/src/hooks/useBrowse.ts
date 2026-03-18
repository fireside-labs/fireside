/**
 * 🌐 useBrowse — Web browsing capability hook.
 *
 * Sprint 3: "Extra Senses" — lets the companion browse the web
 * from the mobile app context. Uses the backend browse plugin
 * when online, falls back to queuing for later.
 */
import { useState, useCallback } from "react";
import { companionAPI } from "../api";

export interface BrowseResult {
    url: string;
    title?: string;
    summary?: string;
    keyPoints?: string[];
    loading: boolean;
    error?: string;
}

/**
 * Hook for browsing the web through the companion.
 *
 * Usage:
 *   const { browse, result, loading } = useBrowse();
 *   await browse("https://example.com");
 */
export function useBrowse() {
    const [result, setResult] = useState<BrowseResult | null>(null);
    const [loading, setLoading] = useState(false);

    const browse = useCallback(async (url: string) => {
        setLoading(true);
        setResult({ url, loading: true });

        try {
            const res = await companionAPI.browseSummarize(url);
            setResult({
                url,
                title: res.title,
                summary: res.summary,
                keyPoints: res.keyPoints,
                loading: false,
            });
        } catch (e: any) {
            // Queue for later if offline
            try {
                await companionAPI.queueTask("browse", { url });
            } catch { }
            setResult({
                url,
                loading: false,
                error: "Offline — queued for later.",
            });
        }

        setLoading(false);
    }, []);

    const clear = useCallback(() => {
        setResult(null);
    }, []);

    return { browse, result, loading, clear };
}
