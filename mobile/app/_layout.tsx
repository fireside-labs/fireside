/**
 * Root layout — Expo Router entry point.
 *
 * Loads the Inter font, sets status bar to light, and wraps
 * the app in the connection provider.
 */
import { useEffect, useState } from "react";
import { View, ActivityIndicator, StyleSheet } from "react-native";
import { Slot, useRouter, useSegments } from "expo-router";
import { StatusBar } from "expo-status-bar";
import {
    useFonts,
    Inter_400Regular,
    Inter_500Medium,
    Inter_600SemiBold,
    Inter_700Bold,
} from "@expo-google-fonts/inter";
import { getHost } from "../src/api";
import { colors } from "../src/theme";

export default function RootLayout() {
    const [fontsLoaded] = useFonts({
        Inter_400Regular,
        Inter_500Medium,
        Inter_600SemiBold,
        Inter_700Bold,
    });

    const [isReady, setIsReady] = useState(false);
    const [needsSetup, setNeedsSetup] = useState(false);
    const router = useRouter();
    const segments = useSegments();

    useEffect(() => {
        (async () => {
            const host = await getHost();
            setNeedsSetup(!host);
            setIsReady(true);
        })();
    }, []);

    // Redirect to setup if no host configured
    useEffect(() => {
        if (!isReady || !fontsLoaded) return;
        const inSetup = segments[0] === "setup";
        if (needsSetup && !inSetup) {
            router.replace("/setup");
        } else if (!needsSetup && inSetup) {
            router.replace("/(tabs)/care");
        }
    }, [isReady, fontsLoaded, needsSetup, segments, router]);

    if (!fontsLoaded || !isReady) {
        return (
            <View style={styles.loading}>
                <ActivityIndicator size="large" color={colors.neon} />
                <StatusBar style="light" />
            </View>
        );
    }

    return (
        <View style={styles.container}>
            <StatusBar style="light" />
            <Slot />
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: colors.bgPrimary,
    },
    loading: {
        flex: 1,
        backgroundColor: colors.bgPrimary,
        justifyContent: "center",
        alignItems: "center",
    },
});
