/**
 * 🐾 Care Tab — Feed, walk, and monitor your companion.
 *
 * Animated happiness bar, XP progress, feed/walk buttons.
 * Works offline with optimistic updates.
 */
import { useState, useCallback } from "react";
import {
    View,
    Text,
    TouchableOpacity,
    ScrollView,
    StyleSheet,
    Animated,
} from "react-native";
import { useConnection } from "../../src/hooks/useConnection";
import { companionAPI } from "../../src/api";
import { colors, spacing, borderRadius, fontSize, shadows } from "../../src/theme";
import type { PetSpecies, WalkEvent } from "../../src/types";

const SPECIES_EMOJI: Record<PetSpecies, string> = {
    cat: "🐱",
    dog: "🐶",
    penguin: "🐧",
    fox: "🦊",
    owl: "🦉",
    dragon: "🐉",
};

const TREAT_ITEMS = [
    { emoji: "🐟", name: "Fish", key: "fish" },
    { emoji: "🍬", name: "Treat", key: "treat" },
    { emoji: "🥗", name: "Salad", key: "salad" },
    { emoji: "🎂", name: "Cake", key: "cake" },
];

const OFFLINE_WALK_EVENTS: Record<PetSpecies, WalkEvent[]> = {
    cat: [
        { text: "stared at a wall. Deep thoughts.", happinessBoost: 6, xpGain: 3, emoji: "🧘" },
        { text: "found a sunbeam. Napped instantly.", happinessBoost: 10, xpGain: 2, emoji: "☀️" },
    ],
    dog: [
        { text: "found THE GREATEST STICK!", happinessBoost: 12, xpGain: 5, emoji: "🪵" },
        { text: "met a new friend! BEST DAY EVER!", happinessBoost: 15, xpGain: 4, emoji: "🐕" },
    ],
    penguin: [
        { text: "organized rocks by size. Satisfying.", happinessBoost: 8, xpGain: 6, emoji: "🪨" },
        { text: "slid on ice. With dignity.", happinessBoost: 10, xpGain: 3, emoji: "🧊" },
    ],
    fox: [
        { text: "found a shiny thing. Pocketed it.", happinessBoost: 10, xpGain: 5, emoji: "✨" },
        { text: "outsmarted a vending machine.", happinessBoost: 12, xpGain: 7, emoji: "🍫" },
    ],
    owl: [
        { text: "counted 47 stars. Lost count.", happinessBoost: 8, xpGain: 5, emoji: "⭐" },
        { text: "found an old book. Read it twice.", happinessBoost: 12, xpGain: 10, emoji: "📖" },
    ],
    dragon: [
        { text: "SET A BUSH ON FIRE. Accidentally.", happinessBoost: 12, xpGain: 5, emoji: "🔥" },
        { text: "found coins. ADDED TO THE HOARD!", happinessBoost: 18, xpGain: 8, emoji: "💰" },
    ],
};

