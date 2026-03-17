/**
 * Tab layout — Mode-aware bottom tab navigator.
 *
 * Companion Mode: 🏠 Care | 💬 Chat | 🧠 Brain | ⚡ Skills | 🎭 More
 * Executive Mode: 💬 Chat | 🔧 Tools | 📋 Tasks | 🧠 Brain | 🎭 More
 *
 * "More" gives access to: Tasks, Quest, Bag, Marketplace, Personality.
 * Screens without a tab bar entry are still navigable but hidden from the bar.
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
            {/* ── Both modes ── */}
            <Tabs.Screen
                name="care"
                options={{
                    title: isPetMode ? "Home" : "Home",
                    tabBarIcon: ({ focused }) => (
                        <Text style={[styles.icon, focused && styles.iconActive]}>🏠</Text>
                    ),
                }}
            />
            <Tabs.Screen
                name="chat"
                options={{
                    title: "Chat",
                    tabBarIcon: ({ focused }) => (
                        <Text style={[styles.icon, focused && styles.iconActive]}>💬</Text>
                    ),
                }}
            />

            {/* ── Tools (Executive only in tab bar) ── */}
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

            {/* ── Brain ── */}
            <Tabs.Screen
                name="brain"
                options={{
                    title: "Brain",
                    tabBarIcon: ({ focused }) => (
                        <Text style={[styles.icon, focused && styles.iconActive]}>🧠</Text>
                    ),
                }}
            />

            {/* ── Skills (Companion mode in tab bar) / Tasks (Executive mode in tab bar) ── */}
            <Tabs.Screen
                name="skills"
                options={{
                    title: "Skills",
                    tabBarIcon: ({ focused }) => (
                        <Text style={[styles.icon, focused && styles.iconActive]}>⚡</Text>
                    ),
                    href: isPetMode ? "/(tabs)/skills" : null,
                }}
            />
            <Tabs.Screen
                name="tasks"
                options={{
                    title: "Tasks",
                    tabBarIcon: ({ focused }) => (
                        <Text style={[styles.icon, focused && styles.iconActive]}>📋</Text>
                    ),
                    href: isPetMode ? null : "/(tabs)/tasks",
                }}
            />

            {/* ── Personality (both modes, last tab) ── */}
            <Tabs.Screen
                name="personality"
                options={{
                    title: "Soul",
                    tabBarIcon: ({ focused }) => (
                        <Text style={[styles.icon, focused && styles.iconActive]}>🎭</Text>
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
