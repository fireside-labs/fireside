/**
 * 🔥 CampfireScene — Animated particle campfire reflecting power state.
 *
 * VISUAL LAYERS (bottom to top):
 *   1. Radial glow backdrop — soft ambient light
 *   2. Inner glow ring — warm halo behind the fire
 *   3. Ember particles — 12 animated circles floating upward
 *   4. Fire core — layered gradient flames (3 layers)
 *   5. Companion avatar — the fox sitting at the fire
 *   6. Log base — campfire log silhouette
 *   7. Power badge — state indicator
 *   8. Speech bubble — companion's contextual line
 *
 * STATES:
 *   home        → Big bright fire, fast sparks, warm pulse
 *   connected   → Same intensity, cooler blue-tinted sparks
 *   offline     → Small dim candle, slow drift, muted glow
 *   reconnected → Burst flare, rapid sparks, then settle
 */
import { useEffect, useRef, useMemo } from "react";
import { View, Text, Animated, StyleSheet, Dimensions } from "react-native";
import { colors, spacing, borderRadius, fontSize } from "./theme";
import type { PowerState } from "./hooks/useConnection";

const { width: SCREEN_WIDTH } = Dimensions.get("window");
const SCENE_SIZE = Math.min(SCREEN_WIDTH - 64, 320);
const PARTICLE_COUNT = 14;

interface CampfireSceneProps {
    powerState: PowerState;
    companionEmoji?: string;
    companionName?: string;
}

// ─── Speech per state ───
const STATE_SPEECH: Record<PowerState, string[]> = {
    home: [
        "What are we building today?",
        "The fire is warm and bright. I'm ready.",
        "Full power! Let's go.",
    ],
    connected: [
        "Connected through the bridge. Still got it.",
        "I can feel home from here.",
        "Tailscale tunnel is holding steady.",
    ],
    offline: [
        "Running on pocket power... connect me home 🦊",
        "The fire is dim, but I'm still here.",
        "I'll keep watch until we're home again.",
    ],
    reconnected: [
        "I'm back at full power! What did I miss?",
        "The fire roars again! 🔥",
        "Reconnected! Let's catch up.",
    ],
};

const STATE_BADGE: Record<PowerState, { emoji: string; label: string; color: string }> = {
    home: { emoji: "🔥", label: "Home Fire", color: "#F5A623" },
    connected: { emoji: "⚡", label: "Bridge", color: "#3b82f6" },
    offline: { emoji: "🕯️", label: "Pocket Mode", color: "#8E8E93" },
    reconnected: { emoji: "✨", label: "Rekindled!", color: "#2ecc71" },
};

// ─── Color palettes per state ───
const STATE_COLORS: Record<PowerState, {
    glowOuter: string; glowInner: string;
    flameCore: string; flameMid: string; flameOuter: string;
    ember: string; emberDim: string;
}> = {
    home: {
        glowOuter: "rgba(245,166,35,0.06)", glowInner: "rgba(232,113,44,0.12)",
        flameCore: "#FFDD57", flameMid: "#F5A623", flameOuter: "#E8712C",
        ember: "#F5A623", emberDim: "rgba(245,166,35,0.4)",
    },
    connected: {
        glowOuter: "rgba(59,130,246,0.05)", glowInner: "rgba(232,113,44,0.08)",
        flameCore: "#FFD93D", flameMid: "#E8712C", flameOuter: "#3b82f6",
        ember: "#60a5fa", emberDim: "rgba(96,165,250,0.4)",
    },
    offline: {
        glowOuter: "rgba(142,142,147,0.03)", glowInner: "rgba(245,166,35,0.04)",
        flameCore: "#F5A623", flameMid: "rgba(232,113,44,0.5)", flameOuter: "rgba(142,142,147,0.3)",
        ember: "rgba(245,166,35,0.3)", emberDim: "rgba(142,142,147,0.15)",
    },
    reconnected: {
        glowOuter: "rgba(46,204,113,0.08)", glowInner: "rgba(245,166,35,0.15)",
        flameCore: "#FFFFFF", flameMid: "#FFD93D", flameOuter: "#2ecc71",
        ember: "#2ecc71", emberDim: "rgba(46,204,113,0.5)",
    },
};

