/**
 * 🏠 Hub — Companion campfire scene + status + actions.
 *
 * The campfire reflects the power state:
 *   🔥 Home — full fire, sparks, "What are we building today?"
 *   ⚡ Connected — bright fire via Tailscale
 *   🕯️ Offline — dim candle, "pocket power"
 *   🔥 Reconnected — burst flare, "I'm back!"
 *
 * One companion, one soul. It dims when away from home.
 */
import { useState, useCallback, useEffect } from "react";
import {
    View,
    Text,
    TouchableOpacity,
    ScrollView,
    StyleSheet,
    RefreshControl,
} from "react-native";
import * as Haptics from "expo-haptics";
import { useConnection } from "../../src/hooks/useConnection";
import { companionAPI } from "../../src/api";
import { colors, spacing, borderRadius, fontSize, shadows } from "../../src/theme";
import { playSound } from "../../src/sounds";
import CampfireScene from "../../src/CampfireScene";
import FadedImage from "../../src/FadedImage";
import DailyGiftModal from "../../src/DailyGift";
import MorningBriefing from "../../src/MorningBriefing";
import type { PetSpecies, WalkEvent } from "../../src/types";

// Mood-reactive avatar images
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

function getAvatarSource(species: PetSpecies, happiness: number) {
    const mood: Mood = happiness > 70 ? "happy" : happiness > 30 ? "neutral" : "sad";
    return AVATAR_MAP[`${species}_${mood}`];
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

export default function HubTab() {
    const { isOnline, powerState, companionData, queueAction, updateCompanionLocal, sync } = useConnection();
    const [walking, setWalking] = useState(false);
    const [feeding, setFeeding] = useState(false);
    const [walkResult, setWalkResult] = useState<WalkEvent | null>(null);
    const [refreshing, setRefreshing] = useState(false);
    // Heartbeat — what the companion is doing right now
    const [heartbeat, setHeartbeat] = useState<{ activity: string; emoji: string; detail?: string } | null>(null);

    // Fetch heartbeat on mount + refresh
    useEffect(() => {
        if (isOnline) {
            companionAPI.heartbeat().then(setHeartbeat).catch(() => {});
        }
    }, [isOnline]);

    const companion = companionData?.companion;
    const petName = companion?.name || "";
    const species = (companion?.species || "fox") as PetSpecies;
    const happiness = companion?.happiness ?? 50;
    const xp = companion?.xp ?? 0;
    const level = companion?.level ?? 1;
    const xpNeeded = level * 20;

    const happinessColor =
        happiness > 70 ? colors.happinessHigh :
            happiness > 30 ? colors.happinessMid :
                colors.happinessLow;

    const onRefresh = useCallback(async () => {
        setRefreshing(true);
        await sync();
        if (isOnline) {
            companionAPI.heartbeat().then(setHeartbeat).catch(() => {});
        }
        setRefreshing(false);
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
    }, [sync, isOnline]);

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

    // No companion data — show transfer instruction
    if (!petName) {
        return (
            <ScrollView style={styles.container} contentContainerStyle={styles.waitingContent}>
                <Text style={styles.waitingTitle}>🔥 Almost There!</Text>
                <Text style={styles.waitingSubtitle}>
                    Your companion hasn't arrived yet. Make sure your PC is running and you've completed pairing.
                </Text>
                <View style={styles.transferCard}>
                    <Text style={styles.transferEmoji}>📱 ↔ 💻</Text>
                    <Text style={styles.transferTitle}>One soul, two devices</Text>
                    <Text style={styles.transferStep}>Your companion's brain lives on your PC.</Text>
                    <Text style={styles.transferStep}>This phone is the portal — same personality, same memories.</Text>
                    <Text style={styles.transferStep}>Pull down to refresh once your PC is connected.</Text>
                </View>
            </ScrollView>
        );
    }

    return (
        <ScrollView
            style={styles.container}
            contentContainerStyle={styles.content}
            refreshControl={
                <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.neon} />
            }
        >
            {/* Morning Briefing */}
            <MorningBriefing
                petName={petName}
                species={species}
                platform={companionData?.platform}
            />

            {/* Heartbeat Feed — what the companion is doing right now */}
            {heartbeat && (
                <View style={styles.heartbeatBanner}>
                    <Text style={styles.heartbeatEmoji}>{heartbeat.emoji}</Text>
                    <View style={styles.heartbeatContent}>
                        <Text style={styles.heartbeatActivity}>{heartbeat.activity}</Text>
                        {heartbeat.detail && (
                            <Text style={styles.heartbeatDetail}>{heartbeat.detail}</Text>
                        )}
                    </View>
                    <Text style={styles.heartbeatLive}>● LIVE</Text>
                </View>
            )}

            {/* Daily Gift */}
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

            {/* ═══ Campfire Scene ═══ */}
            <CampfireScene
                powerState={powerState}
                companionEmoji={SPECIES_EMOJI[species]}
                companionName={petName}
            />

            {/* Avatar + Name */}
            <View style={styles.avatarRow}>
                <FadedImage
                    source={getAvatarSource(species, happiness)}
                    size={72}
                    fadeWidth={14}
                    circular
                />
                <View>
                    <Text style={styles.avatarName}>{petName}</Text>
                    <Text style={styles.avatarSpecies}>Level {level} {species}</Text>
                </View>
            </View>

            {/* Stat Bars */}
            <View style={styles.statsRow}>
                {/* Happiness */}
                <View style={styles.statCard}>
                    <Text style={styles.statLabel}>
                        {happiness > 70 ? "💚" : happiness > 30 ? "💛" : "🧡"} Mood
                    </Text>
                    <View style={styles.barTrack}>
                        <View style={[styles.barFill, { width: `${happiness}%`, backgroundColor: happinessColor }]} />
                    </View>
                    <Text style={styles.statValue}>{happiness}%</Text>
                </View>

                {/* XP */}
                <View style={styles.statCard}>
                    <Text style={styles.statLabel}>✨ XP</Text>
                    <View style={styles.barTrack}>
                        <View style={[styles.barFill, styles.xpBar, { width: `${Math.min(100, (xp / xpNeeded) * 100)}%` }]} />
                    </View>
                    <Text style={styles.statValue}>{xp}/{xpNeeded}</Text>
                </View>
            </View>

            {/* Actions */}
            <View style={styles.actionRow}>
                <TouchableOpacity
                    style={[styles.actionBtn, walking && styles.actionBtnDisabled]}
                    onPress={handleWalk}
                    disabled={walking}
                    activeOpacity={0.7}
                >
                    <Text style={styles.actionEmoji}>{walking ? "🚶" : "🐾"}</Text>
                    <Text style={styles.actionText}>{walking ? "Walking..." : "Walk"}</Text>
                </TouchableOpacity>

                <TouchableOpacity
                    style={[styles.actionBtn, styles.actionBtnPrimary]}
                    onPress={() => handleFeed("treat")}
                    disabled={feeding || happiness >= 100}
                    activeOpacity={0.7}
                >
                    <Text style={styles.actionEmoji}>🍬</Text>
                    <Text style={[styles.actionText, styles.actionTextPrimary]}>Feed</Text>
                </TouchableOpacity>

                <TouchableOpacity
                    style={styles.actionBtn}
                    onPress={() => {
                        Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
                        playSound("feed");
                        updateCompanionLocal((prev) => ({
                            ...prev,
                            happiness: Math.min(100, prev.happiness + 5),
                            xp: prev.xp + 1,
                        }));
                    }}
                    activeOpacity={0.7}
                >
                    <Text style={styles.actionEmoji}>🎾</Text>
                    <Text style={styles.actionText}>Play</Text>
                </TouchableOpacity>
            </View>

            {/* Walk Result */}
            {walkResult && (
                <View style={styles.walkResult}>
                    <Text style={styles.walkResultText}>
                        {walkResult.emoji} {petName} {walkResult.text}
                    </Text>
                    <Text style={styles.walkBonus}>
                        +{walkResult.happinessBoost}% mood · +{walkResult.xpGain} XP
                    </Text>
                </View>
            )}

            {/* Feed Options */}
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

            {happiness < 30 && (
                <Text style={styles.warningText}>Your companion misses you 🥺</Text>
            )}
        </ScrollView>
    );
}

