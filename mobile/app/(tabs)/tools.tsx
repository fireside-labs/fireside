/**
 * 🔧 Tools Tab — Executive mode utilities.
 *
 * Translation is USER-INITIATED via action menu or paste.
 * DO NOT auto-translate. Users may speak multiple languages.
 * Contains: Platform card, URL summary, Translation, TeachMe.
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
    Image,
} from "react-native";
import * as Haptics from "expo-haptics";
import * as Clipboard from "expo-clipboard";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { useConnection } from "../../src/hooks/useConnection";
import { companionAPI } from "../../src/api";
import { colors, spacing, borderRadius, fontSize, shadows } from "../../src/theme";
import UrlSummary from "../../src/UrlSummary";
import type { PetSpecies } from "../../src/types";

// ———— TeachMe ————

const CONFIRM_RESPONSES: Record<PetSpecies, (fact: string) => string> = {
    cat: (f) => `*yawns* Fine. I'll remember "${f}." Don't expect me to care.`,
    dog: (f) => `OH WOW!! "${f}" — GOT IT!! I'll NEVER forget!! Promise!! 🎾`,
    penguin: (f) => `Noted. "${f}" has been filed under Personal Facts, subsection User Preferences.`,
    fox: (f) => `*ears perk up* Interesting... "${f}." I'll keep that one close.`,
    owl: (f) => `Wisdom shared is wisdom doubled. "${f}" — archived in the library of knowing.`,
    dragon: (f) => `"${f}" — INSCRIBED INTO THE HOARD OF KNOWLEDGE! It shall not be forgotten!`,
};
const TEACH_FACTS_KEY = "fireside_taught_facts";

// ———— Language list (top 30 — full 200 from API) ————
const LANGUAGES = [
    "English", "Spanish", "French", "German", "Portuguese", "Italian", "Dutch",
    "Russian", "Chinese (Simplified)", "Chinese (Traditional)", "Japanese", "Korean",
    "Arabic", "Hindi", "Bengali", "Urdu", "Turkish", "Vietnamese", "Thai", "Indonesian",
    "Malay", "Swahili", "Polish", "Ukrainian", "Czech", "Romanian", "Greek", "Hebrew",
    "Persian", "Swedish", "Norwegian", "Danish", "Finnish", "Hungarian", "Tagalog",
    "Catalan", "Croatian", "Serbian", "Slovak", "Slovenian", "Bulgarian", "Lithuanian",
    "Latvian", "Estonian", "Icelandic", "Welsh", "Irish", "Basque", "Galician", "Tamil",
    "Telugu", "Kannada", "Malayalam", "Marathi", "Gujarati", "Punjabi", "Sinhala",
    "Burmese", "Khmer", "Lao", "Georgian", "Armenian", "Amharic", "Yoruba", "Zulu",
];

export default function ToolsTab() {
    const { isOnline, companionData } = useConnection();
    const [refreshing, setRefreshing] = useState(false);

    const petName = companionData?.companion?.name || "Companion";
    const species = (companionData?.companion?.species || "cat") as PetSpecies;
    const platform = companionData?.platform;

    // ———— Teach Me state ————
    const [teachInput, setTeachInput] = useState("");
    const [teachConfirm, setTeachConfirm] = useState<string | null>(null);
    const [factCount, setFactCount] = useState(0);

    // Load fact count on mount
    useEffect(() => {
        AsyncStorage.getItem(TEACH_FACTS_KEY).then((v) => {
            if (v) try { setFactCount(JSON.parse(v).length); } catch { }
        });
    }, []);

    const handleTeach = async () => {
        if (!teachInput.trim()) return;
        const fact = teachInput.trim();
        Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);

        // Store locally
        const raw = await AsyncStorage.getItem(TEACH_FACTS_KEY);
        const facts = raw ? JSON.parse(raw) : [];
        facts.push({ fact, timestamp: Date.now() });
        await AsyncStorage.setItem(TEACH_FACTS_KEY, JSON.stringify(facts));
        setFactCount(facts.length);

        // API call
        if (isOnline) {
            try { await companionAPI.teach(fact); } catch { }
        }

        setTeachConfirm(CONFIRM_RESPONSES[species](fact));
        setTeachInput("");
        setTimeout(() => setTeachConfirm(null), 4000);
    };

    // ———— Translation state ————
    const [translateInput, setTranslateInput] = useState("");
    const [sourceLang, setSourceLang] = useState("auto");
    const [targetLang, setTargetLang] = useState("Spanish");
    const [translateResult, setTranslateResult] = useState("");
    const [translateConfidence, setTranslateConfidence] = useState<number | null>(null);
    const [translating, setTranslating] = useState(false);
    const [langSearch, setLangSearch] = useState("");
    const [showLangPicker, setShowLangPicker] = useState<"source" | "target" | null>(null);

    const filteredLangs = LANGUAGES.filter((l) =>
        l.toLowerCase().includes(langSearch.toLowerCase())
    );

    const handleTranslate = async () => {
        if (!translateInput.trim() || translating) return;
        setTranslating(true);
        Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);

        try {
            const res = await companionAPI.translate(translateInput, sourceLang, targetLang);
            setTranslateResult(res.translated || "Translation failed");
            setTranslateConfidence(res.confidence || null);
        } catch {
            setTranslateResult("⚠️ Translation service unavailable. Is your home PC online?");
            setTranslateConfidence(null);
        }
        setTranslating(false);
    };

    const handleCopyResult = () => {
        if (translateResult) {
            Clipboard.setStringAsync(translateResult);
            Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
        }
    };

    const onRefresh = useCallback(async () => {
        setRefreshing(true);
        try { await companionAPI.sync(); } catch { }
        setRefreshing(false);
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
    }, []);

    return (
        <ScrollView
            style={styles.container}
            contentContainerStyle={styles.content}
            refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.neon} />}
        >
            <Text style={styles.title}>🔧 Tools</Text>
            <Text style={styles.subtitle}>{petName}'s utility toolkit</Text>

            {/* ———— What's Happening at Home ———— */}
            <View style={styles.card}>
                <Text style={styles.cardTitle}>🏠 Your Home PC</Text>
                {isOnline && platform ? (
                    <View>
                        {platform.uptime && (
                            <Text style={styles.statLine}>⏱️ Uptime: {typeof platform.uptime === "number" ? `${(platform.uptime / 3600).toFixed(1)} hours` : platform.uptime}</Text>
                        )}
                        {platform.models_loaded && (
                            <Text style={styles.statLine}>🧠 Models: {Array.isArray(platform.models_loaded) ? platform.models_loaded.join(", ") : platform.models_loaded}</Text>
                        )}
                        {platform.memory_count != null && (
                            <Text style={styles.statLine}>💭 Memories: {platform.memory_count} stored</Text>
                        )}
                        {platform.mesh_nodes != null && (
                            <Text style={styles.statLine}>🌐 Mesh nodes: {platform.mesh_nodes}</Text>
                        )}
                        {platform.last_dream && (
                            <Text style={styles.statLine}>🌙 Last dream: {platform.last_dream}</Text>
                        )}
                        {!platform.uptime && !platform.models_loaded && (
                            <Text style={styles.statLine}>Connected — waiting for status data...</Text>
                        )}
                    </View>
                ) : (
                    <Text style={styles.offlineText}>
                        Your home PC is offline. Your companion is running on cached data.
                    </Text>
                )}
            </View>

            {/* ———— URL Summary ———— */}
            <UrlSummary petName={petName} isOnline={isOnline} />

            {/* ———— Translation (User-Initiated Action Menu) ———— */}
            <View style={styles.card}>
                <Text style={styles.cardTitle}>🌐 Translate with {petName}</Text>
                <Text style={styles.cardSubtitle}>
                    200 languages · NLLB-200 · User-initiated only
                </Text>
                <Text style={styles.actionNote}>
                    📱 Shared text from other apps appears here automatically.
                    Or paste text below to translate.
                </Text>

                {/* Language selectors */}
                <View style={styles.langRow}>
                    <TouchableOpacity
                        style={styles.langBtn}
                        onPress={() => { setShowLangPicker("source"); setLangSearch(""); }}
                        activeOpacity={0.7}
                    >
                        <Text style={styles.langBtnText}>
                            {sourceLang === "auto" ? "🔍 Auto-detect" : sourceLang}
                        </Text>
                    </TouchableOpacity>
                    <Text style={styles.langArrow}>→</Text>
                    <TouchableOpacity
                        style={styles.langBtn}
                        onPress={() => { setShowLangPicker("target"); setLangSearch(""); }}
                        activeOpacity={0.7}
                    >
                        <Text style={styles.langBtnText}>{targetLang}</Text>
                    </TouchableOpacity>
                </View>

                {/* Language picker dropdown */}
                {showLangPicker && (
                    <View style={styles.langPicker}>
                        <TextInput
                            style={styles.langSearchInput}
                            placeholder="Search languages..."
                            placeholderTextColor={colors.textMuted}
                            value={langSearch}
                            onChangeText={setLangSearch}
                            autoFocus
                        />
                        <ScrollView style={styles.langList} nestedScrollEnabled>
                            {showLangPicker === "source" && (
                                <TouchableOpacity
                                    style={styles.langItem}
                                    onPress={() => { setSourceLang("auto"); setShowLangPicker(null); }}
                                >
                                    <Text style={styles.langItemText}>🔍 Auto-detect</Text>
                                </TouchableOpacity>
                            )}
                            {filteredLangs.map((lang) => (
                                <TouchableOpacity
                                    key={lang}
                                    style={styles.langItem}
                                    onPress={() => {
                                        if (showLangPicker === "source") setSourceLang(lang);
                                        else setTargetLang(lang);
                                        setShowLangPicker(null);
                                        Haptics.selectionAsync();
                                    }}
                                >
                                    <Text style={styles.langItemText}>{lang}</Text>
                                </TouchableOpacity>
                            ))}
                        </ScrollView>
                    </View>
                )}

                {/* Text input */}
                <TextInput
                    style={styles.translateInput}
                    value={translateInput}
                    onChangeText={setTranslateInput}
                    placeholder="Type text to translate..."
                    placeholderTextColor={colors.textMuted}
                    multiline
                    numberOfLines={3}
                />

                <TouchableOpacity
                    style={[styles.translateBtn, translating && { opacity: 0.5 }]}
                    onPress={handleTranslate}
                    disabled={translating || !translateInput.trim()}
                    activeOpacity={0.7}
                >
                    <Text style={styles.translateBtnText}>
                        {translating ? "Translating..." : "🌐 Translate"}
                    </Text>
                </TouchableOpacity>

                {/* Paste from clipboard */}
                <TouchableOpacity
                    style={styles.pasteBtn}
                    onPress={async () => {
                        const text = await Clipboard.getStringAsync();
                        if (text) {
                            setTranslateInput(text);
                            Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
                        }
                    }}
                    activeOpacity={0.7}
                >
                    <Text style={styles.pasteBtnText}>📋 Paste from clipboard</Text>
                </TouchableOpacity>

                {/* Result */}
                {translateResult ? (
                    <View style={styles.translateResult}>
                        <Text style={styles.translateResultText}>{translateResult}</Text>
                        {translateConfidence != null && (
                            <Text style={styles.confidenceText}>
                                Confidence: {(translateConfidence * 100).toFixed(0)}%
                            </Text>
                        )}
                        <TouchableOpacity
                            style={styles.copyBtn}
                            onPress={handleCopyResult}
                            activeOpacity={0.7}
                        >
                            <Text style={styles.copyBtnText}>📋 Copy</Text>
                        </TouchableOpacity>
                    </View>
                ) : null}
            </View>

            {/* ———— Teach Me ———— */}
            <View style={styles.card}>
                <Text style={styles.cardTitle}>💡 Teach {petName}</Text>
                <Text style={styles.cardSubtitle}>
                    {factCount > 0
                        ? `${factCount} fact${factCount === 1 ? "" : "s"} learned · Teach more`
                        : "Tell your companion something to remember"}
                </Text>

                {teachConfirm ? (
                    <View style={styles.confirmBox}>
                        <Text style={styles.confirmText}>{teachConfirm}</Text>
                        <Text style={styles.confirmCount}>
                            📚 {factCount} fact{factCount === 1 ? "" : "s"} learned total
                        </Text>
                    </View>
                ) : (
                    <View>
                        <TextInput
                            style={styles.teachInput}
                            value={teachInput}
                            onChangeText={setTeachInput}
                            placeholder="I'm allergic to shellfish..."
                            placeholderTextColor={colors.textMuted}
                            onSubmitEditing={handleTeach}
                            returnKeyType="done"
                        />
                        <TouchableOpacity
                            style={[styles.teachBtn, !teachInput.trim() && { opacity: 0.3 }]}
                            onPress={handleTeach}
                            disabled={!teachInput.trim()}
                            activeOpacity={0.7}
                        >
                            <Text style={styles.teachBtnText}>Remember</Text>
                        </TouchableOpacity>
                    </View>
                )}
            </View>
        </ScrollView>
    );
}

