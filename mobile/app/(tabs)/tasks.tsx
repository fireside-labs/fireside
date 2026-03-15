/**
 * 📋 Tasks Tab — Queued tasks from phone → home PC.
 *
 * Shows pending, sent, completed, and failed tasks.
 * "Clear completed" button removes done items.
 */
import { useState, useEffect, useCallback } from "react";
import {
    View,
    Text,
    TouchableOpacity,
    FlatList,
    StyleSheet,
} from "react-native";
import { useConnection } from "../../src/hooks/useConnection";
import { companionAPI } from "../../src/api";
import { colors, spacing, borderRadius, fontSize } from "../../src/theme";
import type { QueuedTask } from "../../src/types";

// Fallback tasks when offline
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
    const { isOnline, companionData } = useConnection();
    const [tasks, setTasks] = useState<QueuedTask[]>([]);
    const [expanded, setExpanded] = useState<string | null>(null);

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

    const clearCompleted = useCallback(() => {
        setTasks((prev) => prev.filter((t) => t.status !== "completed"));
    }, []);

    const toggleExpand = (id: string) => {
        setExpanded(expanded === id ? null : id);
    };

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
                Tasks queued while offline. They'll send to your home PC when you're
                back online.
            </Text>

            {/* Task List */}
            {tasks.length === 0 ? (
                <View style={styles.emptyState}>
                    <Text style={styles.emptyEmoji}>📭</Text>
                    <Text style={styles.emptyTitle}>No tasks yet</Text>
                    <Text style={styles.emptySubtitle}>
                        Tasks queued from chat and actions{"\n"}will appear here.
                    </Text>
                </View>
            ) : (
                <FlatList
                    data={tasks}
                    renderItem={renderTask}
                    keyExtractor={(item) => item.id}
                    contentContainerStyle={styles.listContent}
                    ItemSeparatorComponent={() => <View style={{ height: spacing.sm }} />}
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
        paddingBottom: spacing.xxxl,
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
});
