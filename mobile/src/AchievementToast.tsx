/**
 * 🎉 Achievement Toast.
 *
 * Slides in from top when a new achievement is earned.
 * Celebratory animation + haptic + sound.
 * Auto-dismisses after 3 seconds.
 */
import { useEffect, useRef } from "react";
import { View, Text, StyleSheet, Animated } from "react-native";
import * as Haptics from "expo-haptics";
import { playSound } from "./sounds";
import { colors, spacing, borderRadius, fontSize, shadows } from "./theme";

interface AchievementToastProps {
    achievementName: string;
    achievementDesc: string;
    emoji: string;
    petName: string;
    onDismiss: () => void;
}

export default function AchievementToast({
    achievementName,
    achievementDesc,
    emoji,
    petName,
    onDismiss,
}: AchievementToastProps) {
    const slideAnim = useRef(new Animated.Value(-120)).current;
    const sparkleAnim = useRef(new Animated.Value(0)).current;

    useEffect(() => {
        // Haptic + sound
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
        try { playSound("levelUp"); } catch { }

        // Slide in
        Animated.spring(slideAnim, { toValue: 60, useNativeDriver: true, tension: 80, friction: 10 }).start();

        // Sparkle pulse
        Animated.loop(
            Animated.sequence([
                Animated.timing(sparkleAnim, { toValue: 1, duration: 400, useNativeDriver: true }),
                Animated.timing(sparkleAnim, { toValue: 0, duration: 400, useNativeDriver: true }),
            ])
        ).start();

        // Auto-dismiss
        const timer = setTimeout(() => {
            Animated.timing(slideAnim, { toValue: -120, duration: 300, useNativeDriver: true }).start(() => {
                onDismiss();
            });
        }, 3000);

        return () => clearTimeout(timer);
    }, [slideAnim, sparkleAnim, onDismiss]);

    return (
        <Animated.View style={[styles.container, { transform: [{ translateY: slideAnim }] }]}>
            {/* Sparkle background */}
            <Animated.Text style={[styles.sparkleLeft, { opacity: sparkleAnim }]}>✨</Animated.Text>
            <Animated.Text style={[styles.sparkleRight, { opacity: sparkleAnim }]}>✨</Animated.Text>

            <View style={styles.content}>
                <Text style={styles.emoji}>{emoji}</Text>
                <View style={styles.textWrap}>
                    <Text style={styles.title}>Achievement Unlocked!</Text>
                    <Text style={styles.name}>{achievementName}</Text>
                    <Text style={styles.desc}>{achievementDesc}</Text>
                </View>
            </View>
        </Animated.View>
    );
}

const styles = StyleSheet.create({
    container: {
        position: "absolute",
        top: 0,
        left: spacing.lg,
        right: spacing.lg,
        zIndex: 999,
        backgroundColor: colors.bgCard,
        borderRadius: borderRadius.lg,
        borderWidth: 2,
        borderColor: colors.neon,
        padding: spacing.md,
        ...shadows.glow,
    },
    content: { flexDirection: "row", alignItems: "center", gap: spacing.md },
    emoji: { fontSize: 36 },
    textWrap: { flex: 1 },
    title: { fontFamily: "Inter_700Bold", fontSize: fontSize.tiny, color: colors.neon, textTransform: "uppercase", letterSpacing: 1 },
    name: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.sm, color: colors.textPrimary, marginTop: 2 },
    desc: { fontFamily: "Inter_400Regular", fontSize: fontSize.tiny, color: colors.textDim, marginTop: 1 },
    sparkleLeft: { position: "absolute", top: -8, left: -4, fontSize: 20 },
    sparkleRight: { position: "absolute", top: -8, right: -4, fontSize: 20 },
});
