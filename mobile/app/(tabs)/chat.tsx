/**
 * 💬 Chat Tab — Talk to your companion.
 *
 * Features: chat history persistence, haptic feedback, sound effects,
 * message guardian, proactive guardian, hold-to-talk voice mode,
 * rich action cards, companion references AI agent by name.
 */
import { useState, useEffect, useRef, useCallback } from "react";
import {
    View,
    Text,
    TextInput,
    TouchableOpacity,
    FlatList,
    StyleSheet,
    KeyboardAvoidingView,
    Platform,
} from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import * as Haptics from "expo-haptics";
import { useConnection } from "../../src/hooks/useConnection";
import { companionAPI } from "../../src/api";
import { colors, spacing, borderRadius, fontSize } from "../../src/theme";
import { playSound } from "../../src/sounds";
import GuardianModal from "../../src/GuardianModal";
import ProactiveGuardian from "../../src/ProactiveGuardian";
import VoiceMode from "../../src/VoiceMode";
import ActionCard from "../../src/ActionCard";
import SearchAll from "../../src/SearchAll";
import { useAgent } from "../../src/AgentContext";
import type { Message, PetSpecies } from "../../src/types";

const CHAT_HISTORY_KEY = "valhalla_chat_history";
const MAX_HISTORY = 100;

const OFFLINE_RESPONSES: Record<PetSpecies, string[]> = {
    cat: [
        "I need some wifi to think harder about that 😸",
        "*yawns and rolls over* Ask me when we're back online.",
        "My brain runs on the cloud, hooman. Try later.",
    ],
    dog: [
        "I WANT to help SO BAD but I can't reach home!! 🐕",
        "No signal = no fetch. Wait, I mean... different fetch.",
        "AAAH I can't think without the home server!",
    ],
    penguin: [
        "I regret to inform you that my processing unit is offline.",
        "Per protocol, I cannot respond without a valid connection.",
        "A formal apology: connectivity is required for this operation.",
    ],
    fox: [
        "Hmm, I'd answer but my clever brain is on the home server...",
        "No connection? That's... inconvenient. Ask me later?",
        "I've got a witty answer ready, but it's stuck upstream.",
    ],
    owl: [
        "Wisdom requires connection to the greater repository of knowledge.",
        "Even owls need the internet sometimes. Try again later.",
        "My thoughts are deeper than offline mode allows.",
    ],
    dragon: [
        "THE ANSWER REQUIRES MORE POWER THAN OFFLINE MODE PROVIDES!",
        "My fire is strong but my wifi is weak! Connect me!",
        "A DRAGON without internet is like... still impressive, but limited.",
    ],
};

function getOfflineResponse(species: PetSpecies): string {
    const responses = OFFLINE_RESPONSES[species] || OFFLINE_RESPONSES.cat;
    return responses[Math.floor(Math.random() * responses.length)];
}

/** Save chat history to AsyncStorage (capped at MAX_HISTORY msgs). */
async function saveHistory(messages: Message[]) {
    try {
        const trimmed = messages.slice(-MAX_HISTORY);
        await AsyncStorage.setItem(CHAT_HISTORY_KEY, JSON.stringify(trimmed));
    } catch {
        // silently fail
    }
}

/** Load chat history from AsyncStorage. */
async function loadHistory(): Promise<Message[]> {
    try {
        const raw = await AsyncStorage.getItem(CHAT_HISTORY_KEY);
        return raw ? JSON.parse(raw) : [];
    } catch {
        return [];
    }
}

