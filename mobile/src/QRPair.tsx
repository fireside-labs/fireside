/**
 * 📱 QR Code Scanner + PIN Pairing.
 *
 * Three ways to connect:
 *   1. Scan QR code from desktop dashboard (instant)
 *   2. Enter 6-digit PIN from mesh join flow (like Bluetooth pairing)
 *   3. Manual IP entry (fallback)
 */
import { useState, useEffect } from "react";
import {
    View,
    Text,
    TouchableOpacity,
    TextInput,
    StyleSheet,
    Alert,
    ActivityIndicator,
} from "react-native";
import { CameraView, useCameraPermissions } from "expo-camera";
import * as Haptics from "expo-haptics";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { setHost, testConnection, discoverFireside } from "./api";
import { colors, spacing, borderRadius, fontSize, shadows } from "./theme";

interface QRPairProps {
    onPaired: () => void;
}

export default function QRPair({ onPaired }: QRPairProps) {
    const [permission, requestPermission] = useCameraPermissions();
    const [scanning, setScanning] = useState(false);
    const [manualIP, setManualIP] = useState("");
    const [pin, setPin] = useState("");
    const [connecting, setConnecting] = useState(false);
    const [discovering, setDiscovering] = useState(false);
    const [error, setError] = useState("");

    const handleBarCodeScanned = async ({ data }: { data: string }) => {
        if (connecting) return;
        setScanning(false);
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);

        try {
            const parsed = JSON.parse(data);
            if (parsed.host) {
                setConnecting(true);
                setError("");
                await setHost(parsed.host);

                // Store pairing token/PIN if present
                if (parsed.token) {
                    await AsyncStorage.setItem("pairingToken", parsed.token);
                }
                if (parsed.pin) {
                    await AsyncStorage.setItem("pairingPin", parsed.pin);
                }

                const ok = await testConnection();
                if (ok) {
                    onPaired();
                } else {
                    setError("Connected but verification failed. Try again.");
                    setConnecting(false);
                }
            } else {
                setError("Invalid QR code — missing host info.");
            }
        } catch {
            setError("Could not read QR code. Try manual IP entry.");
        }
    };

    const handlePinConnect = async () => {
        const cleanPin = pin.trim();
        if (cleanPin.length !== 6) {
            setError("PIN must be 6 digits");
            return;
        }

        setDiscovering(true);
        setError("");
        Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);

        try {
            // Auto-discover the desktop on the LAN
            const discovered = await discoverFireside();

            if (discovered) {
                // Found a Fireside instance — try to connect
                await setHost(discovered.ip);

                // Validate the PIN against the mesh join endpoint
                const ok = await testConnection();
                if (ok) {
                    // Store PIN for future reference
                    await AsyncStorage.setItem("pairingPin", cleanPin);
                    Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
                    onPaired();
                    return;
                }
            }

            setError("Could not find your PC on the network. Make sure both devices are on the same WiFi.");
        } catch {
            setError("Discovery failed. Try entering the IP manually.");
        } finally {
            setDiscovering(false);
        }
    };

    const handleManualConnect = async () => {
        const ip = manualIP.trim();
        if (!ip) return;

        setConnecting(true);
        setError("");
        Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);

        await setHost(ip);
        const ok = await testConnection();
        if (ok) {
            onPaired();
        } else {
            setError("Could not connect. Check the IP and make sure your PC is running Fireside.");
            setConnecting(false);
        }
    };

    const startScanning = async () => {
        if (!permission?.granted) {
            const result = await requestPermission();
            if (!result.granted) {
                Alert.alert("Camera Required", "Camera access is needed to scan the QR code.");
                return;
            }
        }
        setScanning(true);
        setError("");
    };

    if (scanning) {
        return (
            <View style={styles.scanContainer}>
                <CameraView
                    style={styles.camera}
                    barcodeScannerSettings={{ barcodeTypes: ["qr"] }}
                    onBarcodeScanned={handleBarCodeScanned}
                />
                <View style={styles.overlay}>
                    <View style={styles.scanFrame} />
                    <Text style={styles.scanText}>Point at QR code on your desktop</Text>
                </View>
                <TouchableOpacity
                    style={styles.cancelScan}
                    onPress={() => setScanning(false)}
                    activeOpacity={0.7}
                >
                    <Text style={styles.cancelScanText}>Cancel</Text>
                </TouchableOpacity>
            </View>
        );
    }

    return (
        <View style={styles.container}>
            <Text style={styles.title}>📱 Connect to Your PC</Text>
            <Text style={styles.subtitle}>
                Open your Fireside dashboard and go to Settings → Pair Phone
            </Text>

            {/* QR Scan button */}
            <TouchableOpacity
                style={styles.qrBtn}
                onPress={startScanning}
                activeOpacity={0.7}
            >
                <Text style={styles.qrBtnEmoji}>📷</Text>
                <Text style={styles.qrBtnText}>Scan QR Code</Text>
                <Text style={styles.qrBtnHint}>Fastest way to connect</Text>
            </TouchableOpacity>

            <View style={styles.divider}>
                <View style={styles.dividerLine} />
                <Text style={styles.dividerText}>or</Text>
                <View style={styles.dividerLine} />
            </View>

            {/* 6-digit PIN entry */}
            <Text style={styles.manualLabel}>Enter 6-digit PIN from your desktop:</Text>
            <TextInput
                style={styles.pinInput}
                value={pin}
                onChangeText={(t) => setPin(t.replace(/[^0-9]/g, "").slice(0, 6))}
                placeholder="000000"
                placeholderTextColor={colors.textMuted}
                keyboardType="number-pad"
                maxLength={6}
                autoCorrect={false}
                textAlign="center"
                onSubmitEditing={handlePinConnect}
                returnKeyType="go"
            />
            <TouchableOpacity
                style={[styles.connectBtn, styles.pinBtn, (discovering || pin.length !== 6) && { opacity: 0.4 }]}
                onPress={handlePinConnect}
                disabled={discovering || pin.length !== 6}
                activeOpacity={0.7}
            >
                {discovering ? (
                    <View style={styles.discoveringRow}>
                        <ActivityIndicator size="small" color={colors.neon} />
                        <Text style={[styles.connectBtnText, { marginLeft: spacing.sm }]}>
                            Finding your PC...
                        </Text>
                    </View>
                ) : (
                    <Text style={styles.connectBtnText}>Connect with PIN</Text>
                )}
            </TouchableOpacity>

            <View style={styles.divider}>
                <View style={styles.dividerLine} />
                <Text style={styles.dividerText}>or</Text>
                <View style={styles.dividerLine} />
            </View>

            {/* Manual IP entry */}
            <Text style={styles.manualLabel}>Enter your PC's IP manually:</Text>
            <TextInput
                style={styles.ipInput}
                value={manualIP}
                onChangeText={setManualIP}
                placeholder="192.168.1.100:8765"
                placeholderTextColor={colors.textMuted}
                keyboardType="url"
                autoCapitalize="none"
                autoCorrect={false}
                onSubmitEditing={handleManualConnect}
                returnKeyType="go"
            />

            <TouchableOpacity
                style={[styles.connectBtn, (connecting || !manualIP.trim()) && { opacity: 0.4 }]}
                onPress={handleManualConnect}
                disabled={connecting || !manualIP.trim()}
                activeOpacity={0.7}
            >
                <Text style={styles.connectBtnText}>
                    {connecting ? "Connecting..." : "Connect"}
                </Text>
            </TouchableOpacity>

            {error ? <Text style={styles.errorText}>{error}</Text> : null}
        </View>
    );
}

