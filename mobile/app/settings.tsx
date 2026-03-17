/**
 * ⚙️ Settings Screen — Sprint 8 Task 1.
 * Sprint 10: Added AI Agent section.
 *
 * One scrollable screen: mode switch, connection, companion info,
 * AI agent, voice, notifications, privacy, about.
 *
 * Per CREATIVE_DIRECTION.md: clean, no nested menus.
 */
import { useState } from "react";
import {
    View,
    Text,
    TouchableOpacity,
    ScrollView,
    StyleSheet,
    Switch,
    Alert,
} from "react-native";
import { useRouter } from "expo-router";
import * as Haptics from "expo-haptics";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { useMode } from "../src/ModeContext";
import { useConnection } from "../src/hooks/useConnection";
import { useAgent } from "../src/AgentContext";
import { colors, spacing, borderRadius, fontSize, shadows } from "../src/theme";

export default function SettingsScreen() {
    const router = useRouter();
    const { mode, setMode, isPetMode } = useMode();
    const { isOnline, companionData } = useConnection();
    const { agent } = useAgent();

    const petName = companionData?.companion?.name || "Companion";
    const species = companionData?.companion?.species || "cat";
    const level = companionData?.companion?.level || 1;

    const [voiceEnabled, setVoiceEnabled] = useState(true);
    const [notifCare, setNotifCare] = useState(true);
    const [notifTasks, setNotifTasks] = useState(true);
    const [notifGuardian, setNotifGuardian] = useState(true);

    const handleModeSwitch = () => {
        const newMode = isPetMode ? "tool" : "pet";
        setMode(newMode);
        Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    };

    const handleRePair = () => {
        Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
        Alert.alert(
            "Re-pair Device",
            "This will disconnect from your current PC. You'll need to scan a QR code or enter an IP to reconnect.",
            [
                { text: "Cancel", style: "cancel" },
                {
                    text: "Re-pair",
                    style: "destructive",
                    onPress: async () => {
                        await AsyncStorage.removeItem("valhalla_host");
                        await AsyncStorage.removeItem("valhalla_tailscale_ip");
                        await AsyncStorage.removeItem("valhalla_conn_pref");
                        await AsyncStorage.removeItem("pairingToken");
                        await AsyncStorage.removeItem("connectionMode");
                        router.replace("/onboarding");
                    },
                },
            ]
        );
    };

    return (
        <ScrollView style={styles.container} contentContainerStyle={styles.content}>
            <Text style={styles.title}>⚙️ Settings</Text>

            {/* ———— Mode Switch ———— */}
            <View style={styles.section}>
                <Text style={styles.sectionTitle}>Experience</Text>
                <TouchableOpacity style={styles.modeCard} onPress={handleModeSwitch} activeOpacity={0.7}>
                    <View style={styles.modeRow}>
                        <Text style={styles.modeEmoji}>{isPetMode ? "🐾" : "💼"}</Text>
                        <View style={styles.modeInfo}>
                            <Text style={styles.modeName}>
                                {isPetMode ? "Companion Mode" : "Executive Mode"}
                            </Text>
                            <Text style={styles.modeDesc}>
                                {isPetMode ? "A friendly AI that grows with you" : "Your private AI assistant"}
                            </Text>
                        </View>
                        <Text style={styles.switchHint}>Switch →</Text>
                    </View>
                </TouchableOpacity>
            </View>

            {/* ———— Connection ———— */}
            <View style={styles.section}>
                <Text style={styles.sectionTitle}>Connection</Text>
                <View style={styles.card}>
                    <View style={styles.row}>
                        <View style={[styles.statusDot, isOnline ? styles.online : styles.offline]} />
                        <Text style={styles.rowLabel}>
                            {isOnline ? "Connected to your PC" : "Offline"}
                        </Text>
                    </View>
                    <TouchableOpacity style={styles.rePairBtn} onPress={handleRePair} activeOpacity={0.7}>
                        <Text style={styles.rePairText}>📱 Re-pair Device</Text>
                    </TouchableOpacity>
                </View>
            </View>

            {/* ———— Companion ———— */}
            <View style={styles.section}>
                <Text style={styles.sectionTitle}>Your Companion</Text>
                <View style={styles.card}>
                    <View style={styles.row}>
                        <Text style={styles.rowLabel}>Name</Text>
                        <Text style={styles.rowValue}>{petName}</Text>
                    </View>
                    <View style={styles.divider} />
                    <View style={styles.row}>
                        <Text style={styles.rowLabel}>Species</Text>
                        <Text style={styles.rowValue}>{species.charAt(0).toUpperCase() + species.slice(1)}</Text>
                    </View>
                    <View style={styles.divider} />
                    <View style={styles.row}>
                        <Text style={styles.rowLabel}>Level</Text>
                        <Text style={styles.rowValue}>{level}</Text>
                    </View>
                </View>
            </View>

            {/* ———— AI Agent (Sprint 10) ———— */}
            <View style={styles.section}>
                <Text style={styles.sectionTitle}>Your AI at Home</Text>
                <View style={styles.card}>
                    <View style={styles.row}>
                        <Text style={styles.rowLabel}>🏠 AI Name</Text>
                        <Text style={styles.rowValue}>{agent.name}</Text>
                    </View>
                    <View style={styles.divider} />
                    <View style={styles.row}>
                        <Text style={styles.rowLabel}>Style</Text>
                        <Text style={styles.rowValue}>{agent.style.charAt(0).toUpperCase() + agent.style.slice(1)}</Text>
                    </View>
                    <View style={styles.divider} />
                    <View style={styles.row}>
                        <Text style={styles.rowLabel}>Status</Text>
                        <Text style={[styles.rowValue, { color: isOnline ? colors.onlineDot : colors.offlineDot }]}>
                            {isOnline ? "🟢 Online" : "🔴 Offline"}
                        </Text>
                    </View>
                    {agent.uptime && (
                        <>
                            <View style={styles.divider} />
                            <View style={styles.row}>
                                <Text style={styles.rowLabel}>Uptime</Text>
                                <Text style={styles.rowValue}>{agent.uptime}</Text>
                            </View>
                        </>
                    )}
                </View>
            </View>

            {/* ———— Voice ———— */}
            <View style={styles.section}>
                <Text style={styles.sectionTitle}>Voice</Text>
                <View style={styles.card}>
                    <View style={styles.row}>
                        <Text style={styles.rowLabel}>🎤 Voice Mode</Text>
                        <Switch
                            value={voiceEnabled}
                            onValueChange={(v) => { setVoiceEnabled(v); Haptics.selectionAsync(); }}
                            trackColor={{ false: colors.glassBorder, true: colors.neonGlow }}
                            thumbColor={voiceEnabled ? colors.neon : colors.textMuted}
                        />
                    </View>
                </View>
            </View>

            {/* ———— Notifications ———— */}
            <View style={styles.section}>
                <Text style={styles.sectionTitle}>Notifications</Text>
                <View style={styles.card}>
                    <View style={styles.row}>
                        <Text style={styles.rowLabel}>🐾 Companion Care</Text>
                        <Switch
                            value={notifCare}
                            onValueChange={(v) => { setNotifCare(v); Haptics.selectionAsync(); }}
                            trackColor={{ false: colors.glassBorder, true: colors.neonGlow }}
                            thumbColor={notifCare ? colors.neon : colors.textMuted}
                        />
                    </View>
                    <View style={styles.divider} />
                    <View style={styles.row}>
                        <Text style={styles.rowLabel}>📋 Tasks</Text>
                        <Switch
                            value={notifTasks}
                            onValueChange={(v) => { setNotifTasks(v); Haptics.selectionAsync(); }}
                            trackColor={{ false: colors.glassBorder, true: colors.neonGlow }}
                            thumbColor={notifTasks ? colors.neon : colors.textMuted}
                        />
                    </View>
                    <View style={styles.divider} />
                    <View style={styles.row}>
                        <Text style={styles.rowLabel}>🛡️ Guardian Alerts</Text>
                        <Switch
                            value={notifGuardian}
                            onValueChange={(v) => { setNotifGuardian(v); Haptics.selectionAsync(); }}
                            trackColor={{ false: colors.glassBorder, true: colors.neonGlow }}
                            thumbColor={notifGuardian ? colors.neon : colors.textMuted}
                        />
                    </View>
                </View>
            </View>

            {/* ———— Privacy ———— */}
            <View style={styles.section}>
                <Text style={styles.sectionTitle}>Privacy</Text>
                <View style={[styles.card, styles.privacyCard]}>
                    <Text style={styles.privacyIcon}>🔒</Text>
                    <Text style={styles.privacyText}>
                        All your data stays on your home PC. Your conversations, memories, and files never touch our servers.
                    </Text>
                </View>
            </View>

            {/* ———— About ———— */}
            <View style={styles.section}>
                <Text style={styles.sectionTitle}>About</Text>
                <View style={styles.card}>
                    <View style={styles.row}>
                        <Text style={styles.rowLabel}>App</Text>
                        <Text style={styles.rowValue}>Fireside</Text>
                    </View>
                    <View style={styles.divider} />
                    <View style={styles.row}>
                        <Text style={styles.rowLabel}>Version</Text>
                        <Text style={styles.rowValue}>1.0.0</Text>
                    </View>
                    <View style={styles.divider} />
                    <View style={styles.row}>
                        <Text style={styles.rowLabel}>Build</Text>
                        <Text style={styles.rowValue}>Sprint 8</Text>
                    </View>
                    <View style={styles.divider} />
                    <Text style={styles.poweredBy}>Powered by Fireside 🔥</Text>
                </View>
            </View>
        </ScrollView>
    );
}

