/**
 * 📋 Tasks Tab — Queued tasks from phone → home PC.
 *
 * Sprint 2 additions:
 * - Pull-to-refresh (Valkyrie #4)
 * - New task creation button (Valkyrie #6)
 * - Haptic feedback
 */
import { useState, useEffect, useCallback } from "react";
import {
    View,
    Text,
    TextInput,
    TouchableOpacity,
    FlatList,
    StyleSheet,
    RefreshControl,
    Modal,
} from "react-native";
import * as Haptics from "expo-haptics";
import { useConnection } from "../../src/hooks/useConnection";
import { companionAPI } from "../../src/api";
import { colors, spacing, borderRadius, fontSize, shadows } from "../../src/theme";
import type { QueuedTask } from "../../src/types";

// Pipeline types for mini-view
interface PipelineStage {
    name: string;
    status: "done" | "running" | "pending" | "failed";
}

interface PipelineSummary {
    id: string;
    name: string;
    status: "running" | "completed" | "failed" | "escalated";
    stages: PipelineStage[];
    iteration: number;
    elapsed: string;
    test_pass?: number;
    test_total?: number;
}

const FALLBACK_TASKS: QueuedTask[] = [];

const STATUS_CONFIG: Record<
    string,
    { bg: string; text: string; label: string }
> = {
    pending: {
        bg: "rgba(255,255,255,0.03)",
        text: colors.textDim,
        label: "⏳ Queued",
    },
    sent: {
        bg: colors.neonGlow,
        text: colors.neon,
        label: "📡 Sent",
    },
    completed: {
        bg: "rgba(0,255,136,0.06)",
        text: colors.neon,
        label: "✅ Done",
    },
    failed: {
        bg: "rgba(255,68,102,0.05)",
        text: colors.danger,
        label: "❌ Failed",
    },
};

