/**
 * 🔍 Cross-Context Search — Sprint 9 Task 2.
 *
 * Search across the companion's entire memory: working memory, taught facts,
 * chat history, hypotheses. Calls POST /api/v1/companion/query.
 *
 * Accessible from search icon in chat header.
 */
import { useState, useCallback, useRef } from "react";
import {
    View,
    Text,
    TextInput,
    TouchableOpacity,
    ScrollView,
    StyleSheet,
    Animated,
    Modal,
} from "react-native";
import * as Haptics from "expo-haptics";
import { companionAPI } from "./api";
import { colors, spacing, borderRadius, fontSize, shadows } from "./theme";

interface SearchResult {
    source: string;
    content: string;
    relevance: number;
    date?: string;
}

interface SearchAllProps {
    visible: boolean;
    onClose: () => void;
}

const SOURCE_ICONS: Record<string, { emoji: string; label: string }> = {
    working_memory: { emoji: "🧠", label: "Memory" },
    taught_facts: { emoji: "📚", label: "Taught" },
    chat_history: { emoji: "💬", label: "Conversations" },
    hypotheses: { emoji: "🔮", label: "Hypotheses" },
};

export default function SearchAll({ visible, onClose }: SearchAllProps) {
    const [query, setQuery] = useState("");
    const [results, setResults] = useState<SearchResult[]>([]);
    const [loading, setLoading] = useState(false);
    const [expandedIdx, setExpandedIdx] = useState<number | null>(null);
    const [searched, setSearched] = useState(false);
    const debounceRef = useRef<NodeJS.Timeout | null>(null);

    const handleSearch = useCallback((text: string) => {
        setQuery(text);
        if (debounceRef.current) clearTimeout(debounceRef.current);
        if (!text.trim()) {
            setResults([]);
            setSearched(false);
            return;
        }
        debounceRef.current = setTimeout(async () => {
            setLoading(true);
            try {
                const res = await companionAPI.query(text.trim());
                setResults(res.results || []);
            } catch {
                setResults([]);
            }
            setLoading(false);
            setSearched(true);
        }, 500);
    }, []);

    const toggleExpand = (idx: number) => {
        Haptics.selectionAsync();
        setExpandedIdx(expandedIdx === idx ? null : idx);
    };

    // Group results by source
    const grouped = results.reduce<Record<string, SearchResult[]>>((acc, r) => {
        const src = r.source || "unknown";
        if (!acc[src]) acc[src] = [];
        acc[src].push(r);
        return acc;
    }, {});

    return (
        <Modal visible={visible} animationType="slide" presentationStyle="pageSheet">
            <View style={styles.container}>
                {/* Header */}
                <View style={styles.header}>
                    <Text style={styles.title}>🔍 Search</Text>
                    <TouchableOpacity onPress={onClose} activeOpacity={0.7}>
                        <Text style={styles.closeBtn}>Done</Text>
                    </TouchableOpacity>
                </View>

                {/* Search input */}
                <TextInput
                    style={styles.searchInput}
                    value={query}
                    onChangeText={handleSearch}
                    placeholder="Search across your AI's memory..."
                    placeholderTextColor={colors.textMuted}
                    autoFocus
                    returnKeyType="search"
                />

                <ScrollView style={styles.results} contentContainerStyle={{ paddingBottom: 40 }}>
                    {loading && (
                        <Text style={styles.loadingText}>Searching...</Text>
                    )}

                    {!loading && searched && results.length === 0 && (
                        <View style={styles.emptyState}>
                            <Text style={styles.emptyEmoji}>🌟</Text>
                            <Text style={styles.emptyTitle}>No results found</Text>
                            <Text style={styles.emptyDesc}>
                                Your AI's memory is empty for this query. Start chatting, teaching, and exploring!
                            </Text>
                        </View>
                    )}

                    {!loading && Object.entries(grouped).map(([source, items]) => {
                        const info = SOURCE_ICONS[source] || { emoji: "📄", label: source };
                        return (
                            <View key={source} style={styles.sourceGroup}>
                                <View style={styles.sourceHeader}>
                                    <Text style={styles.sourceEmoji}>{info.emoji}</Text>
                                    <Text style={styles.sourceLabel}>{info.label}</Text>
                                    <Text style={styles.sourceCount}>{items.length}</Text>
                                </View>

                                {items.map((result, idx) => {
                                    const globalIdx = results.indexOf(result);
                                    const isExpanded = expandedIdx === globalIdx;
                                    return (
                                        <TouchableOpacity
                                            key={idx}
                                            style={styles.resultCard}
                                            onPress={() => toggleExpand(globalIdx)}
                                            activeOpacity={0.7}
                                        >
                                            <View style={styles.resultRow}>
                                                <Text
                                                    style={styles.resultContent}
                                                    numberOfLines={isExpanded ? undefined : 2}
                                                >
                                                    {result.content}
                                                </Text>
                                                <View style={[styles.relevanceBadge, { backgroundColor: result.relevance > 0.8 ? colors.neonGlow : colors.bgInput }]}>
                                                    <Text style={styles.relevanceText}>{Math.round(result.relevance * 100)}%</Text>
                                                </View>
                                            </View>
                                            {result.date && (
                                                <Text style={styles.resultDate}>{result.date}</Text>
                                            )}
                                        </TouchableOpacity>
                                    );
                                })}
                            </View>
                        );
                    })}
                </ScrollView>
            </View>
        </Modal>
    );
}

