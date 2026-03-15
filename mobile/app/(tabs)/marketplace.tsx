/**
 * 🛒 Marketplace — Sprint 6 Task 2.
 *
 * Browse, search, and install agent personalities, themes, voice packs, plugins.
 */
import { useState, useEffect, useCallback } from "react";
import {
    View,
    Text,
    TextInput,
    TouchableOpacity,
    FlatList,
    ScrollView,
    StyleSheet,
    Image,
    ActivityIndicator,
} from "react-native";
import * as Haptics from "expo-haptics";
import { companionAPI } from "../../src/api";
import { colors, spacing, borderRadius, fontSize, shadows } from "../../src/theme";

type Category = "all" | "agents" | "themes" | "voices" | "plugins";

interface MarketItem {
    id: string;
    name: string;
    creator: string;
    description: string;
    category: Category;
    price: number; // 0 = free
    rating: number;
    installs: number;
    icon?: string;
    installed?: boolean;
}

const CATEGORIES: { key: Category; label: string; emoji: string }[] = [
    { key: "all", label: "All", emoji: "🏪" },
    { key: "agents", label: "Agents", emoji: "🤖" },
    { key: "themes", label: "Themes", emoji: "🎨" },
    { key: "voices", label: "Voices", emoji: "🎤" },
    { key: "plugins", label: "Plugins", emoji: "🧩" },
];

// Placeholder items until backend responds
const PLACEHOLDER_ITEMS: MarketItem[] = [
    { id: "sage", name: "Sage Advisor", creator: "Fireside", description: "A wise AI companion with deep knowledge of philosophy and ethics.", category: "agents", price: 0, rating: 4.8, installs: 1240, installed: false },
    { id: "midnight", name: "Midnight Theme", creator: "Fireside", description: "Deep dark mode with purple accents and subtle star animations.", category: "themes", price: 0, rating: 4.6, installs: 890, installed: true },
    { id: "luna-voice", name: "Luna Voice Pack", creator: "Community", description: "Warm Australian accent. G'day mate!", category: "voices", price: 2.99, rating: 4.9, installs: 320 },
    { id: "code-helper", name: "Code Assistant", creator: "Fireside", description: "Specialized coding companion with syntax highlighting and code review.", category: "plugins", price: 0, rating: 4.7, installs: 2100 },
    { id: "artist", name: "Creative Muse", creator: "Community", description: "Inspires creative writing, poetry, and artistic expression.", category: "agents", price: 1.99, rating: 4.5, installs: 560 },
    { id: "ocean", name: "Ocean Breeze", creator: "Community", description: "Cool ocean blues with wave animations and ambient sounds.", category: "themes", price: 0.99, rating: 4.3, installs: 450 },
    { id: "zephyr-voice", name: "Zephyr Voice Pack", creator: "Fireside", description: "Calm and soothing voice for meditation and relaxation.", category: "voices", price: 0, rating: 4.4, installs: 780 },
    { id: "translator", name: "Poly Translator", creator: "Community", description: "Enhanced translation with cultural context and idiom support.", category: "plugins", price: 0, rating: 4.2, installs: 340 },
];

