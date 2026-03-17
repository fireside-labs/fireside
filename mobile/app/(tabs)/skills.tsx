/**
 * ⚡ Skills Tab — RPG skill toggle cards with unbounded XP tiers.
 *
 * Tier system (no cap):
 *   🌱 Basic (0-499) → 🌿 Solid (500-999) → 💪 Strong (1000-1499)
 *   → ⚡ Legendary (1500-1999) → 🔥 Mythic (2000-2499) → 🌟 Ascended (2500+)
 *
 * XP = skill points × 50. Progress bar fills within each 500 XP tier.
 * Display: "⚡ Legendary · 3,500 XP"
 */
import { useState, useEffect, useCallback, useMemo } from "react";
import {
    View,
    Text,
    ScrollView,
    StyleSheet,
    RefreshControl,
    Switch,
    ActivityIndicator,
} from "react-native";
import * as Haptics from "expo-haptics";
import { useConnection } from "../../src/hooks/useConnection";
import { companionAPI } from "../../src/api";
import { colors, spacing, borderRadius, fontSize, shadows } from "../../src/theme";

interface Skill {
    id: string;
    name: string;
    description: string;
    emoji: string;
    enabled: boolean;
    level: number;
    xp_cost?: number;
}

// ── Tier System ──
const TIER_SIZE = 500;

interface Tier {
    name: string;
    emoji: string;
    color: string;
    minXP: number;
}

const TIERS: Tier[] = [
    { name: "Basic",     emoji: "🌱", color: "#6b7280", minXP: 0 },
    { name: "Solid",     emoji: "🌿", color: "#22c55e", minXP: 500 },
    { name: "Strong",    emoji: "💪", color: "#3b82f6", minXP: 1000 },
    { name: "Legendary", emoji: "⚡", color: "#f59e0b", minXP: 1500 },
    { name: "Mythic",    emoji: "🔥", color: "#ef4444", minXP: 2000 },
    { name: "Ascended",  emoji: "🌟", color: "#a855f7", minXP: 2500 },
];

function getTier(xp: number): Tier {
    for (let i = TIERS.length - 1; i >= 0; i--) {
        if (xp >= TIERS[i].minXP) return TIERS[i];
    }
    return TIERS[0];
}

function getTierProgress(xp: number): number {
    const tier = getTier(xp);
    const tierIndex = TIERS.indexOf(tier);
    const nextTier = TIERS[tierIndex + 1];
    if (!nextTier) {
        // Ascended — progress continues beyond 2500, loop within 500
        return ((xp - tier.minXP) % TIER_SIZE) / TIER_SIZE;
    }
    return (xp - tier.minXP) / TIER_SIZE;
}

// Fallback skills
const FALLBACK_SKILLS: Skill[] = [
    { id: "web_search", name: "Web Search", description: "Search the internet for information", emoji: "🔍", enabled: true, level: 3 },
    { id: "code_review", name: "Code Review", description: "Analyze and review code quality", emoji: "💻", enabled: true, level: 2 },
    { id: "translation", name: "Translation", description: "Translate between 200 languages via NLLB", emoji: "🌐", enabled: true, level: 5 },
    { id: "summarization", name: "Summarization", description: "Summarize long documents and articles", emoji: "📋", enabled: false, level: 1 },
    { id: "creative_writing", name: "Creative Writing", description: "Generate stories, poems, and creative content", emoji: "✍️", enabled: false, level: 1 },
    { id: "memory_recall", name: "Memory Recall", description: "Remember past conversations and facts", emoji: "🧠", enabled: true, level: 4 },
    { id: "task_planning", name: "Task Planning", description: "Break down complex tasks into steps", emoji: "📊", enabled: true, level: 2 },
    { id: "guardian", name: "Guardian", description: "Emotional safety check before sending messages", emoji: "🛡️", enabled: true, level: 3 },
];

