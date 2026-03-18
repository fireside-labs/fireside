/**
 * 🛡️ Proactive Guardian bar.
 *
 * On chat tab open, checks time. If late night (midnight-6AM):
 * Shows a gentle bar: "It's late. Want me to hold messages until morning?"
 * Two options: "Hold Messages" / "I'm Fine"
 */
import { useState, useEffect } from "react";
import {
    View,
    Text,
    TouchableOpacity,
    StyleSheet,
    Animated,
} from "react-native";
import * as Haptics from "expo-haptics";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { companionAPI } from "./api";
import { colors, spacing, borderRadius, fontSize } from "./theme";

const GUARDIAN_CHECKIN_KEY = "fireside_guardian_checkin";

interface ProactiveGuardianProps {
    isOnline: boolean;
    onHoldMessages: () => void;
}

export default function ProactiveGuardian({ isOnline, onHoldMessages }: ProactiveGuardianProps) {
    const [visible, setVisible] = useState(false);
    const [holding, setHolding] = useState(false);
    const slideAnim = useState(new Animated.Value(-60))[0];

    useEffect(() => {
        (async () => {
            const hour = new Date().getHours();
            const isLateNight = hour >= 0 && hour < 6;
            if (!isLateNight) return;

            // Check if already dismissed today
            const last = await AsyncStorage.getItem(GUARDIAN_CHECKIN_KEY);
            const today = new Date().toDateString();
            if (last === today) return;

            // Try API check-in if online
            if (isOnline) {
                try {
                    const res = await companionAPI.guardianCheckIn();
                    if (!res.proactive_warning) return;
                } catch {
                    // API failed — still show if it's late
                }
            }

            setVisible(true);
            Animated.spring(slideAnim, { toValue: 0, useNativeDriver: true, speed: 12 }).start();
        })();
    }, [isOnline]);

    if (!visible) return null;

    const handleHold = async () => {
        Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
        await AsyncStorage.setItem(GUARDIAN_CHECKIN_KEY, new Date().toDateString());
        setHolding(true);
        onHoldMessages();
    };

    const handleDismiss = async () => {
        Haptics.selectionAsync();
        await AsyncStorage.setItem(GUARDIAN_CHECKIN_KEY, new Date().toDateString());
        Animated.timing(slideAnim, { toValue: -80, duration: 200, useNativeDriver: true }).start(() => {
            setVisible(false);
        });
    };

    if (holding) {
        const now = new Date();
        const sevenAm = new Date(now);
        sevenAm.setHours(7, 0, 0, 0);
        if (sevenAm <= now) sevenAm.setDate(sevenAm.getDate() + 1);
        const hoursUntil = ((sevenAm.getTime() - now.getTime()) / 3600000).toFixed(1);

        return (
            <Animated.View style={[styles.holdingBar, { transform: [{ translateY: slideAnim }] }]}>
                <Text style={styles.holdingText}>
                    🌙 Messages held until 7AM ({hoursUntil}h)
                </Text>
                <TouchableOpacity onPress={handleDismiss} activeOpacity={0.7}>
                    <Text style={styles.cancelText}>Cancel</Text>
                </TouchableOpacity>
            </Animated.View>
        );
    }

    return (
        <Animated.View style={[styles.bar, { transform: [{ translateY: slideAnim }] }]}>
            <Text style={styles.barText}>🌙 It's late. Want me to hold messages until morning?</Text>
            <View style={styles.actions}>
                <TouchableOpacity style={styles.holdBtn} onPress={handleHold} activeOpacity={0.7}>
                    <Text style={styles.holdBtnText}>Hold Messages</Text>
                </TouchableOpacity>
                <TouchableOpacity style={styles.fineBtn} onPress={handleDismiss} activeOpacity={0.7}>
                    <Text style={styles.fineBtnText}>I'm Fine</Text>
                </TouchableOpacity>
            </View>
        </Animated.View>
    );
}

const styles = StyleSheet.create({
    bar: { backgroundColor: "rgba(147,112,219,0.12)", borderWidth: 1, borderColor: "rgba(147,112,219,0.25)", borderRadius: borderRadius.md, padding: spacing.md, marginBottom: spacing.md },
    barText: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.textSecondary, marginBottom: spacing.sm, lineHeight: 18 },
    actions: { flexDirection: "row", gap: spacing.sm },
    holdBtn: { flex: 1, backgroundColor: "rgba(147,112,219,0.2)", borderRadius: borderRadius.sm, paddingVertical: spacing.sm, alignItems: "center" },
    holdBtnText: { fontFamily: "Inter_500Medium", fontSize: fontSize.xs, color: "#9370DB" },
    fineBtn: { flex: 1, backgroundColor: colors.bgCard, borderRadius: borderRadius.sm, paddingVertical: spacing.sm, alignItems: "center" },
    fineBtnText: { fontFamily: "Inter_500Medium", fontSize: fontSize.xs, color: colors.textDim },
    holdingBar: { backgroundColor: "rgba(147,112,219,0.08)", borderWidth: 1, borderColor: "rgba(147,112,219,0.15)", borderRadius: borderRadius.md, padding: spacing.md, marginBottom: spacing.md, flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
    holdingText: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: "#9370DB" },
    cancelText: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.textMuted, textDecorationLine: "underline" },
});
