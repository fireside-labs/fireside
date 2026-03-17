/**
 * 🚀 Onboarding v2 — Sprint 8 Task 2.
 * Sprint 11: Connection choice (Local Only vs Anywhere Bridge).
 *
 * Three paths:
 *   1. Self-hosted: QR/IP → connection choice → mode select → permissions → done
 *   2. Waitlist: email signup → "spot saved" → end
 *   3. Anywhere Bridge: Tailscale VPN guidance
 *
 * Per CREATIVE_DIRECTION.md: warm, inviting, campfire aesthetic.
 */
import { useState } from "react";
import {
    View,
    Text,
    TextInput,
    TouchableOpacity,
    ScrollView,
    StyleSheet,
    Alert,
} from "react-native";
import { useRouter } from "expo-router";
import * as Haptics from "expo-haptics";
import * as Notifications from "expo-notifications";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { companionAPI, setHost, setTailscaleIP, setConnectionPref, testConnection } from "../src/api";
import { colors, spacing, borderRadius, fontSize, shadows } from "../src/theme";

/** Check if onboarding has been completed. */
export async function hasOnboarded(): Promise<boolean> {
    const mode = await AsyncStorage.getItem("connectionMode");
    return mode === "selfhosted" || mode === "waitlist";
}

type OnboardingStep = "welcome" | "connect" | "waitlist_done" | "bridge" | "vpn_guide" | "mode" | "permissions" | "done";

