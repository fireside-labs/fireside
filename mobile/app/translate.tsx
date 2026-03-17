/**
 * 🌐 Share/Translate — Receives shared text from other apps.
 *
 * Android: Intent filter catches ACTION_SEND text/plain → opens this screen.
 * iOS: Share Extension / Action Extension → deep links here.
 *
 * Shows: shared text → language selector → translate → copy result.
 */
import { useState, useEffect } from "react";
import {
    View,
    Text,
    TextInput,
    TouchableOpacity,
    ScrollView,
    StyleSheet,
    Platform,
} from "react-native";
import * as Haptics from "expo-haptics";
import * as Clipboard from "expo-clipboard";
import * as Linking from "expo-linking";
import { useRouter, useLocalSearchParams } from "expo-router";
import { companionAPI } from "../src/api";
import { colors, spacing, borderRadius, fontSize, shadows } from "../src/theme";

const TOP_LANGUAGES = [
    "Spanish", "French", "German", "Portuguese", "Italian",
    "Chinese (Simplified)", "Japanese", "Korean", "Arabic", "Hindi",
    "Russian", "Dutch", "Turkish", "Vietnamese", "Thai",
];

export default function ShareTranslateScreen() {
    const router = useRouter();
    const params = useLocalSearchParams<{ text?: string }>();
    const [inputText, setInputText] = useState(params.text || "");
    const [targetLang, setTargetLang] = useState("Spanish");
    const [result, setResult] = useState("");
    const [translating, setTranslating] = useState(false);
    const [copied, setCopied] = useState(false);

    // Auto-translate if text was shared in
    useEffect(() => {
        if (params.text && params.text.trim()) {
            setInputText(params.text);
        }
    }, [params.text]);

    const handleTranslate = async () => {
        if (!inputText.trim() || translating) return;
        setTranslating(true);
        setCopied(false);
        Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);

        try {
            const res = await companionAPI.translate(inputText, "auto", targetLang);
            setResult(res.translation || "Translation failed");
        } catch {
            setResult("⚠️ Couldn't reach your home PC. Is it online?");
        }
        setTranslating(false);
    };

    const handleCopy = async () => {
        if (result) {
            await Clipboard.setStringAsync(result);
            setCopied(true);
            Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
        }
    };

    return (
        <View style={styles.container}>
            {/* Header */}
            <View style={styles.header}>
                <TouchableOpacity onPress={() => router.back()} activeOpacity={0.7}>
                    <Text style={styles.backBtn}>✕</Text>
                </TouchableOpacity>
                <Text style={styles.headerTitle}>🦊 Translate with Ember</Text>
                <View style={{ width: 24 }} />
            </View>

            <ScrollView contentContainerStyle={styles.content}>
                {/* Input */}
                <TextInput
                    style={styles.input}
                    value={inputText}
                    onChangeText={setInputText}
                    placeholder="Text to translate..."
                    placeholderTextColor={colors.textMuted}
                    multiline
                    numberOfLines={4}
                    autoFocus={!params.text}
                />

                {/* Quick language chips */}
                <Text style={styles.langLabel}>Translate to:</Text>
                <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.langScroll}>
                    {TOP_LANGUAGES.map((lang) => (
                        <TouchableOpacity
                            key={lang}
                            style={[styles.langChip, targetLang === lang && styles.langChipActive]}
                            onPress={() => {
                                setTargetLang(lang);
                                Haptics.selectionAsync();
                            }}
                            activeOpacity={0.7}
                        >
                            <Text style={[styles.langChipText, targetLang === lang && styles.langChipTextActive]}>
                                {lang}
                            </Text>
                        </TouchableOpacity>
                    ))}
                </ScrollView>

                {/* Translate button */}
                <TouchableOpacity
                    style={[styles.translateBtn, (translating || !inputText.trim()) && styles.translateBtnDisabled]}
                    onPress={handleTranslate}
                    disabled={translating || !inputText.trim()}
                    activeOpacity={0.7}
                >
                    <Text style={styles.translateBtnText}>
                        {translating ? "Translating..." : "🌐 Translate"}
                    </Text>
                </TouchableOpacity>

                {/* Result */}
                {result ? (
                    <View style={styles.resultCard}>
                        <View style={styles.resultHeader}>
                            <Text style={styles.resultLangBadge}>{targetLang}</Text>
                        </View>
                        <Text style={styles.resultText}>{result}</Text>
                        <TouchableOpacity
                            style={styles.copyBtn}
                            onPress={handleCopy}
                            activeOpacity={0.7}
                        >
                            <Text style={styles.copyBtnText}>
                                {copied ? "✅ Copied!" : "📋 Copy translation"}
                            </Text>
                        </TouchableOpacity>
                    </View>
                ) : null}

                {/* Info */}
                <Text style={styles.infoText}>
                    🔒 Powered by NLLB-200 running locally on your PC.
                    No text is sent to external services.
                </Text>
            </ScrollView>
        </View>
    );
}

