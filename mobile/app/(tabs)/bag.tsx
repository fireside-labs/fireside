/**
 * 🎒 Bag Tab — Companion inventory.
 *
 * 5-column grid of items, tap to see details, use consumables.
 * Data comes from the mobile/sync response.
 */
import { useState } from "react";
import {
    View,
    Text,
    TouchableOpacity,
    ScrollView,
    StyleSheet,
} from "react-native";
import { useConnection } from "../../src/hooks/useConnection";
import { colors, spacing, borderRadius, fontSize, shadows } from "../../src/theme";
import type { InventoryItem } from "../../src/types";

const MAX_SLOTS = 20;

// Fallback inventory when offline and no cache available
const FALLBACK_INVENTORY: InventoryItem[] = [
    { item: "golden_treat", count: 3, emoji: "🍬✨", consumable: true, description: "+30 happiness" },
    { item: "tiny_hat", count: 1, emoji: "🎩", equipped: true, description: "Looks adorable" },
    { item: "story_fragment", count: 7, emoji: "📜", description: "7/10 collected" },
    { item: "moonpetal", count: 2, emoji: "🌿", consumable: true, description: "+25 happiness when used" },
    { item: "friendship_badge", count: 1, emoji: "🤝", description: "Helped a lost pet" },
    { item: "cave_crystal", count: 1, emoji: "💎", rare: true, description: "Found in a storm shelter" },
    { item: "ancient_compass", count: 1, emoji: "🧭", description: "Won from a riddle guardian" },
];

