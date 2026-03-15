/**
 * 📊 Weekly Summary — Sprint 7 Task 2.
 *
 * Shows at top of Care/Tools tab on first open each week.
 * Ported from dashboard/components/WeeklyCard.tsx.
 */
import { useState, useEffect } from "react";
import { View, Text, TouchableOpacity, StyleSheet, Share } from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import * as Haptics from "expo-haptics";
import { companionAPI } from "./api";
import { colors, spacing, borderRadius, fontSize, shadows } from "./theme";

const WEEKLY_DISMISS_KEY = "fireside_weekly_dismissed";

interface WeeklyStats {
    feeds: number;
    walks: number;
    quests: number;
    facts: number;
    messages: number;
    levelsGained: number;
    achievementsEarned: string[];
    highlights: string[];
}

interface WeeklySummaryProps {
    petName: string;
}

export default function WeeklySummary({ petName }: WeeklySummaryProps) {
    const [visible, setVisible] = useState(false);
    const [stats, setStats] = useState<WeeklyStats | null>(null);

    useEffect(() => {
        checkAndLoad();
    }, []);

    const checkAndLoad = async () => {
        // Check if already dismissed this week
        const lastDismissed = await AsyncStorage.getItem(WEEKLY_DISMISS_KEY);
        if (lastDismissed) {
            const dismissedDate = new Date(lastDismissed);
            const now = new Date();
            // Same week (within 7 days and same or later day of week)
            const daysSince = (now.getTime() - dismissedDate.getTime()) / (1000 * 60 * 60 * 24);
            if (daysSince < 7) return;
        }

        // Check if it's the right time (Monday/Sunday or first open of week)
        const day = new Date().getDay();
        const isWeekStart = day === 0 || day === 1; // Sunday or Monday

        // Show if it's week start OR we haven't shown this week
        if (isWeekStart || !lastDismissed) {
            try {
                const res = await companionAPI.weeklySummary();
                setStats(res as any);
                setVisible(true);
            } catch {
                // Mock stats if API unavailable
                setStats({
                    feeds: 14, walks: 8, quests: 3, facts: 5, messages: 47, levelsGained: 2,
                    achievementsEarned: ["First Bite", "Adventurer"],
                    highlights: [`Reached level ${Math.floor(Math.random() * 10) + 5}!`, `${petName} learned 5 new things about you`],
                });
                setVisible(true);
            }
        }
    };

    const handleDismiss = async () => {
        await AsyncStorage.setItem(WEEKLY_DISMISS_KEY, new Date().toISOString());
        Haptics.selectionAsync();
        setVisible(false);
    };

    const handleShare = async () => {
        if (!stats) return;
        Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
        const text = [
            `📊 My Week with ${petName}`,
            `🍖 ${stats.feeds} feeds · 🐾 ${stats.walks} walks · ⚔️ ${stats.quests} quests`,
            `💬 ${stats.messages} messages · 💡 ${stats.facts} facts taught`,
            ...(stats.highlights || []).map((h) => `✨ ${h}`),
            `#Fireside #AI`,
        ].join("\n");
        try { await Share.share({ message: text }); } catch { }
    };

    if (!visible || !stats) return null;

    return (
        <View style={styles.card}>
            <View style={styles.header}>
                <View style={{ flex: 1 }}>
                    <Text style={styles.title}>📊 Your Week with {petName}</Text>
                    <Text style={styles.subtitle}>Weekly summary</Text>
                </View>
                <TouchableOpacity onPress={handleDismiss} activeOpacity={0.7}>
                    <Text style={styles.closeBtn}>✕</Text>
                </TouchableOpacity>
            </View>

            <View style={styles.statsGrid}>
                <View style={styles.statItem}><Text style={styles.statNum}>{stats.feeds}</Text><Text style={styles.statLabel}>🍖 Feeds</Text></View>
                <View style={styles.statItem}><Text style={styles.statNum}>{stats.walks}</Text><Text style={styles.statLabel}>🐾 Walks</Text></View>
                <View style={styles.statItem}><Text style={styles.statNum}>{stats.quests}</Text><Text style={styles.statLabel}>⚔️ Quests</Text></View>
                <View style={styles.statItem}><Text style={styles.statNum}>{stats.messages}</Text><Text style={styles.statLabel}>💬 Msgs</Text></View>
                <View style={styles.statItem}><Text style={styles.statNum}>{stats.facts}</Text><Text style={styles.statLabel}>💡 Facts</Text></View>
                <View style={styles.statItem}><Text style={styles.statNum}>{stats.levelsGained}</Text><Text style={styles.statLabel}>⬆️ Levels</Text></View>
            </View>

            {stats.highlights && stats.highlights.length > 0 && (
                <View style={styles.highlights}>
                    <Text style={styles.highlightsLabel}>✨ Highlight Reel</Text>
                    {stats.highlights.map((h, i) => (
                        <Text key={i} style={styles.highlight}>• {h}</Text>
                    ))}
                </View>
            )}

            {stats.achievementsEarned && stats.achievementsEarned.length > 0 && (
                <Text style={styles.achievementsLine}>
                    🏆 Earned: {stats.achievementsEarned.join(", ")}
                </Text>
            )}

            <View style={styles.actions}>
                <TouchableOpacity style={styles.shareBtn} onPress={handleShare} activeOpacity={0.7}>
                    <Text style={styles.shareBtnText}>📤 Share my week</Text>
                </TouchableOpacity>
                <TouchableOpacity style={styles.dismissBtn} onPress={handleDismiss} activeOpacity={0.7}>
                    <Text style={styles.dismissBtnText}>Got it</Text>
                </TouchableOpacity>
            </View>
        </View>
    );
}

const styles = StyleSheet.create({
    card: { backgroundColor: colors.bgCard, borderRadius: borderRadius.lg, borderWidth: 1, borderColor: colors.neon, padding: spacing.xl, marginBottom: spacing.lg, ...shadows.glow },
    header: { flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start", marginBottom: spacing.md },
    title: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.md, color: colors.textPrimary },
    subtitle: { fontFamily: "Inter_400Regular", fontSize: fontSize.tiny, color: colors.textDim, marginTop: 2 },
    closeBtn: { fontSize: fontSize.sm, color: colors.textMuted, padding: spacing.xs },
    statsGrid: { flexDirection: "row", flexWrap: "wrap", marginBottom: spacing.md },
    statItem: { width: "33.33%", alignItems: "center", paddingVertical: spacing.sm },
    statNum: { fontFamily: "Inter_700Bold", fontSize: fontSize.lg, color: colors.textPrimary },
    statLabel: { fontFamily: "Inter_400Regular", fontSize: fontSize.tiny, color: colors.textDim, marginTop: 2 },
    highlights: { marginBottom: spacing.md },
    highlightsLabel: { fontFamily: "Inter_500Medium", fontSize: fontSize.tiny, color: colors.neon, marginBottom: spacing.xs },
    highlight: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.textSecondary, lineHeight: 18 },
    achievementsLine: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.textDim, marginBottom: spacing.md },
    actions: { flexDirection: "row", gap: spacing.sm },
    shareBtn: { flex: 1, backgroundColor: colors.neon, borderRadius: borderRadius.md, paddingVertical: spacing.sm, alignItems: "center" },
    shareBtnText: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.xs, color: colors.bgPrimary },
    dismissBtn: { flex: 1, backgroundColor: colors.bgInput, borderRadius: borderRadius.md, paddingVertical: spacing.sm, alignItems: "center", borderWidth: 1, borderColor: colors.glassBorder },
    dismissBtnText: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.textDim },
});
