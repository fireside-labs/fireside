/**
 * Push Notifications.
 *
 * Registers for Expo push notifications, sends token to backend,
 * and handles notification tap routing.
 */
import { Platform } from "react-native";
import * as Notifications from "expo-notifications";
import * as Device from "expo-device";
import Constants from "expo-constants";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { companionAPI } from "./api";

const PUSH_TOKEN_KEY = "valhalla_push_token";

// Configure foreground notification behavior
Notifications.setNotificationHandler({
    handleNotification: async () => ({
        shouldShowAlert: true,
        shouldPlaySound: true,
        shouldSetBadge: false,
        shouldShowBanner: true,
        shouldShowList: true,
    }),
});

/**
 * Register for push notifications:
 * 1. Check if physical device
 * 2. Request permissions
 * 3. Get Expo push token
 * 4. Send to backend
 */
export async function registerForPushNotifications(): Promise<string | null> {
    if (!Device.isDevice) {
        console.log("Push notifications require a physical device");
        return null;
    }

    const { status: existingStatus } = await Notifications.getPermissionsAsync();
    let finalStatus = existingStatus;

    if (existingStatus !== "granted") {
        const { status } = await Notifications.requestPermissionsAsync();
        finalStatus = status;
    }

    if (finalStatus !== "granted") {
        console.log("Push notification permission denied");
        return null;
    }

    // Get the Expo push token
    const projectId = Constants.expoConfig?.extra?.eas?.projectId;
    const tokenData = await Notifications.getExpoPushTokenAsync({
        projectId: projectId || undefined,
    });
    const token = tokenData.data;

    // Save locally
    await AsyncStorage.setItem(PUSH_TOKEN_KEY, token);

    // Register with backend
    try {
        await companionAPI.registerPush(token);
    } catch {
        // Will retry on next app launch
    }

    // Android channel
    if (Platform.OS === "android") {
        await Notifications.setNotificationChannelAsync("default", {
            name: "Companion",
            importance: Notifications.AndroidImportance.DEFAULT,
            vibrationPattern: [0, 250, 250, 250],
        });
    }

    return token;
}

/**
 * Unregister push notifications.
 */
export async function unregisterPushNotifications(): Promise<void> {
    try {
        const token = await AsyncStorage.getItem(PUSH_TOKEN_KEY);
        if (token) {
            await companionAPI.unregisterPush(token);
        }
        await AsyncStorage.removeItem(PUSH_TOKEN_KEY);
    } catch {
        // silently fail
    }
}

/**
 * Map notification data to a tab route.
 * Returns the route to navigate to when the notification is tapped.
 */
export function getNotificationRoute(
    data: Record<string, unknown>
): string {
    const type = data?.type as string;
    switch (type) {
        case "misses_you":
        case "surprise":
        case "gift":
        case "leveled_up":
            return "/(tabs)/care";
        case "task_done":
            return "/(tabs)/tasks";
        default:
            return "/(tabs)/care";
    }
}

/**
 * Check if push notifications are currently enabled.
 */
export async function isPushEnabled(): Promise<boolean> {
    const token = await AsyncStorage.getItem(PUSH_TOKEN_KEY);
    return !!token;
}
