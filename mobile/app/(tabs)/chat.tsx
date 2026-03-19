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
    Animated,
} from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import * as Haptics from "expo-haptics";
import { useConnection } from "../../src/hooks/useConnection";
import { companionAPI } from "../../src/api";
import { getSocket } from "../../src/FiresideSocket";
import { colors, spacing, borderRadius, fontSize } from "../../src/theme";
import { playSound } from "../../src/sounds";
import GuardianModal from "../../src/GuardianModal";
import ProactiveGuardian from "../../src/ProactiveGuardian";
import VoiceMode from "../../src/VoiceMode";
import ActionCard from "../../src/ActionCard";
import SearchAll from "../../src/SearchAll";
import { useAgent } from "../../src/AgentContext";
import type { Message, PetSpecies } from "../../src/types";

const CHAT_HISTORY_KEY = "fireside_chat_history";
const MAX_HISTORY = 100;

/** Format timestamp to relative time ("just now", "2m", "1h", "yesterday"). */
function relativeTime(ts?: number): string {
    if (!ts) return "";
    const diff = Date.now() - ts;
    if (diff < 60_000) return "just now";
    if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}m`;
    if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)}h`;
    if (diff < 172_800_000) return "yesterday";
    return `${Math.floor(diff / 86_400_000)}d`;
}

/** Get a contextual greeting based on time of day. */
function getGreeting(petName: string): string {
    const h = new Date().getHours();
    if (h < 6) return `🌙 ${petName} is up late with you. What's on your mind?`;
    if (h < 12) return `☀️ Good morning! ${petName} here. How can I help today?`;
    if (h < 17) return `👋 Hey! ${petName} at your service. What's up?`;
    if (h < 21) return `🌆 Good evening! ${petName} here. How's your day been?`;
    return `🌙 It's getting late. ${petName} is here if you need anything.`;
}

