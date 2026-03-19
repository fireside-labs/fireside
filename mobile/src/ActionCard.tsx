/**
 * 🎴 Action Card.
 *
 * Renders rich visual cards in chat when the backend returns an `action` field.
 * Types: browse_result, pipeline_status, pipeline_complete, memory_recall, translation_result.
 *
 * Per CREATIVE_DIRECTION.md: fire-orange left border accent, warm palette.
 */
import { useState, useEffect, useRef } from "react";
import {
    View,
    Text,
    TouchableOpacity,
    StyleSheet,
    Animated,
    Linking,
} from "react-native";
import * as Clipboard from "expo-clipboard";
import * as Haptics from "expo-haptics";
import { colors, spacing, borderRadius, fontSize, shadows } from "./theme";
import type { ActionData } from "./types";

interface ActionCardProps {
    action: ActionData;
}

export default function ActionCard({ action }: ActionCardProps) {
    switch (action.type) {
        case "browse_result":
            return <BrowseResultCard action={action} />;
        case "pipeline_status":
            return <PipelineStatusCard action={action} />;
        case "pipeline_complete":
            return <PipelineCompleteCard action={action} />;
        case "memory_recall":
            return <MemoryRecallCard action={action} />;
        case "translation_result":
            return <TranslationResultCard action={action} />;
        case "calendar_event":
            return <CalendarEventCard action={action} />;
        case "health_summary":
            return <HealthSummaryCard action={action} />;
        case "contact_info":
            return <ContactInfoCard action={action} />;
        default:
            return null;
    }
}

/** 🌐 Browse Result — URL summary with key points */
function BrowseResultCard({ action }: { action: ActionData }) {
    const handleOpenURL = () => {
        if (action.url) {
            Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
            Linking.openURL(action.url);
        }
    };

    return (
        <View style={[styles.card, styles.browseCard]}>
            <View style={styles.cardHeader}>
                <Text style={styles.cardIcon}>🌐</Text>
                <Text style={styles.cardTitle} numberOfLines={1}>{action.title || "Web Result"}</Text>
            </View>

            {action.url && (
                <TouchableOpacity onPress={handleOpenURL} activeOpacity={0.7}>
                    <Text style={styles.urlText} numberOfLines={1}>{action.url}</Text>
                </TouchableOpacity>
            )}

            {action.summary && (
                <Text style={styles.summaryText}>{action.summary}</Text>
            )}

            {action.key_points && action.key_points.length > 0 && (
                <View style={styles.chipRow}>
                    {action.key_points.map((point, i) => (
                        <View key={i} style={styles.chip}>
                            <Text style={styles.chipText}>{point}</Text>
                        </View>
                    ))}
                </View>
            )}

            {action.timestamp && (
                <Text style={styles.timestampText}>
                    {new Date(action.timestamp).toLocaleString()}
                </Text>
            )}
        </View>
    );
}

/** ⚡ Pipeline Status — progress bar, pulsing animation */
function PipelineStatusCard({ action }: { action: ActionData }) {
    const pulse = useRef(new Animated.Value(0.6)).current;

    useEffect(() => {
        const anim = Animated.loop(
            Animated.sequence([
                Animated.timing(pulse, { toValue: 1, duration: 800, useNativeDriver: true }),
                Animated.timing(pulse, { toValue: 0.6, duration: 800, useNativeDriver: true }),
            ])
        );
        anim.start();
        return () => anim.stop();
    }, []);

    const percent = action.percent ?? 0;

    return (
        <Animated.View style={[styles.card, styles.pipelineCard, { opacity: pulse }]}>
            <View style={styles.cardHeader}>
                <Text style={styles.cardIcon}>⚡</Text>
                <Text style={styles.cardTitle}>{action.name || "Processing..."}</Text>
            </View>

            {action.stage && (
                <Text style={styles.stageText}>Stage: {action.stage}</Text>
            )}

            <View style={styles.progressBg}>
                <View style={[styles.progressFill, { width: `${Math.min(percent, 100)}%` }]} />
            </View>
            <Text style={styles.percentText}>{percent}%</Text>

            {action.estimated_completion && (
                <Text style={styles.etaText}>ETA: {action.estimated_completion}</Text>
            )}
        </Animated.View>
    );
}

