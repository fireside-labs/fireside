/**
 * Root layout — Expo Router entry point.
 *
 * Loads the Inter font, sets status bar to light, and wraps
 * the app in the connection provider.
 */
import { useEffect, useState } from "react";
import { View, ActivityIndicator, StyleSheet } from "react-native";
import * as Notifications from "expo-notifications";
import { Slot, useRouter, useSegments } from "expo-router";
import { StatusBar } from "expo-status-bar";
import {
    useFonts,
    Inter_400Regular,
    Inter_500Medium,
    Inter_600SemiBold,
    Inter_700Bold,
} from "@expo-google-fonts/inter";
import { hasOnboarded } from "./onboarding";
import { registerForPushNotifications, getNotificationRoute } from "../src/notifications";
import { ModeProvider } from "../src/ModeContext";
import { AgentProvider } from "../src/AgentContext";
import { colors } from "../src/theme";

export default function RootLayout() {
    const [fontsLoaded] = useFonts({
        Inter_400Regular,
        Inter_500Medium,
        Inter_600SemiBold,
        Inter_700Bold,
    });

    const [isReady, setIsReady] = useState(false);
    const [needsOnboarding, setNeedsOnboarding] = useState(false);
    const router = useRouter();
    const segments = useSegments();

    useEffect(() => {
        (async () => {
            const onboarded = await hasOnboarded();
            setNeedsOnboarding(!onboarded);
            setIsReady(true);
        })();
    }, []);

    // Register for push notifications after onboarding
    useEffect(() => {
        if (!isReady || needsOnboarding) return;
        registerForPushNotifications();
    }, [isReady, needsOnboarding]);

    // Handle notification tap — navigate to relevant tab
    useEffect(() => {
        const sub = Notifications.addNotificationResponseReceivedListener((response) => {
            const data = response.notification.request.content.data || {};
            const route = getNotificationRoute(data);
            router.push(route as any);
        });
        return () => sub.remove();
    }, [router]);

    // Redirect to onboarding if needed
    useEffect(() => {
        if (!isReady || !fontsLoaded) return;
        const inOnboarding = segments[0] === "onboarding";
        if (needsOnboarding && !inOnboarding) {
            router.replace("/onboarding");
        } else if (!needsOnboarding && inOnboarding) {
            router.replace("/(tabs)/care");
        }
    }, [isReady, fontsLoaded, needsOnboarding, segments, router]);

    if (!fontsLoaded || !isReady) {
        return (
            <View style={styles.loading}>
                <ActivityIndicator size="large" color={colors.neon} />
                <StatusBar style="light" />
            </View>
        );
    }

    return (
        <ModeProvider>
            <AgentProvider>
                <View style={styles.container}>
                    <StatusBar style="light" />
                    <Slot />
                </View>
            </AgentProvider>
        </ModeProvider>
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
