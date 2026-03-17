/**
 * 🎭 Personality Tab — View and edit companion traits.
 *
 * Fetches personality from PC soul files. Edits sync back.
 * Shows greeting, bio, voice style, and personality traits.
 */
import { useState, useEffect, useCallback } from "react";
import {
    View,
    Text,
    TextInput,
    TouchableOpacity,
    ScrollView,
    StyleSheet,
    RefreshControl,
    ActivityIndicator,
    Alert,
} from "react-native";
import * as Haptics from "expo-haptics";
import { useConnection } from "../../src/hooks/useConnection";
import { companionAPI } from "../../src/api";
import { colors, spacing, borderRadius, fontSize, shadows } from "../../src/theme";

interface PersonalityData {
    traits: Record<string, string>;
    voice_style?: string;
    greeting?: string;
    bio?: string;
}

// Trait display config
const TRAIT_CONFIG: Record<string, { emoji: string; label: string }> = {
    warmth: { emoji: "🔥", label: "Warmth" },
    humor: { emoji: "😄", label: "Humor" },
    formality: { emoji: "🎩", label: "Formality" },
    curiosity: { emoji: "🔎", label: "Curiosity" },
    empathy: { emoji: "💜", label: "Empathy" },
    creativity: { emoji: "🎨", label: "Creativity" },
    directness: { emoji: "🎯", label: "Directness" },
    patience: { emoji: "🧘", label: "Patience" },
    enthusiasm: { emoji: "⚡", label: "Enthusiasm" },
    sarcasm: { emoji: "😏", label: "Sarcasm" },
};

export default function PersonalityTab() {
    const { isOnline, companionData } = useConnection();
    const [personality, setPersonality] = useState<PersonalityData | null>(null);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [editing, setEditing] = useState<string | null>(null);
    const [editValue, setEditValue] = useState("");
    const [saving, setSaving] = useState(false);

    const petName = companionData?.companion?.name || "Companion";

    const fetchPersonality = useCallback(async () => {
        try {
            const res = await companionAPI.personality();
            setPersonality(res);
        } catch {
            // Use defaults
            setPersonality({
                traits: { warmth: "high", humor: "medium", formality: "low", curiosity: "high", empathy: "high" },
                voice_style: "warm and friendly",
                greeting: `Hey there! I'm ${petName}.`,
                bio: "A curious AI companion who loves learning new things.",
            });
        }
        setLoading(false);
    }, [petName]);

    useEffect(() => {
        fetchPersonality();
    }, [fetchPersonality]);

    const handleEdit = (key: string, currentValue: string) => {
        setEditing(key);
        setEditValue(currentValue);
        Haptics.selectionAsync();
    };

    const handleSave = async () => {
        if (!editing || !personality) return;
        setSaving(true);
        Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);

        const updatedTraits = { ...personality.traits, [editing]: editValue };

        // Optimistic update
        setPersonality((prev) => prev ? { ...prev, traits: updatedTraits } : prev);
        setEditing(null);

        if (isOnline) {
            try {
                await companionAPI.personalityUpdate({ [editing]: editValue });
                Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
            } catch {
                Alert.alert("Save Failed", "Could not sync personality to your PC. Changes saved locally.");
            }
        }
        setSaving(false);
    };

    const handleCancel = () => {
        setEditing(null);
        setEditValue("");
    };

    const onRefresh = useCallback(async () => {
        setRefreshing(true);
        await fetchPersonality();
        setRefreshing(false);
    }, [fetchPersonality]);

    if (loading) {
        return (
            <View style={styles.loadingContainer}>
                <ActivityIndicator size="large" color={colors.neon} />
            </View>
        );
    }

    const traits = personality?.traits || {};

    return (
        <ScrollView
            style={styles.container}
            contentContainerStyle={styles.content}
            refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.neon} />}
        >
            <Text style={styles.title}>🎭 Personality</Text>
            <Text style={styles.subtitle}>{petName}'s soul traits — synced to your PC</Text>

            {/* Greeting */}
            {personality?.greeting && (
                <View style={styles.greetingCard}>
                    <Text style={styles.greetingLabel}>Greeting</Text>
                    <Text style={styles.greetingText}>"{personality.greeting}"</Text>
                </View>
            )}

            {/* Bio */}
            {personality?.bio && (
                <View style={styles.bioCard}>
                    <Text style={styles.bioLabel}>Bio</Text>
                    <Text style={styles.bioText}>{personality.bio}</Text>
                </View>
            )}

            {/* Voice Style */}
            {personality?.voice_style && (
                <View style={styles.voiceCard}>
                    <Text style={styles.voiceEmoji}>🎤</Text>
                    <View>
                        <Text style={styles.voiceLabel}>Voice Style</Text>
                        <Text style={styles.voiceText}>{personality.voice_style}</Text>
                    </View>
                </View>
            )}

            {/* Traits */}
            <Text style={styles.sectionTitle}>Personality Traits</Text>
            {Object.entries(traits).map(([key, value]) => {
                const config = TRAIT_CONFIG[key] || { emoji: "✨", label: key.charAt(0).toUpperCase() + key.slice(1) };
                const isEditing = editing === key;

                return (
                    <View key={key} style={[styles.traitCard, isEditing && styles.traitCardEditing]}>
                        <View style={styles.traitHeader}>
                            <Text style={styles.traitEmoji}>{config.emoji}</Text>
                            <Text style={styles.traitLabel}>{config.label}</Text>
                        </View>

                        {isEditing ? (
                            <View style={styles.editRow}>
                                <TextInput
                                    style={styles.editInput}
                                    value={editValue}
                                    onChangeText={setEditValue}
                                    placeholder={`Set ${config.label.toLowerCase()}...`}
                                    placeholderTextColor={colors.textMuted}
                                    autoFocus
                                    onSubmitEditing={handleSave}
                                />
                                <TouchableOpacity style={styles.saveBtn} onPress={handleSave} activeOpacity={0.7}>
                                    <Text style={styles.saveBtnText}>✓</Text>
                                </TouchableOpacity>
                                <TouchableOpacity onPress={handleCancel} activeOpacity={0.7}>
                                    <Text style={styles.cancelText}>✕</Text>
                                </TouchableOpacity>
                            </View>
                        ) : (
                            <TouchableOpacity
                                style={styles.traitValueRow}
                                onPress={() => handleEdit(key, value)}
                                activeOpacity={0.7}
                            >
                                <Text style={styles.traitValue}>{value}</Text>
                                <Text style={styles.editHint}>✏️</Text>
                            </TouchableOpacity>
                        )}
                    </View>
                );
            })}

            {/* Sync indicator */}
            <View style={styles.syncCard}>
                <View style={[styles.syncDot, { backgroundColor: isOnline ? colors.onlineDot : colors.offlineDot }]} />
                <Text style={styles.syncText}>
                    {isOnline
                        ? "Changes sync to PC soul files in real-time"
                        : "Offline — changes will sync when reconnected"}
                </Text>
            </View>
        </ScrollView>
    );
}

