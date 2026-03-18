/**
 * 🧠 Brain Tab — Remote model management + GPU monitor.
 *
 * Shows the AI model running on the home PC, GPU info, VRAM usage,
 * and allows switching between available models.
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

interface GPUInfo {
    name: string | null;
    vram_total_gb: number | null;
    vram_used_gb: number | null;
}

export default function BrainTab() {
    const { isOnline } = useConnection();
    const [models, setModels] = useState<ModelInfo[]>([]);
    const [activeModel, setActiveModel] = useState<string>("");
    const [activeBackend, setActiveBackend] = useState<string>("llama.cpp");
    const [contextLength, setContextLength] = useState<number | null>(null);
    const [gpu, setGpu] = useState<GPUInfo | null>(null);
    const [uptimeHuman, setUptimeHuman] = useState<string>("");
    const [pluginsLoaded, setPluginsLoaded] = useState<number>(0);
    const [loading, setLoading] = useState(true);
    const [switching, setSwitching] = useState<string | null>(null);
    const [refreshing, setRefreshing] = useState(false);

    const fetchData = useCallback(async () => {
        try {
            // Fetch status (always works) + models + active brain in parallel
            const [statusRes, modelsRes, activeRes] = await Promise.allSettled([
                companionAPI.status(),
                companionAPI.brainModels(),
                companionAPI.brainActive(),
            ]);

            if (statusRes.status === "fulfilled") {
                const s = statusRes.value;
                setGpu(s.gpu || null);
                setUptimeHuman(s.uptime_human || "");
                setPluginsLoaded(s.plugins_loaded || 0);
                if (s.model) setActiveModel(s.model);
            }
            if (modelsRes.status === "fulfilled") {
                setModels(modelsRes.value.models || []);
            }
            if (activeRes.status === "fulfilled") {
                const a = activeRes.value;
                if (a.model) setActiveModel(a.model);
                setActiveBackend(a.backend || "llama.cpp");
                setContextLength(a.context_length || null);
            }
        } catch { }
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

    // VRAM percentage
    const vramPct = gpu?.vram_total_gb && gpu?.vram_used_gb
        ? Math.round((gpu.vram_used_gb / gpu.vram_total_gb) * 100)
        : null;

    return (
        <ScrollView
            style={styles.container}
            contentContainerStyle={styles.content}
            refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.neon} />}
        >
            <Text style={styles.title}>🧠 Brain</Text>
            <Text style={styles.subtitle}>AI model running on your home PC</Text>

            {/* ═══ GPU Card ═══ */}
            {gpu && (
                <View style={styles.gpuCard}>
                    <View style={styles.gpuHeader}>
                        <Text style={styles.gpuIcon}>🎮</Text>
                        <View style={styles.gpuInfo}>
                            <Text style={styles.gpuName}>{gpu.name || "GPU"}</Text>
                            <Text style={styles.gpuSubtext}>
                                {uptimeHuman ? `Up ${uptimeHuman}` : ""}{pluginsLoaded ? ` · ${pluginsLoaded} plugins` : ""}
                            </Text>
                        </View>
                        <View style={[styles.gpuDot, { backgroundColor: colors.success }]} />
                    </View>

                    {/* VRAM bar */}
                    {gpu.vram_total_gb && (
                        <View style={styles.vramSection}>
                            <View style={styles.vramHeader}>
                                <Text style={styles.vramLabel}>VRAM</Text>
                                <Text style={styles.vramValue}>
                                    {gpu.vram_used_gb?.toFixed(1) || "?"} / {gpu.vram_total_gb.toFixed(1)} GB
                                </Text>
                            </View>
                            <View style={styles.vramTrack}>
                                <View
                                    style={[
                                        styles.vramFill,
                                        {
                                            width: `${vramPct || 0}%`,
                                            backgroundColor: (vramPct || 0) > 85
                                                ? colors.danger
                                                : (vramPct || 0) > 60
                                                    ? colors.warning
                                                    : colors.success,
                                        },
                                    ]}
                                />
                            </View>
                            <Text style={styles.vramPct}>{vramPct}% used</Text>
                        </View>
                    )}
                </View>
            )}

            {/* ═══ Active Model Card ═══ */}
            <View style={styles.activeCard}>
                <Text style={styles.activeLabel}>CURRENTLY ACTIVE</Text>
                {activeModel ? (
                    <>
                        <Text style={styles.activeModel}>{activeModel}</Text>
                        <View style={styles.activeDetails}>
                            <View style={styles.detailChip}>
                                <Text style={styles.detailText}>⚡ {activeBackend}</Text>
                            </View>
                            {contextLength && (
                                <View style={styles.detailChip}>
                                    <Text style={styles.detailText}>📐 {contextLength.toLocaleString()} ctx</Text>
                                </View>
                            )}
                        </View>
                    </>
                ) : (
                    <Text style={styles.offlineText}>
                        {isOnline ? "Loading..." : "Connect to your PC to see model info"}
                    </Text>
                )}
                <View style={[styles.statusDot, { backgroundColor: isOnline ? colors.onlineDot : colors.offlineDot }]} />
            </View>

            {/* ═══ Model List ═══ */}
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

            {/* Privacy note */}
            <View style={styles.privacyCard}>
                <Text style={styles.privacyText}>
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
    // GPU card
    gpuCard: {
        backgroundColor: "rgba(46,204,113,0.04)", borderWidth: 1, borderColor: "rgba(46,204,113,0.15)",
        borderRadius: borderRadius.lg, padding: spacing.xl, marginBottom: spacing.lg,
    },
    gpuHeader: { flexDirection: "row", alignItems: "center", gap: spacing.md },
    gpuIcon: { fontSize: 28 },
    gpuInfo: { flex: 1 },
    gpuName: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.sm, color: colors.textPrimary },
    gpuSubtext: { fontFamily: "Inter_400Regular", fontSize: fontSize.tiny, color: colors.textDim, marginTop: 1 },
    gpuDot: { width: 8, height: 8, borderRadius: 4 },
    // VRAM
    vramSection: { marginTop: spacing.md },
    vramHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: spacing.xs },
    vramLabel: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.tiny, color: colors.textDim, letterSpacing: 1.5 },
    vramValue: { fontFamily: "Inter_400Regular", fontSize: fontSize.tiny, color: colors.textSecondary },
    vramTrack: { height: 6, borderRadius: 3, backgroundColor: "rgba(255,255,255,0.06)", overflow: "hidden" },
    vramFill: { height: 6, borderRadius: 3 },
    vramPct: { fontFamily: "Inter_400Regular", fontSize: fontSize.tiny, color: colors.textDim, marginTop: spacing.xs, textAlign: "right" },
    // Active card
    activeCard: { backgroundColor: colors.neonGlow, borderWidth: 1, borderColor: colors.neonBorder, borderRadius: borderRadius.lg, padding: spacing.xl, marginBottom: spacing.xl, ...shadows.ember, position: "relative" as const },
    activeLabel: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.tiny, color: colors.neon, letterSpacing: 1.5, marginBottom: spacing.sm },
    activeModel: { fontFamily: "Inter_700Bold", fontSize: fontSize.lg, color: colors.textPrimary, marginBottom: spacing.sm },
    activeDetails: { flexDirection: "row", gap: spacing.sm },
    detailChip: { backgroundColor: "rgba(255,255,255,0.04)", paddingHorizontal: spacing.sm, paddingVertical: 3, borderRadius: borderRadius.sm, borderWidth: 1, borderColor: "rgba(255,255,255,0.06)" },
    detailText: { fontFamily: "Inter_400Regular", fontSize: fontSize.tiny, color: colors.textDim },
    statusDot: { position: "absolute" as const, top: spacing.lg, right: spacing.lg, width: 8, height: 8, borderRadius: 4 },
    // Section
    sectionTitle: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.xs, color: colors.textDim, textTransform: "uppercase" as const, letterSpacing: 1, marginBottom: spacing.sm },
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
    offlineText: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.textDim, fontStyle: "italic" as const },
    // Privacy
    privacyCard: { backgroundColor: "rgba(46,204,113,0.04)", borderRadius: borderRadius.md, padding: spacing.md, marginTop: spacing.lg, borderWidth: 1, borderColor: "rgba(46,204,113,0.08)" },
    privacyText: { fontFamily: "Inter_400Regular", fontSize: fontSize.tiny, color: "#4ade80", textAlign: "center", lineHeight: 16 },
});