// ─── Get a random speech ───
function getSpeech(state: PowerState): string {
    const lines = STATE_SPEECH[state];
    return lines[Math.floor(Math.random() * lines.length)];
}

// ─── Particle data ───
interface Particle {
    x: Animated.Value;
    y: Animated.Value;
    opacity: Animated.Value;
    scale: Animated.Value;
    startX: number;
    size: number;
}

export default function CampfireScene({ powerState, companionEmoji, companionName }: CampfireSceneProps) {
    // Main animation values
    const glowPulse = useRef(new Animated.Value(0.8)).current;
    const glowScale = useRef(new Animated.Value(1)).current;
    const flameScale = useRef(new Animated.Value(1)).current;
    const flameSway = useRef(new Animated.Value(0)).current;
    const burstScale = useRef(new Animated.Value(1)).current;
    const innerGlowOpacity = useRef(new Animated.Value(0.5)).current;

    // Particles
    const particles = useRef<Particle[]>(
        Array.from({ length: PARTICLE_COUNT }, (_, i) => ({
            x: new Animated.Value(0),
            y: new Animated.Value(0),
            opacity: new Animated.Value(0),
            scale: new Animated.Value(0.3),
            startX: (Math.random() - 0.5) * 80,
            size: 3 + Math.random() * 5,
        }))
    ).current;

    // Speech state — changes on power state change
    const speechRef = useRef(getSpeech(powerState));
    useEffect(() => {
        speechRef.current = getSpeech(powerState);
    }, [powerState]);

    // ─── Particle animation loop ───
    useEffect(() => {
        const isOffline = powerState === "offline";
        const speed = isOffline ? 1 : powerState === "reconnected" ? 0.5 : 0.7;

        particles.forEach((p, i) => {
            const delay = (i / PARTICLE_COUNT) * (isOffline ? 4000 : 2000);
            const duration = (isOffline ? 4000 : 2200) * speed + Math.random() * 800;

            const animateParticle = () => {
                // Reset
                p.x.setValue(p.startX + (Math.random() - 0.5) * 20);
                p.y.setValue(0);
                p.opacity.setValue(0);
                p.scale.setValue(isOffline ? 0.2 : 0.4 + Math.random() * 0.3);

                Animated.sequence([
                    Animated.delay(delay),
                    Animated.parallel([
                        // Float upward
                        Animated.timing(p.y, {
                            toValue: -(60 + Math.random() * 60),
                            duration,
                            useNativeDriver: true,
                        }),
                        // Drift sideways
                        Animated.timing(p.x, {
                            toValue: p.startX + (Math.random() - 0.5) * 50,
                            duration,
                            useNativeDriver: true,
                        }),
                        // Fade in then out
                        Animated.sequence([
                            Animated.timing(p.opacity, {
                                toValue: isOffline ? 0.3 : 0.8,
                                duration: duration * 0.2,
                                useNativeDriver: true,
                            }),
                            Animated.timing(p.opacity, {
                                toValue: 0,
                                duration: duration * 0.8,
                                useNativeDriver: true,
                            }),
                        ]),
                        // Shrink as they rise
                        Animated.timing(p.scale, {
                            toValue: 0,
                            duration,
                            useNativeDriver: true,
                        }),
                    ]),
                ]).start(() => animateParticle());
            };

            animateParticle();
        });

        return () => {
            particles.forEach((p) => {
                p.x.stopAnimation();
                p.y.stopAnimation();
                p.opacity.stopAnimation();
                p.scale.stopAnimation();
            });
        };
    }, [powerState, particles]);

    // ─── Main scene animations ───
    useEffect(() => {
        glowPulse.stopAnimation();
        glowScale.stopAnimation();
        flameScale.stopAnimation();
        flameSway.stopAnimation();
        burstScale.stopAnimation();
        innerGlowOpacity.stopAnimation();

        switch (powerState) {
            case "home": {
                // Full warm pulsing fire
                Animated.loop(Animated.sequence([
                    Animated.timing(glowPulse, { toValue: 1, duration: 1800, useNativeDriver: true }),
                    Animated.timing(glowPulse, { toValue: 0.65, duration: 1800, useNativeDriver: true }),
                ])).start();
                Animated.loop(Animated.sequence([
                    Animated.timing(flameScale, { toValue: 1.06, duration: 600, useNativeDriver: true }),
                    Animated.timing(flameScale, { toValue: 0.97, duration: 700, useNativeDriver: true }),
                ])).start();
                Animated.loop(Animated.sequence([
                    Animated.timing(flameSway, { toValue: 3, duration: 1200, useNativeDriver: true }),
                    Animated.timing(flameSway, { toValue: -3, duration: 1200, useNativeDriver: true }),
                ])).start();
                Animated.loop(Animated.sequence([
                    Animated.timing(innerGlowOpacity, { toValue: 0.8, duration: 1500, useNativeDriver: true }),
                    Animated.timing(innerGlowOpacity, { toValue: 0.4, duration: 1500, useNativeDriver: true }),
                ])).start();
                glowScale.setValue(1);
                burstScale.setValue(1);
                break;
            }
            case "connected": {
                Animated.loop(Animated.sequence([
                    Animated.timing(glowPulse, { toValue: 0.85, duration: 2000, useNativeDriver: true }),
                    Animated.timing(glowPulse, { toValue: 0.55, duration: 2000, useNativeDriver: true }),
                ])).start();
                Animated.loop(Animated.sequence([
                    Animated.timing(flameScale, { toValue: 1.04, duration: 700, useNativeDriver: true }),
                    Animated.timing(flameScale, { toValue: 0.98, duration: 800, useNativeDriver: true }),
                ])).start();
                Animated.loop(Animated.sequence([
                    Animated.timing(flameSway, { toValue: 2, duration: 1400, useNativeDriver: true }),
                    Animated.timing(flameSway, { toValue: -2, duration: 1400, useNativeDriver: true }),
                ])).start();
                innerGlowOpacity.setValue(0.5);
                glowScale.setValue(1);
                burstScale.setValue(1);
                break;
            }
            case "offline": {
                // Dim candle — slow, muted
                Animated.timing(glowPulse, { toValue: 0.2, duration: 1200, useNativeDriver: true }).start();
                Animated.timing(flameScale, { toValue: 0.6, duration: 1200, useNativeDriver: true }).start();
                Animated.timing(innerGlowOpacity, { toValue: 0.15, duration: 1000, useNativeDriver: true }).start();
                Animated.loop(Animated.sequence([
                    Animated.timing(glowScale, { toValue: 1.015, duration: 3000, useNativeDriver: true }),
                    Animated.timing(glowScale, { toValue: 0.985, duration: 3000, useNativeDriver: true }),
                ])).start();
                Animated.loop(Animated.sequence([
                    Animated.timing(flameSway, { toValue: 1, duration: 2500, useNativeDriver: true }),
                    Animated.timing(flameSway, { toValue: -1, duration: 2500, useNativeDriver: true }),
                ])).start();
                burstScale.setValue(1);
                break;
            }
            case "reconnected": {
                // Burst flare!
                burstScale.setValue(0.4);
                Animated.sequence([
                    Animated.parallel([
                        Animated.spring(burstScale, { toValue: 1.35, useNativeDriver: true, speed: 18, bounciness: 8 }),
                        Animated.timing(glowPulse, { toValue: 1, duration: 250, useNativeDriver: true }),
                        Animated.timing(innerGlowOpacity, { toValue: 1, duration: 200, useNativeDriver: true }),
                    ]),
                    Animated.parallel([
                        Animated.timing(burstScale, { toValue: 1, duration: 1000, useNativeDriver: true }),
                        Animated.timing(innerGlowOpacity, { toValue: 0.6, duration: 1000, useNativeDriver: true }),
                    ]),
                ]).start();
                flameScale.setValue(1.1);
                glowScale.setValue(1);
                break;
            }
        }
    }, [powerState, glowPulse, glowScale, flameScale, flameSway, burstScale, innerGlowOpacity]);

    const palette = STATE_COLORS[powerState];
    const badge = STATE_BADGE[powerState];
    const speech = speechRef.current;
    const isOnline = powerState !== "offline";

    return (
        <View style={styles.container}>
            {/* ═══ Layer 1: Outer radial glow ═══ */}
            <Animated.View
                style={[
                    styles.glowOuter,
                    {
                        opacity: glowPulse,
                        transform: [{ scale: glowScale }],
                        backgroundColor: palette.glowOuter,
                    },
                ]}
            />

            {/* ═══ Layer 2: Inner glow ring ═══ */}
            <Animated.View
                style={[
                    styles.glowInner,
                    {
                        opacity: innerGlowOpacity,
                        backgroundColor: palette.glowInner,
                    },
                ]}
            />

            {/* ═══ Layer 3: Ember particles ═══ */}
            <View style={styles.particleField}>
                {particles.map((p, i) => (
                    <Animated.View
                        key={i}
                        style={[
                            styles.particle,
                            {
                                width: p.size,
                                height: p.size,
                                borderRadius: p.size / 2,
                                backgroundColor: i % 3 === 0 ? palette.ember : palette.emberDim,
                                opacity: p.opacity,
                                transform: [
                                    { translateX: p.x },
                                    { translateY: p.y },
                                    { scale: p.scale },
                                ],
                            },
                        ]}
                    />
                ))}
            </View>

            {/* ═══ Layer 4: Flame core (3 layers) ═══ */}
            <Animated.View
                style={[
                    styles.flameGroup,
                    {
                        transform: [
                            { scale: Animated.multiply(flameScale, burstScale) },
                            { translateX: flameSway },
                        ],
                    },
                ]}
            >
                {/* Outer flame */}
                <View style={[styles.flame, styles.flameOuter, { backgroundColor: palette.flameOuter }]} />
                {/* Mid flame */}
                <View style={[styles.flame, styles.flameMid, { backgroundColor: palette.flameMid }]} />
                {/* Core flame */}
                <View style={[styles.flame, styles.flameCore, { backgroundColor: palette.flameCore }]} />
            </Animated.View>

            {/* ═══ Layer 5: Companion avatar ═══ */}
            <Text style={[styles.companionEmoji, !isOnline && styles.companionDim]}>
                {companionEmoji || "🦊"}
            </Text>

            {/* ═══ Layer 6: Log base ═══ */}
            <View style={styles.logBase}>
                <View style={[styles.log, styles.logLeft]} />
                <View style={[styles.log, styles.logRight]} />
            </View>

            {/* ═══ Layer 7: Power badge ═══ */}
            <View style={[styles.badge, { borderColor: badge.color, shadowColor: badge.color }]}>
                <Text style={styles.badgeEmoji}>{badge.emoji}</Text>
                <Text style={[styles.badgeLabel, { color: badge.color }]}>{badge.label}</Text>
            </View>

            {/* ═══ Layer 8: Speech bubble ═══ */}
            <View style={[styles.speechBubble, !isOnline && styles.speechBubbleDim]}>
                <View style={styles.speechTail} />
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
        paddingVertical: spacing.xl,
        height: SCENE_SIZE,
        justifyContent: "center",
        position: "relative",
    },
    // Glow layers
    glowOuter: {
        position: "absolute",
        width: SCENE_SIZE * 1.4,
        height: SCENE_SIZE * 1.2,
        borderRadius: SCENE_SIZE * 0.7,
        top: -SCENE_SIZE * 0.1,
    },
    glowInner: {
        position: "absolute",
        width: SCENE_SIZE * 0.7,
        height: SCENE_SIZE * 0.6,
        borderRadius: SCENE_SIZE * 0.35,
        top: SCENE_SIZE * 0.15,
    },
    // Particle field
    particleField: {
        position: "absolute",
        width: 120,
        height: 120,
        top: SCENE_SIZE * 0.15,
        alignItems: "center",
        justifyContent: "flex-end",
    },
    particle: {
        position: "absolute",
        bottom: 20,
    },
    // Flame layers
    flameGroup: {
        alignItems: "center",
        justifyContent: "flex-end",
        width: 60,
        height: 80,
        marginBottom: -8,
    },
    flame: {
        position: "absolute",
        bottom: 0,
    },
    flameOuter: {
        width: 44,
        height: 64,
        borderRadius: 22,
        borderTopLeftRadius: 18,
        borderTopRightRadius: 18,
        opacity: 0.5,
    },
    flameMid: {
        width: 32,
        height: 52,
        borderRadius: 16,
        borderTopLeftRadius: 14,
        borderTopRightRadius: 14,
        opacity: 0.7,
    },
    flameCore: {
        width: 18,
        height: 36,
        borderRadius: 9,
        borderTopLeftRadius: 8,
        borderTopRightRadius: 8,
        opacity: 0.9,
    },
    // Companion
    companionEmoji: {
        fontSize: 44,
        marginTop: -4,
    },
    companionDim: {
        opacity: 0.5,
    },
    // Log base
    logBase: {
        flexDirection: "row",
        alignItems: "center",
        gap: 2,
        marginTop: -6,
        marginBottom: spacing.sm,
    },
    log: {
        height: 6,
        borderRadius: 3,
        backgroundColor: "rgba(139,90,43,0.4)",
    },
    logLeft: {
        width: 36,
        transform: [{ rotate: "-12deg" }],
    },
    logRight: {
        width: 36,
        transform: [{ rotate: "12deg" }],
    },
    // Badge
    badge: {
        flexDirection: "row",
        alignItems: "center",
        gap: 5,
        paddingHorizontal: spacing.md,
        paddingVertical: spacing.xs + 1,
        borderRadius: borderRadius.full,
        borderWidth: 1,
        backgroundColor: "rgba(0,0,0,0.5)",
        marginBottom: spacing.sm,
        shadowOffset: { width: 0, height: 0 },
        shadowOpacity: 0.3,
        shadowRadius: 6,
        elevation: 4,
    },
    badgeEmoji: {
        fontSize: 11,
    },
    badgeLabel: {
        fontFamily: "Inter_600SemiBold",
        fontSize: fontSize.tiny,
        textTransform: "uppercase",
        letterSpacing: 1.2,
    },
    // Speech
    speechBubble: {
        backgroundColor: "rgba(255,255,255,0.04)",
        borderRadius: borderRadius.lg,
        borderWidth: 1,
        borderColor: "rgba(245,166,35,0.12)",
        paddingHorizontal: spacing.xl,
        paddingVertical: spacing.md,
        maxWidth: 280,
        position: "relative",
    },
    speechBubbleDim: {
        borderColor: "rgba(142,142,147,0.08)",
        backgroundColor: "rgba(255,255,255,0.02)",
    },
    speechTail: {
        position: "absolute",
        top: -6,
        alignSelf: "center",
        left: "50%",
        marginLeft: -6,
        width: 12,
        height: 12,
        backgroundColor: "rgba(255,255,255,0.04)",
        borderWidth: 1,
        borderColor: "rgba(245,166,35,0.12)",
        borderBottomWidth: 0,
        borderRightWidth: 0,
        transform: [{ rotate: "45deg" }],
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