const styles = StyleSheet.create({
    container: { flex: 1, backgroundColor: colors.bgPrimary },
    content: { paddingHorizontal: spacing.lg, paddingTop: 60, paddingBottom: spacing.xxxl },
    title: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.xl, color: colors.textPrimary, marginBottom: 2 },
    subtitle: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.textDim, marginBottom: spacing.xl },
    // Cards
    card: { backgroundColor: colors.bgCard, borderRadius: borderRadius.lg, borderWidth: 1, borderColor: colors.glassBorder, padding: spacing.xl, marginBottom: spacing.lg, ...shadows.card },
    cardTitle: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.md, color: colors.textPrimary, marginBottom: spacing.xs },
    cardSubtitle: { fontFamily: "Inter_400Regular", fontSize: fontSize.tiny, color: colors.textDim, marginBottom: spacing.md },
    // Platform card
    statLine: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.textSecondary, lineHeight: 22 },
    offlineText: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.textMuted, fontStyle: "italic" },
    actionNote: { fontFamily: "Inter_400Regular", fontSize: fontSize.tiny, color: colors.textMuted, marginBottom: spacing.md, lineHeight: 16 },
    pasteBtn: { backgroundColor: colors.bgInput, borderRadius: borderRadius.md, paddingVertical: spacing.sm, alignItems: "center", marginBottom: spacing.md, borderWidth: 1, borderColor: colors.glassBorder },
    pasteBtnText: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.textDim },
    // Translation
    langRow: { flexDirection: "row", alignItems: "center", gap: spacing.sm, marginBottom: spacing.md },
    langBtn: { flex: 1, backgroundColor: colors.bgInput, borderRadius: borderRadius.md, paddingVertical: spacing.sm + 2, paddingHorizontal: spacing.md, borderWidth: 1, borderColor: colors.glassBorder },
    langBtnText: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.textSecondary, textAlign: "center" },
    langArrow: { fontFamily: "Inter_400Regular", fontSize: fontSize.md, color: colors.textMuted },
    langPicker: { backgroundColor: colors.bgInput, borderRadius: borderRadius.md, borderWidth: 1, borderColor: colors.glassBorder, padding: spacing.sm, marginBottom: spacing.md, maxHeight: 200 },
    langSearchInput: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.textPrimary, paddingHorizontal: spacing.sm, paddingVertical: spacing.xs, borderBottomWidth: 1, borderBottomColor: colors.glassBorder, marginBottom: spacing.xs },
    langList: { maxHeight: 150 },
    langItem: { paddingVertical: spacing.sm, paddingHorizontal: spacing.sm },
    langItemText: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.textSecondary },
    translateInput: { backgroundColor: colors.bgInput, borderRadius: borderRadius.md, borderWidth: 1, borderColor: colors.glassBorder, paddingHorizontal: spacing.md, paddingVertical: spacing.md, fontFamily: "Inter_400Regular", fontSize: fontSize.sm, color: colors.textPrimary, minHeight: 80, textAlignVertical: "top", marginBottom: spacing.md },
    translateBtn: { backgroundColor: colors.neon, borderRadius: borderRadius.md, paddingVertical: spacing.md, alignItems: "center", marginBottom: spacing.md, ...shadows.glow },
    translateBtnText: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.sm, color: colors.bgPrimary },
    translateResult: { backgroundColor: colors.neonGlow, borderWidth: 1, borderColor: colors.neonBorder, borderRadius: borderRadius.md, padding: spacing.md },
    translateResultText: { fontFamily: "Inter_400Regular", fontSize: fontSize.sm, color: colors.textSecondary, lineHeight: 22, marginBottom: spacing.xs },
    confidenceText: { fontFamily: "Inter_400Regular", fontSize: fontSize.tiny, color: colors.neon, marginBottom: spacing.sm },
    copyBtn: { backgroundColor: colors.bgCard, borderRadius: borderRadius.sm, paddingVertical: spacing.xs, paddingHorizontal: spacing.md, alignSelf: "flex-start" },
    copyBtnText: { fontFamily: "Inter_400Regular", fontSize: fontSize.tiny, color: colors.textDim },
    // TeachMe
    teachInput: { backgroundColor: colors.bgInput, borderRadius: borderRadius.md, borderWidth: 1, borderColor: colors.glassBorder, paddingHorizontal: spacing.md, paddingVertical: spacing.sm, fontFamily: "Inter_400Regular", fontSize: fontSize.sm, color: colors.textPrimary, marginBottom: spacing.sm },
    teachBtn: { backgroundColor: colors.neon, borderRadius: borderRadius.md, paddingVertical: spacing.sm + 2, alignItems: "center" },
    teachBtnText: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.xs, color: colors.bgPrimary },
    confirmBox: { backgroundColor: colors.neonGlow, borderWidth: 1, borderColor: colors.neonBorder, borderRadius: borderRadius.md, padding: spacing.md },
    confirmText: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.textSecondary, fontStyle: "italic", marginBottom: spacing.xs },
    confirmCount: { fontFamily: "Inter_400Regular", fontSize: fontSize.tiny, color: colors.neon },
});
