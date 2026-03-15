/**
 * Tab layout — Bottom tab navigator with 5 tabs.
 *
 * 💬 Chat | 🐾 Care | 🎒 Bag | 📋 Tasks | ⚔️ Quest
 */
import { Tabs } from "expo-router";
import { View, Text, StyleSheet } from "react-native";
import { colors, fontSize } from "../../src/theme";

export default function TabsLayout() {
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
                }}
            />
            <Tabs.Screen
                name="bag"
                options={{
                    title: "Bag",
                    tabBarIcon: ({ focused }) => (
                        <Text style={[styles.icon, focused && styles.iconActive]}>🎒</Text>
                    ),
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
