/**
 * 🐾 Care Tab — Feed, walk, and monitor your companion.
 *
 * Sprint 2 additions:
 * - Pull-to-refresh (Valkyrie #4)
 * - Haptic feedback on feed/walk (Valkyrie #3)
 * - Companion avatar images replace emoji (Valkyrie #2)
 * - Mobile adoption flow if no companion exists (Valkyrie #6)
 */
import { useState, useCallback } from "react";
import {
    View,
    Text,
    TextInput,
    TouchableOpacity,
    ScrollView,
    StyleSheet,
    RefreshControl,
    Image,
} from "react-native";
import * as Haptics from "expo-haptics";
import { useConnection } from "../../src/hooks/useConnection";
import { companionAPI } from "../../src/api";
import { colors, spacing, borderRadius, fontSize, shadows } from "../../src/theme";
import { playSound } from "../../src/sounds";
import DailyGiftModal from "../../src/DailyGift";
import type { PetSpecies, WalkEvent } from "../../src/types";

// Mood-reactive avatar images — Sprint 3 (3 expressions per species)
type Mood = "happy" | "neutral" | "sad";

const AVATAR_MAP: Record<string, ReturnType<typeof require>> = {
    cat_happy: require("../../assets/companions/cat_happy.png"),
    cat_neutral: require("../../assets/companions/cat_neutral.png"),
    cat_sad: require("../../assets/companions/cat_sad.png"),
    dog_happy: require("../../assets/companions/dog_happy.png"),
    dog_neutral: require("../../assets/companions/dog_neutral.png"),
    dog_sad: require("../../assets/companions/dog_sad.png"),
    penguin_happy: require("../../assets/companions/penguin_happy.png"),
    penguin_neutral: require("../../assets/companions/penguin_neutral.png"),
    penguin_sad: require("../../assets/companions/penguin_sad.png"),
    fox_happy: require("../../assets/companions/fox_happy.png"),
    fox_neutral: require("../../assets/companions/fox_neutral.png"),
    fox_sad: require("../../assets/companions/fox_sad.png"),
    owl_happy: require("../../assets/companions/owl_happy.png"),
    owl_neutral: require("../../assets/companions/owl_neutral.png"),
    owl_sad: require("../../assets/companions/owl_sad.png"),
    dragon_happy: require("../../assets/companions/dragon_happy.png"),
    dragon_neutral: require("../../assets/companions/dragon_neutral.png"),
    dragon_sad: require("../../assets/companions/dragon_sad.png"),
};

// Fallback map for adoption picker (uses neutral)
const SPECIES_AVATARS: Record<PetSpecies, ReturnType<typeof require>> = {
    cat: require("../../assets/companions/cat_neutral.png"),
    dog: require("../../assets/companions/dog_neutral.png"),
    penguin: require("../../assets/companions/penguin_neutral.png"),
    fox: require("../../assets/companions/fox_neutral.png"),
    owl: require("../../assets/companions/owl_neutral.png"),
    dragon: require("../../assets/companions/dragon_neutral.png"),
};

function getAvatarSource(species: PetSpecies, happiness: number) {
    const mood: Mood = happiness > 70 ? "happy" : happiness > 30 ? "neutral" : "sad";
    return AVATAR_MAP[`${species}_${mood}`] || SPECIES_AVATARS[species];
}