/** ✅ Pipeline Complete — celebration badge */
function PipelineCompleteCard({ action }: { action: ActionData }) {
    const scale = useRef(new Animated.Value(0.8)).current;

    useEffect(() => {
        Animated.spring(scale, { toValue: 1, friction: 4, tension: 100, useNativeDriver: true }).start();
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
    }, []);

    return (
        <Animated.View style={[styles.card, styles.completeCard, { transform: [{ scale }] }]}>
            <View style={styles.cardHeader}>
                <Text style={styles.cardIcon}>✅</Text>
                <Text style={styles.cardTitle}>{action.name || "Complete!"}</Text>
            </View>

            {action.results && (
                <Text style={styles.summaryText}>{action.results}</Text>
            )}
        </Animated.View>
    );
}

/** 🧠 Memory Recall — dimmer supplemental card */
function MemoryRecallCard({ action }: { action: ActionData }) {
    const sourceIcon = action.source === "working_memory" ? "🧠" :
        action.source === "taught_facts" ? "📚" :
            action.source === "chat_history" ? "💬" : "🔮";

    const sourceLabel = action.source === "working_memory" ? "Memory" :
        action.source === "taught_facts" ? "Taught" :
            action.source === "chat_history" ? "Chat" : "Hypothesis";

    return (
        <View style={[styles.card, styles.memoryCard]}>
            <View style={styles.cardHeader}>
                <Text style={styles.cardIcon}>{sourceIcon}</Text>
                <View style={styles.sourceBadge}>
                    <Text style={styles.sourceBadgeText}>{sourceLabel}</Text>
                </View>
                {action.date && <Text style={styles.dateText}>{action.date}</Text>}
            </View>

            {action.content && (
                <Text style={styles.memoryContent} numberOfLines={3}>{action.content}</Text>
            )}

            {action.relevance != null && (
                <View style={styles.relevanceRow}>
                    <View style={[styles.relevanceDot, { backgroundColor: action.relevance > 0.8 ? colors.neon : colors.ember }]} />
                    <Text style={styles.relevanceText}>{Math.round(action.relevance * 100)}% relevant</Text>
                </View>
            )}
        </View>
    );
}

/** 🌍 Translation Result — language pair with copy */
function TranslationResultCard({ action }: { action: ActionData }) {
    const [copied, setCopied] = useState(false);

    const handleCopy = () => {
        if (action.translated) {
            Clipboard.setStringAsync(action.translated);
            setCopied(true);
            Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
            setTimeout(() => setCopied(false), 2000);
        }
    };

    return (
        <View style={[styles.card, styles.translationCard]}>
            <View style={styles.cardHeader}>
                <Text style={styles.cardIcon}>🌍</Text>
                <Text style={styles.cardTitle}>
                    {action.source_lang || "?"} → {action.target_lang || "?"}
                </Text>
            </View>

            {action.original && (
                <View style={styles.translationBlock}>
                    <Text style={styles.translationLabel}>Original</Text>
                    <Text style={styles.translationText}>{action.original}</Text>
                </View>
            )}

            {action.translated && (
                <View style={[styles.translationBlock, styles.translatedBlock]}>
                    <Text style={styles.translationLabel}>Translated</Text>
                    <Text style={[styles.translationText, { color: colors.textPrimary }]}>{action.translated}</Text>
                </View>
            )}

            <TouchableOpacity style={styles.copyBtn} onPress={handleCopy} activeOpacity={0.7}>
                <Text style={styles.copyBtnText}>{copied ? "✅ Copied!" : "📋 Copy Translation"}</Text>
            </TouchableOpacity>
        </View>
    );
}