const styles = StyleSheet.create({
    container: { flex: 1, backgroundColor: colors.bgPrimary },
    header: {
        flexDirection: "row", justifyContent: "space-between", alignItems: "center",
        paddingHorizontal: spacing.lg, paddingTop: Platform.OS === "ios" ? 56 : 40,
        paddingBottom: spacing.md, borderBottomWidth: 1, borderBottomColor: colors.glassBorder,
    },
    backBtn: { fontSize: 20, color: colors.textMuted },
    headerTitle: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.md, color: colors.textPrimary },
    content: { paddingHorizontal: spacing.lg, paddingTop: spacing.lg, paddingBottom: spacing.xxxl },
    input: {
        backgroundColor: colors.bgCard, borderRadius: borderRadius.md, borderWidth: 1,
        borderColor: colors.glassBorder, paddingHorizontal: spacing.lg, paddingVertical: spacing.lg,
        fontFamily: "Inter_400Regular", fontSize: fontSize.sm, color: colors.textPrimary,
        minHeight: 100, textAlignVertical: "top", marginBottom: spacing.md,
    },
    langLabel: { fontFamily: "Inter_500Medium", fontSize: fontSize.xs, color: colors.textDim, marginBottom: spacing.sm },
    langScroll: { marginBottom: spacing.lg },
    langChip: {
        paddingHorizontal: spacing.md, paddingVertical: spacing.sm, borderRadius: borderRadius.full,
        backgroundColor: colors.bgCard, borderWidth: 1, borderColor: colors.glassBorder, marginRight: spacing.sm,
    },
    langChipActive: { backgroundColor: colors.neonGlow, borderColor: colors.neon },
    langChipText: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.textDim },
    langChipTextActive: { color: colors.neon },
    translateBtn: { backgroundColor: colors.neon, borderRadius: borderRadius.md, paddingVertical: spacing.lg, alignItems: "center", marginBottom: spacing.lg, ...shadows.glow },
    translateBtnDisabled: { opacity: 0.4 },
    translateBtnText: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.md, color: colors.bgPrimary },
    resultCard: { backgroundColor: colors.neonGlow, borderWidth: 1, borderColor: colors.neonBorder, borderRadius: borderRadius.lg, padding: spacing.xl, marginBottom: spacing.lg },
    resultHeader: { flexDirection: "row", justifyContent: "flex-end", marginBottom: spacing.sm },
    resultLangBadge: { fontFamily: "Inter_500Medium", fontSize: fontSize.tiny, color: colors.neon, backgroundColor: "rgba(232,113,44,0.1)", paddingHorizontal: spacing.sm, paddingVertical: 2, borderRadius: borderRadius.sm },
    resultText: { fontFamily: "Inter_400Regular", fontSize: fontSize.md, color: colors.textPrimary, lineHeight: 24, marginBottom: spacing.md },
    copyBtn: { backgroundColor: colors.neon, borderRadius: borderRadius.md, paddingVertical: spacing.md, alignItems: "center" },
    copyBtnText: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.sm, color: colors.bgPrimary },
    infoText: { fontFamily: "Inter_400Regular", fontSize: fontSize.tiny, color: colors.textDim, textAlign: "center", lineHeight: 16, marginTop: spacing.md },
});