const SPECIES_EMOJI: Record<PetSpecies, string> = {
    cat: "🐱", dog: "🐶", penguin: "🐧", fox: "🦊", owl: "🦉", dragon: "🐉",
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

const ADOPTABLE_SPECIES: { species: PetSpecies; emoji: string; desc: string }[] = [
    { species: "cat", emoji: "🐱", desc: "Curious & independent" },
    { species: "dog", emoji: "🐶", desc: "Loyal & energetic" },
    { species: "penguin", emoji: "🐧", desc: "Formal & precise" },
    { species: "fox", emoji: "🦊", desc: "Clever & resourceful" },
    { species: "owl", emoji: "🦉", desc: "Wise & thoughtful" },
    { species: "dragon", emoji: "🐉", desc: "Fierce & majestic" },
];

export default function CareTab() {
    const { isOnline, companionData, queueAction, updateCompanionLocal, sync } = useConnection();
    const [walking, setWalking] = useState(false);
    const [feeding, setFeeding] = useState(false);
    const [walkResult, setWalkResult] = useState<WalkEvent | null>(null);
    const [refreshing, setRefreshing] = useState(false);
    // Adoption flow state
    const [adopting, setAdopting] = useState(false);
    const [adoptName, setAdoptName] = useState("");
    const [adoptSpecies, setAdoptSpecies] = useState<PetSpecies>("cat");

    const companion = companionData?.companion;
    const petName = companion?.name || "";
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

    // Pull-to-refresh — Sprint 2
    const onRefresh = useCallback(async () => {
        setRefreshing(true);
        await sync();
        setRefreshing(false);
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
    }, [sync]);

    const handleFeed = useCallback(
        async (food: string) => {
            if (feeding) return;
            setFeeding(true);
            Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
            playSound("feed");

            if (isOnline) {
                try {
                    const res = await companionAPI.feed(food);
                    updateCompanionLocal(() => res.companion);
                } catch {
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
        Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
        playSound("walk");

        if (isOnline) {
            try {
                const res = await companionAPI.walk();
                updateCompanionLocal(() => res.companion);
                setWalkResult(res.event);
                Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
            } catch {
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
            Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
        }

        setTimeout(() => setWalking(false), 2000);
    }, [walking, isOnline, species, queueAction, updateCompanionLocal]);

    // Adoption flow — Sprint 2
    const handleAdopt = useCallback(async () => {
        const name = adoptName.trim();
        if (!name) return;
        setAdopting(true);
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);

        if (isOnline) {
            try {
                await companionAPI.adopt(name, adoptSpecies);
                await sync();
            } catch {
                // Optimistic local adoption
                updateCompanionLocal(() => ({
                    name,
                    species: adoptSpecies,
                    happiness: 80,
                    xp: 0,
                    level: 1,
                    streak: 0,
                }));
            }
        } else {
            updateCompanionLocal(() => ({
                name,
                species: adoptSpecies,
                happiness: 80,
                xp: 0,
                level: 1,
                streak: 0,
            }));
        }
        setAdopting(false);
    }, [adoptName, adoptSpecies, isOnline, sync, updateCompanionLocal]);

    // No companion — show adoption flow
    if (!petName) {
        return (
            <ScrollView style={styles.container} contentContainerStyle={styles.adoptContent}>
                <Text style={styles.adoptTitle}>🐾 Adopt a Companion</Text>
                <Text style={styles.adoptSubtitle}>
                    Choose a species and give your companion a name!
                </Text>

                {/* Species picker */}
                <View style={styles.speciesGrid}>
                    {ADOPTABLE_SPECIES.map((s) => (
                        <TouchableOpacity
                            key={s.species}
                            style={[
                                styles.speciesCard,
                                adoptSpecies === s.species && styles.speciesCardSelected,
                            ]}
                            onPress={() => {
                                setAdoptSpecies(s.species);
                                Haptics.selectionAsync();
                            }}
                            activeOpacity={0.7}
                        >
                            <Image
                                source={SPECIES_AVATARS[s.species]}
                                style={styles.speciesAvatar}
                            />
                            <Text style={styles.speciesName}>{s.species}</Text>
                            <Text style={styles.speciesDesc}>{s.desc}</Text>
                        </TouchableOpacity>
                    ))}
                </View>

                {/* Name input */}
                <TextInput
                    style={styles.nameInput}
                    value={adoptName}
                    onChangeText={setAdoptName}
                    placeholder="Name your companion..."
                    placeholderTextColor={colors.textMuted}
                    autoCapitalize="words"
                    maxLength={20}
                />

                {/* Adopt button */}
                <TouchableOpacity
                    style={[styles.adoptBtn, (!adoptName.trim() || adopting) && styles.adoptBtnDisabled]}
                    onPress={handleAdopt}
                    disabled={!adoptName.trim() || adopting}
                    activeOpacity={0.7}
                >
                    <Text style={styles.adoptBtnText}>
                        {adopting ? "Adopting..." : `Adopt ${adoptName.trim() || "companion"}`}
                    </Text>
                </TouchableOpacity>
            </ScrollView>
        );
    }

    return (
        <ScrollView
            style={styles.container}
            contentContainerStyle={styles.content}
            refreshControl={
                <RefreshControl
                    refreshing={refreshing}
                    onRefresh={onRefresh}
                    tintColor={colors.neon}
                    colors={[colors.neon]}
                />
            }
        >
            {/* Daily Gift — Sprint 4 */}
            <DailyGiftModal
                petName={petName}
                species={species}
                onCollect={(gift) => {
                    if (gift.happinessBoost) {
                        updateCompanionLocal((prev: any) => ({
                            ...prev,
                            happiness: Math.min(100, prev.happiness + gift.happinessBoost),
                        }));
                    }
                }}
            />

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

            {/* Avatar Card — Sprint 3: mood-reactive expression */}
            <View style={styles.avatarCard}>
                <Image source={getAvatarSource(species, happiness)} style={styles.avatarImage} />
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
    avatarImage: {
        width: 96,
        height: 96,
        borderRadius: 48,
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
    // Adoption flow styles
    adoptContent: {
        paddingHorizontal: spacing.lg,
        paddingTop: 80,
        paddingBottom: spacing.xxxl,
    },
    adoptTitle: {
        fontFamily: "Inter_700Bold",
        fontSize: fontSize.hero,
        color: colors.textPrimary,
        textAlign: "center",
        marginBottom: spacing.sm,
    },
    adoptSubtitle: {
        fontFamily: "Inter_400Regular",
        fontSize: fontSize.md,
        color: colors.textDim,
        textAlign: "center",
        marginBottom: spacing.xxl,
    },
    speciesGrid: {
        flexDirection: "row",
        flexWrap: "wrap",
        gap: spacing.sm,
        marginBottom: spacing.xxl,
    },
    speciesCard: {
        width: "31%",
        backgroundColor: colors.bgCard,
        borderRadius: borderRadius.md,
        borderWidth: 1,
        borderColor: colors.glassBorder,
        paddingVertical: spacing.md,
        alignItems: "center",
    },
    speciesCardSelected: {
        backgroundColor: colors.neonGlow,
        borderColor: colors.neon,
    },
    speciesAvatar: {
        width: 48,
        height: 48,
        borderRadius: 24,
        marginBottom: spacing.xs,
    },
    speciesName: {
        fontFamily: "Inter_500Medium",
        fontSize: fontSize.xs,
        color: colors.textPrimary,
        textTransform: "capitalize",
    },
    speciesDesc: {
        fontFamily: "Inter_400Regular",
        fontSize: fontSize.tiny,
        color: colors.textDim,
        textAlign: "center",
    },
    nameInput: {
        backgroundColor: colors.bgInput,
        borderWidth: 1,
        borderColor: colors.glassBorder,
        borderRadius: borderRadius.md,
        paddingHorizontal: spacing.lg,
        paddingVertical: spacing.lg,
        fontFamily: "Inter_400Regular",
        fontSize: fontSize.lg,
        color: colors.textPrimary,
        marginBottom: spacing.lg,
    },
    adoptBtn: {
        backgroundColor: colors.neon,
        borderRadius: borderRadius.md,
        paddingVertical: spacing.lg,
        alignItems: "center",
    },
    adoptBtnDisabled: {
        opacity: 0.4,
    },
    adoptBtnText: {
        fontFamily: "Inter_600SemiBold",
        fontSize: fontSize.lg,
        color: colors.bgPrimary,
    },
});
