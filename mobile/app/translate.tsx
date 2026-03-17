/**
 * 🌐 Translate with Ember — Share/Action receiver.
 *
 * Entry points:
 *   Android: Share menu → ACTION_SEND text/plain → opens this screen
 *   iOS:     Action Extension → deep links valhalla://translate?text=...
 *   In-app:  Navigation from tools tab
 *
 * Flow: source text → auto-detect language → pick target → NLLB → copy
 * Translation is ALWAYS user-initiated. No auto-translate.
 */
import { useState, useEffect, useRef } from "react";
import {
    View,
    Text,
    TextInput,
    TouchableOpacity,
    ScrollView,
    StyleSheet,
    Platform,
    Animated,
    ActivityIndicator,
} from "react-native";
import * as Haptics from "expo-haptics";
import * as Clipboard from "expo-clipboard";
import * as Linking from "expo-linking";
import { useRouter, useLocalSearchParams } from "expo-router";
import { companionAPI } from "../src/api";
import { colors, spacing, borderRadius, fontSize, shadows } from "../src/theme";
import { useConnection } from "../src/hooks/useConnection";

// ── Language list with NLLB codes ──
const LANGUAGE_MAP: { label: string; code: string; flag: string }[] = [
    { label: "English", code: "eng_Latn", flag: "🇺🇸" },
    { label: "Spanish", code: "spa_Latn", flag: "🇪🇸" },
    { label: "French", code: "fra_Latn", flag: "🇫🇷" },
    { label: "German", code: "deu_Latn", flag: "🇩🇪" },
    { label: "Portuguese", code: "por_Latn", flag: "🇧🇷" },
    { label: "Italian", code: "ita_Latn", flag: "🇮🇹" },
    { label: "Dutch", code: "nld_Latn", flag: "🇳🇱" },
    { label: "Russian", code: "rus_Cyrl", flag: "🇷🇺" },
    { label: "Chinese", code: "zho_Hans", flag: "🇨🇳" },
    { label: "Japanese", code: "jpn_Jpan", flag: "🇯🇵" },
    { label: "Korean", code: "kor_Hang", flag: "🇰🇷" },
    { label: "Arabic", code: "arb_Arab", flag: "🇸🇦" },
    { label: "Hindi", code: "hin_Deva", flag: "🇮🇳" },
    { label: "Bengali", code: "ben_Beng", flag: "🇧🇩" },
    { label: "Turkish", code: "tur_Latn", flag: "🇹🇷" },
    { label: "Vietnamese", code: "vie_Latn", flag: "🇻🇳" },
    { label: "Thai", code: "tha_Thai", flag: "🇹🇭" },
    { label: "Indonesian", code: "ind_Latn", flag: "🇮🇩" },
    { label: "Polish", code: "pol_Latn", flag: "🇵🇱" },
    { label: "Ukrainian", code: "ukr_Cyrl", flag: "🇺🇦" },
    { label: "Swedish", code: "swe_Latn", flag: "🇸🇪" },
    { label: "Czech", code: "ces_Latn", flag: "🇨🇿" },
    { label: "Greek", code: "ell_Grek", flag: "🇬🇷" },
    { label: "Hebrew", code: "heb_Hebr", flag: "🇮🇱" },
    { label: "Tagalog", code: "tgl_Latn", flag: "🇵🇭" },
    { label: "Swahili", code: "swh_Latn", flag: "🇰🇪" },
    { label: "Tamil", code: "tam_Taml", flag: "🇱🇰" },
    { label: "Urdu", code: "urd_Arab", flag: "🇵🇰" },
    { label: "Persian", code: "pes_Arab", flag: "🇮🇷" },
    { label: "Malay", code: "zsm_Latn", flag: "🇲🇾" },
];