/** 📅 Calendar Event — meeting details with prep button */
function CalendarEventCard({ action }: { action: ActionData }) {
    const formatTime = (iso?: string) => {
        if (!iso) return "";
        return new Date(iso).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
    };

    return (
        <View style={[styles.card, styles.calendarCard]}>
            <View style={styles.cardHeader}>
                <Text style={styles.cardIcon}>📅</Text>
                <Text style={styles.cardTitle}>{action.title || "Upcoming Event"}</Text>
            </View>

            <View style={styles.calendarDetail}>
                <Text style={styles.calendarDetailIcon}>🕐</Text>
                <Text style={styles.calendarDetailText}>
                    {formatTime(action.startDate)}{action.endDate ? ` – ${formatTime(action.endDate)}` : ""}
                </Text>
            </View>

            {action.location && (
                <View style={styles.calendarDetail}>
                    <Text style={styles.calendarDetailIcon}>📍</Text>
                    <Text style={styles.calendarDetailText}>{action.location}</Text>
                </View>
            )}

            {action.attendees && action.attendees.length > 0 && (
                <View style={styles.calendarDetail}>
                    <Text style={styles.calendarDetailIcon}>👥</Text>
                    <Text style={styles.calendarDetailText}>
                        {action.attendees.slice(0, 3).join(", ")}
                        {action.attendees.length > 3 ? ` + ${action.attendees.length - 3}` : ""}
                    </Text>
                </View>
            )}

            <TouchableOpacity style={styles.prepBtn} activeOpacity={0.7}
                onPress={() => Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light)}>
                <Text style={styles.prepBtnText}>Help me prep →</Text>
            </TouchableOpacity>
        </View>
    );
}

/** 👣 Health Summary — daily activity with goal progress */
function HealthSummaryCard({ action }: { action: ActionData }) {
    const steps = action.steps ?? 0;
    const calories = action.calories ?? 0;
    const active = action.activeMinutes ?? 0;
    const goal = action.goal ?? 10000;
    const pct = Math.min(Math.round((steps / goal) * 100), 100);

    return (
        <View style={[styles.card, styles.healthCard]}>
            <View style={styles.cardHeader}>
                <Text style={styles.cardIcon}>👣</Text>
                <Text style={styles.cardTitle}>{action.title || "Today's Activity"}</Text>
            </View>

            <View style={styles.healthStats}>
                <View style={styles.healthStat}>
                    <Text style={styles.healthStatIcon}>👣</Text>
                    <Text style={styles.healthStatValue}>{steps.toLocaleString()}</Text>
                    <Text style={styles.healthStatLabel}>steps</Text>
                </View>
                <View style={styles.healthStat}>
                    <Text style={styles.healthStatIcon}>🔥</Text>
                    <Text style={styles.healthStatValue}>{calories}</Text>
                    <Text style={styles.healthStatLabel}>calories</Text>
                </View>
                <View style={styles.healthStat}>
                    <Text style={styles.healthStatIcon}>⏱</Text>
                    <Text style={styles.healthStatValue}>{active}</Text>
                    <Text style={styles.healthStatLabel}>active minutes</Text>
                </View>
            </View>

            <View style={styles.goalBar}>
                <View style={[styles.goalFill, {
                    width: `${pct}%`,
                    backgroundColor: pct >= 100 ? colors.success : colors.neon,
                }]} />
            </View>
            <Text style={styles.goalText}>
                {pct >= 100 ? "🎉 Goal reached!" : `${pct}% of daily goal`}
            </Text>
        </View>
    );
}