const styles = StyleSheet.create({
    container: { flex: 1, backgroundColor: colors.bgPrimary },
    header: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingHorizontal: spacing.lg, paddingTop: 60, paddingBottom: spacing.md },
    title: { fontFamily: "Inter_700Bold", fontSize: fontSize.xl, color: colors.textPrimary },
    closeBtn: { fontFamily: "Inter_500Medium", fontSize: fontSize.md, color: colors.neon },
    searchInput: { backgroundColor: colors.bgInput, borderRadius: borderRadius.md, borderWidth: 1, borderColor: colors.glassBorder, marginHorizontal: spacing.lg, paddingHorizontal: spacing.md, paddingVertical: spacing.md, fontFamily: "Inter_400Regular", fontSize: fontSize.md, color: colors.textPrimary },
    results: { flex: 1, paddingHorizontal: spacing.lg, marginTop: spacing.lg },
    loadingText: { fontFamily: "Inter_400Regular", fontSize: fontSize.sm, color: colors.textDim, textAlign: "center", marginTop: spacing.xl },
    // Empty
    emptyState: { alignItems: "center", paddingTop: spacing.xxxl },
    emptyEmoji: { fontSize: 48, marginBottom: spacing.md },
    emptyTitle: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.md, color: colors.textPrimary, marginBottom: spacing.xs },
    emptyDesc: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.textDim, textAlign: "center", lineHeight: 18, paddingHorizontal: spacing.xl },
    // Groups
    sourceGroup: { marginBottom: spacing.xl },
    sourceHeader: { flexDirection: "row", alignItems: "center", gap: spacing.sm, marginBottom: spacing.sm },
    sourceEmoji: { fontSize: 18 },
    sourceLabel: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.sm, color: colors.textSecondary },
    sourceCount: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.textMuted, backgroundColor: colors.bgInput, paddingHorizontal: spacing.sm, paddingVertical: 2, borderRadius: borderRadius.full },
    // Results
    resultCard: { backgroundColor: colors.bgCard, borderRadius: borderRadius.md, borderWidth: 1, borderColor: colors.glassBorder, padding: spacing.md, marginBottom: spacing.sm, ...shadows.card },
    resultRow: { flexDirection: "row", alignItems: "flex-start", gap: spacing.sm },
    resultContent: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.textSecondary, lineHeight: 18, flex: 1 },
    relevanceBadge: { borderRadius: borderRadius.full, paddingHorizontal: spacing.sm, paddingVertical: 2 },
    relevanceText: { fontFamily: "Inter_500Medium", fontSize: fontSize.tiny, color: colors.neon },
    resultDate: { fontFamily: "Inter_400Regular", fontSize: fontSize.tiny, color: colors.textMuted, marginTop: spacing.xs },
});