export default function BagTab() {
    const { companionData } = useConnection();
    const [selected, setSelected] = useState<InventoryItem | null>(null);

    const petName = companionData?.companion?.name || "Companion";
    const items: InventoryItem[] = companionData?.inventory || FALLBACK_INVENTORY;
    const emptySlots = Math.max(0, MAX_SLOTS - items.length);

    const handleSelect = (item: InventoryItem) => {
        setSelected(selected?.item === item.item ? null : item);
    };

    const handleUse = () => {
        // In a real implementation, this would call the API and update state
        setSelected(null);
    };

    return (
        <ScrollView style={styles.container} contentContainerStyle={styles.content}>
            {/* Header */}
            <View style={styles.header}>
                <Text style={styles.title}>🎒 {petName}&apos;s Inventory</Text>
                <Text style={styles.slotCount}>
                    {items.length}/{MAX_SLOTS} slots
                </Text>
            </View>

            {/* Grid */}
            <View style={styles.grid}>
                {items.map((item) => (
                    <TouchableOpacity
                        key={item.item}
                        style={[
                            styles.gridItem,
                            selected?.item === item.item && styles.gridItemSelected,
                            item.rare && styles.gridItemRare,
                        ]}
                        onPress={() => handleSelect(item)}
                        activeOpacity={0.7}
                    >
                        <Text style={styles.itemEmoji}>{item.emoji}</Text>
                        {item.count > 1 && (
                            <View style={styles.countBadge}>
                                <Text style={styles.countText}>×{item.count}</Text>
                            </View>
                        )}
                        {item.equipped && (
                            <View style={styles.equippedBadge}>
                                <Text style={styles.equippedText}>✅</Text>
                            </View>
                        )}
                    </TouchableOpacity>
                ))}

                {/* Empty slots */}
                {Array.from({ length: Math.min(emptySlots, 8) }).map((_, i) => (
                    <View key={`empty-${i}`} style={[styles.gridItem, styles.emptySlot]}>
                        <Text style={styles.emptyDot}>·</Text>
                    </View>
                ))}
            </View>

            {/* Selected Item Detail */}
            {selected && (
                <View style={styles.detailCard}>
                    <View style={styles.detailHeader}>
                        <Text style={styles.detailName}>
                            {selected.emoji} {selected.item.replace(/_/g, " ")}
                            {selected.rare && (
                                <Text style={styles.rareBadge}> ★ RARE</Text>
                            )}
                        </Text>
                        <Text style={styles.detailCount}>×{selected.count}</Text>
                    </View>

                    {selected.description && (
                        <Text style={styles.detailDesc}>{selected.description}</Text>
                    )}

                    <View style={styles.detailActions}>
                        {selected.consumable && (
                            <TouchableOpacity
                                style={styles.actionBtn}
                                onPress={handleUse}
                                activeOpacity={0.7}
                            >
                                <Text style={styles.actionBtnText}>Use</Text>
                            </TouchableOpacity>
                        )}
                        {selected.equipped !== undefined && !selected.consumable && (
                            <TouchableOpacity
                                style={styles.actionBtn}
                                onPress={handleUse}
                                activeOpacity={0.7}
                            >
                                <Text style={styles.actionBtnText}>
                                    {selected.equipped ? "Unequip" : "Equip"}
                                </Text>
                            </TouchableOpacity>
                        )}
                    </View>
                </View>
            )}
        </ScrollView>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: colors.bgPrimary,
    },
    content: {
        paddingHorizontal: spacing.lg,
        paddingTop: 60,
        paddingBottom: spacing.xxxl,
    },
    header: {
        flexDirection: "row",
        justifyContent: "space-between",
        alignItems: "center",
        marginBottom: spacing.xl,
    },
    title: {
        fontFamily: "Inter_600SemiBold",
        fontSize: fontSize.xl,
        color: colors.textPrimary,
    },
    slotCount: {
        fontFamily: "Inter_400Regular",
        fontSize: fontSize.tiny,
        color: colors.textDim,
    },
    grid: {
        flexDirection: "row",
        flexWrap: "wrap",
        gap: spacing.sm,
        marginBottom: spacing.lg,
    },
    gridItem: {
        width: "18%",
        aspectRatio: 1,
        backgroundColor: colors.bgCard,
        borderRadius: borderRadius.md,
        borderWidth: 1,
        borderColor: colors.glassBorder,
        justifyContent: "center",
        alignItems: "center",
        position: "relative",
    },
    gridItemSelected: {
        backgroundColor: colors.neonGlow,
        borderColor: colors.neon,
    },
    gridItemRare: {
        borderLeftWidth: 3,
        borderLeftColor: "#ffd700",
    },
    emptySlot: {
        opacity: 0.3,
    },
    itemEmoji: {
        fontSize: 24,
    },
    emptyDot: {
        fontSize: 20,
        color: colors.textMuted,
    },
    countBadge: {
        position: "absolute",
        bottom: 2,
        right: 4,
        backgroundColor: "rgba(0,0,0,0.6)",
        borderRadius: 4,
        paddingHorizontal: 3,
    },
    countText: {
        fontFamily: "Inter_400Regular",
        fontSize: 8,
        color: colors.textPrimary,
    },
    equippedBadge: {
        position: "absolute",
        top: 1,
        right: 2,
    },
    equippedText: {
        fontSize: 8,
    },
    detailCard: {
        backgroundColor: colors.bgCard,
        borderRadius: borderRadius.md,
        borderWidth: 1,
        borderColor: colors.glassBorder,
        borderLeftWidth: 3,
        borderLeftColor: colors.neon,
        padding: spacing.lg,
        ...shadows.card,
    },
    detailHeader: {
        flexDirection: "row",
        justifyContent: "space-between",
        alignItems: "center",
        marginBottom: spacing.xs,
    },
    detailName: {
        fontFamily: "Inter_500Medium",
        fontSize: fontSize.sm,
        color: colors.textPrimary,
        textTransform: "capitalize",
    },
    rareBadge: {
        fontSize: fontSize.tiny,
        color: "#ffd700",
    },
    detailCount: {
        fontFamily: "Inter_400Regular",
        fontSize: fontSize.tiny,
        color: colors.textDim,
    },
    detailDesc: {
        fontFamily: "Inter_400Regular",
        fontSize: fontSize.xs,
        color: colors.textDim,
        marginBottom: spacing.md,
    },
    detailActions: {
        flexDirection: "row",
        gap: spacing.sm,
    },
    actionBtn: {
        flex: 1,
        backgroundColor: colors.neon,
        borderRadius: borderRadius.sm,
        paddingVertical: spacing.sm,
        alignItems: "center",
    },
    actionBtnText: {
        fontFamily: "Inter_600SemiBold",
        fontSize: fontSize.xs,
        color: colors.bgPrimary,
    },
});