/** 👤 Contact Info — person card with action buttons */
function ContactInfoCard({ action }: { action: ActionData }) {
    return (
        <View style={[styles.card, styles.contactCard]}>
            <View style={styles.cardHeader}>
                <Text style={styles.cardIcon}>👤</Text>
                <Text style={styles.cardTitle}>Contact</Text>
            </View>

            <Text style={styles.contactName}>{action.name || action.title || "Unknown"}</Text>
            {action.organization && (
                <Text style={styles.contactOrg}>{action.organization}</Text>
            )}

            {action.email && (
                <View style={styles.contactDetail}>
                    <Text style={styles.calendarDetailIcon}>📧</Text>
                    <Text style={styles.contactDetailText}>{action.email}</Text>
                </View>
            )}

            {action.phone && (
                <View style={styles.contactDetail}>
                    <Text style={styles.calendarDetailIcon}>📱</Text>
                    <Text style={styles.contactDetailText}>{action.phone}</Text>
                </View>
            )}

            {action.lastContacted && (
                <View style={styles.contactDetail}>
                    <Text style={styles.calendarDetailIcon}>📅</Text>
                    <Text style={styles.contactDetailText}>Last met: {action.lastContacted}</Text>
                </View>
            )}

            <View style={styles.contactActions}>
                {action.phone && (
                    <TouchableOpacity style={styles.contactActionBtn} activeOpacity={0.7}
                        onPress={() => { Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light); Linking.openURL(`tel:${action.phone}`); }}>
                        <Text style={styles.contactActionText}>📞 Call</Text>
                    </TouchableOpacity>
                )}
                {action.phone && (
                    <TouchableOpacity style={styles.contactActionBtn} activeOpacity={0.7}
                        onPress={() => { Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light); Linking.openURL(`sms:${action.phone}`); }}>
                        <Text style={styles.contactActionText}>💬 Message</Text>
                    </TouchableOpacity>
                )}
                {action.email && (
                    <TouchableOpacity style={styles.contactActionBtn} activeOpacity={0.7}
                        onPress={() => { Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light); Linking.openURL(`mailto:${action.email}`); }}>
                        <Text style={styles.contactActionText}>📧 Email</Text>
                    </TouchableOpacity>
                )}
            </View>
        </View>
    );
}

