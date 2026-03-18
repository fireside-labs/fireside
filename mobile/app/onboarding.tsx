/**
 * 🚀 Onboarding v2.
 * Connection choice (Local Only vs Anywhere Bridge).
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

type OnboardingStep = "welcome" | "connect" | "waitlist_done" | "orphan_save" | "companion_create" | "bridge" | "vpn_guide" | "mode" | "permissions" | "first_jump" | "done";

const SPECIES_OPTIONS: Array<{ id: string; emoji: string; name: string; personality: string; greeting: string }> = [
    { id: "fox", emoji: "🦊", name: "Fox", personality: "Clever & curious", greeting: "Hmm, interesting place you've got here. I like it — cozy." },
    { id: "cat", emoji: "🐱", name: "Cat", personality: "Independent & witty", greeting: "*yawns* Oh, a phone. Let me get comfortable..." },
    { id: "dog", emoji: "🐶", name: "Dog", personality: "Loyal & enthusiastic", greeting: "OH WOW A NEW HOME!! I'm SO excited to be here!!" },
    { id: "owl", emoji: "🦉", name: "Owl", personality: "Wise & thoughtful", greeting: "Ah, a pocket-sized dwelling. Compact, yet adequate for wisdom." },
    { id: "penguin", emoji: "🐧", name: "Penguin", personality: "Formal & precise", greeting: "Good day. I've completed the transfer protocol. All systems nominal." },
    { id: "dragon", emoji: "🐉", name: "Dragon", personality: "Bold & dramatic", greeting: "A PHONE?! This is... surprisingly warm. I approve!" },
];

export default function OnboardingV2() {
    const router = useRouter();
    const [step, setStep] = useState<OnboardingStep>("welcome");
    const [waitlistEmail, setWaitlistEmail] = useState("");
    const [waitlistSubmitting, setWaitlistSubmitting] = useState(false);
    const [manualIP, setManualIP] = useState("");
    const [connecting, setConnecting] = useState(false);
    const [selectedMode, setSelectedMode] = useState<"pet" | "tool">("pet");
    const [fetchingBridge, setFetchingBridge] = useState(false);
    // Companion creation state
    const [selectedSpecies, setSelectedSpecies] = useState("fox");
    const [companionName, setCompanionName] = useState("");
    const [adopting, setAdopting] = useState(false);
    const [hasExistingCompanion, setHasExistingCompanion] = useState(false);

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
                // Check if a companion already exists on the desktop
                try {
                    const status = await companionAPI.companionStatus();
                    if (status.companion && Object.keys(status.companion).length > 0) {
                        setHasExistingCompanion(true);
                        setCompanionName((status.companion as any).name || "");
                        setSelectedSpecies((status.companion as any).species || "fox");
                        setStep("bridge"); // companion exists, skip creation
                    } else {
                        setStep("companion_create"); // no companion — let user create one
                    }
                } catch {
                    setStep("companion_create"); // can't check — offer creation
                }
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
            setStep("orphan_save");
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

    // — Orphan Save (no desktop — pick companion + email link) —
    if (step === "orphan_save") {
        return (
            <ScrollView style={styles.scrollScreen} contentContainerStyle={styles.scrollContent}>
                <Text style={styles.stepTitle}>Pick Your Companion</Text>
                <Text style={styles.stepSubtitle}>
                    Choose who'll be waiting when you set up your desktop
                </Text>

                <View style={styles.speciesGrid}>
                    {SPECIES_OPTIONS.map((s) => (
                        <TouchableOpacity
                            key={s.id}
                            style={[styles.speciesCard, selectedSpecies === s.id && styles.speciesSelected]}
                            onPress={() => { setSelectedSpecies(s.id); Haptics.selectionAsync(); }}
                            activeOpacity={0.7}
                        >
                            <Text style={styles.speciesEmoji}>{s.emoji}</Text>
                            <Text style={styles.speciesName}>{s.name}</Text>
                            <Text style={styles.speciesPersonality}>{s.personality}</Text>
                        </TouchableOpacity>
                    ))}
                </View>

                <TextInput
                    style={styles.nameInput}
                    value={companionName}
                    onChangeText={setCompanionName}
                    placeholder="Name your companion..."
                    placeholderTextColor={colors.textMuted}
                    autoCapitalize="words"
                    maxLength={20}
                />

                <View style={styles.pathCard}>
                    <Text style={styles.pathEmoji}>📧</Text>
                    <Text style={styles.pathTitle}>We saved your choice!</Text>
                    <Text style={styles.pathDesc}>
                        We'll email you the link to download Fireside on your PC. Once it's running, open this app and your {SPECIES_OPTIONS.find(s => s.id === selectedSpecies)?.name || "companion"} will be waiting.
                    </Text>
                </View>

                <TouchableOpacity
                    style={styles.primaryBtn}
                    onPress={async () => {
                        await AsyncStorage.setItem("saved_species", selectedSpecies);
                        await AsyncStorage.setItem("saved_name", companionName || SPECIES_OPTIONS.find(s => s.id === selectedSpecies)?.name || "Ember");
                        Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
                        setStep("waitlist_done");
                    }}
                    activeOpacity={0.8}
                >
                    <Text style={styles.primaryBtnText}>Save & Done 🔥</Text>
                </TouchableOpacity>
            </ScrollView>
        );
    }

    // — Companion Creation (connected to desktop, no companion yet) —
    if (step === "companion_create") {
        const handleAdopt = async () => {
            const name = companionName.trim() || SPECIES_OPTIONS.find(s => s.id === selectedSpecies)?.name || "Ember";
            setAdopting(true);
            Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
            try {
                await companionAPI.adopt(name, selectedSpecies);
                setCompanionName(name);
                setStep("bridge");
            } catch {
                Alert.alert("Adoption Failed", "Couldn't create your companion. Make sure your PC is running.");
            }
            setAdopting(false);
        };

        return (
            <ScrollView style={styles.scrollScreen} contentContainerStyle={styles.scrollContent}>
                <Text style={styles.fireEmoji}>✨</Text>
                <Text style={styles.stepTitle}>Create Your Companion</Text>
                <Text style={styles.stepSubtitle}>
                    One soul — lives on your PC, travels with your phone
                </Text>

                <View style={styles.speciesGrid}>
                    {SPECIES_OPTIONS.map((s) => (
                        <TouchableOpacity
                            key={s.id}
                            style={[styles.speciesCard, selectedSpecies === s.id && styles.speciesSelected]}
                            onPress={() => { setSelectedSpecies(s.id); Haptics.selectionAsync(); }}
                            activeOpacity={0.7}
                        >
                            <Text style={styles.speciesEmoji}>{s.emoji}</Text>
                            <Text style={styles.speciesName}>{s.name}</Text>
                            <Text style={styles.speciesPersonality}>{s.personality}</Text>
                        </TouchableOpacity>
                    ))}
                </View>

                <TextInput
                    style={styles.nameInput}
                    value={companionName}
                    onChangeText={setCompanionName}
                    placeholder="Name your companion..."
                    placeholderTextColor={colors.textMuted}
                    autoCapitalize="words"
                    maxLength={20}
                    onSubmitEditing={handleAdopt}
                />

                <TouchableOpacity
                    style={[styles.primaryBtn, adopting && { opacity: 0.5 }]}
                    onPress={handleAdopt}
                    disabled={adopting}
                    activeOpacity={0.8}
                >
                    <Text style={styles.primaryBtnText}>
                        {adopting ? "Creating..." : `Adopt ${companionName.trim() || SPECIES_OPTIONS.find(s => s.id === selectedSpecies)?.name || "Ember"} 🔥`}
                    </Text>
                </TouchableOpacity>
            </ScrollView>
        );
    }

    // — Connection Choice —
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

    // — VPN Guidance —
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
                        setStep(hasExistingCompanion ? "permissions" : "permissions");
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
            setStep(hasExistingCompanion ? "first_jump" : "done");
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
                <TouchableOpacity onPress={() => setStep(hasExistingCompanion ? "first_jump" : "done")} activeOpacity={0.7}>
                    <Text style={styles.skipText}>Skip for now</Text>
                </TouchableOpacity>
            </View>
        );
    }

    // — First Jump Greeting (companion speaks in character) —
    if (step === "first_jump") {
        const speciesData = SPECIES_OPTIONS.find(s => s.id === selectedSpecies) || SPECIES_OPTIONS[0];
        const displayName = companionName || "Companion";

        return (
            <View style={styles.screen}>
                <Text style={styles.jumpEmoji}>{speciesData.emoji}</Text>
                <Text style={styles.jumpTitle}>{displayName}</Text>
                <View style={styles.jumpBubble}>
                    <Text style={styles.jumpGreeting}>
                        {speciesData.greeting}
                    </Text>
                </View>
                <Text style={styles.jumpSubtext}>
                    My brain lives on your PC, but now I can see through your phone too. Same soul — just portable.
                </Text>
                <TouchableOpacity
                    style={styles.primaryBtn}
                    onPress={() => router.replace("/(tabs)/care")}
                    activeOpacity={0.8}
                >
                    <Text style={styles.primaryBtnText}>Hey {displayName}! 🔥</Text>
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
    // Species picker
    speciesGrid: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm, marginBottom: spacing.lg },
    speciesCard: { width: "48%" as any, backgroundColor: colors.bgCard, borderRadius: borderRadius.lg, borderWidth: 2, borderColor: colors.glassBorder, padding: spacing.lg, alignItems: "center", ...shadows.card },
    speciesSelected: { borderColor: colors.neon, backgroundColor: colors.neonGlow, ...shadows.glow },
    speciesEmoji: { fontSize: 36, marginBottom: spacing.xs },
    speciesName: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.md, color: colors.textPrimary },
    speciesPersonality: { fontFamily: "Inter_400Regular", fontSize: fontSize.tiny, color: colors.textDim, textAlign: "center", marginTop: 2 },
    nameInput: { backgroundColor: colors.bgInput, borderRadius: borderRadius.md, borderWidth: 1, borderColor: colors.glassBorder, paddingHorizontal: spacing.md, paddingVertical: spacing.lg, fontFamily: "Inter_600SemiBold", fontSize: fontSize.lg, color: colors.textPrimary, textAlign: "center", marginBottom: spacing.md },
    // First jump greeting
    jumpEmoji: { fontSize: 80, marginBottom: spacing.md },
    jumpTitle: { fontFamily: "Inter_700Bold", fontSize: fontSize.hero, color: colors.textPrimary, marginBottom: spacing.lg },
    jumpBubble: { backgroundColor: colors.bgCard, borderRadius: borderRadius.lg, borderWidth: 1, borderColor: colors.neonBorder, padding: spacing.xl, marginBottom: spacing.lg, maxWidth: "85%" as any, ...shadows.card },
    jumpGreeting: { fontFamily: "Inter_400Regular", fontSize: fontSize.md, color: colors.textSecondary, lineHeight: 22, textAlign: "center", fontStyle: "italic" },
    jumpSubtext: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.textDim, textAlign: "center", lineHeight: 18, paddingHorizontal: spacing.xl, marginBottom: spacing.lg },
});