const styles = StyleSheet.create({
    container: { flex: 1, backgroundColor: colors.bgPrimary },
    content: { paddingHorizontal: spacing.lg, paddingTop: 60, paddingBottom: spacing.xxxl },
    // Avatar row
    avatarRow: { flexDirection: "row", alignItems: "center", gap: spacing.md, marginBottom: spacing.lg },
    // avatarImage now handled by FadedImage component
    avatarName: { fontFamily: "Inter_700Bold", fontSize: fontSize.lg, color: colors.textPrimary },
    avatarSpecies: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.textDim, textTransform: "capitalize" },
    // Stats
    statsRow: { flexDirection: "row", gap: spacing.sm, marginBottom: spacing.lg },
    statCard: { flex: 1, backgroundColor: colors.bgCard, borderRadius: borderRadius.md, borderWidth: 1, borderColor: colors.glassBorder, padding: spacing.md },
    statLabel: { fontFamily: "Inter_400Regular", fontSize: fontSize.tiny, color: colors.textDim, marginBottom: spacing.xs },
    barTrack: { height: 6, borderRadius: 3, backgroundColor: colors.bgInput, overflow: "hidden", marginBottom: spacing.xs },
    barFill: { height: 6, borderRadius: 3 },
    xpBar: { backgroundColor: colors.neon },
    statValue: { fontFamily: "Inter_500Medium", fontSize: fontSize.tiny, color: colors.textSecondary, textAlign: "right" },
    // Actions
    actionRow: { flexDirection: "row", gap: spacing.sm, marginBottom: spacing.lg },
    actionBtn: { flex: 1, backgroundColor: colors.bgCard, borderRadius: borderRadius.md, borderWidth: 1, borderColor: colors.glassBorder, paddingVertical: spacing.md, alignItems: "center", ...shadows.card },
    actionBtnPrimary: { backgroundColor: colors.neon, borderColor: colors.neon, ...shadows.glow },
    actionBtnDisabled: { opacity: 0.4 },
    actionEmoji: { fontSize: 24, marginBottom: 2 },
    actionText: { fontFamily: "Inter_500Medium", fontSize: fontSize.tiny, color: colors.textDim },
    actionTextPrimary: { color: colors.bgPrimary },
    // Walk result
    walkResult: { backgroundColor: colors.neonGlow, borderWidth: 1, borderColor: colors.neonBorder, borderRadius: borderRadius.md, padding: spacing.md, marginBottom: spacing.lg },
    walkResultText: { fontFamily: "Inter_400Regular", fontSize: fontSize.sm, color: colors.textSecondary, lineHeight: 20 },
    walkBonus: { fontFamily: "Inter_400Regular", fontSize: fontSize.tiny, color: colors.neon, marginTop: spacing.xs },
    // Feed
    sectionLabel: { fontFamily: "Inter_500Medium", fontSize: fontSize.sm, color: colors.textDim, marginBottom: spacing.sm },
    treatRow: { flexDirection: "row", gap: spacing.sm, marginBottom: spacing.md },
    treatBtn: { flex: 1, backgroundColor: colors.bgCard, borderRadius: borderRadius.md, borderWidth: 1, borderColor: colors.glassBorder, paddingVertical: spacing.md, alignItems: "center" },
    treatBtnDisabled: { opacity: 0.3 },
    treatEmoji: { fontSize: 24, marginBottom: 2 },
    treatName: { fontFamily: "Inter_400Regular", fontSize: fontSize.tiny, color: colors.textDim },
    warningText: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.warning, textAlign: "center", marginTop: spacing.sm },
    // Transfer waiting
    waitingContent: { paddingHorizontal: spacing.lg, paddingTop: 80, paddingBottom: spacing.xxxl },
    waitingTitle: { fontFamily: "Inter_700Bold", fontSize: fontSize.hero, color: colors.textPrimary, textAlign: "center", marginBottom: spacing.sm },
    waitingSubtitle: { fontFamily: "Inter_400Regular", fontSize: fontSize.md, color: colors.textDim, textAlign: "center", marginBottom: spacing.xxl },
    transferCard: { backgroundColor: colors.bgCard, borderRadius: borderRadius.lg, borderWidth: 1, borderColor: colors.neonBorder, padding: spacing.xl, marginBottom: spacing.xl, ...shadows.card },
    transferEmoji: { fontSize: 32, textAlign: "center", marginBottom: spacing.md },
    transferTitle: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.md, color: colors.textPrimary, textAlign: "center", marginBottom: spacing.md },
    transferStep: { fontFamily: "Inter_400Regular", fontSize: fontSize.sm, color: colors.textSecondary, lineHeight: 24, paddingLeft: spacing.sm },
    transferNote: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.textDim, textAlign: "center", lineHeight: 18 },
    // Heartbeat banner
    heartbeatBanner: { flexDirection: "row", alignItems: "center", backgroundColor: colors.bgCard, borderRadius: borderRadius.md, borderWidth: 1, borderColor: colors.neonBorder, padding: spacing.md, marginBottom: spacing.lg, gap: spacing.sm, ...shadows.card },
    heartbeatEmoji: { fontSize: 24 },
    heartbeatContent: { flex: 1 },
    heartbeatActivity: { fontFamily: "Inter_500Medium", fontSize: fontSize.sm, color: colors.textPrimary },
    heartbeatDetail: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.textDim, marginTop: 2 },
    heartbeatLive: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.tiny, color: colors.neon },
});