export default function Marketplace() {
    const [search, setSearch] = useState("");
    const [category, setCategory] = useState<Category>("all");
    const [items, setItems] = useState<MarketItem[]>(PLACEHOLDER_ITEMS);
    const [loading, setLoading] = useState(false);
    const [selectedItem, setSelectedItem] = useState<MarketItem | null>(null);

    const fetchItems = useCallback(async (query?: string) => {
        setLoading(true);
        try {
            const res = await companionAPI.marketplaceSearch(query || "", category === "all" ? undefined : category);
            if (res.items) setItems(res.items as any);
        } catch {
            // API unavailable — use placeholder items
        }
        setLoading(false);
    }, [category]);

    useEffect(() => { fetchItems(); }, [category]);

    const handleSearch = () => {
        if (search.trim()) fetchItems(search.trim());
    };

    const handleInstall = async (item: MarketItem) => {
        Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
        try {
            await companionAPI.marketplaceInstall(item.id);
            setItems((prev) => prev.map((i) => i.id === item.id ? { ...i, installed: true } : i));
            if (selectedItem?.id === item.id) setSelectedItem({ ...item, installed: true });
        } catch { }
    };

    const filtered = items.filter((i) =>
        (category === "all" || i.category === category) &&
        (!search.trim() || i.name.toLowerCase().includes(search.toLowerCase()) || i.description.toLowerCase().includes(search.toLowerCase()))
    );

    // Detail view
    if (selectedItem) {
        return (
            <ScrollView style={styles.container} contentContainerStyle={styles.content}>
                <TouchableOpacity onPress={() => setSelectedItem(null)} style={styles.backBtn} activeOpacity={0.7}>
                    <Text style={styles.backText}>← Back</Text>
                </TouchableOpacity>

                <Text style={styles.detailName}>{selectedItem.name}</Text>
                <Text style={styles.detailCreator}>by {selectedItem.creator}</Text>
                <View style={styles.detailStats}>
                    <Text style={styles.detailStat}>⭐ {selectedItem.rating}</Text>
                    <Text style={styles.detailStat}>📥 {selectedItem.installs.toLocaleString()}</Text>
                    <Text style={[styles.detailStat, { color: selectedItem.price === 0 ? "#4ade80" : colors.neon }]}>
                        {selectedItem.price === 0 ? "Free" : `$${selectedItem.price.toFixed(2)}`}
                    </Text>
                </View>

                <Text style={styles.detailDesc}>{selectedItem.description}</Text>

                {selectedItem.price === 0 ? (
                    <TouchableOpacity
                        style={[styles.installDetailBtn, selectedItem.installed && styles.installedBtn]}
                        onPress={() => !selectedItem.installed && handleInstall(selectedItem)}
                        disabled={selectedItem.installed}
                        activeOpacity={0.7}
                    >
                        <Text style={[styles.installDetailText, selectedItem.installed && styles.installedText]}>
                            {selectedItem.installed ? "✅ Installed" : "Install — Free"}
                        </Text>
                    </TouchableOpacity>
                ) : (
                    <View style={styles.paidNote}>
                        <Text style={styles.paidNoteText}>
                            💻 Purchase on desktop dashboard
                        </Text>
                        <Text style={styles.paidNotePrice}>
                            ${selectedItem.price.toFixed(2)}
                        </Text>
                    </View>
                )}
            </ScrollView>
        );
    }

    return (
        <ScrollView style={styles.container} contentContainerStyle={styles.content}>
            <Text style={styles.title}>🛒 Marketplace</Text>
            <Text style={styles.subtitle}>Agent personalities, themes, voice packs, plugins</Text>

            {/* Search */}
            <View style={styles.searchRow}>
                <TextInput
                    style={styles.searchInput}
                    value={search}
                    onChangeText={setSearch}
                    placeholder="Search marketplace..."
                    placeholderTextColor={colors.textMuted}
                    onSubmitEditing={handleSearch}
                    returnKeyType="search"
                />
            </View>

            {/* Category filters */}
            <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.catRow}>
                {CATEGORIES.map((cat) => (
                    <TouchableOpacity
                        key={cat.key}
                        style={[styles.catBtn, category === cat.key && styles.catBtnActive]}
                        onPress={() => { setCategory(cat.key); Haptics.selectionAsync(); }}
                        activeOpacity={0.7}
                    >
                        <Text style={[styles.catText, category === cat.key && styles.catTextActive]}>
                            {cat.emoji} {cat.label}
                        </Text>
                    </TouchableOpacity>
                ))}
            </ScrollView>

            {loading && <ActivityIndicator color={colors.neon} style={{ marginVertical: spacing.lg }} />}

            {/* Items grid */}
            {filtered.map((item) => (
                <TouchableOpacity
                    key={item.id}
                    style={styles.itemCard}
                    onPress={() => setSelectedItem(item)}
                    activeOpacity={0.7}
                >
                    <View style={styles.itemHeader}>
                        <View style={styles.itemIcon}>
                            <Text style={styles.itemIconText}>
                                {item.category === "agents" ? "🤖" : item.category === "themes" ? "🎨" : item.category === "voices" ? "🎤" : "🧩"}
                            </Text>
                        </View>
                        <View style={styles.itemInfo}>
                            <Text style={styles.itemName}>{item.name}</Text>
                            <Text style={styles.itemCreator}>{item.creator}</Text>
                        </View>
                        <View style={styles.itemRight}>
                            <Text style={styles.itemRating}>⭐ {item.rating}</Text>
                            <Text style={[styles.itemPrice, item.price === 0 && { color: "#4ade80" }]}>
                                {item.price === 0 ? "Free" : `$${item.price.toFixed(2)}`}
                            </Text>
                        </View>
                    </View>
                    <Text style={styles.itemDesc} numberOfLines={2}>{item.description}</Text>
                    <View style={styles.itemFooter}>
                        <Text style={styles.itemInstalls}>📥 {item.installs.toLocaleString()}</Text>
                        {item.installed && <Text style={styles.installedBadge}>✅ Installed</Text>}
                    </View>
                </TouchableOpacity>
            ))}
        </ScrollView>
    );
}

