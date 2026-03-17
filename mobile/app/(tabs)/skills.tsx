/**
 * ⚡ Skills Tab — RPG skill toggle cards.
 *
 * Lists companion's active skills with toggle switches.
 * Power level (unbounded XP, no cap). Shows skill tree progress.
 */
import { useState, useEffect, useCallback } from "react";
import {
    View,
    Text,
    TouchableOpacity,
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

// Fallback skills when offline
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
    const totalXP = companionData?.companion?.xp ?? 0;
    const level = companionData?.companion?.level ?? 1;
    const enabledCount = skills.filter((s) => s.enabled).length;
    const totalPower = skills.reduce((acc, s) => acc + (s.enabled ? s.level * 10 : 0), 0);

    const fetchSkills = useCallback(async () => {
        try {
            const res = await companionAPI.skills();
            if (res.skills?.length) setSkills(res.skills);
        } catch {
            // Use fallback
        }
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
                // Revert on failure
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

            {/* Power Level Card */}
            <View style={styles.powerCard}>
                <Text style={styles.powerLabel}>POWER LEVEL</Text>
                <Text style={styles.powerValue}>{totalPower}</Text>
                <View style={styles.powerStats}>
                    <Text style={styles.powerStat}>⚡ {enabledCount}/{skills.length} active</Text>
                    <Text style={styles.powerStat}>✨ {totalXP.toLocaleString()} XP</Text>
                    <Text style={styles.powerStat}>📊 Level {level}</Text>
                </View>
            </View>

            {/* Skill Cards */}
            {loading ? (
                <ActivityIndicator color={colors.neon} style={{ marginTop: spacing.xl }} />
            ) : (
                skills.map((skill) => (
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
                                <View style={[styles.levelFill, { width: `${Math.min(100, skill.level * 20)}%` }]} />
                            </View>
                            <Text style={styles.levelText}>Lv.{skill.level}</Text>
                        </View>
                    </View>
                ))
            )}

            {/* No cap note */}
            <View style={styles.noteCard}>
                <Text style={styles.noteText}>
                    💎 Power level has no cap. The more you use skills, the stronger they get.
                    Each skill levels up independently through usage.
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
    powerCard: { backgroundColor: colors.neonGlow, borderWidth: 1, borderColor: colors.neonBorder, borderRadius: borderRadius.lg, padding: spacing.xl, marginBottom: spacing.xl, alignItems: "center", ...shadows.ember },
    powerLabel: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.tiny, color: colors.neon, letterSpacing: 2, marginBottom: spacing.xs },
    powerValue: { fontFamily: "Inter_700Bold", fontSize: 48, color: colors.ember, marginBottom: spacing.sm },
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
    levelFill: { height: 4, borderRadius: 2, backgroundColor: colors.ember },
    levelText: { fontFamily: "Inter_500Medium", fontSize: fontSize.tiny, color: colors.ember, minWidth: 28 },
    // Note
    noteCard: { backgroundColor: colors.bgCard, borderRadius: borderRadius.md, padding: spacing.md, marginTop: spacing.md },
    noteText: { fontFamily: "Inter_400Regular", fontSize: fontSize.tiny, color: colors.textDim, textAlign: "center", lineHeight: 16 },
});
