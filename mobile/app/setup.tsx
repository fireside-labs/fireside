/**
 * Setup Screen — Shown on first launch.
 *
 * User enters their home PC IP address, tests the connection,
 * then gets routed to the main app.
 */
import { useState } from "react";
import {
    View,
    Text,
    TextInput,
    TouchableOpacity,
    StyleSheet,
    KeyboardAvoidingView,
    Platform,
    ActivityIndicator,
} from "react-native";
import { useRouter } from "expo-router";
import { setHost, testConnection } from "../src/api";
import { colors, spacing, borderRadius, fontSize } from "../src/theme";

type ConnectionStatus = "idle" | "testing" | "success" | "error";

export default function SetupScreen() {
    const [ip, setIp] = useState("");
    const [status, setStatus] = useState<ConnectionStatus>("idle");
    const [errorMsg, setErrorMsg] = useState("");
    const router = useRouter();

    const handleTest = async () => {
        const trimmed = ip.trim();
        if (!trimmed) {
            setErrorMsg("Enter your home PC's IP address");
            setStatus("error");
            return;
        }

        setStatus("testing");
        setErrorMsg("");

        // Temporarily save the host for testing
        await setHost(trimmed);
        const ok = await testConnection();

        if (ok) {
            setStatus("success");
            // Short delay to show success state
            setTimeout(() => {
                router.replace("/(tabs)/care");
            }, 800);
        } else {
            setStatus("error");
            setErrorMsg("Can't reach your home PC. Check the IP and port.");
        }
    };

    return (
        <KeyboardAvoidingView
            style={styles.container}
            behavior={Platform.OS === "ios" ? "padding" : undefined}
        >
            <View style={styles.inner}>
                {/* Logo / Header */}
                <View style={styles.header}>
                    <Text style={styles.logo}>⚡</Text>
                    <Text style={styles.title}>Valhalla</Text>
                    <Text style={styles.subtitle}>Connect to your companion</Text>
                </View>

                {/* IP Input */}
                <View style={styles.inputSection}>
                    <Text style={styles.label}>Home PC Address</Text>
                    <TextInput
                        style={[
                            styles.input,
                            status === "error" && styles.inputError,
                            status === "success" && styles.inputSuccess,
                        ]}
                        value={ip}
                        onChangeText={setIp}
                        placeholder="192.168.1.100:8765"
                        placeholderTextColor={colors.textMuted}
                        keyboardType="url"
                        autoCapitalize="none"
                        autoCorrect={false}
                        returnKeyType="go"
                        onSubmitEditing={handleTest}
                    />
                    <Text style={styles.hint}>
                        Find this in your Valhalla dashboard → Settings
                    </Text>
                </View>

                {/* Error Message */}
                {status === "error" && errorMsg ? (
                    <View style={styles.errorBox}>
                        <Text style={styles.errorText}>⚠️ {errorMsg}</Text>
                    </View>
                ) : null}

                {/* Success Message */}
                {status === "success" && (
                    <View style={styles.successBox}>
                        <Text style={styles.successText}>✅ Connected! Loading your companion...</Text>
                    </View>
                )}

                {/* Test Button */}
                <TouchableOpacity
                    style={[
                        styles.button,
                        status === "testing" && styles.buttonDisabled,
                        status === "success" && styles.buttonSuccess,
                    ]}
                    onPress={handleTest}
                    disabled={status === "testing" || status === "success"}
                    activeOpacity={0.7}
                >
                    {status === "testing" ? (
                        <ActivityIndicator size="small" color={colors.bgPrimary} />
                    ) : (
                        <Text style={styles.buttonText}>
                            {status === "success" ? "✅ Connected" : "🔗 Test Connection"}
                        </Text>
                    )}
                </TouchableOpacity>

                <Text style={styles.tip}>
                    Make sure your home PC is running Bifrost{"\n"}and you're on the same network.
                </Text>

                {/* Privacy Policy link */}
                <TouchableOpacity
                    onPress={() => router.push("/privacy")}
                    style={styles.privacyLink}
                    activeOpacity={0.7}
                >
                    <Text style={styles.privacyText}>Privacy Policy</Text>
                </TouchableOpacity>
            </View>
        </KeyboardAvoidingView>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: colors.bgPrimary,
    },
    inner: {
        flex: 1,
        justifyContent: "center",
        paddingHorizontal: spacing.xxl,
    },
    header: {
        alignItems: "center",
        marginBottom: spacing.xxxl + 8,
    },
    logo: {
        fontSize: 48,
        marginBottom: spacing.sm,
    },
    title: {
        fontFamily: "Inter_700Bold",
        fontSize: fontSize.hero,
        color: colors.textPrimary,
        letterSpacing: 1,
    },
    subtitle: {
        fontFamily: "Inter_400Regular",
        fontSize: fontSize.md,
        color: colors.textDim,
        marginTop: spacing.xs,
    },
    inputSection: {
        marginBottom: spacing.lg,
    },
    label: {
        fontFamily: "Inter_500Medium",
        fontSize: fontSize.sm,
        color: colors.textSecondary,
        marginBottom: spacing.sm,
    },
    input: {
        backgroundColor: colors.bgInput,
        borderWidth: 1,
        borderColor: colors.glassBorder,
        borderRadius: borderRadius.md,
        paddingHorizontal: spacing.lg,
        paddingVertical: spacing.lg,
        fontFamily: "Inter_400Regular",
        fontSize: fontSize.lg,
        color: colors.textPrimary,
    },
    inputError: {
        borderColor: colors.danger,
    },
    inputSuccess: {
        borderColor: colors.neon,
    },
    hint: {
        fontFamily: "Inter_400Regular",
        fontSize: fontSize.xs,
        color: colors.textMuted,
        marginTop: spacing.sm,
    },
    errorBox: {
        backgroundColor: "rgba(255, 68, 102, 0.08)",
        borderRadius: borderRadius.sm,
        padding: spacing.md,
        marginBottom: spacing.lg,
    },
    errorText: {
        fontFamily: "Inter_400Regular",
        fontSize: fontSize.sm,
        color: colors.danger,
    },
    successBox: {
        backgroundColor: colors.neonGlow,
        borderRadius: borderRadius.sm,
        padding: spacing.md,
        marginBottom: spacing.lg,
    },
    successText: {
        fontFamily: "Inter_400Regular",
        fontSize: fontSize.sm,
        color: colors.neon,
    },
    button: {
        backgroundColor: colors.neon,
        borderRadius: borderRadius.md,
        paddingVertical: spacing.lg,
        alignItems: "center",
        marginBottom: spacing.xl,
    },
    buttonDisabled: {
        opacity: 0.6,
    },
    buttonSuccess: {
        backgroundColor: colors.neon,
    },
    buttonText: {
        fontFamily: "Inter_600SemiBold",
        fontSize: fontSize.lg,
        color: colors.bgPrimary,
    },
    tip: {
        fontFamily: "Inter_400Regular",
        fontSize: fontSize.xs,
        color: colors.textMuted,
        textAlign: "center",
        lineHeight: 18,
    },
    privacyLink: {
        marginTop: spacing.lg,
        alignItems: "center",
    },
    privacyText: {
        fontFamily: "Inter_400Regular",
        fontSize: fontSize.xs,
        color: colors.textDim,
        textDecorationLine: "underline",
    },
});
