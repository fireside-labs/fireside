/**
 * Onboarding Carousel — 3-slide intro before setup screen.
 *
 * Sprint 2: Addresses Valkyrie Finding #1 (users land cold).
 * "Meet your AI companion → It lives on your home PC → Enter the address to connect."
 */
import { useState, useRef } from "react";
import {
    View,
    Text,
    TouchableOpacity,
    FlatList,
    StyleSheet,
    Dimensions,
    Animated,
} from "react-native";
import { useRouter } from "expo-router";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { colors, spacing, borderRadius, fontSize } from "../src/theme";

const { width } = Dimensions.get("window");
const ONBOARDING_KEY = "valhalla_onboarded";

const SLIDES = [
    {
        id: "1",
        emoji: "🐾",
        title: "Meet Your Companion",
        subtitle: "A pocket pet that lives on your home\nserver. Feed it, walk it, chat with it.",
        accent: "Your companion remembers everything.",
    },
    {
        id: "2",
        emoji: "🖥️",
        title: "Runs on Your PC",
        subtitle: "No cloud. No subscriptions.\nYour companion's brain runs locally.",
        accent: "Private by design.",
    },
    {
        id: "3",
        emoji: "📱",
        title: "Connect From Anywhere",
        subtitle: "Enter your home PC's address\nand your companion is in your pocket.",
        accent: "Let's get started.",
    },
];

export default function OnboardingScreen() {
    const [currentIndex, setCurrentIndex] = useState(0);
    const flatListRef = useRef<FlatList>(null);
    const scrollX = useRef(new Animated.Value(0)).current;
    const router = useRouter();

    const handleNext = async () => {
        if (currentIndex < SLIDES.length - 1) {
            flatListRef.current?.scrollToIndex({
                index: currentIndex + 1,
                animated: true,
            });
        } else {
            await AsyncStorage.setItem(ONBOARDING_KEY, "true");
            router.replace("/setup");
        }
    };

    const handleSkip = async () => {
        await AsyncStorage.setItem(ONBOARDING_KEY, "true");
        router.replace("/setup");
    };

    const renderSlide = ({ item }: { item: (typeof SLIDES)[0] }) => (
        <View style={[styles.slide, { width }]}>
            <Text style={styles.slideEmoji}>{item.emoji}</Text>
            <Text style={styles.slideTitle}>{item.title}</Text>
            <Text style={styles.slideSubtitle}>{item.subtitle}</Text>
            <Text style={styles.slideAccent}>{item.accent}</Text>
        </View>
    );

    const isLast = currentIndex === SLIDES.length - 1;

    return (
        <View style={styles.container}>
            {/* Skip button */}
            {!isLast && (
                <TouchableOpacity
                    style={styles.skipBtn}
                    onPress={handleSkip}
                    activeOpacity={0.7}
                >
                    <Text style={styles.skipText}>Skip</Text>
                </TouchableOpacity>
            )}

            {/* Slides */}
            <Animated.FlatList
                ref={flatListRef}
                data={SLIDES}
                renderItem={renderSlide}
                keyExtractor={(item) => item.id}
                horizontal
                pagingEnabled
                showsHorizontalScrollIndicator={false}
                scrollEventThrottle={16}
                onScroll={Animated.event(
                    [{ nativeEvent: { contentOffset: { x: scrollX } } }],
                    { useNativeDriver: false }
                )}
                onMomentumScrollEnd={(e) => {
                    const idx = Math.round(
                        e.nativeEvent.contentOffset.x / width
                    );
                    setCurrentIndex(idx);
                }}
            />

            {/* Bottom */}
            <View style={styles.bottomSection}>
                {/* Dots */}
                <View style={styles.dotsRow}>
                    {SLIDES.map((_, i) => {
                        const inputRange = [
                            (i - 1) * width,
                            i * width,
                            (i + 1) * width,
                        ];
                        const dotWidth = scrollX.interpolate({
                            inputRange,
                            outputRange: [6, 20, 6],
                            extrapolate: "clamp",
                        });
                        const dotOpacity = scrollX.interpolate({
                            inputRange,
                            outputRange: [0.3, 1, 0.3],
                            extrapolate: "clamp",
                        });
                        return (
                            <Animated.View
                                key={i}
                                style={[
                                    styles.dot,
                                    { width: dotWidth, opacity: dotOpacity },
                                ]}
                            />
                        );
                    })}
                </View>

                {/* Next / Get Started */}
                <TouchableOpacity
                    style={styles.nextBtn}
                    onPress={handleNext}
                    activeOpacity={0.7}
                >
                    <Text style={styles.nextText}>
                        {isLast ? "Get Started →" : "Next"}
                    </Text>
                </TouchableOpacity>
            </View>
        </View>
    );
}

/** Check if user has completed onboarding. */
export async function hasOnboarded(): Promise<boolean> {
    const val = await AsyncStorage.getItem(ONBOARDING_KEY);
    return val === "true";
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: colors.bgPrimary,
    },
    skipBtn: {
        position: "absolute",
        top: 60,
        right: spacing.xxl,
        zIndex: 10,
    },
    skipText: {
        fontFamily: "Inter_400Regular",
        fontSize: fontSize.sm,
        color: colors.textDim,
    },
    slide: {
        flex: 1,
        justifyContent: "center",
        alignItems: "center",
        paddingHorizontal: spacing.xxxl,
    },
    slideEmoji: {
        fontSize: 72,
        marginBottom: spacing.xxl,
    },
    slideTitle: {
        fontFamily: "Inter_700Bold",
        fontSize: fontSize.hero,
        color: colors.textPrimary,
        textAlign: "center",
        marginBottom: spacing.md,
    },
    slideSubtitle: {
        fontFamily: "Inter_400Regular",
        fontSize: fontSize.md,
        color: colors.textSecondary,
        textAlign: "center",
        lineHeight: 22,
        marginBottom: spacing.lg,
    },
    slideAccent: {
        fontFamily: "Inter_500Medium",
        fontSize: fontSize.sm,
        color: colors.neon,
        textAlign: "center",
    },
    bottomSection: {
        paddingHorizontal: spacing.xxl,
        paddingBottom: 50,
        alignItems: "center",
    },
    dotsRow: {
        flexDirection: "row",
        alignItems: "center",
        marginBottom: spacing.xl,
        gap: spacing.sm,
    },
    dot: {
        height: 6,
        borderRadius: 3,
        backgroundColor: colors.neon,
    },
    nextBtn: {
        backgroundColor: colors.neon,
        borderRadius: borderRadius.md,
        paddingVertical: spacing.lg,
        paddingHorizontal: spacing.xxxl + 16,
        alignItems: "center",
        width: "100%",
    },
    nextText: {
        fontFamily: "Inter_600SemiBold",
        fontSize: fontSize.lg,
        color: colors.bgPrimary,
    },
});