export default function SkillsTab() {
    const { isOnline, companionData } = useConnection();
    const [skills, setSkills] = useState<Skill[]>(FALLBACK_SKILLS);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);

    const petName = companionData?.companion?.name || "Companion";
    const enabledCount = skills.filter((s) => s.enabled).length;

    // Calculate total XP: each enabled skill point × 50
    const totalXP = useMemo(() => {
        return skills.reduce((acc, s) => acc + (s.enabled ? s.level * 50 : 0), 0);
    }, [skills]);

    const currentTier = useMemo(() => getTier(totalXP), [totalXP]);
    const tierProgress = useMemo(() => getTierProgress(totalXP), [totalXP]);

    const fetchSkills = useCallback(async () => {
        try {
            const res = await companionAPI.skills();
            if (res.skills?.length) setSkills(res.skills);
        } catch { }
        setLoading(false);
    }, []);

    useEffect(() => {
        if (isOnline) fetchSkills();
        else setLoading(false);
    }, [isOnline, fetchSkills]);

    const handleToggle = async (skill: Skill) => {
        const newEnabled = !skill.enabled;
        Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);

        // Optimistic update
        setSkills((prev) =>
            prev.map((s) => (s.id === skill.id ? { ...s, enabled: newEnabled } : s))
        );

        if (isOnline) {
            try {
                await companionAPI.skillToggle(skill.id, newEnabled);
            } catch {
                setSkills((prev) =>
                    prev.map((s) => (s.id === skill.id ? { ...s, enabled: !newEnabled } : s))
                );
            }
        }
    };

    const onRefresh = useCallback(async () => {
        setRefreshing(true);
        await fetchSkills();
        setRefreshing(false);
    }, [fetchSkills]);

    return (
        <ScrollView
            style={styles.container}
            contentContainerStyle={styles.content}
            refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.neon} />}
        >
            <Text style={styles.title}>⚡ Skills</Text>
            <Text style={styles.subtitle}>{petName}'s active abilities</Text>

            {/* ═══ Power Level Card ═══ */}
            <View style={[styles.powerCard, { borderColor: currentTier.color }]}>
                <Text style={styles.powerLabel}>POWER LEVEL</Text>

                {/* Tier badge */}
                <View style={styles.tierRow}>
                    <Text style={styles.tierEmoji}>{currentTier.emoji}</Text>
                    <Text style={[styles.tierName, { color: currentTier.color }]}>
                        {currentTier.name}
                    </Text>
                </View>

                {/* XP display */}
                <Text style={styles.xpValue}>{totalXP.toLocaleString()} XP</Text>

                {/* Tier progress bar */}
                <View style={styles.tierBarTrack}>
                    <View
                        style={[
                            styles.tierBarFill,
                            {
                                width: `${Math.min(100, tierProgress * 100)}%`,
                                backgroundColor: currentTier.color,
                            },
                        ]}
                    />
                </View>

                {/* Tier milestone labels */}
                <View style={styles.tierMilestones}>
                    {TIERS.map((t) => (
                        <Text
                            key={t.name}
                            style={[
                                styles.tierMilestone,
                                totalXP >= t.minXP && { color: t.color, opacity: 1 },
                            ]}
                        >
                            {t.emoji}
                        </Text>
                    ))}
                </View>

                <View style={styles.powerStats}>
                    <Text style={styles.powerStat}>⚡ {enabledCount}/{skills.length} active</Text>
                    <Text style={styles.powerStat}>✨ {totalXP.toLocaleString()} XP</Text>
                </View>
            </View>

            {/* ═══ Skill Cards ═══ */}
            {loading ? (
                <ActivityIndicator color={colors.neon} style={{ marginTop: spacing.xl }} />
            ) : (
                skills.map((skill) => {
                    const skillXP = skill.level * 50;
                    const skillTier = getTier(skillXP);

                    return (
                        <View
                            key={skill.id}
                            style={[styles.skillCard, skill.enabled && styles.skillCardEnabled]}
                        >
                            <View style={styles.skillHeader}>
                                <Text style={styles.skillEmoji}>{skill.emoji}</Text>
                                <View style={styles.skillInfo}>
                                    <Text style={styles.skillName}>{skill.name}</Text>
                                    <Text style={styles.skillDesc}>{skill.description}</Text>
                                </View>
                                <Switch
                                    value={skill.enabled}
                                    onValueChange={() => handleToggle(skill)}
                                    trackColor={{ false: colors.glassBorder, true: colors.neonGlow }}
                                    thumbColor={skill.enabled ? colors.neon : colors.textMuted}
                                />
                            </View>
                            <View style={styles.skillFooter}>
                                <View style={styles.levelBar}>
                                    <View
                                        style={[
                                            styles.levelFill,
                                            {
                                                width: `${Math.min(100, getTierProgress(skillXP) * 100)}%`,
                                                backgroundColor: skillTier.color,
                                            },
                                        ]}
                                    />
                                </View>
                                <Text style={[styles.levelText, { color: skillTier.color }]}>
                                    {skillTier.emoji} {skillXP} XP
                                </Text>
                            </View>
                        </View>
                    );
                })
            )}

            {/* Info note */}
            <View style={styles.noteCard}>
                <Text style={styles.noteText}>
                    💎 Power level has no cap. Each skill levels up independently through usage.
                    XP multiplied by 50 per skill point. Tiers reset every 500 XP.
                </Text>
            </View>
        </ScrollView>
    );
}

