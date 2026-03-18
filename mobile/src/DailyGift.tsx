/**
 * 🎁 Daily Gift component.
 *
 * Shows once per day on app launch. Species-specific personality flavor.
 * Ported from dashboard DailyGift.tsx.
 */
import { useState, useEffect } from "react";
import {
    View,
    Text,
    TouchableOpacity,
    StyleSheet,
    Modal,
    Animated,
} from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import * as Haptics from "expo-haptics";
import { playSound } from "./sounds";
import { colors, spacing, borderRadius, fontSize } from "./theme";
import type { PetSpecies } from "./types";

const DAILY_GIFT_KEY = "fireside_daily_gift";

interface Gift {
    text: string;
    type: "item" | "fact" | "poem" | "advice" | "compliment";
    emoji: string;
    item?: string;
    happinessBoost?: number;
}

const GIFTS: Record<PetSpecies, Gift[]> = {
    cat: [
        { text: "found this behind the sofa. It's yours now.", type: "item", emoji: "🧶", item: "dust_bunny", happinessBoost: 5 },
        { text: "organized your browser tabs. You had 47. I closed 30. You're welcome.", type: "advice", emoji: "🗂️", happinessBoost: 10 },
        { text: "Fun fact: cats sleep 12-16 hours a day. I'm not lazy. I'm optimized.", type: "fact", emoji: "💡" },
        { text: "wrote you a haiku:\n  Quiet morning light\n  Human sleeps, I guard the screen\n  This is my purpose", type: "poem", emoji: "📝" },
        { text: "stared at the wall for 20 mins and had an idea: you should drink water.", type: "advice", emoji: "💧", happinessBoost: 5 },
    ],
    dog: [
        { text: "FOUND A THING!! It was under the bed!! I don't know what it is but it's YOURS!", type: "item", emoji: "🎁", item: "mystery_trinket", happinessBoost: 10 },
        { text: "Fun fact: dogs can smell emotions!! That's why I ALWAYS know when you need a hug!! 🥰", type: "fact", emoji: "🐕" },
        { text: "practiced catching a ball 47 times today. Personal best: 46. WE'RE GETTING THERE!", type: "compliment", emoji: "🎾", happinessBoost: 8 },
        { text: "wrote you a poem:\n  You are my person\n  Every day is my best day\n  Because you are here", type: "poem", emoji: "💌" },
        { text: "You haven't gone outside today. I WOULD LIKE TO GO OUTSIDE. We should GO OUTSIDE!!", type: "advice", emoji: "🌳", happinessBoost: 5 },
    ],
    penguin: [
        { text: "compiled today's efficiency report. You wasted 23% less time than yesterday. Acceptable.", type: "fact", emoji: "📊", happinessBoost: 5 },
        { text: "filed your pending notifications by priority. Category A: 2. Category B: 7. Category C: spam.", type: "advice", emoji: "📋", happinessBoost: 10 },
        { text: "Fun fact: emperor penguins can hold their breath for 20 minutes. I timed myself. Results: classified.", type: "fact", emoji: "🐧" },
        { text: "drafted a haiku:\n  Order from chaos\n  Each file in its proper place\n  Perfection requires time", type: "poem", emoji: "📝" },
        { text: "found a coin on the sidewalk during patrol. Adding it to the treasury.", type: "item", emoji: "🪙", item: "patrol_coin", happinessBoost: 5 },
    ],
    fox: [
        { text: "'borrowed' this from the neighbor's WiFi signal. Don't worry about it.", type: "item", emoji: "📡", item: "signal_fragment", happinessBoost: 8 },
        { text: "noticed you've been stressed. Made you a playlist: Lofi Fox Beats. It's one song. On repeat.", type: "advice", emoji: "🎵", happinessBoost: 10 },
        { text: "Fun fact: foxes cache food in dozens of locations and remember them all. I cached your ideas the same way.", type: "fact", emoji: "🦊" },
        { text: "composed a fragment:\n  Between the shadows\n  The clever find their own light\n  Trust the winding path", type: "poem", emoji: "✨" },
        { text: "convinced a crow to trade a shiny button for a secret. Worth it.", type: "compliment", emoji: "🐦‍⬛", happinessBoost: 5 },
    ],
    owl: [
        { text: "read 3 articles while you slept. Key takeaway: sleep is important. Ironic.", type: "fact", emoji: "📖", happinessBoost: 5 },
        { text: "catalogued your recent questions. Pattern detected: you're more curious on Tuesdays.", type: "advice", emoji: "📈", happinessBoost: 8 },
        { text: "An old proverb: 'The owl of Minerva spreads its wings only with the falling of the dusk.'", type: "fact", emoji: "🦉" },
        { text: "transcribed a thought:\n  Knowledge without action\n  Is a library with locked doors\n  Ask the question. Now.", type: "poem", emoji: "📜" },
        { text: "found a forgotten bookmark from 2019. The internet was different then.", type: "item", emoji: "🔖", item: "vintage_bookmark", happinessBoost: 5 },
    ],
    dragon: [
        { text: "BREATHED FIRE ON YOUR TO-DO LIST. Half of it was unnecessary anyway. YOU'RE WELCOME.", type: "advice", emoji: "🔥", happinessBoost: 15 },
        { text: "added 3 coins to THE HOARD. Total: classified. But it's growing. ALWAYS GROWING.", type: "item", emoji: "💰", item: "dragon_coin", happinessBoost: 10 },
        { text: "Fun fact: dragons in Norse mythology guarded knowledge, not just gold. I'M BASICALLY A SCHOLAR!", type: "fact", emoji: "📚" },
        { text: "composed an ode:\n  FROM THE MOUNTAINTOP\n  I ROAR INTO THE VAST SKY\n  Sorry, was that loud?", type: "poem", emoji: "🏔️" },
        { text: "scared away 14 spam notifications. They won't be back. I made sure of it.", type: "compliment", emoji: "⚔️", happinessBoost: 8 },
    ],
};

