/**
 * ⚙️ Settings Tab — Connection, mode, and account management.
 *
 * Features:
 *   - Connection status + diagnostics
 *   - Switch Companion/Executive mode
 *   - Re-pair to different PC
 *   - Connection preference (Local Only vs Anywhere Bridge)
 *   - About + version info
 */
import { useState, useEffect, useCallback } from "react";
import {
    View,
    Text,
    TouchableOpacity,
    ScrollView,
    StyleSheet,
    Alert,
    Switch,
    TextInput,
} from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import * as Haptics from "expo-haptics";
import { useRouter } from "expo-router";
import { useConnection } from "../../src/hooks/useConnection";
import { useMode } from "../../src/ModeContext";
import {
    getHost,
    setHost,
    getTailscaleIP,
    setTailscaleIP,
    getConnectionPref,
    setConnectionPref,
    testConnection,
    companionAPI,
} from "../../src/api";
import { getSocket } from "../../src/FiresideSocket";
import { colors, spacing, borderRadius, fontSize, shadows } from "../../src/theme";

export default function SettingsTab() {
    const router = useRouter();
    const { isOnline, connectionPhase, companionData, lastSeen, awayDuration } = useConnection();
    const { isPetMode, toggleMode } = useMode();

    const [currentHost, setCurrentHost] = useState<string | null>(null);
    const [tailscaleIP, setTailscaleIPState] = useState<string | null>(null);
    const [connPref, setConnPref] = useState<"local" | "bridge">("local");
    const [newHost, setNewHost] = useState("");
    const [reconnecting, setReconnecting] = useState(false);
    const [showReconnect, setShowReconnect] = useState(false);

    // Load current settings
    useEffect(() => {
        (async () => {
            const host = await getHost();
            const ts = await getTailscaleIP();
            const pref = await getConnectionPref();
            setCurrentHost(host);
            setTailscaleIPState(ts);
            setConnPref((pref as "local" | "bridge") || "local");
        })();
    }, []);

    const handleReconnect = useCallback(async () => {
        const ip = newHost.trim();
        if (!ip) return;
        setReconnecting(true);
        Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);

        await setHost(ip);
        const ok = await testConnection();
        if (ok) {
            setCurrentHost(ip);
            setShowReconnect(false);
            setNewHost("");

            // Re-sync to get device token
            try { await companionAPI.sync(); } catch { }

            // Reconnect WebSocket
            const socket = getSocket();
            socket.disconnect();
            socket.connect();

            Alert.alert("Connected!", `Now connected to ${ip}`);
        } else {
            Alert.alert("Connection Failed", "Check the IP and make sure Fireside is running.");
        }
        setReconnecting(false);
    }, [newHost]);

    const handleModeSwitch = useCallback(async () => {
        Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
        toggleMode();
    }, [toggleMode]);

    const handleConnPrefChange = useCallback(async (pref: "local" | "bridge") => {
        Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
        await setConnectionPref(pref);
        setConnPref(pref);

        // Reconnect WebSocket with new routing
        const socket = getSocket();
        socket.disconnect();
        socket.connect();
    }, []);

    const handleForgetAll = useCallback(async () => {
        Alert.alert(
            "Reset Everything?",
            "This will disconnect from your PC, clear all local data, and restart onboarding. Your companion data on the PC is NOT affected.",
            [
                { text: "Cancel", style: "cancel" },
                {
                    text: "Reset",
                    style: "destructive",
                    onPress: async () => {
                        Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Heavy);
                        getSocket().destroy();
                        await AsyncStorage.clear();
                        router.replace("/onboarding");
                    },
                },
            ]
        );
    }, [router]);

    // Connection phase display
    const phaseConfig: Record<string, { color: string; label: string; emoji: string }> = {
        connected:    { color: colors.onlineDot, label: "Connected",          emoji: "🟢" },
        reconnecting: { color: "#F59E0B",        label: "Reconnecting...",    emoji: "🟡" },
        connecting:   { color: "#60A5FA",        label: "Connecting...",      emoji: "🔵" },
        discovering:  { color: "#60A5FA",        label: "Discovering...",     emoji: "🔍" },
        offline:      { color: colors.offlineDot, label: "Offline",           emoji: "⚫" },
        idle:         { color: colors.offlineDot, label: "Not connected",     emoji: "⚫" },
    };
    const phase = phaseConfig[connectionPhase] || phaseConfig.idle;

    return (
        <ScrollView style={styles.screen} contentContainerStyle={styles.content}>
            <Text style={styles.title}>Settings</Text>

            {/* ── Connection Status ── */}
            <View style={styles.section}>
                <Text style={styles.sectionTitle}>Connection</Text>

                <View style={styles.card}>
                    <View style={styles.statusRow}>
                        <Text style={styles.statusEmoji}>{phase.emoji}</Text>
                        <View style={{ flex: 1 }}>
                            <Text style={styles.statusLabel}>{phase.label}</Text>
                            {currentHost && (
                                <Text style={styles.statusDetail}>
                                    {currentHost}
                                </Text>
                            )}
                            {lastSeen && connectionPhase === "connected" && (
                                <Text style={styles.statusDetail}>
                                    Last sync: just now
                                </Text>
                            )}
                            {awayDuration && connectionPhase !== "connected" && (
                                <Text style={styles.statusDetail}>
                                    Away for {awayDuration}
                                </Text>
                            )}
                        </View>
                    </View>

                    {/* Reconnect controls */}
                    {!showReconnect ? (
                        <TouchableOpacity
                            style={styles.secondaryBtn}
                            onPress={() => setShowReconnect(true)}
                            activeOpacity={0.7}
                        >
                            <Text style={styles.secondaryBtnText}>
                                Change PC Connection
                            </Text>
                        </TouchableOpacity>
                    ) : (
                        <View style={styles.reconnectBox}>
                            <TextInput
                                style={styles.ipInput}
                                value={newHost}
                                onChangeText={setNewHost}
                                placeholder="192.168.1.100:8765"
                                placeholderTextColor={colors.textMuted}
                                keyboardType="url"
                                autoCapitalize="none"
                                autoCorrect={false}
                                onSubmitEditing={handleReconnect}
                            />
                            <View style={styles.reconnectBtns}>
                                <TouchableOpacity
                                    style={[styles.actionBtn, (!newHost.trim() || reconnecting) && { opacity: 0.4 }]}
                                    onPress={handleReconnect}
                                    disabled={!newHost.trim() || reconnecting}
                                >
                                    <Text style={styles.actionBtnText}>
                                        {reconnecting ? "Connecting..." : "Connect"}
                                    </Text>
                                </TouchableOpacity>
                                <TouchableOpacity
                                    style={styles.cancelBtn}
                                    onPress={() => { setShowReconnect(false); setNewHost(""); }}
                                >
                                    <Text style={styles.cancelBtnText}>Cancel</Text>
                                </TouchableOpacity>
                            </View>
                        </View>
                    )}
                </View>

                {/* Connection Preference */}
                <View style={styles.card}>
                    <Text style={styles.cardTitle}>Connection Mode</Text>
                    <TouchableOpacity
                        style={[styles.optionRow, connPref === "local" && styles.optionSelected]}
                        onPress={() => handleConnPrefChange("local")}
                        activeOpacity={0.7}
                    >
                        <Text style={styles.optionEmoji}>🏠</Text>
                        <View style={{ flex: 1 }}>
                            <Text style={styles.optionLabel}>Local Only</Text>
                            <Text style={styles.optionDesc}>WiFi only — fastest, works at home</Text>
                        </View>
                    </TouchableOpacity>
                    <TouchableOpacity
                        style={[styles.optionRow, connPref === "bridge" && styles.optionSelected]}
                        onPress={() => handleConnPrefChange("bridge")}
                        activeOpacity={0.7}
                    >
                        <Text style={styles.optionEmoji}>🌍</Text>
                        <View style={{ flex: 1 }}>
                            <Text style={styles.optionLabel}>Anywhere Bridge</Text>
                            <Text style={styles.optionDesc}>
                                Via Tailscale VPN {tailscaleIP ? `(${tailscaleIP})` : "— not configured"}
                            </Text>
                        </View>
                    </TouchableOpacity>
                </View>
            </View>

            {/* ── Mode ── */}
            <View style={styles.section}>
                <Text style={styles.sectionTitle}>Experience Mode</Text>
                <View style={styles.card}>
                    <View style={styles.modeRow}>
                        <View style={{ flex: 1 }}>
                            <Text style={styles.cardTitle}>
                                {isPetMode ? "🐾 Companion Mode" : "💼 Executive Mode"}
                            </Text>
                            <Text style={styles.cardDesc}>
                                {isPetMode
                                    ? "Friendly AI companion with care features"
                                    : "Professional assistant with tools & tasks"}
                            </Text>
                        </View>
                        <Switch
                            value={!isPetMode}
                            onValueChange={handleModeSwitch}
                            trackColor={{ false: colors.glassBorder, true: colors.neon }}
                            thumbColor="#fff"
                        />
                    </View>
                    <Text style={styles.modeHint}>
                        {isPetMode ? "Toggle for Executive mode →" : "← Toggle for Companion mode"}
                    </Text>
                </View>
            </View>

            {/* ── Companion Info ── */}
            {companionData?.companion && (
                <View style={styles.section}>
                    <Text style={styles.sectionTitle}>Companion</Text>
                    <View style={styles.card}>
                        <Text style={styles.cardTitle}>
                            {(companionData.companion as any).name || "Companion"}
                        </Text>
                        <Text style={styles.cardDesc}>
                            Species: {(companionData.companion as any).species || "Unknown"} ·
                            Level {(companionData.companion as any).level || 1} ·
                            Happiness: {(companionData.companion as any).happiness || 0}%
                        </Text>
                    </View>
                </View>
            )}

            {/* ── Danger Zone ── */}
            <View style={[styles.section, { marginBottom: spacing.xxxl }]}>
                <Text style={styles.sectionTitle}>Danger Zone</Text>
                <View style={styles.card}>
                    <TouchableOpacity
                        style={styles.dangerBtn}
                        onPress={handleForgetAll}
                        activeOpacity={0.7}
                    >
                        <Text style={styles.dangerBtnText}>Reset App & Disconnect</Text>
                    </TouchableOpacity>
                    <Text style={styles.dangerHint}>
                        Clears local data and restarts onboarding. Your companion on the PC is safe.
                    </Text>
                </View>
            </View>

            {/* ── About ── */}
            <View style={styles.aboutSection}>
                <Text style={styles.aboutText}>Fireside · v0.1.0</Text>
                <Text style={styles.aboutText}>Your private AI companion</Text>
            </View>
        </ScrollView>
    );
}