const styles = StyleSheet.create({
    container: { flex: 1, backgroundColor: colors.bgPrimary },
    content: { paddingHorizontal: spacing.lg, paddingTop: 60, paddingBottom: spacing.xxxl },
    title: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.xl, color: colors.textPrimary, marginBottom: 2 },
    subtitle: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.textDim, marginBottom: spacing.xl },
    // Power card
    powerCard: {
        backgroundColor: "rgba(255,255,255,0.03)",
        borderWidth: 1,
        borderRadius: borderRadius.lg,
        padding: spacing.xl,
        marginBottom: spacing.xl,
        alignItems: "center",
        ...shadows.ember,
    },
    powerLabel: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.tiny, color: colors.textDim, letterSpacing: 2, marginBottom: spacing.sm },
    tierRow: { flexDirection: "row", alignItems: "center", gap: spacing.sm, marginBottom: spacing.xs },
    tierEmoji: { fontSize: 28 },
    tierName: { fontFamily: "Inter_700Bold", fontSize: fontSize.xl, textTransform: "uppercase", letterSpacing: 2 },
    xpValue: { fontFamily: "Inter_400Regular", fontSize: fontSize.sm, color: colors.textDim, marginBottom: spacing.md },
    // Tier progress bar
    tierBarTrack: { width: "100%", height: 8, borderRadius: 4, backgroundColor: colors.bgInput, overflow: "hidden", marginBottom: spacing.sm },
    tierBarFill: { height: 8, borderRadius: 4 },
    tierMilestones: { flexDirection: "row", justifyContent: "space-between", width: "100%", marginBottom: spacing.md },
    tierMilestone: { fontSize: 12, opacity: 0.3 },
    powerStats: { flexDirection: "row", gap: spacing.lg },
    powerStat: { fontFamily: "Inter_400Regular", fontSize: fontSize.tiny, color: colors.textDim },
    // Skill cards
    skillCard: { backgroundColor: colors.bgCard, borderRadius: borderRadius.md, borderWidth: 1, borderColor: colors.glassBorder, padding: spacing.lg, marginBottom: spacing.sm },
    skillCardEnabled: { borderLeftWidth: 3, borderLeftColor: colors.neon },
    skillHeader: { flexDirection: "row", alignItems: "center", gap: spacing.md, marginBottom: spacing.sm },
    skillEmoji: { fontSize: 24 },
    skillInfo: { flex: 1 },
    skillName: { fontFamily: "Inter_500Medium", fontSize: fontSize.sm, color: colors.textPrimary },
    skillDesc: { fontFamily: "Inter_400Regular", fontSize: fontSize.tiny, color: colors.textDim, marginTop: 1 },
    skillFooter: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
    levelBar: { flex: 1, height: 4, borderRadius: 2, backgroundColor: colors.bgInput, overflow: "hidden" },
    levelFill: { height: 4, borderRadius: 2 },
    levelText: { fontFamily: "Inter_500Medium", fontSize: fontSize.tiny, minWidth: 70 },
    // Note
    noteCard: { backgroundColor: colors.bgCard, borderRadius: borderRadius.md, padding: spacing.md, marginTop: spacing.md },
    noteText: { fontFamily: "Inter_400Regular", fontSize: fontSize.tiny, color: colors.textDim, textAlign: "center", lineHeight: 16 },
});