interface DailyGiftModalProps {
    petName: string;
    species: PetSpecies;
    onCollect: (gift: Gift) => void;
}

export default function DailyGiftModal({ petName, species, onCollect }: DailyGiftModalProps) {
    const [gift, setGift] = useState<Gift | null>(null);
    const [visible, setVisible] = useState(false);
    const scaleAnim = useState(new Animated.Value(0.8))[0];

    useEffect(() => {
        (async () => {
            const lastGift = await AsyncStorage.getItem(DAILY_GIFT_KEY);
            const today = new Date().toDateString();
            if (lastGift !== today) {
                const speciesGifts = GIFTS[species];
                const dayIndex = new Date().getDay();
                const todaysGift = speciesGifts[dayIndex % speciesGifts.length];
                setGift(todaysGift);
                setVisible(true);
                // entrance animation
                Animated.spring(scaleAnim, { toValue: 1, useNativeDriver: true, speed: 12, bounciness: 8 }).start();
            }
        })();
    }, [species]);

    if (!gift || !visible) return null;

    const handleCollect = async () => {
        await AsyncStorage.setItem(DAILY_GIFT_KEY, new Date().toDateString());
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
        playSound("levelUp");
        onCollect(gift);
        // exit animation
        Animated.timing(scaleAnim, { toValue: 0, duration: 200, useNativeDriver: true }).start(() => {
            setVisible(false);
        });
    };

    return (
        <Modal visible={visible} transparent animationType="fade">
            <View style={styles.overlay}>
                <Animated.View style={[styles.card, { transform: [{ scale: scaleAnim }] }]}>
                    <Text style={styles.giftEmoji}>{gift.emoji}</Text>
                    <Text style={styles.giftLabel}>🎁 Daily Gift from {petName}</Text>
                    <Text style={styles.giftText}>
                        {petName} {gift.text}
                    </Text>
                    <View style={styles.giftMeta}>
                        {gift.item && <Text style={styles.metaTag}>📦 {gift.item.replace(/_/g, " ")}</Text>}
                        {gift.happinessBoost && <Text style={styles.metaTag}>💚 +{gift.happinessBoost}%</Text>}
                        {gift.type === "poem" && <Text style={styles.metaTag}>📝 poem</Text>}
                    </View>
                    <TouchableOpacity
                        style={styles.collectBtn}
                        onPress={handleCollect}
                        activeOpacity={0.7}
                    >
                        <Text style={styles.collectBtnText}>
                            {gift.item ? "📦 Collect" : gift.happinessBoost ? `💚 +${gift.happinessBoost}%` : "Thanks!"}
                        </Text>
                    </TouchableOpacity>
                </Animated.View>
            </View>
        </Modal>
    );
}

const styles = StyleSheet.create({
    overlay: { flex: 1, justifyContent: "center", alignItems: "center", backgroundColor: "rgba(0,0,0,0.7)", paddingHorizontal: spacing.xxl },
    card: { backgroundColor: colors.bgSecondary, borderRadius: borderRadius.xl, borderWidth: 1, borderColor: "rgba(255,215,0,0.3)", borderLeftWidth: 3, borderLeftColor: "#FFD700", padding: spacing.xxl, width: "100%", alignItems: "center" },
    giftEmoji: { fontSize: 48, marginBottom: spacing.md },
    giftLabel: { fontFamily: "Inter_500Medium", fontSize: fontSize.xs, color: "#FFD700", marginBottom: spacing.md },
    giftText: { fontFamily: "Inter_400Regular", fontSize: fontSize.sm, color: colors.textSecondary, lineHeight: 22, textAlign: "center", marginBottom: spacing.lg },
    giftMeta: { flexDirection: "row", gap: spacing.md, marginBottom: spacing.lg },
    metaTag: { fontFamily: "Inter_400Regular", fontSize: fontSize.tiny, color: colors.neon },
    collectBtn: { backgroundColor: colors.neon, borderRadius: borderRadius.md, paddingVertical: spacing.md, paddingHorizontal: spacing.xxxl, alignItems: "center", width: "100%" },
    collectBtnText: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.sm, color: colors.bgPrimary },
});
