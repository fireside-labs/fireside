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
import { colors, spacing, borderRadius, fontSize } from "../../src/theme";
import type { QueuedTask } from "../../src/types";

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

    useEffect(() => {
        if (isOnline) {
            companionAPI
                .queue()
                .then((res) => setTasks(res.tasks || []))
                .catch(() => setTasks(companionData?.pending_tasks || FALLBACK_TASKS));
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
});