export default function TasksTab() {
    const { isOnline, companionData, sync } = useConnection();
    const [tasks, setTasks] = useState<QueuedTask[]>([]);
    const [expanded, setExpanded] = useState<string | null>(null);
    const [refreshing, setRefreshing] = useState(false);
    // Task creation
    const [showNewTask, setShowNewTask] = useState(false);
    const [newTaskText, setNewTaskText] = useState("");
    const [creating, setCreating] = useState(false);
    // Pipeline state
    const [pipelines, setPipelines] = useState<PipelineSummary[]>([]);
    const [showIntervene, setShowIntervene] = useState<string | null>(null);
    const [interveneText, setInterveneText] = useState("");
    const [sendingIntervene, setSendingIntervene] = useState(false);

    useEffect(() => {
        if (isOnline) {
            companionAPI
                .queue()
                .then((res) => setTasks(res.tasks || []))
                .catch(() => setTasks(companionData?.pending_tasks || FALLBACK_TASKS));
            // Fetch active pipelines
            companionAPI
                .pipelines()
                .then((res: any) => {
                    if (res.pipelines) setPipelines(res.pipelines);
                })
                .catch(() => {});
        } else {
            setTasks(companionData?.pending_tasks || FALLBACK_TASKS);
        }
    }, [isOnline, companionData]);

    const pending = tasks.filter((t) => t.status === "pending").length;
    const sent = tasks.filter((t) => t.status === "sent").length;
    const done = tasks.filter((t) => t.status === "completed").length;

    // Pull-to-refresh
    const onRefresh = useCallback(async () => {
        setRefreshing(true);
        await sync();
        if (isOnline) {
            try {
                const res = await companionAPI.queue();
                setTasks(res.tasks || []);
            } catch {
                // keep existing
            }
        }
        setRefreshing(false);
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
    }, [sync, isOnline]);

    const clearCompleted = useCallback(() => {
        setTasks((prev) => prev.filter((t) => t.status !== "completed"));
        Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    }, []);

    const toggleExpand = (id: string) => {
        setExpanded(expanded === id ? null : id);
    };

    // Create new task
    const handleCreateTask = useCallback(async () => {
        const text = newTaskText.trim();
        if (!text || creating) return;
        setCreating(true);
        Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);

        if (isOnline) {
            try {
                await companionAPI.queueTask("user_request", { text });
                // Refresh the queue
                const res = await companionAPI.queue();
                setTasks(res.tasks || []);
            } catch {
                // Add locally
                setTasks((prev) => [
                    {
                        id: `local-${Date.now()}`,
                        text,
                        status: "pending",
                        timestamp: new Date().toISOString(),
                    },
                    ...prev,
                ]);
            }
        } else {
            setTasks((prev) => [
                {
                    id: `local-${Date.now()}`,
                    text,
                    status: "pending",
                    timestamp: new Date().toISOString(),
                },
                ...prev,
            ]);
        }

        setNewTaskText("");
        setShowNewTask(false);
        setCreating(false);
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
    }, [newTaskText, creating, isOnline]);

    const renderTask = ({ item }: { item: QueuedTask }) => {
        const config = STATUS_CONFIG[item.status] || STATUS_CONFIG.pending;
        const isExpanded = expanded === item.id;

        return (
            <View>
                <TouchableOpacity
                    style={[styles.taskCard, { backgroundColor: config.bg }]}
                    onPress={() => toggleExpand(item.id)}
                    activeOpacity={0.7}
                >
                    <View style={styles.taskRow}>
                        <Text style={styles.taskText} numberOfLines={isExpanded ? undefined : 1}>
                            {item.text}
                        </Text>
                        <Text style={[styles.taskStatus, { color: config.text }]}>
                            {config.label}
                        </Text>
                    </View>
                    <Text style={styles.taskTime}>{item.timestamp}</Text>
                </TouchableOpacity>

                {isExpanded && item.result && (
                    <View style={styles.resultCard}>
                        <Text style={styles.resultText}>{item.result}</Text>
                    </View>
                )}
            </View>
        );
    };

    return (
        <View style={styles.container}>
            {/* Header */}
            <View style={styles.header}>
                <Text style={styles.title}>📋 Task Queue</Text>
                <View style={styles.statsRow}>
                    {pending > 0 && (
                        <Text style={[styles.stat, { color: colors.textDim }]}>
                            {pending} queued
                        </Text>
                    )}
                    {sent > 0 && (
                        <Text style={[styles.stat, { color: colors.warning }]}>
                            {sent} sending
                        </Text>
                    )}
                    {done > 0 && (
                        <Text style={[styles.stat, { color: colors.neon }]}>
                            {done} done
                        </Text>
                    )}
                </View>
            </View>

            {/* Description */}
            <Text style={styles.description}>
                Tasks queued from your phone. They'll run on your home PC when connected.
            </Text>

            {/* Pipeline Mini-View */}
            {pipelines.length > 0 && (
                <View style={styles.pipelineSection}>
                    <Text style={styles.pipelineSectionTitle}>🔥 Active Pipelines</Text>
                    {pipelines.map((p) => (
                        <View key={p.id} style={[
                            styles.pipelineCard,
                            p.status === "escalated" && styles.pipelineEscalated,
                            p.status === "completed" && styles.pipelineCompleted,
                        ]}>
                            <View style={styles.pipelineHeader}>
                                <Text style={styles.pipelineName} numberOfLines={1}>
                                    {p.name}
                                </Text>
                                <Text style={[
                                    styles.pipelineStatus,
                                    p.status === "running" && { color: colors.neon },
                                    p.status === "completed" && { color: colors.success },
                                    p.status === "failed" && { color: colors.danger },
                                    p.status === "escalated" && { color: colors.warning },
                                ]}>
                                    {p.status === "running" ? "⚡ Running" :
                                     p.status === "completed" ? "✅ Done" :
                                     p.status === "escalated" ? "⚠️ Escalated" : "❌ Failed"}
                                </Text>
                            </View>

                            {/* Stage progress rail */}
                            <View style={styles.stageRail}>
                                {p.stages.map((s, i) => (
                                    <View key={i} style={styles.stageItem}>
                                        <View style={[
                                            styles.stageDot,
                                            s.status === "done" && styles.stageDone,
                                            s.status === "running" && styles.stageRunning,
                                            s.status === "failed" && styles.stageFailed,
                                        ]} />
                                        <Text style={styles.stageName}>{s.name}</Text>
                                        {i < p.stages.length - 1 && (
                                            <View style={[
                                                styles.stageLine,
                                                s.status === "done" && styles.stageLineDone,
                                            ]} />
                                        )}
                                    </View>
                                ))}
                            </View>

                            {/* Metadata row */}
                            <View style={styles.pipelineMeta}>
                                <Text style={styles.pipelineMetaText}>Iter {p.iteration}</Text>
                                {p.test_pass !== undefined && (
                                    <Text style={styles.pipelineMetaText}>
                                        Tests: {p.test_pass}/{p.test_total}
                                    </Text>
                                )}
                                <Text style={styles.pipelineMetaText}>{p.elapsed}</Text>
                            </View>

                            {/* Intervene button */}
                            {(p.status === "running" || p.status === "escalated") && (
                                <TouchableOpacity
                                    style={styles.interveneBtn}
                                    onPress={() => {
                                        setShowIntervene(p.id);
                                        Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
                                    }}
                                    activeOpacity={0.7}
                                >
                                    <Text style={styles.interveneBtnText}>🎯 Intervene</Text>
                                </TouchableOpacity>
                            )}
                        </View>
                    ))}
                </View>
            )}

            {/* Task List */}
            {tasks.length === 0 ? (
                <View style={styles.emptyState}>
                    <Text style={styles.emptyEmoji}>📭</Text>
                    <Text style={styles.emptyTitle}>No tasks yet</Text>
                    <Text style={styles.emptySubtitle}>
                        Tap the + button to create a task{"\n"}for your companion to run at home.
                    </Text>
                </View>
            ) : (
                <FlatList
                    data={tasks}
                    renderItem={renderTask}
                    keyExtractor={(item) => item.id}
                    contentContainerStyle={styles.listContent}
                    ItemSeparatorComponent={() => <View style={{ height: spacing.sm }} />}
                    refreshControl={
                        <RefreshControl
                            refreshing={refreshing}
                            onRefresh={onRefresh}
                            tintColor={colors.neon}
                            colors={[colors.neon]}
                        />
                    }
                />
            )}

            {/* Clear completed */}
            {done > 0 && (
                <TouchableOpacity
                    style={styles.clearBtn}
                    onPress={clearCompleted}
                    activeOpacity={0.7}
                >
                    <Text style={styles.clearBtnText}>Clear completed ({done})</Text>
                </TouchableOpacity>
            )}

            {/* FAB — New Task */}
            <TouchableOpacity
                style={styles.fab}
                onPress={() => {
                    setShowNewTask(true);
                    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
                }}
                activeOpacity={0.8}
            >
                <Text style={styles.fabText}>+</Text>
            </TouchableOpacity>

            {/* New Task Modal */}
            <Modal
                visible={showNewTask}
                transparent
                animationType="slide"
                onRequestClose={() => setShowNewTask(false)}
            >
                <View style={styles.modalOverlay}>
                    <View style={styles.modalCard}>
                        <Text style={styles.modalTitle}>New Task</Text>
                        <Text style={styles.modalSubtitle}>
                            What should your companion do when you're back online?
                        </Text>
                        <TextInput
                            style={styles.modalInput}
                            value={newTaskText}
                            onChangeText={setNewTaskText}
                            placeholder="e.g. Summarize my emails..."
                            placeholderTextColor={colors.textMuted}
                            autoFocus
                            multiline
                            maxLength={200}
                        />
                        <View style={styles.modalActions}>
                            <TouchableOpacity
                                style={styles.modalCancel}
                                onPress={() => {
                                    setShowNewTask(false);
                                    setNewTaskText("");
                                }}
                            >
                                <Text style={styles.modalCancelText}>Cancel</Text>
                            </TouchableOpacity>
                            <TouchableOpacity
                                style={[
                                    styles.modalSubmit,
                                    (!newTaskText.trim() || creating) && styles.modalSubmitDisabled,
                                ]}
                                onPress={handleCreateTask}
                                disabled={!newTaskText.trim() || creating}
                            >
                                <Text style={styles.modalSubmitText}>
                                    {creating ? "Adding..." : "Add Task"}
                                </Text>
                            </TouchableOpacity>
                        </View>
                    </View>
                </View>
            </Modal>

            {/* Intervene Modal */}
            <Modal
                visible={showIntervene !== null}
                transparent
                animationType="slide"
                onRequestClose={() => setShowIntervene(null)}
            >
                <View style={styles.modalOverlay}>
                    <View style={styles.modalCard}>
                        <Text style={styles.modalTitle}>🎯 Intervene</Text>
                        <Text style={styles.modalSubtitle}>
                            Send instructions to the running pipeline. Your companion will inject them into the next iteration.
                        </Text>
                        <TextInput
                            style={styles.modalInput}
                            value={interveneText}
                            onChangeText={setInterveneText}
                            placeholder="e.g. Use a HashMap instead of array..."
                            placeholderTextColor={colors.textMuted}
                            autoFocus
                            multiline
                            maxLength={500}
                        />
                        <View style={styles.modalActions}>
                            <TouchableOpacity
                                style={styles.modalCancel}
                                onPress={() => {
                                    setShowIntervene(null);
                                    setInterveneText("");
                                }}
                            >
                                <Text style={styles.modalCancelText}>Cancel</Text>
                            </TouchableOpacity>
                            <TouchableOpacity
                                style={[
                                    styles.modalSubmit,
                                    (!interveneText.trim() || sendingIntervene) && styles.modalSubmitDisabled,
                                ]}
                                onPress={async () => {
                                    if (!interveneText.trim() || !showIntervene) return;
                                    setSendingIntervene(true);
                                    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Heavy);
                                    try {
                                        await companionAPI.intervene(showIntervene, interveneText.trim());
                                    } catch { }
                                    setSendingIntervene(false);
                                    setShowIntervene(null);
                                    setInterveneText("");
                                    Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
                                }}
                                disabled={!interveneText.trim() || sendingIntervene}
                            >
                                <Text style={styles.modalSubmitText}>
                                    {sendingIntervene ? "Sending..." : "Send to Pipeline"}
                                </Text>
                            </TouchableOpacity>
                        </View>
                    </View>
                </View>
            </Modal>
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: colors.bgPrimary,
        paddingHorizontal: spacing.lg,
        paddingTop: 60,
    },
    header: {
        flexDirection: "row",
        justifyContent: "space-between",
        alignItems: "center",
        marginBottom: spacing.sm,
    },
    title: {
        fontFamily: "Inter_600SemiBold",
        fontSize: fontSize.xl,
        color: colors.textPrimary,
    },
    statsRow: {
        flexDirection: "row",
        gap: spacing.sm,
    },
    stat: {
        fontFamily: "Inter_400Regular",
        fontSize: fontSize.tiny,
    },
    description: {
        fontFamily: "Inter_400Regular",
        fontSize: fontSize.xs,
        color: colors.textDim,
        marginBottom: spacing.lg,
    },
    listContent: {
        paddingBottom: spacing.xxxl + 60,
    },
    taskCard: {
        borderRadius: borderRadius.md,
        padding: spacing.md,
    },
    taskRow: {
        flexDirection: "row",
        justifyContent: "space-between",
        alignItems: "flex-start",
    },
    taskText: {
        fontFamily: "Inter_400Regular",
        fontSize: fontSize.sm,
        color: colors.textSecondary,
        flex: 1,
        marginRight: spacing.sm,
    },
    taskStatus: {
        fontFamily: "Inter_400Regular",
        fontSize: fontSize.tiny,
        flexShrink: 0,
    },
    taskTime: {
        fontFamily: "Inter_400Regular",
        fontSize: fontSize.tiny,
        color: colors.textMuted,
        marginTop: 2,
    },
    resultCard: {
        marginLeft: spacing.md,
        marginTop: spacing.xs,
        padding: spacing.md,
        borderRadius: borderRadius.sm,
        backgroundColor: colors.bgCard,
        borderLeftWidth: 2,
        borderLeftColor: colors.neon,
    },
    resultText: {
        fontFamily: "Inter_400Regular",
        fontSize: fontSize.sm,
        color: colors.textSecondary,
    },
    emptyState: {
        flex: 1,
        justifyContent: "center",
        alignItems: "center",
        paddingBottom: 80,
    },
    emptyEmoji: {
        fontSize: 48,
        marginBottom: spacing.md,
    },
    emptyTitle: {
        fontFamily: "Inter_600SemiBold",
        fontSize: fontSize.lg,
        color: colors.textSecondary,
        marginBottom: spacing.xs,
    },
    emptySubtitle: {
        fontFamily: "Inter_400Regular",
        fontSize: fontSize.sm,
        color: colors.textMuted,
        textAlign: "center",
        lineHeight: 20,
    },
    clearBtn: {
        backgroundColor: colors.bgCard,
        borderRadius: borderRadius.md,
        borderWidth: 1,
        borderColor: colors.glassBorder,
        paddingVertical: spacing.md,
        alignItems: "center",
        marginBottom: spacing.xxxl,
    },
    clearBtnText: {
        fontFamily: "Inter_500Medium",
        fontSize: fontSize.sm,
        color: colors.textDim,
    },
    // FAB
    fab: {
        position: "absolute",
        bottom: 100,
        right: spacing.xl,
        width: 56,
        height: 56,
        borderRadius: 28,
        backgroundColor: colors.neon,
        justifyContent: "center",
        alignItems: "center",
        shadowColor: colors.neon,
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.4,
        shadowRadius: 8,
        elevation: 8,
    },
    fabText: {
        fontSize: 28,
        color: colors.bgPrimary,
        fontFamily: "Inter_700Bold",
        lineHeight: 30,
    },
    // Modal
    modalOverlay: {
        flex: 1,
        justifyContent: "flex-end",
        backgroundColor: "rgba(0,0,0,0.6)",
    },
    modalCard: {
        backgroundColor: colors.bgSecondary,
        borderTopLeftRadius: borderRadius.xl,
        borderTopRightRadius: borderRadius.xl,
        padding: spacing.xxl,
        paddingBottom: 50,
    },
    modalTitle: {
        fontFamily: "Inter_600SemiBold",
        fontSize: fontSize.xl,
        color: colors.textPrimary,
        marginBottom: spacing.xs,
    },
    modalSubtitle: {
        fontFamily: "Inter_400Regular",
        fontSize: fontSize.sm,
        color: colors.textDim,
        marginBottom: spacing.lg,
    },
    modalInput: {
        backgroundColor: colors.bgInput,
        borderWidth: 1,
        borderColor: colors.glassBorder,
        borderRadius: borderRadius.md,
        paddingHorizontal: spacing.lg,
        paddingVertical: spacing.md,
        fontFamily: "Inter_400Regular",
        fontSize: fontSize.md,
        color: colors.textPrimary,
        minHeight: 80,
        textAlignVertical: "top",
        marginBottom: spacing.lg,
    },
    modalActions: {
        flexDirection: "row",
        gap: spacing.md,
    },
    modalCancel: {
        flex: 1,
        backgroundColor: colors.bgCard,
        borderRadius: borderRadius.md,
        paddingVertical: spacing.md,
        alignItems: "center",
    },
    modalCancelText: {
        fontFamily: "Inter_500Medium",
        fontSize: fontSize.sm,
        color: colors.textDim,
    },
    modalSubmit: {
        flex: 2,
        backgroundColor: colors.neon,
        borderRadius: borderRadius.md,
        paddingVertical: spacing.md,
        alignItems: "center",
    },
    modalSubmitDisabled: {
        opacity: 0.4,
    },
    modalSubmitText: {
        fontFamily: "Inter_600SemiBold",
        fontSize: fontSize.sm,
        color: colors.bgPrimary,
    },
    // Pipeline mini-view
    pipelineSection: {
        marginBottom: spacing.lg,
    },
    pipelineSectionTitle: {
        fontFamily: "Inter_600SemiBold",
        fontSize: fontSize.md,
        color: colors.textPrimary,
        marginBottom: spacing.sm,
    },
    pipelineCard: {
        backgroundColor: colors.bgCard,
        borderRadius: borderRadius.md,
        borderWidth: 1,
        borderColor: colors.glassBorder,
        padding: spacing.md,
        marginBottom: spacing.sm,
        ...shadows.card,
    },
    pipelineEscalated: {
        borderColor: colors.warning,
        backgroundColor: "rgba(245, 166, 35, 0.04)",
    },
    pipelineCompleted: {
        borderColor: colors.success,
        backgroundColor: "rgba(46, 204, 113, 0.04)",
    },
    pipelineHeader: {
        flexDirection: "row",
        justifyContent: "space-between",
        alignItems: "center",
        marginBottom: spacing.sm,
    },
    pipelineName: {
        fontFamily: "Inter_500Medium",
        fontSize: fontSize.sm,
        color: colors.textPrimary,
        flex: 1,
        marginRight: spacing.sm,
    },
    pipelineStatus: {
        fontFamily: "Inter_500Medium",
        fontSize: fontSize.tiny,
        color: colors.textDim,
    },
    stageRail: {
        flexDirection: "row",
        alignItems: "center",
        marginBottom: spacing.sm,
    },
    stageItem: {
        flexDirection: "row",
        alignItems: "center",
    },
    stageDot: {
        width: 8,
        height: 8,
        borderRadius: 4,
        backgroundColor: colors.textMuted,
    },
    stageDone: {
        backgroundColor: colors.success,
    },
    stageRunning: {
        backgroundColor: colors.neon,
    },
    stageFailed: {
        backgroundColor: colors.danger,
    },
    stageName: {
        fontFamily: "Inter_400Regular",
        fontSize: fontSize.tiny,
        color: colors.textDim,
        marginLeft: 3,
    },
    stageLine: {
        width: 12,
        height: 1,
        backgroundColor: colors.textMuted,
        marginHorizontal: 2,
    },
    stageLineDone: {
        backgroundColor: colors.success,
    },
    pipelineMeta: {
        flexDirection: "row",
        gap: spacing.md,
    },
    pipelineMetaText: {
        fontFamily: "Inter_400Regular",
        fontSize: fontSize.tiny,
        color: colors.textMuted,
    },
    interveneBtn: {
        backgroundColor: colors.neonGlow,
        borderRadius: borderRadius.sm,
        borderWidth: 1,
        borderColor: colors.neonBorder,
        paddingVertical: spacing.xs,
        paddingHorizontal: spacing.md,
        alignSelf: "flex-start",
        marginTop: spacing.sm,
    },
    interveneBtnText: {
        fontFamily: "Inter_500Medium",
        fontSize: fontSize.tiny,
        color: colors.neon,
    },
});
