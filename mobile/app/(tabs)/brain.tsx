/**
 * 🧠 Brain Tab — Remote model management.
 *
 * View currently loaded model on PC, switch models from the
 * brain-installer registry (30+ models). Shows GPU/VRAM info.
 */
import { useState, useEffect, useCallback } from "react";
import {
    View,
    Text,
    TouchableOpacity,
    ScrollView,
    StyleSheet,
    RefreshControl,
    ActivityIndicator,
} from "react-native";
import * as Haptics from "expo-haptics";
import { useConnection } from "../../src/hooks/useConnection";
import { companionAPI } from "../../src/api";
import { colors, spacing, borderRadius, fontSize, shadows } from "../../src/theme";

interface ModelInfo {
    id: string;
    name: string;
    size: string;
    quantization: string;
    loaded: boolean;
    vram_required?: string;
}

export default function BrainTab() {
    const { isOnline } = useConnection();
    const [models, setModels] = useState<ModelInfo[]>([]);
    const [activeModel, setActiveModel] = useState<string>("");
    const [activeBackend, setActiveBackend] = useState<string>("llama.cpp");
    const [contextLength, setContextLength] = useState<number | null>(null);
    const [loading, setLoading] = useState(true);
    const [switching, setSwitching] = useState<string | null>(null);
    const [refreshing, setRefreshing] = useState(false);

    const fetchData = useCallback(async () => {
        try {
            const [modelsRes, activeRes] = await Promise.all([
                companionAPI.brainModels(),
                companionAPI.brainActive(),
            ]);
            setModels(modelsRes.models || []);
            setActiveModel(activeRes.model || "");
            setActiveBackend(activeRes.backend || "llama.cpp");
            setContextLength(activeRes.context_length || null);
        } catch {
            // Offline — show placeholder
        }
        setLoading(false);
    }, []);

    useEffect(() => {
        if (isOnline) fetchData();
        else setLoading(false);
    }, [isOnline, fetchData]);

    const handleSwitch = async (modelId: string) => {
        if (switching || modelId === activeModel) return;
        setSwitching(modelId);
        Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
        try {
            const res = await companionAPI.brainSwitch(modelId);
            if (res.ok) {
                setActiveModel(res.model);
                Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
            }
        } catch { }
        setSwitching(null);
    };

    const onRefresh = useCallback(async () => {
        setRefreshing(true);
        await fetchData();
        setRefreshing(false);
    }, [fetchData]);

    return (
        <ScrollView
            style={styles.container}
            contentContainerStyle={styles.content}
            refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.neon} />}
        >
            <Text style={styles.title}>🧠 Brain</Text>
            <Text style={styles.subtitle}>Manage the AI model running on your home PC</Text>

            {/* Active Model */}
            <View style={styles.activeCard}>
                <Text style={styles.activeLabel}>Currently Active</Text>
                {activeModel ? (
                    <>
                        <Text style={styles.activeModel}>{activeModel}</Text>
                        <View style={styles.activeDetails}>
                            <Text style={styles.activeStat}>⚡ {activeBackend}</Text>
                            {contextLength && <Text style={styles.activeStat}>📐 {contextLength.toLocaleString()} ctx</Text>}
                        </View>
                    </>
                ) : (
                    <Text style={styles.offlineText}>
                        {isOnline ? "Loading..." : "Connect to your PC to see model info"}
                    </Text>
                )}
                <View style={[styles.statusDot, { backgroundColor: isOnline ? colors.onlineDot : colors.offlineDot }]} />
            </View>

            {/* Model List */}
            {loading ? (
                <ActivityIndicator color={colors.neon} style={{ marginTop: spacing.xl }} />
            ) : !isOnline ? (
                <View style={styles.offlineCard}>
                    <Text style={styles.offlineEmoji}>📡</Text>
                    <Text style={styles.offlineTitle}>PC Offline</Text>
                    <Text style={styles.offlineDesc}>
                        Model switching requires your home PC to be online.
                        Your companion will use on-device inference when available.
                    </Text>
                </View>
            ) : (
                <>
                    <Text style={styles.sectionTitle}>Available Models</Text>
                    {models.map((model) => {
                        const isActive = model.id === activeModel || model.loaded;
                        const isSwitching = switching === model.id;
                        return (
                            <TouchableOpacity
                                key={model.id}
                                style={[styles.modelCard, isActive && styles.modelCardActive]}
                                onPress={() => handleSwitch(model.id)}
                                disabled={isActive || !!switching}
                                activeOpacity={0.7}
                            >
                                <View style={styles.modelHeader}>
                                    <View style={styles.modelInfo}>
                                        <Text style={styles.modelName}>{model.name}</Text>
                                        <View style={styles.modelTags}>
                                            <Text style={styles.modelTag}>{model.size}</Text>
                                            <Text style={styles.modelTag}>{model.quantization}</Text>
                                            {model.vram_required && (
                                                <Text style={styles.modelTag}>🎮 {model.vram_required}</Text>
                                            )}
                                        </View>
                                    </View>
                                    {isActive ? (
                                        <Text style={styles.activeBadge}>✅ Active</Text>
                                    ) : isSwitching ? (
                                        <ActivityIndicator size="small" color={colors.neon} />
                                    ) : (
                                        <Text style={styles.switchText}>Switch →</Text>
                                    )}
                                </View>
                            </TouchableOpacity>
                        );
                    })}
                </>
            )}

            {/* Info */}
            <View style={styles.infoCard}>
                <Text style={styles.infoText}>
                    🔒 Models run entirely on your home PC via llama.cpp.
                    No data is sent to external servers.
                </Text>
            </View>
        </ScrollView>
    );
}

