/**
 * ⚔️ Quest Tab — Adventures screen.
 *
 * Sprint 4 Task 1: Port AdventureCard.tsx from dashboard to mobile.
 * 8 encounter types with species-specific narratives, choices, and rewards.
 * Phases: idle → intro → active → result
 */
import { useState, useRef, useCallback } from "react";
import {
    View,
    Text,
    TextInput,
    TouchableOpacity,
    ScrollView,
    StyleSheet,
    Animated,
    Image,
} from "react-native";
import * as Haptics from "expo-haptics";
import { useConnection } from "../../src/hooks/useConnection";
import { companionAPI } from "../../src/api";
import { playSound } from "../../src/sounds";
import { colors, spacing, borderRadius, fontSize, shadows } from "../../src/theme";
import type { PetSpecies } from "../../src/types";

// --- Types ---
interface LootItem {
    item: string;
    chance: number;
    emoji: string;
    happiness?: number;
    rare?: boolean;
    description?: string;
}
interface Choice {
    text: string;
    reward: { xp?: number; happiness?: number; item?: string };
}
interface Adventure {
    type: "riddle" | "treasure" | "merchant" | "forage" | "lost_pet" | "weather" | "storyteller" | "challenge";
    intro: string;
    riddle?: string;
    answer?: string;
    acceptAnswers?: string[];
    failText?: string;
    lootTable?: LootItem[];
    choices?: Choice[];
    story?: string;
    moral?: string;
    text?: string;
    reward?: { xp?: number; happiness?: number; item?: string };
    failReward?: { xp?: number; happiness?: number };
    winReward?: { xp?: number; happiness?: number; item?: string };
    loseReward?: { xp?: number; happiness?: number };
}
type Reward = { xp?: number; happiness?: number; item?: string };

// --- Encounter icons & labels ---
const TYPE_ICONS: Record<string, string> = {
    riddle: "🗿", treasure: "🎁", merchant: "👻", forage: "🌿",
    lost_pet: "🐾", weather: "⛈️", storyteller: "🎭", challenge: "🏴‍☠️",
};
const TYPE_LABELS: Record<string, string> = {
    riddle: "Riddle Guardian", treasure: "Treasure Chest", merchant: "Ghostly Merchant",
    forage: "Herb Foraging", lost_pet: "Lost Pet", weather: "Weather Event",
    storyteller: "The Storyteller", challenge: "The Challenger",
};

// --- Species adventures (from dashboard AdventureCard.tsx) ---
const ADVENTURES: Record<PetSpecies, Adventure> = {
    cat: {
        type: "riddle",
        intro: "A stone cat statue blocks the path. Its eyes glow.\n\"Answer my riddle, mortal.\"",
        riddle: "I have cities but no houses, forests but no trees, water but no fish. What am I?",
        answer: "a map", acceptAnswers: ["map", "a map"],
        reward: { xp: 25, happiness: 15, item: "ancient_compass" },
        failText: "The statue yawns. \"Disappointing. Even for a human.\"",
        failReward: { xp: 5, happiness: 5 },
    },
    dog: {
        type: "treasure",
        intro: "YOUR NOSE IS GOING CRAZY!!\nThere's something buried here!!",
        lootTable: [
            { item: "golden_treat", chance: 0.4, emoji: "🍬✨", happiness: 30 },
            { item: "tiny_hat", chance: 0.3, emoji: "🎩" },
            { item: "mystery_egg", chance: 0.2, emoji: "🥚", description: "It's warm..." },
            { item: "legendary_bone", chance: 0.1, emoji: "🦴✨", happiness: 50, rare: true },
        ],
    },
    penguin: {
        type: "storyteller",
        intro: "An old raven perches on a formal lectern.\n\"Shall I read the minutes of a prior age?\"",
        story: "Once, a penguin filed a complaint about the temperature of the ocean. It took 400 years, but eventually, the currents shifted. Bureaucracy wins in the end.",
        moral: "Persistence outlasts everything.",
        reward: { xp: 10, happiness: 10, item: "story_fragment" },
    },
    fox: {
        type: "lost_pet",
        intro: "A tiny hamster is shivering behind a mushroom.\nIt looks lost...",
        choices: [
            { text: "🤝 Help it find home", reward: { xp: 20, happiness: 25, item: "friendship_badge" } },
            { text: "🐟 Give it some food", reward: { xp: 10, happiness: 15 } },
            { text: "👋 Walk away", reward: { xp: 0, happiness: -5 } },
        ],
    },
    owl: {
        type: "forage",
        intro: "A patch of moonlit herbs rustles with potential.\nYour owl investigates...",
        lootTable: [
            { item: "moonpetal", chance: 0.5, emoji: "🌸", happiness: 25, description: "+25 happiness" },
            { item: "sunroot", chance: 0.3, emoji: "☀️", description: "Double XP next walk" },
            { item: "dreamberry", chance: 0.2, emoji: "🫐", description: "Extra morning briefing" },
        ],
    },
    dragon: {
        type: "challenge",
        intro: "A rival dragon lands with a THUD.\n\"I can roar louder than you!\nPROVE ME WRONG!\"",
        winReward: { xp: 30, happiness: 20, item: "champion_scarf" },
        loseReward: { xp: 10, happiness: 5 },
    },
};