const styles = StyleSheet.create({
    screen: { flex: 1, backgroundColor: colors.bgPrimary },
    content: { paddingHorizontal: spacing.xl, paddingTop: 60, paddingBottom: 120 },
    title: { fontFamily: "Inter_700Bold", fontSize: fontSize.hero, color: colors.textPrimary, marginBottom: spacing.xl },

    section: { marginBottom: spacing.xl },
    sectionTitle: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.xs, color: colors.textMuted, textTransform: "uppercase", letterSpacing: 1, marginBottom: spacing.sm, marginLeft: spacing.xs },

    card: { backgroundColor: colors.bgCard, borderRadius: borderRadius.lg, borderWidth: 1, borderColor: colors.glassBorder, padding: spacing.lg, marginBottom: spacing.sm, ...shadows.card },
    cardTitle: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.md, color: colors.textPrimary, marginBottom: spacing.xs },
    cardDesc: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.textDim, lineHeight: 18 },

    statusRow: { flexDirection: "row", alignItems: "center", gap: spacing.md, marginBottom: spacing.md },
    statusEmoji: { fontSize: 24 },
    statusLabel: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.md, color: colors.textPrimary },
    statusDetail: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.textDim, marginTop: 2 },

    secondaryBtn: { backgroundColor: colors.bgSecondary, borderRadius: borderRadius.md, paddingVertical: spacing.sm, alignItems: "center", borderWidth: 1, borderColor: colors.glassBorder },
    secondaryBtnText: { fontFamily: "Inter_500Medium", fontSize: fontSize.sm, color: colors.textSecondary },

    reconnectBox: { marginTop: spacing.sm },
    ipInput: { backgroundColor: colors.bgInput, borderRadius: borderRadius.md, borderWidth: 1, borderColor: colors.glassBorder, paddingHorizontal: spacing.md, paddingVertical: spacing.md, fontFamily: "Inter_400Regular", fontSize: fontSize.sm, color: colors.textPrimary, marginBottom: spacing.sm },
    reconnectBtns: { flexDirection: "row", gap: spacing.sm },
    actionBtn: { flex: 1, backgroundColor: colors.neon, borderRadius: borderRadius.md, paddingVertical: spacing.sm, alignItems: "center", ...shadows.glow },
    actionBtnText: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.sm, color: colors.bgPrimary },
    cancelBtn: { flex: 1, backgroundColor: colors.bgSecondary, borderRadius: borderRadius.md, paddingVertical: spacing.sm, alignItems: "center", borderWidth: 1, borderColor: colors.glassBorder },
    cancelBtnText: { fontFamily: "Inter_500Medium", fontSize: fontSize.sm, color: colors.textDim },

    optionRow: { flexDirection: "row", alignItems: "center", gap: spacing.md, paddingVertical: spacing.md, paddingHorizontal: spacing.sm, borderRadius: borderRadius.md, marginTop: spacing.xs },
    optionSelected: { backgroundColor: colors.neonGlow, borderWidth: 1, borderColor: colors.neonBorder },
    optionEmoji: { fontSize: 24 },
    optionLabel: { fontFamily: "Inter_500Medium", fontSize: fontSize.sm, color: colors.textPrimary },
    optionDesc: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.textDim, marginTop: 2 },

    modeRow: { flexDirection: "row", alignItems: "center", gap: spacing.md },
    modeHint: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.textMuted, marginTop: spacing.sm, textAlign: "center" },

    dangerBtn: { backgroundColor: "rgba(239, 68, 68, 0.15)", borderRadius: borderRadius.md, paddingVertical: spacing.md, alignItems: "center", borderWidth: 1, borderColor: "rgba(239, 68, 68, 0.3)" },
    dangerBtnText: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.sm, color: "#EF4444" },
    dangerHint: { fontFamily: "Inter_400Regular", fontSize: fontSize.tiny, color: colors.textMuted, marginTop: spacing.sm, textAlign: "center" },

    aboutSection: { alignItems: "center", marginBottom: spacing.xxxl },
    aboutText: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.textMuted, marginBottom: 2 },
});