export default function ChatTab() {
    const { isOnline, companionData, queueAction } = useConnection();
    const { agent } = useAgent();
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState("");
    const [typing, setTyping] = useState(false);
    const [historyLoaded, setHistoryLoaded] = useState(false);
    const flatListRef = useRef<FlatList>(null);

    const petName = companionData?.companion?.name || "Companion";
    const species = (companionData?.companion?.species || "cat") as PetSpecies;
    const mood = companionData?.companion?.happiness ?? 50;

    // Load chat history from AsyncStorage on mount
    useEffect(() => {
        (async () => {
            const history = await loadHistory();
            if (history.length > 0) {
                setMessages(history);
            } else {
                const prefix = companionData?.mood_prefix || "";
                setMessages([
                    { role: "pet", content: `${prefix}Hey! I'm ${petName}. What's up?` },
                ]);
            }
            setHistoryLoaded(true);
        })();
    }, []);

    // Persist whenever messages change
    useEffect(() => {
        if (historyLoaded && messages.length > 0) {
            saveHistory(messages);
        }
    }, [messages, historyLoaded]);

    // Guardian state
    const [guardianVisible, setGuardianVisible] = useState(false);
    const [guardianResult, setGuardianResult] = useState<{ safe: boolean; reason?: string; suggestedRewrite?: string; sentiment?: string }>({ safe: true });
    const [pendingMessage, setPendingMessage] = useState("");

    // Search state
    const [searchVisible, setSearchVisible] = useState(false);

    const actualSend = useCallback(async (text: string) => {
        setMessages((prev) => [...prev, { role: "user", content: text }]);
        setInput("");
        setTyping(true);

        if (isOnline) {
            try {
                const res = await companionAPI.chat(text);
                // Add relay flavor text
                const relayPrefix = `Let me check with ${agent.name}... `;
                const petMsg: Message = { role: "pet", content: relayPrefix + res.reply };
                if (res.action) petMsg.action = res.action;
                setMessages((prev) => [...prev, petMsg]);
            } catch {
                const reply = getOfflineResponse(species);
                setMessages((prev) => [...prev, { role: "pet", content: reply }]);
            }
        } else {
            queueAction({ type: "chat", payload: text, timestamp: Date.now() });
            await new Promise((r) => setTimeout(r, 800 + Math.random() * 700));
            const reply = `${agent.name} is resting right now, but I'll remember this for when we're home. ` + getOfflineResponse(species);
            setMessages((prev) => [...prev, { role: "pet", content: reply }]);
        }

        setTyping(false);
    }, [isOnline, species, queueAction]);

    const handleSend = useCallback(async () => {
        const text = input.trim();
        if (!text || typing) return;

        Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
        playSound("send");

        // Guardian check: intercept before sending
        if (isOnline) {
            try {
                const hour = new Date().getHours();
                const timeOfDay = hour < 6 ? "late_night" : hour < 12 ? "morning" : hour < 18 ? "afternoon" : "evening";
                const result = await companionAPI.guardian(text, timeOfDay);
                if (!result.safe) {
                    setPendingMessage(text);
                    setGuardianResult(result);
                    setGuardianVisible(true);
                    return;
                }
            } catch {
                // Guardian offline — send normally
            }
        }

        await actualSend(text);
    }, [input, typing, isOnline, actualSend]);

    const handleGuardianSendAnyway = useCallback(async () => {
        setGuardianVisible(false);
        await actualSend(pendingMessage);
    }, [pendingMessage, actualSend]);

    const handleGuardianUseRewrite = useCallback(async (rewrite: string) => {
        setGuardianVisible(false);
        await actualSend(rewrite);
    }, [actualSend]);

    const handleGuardianCancel = useCallback(() => {
        setGuardianVisible(false);
        setInput(pendingMessage);
    }, [pendingMessage]);

    const renderMessage = ({ item }: { item: Message }) => {
        const isUser = item.role === "user";
        return (
            <View style={[styles.bubble, isUser ? styles.userBubble : styles.petBubble]}>
                {!isUser && <Text style={styles.petLabel}>{petName}</Text>}
                <Text style={[styles.messageText, isUser && styles.userText]}>
                    {item.content}
                </Text>
                {!isUser && item.action && <ActionCard action={item.action} />}
            </View>
        );
    };

    return (
        <KeyboardAvoidingView
            style={styles.container}
            behavior={Platform.OS === "ios" ? "padding" : undefined}
            keyboardVerticalOffset={90}
        >
            {/* Header */}
            <View style={styles.header}>
                <View style={styles.headerInfo}>
                    <Text style={styles.headerName}>{petName}</Text>
                    <View style={styles.statusRow}>
                        <View
                            style={[
                                styles.statusDot,
                                { backgroundColor: isOnline ? colors.onlineDot : colors.offlineDot },
                            ]}
                        />
                        <Text style={styles.statusText}>
                            {isOnline ? "Home PC connected" : "Offline — local mode"}
                        </Text>
                    </View>
                </View>
                <TouchableOpacity onPress={() => setSearchVisible(true)} activeOpacity={0.7} style={{ padding: spacing.sm }}>
                    <Text style={{ fontSize: 20 }}>🔍</Text>
                </TouchableOpacity>
                {mood < 30 && <Text style={styles.moodEmoji}>😢</Text>}
            </View>

            {/* Proactive Guardian */}
            <ProactiveGuardian
                isOnline={isOnline}
                onHoldMessages={() => { }}
            />

            {/* Messages */}
            <FlatList
                ref={flatListRef}
                data={messages}
                renderItem={renderMessage}
                keyExtractor={(_, i) => String(i)}
                contentContainerStyle={styles.messagesList}
                onContentSizeChange={() =>
                    flatListRef.current?.scrollToEnd({ animated: true })
                }
                ListFooterComponent={
                    typing ? (
                        <View style={[styles.bubble, styles.petBubble]}>
                            <Text style={styles.typingDots}>• • •</Text>
                        </View>
                    ) : null
                }
            />

            {/* Input */}
            <View style={styles.inputBar}>
                <TextInput
                    style={styles.input}
                    value={input}
                    onChangeText={setInput}
                    placeholder={`Talk to ${petName}...`}
                    placeholderTextColor={colors.textMuted}
                    onSubmitEditing={handleSend}
                    returnKeyType="send"
                    editable={!typing}
                />
                <TouchableOpacity
                    style={[styles.sendBtn, (!input.trim() || typing) && styles.sendBtnDisabled]}
                    onPress={handleSend}
                    disabled={!input.trim() || typing}
                    activeOpacity={0.7}
                >
                    <Text style={styles.sendText}>{typing ? "⏳" : "Send"}</Text>
                </TouchableOpacity>
            </View>

            {/* Voice Mode */}
            <VoiceMode
                petName={petName}
                species={species}
                isOnline={isOnline}
                onChatMessage={(userText, replyText) => {
                    setMessages((prev) => [
                        ...prev,
                        { role: "user", content: `🎙️ ${userText}` },
                        { role: "pet", content: replyText },
                    ]);
                }}
            />

            {/* Guardian Modal */}
            <GuardianModal
                visible={guardianVisible}
                species={species}
                petName={petName}
                originalMessage={pendingMessage}
                guardianResult={guardianResult}
                onSendAnyway={handleGuardianSendAnyway}
                onUseRewrite={handleGuardianUseRewrite}
                onCancel={handleGuardianCancel}
            />

            {/* Cross-Context Search */}
            <SearchAll visible={searchVisible} onClose={() => setSearchVisible(false)} />
        </KeyboardAvoidingView>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: colors.bgPrimary,
    },
    header: {
        flexDirection: "row",
        alignItems: "center",
        justifyContent: "space-between",
        paddingHorizontal: spacing.lg,
        paddingTop: 60,
        paddingBottom: spacing.md,
        backgroundColor: colors.bgSecondary,
        borderBottomWidth: 1,
        borderBottomColor: colors.glassBorder,
    },
    headerInfo: {
        flex: 1,
    },
    headerName: {
        fontFamily: "Inter_600SemiBold",
        fontSize: fontSize.lg,
        color: colors.textPrimary,
    },
    statusRow: {
        flexDirection: "row",
        alignItems: "center",
        marginTop: 2,
    },
    statusDot: {
        width: 6,
        height: 6,
        borderRadius: 3,
        marginRight: spacing.xs,
    },
    statusText: {
        fontFamily: "Inter_400Regular",
        fontSize: fontSize.tiny,
        color: colors.textDim,
    },
    moodEmoji: {
        fontSize: 20,
    },
    messagesList: {
        paddingHorizontal: spacing.md,
        paddingVertical: spacing.md,
    },
    bubble: {
        maxWidth: "80%",
        borderRadius: borderRadius.lg,
        paddingHorizontal: spacing.md,
        paddingVertical: spacing.sm + 2,
        marginBottom: spacing.sm,
    },
    userBubble: {
        alignSelf: "flex-end",
        backgroundColor: colors.neonGlow,
        borderWidth: 1,
        borderColor: colors.neonBorder,
    },
    petBubble: {
        alignSelf: "flex-start",
        backgroundColor: colors.bgCard,
        borderWidth: 1,
        borderColor: colors.glassBorder,
    },
    petLabel: {
        fontFamily: "Inter_400Regular",
        fontSize: fontSize.tiny,
        color: colors.textDim,
        marginBottom: 2,
    },
    messageText: {
        fontFamily: "Inter_400Regular",
        fontSize: fontSize.sm,
        color: colors.textSecondary,
        lineHeight: 18,
    },
    userText: {
        color: colors.neon,
    },
    typingDots: {
        color: colors.textDim,
        fontSize: fontSize.lg,
        letterSpacing: 2,
    },
    inputBar: {
        flexDirection: "row",
        alignItems: "center",
        paddingHorizontal: spacing.md,
        paddingVertical: spacing.md,
        borderTopWidth: 1,
        borderTopColor: colors.glassBorder,
        backgroundColor: colors.bgSecondary,
        paddingBottom: 30,
    },
    input: {
        flex: 1,
        fontFamily: "Inter_400Regular",
        fontSize: fontSize.md,
        color: colors.textPrimary,
        paddingVertical: spacing.sm,
    },
    sendBtn: {
        backgroundColor: colors.neon,
        borderRadius: borderRadius.sm,
        paddingHorizontal: spacing.md,
        paddingVertical: spacing.sm,
        marginLeft: spacing.sm,
    },
    sendBtnDisabled: {
        opacity: 0.3,
    },
    sendText: {
        fontFamily: "Inter_600SemiBold",
        fontSize: fontSize.sm,
        color: colors.bgPrimary,
    },
});
