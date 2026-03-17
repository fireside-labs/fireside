/**
 * 🔥 CampfireScene — Animated campfire that reflects power state.
 *
 * States:
 *   home        — Bright fire, sparks flying, full warm glow
 *   connected   — Bright fire + "remote" badge (via Tailscale)
 *   offline     — Dim candle, soft glow, fewer embers
 *   reconnected — Flare burst, sparks explode, then settles
 *
 * The companion never "dies" — it always works, just at reduced capacity.
 */
import { useEffect, useRef } from "react";
import { View, Text, Animated, StyleSheet } from "react-native";
import { colors, spacing, borderRadius, fontSize } from "./theme";
import type { PowerState } from "./hooks/useConnection";

interface CampfireSceneProps {
    powerState: PowerState;
    companionEmoji?: string;
    companionName?: string;
}

// Speech per power state
const STATE_SPEECH: Record<PowerState, string> = {
    home: "What are we building today?",
    connected: "I'm still connected to home!",
    offline: "I'm running on pocket power... connect me home 🦊",
    reconnected: "I'm back at full power! What did I miss?",
};

const STATE_BADGE: Record<PowerState, { emoji: string; label: string; color: string }> = {
    home: { emoji: "🔥", label: "Home", color: "#F5A623" },
    connected: { emoji: "⚡", label: "Bridge", color: "#3b82f6" },
    offline: { emoji: "🕯️", label: "Pocket", color: "#8E8E93" },
    reconnected: { emoji: "🔥", label: "Back!", color: "#2ecc71" },
};