const styles = StyleSheet.create({
    // Shared card
    card: { borderRadius: borderRadius.lg, borderWidth: 1, padding: spacing.md, marginTop: spacing.sm, ...shadows.card },
    cardHeader: { flexDirection: "row", alignItems: "center", gap: spacing.sm, marginBottom: spacing.sm },
    cardIcon: { fontSize: 18 },
    cardTitle: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.sm, color: colors.textPrimary, flex: 1 },

    // Browse
    browseCard: { backgroundColor: "rgba(232, 113, 44, 0.06)", borderColor: colors.neon, borderLeftWidth: 3 },
    urlText: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.neon, marginBottom: spacing.sm, textDecorationLine: "underline" },
    summaryText: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.textSecondary, lineHeight: 18, marginBottom: spacing.sm },
    chipRow: { flexDirection: "row", flexWrap: "wrap", gap: spacing.xs },
    chip: { backgroundColor: colors.neonGlow, borderRadius: borderRadius.full, paddingHorizontal: spacing.sm, paddingVertical: spacing.xs, borderWidth: 1, borderColor: colors.neonBorder },
    chipText: { fontFamily: "Inter_400Regular", fontSize: fontSize.tiny, color: colors.textSecondary },
    timestampText: { fontFamily: "Inter_400Regular", fontSize: fontSize.tiny, color: colors.textMuted, marginTop: spacing.sm },

    // Pipeline
    pipelineCard: { backgroundColor: "rgba(245, 166, 35, 0.06)", borderColor: colors.ember },
    stageText: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.textDim, marginBottom: spacing.sm },
    progressBg: { height: 6, backgroundColor: colors.bgInput, borderRadius: 3, overflow: "hidden", marginBottom: spacing.xs },
    progressFill: { height: "100%", backgroundColor: colors.neon, borderRadius: 3 },
    percentText: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.xs, color: colors.neon },
    etaText: { fontFamily: "Inter_400Regular", fontSize: fontSize.tiny, color: colors.textMuted, marginTop: spacing.xs },

    // Complete
    completeCard: { backgroundColor: "rgba(46, 204, 113, 0.06)", borderColor: colors.success },

    // Memory
    memoryCard: { backgroundColor: "rgba(255, 255, 255, 0.02)", borderColor: colors.glassBorder, opacity: 0.85 },
    sourceBadge: { backgroundColor: colors.bgInput, borderRadius: borderRadius.full, paddingHorizontal: spacing.sm, paddingVertical: 2 },
    sourceBadgeText: { fontFamily: "Inter_500Medium", fontSize: fontSize.tiny, color: colors.textDim },
    dateText: { fontFamily: "Inter_400Regular", fontSize: fontSize.tiny, color: colors.textMuted, marginLeft: "auto" },
    memoryContent: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.textDim, lineHeight: 18, fontStyle: "italic" },
    relevanceRow: { flexDirection: "row", alignItems: "center", gap: spacing.xs, marginTop: spacing.sm },
    relevanceDot: { width: 6, height: 6, borderRadius: 3 },
    relevanceText: { fontFamily: "Inter_400Regular", fontSize: fontSize.tiny, color: colors.textMuted },

    // Translation
    translationCard: { backgroundColor: "rgba(232, 113, 44, 0.04)", borderColor: colors.neonBorder },
    translationBlock: { marginBottom: spacing.sm },
    translatedBlock: { backgroundColor: colors.neonGlow, borderRadius: borderRadius.md, padding: spacing.sm },
    translationLabel: { fontFamily: "Inter_500Medium", fontSize: fontSize.tiny, color: colors.textMuted, marginBottom: 2 },
    translationText: { fontFamily: "Inter_400Regular", fontSize: fontSize.sm, color: colors.textDim, lineHeight: 20 },
    copyBtn: { alignSelf: "flex-start", backgroundColor: colors.bgInput, borderRadius: borderRadius.md, paddingHorizontal: spacing.md, paddingVertical: spacing.xs, marginTop: spacing.xs },
    copyBtnText: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.textDim },

    // Calendar
    calendarCard: { backgroundColor: "rgba(59, 130, 246, 0.06)", borderColor: "#3B82F6", borderLeftWidth: 3 },
    calendarDetail: { flexDirection: "row", alignItems: "center", gap: spacing.sm, marginBottom: spacing.xs },
    calendarDetailIcon: { fontSize: 14 },
    calendarDetailText: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.textSecondary },
    prepBtn: { alignSelf: "flex-start", backgroundColor: colors.neonGlow, borderRadius: borderRadius.md, borderWidth: 1, borderColor: colors.neonBorder, paddingHorizontal: spacing.md, paddingVertical: spacing.sm, marginTop: spacing.sm },
    prepBtnText: { fontFamily: "Inter_500Medium", fontSize: fontSize.xs, color: colors.neon },

    // Health
    healthCard: { backgroundColor: "rgba(239, 68, 68, 0.05)", borderColor: "#EF4444", borderLeftWidth: 3 },
    healthStats: { gap: spacing.sm, marginBottom: spacing.sm },
    healthStat: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
    healthStatIcon: { fontSize: 16 },
    healthStatValue: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.md, color: colors.textPrimary },
    healthStatLabel: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.textDim },
    goalBar: { height: 8, backgroundColor: colors.bgInput, borderRadius: 4, overflow: "hidden", marginBottom: spacing.xs },
    goalFill: { height: "100%", borderRadius: 4 },
    goalText: { fontFamily: "Inter_400Regular", fontSize: fontSize.tiny, color: colors.textMuted },

    // Contact
    contactCard: { backgroundColor: "rgba(139, 92, 246, 0.06)", borderColor: "#8B5CF6", borderLeftWidth: 3 },
    contactName: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.md, color: colors.textPrimary, marginBottom: 2 },
    contactOrg: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.textDim, marginBottom: spacing.sm },
    contactDetail: { flexDirection: "row", alignItems: "center", gap: spacing.sm, marginBottom: spacing.xs },
    contactDetailText: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.textSecondary },
    contactActions: { flexDirection: "row", gap: spacing.sm, marginTop: spacing.sm },
    contactActionBtn: { flex: 1, backgroundColor: colors.bgInput, borderRadius: borderRadius.md, paddingVertical: spacing.sm, alignItems: "center" },
    contactActionText: { fontFamily: "Inter_500Medium", fontSize: fontSize.xs, color: colors.textDim },
});