const styles = StyleSheet.create({
    container: { flex: 1, backgroundColor: colors.bgPrimary },
    content: { paddingHorizontal: spacing.lg, paddingTop: 60, paddingBottom: spacing.xxxl + 40 },
    title: { fontFamily: "Inter_700Bold", fontSize: fontSize.xxl, color: colors.textPrimary, marginBottom: spacing.xl },
    section: { marginBottom: spacing.xl },
    sectionTitle: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.xs, color: colors.textDim, textTransform: "uppercase", letterSpacing: 1, marginBottom: spacing.sm, paddingLeft: spacing.xs },
    card: { backgroundColor: colors.bgCard, borderRadius: borderRadius.lg, borderWidth: 1, borderColor: colors.glassBorder, padding: spacing.lg, ...shadows.card },
    row: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingVertical: spacing.sm },
    rowLabel: { fontFamily: "Inter_400Regular", fontSize: fontSize.md, color: colors.textSecondary },
    rowValue: { fontFamily: "Inter_500Medium", fontSize: fontSize.md, color: colors.textPrimary },
    divider: { height: 1, backgroundColor: colors.glassBorder, marginVertical: spacing.xs },
    // Mode
    modeCard: { backgroundColor: colors.neonGlow, borderRadius: borderRadius.lg, borderWidth: 1, borderColor: colors.neonBorder, padding: spacing.lg, ...shadows.glow },
    modeRow: { flexDirection: "row", alignItems: "center", gap: spacing.md },
    modeEmoji: { fontSize: 28 },
    modeInfo: { flex: 1 },
    modeName: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.md, color: colors.textPrimary },
    modeDesc: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.textDim, marginTop: 2 },
    switchHint: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.neon },
    // Connection
    statusDot: { width: 10, height: 10, borderRadius: 5, marginRight: spacing.sm },
    online: { backgroundColor: colors.onlineDot },
    offline: { backgroundColor: colors.offlineDot },
    rePairBtn: { backgroundColor: colors.bgInput, borderRadius: borderRadius.md, paddingVertical: spacing.sm, alignItems: "center", marginTop: spacing.md },
    rePairText: { fontFamily: "Inter_400Regular", fontSize: fontSize.sm, color: colors.textDim },
    // Privacy
    privacyCard: { alignItems: "center", borderColor: colors.neonBorder },
    privacyIcon: { fontSize: 32, marginBottom: spacing.sm },
    privacyText: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.textSecondary, textAlign: "center", lineHeight: 18 },
    // About
    poweredBy: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.textDim, textAlign: "center", paddingTop: spacing.md },
});