export default function TranslateScreen() {
    const router = useRouter();
    const params = useLocalSearchParams<{ text?: string; source?: string }>();
    const { isOnline, powerState } = useConnection();

    const [inputText, setInputText] = useState("");
    const [targetLang, setTargetLang] = useState(LANGUAGE_MAP[0]); // English default
    const [detectedLang, setDetectedLang] = useState<string | null>(null);
    const [result, setResult] = useState("");
    const [translating, setTranslating] = useState(false);
    const [copied, setCopied] = useState(false);
    const [showAllLangs, setShowAllLangs] = useState(false);
    const [langSearch, setLangSearch] = useState("");

    // Fox mascot animation
    const foxBounce = useRef(new Animated.Value(0)).current;
    useEffect(() => {
        Animated.loop(
            Animated.sequence([
                Animated.timing(foxBounce, { toValue: -4, duration: 1200, useNativeDriver: true }),
                Animated.timing(foxBounce, { toValue: 0, duration: 1200, useNativeDriver: true }),
            ])
        ).start();
    }, [foxBounce]);

    // ── Receive shared text ──
    useEffect(() => {
        // From deep link params (iOS extension → valhalla://translate?text=...)
        if (params.text) {
            setInputText(params.text);
            return;
        }

        // From Android share intent
        const handleUrl = (event: { url: string }) => {
            const parsed = Linking.parse(event.url);
            if (parsed.queryParams?.text) {
                setInputText(String(parsed.queryParams.text));
            }
        };

        // Check initial URL (app opened via share)
        Linking.getInitialURL().then((url) => {
            if (url) handleUrl({ url });
        });

        // Listen for subsequent URLs
        const sub = Linking.addEventListener("url", handleUrl);
        return () => sub.remove();
    }, [params.text]);

    // ── Paste from clipboard ──
    const handlePaste = async () => {
        const text = await Clipboard.getStringAsync();
        if (text?.trim()) {
            setInputText(text);
            Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
        }
    };

    // ── Translate via NLLB ──
    const handleTranslate = async () => {
        if (!inputText.trim() || translating) return;
        setTranslating(true);
        setCopied(false);
        setDetectedLang(null);
        Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);

        try {
            const res = await companionAPI.translate(
                inputText.trim(),
                "auto",
                targetLang.code
            );
            setResult(res.translation || "Translation failed");
            if (res.source_lang) setDetectedLang(res.source_lang);
        } catch {
            setResult("⚠️ Couldn't reach your home PC. Is it online?");
        }
        setTranslating(false);
    };

    // ── Copy result ──
    const handleCopy = async () => {
        if (!result || result.startsWith("⚠️")) return;
        await Clipboard.setStringAsync(result);
        setCopied(true);
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
        // Auto-reset after 2s
        setTimeout(() => setCopied(false), 2000);
    };

    // Filtered languages
    const filteredLangs = langSearch
        ? LANGUAGE_MAP.filter((l) =>
            l.label.toLowerCase().includes(langSearch.toLowerCase())
        )
        : LANGUAGE_MAP;

    // Quick picks (top 8)
    const quickLangs = LANGUAGE_MAP.slice(0, 8);

    return (
        <View style={styles.container}>
            {/* ── Header ── */}
            <View style={styles.header}>
                <TouchableOpacity onPress={() => router.back()} activeOpacity={0.7} hitSlop={12}>
                    <Text style={styles.backBtn}>✕</Text>
                </TouchableOpacity>
                <View style={styles.headerCenter}>
                    <Animated.Text style={[styles.foxIcon, { transform: [{ translateY: foxBounce }] }]}>
                        🦊
                    </Animated.Text>
                    <Text style={styles.headerTitle}>Translate with Ember</Text>
                </View>
                <View style={{ width: 28 }} />
            </View>

            {/* ── Connection badge ── */}
            <View style={styles.connBadge}>
                <Text style={styles.connDot}>
                    {isOnline ? "🟢" : "🔴"}
                </Text>
                <Text style={styles.connText}>
                    {isOnline
                        ? powerState === "home" ? "Connected to home PC" : "Connected via bridge"
                        : "Offline — translation requires PC connection"
                    }
                </Text>
            </View>

            <ScrollView
                contentContainerStyle={styles.content}
                keyboardShouldPersistTaps="handled"
            >
                {/* ── Source text input ── */}
                <View style={styles.inputCard}>
                    <View style={styles.inputHeader}>
                        <Text style={styles.inputLabel}>
                            {detectedLang ? `Detected: ${detectedLang}` : "Source text"}
                        </Text>
                        <TouchableOpacity onPress={handlePaste} activeOpacity={0.7}>
                            <Text style={styles.pasteLink}>📋 Paste</Text>
                        </TouchableOpacity>
                    </View>
                    <TextInput
                        style={styles.input}
                        value={inputText}
                        onChangeText={(t) => { setInputText(t); setResult(""); }}
                        placeholder="Type or paste text to translate..."
                        placeholderTextColor={colors.textMuted}
                        multiline
                        numberOfLines={4}
                        autoFocus={!params.text}
                    />
                    {inputText.length > 0 && (
                        <TouchableOpacity
                            style={styles.clearBtn}
                            onPress={() => { setInputText(""); setResult(""); }}
                            activeOpacity={0.7}
                        >
                            <Text style={styles.clearBtnText}>✕ Clear</Text>
                        </TouchableOpacity>
                    )}
                </View>

                {/* ── Target language ── */}
                <Text style={styles.sectionLabel}>Translate to</Text>

                {/* Quick picks */}
                <ScrollView
                    horizontal
                    showsHorizontalScrollIndicator={false}
                    style={styles.chipScroll}
                    contentContainerStyle={styles.chipScrollContent}
                >
                    {quickLangs.map((lang) => (
                        <TouchableOpacity
                            key={lang.code}
                            style={[styles.chip, targetLang.code === lang.code && styles.chipActive]}
                            onPress={() => {
                                setTargetLang(lang);
                                setResult("");
                                Haptics.selectionAsync();
                            }}
                            activeOpacity={0.7}
                        >
                            <Text style={styles.chipFlag}>{lang.flag}</Text>
                            <Text style={[styles.chipLabel, targetLang.code === lang.code && styles.chipLabelActive]}>
                                {lang.label}
                            </Text>
                        </TouchableOpacity>
                    ))}
                    <TouchableOpacity
                        style={[styles.chip, styles.chipMore]}
                        onPress={() => setShowAllLangs(!showAllLangs)}
                        activeOpacity={0.7}
                    >
                        <Text style={styles.chipLabel}>{showAllLangs ? "Less ▲" : "More ▼"}</Text>
                    </TouchableOpacity>
                </ScrollView>

                {/* All languages dropdown */}
                {showAllLangs && (
                    <View style={styles.langDropdown}>
                        <TextInput
                            style={styles.langSearchInput}
                            value={langSearch}
                            onChangeText={setLangSearch}
                            placeholder="Search 200 languages..."
                            placeholderTextColor={colors.textMuted}
                            autoFocus
                        />
                        <ScrollView style={styles.langList} nestedScrollEnabled>
                            {filteredLangs.map((lang) => (
                                <TouchableOpacity
                                    key={lang.code}
                                    style={[styles.langItem, targetLang.code === lang.code && styles.langItemActive]}
                                    onPress={() => {
                                        setTargetLang(lang);
                                        setShowAllLangs(false);
                                        setLangSearch("");
                                        setResult("");
                                        Haptics.selectionAsync();
                                    }}
                                >
                                    <Text style={styles.langItemFlag}>{lang.flag}</Text>
                                    <Text style={[styles.langItemText, targetLang.code === lang.code && styles.langItemTextActive]}>
                                        {lang.label}
                                    </Text>
                                    {targetLang.code === lang.code && (
                                        <Text style={styles.langItemCheck}>✓</Text>
                                    )}
                                </TouchableOpacity>
                            ))}
                        </ScrollView>
                    </View>
                )}

                {/* ── Translate button ── */}
                <TouchableOpacity
                    style={[
                        styles.translateBtn,
                        (translating || !inputText.trim() || !isOnline) && styles.translateBtnDisabled,
                    ]}
                    onPress={handleTranslate}
                    disabled={translating || !inputText.trim() || !isOnline}
                    activeOpacity={0.7}
                >
                    {translating ? (
                        <View style={styles.translateBtnRow}>
                            <ActivityIndicator size="small" color={colors.bgPrimary} />
                            <Text style={styles.translateBtnText}> Translating...</Text>
                        </View>
                    ) : (
                        <Text style={styles.translateBtnText}>🌐 Translate to {targetLang.flag} {targetLang.label}</Text>
                    )}
                </TouchableOpacity>

                {/* ── Result card ── */}
                {result ? (
                    <View style={[styles.resultCard, result.startsWith("⚠️") && styles.resultCardError]}>
                        <View style={styles.resultHeader}>
                            {detectedLang && (
                                <Text style={styles.resultBadge}>
                                    {detectedLang} → {targetLang.label}
                                </Text>
                            )}
                            <Text style={styles.resultLangBadge}>
                                {targetLang.flag} {targetLang.label}
                            </Text>
                        </View>

                        <Text style={styles.resultText} selectable>{result}</Text>

                        {!result.startsWith("⚠️") && (
                            <TouchableOpacity
                                style={[styles.copyBtn, copied && styles.copyBtnSuccess]}
                                onPress={handleCopy}
                                activeOpacity={0.7}
                            >
                                <Text style={[styles.copyBtnText, copied && styles.copyBtnTextSuccess]}>
                                    {copied ? "✅ Copied to clipboard!" : "📋 Copy translation"}
                                </Text>
                            </TouchableOpacity>
                        )}
                    </View>
                ) : null}

                {/* ── Privacy note ── */}
                <View style={styles.privacyCard}>
                    <Text style={styles.privacyText}>
                        🔒 Powered by NLLB-200 running on your home PC.{"\n"}
                        200 languages · fully offline · no cloud services.{"\n"}
                        Your text never leaves your network.
                    </Text>
                </View>
            </ScrollView>
        </View>
    );
}

