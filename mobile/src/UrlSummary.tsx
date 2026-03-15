/**
 * 🌐 URL Summary — Sprint 6 Task 3.
 *
 * Paste a URL → get a summary from the browse plugin on your home PC.
 * Alternative to native share sheet extension (simpler Expo approach).
 */
import { useState } from "react";
import {
    View,
    Text,
    TextInput,
    TouchableOpacity,
    StyleSheet,
    ScrollView,
} from "react-native";
import * as Haptics from "expo-haptics";
import * as Clipboard from "expo-clipboard";
import { companionAPI } from "./api";
import { colors, spacing, borderRadius, fontSize, shadows } from "./theme";

interface UrlSummaryProps {
    petName: string;
    isOnline: boolean;
}

export default function UrlSummary({ petName, isOnline }: UrlSummaryProps) {
    const [url, setUrl] = useState("");
    const [summary, setSummary] = useState<{ title?: string; summary?: string; keyPoints?: string[] } | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    const handleSummarize = async () => {
        const trimmed = url.trim();
        if (!trimmed || loading) return;

        // Basic URL validation
        if (!trimmed.startsWith("http://") && !trimmed.startsWith("https://")) {
            setError("Please enter a valid URL starting with http:// or https://");
            return;
        }

        Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
        setLoading(true);
        setError("");
        setSummary(null);

        try {
            const res = await companionAPI.browseSummarize(trimmed);
            setSummary(res);
        } catch {
            setError("Failed to summarize — is your home PC online?");
        }
        setLoading(false);
    };

    const handlePasteFromClipboard = async () => {
        const text = await Clipboard.getStringAsync();
        if (text) {
            setUrl(text);
            Haptics.selectionAsync();
        }
    };

    const handleCopySummary = async () => {
        if (summary?.summary) {
            await Clipboard.setStringAsync(summary.summary);
            Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
        }
    };

    const handleAskCompanion = async () => {
        // Future: open chat with summary pre-loaded
        Haptics.selectionAsync();
    };

    return (
        <View style={styles.card}>
            <Text style={styles.cardTitle}>🌐 Summarize a Page</Text>
            <Text style={styles.cardSubtitle}>
                Paste a URL — {petName} will read and summarize it using your home PC
            </Text>

            <View style={styles.inputRow}>
                <TextInput
                    style={styles.urlInput}
                    value={url}
                    onChangeText={setUrl}
                    placeholder="https://example.com/article"
                    placeholderTextColor={colors.textMuted}
                    keyboardType="url"
                    autoCapitalize="none"
                    autoCorrect={false}
                    onSubmitEditing={handleSummarize}
                    returnKeyType="go"
                />
                <TouchableOpacity style={styles.pasteBtn} onPress={handlePasteFromClipboard} activeOpacity={0.7}>
                    <Text style={styles.pasteBtnText}>📋</Text>
                </TouchableOpacity>
            </View>

            <TouchableOpacity
                style={[styles.summarizeBtn, (loading || !url.trim()) && { opacity: 0.4 }]}
                onPress={handleSummarize}
                disabled={loading || !url.trim() || !isOnline}
                activeOpacity={0.7}
            >
                <Text style={styles.summarizeBtnText}>
                    {loading ? "Reading page..." : "📖 Summarize"}
                </Text>
            </TouchableOpacity>

            {!isOnline && (
                <Text style={styles.offlineNote}>Requires your home PC to be online</Text>
            )}

            {error ? <Text style={styles.errorText}>{error}</Text> : null}

            {summary && (
                <View style={styles.resultCard}>
                    {summary.title && <Text style={styles.resultTitle}>{summary.title}</Text>}
                    {summary.summary && <Text style={styles.resultSummary}>{summary.summary}</Text>}
                    {summary.keyPoints && summary.keyPoints.length > 0 && (
                        <View style={styles.keyPoints}>
                            <Text style={styles.keyPointsLabel}>Key Points:</Text>
                            {summary.keyPoints.map((kp, i) => (
                                <Text key={i} style={styles.keyPoint}>• {kp}</Text>
                            ))}
                        </View>
                    )}
                    <View style={styles.resultActions}>
                        <TouchableOpacity style={styles.resultActionBtn} onPress={handleCopySummary} activeOpacity={0.7}>
                            <Text style={styles.resultActionText}>📋 Copy</Text>
                        </TouchableOpacity>
                        <TouchableOpacity style={styles.resultActionBtn} onPress={handleAskCompanion} activeOpacity={0.7}>
                            <Text style={styles.resultActionText}>💬 Ask {petName}</Text>
                        </TouchableOpacity>
                    </View>
                </View>
            )}
        </View>
    );
}

const styles = StyleSheet.create({
    card: { backgroundColor: colors.bgCard, borderRadius: borderRadius.lg, borderWidth: 1, borderColor: colors.glassBorder, padding: spacing.xl, marginBottom: spacing.lg, ...shadows.card },
    cardTitle: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.md, color: colors.textPrimary, marginBottom: spacing.xs },
    cardSubtitle: { fontFamily: "Inter_400Regular", fontSize: fontSize.tiny, color: colors.textDim, marginBottom: spacing.md },
    inputRow: { flexDirection: "row", gap: spacing.sm, marginBottom: spacing.md },
    urlInput: { flex: 1, backgroundColor: colors.bgInput, borderRadius: borderRadius.md, borderWidth: 1, borderColor: colors.glassBorder, paddingHorizontal: spacing.md, paddingVertical: spacing.sm, fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.textPrimary },
    pasteBtn: { backgroundColor: colors.bgInput, borderRadius: borderRadius.md, borderWidth: 1, borderColor: colors.glassBorder, paddingHorizontal: spacing.md, justifyContent: "center" },
    pasteBtnText: { fontSize: 18 },
    summarizeBtn: { backgroundColor: colors.neon, borderRadius: borderRadius.md, paddingVertical: spacing.md, alignItems: "center", marginBottom: spacing.sm },
    summarizeBtnText: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.sm, color: colors.bgPrimary },
    offlineNote: { fontFamily: "Inter_400Regular", fontSize: fontSize.tiny, color: colors.textMuted, fontStyle: "italic", textAlign: "center", marginBottom: spacing.sm },
    errorText: { fontFamily: "Inter_400Regular", fontSize: fontSize.tiny, color: "#ef4444", marginBottom: spacing.sm },
    resultCard: { backgroundColor: colors.neonGlow, borderWidth: 1, borderColor: colors.neonBorder, borderRadius: borderRadius.md, padding: spacing.md },
    resultTitle: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.sm, color: colors.textPrimary, marginBottom: spacing.sm },
    resultSummary: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.textSecondary, lineHeight: 20, marginBottom: spacing.md },
    keyPoints: { marginBottom: spacing.md },
    keyPointsLabel: { fontFamily: "Inter_500Medium", fontSize: fontSize.tiny, color: colors.neon, marginBottom: spacing.xs },
    keyPoint: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.textSecondary, lineHeight: 18, paddingLeft: spacing.xs },
    resultActions: { flexDirection: "row", gap: spacing.sm },
    resultActionBtn: { flex: 1, backgroundColor: colors.bgCard, borderRadius: borderRadius.sm, paddingVertical: spacing.sm, alignItems: "center" },
    resultActionText: { fontFamily: "Inter_400Regular", fontSize: fontSize.tiny, color: colors.textDim },
});