const styles = StyleSheet.create({
    container: { flex: 1, backgroundColor: colors.bgPrimary },
    content: { paddingHorizontal: spacing.lg, paddingTop: 60, paddingBottom: spacing.xxxl },
    title: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.xl, color: colors.textPrimary, marginBottom: 2 },
    subtitle: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.textDim, marginBottom: spacing.lg },
    // Search
    searchRow: { marginBottom: spacing.md },
    searchInput: { backgroundColor: colors.bgInput, borderRadius: borderRadius.md, borderWidth: 1, borderColor: colors.glassBorder, paddingHorizontal: spacing.md, paddingVertical: spacing.sm, fontFamily: "Inter_400Regular", fontSize: fontSize.sm, color: colors.textPrimary },
    // Categories
    catRow: { marginBottom: spacing.lg, flexGrow: 0 },
    catBtn: { backgroundColor: colors.bgCard, borderRadius: borderRadius.full, paddingHorizontal: spacing.md, paddingVertical: spacing.sm, marginRight: spacing.sm, borderWidth: 1, borderColor: colors.glassBorder },
    catBtnActive: { backgroundColor: colors.neonGlow, borderColor: colors.neon },
    catText: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.textDim },
    catTextActive: { color: colors.neon },
    // Items
    itemCard: { backgroundColor: colors.bgCard, borderRadius: borderRadius.lg, borderWidth: 1, borderColor: colors.glassBorder, padding: spacing.md, marginBottom: spacing.md, ...shadows.card },
    itemHeader: { flexDirection: "row", alignItems: "center", marginBottom: spacing.sm },
    itemIcon: { width: 40, height: 40, borderRadius: 20, backgroundColor: colors.bgInput, justifyContent: "center", alignItems: "center", marginRight: spacing.sm },
    itemIconText: { fontSize: 18 },
    itemInfo: { flex: 1 },
    itemName: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.sm, color: colors.textPrimary },
    itemCreator: { fontFamily: "Inter_400Regular", fontSize: fontSize.tiny, color: colors.textDim },
    itemRight: { alignItems: "flex-end" },
    itemRating: { fontFamily: "Inter_400Regular", fontSize: fontSize.tiny, color: colors.textSecondary },
    itemPrice: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.xs, color: colors.neon },
    itemDesc: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.textMuted, marginBottom: spacing.sm },
    itemFooter: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
    itemInstalls: { fontFamily: "Inter_400Regular", fontSize: fontSize.tiny, color: colors.textDim },
    installedBadge: { fontFamily: "Inter_500Medium", fontSize: fontSize.tiny, color: "#4ade80" },
    // Detail
    backBtn: { marginBottom: spacing.md },
    backText: { fontFamily: "Inter_400Regular", fontSize: fontSize.sm, color: colors.neon },
    detailName: { fontFamily: "Inter_700Bold", fontSize: fontSize.xl, color: colors.textPrimary, marginBottom: spacing.xs },
    detailCreator: { fontFamily: "Inter_400Regular", fontSize: fontSize.sm, color: colors.textDim, marginBottom: spacing.md },
    detailStats: { flexDirection: "row", gap: spacing.lg, marginBottom: spacing.lg },
    detailStat: { fontFamily: "Inter_500Medium", fontSize: fontSize.sm, color: colors.textSecondary },
    detailDesc: { fontFamily: "Inter_400Regular", fontSize: fontSize.sm, color: colors.textSecondary, lineHeight: 22, marginBottom: spacing.xl },
    installDetailBtn: { backgroundColor: colors.neon, borderRadius: borderRadius.md, paddingVertical: spacing.md, alignItems: "center", ...shadows.glow },
    installDetailText: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.sm, color: colors.bgPrimary },
    installedBtn: { backgroundColor: colors.bgCard, borderWidth: 1, borderColor: "#4ade80" },
    installedText: { color: "#4ade80" },
    // Sprint 8: browse-only for paid items
    paidNote: { backgroundColor: colors.bgInput, borderRadius: borderRadius.md, paddingVertical: spacing.md, paddingHorizontal: spacing.lg, alignItems: "center", borderWidth: 1, borderColor: colors.glassBorder },
    paidNoteText: { fontFamily: "Inter_400Regular", fontSize: fontSize.sm, color: colors.textDim, marginBottom: spacing.xs },
    paidNotePrice: { fontFamily: "Inter_600SemiBold", fontSize: fontSize.md, color: colors.ember },
});