export default function OnboardingV2() {
    const router = useRouter();
    const [step, setStep] = useState<OnboardingStep>("welcome");
    const [waitlistEmail, setWaitlistEmail] = useState("");
    const [waitlistSubmitting, setWaitlistSubmitting] = useState(false);
    const [manualIP, setManualIP] = useState("");
    const [connecting, setConnecting] = useState(false);
    const [selectedMode, setSelectedMode] = useState<"pet" | "tool">("pet");
    const [fetchingBridge, setFetchingBridge] = useState(false);

    // — Welcome —
    if (step === "welcome") {
        return (
            <View style={styles.screen}>
                <Text style={styles.fireEmoji}>🔥</Text>
                <Text style={styles.heroTitle}>Fireside</Text>
                <Text style={styles.heroSubtitle}>Your private AI companion</Text>
                <Text style={styles.heroDesc}>
                    Runs on your hardware. Your data never leaves your network.
                </Text>
                <TouchableOpacity
                    style={styles.primaryBtn}
                    onPress={() => { setStep("connect"); Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium); }}
                    activeOpacity={0.8}
                >
                    <Text style={styles.primaryBtnText}>Get Started</Text>
                </TouchableOpacity>
            </View>
        );
    }

    // — Connect —
    if (step === "connect") {
        const handleSelfHosted = async () => {
            const ip = manualIP.trim();
            if (!ip) return;
            setConnecting(true);
            Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
            await setHost(ip);
            const ok = await testConnection();
            if (ok) {
                await AsyncStorage.setItem("connectionMode", "selfhosted");
                setStep("bridge"); // Sprint 11: ask connection preference next
            } else {
                Alert.alert("Connection Failed", "Check the IP and make sure Fireside is running on your PC.");
            }
            setConnecting(false);
        };

        const handleWaitlist = async () => {
            if (!waitlistEmail.trim() || !waitlistEmail.includes("@")) {
                Alert.alert("Invalid Email", "Please enter a valid email address.");
                return;
            }
            setWaitlistSubmitting(true);
            Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
            try {
                await companionAPI.waitlist(waitlistEmail.trim());
            } catch {
                // Backend may not be running — that's okay for waitlist
            }
            await AsyncStorage.setItem("connectionMode", "waitlist");
            await AsyncStorage.setItem("waitlistEmail", waitlistEmail.trim());
            setWaitlistSubmitting(false);
            setStep("waitlist_done");
        };

        return (
            <ScrollView style={styles.scrollScreen} contentContainerStyle={styles.scrollContent}>
                <Text style={styles.stepTitle}>How would you like to connect?</Text>

                {/* Self-hosted path */}
                <View style={styles.pathCard}>
                    <Text style={styles.pathEmoji}>🏠</Text>
                    <Text style={styles.pathTitle}>I have Fireside on my PC</Text>
                    <Text style={styles.pathDesc}>Connect to your home computer running Fireside</Text>

                    <TextInput
                        style={styles.ipInput}
                        value={manualIP}
                        onChangeText={setManualIP}
                        placeholder="192.168.1.100:8765"
                        placeholderTextColor={colors.textMuted}
                        keyboardType="url"
                        autoCapitalize="none"
                        autoCorrect={false}
                        onSubmitEditing={handleSelfHosted}
                    />
                    <TouchableOpacity
                        style={[styles.connectBtn, (!manualIP.trim() || connecting) && { opacity: 0.4 }]}
                        onPress={handleSelfHosted}
                        disabled={!manualIP.trim() || connecting}
                        activeOpacity={0.7}
                    >
                        <Text style={styles.connectBtnText}>
                            {connecting ? "Connecting..." : "Connect"}
                        </Text>
                    </TouchableOpacity>
                </View>

                {/* Waitlist path */}
                <View style={styles.pathCard}>
                    <Text style={styles.pathEmoji}>☁️</Text>
                    <Text style={styles.pathTitle}>Set it up for me</Text>
                    <Text style={styles.pathDesc}>
                        Don't have a PC? Join the waitlist for hosted Fireside.
                    </Text>

                    <TextInput
                        style={styles.ipInput}
                        value={waitlistEmail}
                        onChangeText={setWaitlistEmail}
                        placeholder="your@email.com"
                        placeholderTextColor={colors.textMuted}
                        keyboardType="email-address"
                        autoCapitalize="none"
                        autoCorrect={false}
                        onSubmitEditing={handleWaitlist}
                    />
                    <TouchableOpacity
                        style={[styles.waitlistBtn, (!waitlistEmail.trim() || waitlistSubmitting) && { opacity: 0.4 }]}
                        onPress={handleWaitlist}
                        disabled={!waitlistEmail.trim() || waitlistSubmitting}
                        activeOpacity={0.7}
                    >
                        <Text style={styles.waitlistBtnText}>
                            {waitlistSubmitting ? "Joining..." : "Join Waitlist"}
                        </Text>
                    </TouchableOpacity>
                </View>
            </ScrollView>
        );
    }

    // — Connection Choice (Sprint 11) —
    if (step === "bridge") {
        const handleLocalOnly = async () => {
            await setConnectionPref("local");
            Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
            setStep("mode");
        };

        const handleBridge = async () => {
            setFetchingBridge(true);
            Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
            try {
                const ns = await companionAPI.networkStatus();
                if (ns.tailscale_ip) {
                    await setTailscaleIP(ns.tailscale_ip);
                    await setConnectionPref("bridge");
                    setStep("mode");
                } else {
                    // No Tailscale IP yet — show setup guide
                    await setConnectionPref("bridge");
                    setStep("vpn_guide");
                }
            } catch {
                // Can't reach network/status — show guide anyway
                await setConnectionPref("bridge");
                setStep("vpn_guide");
            }
            setFetchingBridge(false);
        };

        return (
            <View style={styles.screen}>
                <Text style={styles.stepTitle}>How should your companion connect?</Text>
                <Text style={styles.stepSubtitle}>Choose how Ember reaches Atlas when you leave home</Text>

                <TouchableOpacity
                    style={[styles.modeOption, { marginTop: spacing.xl }]}
                    onPress={handleLocalOnly}
                    activeOpacity={0.7}
                >
                    <Text style={styles.modeEmoji}>🏠</Text>
                    <Text style={styles.modeLabel}>Local Only</Text>
                    <Text style={styles.modeDesc2}>Works only at home on Wi-Fi. Simple, no extra setup.</Text>
                </TouchableOpacity>

                <TouchableOpacity
                    style={[styles.modeOption, fetchingBridge && { opacity: 0.5 }]}
                    onPress={handleBridge}
                    disabled={fetchingBridge}
                    activeOpacity={0.7}
                >
                    <Text style={styles.modeEmoji}>🌍</Text>
                    <Text style={styles.modeLabel}>Anywhere Bridge</Text>
                    <Text style={styles.modeDesc2}>
                        {fetchingBridge ? "Checking..." : "Connect securely from anywhere via Tailscale VPN"}
                    </Text>
                </TouchableOpacity>
            </View>
        );
    }

    // — VPN Guidance (Sprint 11) —
    if (step === "vpn_guide") {
        return (
            <ScrollView style={styles.scrollScreen} contentContainerStyle={styles.scrollContent}>
                <Text style={styles.stepTitle}>Set Up Anywhere Bridge</Text>
                <Text style={styles.stepSubtitle}>
                    Tailscale creates a private tunnel so your phone can always reach your home PC — even from coffee shops, work, or travel.
                </Text>

                <View style={styles.pathCard}>
                    <Text style={styles.pathEmoji}>1️⃣</Text>
                    <Text style={styles.pathTitle}>On your PC</Text>
                    <Text style={styles.pathDesc}>
                        Fireside has already set up Tailscale on your computer. If not, run the setup script from the dashboard.
                    </Text>
                </View>

                <View style={styles.pathCard}>
                    <Text style={styles.pathEmoji}>2️⃣</Text>
                    <Text style={styles.pathTitle}>On your iPhone</Text>
                    <Text style={styles.pathDesc}>
                        Download "Tailscale" from the App Store and sign in with the same account you used on your PC.
                    </Text>
                </View>

                <View style={styles.pathCard}>
                    <Text style={styles.pathEmoji}>3️⃣</Text>
                    <Text style={styles.pathTitle}>That's it!</Text>
                    <Text style={styles.pathDesc}>
                        Once both devices are on Tailscale, your companion can reach Atlas from anywhere. Your data still never touches our servers — it goes directly between your devices.
                    </Text>
                </View>

                <TouchableOpacity
                    style={styles.primaryBtn}
                    onPress={async () => {
                        // Try to fetch tailscale_ip one more time
                        try {
                            const ns = await companionAPI.networkStatus();
                            if (ns.tailscale_ip) {
                                await setTailscaleIP(ns.tailscale_ip);
                            }
                        } catch { }
                        Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
                        setStep("mode");
                    }}
                    activeOpacity={0.8}
                >
                    <Text style={styles.primaryBtnText}>I've installed Tailscale →</Text>
                </TouchableOpacity>
                <TouchableOpacity onPress={() => setStep("mode")} activeOpacity={0.7}>
                    <Text style={styles.skipText}>Skip for now</Text>
                </TouchableOpacity>
            </ScrollView>
        );
    }

    // — Waitlist Done —
    if (step === "waitlist_done") {
        return (
            <View style={styles.screen}>
                <Text style={styles.doneEmoji}>✨</Text>
                <Text style={styles.doneTitle}>You're on the list!</Text>
                <Text style={styles.doneDesc}>
                    We'll email you when your private AI is ready. No spam — just one email when it's time.
                </Text>
                <TouchableOpacity
                    style={styles.doneBtn}
                    onPress={() => router.replace("/(tabs)/care")}
                    activeOpacity={0.8}
                >
                    <Text style={styles.doneBtnText}>Got it 🔥</Text>
                </TouchableOpacity>
            </View>
        );
    }

    // — Mode Select (self-hosted only) —
    if (step === "mode") {
        return (
            <View style={styles.screen}>
                <Text style={styles.stepTitle}>Choose your experience</Text>
                <Text style={styles.stepSubtitle}>You can switch anytime in Settings</Text>

                <TouchableOpacity
                    style={[styles.modeOption, selectedMode === "pet" && styles.modeSelected]}
                    onPress={() => { setSelectedMode("pet"); Haptics.selectionAsync(); }}
                    activeOpacity={0.7}
                >
                    <Text style={styles.modeEmoji}>🐾</Text>
                    <Text style={styles.modeLabel}>Companion</Text>
                    <Text style={styles.modeDesc2}>A friendly AI that grows with you</Text>
                </TouchableOpacity>

                <TouchableOpacity
                    style={[styles.modeOption, selectedMode === "tool" && styles.modeSelected]}
                    onPress={() => { setSelectedMode("tool"); Haptics.selectionAsync(); }}
                    activeOpacity={0.7}
                >
                    <Text style={styles.modeEmoji}>💼</Text>
                    <Text style={styles.modeLabel}>Executive</Text>
                    <Text style={styles.modeDesc2}>Your private AI assistant for tasks and research</Text>
                </TouchableOpacity>

                <TouchableOpacity
                    style={styles.primaryBtn}
                    onPress={async () => {
                        await AsyncStorage.setItem("fireside_companion_mode", selectedMode);
                        Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
                        setStep("permissions");
                    }}
                    activeOpacity={0.8}
                >
                    <Text style={styles.primaryBtnText}>Continue</Text>
                </TouchableOpacity>
            </View>
        );
    }

    // — Permissions —
    if (step === "permissions") {
        const requestPermissions = async () => {
            Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
            try { await Notifications.requestPermissionsAsync(); } catch { }
            setStep("done");
        };

        return (
            <View style={styles.screen}>
                <Text style={styles.stepTitle}>Permissions</Text>
                <Text style={styles.stepSubtitle}>These help your companion work better</Text>

                <View style={styles.permList}>
                    <View style={styles.permItem}>
                        <Text style={styles.permIcon}>🎤</Text>
                        <View style={styles.permInfo}>
                            <Text style={styles.permName}>Microphone</Text>
                            <Text style={styles.permWhy}>Talk to your AI with voice mode</Text>
                        </View>
                    </View>
                    <View style={styles.permItem}>
                        <Text style={styles.permIcon}>🔔</Text>
                        <View style={styles.permInfo}>
                            <Text style={styles.permName}>Notifications</Text>
                            <Text style={styles.permWhy}>Get alerts when your companion needs attention</Text>
                        </View>
                    </View>
                    <View style={styles.permItem}>
                        <Text style={styles.permIcon}>📷</Text>
                        <View style={styles.permInfo}>
                            <Text style={styles.permName}>Camera</Text>
                            <Text style={styles.permWhy}>Scan QR codes to pair with your PC</Text>
                        </View>
                    </View>
                </View>

                <TouchableOpacity style={styles.primaryBtn} onPress={requestPermissions} activeOpacity={0.8}>
                    <Text style={styles.primaryBtnText}>Allow & Continue</Text>
                </TouchableOpacity>
                <TouchableOpacity onPress={() => setStep("done")} activeOpacity={0.7}>
                    <Text style={styles.skipText}>Skip for now</Text>
                </TouchableOpacity>
            </View>
        );
    }

    // — Done —
    return (
        <View style={styles.screen}>
            <Text style={styles.doneEmoji}>🔥</Text>
            <Text style={styles.doneTitle}>You're all set!</Text>
            <Text style={styles.doneDesc}>
                {selectedMode === "pet"
                    ? "Your companion is waiting. Go say hello!"
                    : "Your AI assistant is ready. Try asking it something."}
            </Text>
            <TouchableOpacity style={styles.primaryBtn} onPress={() => router.replace("/(tabs)/care")} activeOpacity={0.8}>
                <Text style={styles.primaryBtnText}>Let's go 🔥</Text>
            </TouchableOpacity>
        </View>
    );
}

