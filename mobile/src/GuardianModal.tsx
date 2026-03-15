/**
 * 🛡️ Message Guardian — Sprint 4 Task 3.
 *
 * Before sending a chat message, checks with the guardian API.
 * If unsafe, shows a friendly warning modal with optional rewrite.
 * Feels like a friend warning you, not a firewall.
 */
import { useState } from "react";
import {
    View,
    Text,
    TouchableOpacity,
    StyleSheet,
    Modal,
} from "react-native";
import * as Haptics from "expo-haptics";
import { colors, spacing, borderRadius, fontSize } from "./theme";
import type { PetSpecies } from "./types";

const GUARDIAN_INTROS: Record<PetSpecies, string> = {
    cat: "Are you sure? It's late and this seems... emotional.",
    dog: "Hey friend!! Maybe wait a bit? I love you but this seems hasty!!",
    penguin: "Per protocol, I recommend reviewing this message before sending.",
    fox: "Hmm... I'd sleep on this one. Trust me.",
    owl: "Wisdom suggests restraint. Consider the timing.",
    dragon: "HOLD YOUR FIRE! Even I know timing matters!",
};

interface GuardianResult {
    safe: boolean;
    reason?: string;
    suggestedRewrite?: string;
    sentiment?: string;
}

interface GuardianModalProps {
    visible: boolean;
    species: PetSpecies;
    petName: string;
    originalMessage: string;
    guardianResult: GuardianResult;
    onSendAnyway: () => void;
    onUseRewrite: (rewrite: string) => void;
    onCancel: () => void;
}

export default function GuardianModal({
    visible,
    species,
    petName,
    originalMessage,
    guardianResult,
    onSendAnyway,
    onUseRewrite,
    onCancel,
}: GuardianModalProps) {
    return (
        <Modal visible={visible} transparent animationType="slide">
            <View style={styles.overlay}>
                <View style={styles.card}>
                    {/* Header */}
                    <Text style={styles.emoji}>🛡️</Text>
                    <Text style={styles.title}>{petName} says...</Text>
                    <Text style={styles.intro}>{GUARDIAN_INTROS[species]}</Text>

                    {/* Reason */}
                    {guardianResult.reason && (
                        <View style={styles.reasonBox}>
                            <Text style={styles.reasonText}>{guardianResult.reason}</Text>
                        </View>
                    )}

                    {/* Original message preview */}
                    <View style={styles.messagePreview}>
                        <Text style={styles.previewLabel}>Your message:</Text>
                        <Text style={styles.previewText} numberOfLines={3}>
                            {originalMessage}
                        </Text>
                    </View>

                    {/* Suggested rewrite */}
                    {guardianResult.suggestedRewrite && (
                        <View style={styles.rewriteBox}>
                            <Text style={styles.rewriteLabel}>💡 Softer version:</Text>
                            <Text style={styles.rewriteText}>
                                {guardianResult.suggestedRewrite}
                            </Text>
                            <TouchableOpacity
                                style={styles.rewriteBtn}
                                onPress={() => {
                                    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
                                    onUseRewrite(guardianResult.suggestedRewrite!);
                                }}
                                activeOpacity={0.7}
                            >
                                <Text style={styles.rewriteBtnText}>Use This Instead</Text>
                            </TouchableOpacity>
                        </View>
                    )}

                    {/* Actions */}
                    <View style={styles.actions}>
                        <TouchableOpacity
                            style={styles.cancelBtn}
                            onPress={() => {
                                Haptics.selectionAsync();
                                onCancel();
                            }}
                            activeOpacity={0.7}
                        >
                            <Text style={styles.cancelBtnText}>Don't Send</Text>
                        </TouchableOpacity>
                        <TouchableOpacity
                            style={styles.sendAnywayBtn}
                            onPress={() => {
                                Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
                                onSendAnyway();
                            }}
                            activeOpacity={0.7}
                        >
                            <Text style={styles.sendAnywayText}>Send Anyway</Text>
                        </TouchableOpacity>
                    </View>
                </View>
            </View>
        </Modal>
    );
}

const styles = StyleSheet.create({
    overlay: { flex: 1, justifyContent: "flex-end", backgroundColor: "rgba(0,0,0,0.6)" },
    card: { backgroundColor: colors.bgSecondary, borderTopLeftRadius: borderRadius.xl, borderTopRightRadius: borderRadius.xl, padding: spacing.xxl, paddingBottom: 50 },
    emoji: { fontSize: 32, textAlign: "center", marginBottom: spacing.sm },
    title: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.lg, color: colors.textPrimary, textAlign: "center", marginBottom: spacing.xs },
    intro: { fontFamily: "Inter_400Regular", fontSize: fontSize.sm, color: colors.textSecondary, textAlign: "center", fontStyle: "italic", marginBottom: spacing.lg, lineHeight: 20 },
    reasonBox: { backgroundColor: "rgba(255,165,0,0.08)", borderWidth: 1, borderColor: "rgba(255,165,0,0.2)", borderRadius: borderRadius.md, padding: spacing.md, marginBottom: spacing.md },
    reasonText: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.warning },
    messagePreview: { backgroundColor: colors.bgInput, borderRadius: borderRadius.md, padding: spacing.md, marginBottom: spacing.md },
    previewLabel: { fontFamily: "Inter_400Regular", fontSize: fontSize.tiny, color: colors.textMuted, marginBottom: spacing.xs },
    previewText: { fontFamily: "Inter_400Regular", fontSize: fontSize.sm, color: colors.textSecondary },
    rewriteBox: { backgroundColor: colors.neonGlow, borderWidth: 1, borderColor: colors.neonBorder, borderRadius: borderRadius.md, padding: spacing.md, marginBottom: spacing.lg },
    rewriteLabel: { fontFamily: "Inter_400Regular", fontSize: fontSize.tiny, color: colors.neon, marginBottom: spacing.xs },
    rewriteText: { fontFamily: "Inter_400Regular", fontSize: fontSize.sm, color: colors.textSecondary, lineHeight: 20, marginBottom: spacing.sm },
    rewriteBtn: { backgroundColor: colors.neon, borderRadius: borderRadius.sm, paddingVertical: spacing.sm, alignItems: "center" },
    rewriteBtnText: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.xs, color: colors.bgPrimary },
    actions: { flexDirection: "row", gap: spacing.md },
    cancelBtn: { flex: 1, backgroundColor: colors.bgCard, borderRadius: borderRadius.md, paddingVertical: spacing.md, alignItems: "center" },
    cancelBtnText: { fontFamily: "Inter_500Medium", fontSize: fontSize.sm, color: colors.textDim },
    sendAnywayBtn: { flex: 1, backgroundColor: "rgba(255,68,102,0.15)", borderWidth: 1, borderColor: "rgba(255,68,102,0.3)", borderRadius: borderRadius.md, paddingVertical: spacing.md, alignItems: "center" },
    sendAnywayText: { fontFamily: "Inter_500Medium", fontSize: fontSize.sm, color: colors.danger },
});