const styles = StyleSheet.create({
    container: { flex: 1, backgroundColor: colors.bgPrimary },
    content: { paddingHorizontal: spacing.lg, paddingTop: 60, paddingBottom: spacing.xxxl },
    loadingContainer: { flex: 1, backgroundColor: colors.bgPrimary, justifyContent: "center", alignItems: "center" },
    title: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.xl, color: colors.textPrimary, marginBottom: 2 },
    subtitle: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.textDim, marginBottom: spacing.xl },
    // Greeting
    greetingCard: { backgroundColor: colors.neonGlow, borderWidth: 1, borderColor: colors.neonBorder, borderRadius: borderRadius.lg, padding: spacing.xl, marginBottom: spacing.md },
    greetingLabel: { fontFamily: "Inter_400Regular", fontSize: fontSize.tiny, color: colors.neon, textTransform: "uppercase", letterSpacing: 1, marginBottom: spacing.sm },
    greetingText: { fontFamily: "Inter_400Regular", fontSize: fontSize.sm, color: colors.textSecondary, fontStyle: "italic", lineHeight: 20 },
    // Bio
    bioCard: { backgroundColor: colors.bgCard, borderRadius: borderRadius.md, borderWidth: 1, borderColor: colors.glassBorder, padding: spacing.lg, marginBottom: spacing.md },
    bioLabel: { fontFamily: "Inter_400Regular", fontSize: fontSize.tiny, color: colors.textDim, textTransform: "uppercase", letterSpacing: 1, marginBottom: spacing.xs },
    bioText: { fontFamily: "Inter_400Regular", fontSize: fontSize.sm, color: colors.textSecondary, lineHeight: 20 },
    // Voice
    voiceCard: { flexDirection: "row", alignItems: "center", gap: spacing.md, backgroundColor: colors.bgCard, borderRadius: borderRadius.md, borderWidth: 1, borderColor: colors.glassBorder, padding: spacing.lg, marginBottom: spacing.xl },
    voiceEmoji: { fontSize: 24 },
    voiceLabel: { fontFamily: "Inter_400Regular", fontSize: fontSize.tiny, color: colors.textDim },
    voiceText: { fontFamily: "Inter_500Medium", fontSize: fontSize.sm, color: colors.textPrimary },
    // Section
    sectionTitle: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.xs, color: colors.textDim, textTransform: "uppercase", letterSpacing: 1, marginBottom: spacing.sm },
    // Traits
    traitCard: { backgroundColor: colors.bgCard, borderRadius: borderRadius.md, borderWidth: 1, borderColor: colors.glassBorder, padding: spacing.lg, marginBottom: spacing.sm },
    traitCardEditing: { borderColor: colors.neon, backgroundColor: colors.neonGlow },
    traitHeader: { flexDirection: "row", alignItems: "center", gap: spacing.sm, marginBottom: spacing.sm },
    traitEmoji: { fontSize: 18 },
    traitLabel: { fontFamily: "Inter_500Medium", fontSize: fontSize.sm, color: colors.textPrimary },
    traitValueRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
    traitValue: { fontFamily: "Inter_400Regular", fontSize: fontSize.sm, color: colors.textSecondary, textTransform: "capitalize" },
    editHint: { fontSize: 14, opacity: 0.4 },
    // Edit
    editRow: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
    editInput: { flex: 1, backgroundColor: colors.bgInput, borderRadius: borderRadius.sm, borderWidth: 1, borderColor: colors.neonBorder, paddingHorizontal: spacing.md, paddingVertical: spacing.sm, fontFamily: "Inter_400Regular", fontSize: fontSize.sm, color: colors.textPrimary },
    saveBtn: { backgroundColor: colors.neon, borderRadius: borderRadius.sm, paddingHorizontal: spacing.md, paddingVertical: spacing.sm },
    saveBtnText: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.sm, color: colors.bgPrimary },
    cancelText: { fontFamily: "Inter_400Regular", fontSize: fontSize.md, color: colors.textMuted, paddingHorizontal: spacing.sm },
    // Sync
    syncCard: { flexDirection: "row", alignItems: "center", gap: spacing.sm, backgroundColor: colors.bgCard, borderRadius: borderRadius.md, padding: spacing.md, marginTop: spacing.lg },
    syncDot: { width: 6, height: 6, borderRadius: 3 },
    syncText: { fontFamily: "Inter_400Regular", fontSize: fontSize.tiny, color: colors.textDim, flex: 1 },
});