const styles = StyleSheet.create({
    container: { flex: 1, backgroundColor: colors.bgPrimary },
    content: { paddingHorizontal: spacing.lg, paddingTop: 60, paddingBottom: spacing.xxxl },
    title: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.xl, color: colors.textPrimary, marginBottom: 2 },
    subtitle: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.textDim, marginBottom: spacing.xl },
    // Active model card
    activeCard: { backgroundColor: colors.neonGlow, borderWidth: 1, borderColor: colors.neonBorder, borderRadius: borderRadius.lg, padding: spacing.xl, marginBottom: spacing.xl, ...shadows.ember, position: "relative" },
    activeLabel: { fontFamily: "Inter_400Regular", fontSize: fontSize.tiny, color: colors.neon, textTransform: "uppercase", letterSpacing: 1, marginBottom: spacing.sm },
    activeModel: { fontFamily: "Inter_700Bold", fontSize: fontSize.lg, color: colors.textPrimary, marginBottom: spacing.sm },
    activeDetails: { flexDirection: "row", gap: spacing.md },
    activeStat: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.textDim },
    statusDot: { position: "absolute", top: spacing.lg, right: spacing.lg, width: 8, height: 8, borderRadius: 4 },
    // Section
    sectionTitle: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.xs, color: colors.textDim, textTransform: "uppercase", letterSpacing: 1, marginBottom: spacing.sm },
    // Model cards
    modelCard: { backgroundColor: colors.bgCard, borderRadius: borderRadius.md, borderWidth: 1, borderColor: colors.glassBorder, padding: spacing.lg, marginBottom: spacing.sm },
    modelCardActive: { borderColor: colors.neon, backgroundColor: colors.neonGlow },
    modelHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
    modelInfo: { flex: 1 },
    modelName: { fontFamily: "Inter_500Medium", fontSize: fontSize.sm, color: colors.textPrimary, marginBottom: spacing.xs },
    modelTags: { flexDirection: "row", gap: spacing.sm },
    modelTag: { fontFamily: "Inter_400Regular", fontSize: fontSize.tiny, color: colors.textDim, backgroundColor: colors.bgInput, paddingHorizontal: spacing.sm, paddingVertical: 2, borderRadius: borderRadius.sm },
    activeBadge: { fontFamily: "Inter_500Medium", fontSize: fontSize.xs, color: colors.neon },
    switchText: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.textMuted },
    // Offline
    offlineCard: { backgroundColor: colors.bgCard, borderRadius: borderRadius.lg, borderWidth: 1, borderColor: colors.glassBorder, padding: spacing.xxl, alignItems: "center", marginTop: spacing.lg },
    offlineEmoji: { fontSize: 40, marginBottom: spacing.md },
    offlineTitle: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.md, color: colors.textPrimary, marginBottom: spacing.sm },
    offlineDesc: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.textDim, textAlign: "center", lineHeight: 18 },
    offlineText: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.textDim, fontStyle: "italic" },
    // Info
    infoCard: { backgroundColor: "rgba(0,200,100,0.06)", borderRadius: borderRadius.md, padding: spacing.md, marginTop: spacing.lg },
    infoText: { fontFamily: "Inter_400Regular", fontSize: fontSize.tiny, color: "#4ade80", textAlign: "center", lineHeight: 16 },
});