export default function CareTab() {
    const { isOnline, companionData, queueAction, updateCompanionLocal } = useConnection();
    const [walking, setWalking] = useState(false);
    const [feeding, setFeeding] = useState(false);
    const [walkResult, setWalkResult] = useState<WalkEvent | null>(null);

    const companion = companionData?.companion;
    const petName = companion?.name || "Companion";
    const species = (companion?.species || "cat") as PetSpecies;
    const happiness = companion?.happiness ?? 50;
    const xp = companion?.xp ?? 0;
    const level = companion?.level ?? 1;
    const xpNeeded = level * 20;

    const happinessColor =
        happiness > 70 ? colors.happinessHigh :
            happiness > 30 ? colors.happinessMid :
                colors.happinessLow;

    const happinessEmoji =
        happiness > 70 ? "💚" : happiness > 30 ? "💛" : happiness > 0 ? "🧡" : "💔";

    const handleFeed = useCallback(
        async (food: string) => {
            if (feeding) return;
            setFeeding(true);

            if (isOnline) {
                try {
                    const res = await companionAPI.feed(food);
                    updateCompanionLocal(() => res.companion);
                } catch {
                    // Optimistic local update
                    updateCompanionLocal((prev) => ({
                        ...prev,
                        happiness: Math.min(100, prev.happiness + 8),
                        xp: prev.xp + 2,
                    }));
                }
            } else {
                queueAction({ type: "feed", payload: food, timestamp: Date.now() });
                updateCompanionLocal((prev) => ({
                    ...prev,
                    happiness: Math.min(100, prev.happiness + 8),
                    xp: prev.xp + 2,
                }));
            }

            setTimeout(() => setFeeding(false), 600);
        },
        [feeding, isOnline, queueAction, updateCompanionLocal]
    );

    const handleWalk = useCallback(async () => {
        if (walking) return;
        setWalking(true);
        setWalkResult(null);

        if (isOnline) {
            try {
                const res = await companionAPI.walk();
                updateCompanionLocal(() => res.companion);
                setWalkResult(res.event);
            } catch {
                // Offline fallback
                const events = OFFLINE_WALK_EVENTS[species];
                const event = events[Math.floor(Math.random() * events.length)];
                setWalkResult(event);
                updateCompanionLocal((prev) => ({
                    ...prev,
                    happiness: Math.min(100, prev.happiness + event.happinessBoost),
                    xp: prev.xp + event.xpGain,
                }));
            }
        } else {
            queueAction({ type: "walk", timestamp: Date.now() });
            const events = OFFLINE_WALK_EVENTS[species];
            const event = events[Math.floor(Math.random() * events.length)];
            await new Promise((r) => setTimeout(r, 1500));
            setWalkResult(event);
            updateCompanionLocal((prev) => ({
                ...prev,
                happiness: Math.min(100, prev.happiness + event.happinessBoost),
                xp: prev.xp + event.xpGain,
            }));
        }

        setTimeout(() => setWalking(false), 2000);
    }, [walking, isOnline, species, queueAction, updateCompanionLocal]);

    return (
        <ScrollView style={styles.container} contentContainerStyle={styles.content}>
            {/* Header */}
            <View style={styles.header}>
                <Text style={styles.headerTitle}>{petName}'s Status</Text>
                <View style={styles.headerMeta}>
                    <View
                        style={[
                            styles.onlineDot,
                            { backgroundColor: isOnline ? colors.onlineDot : colors.offlineDot },
                        ]}
                    />
                    <Text style={styles.levelText}>Level {level}</Text>
                </View>
            </View>

            {/* Avatar Card */}
            <View style={styles.avatarCard}>
                <Text style={styles.avatarEmoji}>{SPECIES_EMOJI[species]}</Text>
                <Text style={styles.avatarName}>{petName}</Text>
                <Text style={styles.avatarSpecies}>{species}</Text>
            </View>

            {/* Happiness Bar */}
            <View style={styles.statCard}>
                <View style={styles.statHeader}>
                    <Text style={styles.statLabel}>{happinessEmoji} Happiness</Text>
                    <Text style={styles.statValue}>{happiness}%</Text>
                </View>
                <View style={styles.barTrack}>
                    <View
                        style={[
                            styles.barFill,
                            { width: `${happiness}%`, backgroundColor: happinessColor },
                        ]}
                    />
                </View>
                {happiness < 30 && (
                    <Text style={styles.warningText}>Your companion misses you 🥺</Text>
                )}
            </View>

            {/* XP Bar */}
            <View style={styles.statCard}>
                <View style={styles.statHeader}>
                    <Text style={styles.statLabel}>✨ XP</Text>
                    <Text style={styles.statValue}>
                        {xp}/{xpNeeded}
                    </Text>
                </View>
                <View style={styles.barTrack}>
                    <View
                        style={[
                            styles.barFill,
                            styles.xpBar,
                            { width: `${Math.min(100, (xp / xpNeeded) * 100)}%` },
                        ]}
                    />
                </View>
            </View>

            {/* Walk Button */}
            <TouchableOpacity
                style={[styles.walkBtn, walking && styles.walkBtnActive]}
                onPress={handleWalk}
                disabled={walking}
                activeOpacity={0.7}
            >
                <Text style={styles.walkBtnText}>
                    {walking ? "🚶 Walking..." : "🚶 Go for a walk"}
                </Text>
            </TouchableOpacity>

            {/* Walk Result */}
            {walkResult && (
                <View style={styles.walkResult}>
                    <Text style={styles.walkResultText}>
                        <Text style={styles.walkEmoji}>{walkResult.emoji} </Text>
                        {petName} {walkResult.text}
                    </Text>
                    <Text style={styles.walkBonus}>
                        +{walkResult.happinessBoost}% happiness · +{walkResult.xpGain} XP
                    </Text>
                </View>
            )}

            {/* Feed Buttons */}
            <Text style={styles.sectionLabel}>Feed {petName}</Text>
            <View style={styles.treatRow}>
                {TREAT_ITEMS.map((treat) => (
                    <TouchableOpacity
                        key={treat.key}
                        style={[styles.treatBtn, feeding && styles.treatBtnDisabled]}
                        onPress={() => handleFeed(treat.key)}
                        disabled={feeding || happiness >= 100}
                        activeOpacity={0.7}
                    >
                        <Text style={styles.treatEmoji}>{treat.emoji}</Text>
                        <Text style={styles.treatName}>{treat.name}</Text>
                    </TouchableOpacity>
                ))}
            </View>
        </ScrollView>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: colors.bgPrimary,
    },
    content: {
        paddingHorizontal: spacing.lg,
        paddingTop: 60,
        paddingBottom: spacing.xxxl,
    },
    header: {
        flexDirection: "row",
        justifyContent: "space-between",
        alignItems: "center",
        marginBottom: spacing.xl,
    },
    headerTitle: {
        fontFamily: "Inter_600SemiBold",
        fontSize: fontSize.xl,
        color: colors.textPrimary,
    },
    headerMeta: {
        flexDirection: "row",
        alignItems: "center",
        gap: spacing.sm,
    },
    onlineDot: {
        width: 6,
        height: 6,
        borderRadius: 3,
    },
    levelText: {
        fontFamily: "Inter_400Regular",
        fontSize: fontSize.xs,
        color: colors.textDim,
    },
    avatarCard: {
        backgroundColor: colors.bgCard,
        borderRadius: borderRadius.lg,
        borderWidth: 1,
        borderColor: colors.glassBorder,
        paddingVertical: spacing.xl,
        alignItems: "center",
        marginBottom: spacing.lg,
        ...shadows.card,
    },
    avatarEmoji: {
        fontSize: 56,
        marginBottom: spacing.sm,
    },
    avatarName: {
        fontFamily: "Inter_700Bold",
        fontSize: fontSize.xxl,
        color: colors.textPrimary,
    },
    avatarSpecies: {
        fontFamily: "Inter_400Regular",
        fontSize: fontSize.sm,
        color: colors.textDim,
        textTransform: "capitalize",
        marginTop: 2,
    },
    statCard: {
        backgroundColor: colors.bgCard,
        borderRadius: borderRadius.md,
        borderWidth: 1,
        borderColor: colors.glassBorder,
        padding: spacing.lg,
        marginBottom: spacing.md,
    },
    statHeader: {
        flexDirection: "row",
        justifyContent: "space-between",
        marginBottom: spacing.sm,
    },
    statLabel: {
        fontFamily: "Inter_400Regular",
        fontSize: fontSize.sm,
        color: colors.textDim,
    },
    statValue: {
        fontFamily: "Inter_500Medium",
        fontSize: fontSize.sm,
        color: colors.textSecondary,
    },
    barTrack: {
        height: 8,
        borderRadius: 4,
        backgroundColor: colors.bgInput,
        overflow: "hidden",
    },
    barFill: {
        height: 8,
        borderRadius: 4,
    },
    xpBar: {
        backgroundColor: colors.neon,
    },
    warningText: {
        fontFamily: "Inter_400Regular",
        fontSize: fontSize.xs,
        color: colors.warning,
        marginTop: spacing.xs,
    },
    walkBtn: {
        backgroundColor: colors.neon,
        borderRadius: borderRadius.md,
        paddingVertical: spacing.md + 2,
        alignItems: "center",
        marginBottom: spacing.md,
        ...shadows.glow,
    },
    walkBtnActive: {
        opacity: 0.5,
    },
    walkBtnText: {
        fontFamily: "Inter_600SemiBold",
        fontSize: fontSize.md,
        color: colors.bgPrimary,
    },
    walkResult: {
        backgroundColor: colors.neonGlow,
        borderWidth: 1,
        borderColor: colors.neonBorder,
        borderRadius: borderRadius.md,
        padding: spacing.md,
        marginBottom: spacing.lg,
    },
    walkResultText: {
        fontFamily: "Inter_400Regular",
        fontSize: fontSize.sm,
        color: colors.textSecondary,
        lineHeight: 20,
    },
    walkEmoji: {
        fontSize: fontSize.lg,
    },
    walkBonus: {
        fontFamily: "Inter_400Regular",
        fontSize: fontSize.tiny,
        color: colors.neon,
        marginTop: spacing.xs,
    },
    sectionLabel: {
        fontFamily: "Inter_500Medium",
        fontSize: fontSize.sm,
        color: colors.textDim,
        marginBottom: spacing.sm,
    },
    treatRow: {
        flexDirection: "row",
        gap: spacing.sm,
    },
    treatBtn: {
        flex: 1,
        backgroundColor: colors.bgCard,
        borderRadius: borderRadius.md,
        borderWidth: 1,
        borderColor: colors.glassBorder,
        paddingVertical: spacing.md,
        alignItems: "center",
    },
    treatBtnDisabled: {
        opacity: 0.3,
    },
    treatEmoji: {
        fontSize: 24,
        marginBottom: 2,
    },
    treatName: {
        fontFamily: "Inter_400Regular",
        fontSize: fontSize.tiny,
        color: colors.textDim,
    },
});
