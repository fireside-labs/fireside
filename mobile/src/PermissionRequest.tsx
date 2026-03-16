/**
 * 🐾 Permission Request — Sprint 12 Task 4.
 *
 * Contextual, non-greedy permission flow. Each permission is
 * requested the first time Ember needs it, not at app launch.
 * The companion asks nicely with brand personality.
 */
import { useState, useCallback } from "react";
import {
    View,
    Text,
    TouchableOpacity,
    StyleSheet,
    Modal,
} from "react-native";
import * as Haptics from "expo-haptics";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { colors, spacing, borderRadius, fontSize, shadows } from "./theme";

export type PermissionType = "calendar" | "contacts" | "health";

interface PermissionConfig {
    icon: string;
    emoji: string;
    title: string;
    message: string;
    storageKey: string;
}

const PERMISSIONS: Record<PermissionType, PermissionConfig> = {
    calendar: {
        icon: "📅",
        emoji: "🦊",
        title: "Calendar Access",
        message: "I'd love to read your calendar so I can remind you about upcoming meetings and help you prepare. Is that okay?",
        storageKey: "fireside_perm_calendar",
    },
    contacts: {
        icon: "👤",
        emoji: "🦊",
        title: "Contacts Access",
        message: "When you mention someone by name, I can look them up to help you connect. May I access your contacts?",
        storageKey: "fireside_perm_contacts",
    },
    health: {
        icon: "❤️",
        emoji: "🦊",
        title: "Health Access",
        message: "Want me to track your daily stats? I'll just read your step count and activity — I'll never write anything. Promise!",
        storageKey: "fireside_perm_health",
    },
};

interface PermissionRequestProps {
    type: PermissionType;
    visible: boolean;
    onAllow: () => void;
    onDeny: () => void;
}

/**
 * Modal that appears when Ember needs a native permission for the first time.
 * Shows the companion asking with personality — not a generic system dialog.
 */
export function PermissionRequest({ type, visible, onAllow, onDeny }: PermissionRequestProps) {
    const config = PERMISSIONS[type];

    return (
        <Modal visible={visible} transparent animationType="fade">
            <View style={styles.overlay}>
                <View style={styles.card}>
                    <Text style={styles.emoji}>{config.emoji}</Text>
                    <View style={styles.header}>
                        <Text style={styles.icon}>{config.icon}</Text>
                        <Text style={styles.title}>{config.title}</Text>
                    </View>
                    <View style={styles.bubble}>
                        <Text style={styles.message}>{config.message}</Text>
                    </View>
                    <View style={styles.actions}>
                        <TouchableOpacity
                            style={styles.allowBtn}
                            onPress={() => {
                                Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
                                onAllow();
                            }}
                            activeOpacity={0.8}
                        >
                            <Text style={styles.allowText}>Allow</Text>
                        </TouchableOpacity>
                        <TouchableOpacity
                            style={styles.denyBtn}
                            onPress={() => {
                                Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
                                onDeny();
                            }}
                            activeOpacity={0.7}
                        >
                            <Text style={styles.denyText}>Not Now</Text>
                        </TouchableOpacity>
                    </View>
                </View>
            </View>
        </Modal>
    );
}

/**
 * Hook to manage contextual permission requests.
 * Call `requestIfNeeded("calendar")` before accessing calendar APIs.
 * Returns whether the permission was granted, denied, or skipped.
 */
export function usePermission() {
    const [pending, setPending] = useState<PermissionType | null>(null);
    const [resolver, setResolver] = useState<{ resolve: (granted: boolean) => void } | null>(null);

    const requestIfNeeded = useCallback(async (type: PermissionType): Promise<boolean> => {
        const config = PERMISSIONS[type];
        const stored = await AsyncStorage.getItem(config.storageKey);
        if (stored === "granted") return true;
        if (stored === "denied") return false;

        // First time — show the companion asking
        return new Promise<boolean>((resolve) => {
            setResolver({ resolve });
            setPending(type);
        });
    }, []);

    const handleAllow = useCallback(async () => {
        if (pending) {
            await AsyncStorage.setItem(PERMISSIONS[pending].storageKey, "granted");
        }
        resolver?.resolve(true);
        setPending(null);
        setResolver(null);
    }, [pending, resolver]);

    const handleDeny = useCallback(async () => {
        if (pending) {
            await AsyncStorage.setItem(PERMISSIONS[pending].storageKey, "denied");
        }
        resolver?.resolve(false);
        setPending(null);
        setResolver(null);
    }, [pending, resolver]);

    return {
        requestIfNeeded,
        permissionModal: pending ? (
            <PermissionRequest
                type={pending}
                visible={true}
                onAllow={handleAllow}
                onDeny={handleDeny}
            />
        ) : null,
    };
}

const styles = StyleSheet.create({
    overlay: {
        flex: 1,
        backgroundColor: "rgba(0,0,0,0.7)",
        justifyContent: "center",
        alignItems: "center",
        padding: spacing.xl,
    },
    card: {
        backgroundColor: colors.bgCard,
        borderRadius: borderRadius.xl,
        borderWidth: 1,
        borderColor: colors.neonBorder,
        padding: spacing.xl,
        width: "100%",
        maxWidth: 340,
        alignItems: "center",
        ...shadows.glow,
    },
    emoji: { fontSize: 48, marginBottom: spacing.sm },
    header: { flexDirection: "row", alignItems: "center", gap: spacing.sm, marginBottom: spacing.md },
    icon: { fontSize: 20 },
    title: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.lg, color: colors.textPrimary },
    bubble: {
        backgroundColor: colors.bgInput,
        borderRadius: borderRadius.lg,
        borderTopLeftRadius: 4,
        padding: spacing.md,
        marginBottom: spacing.xl,
        width: "100%",
    },
    message: { fontFamily: "Inter_400Regular", fontSize: fontSize.sm, color: colors.textSecondary, lineHeight: 22 },
    actions: { flexDirection: "row", gap: spacing.md, width: "100%" },
    allowBtn: {
        flex: 1.2,
        backgroundColor: colors.neon,
        borderRadius: borderRadius.md,
        paddingVertical: spacing.md,
        alignItems: "center",
        ...shadows.glow,
    },
    allowText: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.md, color: colors.bgPrimary },
    denyBtn: {
        flex: 1,
        backgroundColor: colors.bgInput,
        borderRadius: borderRadius.md,
        paddingVertical: spacing.md,
        alignItems: "center",
    },
    denyText: { fontFamily: "Inter_400Regular", fontSize: fontSize.sm, color: colors.textMuted },
});
