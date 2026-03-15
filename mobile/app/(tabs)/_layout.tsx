/**
 * Tab layout — Mode-aware bottom tab navigator.
 *
 * Companion Mode: 💬 Chat | 🐾 Care | 🎒 Bag | 📋 Tasks | ⚔️ Quest
 * Executive Mode: 💬 Chat | 🔧 Tools | 📋 Tasks
 *
 * Sprint 5: Mode toggle via ModeContext.
 * Sprint 8: Renamed Pet→Companion, Tool→Executive (display only).
 */
import { Tabs } from "expo-router";
import { Text, StyleSheet } from "react-native";
import { useMode } from "../../src/ModeContext";
import { colors, fontSize } from "../../src/theme";

export default function TabsLayout() {
    const { isPetMode } = useMode();

    return (
        <Tabs
            screenOptions={{
                headerShown: false,
                tabBarStyle: styles.tabBar,
                tabBarActiveTintColor: colors.tabActive,
                tabBarInactiveTintColor: colors.tabInactive,
                tabBarLabelStyle: styles.tabLabel,
            }}
        >
            <Tabs.Screen
                name="chat"
                options={{
                    title: "Chat",
                    tabBarIcon: ({ focused }) => (
                        <Text style={[styles.icon, focused && styles.iconActive]}>💬</Text>
                    ),
                }}
            />
            <Tabs.Screen
                name="care"
                options={{
                    title: "Care",
                    tabBarIcon: ({ focused }) => (
                        <Text style={[styles.icon, focused && styles.iconActive]}>🐾</Text>
                    ),
                    href: isPetMode ? "/(tabs)/care" : null,
                }}
            />
            <Tabs.Screen
                name="tools"
                options={{
                    title: "Tools",
                    tabBarIcon: ({ focused }) => (
                        <Text style={[styles.icon, focused && styles.iconActive]}>🔧</Text>
                    ),
                    href: isPetMode ? null : "/(tabs)/tools",
                }}
            />
            <Tabs.Screen
                name="bag"
                options={{
                    title: "Bag",
                    tabBarIcon: ({ focused }) => (
                        <Text style={[styles.icon, focused && styles.iconActive]}>🎒</Text>
                    ),
                    href: isPetMode ? "/(tabs)/bag" : null,
                }}
            />
            <Tabs.Screen
                name="tasks"
                options={{
                    title: "Tasks",
                    tabBarIcon: ({ focused }) => (
                        <Text style={[styles.icon, focused && styles.iconActive]}>📋</Text>
                    ),
                }}
            />
            <Tabs.Screen
                name="quest"
                options={{
                    title: "Quest",
                    tabBarIcon: ({ focused }) => (
                        <Text style={[styles.icon, focused && styles.iconActive]}>⚔️</Text>
                    ),
                    href: isPetMode ? "/(tabs)/quest" : null,
                }}
            />
            <Tabs.Screen
                name="marketplace"
                options={{
                    title: "Market",
                    tabBarIcon: ({ focused }) => (
                        <Text style={[styles.icon, focused && styles.iconActive]}>🛒</Text>
                    ),
                }}
            />
        </Tabs>
    );
}

const styles = StyleSheet.create({
    tabBar: {
        backgroundColor: colors.tabBg,
        borderTopColor: colors.glassBorder,
        borderTopWidth: 1,
        height: 80,
        paddingBottom: 20,
        paddingTop: 8,
    },
    tabLabel: {
        fontFamily: "Inter_500Medium",
        fontSize: fontSize.tiny,
        marginTop: 2,
    },
    icon: {
        fontSize: 22,
        opacity: 0.5,
    },
    iconActive: {
        opacity: 1,
    },
});