const styles = StyleSheet.create({
    container: { padding: spacing.xl },
    title: { fontFamily: "Inter_700Bold", fontSize: fontSize.xl, color: colors.textPrimary, textAlign: "center", marginBottom: spacing.xs },
    subtitle: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.textDim, textAlign: "center", marginBottom: spacing.xl },
    // QR button
    qrBtn: { backgroundColor: colors.neonGlow, borderWidth: 1, borderColor: colors.neon, borderRadius: borderRadius.lg, padding: spacing.xl, alignItems: "center", marginBottom: spacing.lg, ...shadows.glow },
    qrBtnEmoji: { fontSize: 40, marginBottom: spacing.sm },
    qrBtnText: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.md, color: colors.textPrimary },
    qrBtnHint: { fontFamily: "Inter_400Regular", fontSize: fontSize.tiny, color: colors.neon, marginTop: spacing.xs },
    // Divider
    divider: { flexDirection: "row", alignItems: "center", marginBottom: spacing.lg },
    dividerLine: { flex: 1, height: 1, backgroundColor: colors.glassBorder },
    dividerText: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.textMuted, paddingHorizontal: spacing.md },
    // PIN
    pinInput: { backgroundColor: colors.bgInput, borderRadius: borderRadius.md, borderWidth: 1, borderColor: colors.neon, paddingHorizontal: spacing.lg, paddingVertical: spacing.md + 4, fontFamily: "Inter_700Bold", fontSize: 28, color: colors.textPrimary, marginBottom: spacing.md, letterSpacing: 12 },
    pinBtn: { borderColor: colors.neon, borderWidth: 1, backgroundColor: colors.neonGlow },
    discoveringRow: { flexDirection: "row", alignItems: "center", justifyContent: "center" },
    // Manual
    manualLabel: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.textDim, marginBottom: spacing.sm },
    ipInput: { backgroundColor: colors.bgInput, borderRadius: borderRadius.md, borderWidth: 1, borderColor: colors.glassBorder, paddingHorizontal: spacing.md, paddingVertical: spacing.md, fontFamily: "Inter_400Regular", fontSize: fontSize.sm, color: colors.textPrimary, marginBottom: spacing.md },
    connectBtn: { backgroundColor: colors.bgCard, borderRadius: borderRadius.md, paddingVertical: spacing.md, alignItems: "center", borderWidth: 1, borderColor: colors.glassBorder, marginBottom: spacing.lg },
    connectBtnText: { fontFamily: "Inter_500Medium", fontSize: fontSize.sm, color: colors.textSecondary },
    errorText: { fontFamily: "Inter_400Regular", fontSize: fontSize.tiny, color: "#ef4444", textAlign: "center", marginTop: spacing.md },
    // Scanner
    scanContainer: { flex: 1, backgroundColor: "#000" },
    camera: { flex: 1 },
    overlay: { ...StyleSheet.absoluteFillObject, justifyContent: "center", alignItems: "center" },
    scanFrame: { width: 250, height: 250, borderWidth: 2, borderColor: colors.neon, borderRadius: borderRadius.lg },
    scanText: { fontFamily: "Inter_400Regular", fontSize: fontSize.sm, color: "#fff", marginTop: spacing.lg },
    cancelScan: { position: "absolute", bottom: 60, alignSelf: "center", backgroundColor: "rgba(0,0,0,0.6)", paddingHorizontal: spacing.xl, paddingVertical: spacing.md, borderRadius: borderRadius.full },
    cancelScanText: { fontFamily: "Inter_500Medium", fontSize: fontSize.sm, color: "#fff" },
});