// Avatar map (reuse neutral for quest screen)
const SPECIES_AVATARS: Record<PetSpecies, ReturnType<typeof require>> = {
    cat: require("../../assets/companions/cat_neutral.png"),
    dog: require("../../assets/companions/dog_neutral.png"),
    penguin: require("../../assets/companions/penguin_neutral.png"),
    fox: require("../../assets/companions/fox_neutral.png"),
    owl: require("../../assets/companions/owl_neutral.png"),
    dragon: require("../../assets/companions/dragon_neutral.png"),
};

export default function QuestTab() {
    const { isOnline, companionData, updateCompanionLocal } = useConnection();
    const [phase, setPhase] = useState<"idle" | "intro" | "active" | "result">("idle");
    const [riddleInput, setRiddleInput] = useState("");
    const [resultText, setResultText] = useState("");
    const [resultReward, setResultReward] = useState<Reward | null>(null);
    const [tapCount, setTapCount] = useState(0);
    const [tapping, setTapping] = useState(false);
    const scaleAnim = useRef(new Animated.Value(1)).current;

    const petName = companionData?.companion?.name || "Companion";
    const species = (companionData?.companion?.species || "cat") as PetSpecies;
    const adventure = ADVENTURES[species];

    const applyReward = useCallback((reward: Reward) => {
        updateCompanionLocal((prev) => ({
            ...prev,
            happiness: Math.min(100, Math.max(0, prev.happiness + (reward.happiness || 0))),
            xp: prev.xp + (reward.xp || 0),
        }));
    }, [updateCompanionLocal]);

    const handleStartAdventure = () => {
        setPhase("intro");
        setRiddleInput("");
        setResultText("");
        setResultReward(null);
        setTapCount(0);
        Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    };

    const handleEnterAdventure = () => {
        setPhase("active");
        Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);

        // Auto-resolve certain types
        if (adventure.type === "treasure" || adventure.type === "forage") {
            handleTreasure();
        }
        if (adventure.type === "weather") {
            setResultText(adventure.text || "Something happened!");
            setResultReward(adventure.reward || { xp: 5 });
            setPhase("result");
        }
    };

    const handleRiddleSubmit = () => {
        const isCorrect = adventure.acceptAnswers?.some(
            (a) => riddleInput.trim().toLowerCase() === a.toLowerCase()
        );
        if (isCorrect) {
            setResultText(`✅ Correct! ${petName} puffs with pride.`);
            setResultReward(adventure.reward || { xp: 10, happiness: 10 });
            Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
        } else {
            setResultText(adventure.failText || "Not quite...");
            setResultReward(adventure.failReward || { xp: 5 });
            Haptics.notificationAsync(Haptics.NotificationFeedbackType.Warning);
        }
        setPhase("result");
    };

    const handleTreasure = () => {
        const table = adventure.lootTable || [];
        const roll = Math.random();
        let cumulative = 0;
        for (const loot of table) {
            cumulative += loot.chance;
            if (roll <= cumulative) {
                const rareTag = loot.rare ? " ✨ RARE!" : "";
                setResultText(
                    `${loot.emoji} Found: ${loot.item.replace(/_/g, " ")}${rareTag}${loot.description ? ` — ${loot.description}` : ""}`
                );
                setResultReward({ xp: 15, happiness: loot.happiness || 10, item: loot.item });
                setPhase("result");
                Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
                return;
            }
        }
    };

    const handleChoice = (choice: Choice) => {
        setResultText(`${petName} chose: "${choice.text.slice(2)}"`);
        setResultReward(choice.reward);
        setPhase("result");
        Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    };

    const handleChallenge = () => {
        setTapping(true);
        setTapCount(0);
        Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Heavy);
        setTimeout(() => {
            setTapping(false);
            if (tapCount >= 10) {
                setResultText(`🏆 YOU WIN! ${petName} roars triumphantly!`);
                setResultReward(adventure.winReward || { xp: 20, happiness: 15 });
                Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
            } else {
                setResultText(`Close! ${tapCount}/10 taps. ${petName} shakes it off. "Next time!"`);
                setResultReward(adventure.loseReward || { xp: 5, happiness: 5 });
            }
            setPhase("result");
        }, 5000);
    };

    const handleCollect = () => {
        if (resultReward) {
            applyReward(resultReward);
            playSound("levelUp");
        }
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
        setPhase("idle");
    };

    const handleTap = () => {
        setTapCount((c) => c + 1);
        Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
        // Bounce animation
        Animated.sequence([
            Animated.spring(scaleAnim, { toValue: 0.85, useNativeDriver: true, speed: 50 }),
            Animated.spring(scaleAnim, { toValue: 1, useNativeDriver: true, speed: 50 }),
        ]).start();
    };

    return (
        <ScrollView style={styles.container} contentContainerStyle={styles.content}>
            {/* Header */}
            <Text style={styles.title}>⚔️ Adventures</Text>
            <Text style={styles.subtitle}>
                Encounter quests on your companion's journey
            </Text>

            {/* Idle — start button */}
            {phase === "idle" && (
                <View style={styles.idleCard}>
                    <Image source={SPECIES_AVATARS[species]} style={styles.idleAvatar} />
                    <Text style={styles.idleTitle}>
                        {petName} is ready for adventure!
                    </Text>
                    <Text style={styles.idleType}>
                        {TYPE_ICONS[adventure.type]} {TYPE_LABELS[adventure.type]}
                    </Text>
                    <TouchableOpacity
                        style={styles.startBtn}
                        onPress={handleStartAdventure}
                        activeOpacity={0.7}
                    >
                        <Text style={styles.startBtnText}>🗡️ Start Adventure</Text>
                    </TouchableOpacity>
                </View>
            )}

            {/* Intro */}
            {phase === "intro" && (
                <View style={styles.adventureCard}>
                    <View style={styles.cardHeader}>
                        <Text style={styles.encounterIcon}>{TYPE_ICONS[adventure.type]}</Text>
                        <View>
                            <Text style={styles.encounterLabel}>{TYPE_LABELS[adventure.type]}</Text>
                            <Text style={styles.encounterSub}>Adventure Encounter</Text>
                        </View>
                    </View>
                    <Text style={styles.narrative}>{adventure.intro}</Text>
                    <TouchableOpacity
                        style={styles.actionBtn}
                        onPress={handleEnterAdventure}
                        activeOpacity={0.7}
                    >
                        <Text style={styles.actionBtnText}>🗡️ Enter the Adventure</Text>
                    </TouchableOpacity>
                </View>
            )}

            {/* Active — type-specific */}
            {phase === "active" && (
                <View style={styles.adventureCard}>
                    <View style={styles.cardHeader}>
                        <Text style={styles.encounterIcon}>{TYPE_ICONS[adventure.type]}</Text>
                        <Text style={styles.encounterLabel}>{TYPE_LABELS[adventure.type]}</Text>
                    </View>

                    {/* Riddle */}
                    {adventure.type === "riddle" && (
                        <View>
                            <Text style={styles.narrative}>"{adventure.riddle}"</Text>
                            <View style={styles.riddleRow}>
                                <TextInput
                                    style={styles.riddleInput}
                                    value={riddleInput}
                                    onChangeText={setRiddleInput}
                                    placeholder="Your answer..."
                                    placeholderTextColor={colors.textMuted}
                                    onSubmitEditing={handleRiddleSubmit}
                                    returnKeyType="done"
                                />
                                <TouchableOpacity
                                    style={styles.riddleBtn}
                                    onPress={handleRiddleSubmit}
                                    activeOpacity={0.7}
                                >
                                    <Text style={styles.riddleBtnText}>Answer</Text>
                                </TouchableOpacity>
                            </View>
                        </View>
                    )}

                    {/* Storyteller */}
                    {adventure.type === "storyteller" && (
                        <View>
                            <Text style={styles.narrative}>"{adventure.story}"</Text>
                            {adventure.moral && (
                                <Text style={styles.moral}>💡 Moral: {adventure.moral}</Text>
                            )}
                            <TouchableOpacity
                                style={styles.actionBtn}
                                onPress={() => {
                                    setResultReward(adventure.reward || { xp: 10 });
                                    setResultText(`📜 ${petName} remembers this story.`);
                                    setPhase("result");
                                }}
                                activeOpacity={0.7}
                            >
                                <Text style={styles.actionBtnText}>Continue →</Text>
                            </TouchableOpacity>
                        </View>
                    )}

                    {/* Choices (lost_pet) */}
                    {adventure.type === "lost_pet" && adventure.choices && (
                        <View>
                            <Text style={styles.choicePrompt}>What will {petName} do?</Text>
                            {adventure.choices.map((choice, i) => (
                                <TouchableOpacity
                                    key={i}
                                    style={styles.choiceBtn}
                                    onPress={() => handleChoice(choice)}
                                    activeOpacity={0.7}
                                >
                                    <Text style={styles.choiceBtnText}>{choice.text}</Text>
                                </TouchableOpacity>
                            ))}
                        </View>
                    )}

                    {/* Challenge (tap game) */}
                    {adventure.type === "challenge" && (
                        <View style={styles.challengeArea}>
                            {!tapping ? (
                                <TouchableOpacity
                                    style={styles.actionBtn}
                                    onPress={handleChallenge}
                                    activeOpacity={0.7}
                                >
                                    <Text style={styles.actionBtnText}>⚔️ Accept Challenge!</Text>
                                </TouchableOpacity>
                            ) : (
                                <View style={styles.tapArea}>
                                    <Text style={styles.tapInstructions}>
                                        TAP! TAP! TAP! (10 taps in 5 seconds)
                                    </Text>
                                    <Animated.View style={{ transform: [{ scale: scaleAnim }] }}>
                                        <TouchableOpacity
                                            style={styles.tapButton}
                                            onPress={handleTap}
                                            activeOpacity={0.7}
                                        >
                                            <Text style={styles.tapCount}>{tapCount}</Text>
                                        </TouchableOpacity>
                                    </Animated.View>
                                </View>
                            )}
                        </View>
                    )}
                </View>
            )}

            {/* Result */}
            {phase === "result" && (
                <View style={styles.resultCard}>
                    <Text style={styles.resultText}>{resultText}</Text>
                    {resultReward && (
                        <View style={styles.rewardRow}>
                            {resultReward.xp ? <Text style={styles.rewardTag}>+{resultReward.xp} XP</Text> : null}
                            {resultReward.happiness ? <Text style={styles.rewardTag}>+{resultReward.happiness}% 💚</Text> : null}
                            {resultReward.item ? <Text style={styles.rewardTag}>📦 {resultReward.item.replace(/_/g, " ")}</Text> : null}
                        </View>
                    )}
                    <TouchableOpacity
                        style={styles.collectBtn}
                        onPress={handleCollect}
                        activeOpacity={0.7}
                    >
                        <Text style={styles.collectBtnText}>✨ Collect & Continue</Text>
                    </TouchableOpacity>
                </View>
            )}
        </ScrollView>
    );
}