const styles = StyleSheet.create({
    container: { flex: 1, backgroundColor: colors.bgPrimary },
    // Header
    header: {
        flexDirection: "row", justifyContent: "space-between", alignItems: "center",
        paddingHorizontal: spacing.lg, paddingTop: Platform.OS === "ios" ? 56 : 44,
        paddingBottom: spacing.md, borderBottomWidth: 1, borderBottomColor: colors.glassBorder,
        backgroundColor: colors.bgPrimary,
    },
    backBtn: { fontSize: 20, color: colors.textMuted, padding: 4 },
    headerCenter: { flexDirection: "row", alignItems: "center", gap: 8 },
    foxIcon: { fontSize: 24 },
    headerTitle: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.md, color: colors.textPrimary },
    // Connection badge
    connBadge: {
        flexDirection: "row", alignItems: "center", gap: 6,
        paddingHorizontal: spacing.lg, paddingVertical: spacing.sm,
        backgroundColor: "rgba(255,255,255,0.02)", borderBottomWidth: 1, borderBottomColor: colors.glassBorder,
    },
    connDot: { fontSize: 8 },
    connText: { fontFamily: "Inter_400Regular", fontSize: fontSize.tiny, color: colors.textDim },
    // Content
    content: { paddingHorizontal: spacing.lg, paddingTop: spacing.lg, paddingBottom: spacing.xxxl },
    // Input card
    inputCard: {
        backgroundColor: colors.bgCard, borderRadius: borderRadius.lg, borderWidth: 1,
        borderColor: colors.glassBorder, padding: spacing.lg, marginBottom: spacing.lg,
    },
    inputHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: spacing.sm },
    inputLabel: { fontFamily: "Inter_500Medium", fontSize: fontSize.tiny, color: colors.textDim },
    pasteLink: { fontFamily: "Inter_400Regular", fontSize: fontSize.tiny, color: colors.neon },
    input: {
        fontFamily: "Inter_400Regular", fontSize: fontSize.sm, color: colors.textPrimary,
        minHeight: 80, textAlignVertical: "top", lineHeight: 22,
    },
    clearBtn: { alignSelf: "flex-end", marginTop: spacing.xs },
    clearBtnText: { fontFamily: "Inter_400Regular", fontSize: fontSize.tiny, color: colors.textMuted },
    // Language chips
    sectionLabel: { fontFamily: "Inter_500Medium", fontSize: fontSize.xs, color: colors.textDim, marginBottom: spacing.sm },
    chipScroll: { marginBottom: spacing.lg },
    chipScrollContent: { gap: spacing.sm },
    chip: {
        flexDirection: "row", alignItems: "center", gap: 4,
        paddingHorizontal: spacing.md, paddingVertical: spacing.sm,
        borderRadius: borderRadius.full, backgroundColor: colors.bgCard,
        borderWidth: 1, borderColor: colors.glassBorder,
    },
    chipActive: { backgroundColor: "rgba(232,113,44,0.12)", borderColor: colors.neon },
    chipMore: { borderStyle: "dashed" as any },
    chipFlag: { fontSize: 14 },
    chipLabel: { fontFamily: "Inter_400Regular", fontSize: fontSize.tiny, color: colors.textDim },
    chipLabelActive: { color: colors.neon, fontFamily: "Inter_500Medium" },
    // Language dropdown
    langDropdown: {
        backgroundColor: colors.bgCard, borderRadius: borderRadius.md, borderWidth: 1,
        borderColor: colors.glassBorder, marginBottom: spacing.lg, maxHeight: 260,
    },
    langSearchInput: {
        fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.textPrimary,
        paddingHorizontal: spacing.md, paddingVertical: spacing.sm,
        borderBottomWidth: 1, borderBottomColor: colors.glassBorder,
    },
    langList: { maxHeight: 200 },
    langItem: {
        flexDirection: "row", alignItems: "center", gap: spacing.sm,
        paddingVertical: spacing.sm, paddingHorizontal: spacing.md,
    },
    langItemActive: { backgroundColor: "rgba(232,113,44,0.06)" },
    langItemFlag: { fontSize: 16 },
    langItemText: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.textSecondary, flex: 1 },
    langItemTextActive: { color: colors.neon, fontFamily: "Inter_500Medium" },
    langItemCheck: { color: colors.neon, fontSize: fontSize.sm },
    // Translate button
    translateBtn: {
        backgroundColor: colors.neon, borderRadius: borderRadius.md,
        paddingVertical: spacing.lg, alignItems: "center", marginBottom: spacing.lg,
        ...shadows.glow,
    },
    translateBtnDisabled: { opacity: 0.35 },
    translateBtnRow: { flexDirection: "row", alignItems: "center" },
    translateBtnText: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.md, color: colors.bgPrimary },
    // Result card
    resultCard: {
        backgroundColor: "rgba(232,113,44,0.06)", borderWidth: 1, borderColor: colors.neonBorder,
        borderRadius: borderRadius.lg, padding: spacing.xl, marginBottom: spacing.lg,
    },
    resultCardError: { borderColor: "rgba(239,68,68,0.3)", backgroundColor: "rgba(239,68,68,0.05)" },
    resultHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: spacing.md },
    resultBadge: {
        fontFamily: "Inter_400Regular", fontSize: fontSize.tiny, color: colors.textDim,
        backgroundColor: "rgba(255,255,255,0.05)", paddingHorizontal: spacing.sm, paddingVertical: 2, borderRadius: borderRadius.sm,
    },
    resultLangBadge: {
        fontFamily: "Inter_500Medium", fontSize: fontSize.tiny, color: colors.neon,
        backgroundColor: "rgba(232,113,44,0.1)", paddingHorizontal: spacing.sm, paddingVertical: 2, borderRadius: borderRadius.sm,
    },
    resultText: { fontFamily: "Inter_400Regular", fontSize: fontSize.md, color: colors.textPrimary, lineHeight: 26, marginBottom: spacing.md },
    // Copy button
    copyBtn: {
        backgroundColor: colors.neon, borderRadius: borderRadius.md,
        paddingVertical: spacing.md, alignItems: "center",
    },
    copyBtnSuccess: { backgroundColor: "#22c55e" },
    copyBtnText: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.sm, color: colors.bgPrimary },
    copyBtnTextSuccess: { color: "#ffffff" },
    // Privacy
    privacyCard: {
        backgroundColor: "rgba(255,255,255,0.02)", borderRadius: borderRadius.md,
        padding: spacing.md, borderWidth: 1, borderColor: "rgba(255,255,255,0.04)",
    },
    privacyText: {
        fontFamily: "Inter_400Regular", fontSize: fontSize.tiny, color: colors.textDim,
        textAlign: "center", lineHeight: 18,
    },
});
