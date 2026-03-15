/**
 * 🏆 Achievement Badge — Sprint 7 Task 1.
 *
 * Circular badge with emoji icon, name, earned/locked state.
 * Ported from dashboard/components/AchievementBadge.tsx.
 */
import { View, Text, StyleSheet } from "react-native";
import { colors, spacing, borderRadius, fontSize, shadows } from "./theme";

export interface Achievement {
    id: string;
    name: string;
    description: string;
    emoji: string;
    earned: boolean;
    earnedDate?: string;
    progress?: number;   // 0-1 for count-based
    progressLabel?: string; // e.g. "23/100 feeds"
}

// 16 achievements Thor is building
export const ALL_ACHIEVEMENTS: Achievement[] = [
    { id: "first_feed", name: "First Bite", description: "Feed your companion for the first time", emoji: "🍖", earned: false },
    { id: "first_walk", name: "First Steps", description: "Take your companion for a walk", emoji: "🐾", earned: false },
    { id: "first_chat", name: "Hello World", description: "Send your first message", emoji: "💬", earned: false },
    { id: "first_quest", name: "Adventurer", description: "Complete your first quest", emoji: "⚔️", earned: false },
    { id: "first_teach", name: "Teacher", description: "Teach your companion a fact", emoji: "💡", earned: false },
    { id: "first_translate", name: "Polyglot", description: "Use the translation feature", emoji: "🌐", earned: false },
    { id: "first_voice", name: "Voice Pioneer", description: "Use voice mode for the first time", emoji: "🎤", earned: false },
    { id: "streak_7", name: "Week Warrior", description: "Maintain a 7-day streak", emoji: "🔥", earned: false },
    { id: "streak_30", name: "Monthly Master", description: "Maintain a 30-day streak", emoji: "💀", earned: false },
    { id: "feeds_100", name: "Chef", description: "Feed your companion 100 times", emoji: "👨‍🍳", earned: false, progress: 0, progressLabel: "0/100 feeds" },
    { id: "level_10", name: "Rising Star", description: "Reach level 10", emoji: "⭐", earned: false },
    { id: "level_25", name: "Veteran", description: "Reach level 25", emoji: "🏅", earned: false },
    { id: "level_50", name: "Legend", description: "Reach level 50", emoji: "👑", earned: false },
    { id: "night_owl", name: "Night Owl", description: "Chat after midnight", emoji: "🦉", earned: false },
    { id: "facts_50", name: "Professor", description: "Teach 50 facts", emoji: "📚", earned: false, progress: 0, progressLabel: "0/50 facts" },
    { id: "marketplace", name: "Shopper", description: "Install an item from the marketplace", emoji: "🛒", earned: false },
];

interface AchievementBadgeProps {
    achievement: Achievement;
}

export default function AchievementBadge({ achievement }: AchievementBadgeProps) {
    const { name, emoji, earned, earnedDate, progress } = achievement;

    return (
        <View style={[styles.badge, earned ? styles.badgeEarned : styles.badgeLocked]}>
            <Text style={[styles.icon, !earned && styles.iconLocked]}>
                {earned ? emoji : "❓"}
            </Text>
            <Text style={[styles.name, !earned && styles.nameLocked]} numberOfLines={1}>
                {earned ? name : "???"}
            </Text>
            {earned && earnedDate ? (
                <Text style={styles.date}>{earnedDate}</Text>
            ) : null}
            {!earned && progress != null && progress > 0 ? (
                <View style={styles.progressBar}>
                    <View style={[styles.progressFill, { width: `${Math.min(progress * 100, 100)}%` }]} />
                </View>
            ) : null}
        </View>
    );
}

const styles = StyleSheet.create({
    badge: { width: 80, height: 90, borderRadius: borderRadius.lg, alignItems: "center", justifyContent: "center", padding: spacing.xs, margin: spacing.xs },
    badgeEarned: { backgroundColor: colors.neonGlow, borderWidth: 1, borderColor: colors.neon, ...shadows.glow },
    badgeLocked: { backgroundColor: colors.bgCard, borderWidth: 1, borderColor: colors.glassBorder, opacity: 0.4 },
    icon: { fontSize: 28, marginBottom: 2 },
    iconLocked: { opacity: 0.3 },
    name: { fontFamily: "Inter_500Medium", fontSize: 9, color: colors.textSecondary, textAlign: "center" },
    nameLocked: { color: colors.textMuted },
    date: { fontFamily: "Inter_400Regular", fontSize: 7, color: colors.neon, marginTop: 1 },
    progressBar: { width: "80%", height: 3, backgroundColor: colors.glassBorder, borderRadius: 2, marginTop: 3 },
    progressFill: { height: "100%", backgroundColor: colors.neon, borderRadius: 2 },
});