const styles = StyleSheet.create({
    container: { flex: 1, backgroundColor: colors.bgPrimary },
    content: { paddingHorizontal: spacing.lg, paddingTop: 60, paddingBottom: spacing.xxxl },
    title: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.xl, color: colors.textPrimary, marginBottom: 2 },
    subtitle: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.textDim, marginBottom: spacing.xl },
    // Idle state
    idleCard: { backgroundColor: colors.bgCard, borderRadius: borderRadius.lg, borderWidth: 1, borderColor: colors.glassBorder, padding: spacing.xxl, alignItems: "center", ...shadows.card },
    idleAvatar: { width: 80, height: 80, borderRadius: 40, marginBottom: spacing.md },
    idleTitle: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.lg, color: colors.textPrimary, marginBottom: spacing.xs, textAlign: "center" },
    idleType: { fontFamily: "Inter_400Regular", fontSize: fontSize.sm, color: colors.textDim, marginBottom: spacing.xl },
    startBtn: { backgroundColor: colors.neon, borderRadius: borderRadius.md, paddingVertical: spacing.md + 2, paddingHorizontal: spacing.xxxl, width: "100%", alignItems: "center", ...shadows.glow },
    startBtnText: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.md, color: colors.bgPrimary },
    // Adventure Card
    adventureCard: { backgroundColor: colors.bgCard, borderRadius: borderRadius.lg, borderWidth: 1, borderColor: colors.glassBorder, borderLeftWidth: 3, borderLeftColor: colors.neon, padding: spacing.xl },
    cardHeader: { flexDirection: "row", alignItems: "center", gap: spacing.sm, marginBottom: spacing.md },
    encounterIcon: { fontSize: 24 },
    encounterLabel: { fontFamily: "Inter_500Medium", fontSize: fontSize.sm, color: colors.neon },
    encounterSub: { fontFamily: "Inter_400Regular", fontSize: fontSize.tiny, color: colors.textMuted },
    narrative: { fontFamily: "Inter_400Regular", fontSize: fontSize.sm, color: colors.textSecondary, lineHeight: 22, fontStyle: "italic", marginBottom: spacing.lg },
    // Actions
    actionBtn: { backgroundColor: colors.neon, borderRadius: borderRadius.md, paddingVertical: spacing.md, alignItems: "center", ...shadows.glow },
    actionBtnText: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.sm, color: colors.bgPrimary },
    // Riddle
    riddleRow: { flexDirection: "row", gap: spacing.sm },
    riddleInput: { flex: 1, backgroundColor: colors.bgInput, borderWidth: 1, borderColor: colors.glassBorder, borderRadius: borderRadius.md, paddingHorizontal: spacing.md, paddingVertical: spacing.sm, fontFamily: "Inter_400Regular", fontSize: fontSize.sm, color: colors.textPrimary },
    riddleBtn: { backgroundColor: colors.neon, borderRadius: borderRadius.md, paddingHorizontal: spacing.lg, justifyContent: "center" },
    riddleBtnText: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.xs, color: colors.bgPrimary },
    // Story
    moral: { fontFamily: "Inter_400Regular", fontSize: fontSize.tiny, color: colors.neon, marginBottom: spacing.md },
    // Choices
    choicePrompt: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.textDim, marginBottom: spacing.sm },
    choiceBtn: { backgroundColor: colors.bgInput, borderRadius: borderRadius.md, paddingVertical: spacing.md, paddingHorizontal: spacing.md, marginBottom: spacing.sm },
    choiceBtnText: { fontFamily: "Inter_400Regular", fontSize: fontSize.sm, color: colors.textSecondary },
    // Challenge
    challengeArea: { alignItems: "center" },
    tapArea: { alignItems: "center" },
    tapInstructions: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.textDim, marginBottom: spacing.md },
    tapButton: { width: 96, height: 96, borderRadius: 48, backgroundColor: colors.neonGlow, borderWidth: 2, borderColor: colors.neon, justifyContent: "center", alignItems: "center" },
    tapCount: { fontFamily: "Inter_700Bold", fontSize: 28, color: colors.neon },
    // Result
    resultCard: { backgroundColor: colors.neonGlow, borderWidth: 1, borderColor: colors.neonBorder, borderRadius: borderRadius.lg, padding: spacing.xl },
    resultText: { fontFamily: "Inter_400Regular", fontSize: fontSize.sm, color: colors.textSecondary, lineHeight: 22, marginBottom: spacing.md },
    rewardRow: { flexDirection: "row", gap: spacing.md, marginBottom: spacing.lg },
    rewardTag: { fontFamily: "Inter_400Regular", fontSize: fontSize.tiny, color: colors.neon },
    collectBtn: { backgroundColor: colors.neon, borderRadius: borderRadius.md, paddingVertical: spacing.md, alignItems: "center", ...shadows.glow },
    collectBtnText: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.sm, color: colors.bgPrimary },
});
