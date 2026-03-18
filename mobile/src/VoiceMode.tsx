/**
 * 🎤 Voice Mode.
 *
 * Hold-to-talk walkie-talkie UX.
 * Whisper STT + Kokoro TTS via home PC.
 * Audio NEVER leaves local network — 🔒 privacy indicator.
 */
import { useState, useRef, useCallback } from "react";
import {
    View,
    Text,
    TouchableOpacity,
    StyleSheet,
    Animated,
    ActivityIndicator,
} from "react-native";
import { Audio } from "expo-av";
import * as Haptics from "expo-haptics";
import { companionAPI } from "./api";
import { colors, spacing, borderRadius, fontSize, shadows } from "./theme";
import type { PetSpecies } from "./types";

type VoicePhase = "idle" | "recording" | "transcribing" | "thinking" | "speaking";

interface VoiceModeProps {
    petName: string;
    species: PetSpecies;
    isOnline: boolean;
    onChatMessage?: (userText: string, replyText: string) => void;
}

export default function VoiceMode({ petName, species, isOnline, onChatMessage }: VoiceModeProps) {
    const [phase, setPhase] = useState<VoicePhase>("idle");
    const [transcript, setTranscript] = useState("");
    const [reply, setReply] = useState("");
    const recordingRef = useRef<Audio.Recording | null>(null);
    const pulseAnim = useRef(new Animated.Value(1)).current;
    const waveAnim = useRef(new Animated.Value(0)).current;

    // Pulse animation while recording
    const startPulse = useCallback(() => {
        Animated.loop(
            Animated.sequence([
                Animated.timing(pulseAnim, { toValue: 1.15, duration: 500, useNativeDriver: true }),
                Animated.timing(pulseAnim, { toValue: 1, duration: 500, useNativeDriver: true }),
            ])
        ).start();
    }, [pulseAnim]);

    const stopPulse = useCallback(() => {
        pulseAnim.stopAnimation();
        pulseAnim.setValue(1);
    }, [pulseAnim]);

    // Waveform animation while speaking
    const startWave = useCallback(() => {
        Animated.loop(
            Animated.sequence([
                Animated.timing(waveAnim, { toValue: 1, duration: 300, useNativeDriver: true }),
                Animated.timing(waveAnim, { toValue: 0, duration: 300, useNativeDriver: true }),
            ])
        ).start();
    }, [waveAnim]);

    const stopWave = useCallback(() => {
        waveAnim.stopAnimation();
        waveAnim.setValue(0);
    }, [waveAnim]);

    const handlePressIn = useCallback(async () => {
        if (!isOnline) return;
        Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);

        try {
            await Audio.requestPermissionsAsync();
            await Audio.setAudioModeAsync({
                allowsRecordingIOS: true,
                playsInSilentModeIOS: true,
            });

            const { recording } = await Audio.Recording.createAsync(
                Audio.RecordingOptionsPresets.HIGH_QUALITY
            );
            recordingRef.current = recording;
            setPhase("recording");
            setTranscript("");
            setReply("");
            startPulse();
        } catch (err) {
            console.warn("Recording failed:", err);
        }
    }, [isOnline, startPulse]);

    const handlePressOut = useCallback(async () => {
        if (!recordingRef.current) return;
        Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
        stopPulse();

        try {
            // Stop recording
            setPhase("transcribing");
            await recordingRef.current.stopAndUnloadAsync();
            const uri = recordingRef.current.getURI();
            recordingRef.current = null;

            if (!uri) { setPhase("idle"); return; }

            // Transcribe via Whisper on home PC
            const formData = new FormData();
            formData.append("audio", { uri, type: "audio/m4a", name: "recording.m4a" } as any);

            const transcription = await companionAPI.voiceTranscribe(formData);
            setTranscript(transcription.text);

            // Send to companion
            setPhase("thinking");
            const chatResult = await companionAPI.chat(transcription.text);
            setReply(chatResult.reply);

            // Play TTS response
            setPhase("speaking");
            startWave();

            try {
                const ttsResult = await companionAPI.voiceSpeak(chatResult.reply);
                if (ttsResult.audio_url) {
                    const { sound } = await Audio.Sound.createAsync({ uri: ttsResult.audio_url });
                    await Audio.setAudioModeAsync({ allowsRecordingIOS: false, playsInSilentModeIOS: true });
                    sound.setOnPlaybackStatusUpdate((status) => {
                        if (status.isLoaded && status.didJustFinish) {
                            stopWave();
                            setPhase("idle");
                            sound.unloadAsync();
                        }
                    });
                    await sound.playAsync();
                }
            } catch {
                stopWave();
                setPhase("idle");
            }

            onChatMessage?.(transcription.text, chatResult.reply);
        } catch (err) {
            console.warn("Voice pipeline failed:", err);
            setPhase("idle");
        }
    }, [stopPulse, startWave, stopWave, onChatMessage]);

    const phaseLabels: Record<VoicePhase, string> = {
        idle: `Hold to talk to ${petName}`,
        recording: "Listening...",
        transcribing: "Transcribing...",
        thinking: `${petName} is thinking...`,
        speaking: `${petName} is speaking...`,
    };

    const isActive = phase !== "idle";

    return (
        <View style={styles.container}>
            {/* Privacy indicator */}
            <View style={styles.privacyBadge}>
                <Text style={styles.privacyText}>🔒 Audio stays on your local network</Text>
            </View>

            {/* Transcript + Reply */}
            {transcript ? (
                <View style={styles.transcriptBox}>
                    <Text style={styles.transcriptLabel}>You said:</Text>
                    <Text style={styles.transcriptText}>{transcript}</Text>
                </View>
            ) : null}
            {reply ? (
                <View style={styles.replyBox}>
                    <Text style={styles.replyLabel}>{petName}:</Text>
                    <Text style={styles.replyText}>{reply}</Text>
                </View>
            ) : null}

            {/* Waveform visualization */}
            {phase === "speaking" && (
                <View style={styles.waveContainer}>
                    {[...Array(7)].map((_, i) => (
                        <Animated.View
                            key={i}
                            style={[
                                styles.waveBar,
                                {
                                    transform: [{
                                        scaleY: waveAnim.interpolate({
                                            inputRange: [0, 1],
                                            outputRange: [0.3, 0.3 + Math.random() * 0.7],
                                        }),
                                    }],
                                },
                            ]}
                        />
                    ))}
                </View>
            )}

            {/* Status */}
            <Text style={[styles.statusText, isActive && styles.statusActive]}>
                {phaseLabels[phase]}
            </Text>

            {/* Loading indicator */}
            {(phase === "transcribing" || phase === "thinking") && (
                <ActivityIndicator size="small" color={colors.neon} style={styles.loader} />
            )}

            {/* Mic button */}
            <Animated.View style={{ transform: [{ scale: pulseAnim }] }}>
                <TouchableOpacity
                    style={[
                        styles.micBtn,
                        phase === "recording" && styles.micBtnRecording,
                        !isOnline && styles.micBtnDisabled,
                    ]}
                    onPressIn={handlePressIn}
                    onPressOut={handlePressOut}
                    disabled={!isOnline || (phase !== "idle" && phase !== "recording")}
                    activeOpacity={0.8}
                >
                    <Text style={styles.micIcon}>
                        {phase === "recording" ? "🔴" : "🎤"}
                    </Text>
                </TouchableOpacity>
            </Animated.View>

            {!isOnline && (
                <Text style={styles.offlineNote}>
                    Voice requires your home PC to be online
                </Text>
            )}
        </View>
    );
}

