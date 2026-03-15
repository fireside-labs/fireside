/**
 * Privacy Policy — Sprint 3 Task 5.
 *
 * Static screen accessible from setup screen.
 * Required for App Store submission.
 */
import { ScrollView, Text, StyleSheet, TouchableOpacity } from "react-native";
import { useRouter } from "expo-router";
import { colors, spacing, borderRadius, fontSize } from "../src/theme";

export default function PrivacyPolicyScreen() {
    const router = useRouter();

    return (
        <ScrollView style={styles.container} contentContainerStyle={styles.content}>
            <TouchableOpacity
                style={styles.backBtn}
                onPress={() => router.back()}
                activeOpacity={0.7}
            >
                <Text style={styles.backText}>← Back</Text>
            </TouchableOpacity>

            <Text style={styles.title}>Privacy Policy</Text>
            <Text style={styles.updated}>Last updated: March 2026</Text>

            <Text style={styles.heading}>Your Data Stays With You</Text>
            <Text style={styles.body}>
                Valhalla is designed to run entirely on your own hardware. Your companion's
                brain, memories, and personality live on your home PC — not on our servers,
                not in the cloud.
            </Text>

            <Text style={styles.heading}>What This App Stores</Text>
            <Text style={styles.body}>
                <Text style={styles.bold}>On your phone (locally):</Text>
                {"\n"}• Your home PC's IP address (for connecting)
                {"\n"}• Chat history (last 100 messages)
                {"\n"}• Cached companion state (for offline mode)
                {"\n"}• Onboarding completion flag
                {"\n\n"}
                <Text style={styles.bold}>On your home PC:</Text>
                {"\n"}• Companion data (name, species, happiness, XP)
                {"\n"}• Chat history
                {"\n"}• Task queue
            </Text>

            <Text style={styles.heading}>Push Notifications</Text>
            <Text style={styles.body}>
                If you enable push notifications, your device's Expo push token is sent
                to your home PC so it can reach your phone. This token is stored only on
                your home PC — we do not collect it. You can disable notifications at
                any time from the app settings.
            </Text>

            <Text style={styles.heading}>No Analytics or Tracking</Text>
            <Text style={styles.body}>
                Valhalla does not include any analytics SDKs, tracking pixels, or telemetry.
                We don't know who you are, what you name your companion, or how often you
                use the app.
            </Text>

            <Text style={styles.heading}>No Cloud Servers</Text>
            <Text style={styles.body}>
                All communication happens directly between your phone and your home PC
                over your local network or Tailscale VPN. No data passes through our
                infrastructure.
            </Text>

            <Text style={styles.heading}>Third-Party Services</Text>
            <Text style={styles.body}>
                The only third-party service used is Expo's push notification relay, which
                routes notifications from your home PC to your phone via Apple (APNs) or
                Google (FCM). Expo's privacy policy applies to push token handling only.
            </Text>

            <Text style={styles.heading}>Contact</Text>
            <Text style={styles.body}>
                Questions about this policy?{"\n"}
                Email: privacy@valhalla.local{"\n"}
                GitHub: github.com/valhalla-mesh
            </Text>

            <Text style={styles.footer}>
                Valhalla — Private by design. Your companion, your hardware, your data.
            </Text>
        </ScrollView>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: colors.bgPrimary,
    },
    content: {
        paddingHorizontal: spacing.xxl,
        paddingTop: 60,
        paddingBottom: spacing.xxxl + 20,
    },
    backBtn: {
        marginBottom: spacing.lg,
    },
    backText: {
        fontFamily: "Inter_400Regular",
        fontSize: fontSize.sm,
        color: colors.neon,
    },
    title: {
        fontFamily: "Inter_700Bold",
        fontSize: fontSize.hero,
        color: colors.textPrimary,
        marginBottom: spacing.xs,
    },
    updated: {
        fontFamily: "Inter_400Regular",
        fontSize: fontSize.tiny,
        color: colors.textMuted,
        marginBottom: spacing.xxl,
    },
    heading: {
        fontFamily: "Inter_600SemiBold",
        fontSize: fontSize.lg,
        color: colors.textPrimary,
        marginTop: spacing.xl,
        marginBottom: spacing.sm,
    },
    body: {
        fontFamily: "Inter_400Regular",
        fontSize: fontSize.sm,
        color: colors.textSecondary,
        lineHeight: 20,
    },
    bold: {
        fontFamily: "Inter_600SemiBold",
        color: colors.textPrimary,
    },
    footer: {
        fontFamily: "Inter_500Medium",
        fontSize: fontSize.xs,
        color: colors.neon,
        textAlign: "center",
        marginTop: spacing.xxxl,
        marginBottom: spacing.lg,
    },
});