// ── Animated Typing Dots ──
function TypingIndicator({ petName }: { petName: string }) {
    const dot1 = useRef(new Animated.Value(0)).current;
    const dot2 = useRef(new Animated.Value(0)).current;
    const dot3 = useRef(new Animated.Value(0)).current;

    useEffect(() => {
        const animate = (dot: Animated.Value, delay: number) =>
            Animated.loop(
                Animated.sequence([
                    Animated.delay(delay),
                    Animated.timing(dot, { toValue: -6, duration: 300, useNativeDriver: true }),
                    Animated.timing(dot, { toValue: 0, duration: 300, useNativeDriver: true }),
                    Animated.delay(600 - delay),
                ])
            );
        animate(dot1, 0).start();
        animate(dot2, 150).start();
        animate(dot3, 300).start();
    }, [dot1, dot2, dot3]);

    return (
        <View style={[styles.bubble, styles.petBubble, { paddingVertical: spacing.sm + 4 }]}>
            <Text style={styles.petLabel}>{petName}</Text>
            <View style={styles.typingRow}>
                {[dot1, dot2, dot3].map((dot, i) => (
                    <Animated.View
                        key={i}
                        style={[
                            styles.typingDot,
                            { transform: [{ translateY: dot }] },
                        ]}
                    />
                ))}
            </View>
        </View>
    );
}

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
    const { isOnline, companionData, queueAction, connectionPhase } = useConnection();
    const { agent } = useAgent();
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState("");
    const [typing, setTyping] = useState(false);
    const [historyLoaded, setHistoryLoaded] = useState(false);
    const flatListRef = useRef<FlatList>(null);

    const petName = companionData?.companion?.name || "Companion";
    const species = (companionData?.companion?.species || "cat") as PetSpecies;
    const mood = companionData?.companion?.happiness ?? 50;

    // Bidirectional chat sync: listen for messages from desktop via WebSocket
    useEffect(() => {
        const socket = getSocket();
        const unsub = socket.onEvent((event) => {
            if (event.type === "chat_message" && event.data) {
                const msg = event.data;
                setMessages((prev) => [
                    ...prev,
                    {
                        role: msg.role === "user" ? "user" : "pet",
                        content: msg.message || msg.content || "",
                    },
                ]);
            }
        });
        return unsub;
    }, []);

    // Load chat history from AsyncStorage on mount
    useEffect(() => {
        (async () => {
            const history = await loadHistory();
            if (history.length > 0) {
                setMessages(history);
            } else {
                const greeting = getGreeting(petName);
                setMessages([
                    { role: "pet", content: greeting, timestamp: Date.now() } as any,
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
        setMessages((prev) => [...prev, { role: "user", content: text, timestamp: Date.now() } as any]);
        setInput("");
        setTyping(true);

        if (isOnline) {
            // Build context from recent messages for the agentic loop
            const recentContext = messages.slice(-10).map((m) => ({
                role: m.role === "user" ? "user" : "assistant",
                content: m.content,
            }));

            // Add a placeholder pet message that we'll stream into
            const streamMsgId = Date.now();
            setMessages((prev) => [
                ...prev,
                { role: "pet", content: "", _streamId: streamMsgId, timestamp: Date.now() } as any,
            ]);

            try {
                await companionAPI.chatStream(text, recentContext, {
                    onToken: (token) => {
                        // Append token to the streaming message in real-time
                        setMessages((prev) =>
                            prev.map((m) =>
                                (m as any)._streamId === streamMsgId
                                    ? { ...m, content: m.content + token }
                                    : m
                            )
                        );
                    },
                    onToolStatus: (status) => {
                        // Show tool execution indicator inline
                        setMessages((prev) =>
                            prev.map((m) =>
                                (m as any)._streamId === streamMsgId
                                    ? { ...m, content: m.content + "\n" + status + "\n" }
                                    : m
                            )
                        );
                    },
                    onDone: (fullText) => {
                        // Finalize: remove stream ID, add relay prefix
                        const relayPrefix = ``;
                        setMessages((prev) =>
                            prev.map((m) => {
                                if ((m as any)._streamId === streamMsgId) {
                                    const { _streamId, ...clean } = m as any;
                                    return { ...clean, content: relayPrefix + (fullText || m.content) };
                                }
                                return m;
                            })
                        );
                        setTyping(false);
                    },
                    onError: (error) => {
                        console.warn("Stream chat failed:", error);
                        // Fallback: try legacy non-streaming endpoint
                        companionAPI
                            .chat(text)
                            .then((res) => {
                                const reply = res.reply || (res as any).response || "I couldn't process that.";
                                setMessages((prev) =>
                                    prev.map((m) =>
                                        (m as any)._streamId === streamMsgId
                                            ? { role: "pet", content: reply }
                                            : m
                                    )
                                );
                            })
                            .catch(() => {
                                Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
                                setMessages((prev) =>
                                    prev.map((m) =>
                                        (m as any)._streamId === streamMsgId
                                            ? { role: "pet", content: getOfflineResponse(species) }
                                            : m
                                    )
                                );
                            })
                            .finally(() => setTyping(false));
                    },
                });
            } catch {
                Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
                setMessages((prev) =>
                    prev.map((m) =>
                        (m as any)._streamId === streamMsgId
                            ? { role: "pet", content: getOfflineResponse(species) }
                            : m
                    )
                );
                setTyping(false);
            }
        } else {
            queueAction({ type: "chat", payload: text, timestamp: Date.now() });
            await new Promise((r) => setTimeout(r, 800 + Math.random() * 700));
            const reply = `${agent.name} is resting right now, but I'll remember this for when we're home. ` + getOfflineResponse(species);
            setMessages((prev) => [...prev, { role: "pet", content: reply }]);
            setTyping(false);
        }
    }, [isOnline, species, queueAction, agent, messages]);

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

    const renderMessage = ({ item, index }: { item: Message; index: number }) => {
        const isUser = item.role === "user";
        const ts = (item as any).timestamp;
        const prevTs = index > 0 ? (messages[index - 1] as any).timestamp : 0;
        // Show timestamp if >5 min gap or first message
        const showTime = !prevTs || (ts && prevTs && ts - prevTs > 300_000);

        return (
            <View>
                {showTime && ts ? (
                    <Text style={styles.timestamp}>{relativeTime(ts)}</Text>
                ) : null}
                <View style={[styles.bubble, isUser ? styles.userBubble : styles.petBubble]}>
                    {!isUser && <Text style={styles.petLabel}>{petName}</Text>}
                    <Text style={[styles.messageText, isUser && styles.userText]}>
                        {item.content}
                    </Text>
                    {!isUser && item.action && <ActionCard action={item.action} />}
                </View>
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
                                {
                                    backgroundColor:
                                        connectionPhase === "connected" ? colors.onlineDot
                                        : connectionPhase === "reconnecting" ? "#F59E0B"
                                        : connectionPhase === "connecting" || connectionPhase === "discovering" ? "#60A5FA"
                                        : colors.offlineDot,
                                },
                            ]}
                        />
                        <Text style={styles.statusText}>
                            {connectionPhase === "connected" ? "Home PC connected"
                                : connectionPhase === "reconnecting" ? "Reconnecting..."
                                : connectionPhase === "connecting" ? "Connecting..."
                                : connectionPhase === "discovering" ? "Finding home PC..."
                                : "Offline — local mode"}
                        </Text>
                    </View>
                </View>
                <TouchableOpacity onPress={() => setSearchVisible(true)} activeOpacity={0.7} style={{ padding: spacing.sm }}>
                    <Text style={{ fontSize: 20 }}>🔍</Text>
                </TouchableOpacity>
                <TouchableOpacity
                    onPress={() => {
                        const greeting = getGreeting(petName);
                        setMessages([{ role: "pet", content: greeting, timestamp: Date.now() } as any]);
                        Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
                    }}
                    activeOpacity={0.7}
                    style={{ padding: spacing.sm }}
                >
                    <Text style={{ fontSize: 18 }}>🗑️</Text>
                </TouchableOpacity>
                {mood < 30 && <Text style={styles.moodEmoji}>😢</Text>}
            </View>

            {/* Proactive Guardian */}
            <ProactiveGuardian
                isOnline={isOnline}
                onHoldMessages={() => {
                    setInput("");
                    setMessages((prev) => [...prev, { role: "pet", content: "🌙 I'll hold messages until morning. Sleep well! 💤" }]);
                }}
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
                        <TypingIndicator petName={petName} />
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
                    <Text style={styles.sendText}>{typing ? "⏳" : "↑"}</Text>
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
    // ── Timestamp ──
    timestamp: {
        fontFamily: "Inter_400Regular",
        fontSize: 10,
        color: colors.textDim,
        textAlign: "center",
        marginVertical: spacing.sm,
        letterSpacing: 0.5,
        textTransform: "uppercase",
    },
    // ── Bubbles ──
    bubble: {
        maxWidth: "80%",
        borderRadius: 18,
        paddingHorizontal: spacing.lg,
        paddingVertical: spacing.sm + 4,
        marginBottom: spacing.xs + 2,
    },
    userBubble: {
        alignSelf: "flex-end",
        backgroundColor: colors.neon,
        borderBottomRightRadius: 4,
    },
    petBubble: {
        alignSelf: "flex-start",
        backgroundColor: colors.bgCard,
        borderWidth: 1,
        borderColor: colors.glassBorder,
        borderBottomLeftRadius: 4,
    },
    petLabel: {
        fontFamily: "Inter_500Medium",
        fontSize: 10,
        color: colors.textDim,
        marginBottom: 3,
        letterSpacing: 0.3,
    },
    messageText: {
        fontFamily: "Inter_400Regular",
        fontSize: fontSize.sm,
        color: colors.textSecondary,
        lineHeight: 20,
    },
    userText: {
        color: colors.bgPrimary,
        fontFamily: "Inter_500Medium",
    },
    // ── Animated Typing ──
    typingRow: {
        flexDirection: "row",
        alignItems: "center",
        gap: 4,
        height: 20,
        paddingTop: 2,
    },
    typingDot: {
        width: 7,
        height: 7,
        borderRadius: 3.5,
        backgroundColor: colors.textDim,
    },
    // ── Input Bar ──
    inputBar: {
        flexDirection: "row",
        alignItems: "center",
        paddingHorizontal: spacing.md,
        paddingVertical: spacing.sm,
        borderTopWidth: 1,
        borderTopColor: colors.glassBorder,
        backgroundColor: colors.bgSecondary,
        paddingBottom: Platform.OS === "ios" ? 30 : spacing.md,
    },
    input: {
        flex: 1,
        fontFamily: "Inter_400Regular",
        fontSize: fontSize.md,
        color: colors.textPrimary,
        backgroundColor: colors.bgCard,
        borderRadius: 20,
        paddingHorizontal: spacing.lg,
        paddingVertical: spacing.sm + 2,
        borderWidth: 1,
        borderColor: colors.glassBorder,
        maxHeight: 100,
    },
    sendBtn: {
        backgroundColor: colors.neon,
        width: 36,
        height: 36,
        borderRadius: 18,
        alignItems: "center",
        justifyContent: "center",
        marginLeft: spacing.sm,
    },
    sendBtnDisabled: {
        opacity: 0.3,
    },
    sendText: {
        fontFamily: "Inter_700Bold",
        fontSize: 18,
        color: colors.bgPrimary,
        marginTop: -1,
    },
});