export default function CampfireScene({ powerState, companionEmoji, companionName }: CampfireSceneProps) {
    // Animation values
    const glowOpacity = useRef(new Animated.Value(0.8)).current;
    const glowScale = useRef(new Animated.Value(1)).current;
    const fireScale = useRef(new Animated.Value(1)).current;
    const sparkOpacity = useRef(new Animated.Value(1)).current;
    const burstScale = useRef(new Animated.Value(1)).current;

    useEffect(() => {
        // Stop all previous animations
        glowOpacity.stopAnimation();
        glowScale.stopAnimation();
        fireScale.stopAnimation();
        sparkOpacity.stopAnimation();
        burstScale.stopAnimation();

        switch (powerState) {
            case "home": {
                // Bright warm pulsing glow
                Animated.loop(
                    Animated.sequence([
                        Animated.timing(glowOpacity, { toValue: 1, duration: 1500, useNativeDriver: true }),
                        Animated.timing(glowOpacity, { toValue: 0.7, duration: 1500, useNativeDriver: true }),
                    ])
                ).start();
                Animated.loop(
                    Animated.sequence([
                        Animated.timing(fireScale, { toValue: 1.08, duration: 800, useNativeDriver: true }),
                        Animated.timing(fireScale, { toValue: 0.95, duration: 800, useNativeDriver: true }),
                    ])
                ).start();
                glowScale.setValue(1);
                sparkOpacity.setValue(1);
                break;
            }
            case "connected": {
                // Same as home but with slight blue tinge
                Animated.loop(
                    Animated.sequence([
                        Animated.timing(glowOpacity, { toValue: 0.9, duration: 1800, useNativeDriver: true }),
                        Animated.timing(glowOpacity, { toValue: 0.6, duration: 1800, useNativeDriver: true }),
                    ])
                ).start();
                Animated.loop(
                    Animated.sequence([
                        Animated.timing(fireScale, { toValue: 1.05, duration: 900, useNativeDriver: true }),
                        Animated.timing(fireScale, { toValue: 0.97, duration: 900, useNativeDriver: true }),
                    ])
                ).start();
                glowScale.setValue(1);
                sparkOpacity.setValue(0.8);
                break;
            }
            case "offline": {
                // Dim, slow, candle-like
                Animated.timing(glowOpacity, { toValue: 0.25, duration: 1000, useNativeDriver: true }).start();
                Animated.timing(fireScale, { toValue: 0.7, duration: 1000, useNativeDriver: true }).start();
                Animated.timing(sparkOpacity, { toValue: 0.15, duration: 800, useNativeDriver: true }).start();
                Animated.loop(
                    Animated.sequence([
                        Animated.timing(glowScale, { toValue: 1.02, duration: 2500, useNativeDriver: true }),
                        Animated.timing(glowScale, { toValue: 0.98, duration: 2500, useNativeDriver: true }),
                    ])
                ).start();
                break;
            }
            case "reconnected": {
                // Burst! Then settle
                burstScale.setValue(0.5);
                Animated.sequence([
                    Animated.parallel([
                        Animated.spring(burstScale, { toValue: 1.3, useNativeDriver: true, speed: 20 }),
                        Animated.timing(glowOpacity, { toValue: 1, duration: 300, useNativeDriver: true }),
                        Animated.timing(sparkOpacity, { toValue: 1, duration: 200, useNativeDriver: true }),
                    ]),
                    Animated.timing(burstScale, { toValue: 1, duration: 800, useNativeDriver: true }),
                ]).start();
                fireScale.setValue(1.1);
                glowScale.setValue(1);
                break;
            }
        }
    }, [powerState, glowOpacity, glowScale, fireScale, sparkOpacity, burstScale]);

    const badge = STATE_BADGE[powerState];
    const speech = STATE_SPEECH[powerState];
    const isOnline = powerState !== "offline";

    return (
        <View style={styles.container}>
            {/* Glow backdrop */}
            <Animated.View
                style={[
                    styles.glowBackdrop,
                    {
                        opacity: glowOpacity,
                        transform: [{ scale: glowScale }],
                        backgroundColor: powerState === "connected"
                            ? "rgba(59, 130, 246, 0.06)"
                            : powerState === "offline"
                                ? "rgba(142, 142, 147, 0.04)"
                                : "rgba(245, 166, 35, 0.08)",
                    },
                ]}
            />

            {/* Fire + sparks */}
            <Animated.View style={[styles.fireContainer, { transform: [{ scale: Animated.multiply(fireScale, burstScale) }] }]}>
                {/* Spark particles */}
                <Animated.View style={[styles.sparks, { opacity: sparkOpacity }]}>
                    <Text style={styles.sparkText}>
                        {powerState === "offline" ? "·  ·" : "✦ ✧ ✦"}
                    </Text>
                </Animated.View>

                {/* Fire emoji cluster */}
                <Text style={styles.fireEmoji}>
                    {powerState === "offline" ? "🕯️" : "🔥"}
                </Text>

                {/* Companion avatar */}
                <Text style={styles.companionEmoji}>
                    {companionEmoji || "🦊"}
                </Text>
            </Animated.View>

            {/* Power state badge */}
            <View style={[styles.badge, { borderColor: badge.color }]}>
                <Text style={styles.badgeEmoji}>{badge.emoji}</Text>
                <Text style={[styles.badgeLabel, { color: badge.color }]}>{badge.label}</Text>
            </View>

            {/* Speech bubble */}
            <View style={[styles.speechBubble, !isOnline && styles.speechBubbleDim]}>
                <Text style={[styles.speechText, !isOnline && styles.speechTextDim]}>
                    "{speech}"
                </Text>
                {companionName && (
                    <Text style={styles.speechName}>— {companionName}</Text>
                )}
            </View>
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        alignItems: "center",
        paddingVertical: spacing.lg,
        position: "relative",
    },
    glowBackdrop: {
        position: "absolute",
        top: -20,
        left: -40,
        right: -40,
        bottom: -20,
        borderRadius: 200,
    },
    fireContainer: {
        alignItems: "center",
        marginBottom: spacing.md,
    },
    sparks: {
        marginBottom: -8,
    },
    sparkText: {
        fontSize: 12,
        color: "#F5A623",
        letterSpacing: 8,
    },
    fireEmoji: {
        fontSize: 56,
    },
    companionEmoji: {
        fontSize: 48,
        marginTop: -12,
    },
    badge: {
        flexDirection: "row",
        alignItems: "center",
        gap: 4,
        paddingHorizontal: spacing.md,
        paddingVertical: spacing.xs,
        borderRadius: borderRadius.full,
        borderWidth: 1,
        backgroundColor: "rgba(0,0,0,0.3)",
        marginBottom: spacing.md,
    },
    badgeEmoji: {
        fontSize: 12,
    },
    badgeLabel: {
        fontFamily: "Inter_600SemiBold",
        fontSize: fontSize.tiny,
        textTransform: "uppercase",
        letterSpacing: 1,
    },
    speechBubble: {
        backgroundColor: "rgba(255,255,255,0.04)",
        borderRadius: borderRadius.lg,
        borderWidth: 1,
        borderColor: "rgba(245,166,35,0.15)",
        paddingHorizontal: spacing.xl,
        paddingVertical: spacing.md,
        maxWidth: 280,
    },
    speechBubbleDim: {
        borderColor: "rgba(142,142,147,0.1)",
        backgroundColor: "rgba(255,255,255,0.02)",
    },
    speechText: {
        fontFamily: "Inter_400Regular",
        fontSize: fontSize.sm,
        color: colors.textSecondary,
        textAlign: "center",
        fontStyle: "italic",
        lineHeight: 20,
    },
    speechTextDim: {
        color: colors.textMuted,
    },
    speechName: {
        fontFamily: "Inter_500Medium",
        fontSize: fontSize.tiny,
        color: colors.textDim,
        textAlign: "right",
        marginTop: spacing.xs,
    },
});