const styles = StyleSheet.create({
    screen: { flex: 1, backgroundColor: colors.bgPrimary, justifyContent: "center", alignItems: "center", paddingHorizontal: spacing.xl },
    scrollScreen: { flex: 1, backgroundColor: colors.bgPrimary },
    scrollContent: { paddingHorizontal: spacing.xl, paddingTop: 80, paddingBottom: spacing.xxxl },
    fireEmoji: { fontSize: 64, marginBottom: spacing.lg },
    heroTitle: { fontFamily: "Inter_700Bold", fontSize: 36, color: colors.textPrimary, marginBottom: spacing.xs },
    heroSubtitle: { fontFamily: "Inter_400Regular", fontSize: fontSize.lg, color: colors.neon, marginBottom: spacing.md },
    heroDesc: { fontFamily: "Inter_400Regular", fontSize: fontSize.sm, color: colors.textDim, textAlign: "center", lineHeight: 20, marginBottom: spacing.xxxl },
    stepTitle: { fontFamily: "Inter_700Bold", fontSize: fontSize.xxl, color: colors.textPrimary, textAlign: "center", marginBottom: spacing.xs },
    stepSubtitle: { fontFamily: "Inter_400Regular", fontSize: fontSize.sm, color: colors.textDim, textAlign: "center", marginBottom: spacing.xl },
    // Connect
    pathCard: { backgroundColor: colors.bgCard, borderRadius: borderRadius.lg, borderWidth: 1, borderColor: colors.glassBorder, padding: spacing.xl, marginBottom: spacing.lg, ...shadows.card },
    pathEmoji: { fontSize: 32, marginBottom: spacing.sm },
    pathTitle: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.md, color: colors.textPrimary, marginBottom: spacing.xs },
    pathDesc: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.textDim, marginBottom: spacing.md },
    ipInput: { backgroundColor: colors.bgInput, borderRadius: borderRadius.md, borderWidth: 1, borderColor: colors.glassBorder, paddingHorizontal: spacing.md, paddingVertical: spacing.md, fontFamily: "Inter_400Regular", fontSize: fontSize.sm, color: colors.textPrimary, marginBottom: spacing.md },
    connectBtn: { backgroundColor: colors.neon, borderRadius: borderRadius.md, paddingVertical: spacing.md, alignItems: "center", ...shadows.glow },
    connectBtnText: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.sm, color: colors.bgPrimary },
    waitlistBtn: { backgroundColor: colors.bgSecondary, borderRadius: borderRadius.md, paddingVertical: spacing.md, alignItems: "center", borderWidth: 1, borderColor: colors.neonBorder },
    waitlistBtnText: { fontFamily: "Inter_500Medium", fontSize: fontSize.sm, color: colors.neon },
    // Mode
    modeOption: { width: "100%", backgroundColor: colors.bgCard, borderRadius: borderRadius.lg, borderWidth: 2, borderColor: colors.glassBorder, padding: spacing.xl, marginBottom: spacing.md, alignItems: "center", ...shadows.card },
    modeSelected: { borderColor: colors.neon, backgroundColor: colors.neonGlow, ...shadows.glow },
    modeEmoji: { fontSize: 40, marginBottom: spacing.sm },
    modeLabel: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.lg, color: colors.textPrimary, marginBottom: spacing.xs },
    modeDesc2: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.textDim, textAlign: "center" },
    // Permissions
    permList: { width: "100%", marginBottom: spacing.xl },
    permItem: { flexDirection: "row", alignItems: "center", gap: spacing.md, paddingVertical: spacing.md, borderBottomWidth: 1, borderBottomColor: colors.glassBorder },
    permIcon: { fontSize: 24 },
    permInfo: { flex: 1 },
    permName: { fontFamily: "Inter_500Medium", fontSize: fontSize.md, color: colors.textPrimary },
    permWhy: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.textDim, marginTop: 2 },
    // Done
    doneEmoji: { fontSize: 64, marginBottom: spacing.lg },
    doneTitle: { fontFamily: "Inter_700Bold", fontSize: fontSize.xxl, color: colors.textPrimary, marginBottom: spacing.sm },
    doneDesc: { fontFamily: "Inter_400Regular", fontSize: fontSize.sm, color: colors.textDim, textAlign: "center", lineHeight: 20, marginBottom: spacing.xxxl },
    doneBtn: { backgroundColor: colors.neon, borderRadius: borderRadius.md, paddingVertical: spacing.lg, paddingHorizontal: spacing.xxxl, ...shadows.glow },
    doneBtnText: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.md, color: colors.bgPrimary },
    // Shared
    primaryBtn: { backgroundColor: colors.neon, borderRadius: borderRadius.md, paddingVertical: spacing.lg, paddingHorizontal: spacing.xxxl, marginTop: spacing.lg, ...shadows.glow },
    primaryBtnText: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.md, color: colors.bgPrimary },
    skipText: { fontFamily: "Inter_400Regular", fontSize: fontSize.sm, color: colors.textMuted, marginTop: spacing.lg },
});