const styles = StyleSheet.create({
    container: { alignItems: "center", paddingVertical: spacing.xl },
    privacyBadge: { backgroundColor: "rgba(0,200,100,0.08)", borderRadius: borderRadius.full, paddingHorizontal: spacing.md, paddingVertical: spacing.xs, marginBottom: spacing.lg },
    privacyText: { fontFamily: "Inter_400Regular", fontSize: fontSize.tiny, color: "#4ade80" },
    transcriptBox: { backgroundColor: colors.bgCard, borderRadius: borderRadius.md, padding: spacing.md, width: "100%", marginBottom: spacing.sm, borderWidth: 1, borderColor: colors.glassBorder },
    transcriptLabel: { fontFamily: "Inter_500Medium", fontSize: fontSize.tiny, color: colors.textDim, marginBottom: spacing.xs },
    transcriptText: { fontFamily: "Inter_400Regular", fontSize: fontSize.sm, color: colors.textPrimary },
    replyBox: { backgroundColor: colors.neonGlow, borderRadius: borderRadius.md, padding: spacing.md, width: "100%", marginBottom: spacing.md, borderWidth: 1, borderColor: colors.neonBorder },
    replyLabel: { fontFamily: "Inter_500Medium", fontSize: fontSize.tiny, color: colors.neon, marginBottom: spacing.xs },
    replyText: { fontFamily: "Inter_400Regular", fontSize: fontSize.sm, color: colors.textSecondary },
    waveContainer: { flexDirection: "row", gap: 4, height: 40, alignItems: "center", marginBottom: spacing.md },
    waveBar: { width: 4, height: 30, borderRadius: 2, backgroundColor: colors.neon },
    statusText: { fontFamily: "Inter_400Regular", fontSize: fontSize.xs, color: colors.textMuted, marginBottom: spacing.lg },
    statusActive: { color: colors.neon },
    loader: { marginBottom: spacing.md },
    micBtn: { width: 80, height: 80, borderRadius: 40, backgroundColor: colors.bgCard, borderWidth: 2, borderColor: colors.glassBorder, justifyContent: "center", alignItems: "center", ...shadows.card },
    micBtnRecording: { borderColor: "#ef4444", backgroundColor: "rgba(239,68,68,0.1)" },
    micBtnDisabled: { opacity: 0.3 },
    micIcon: { fontSize: 32 },
    offlineNote: { fontFamily: "Inter_400Regular", fontSize: fontSize.tiny, color: colors.textMuted, marginTop: spacing.md, fontStyle: "italic" },
});
