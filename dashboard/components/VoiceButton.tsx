"use client";

import { useState, useRef, useCallback } from "react";

interface VoiceButtonProps {
    onTranscript?: (text: string) => void;
    disabled?: boolean;
    mode?: "hold" | "toggle";
}

export default function VoiceButton({ onTranscript, disabled, mode = "hold" }: VoiceButtonProps) {
    const [recording, setRecording] = useState(false);
    const [processing, setProcessing] = useState(false);
    const holdTimer = useRef<NodeJS.Timeout | null>(null);

    const startRecording = useCallback(() => {
        if (disabled) return;
        setRecording(true);
        // In production: open WebSocket to ws://localhost:8337/api/v1/voice/stream
        // and stream audio chunks
    }, [disabled]);

    const stopRecording = useCallback(() => {
        setRecording(false);
        setProcessing(true);
        // Simulate transcription
        setTimeout(() => {
            setProcessing(false);
            onTranscript?.("This is a simulated voice transcript");
        }, 800);
    }, [onTranscript]);

    const handleMouseDown = () => {
        if (mode === "hold") startRecording();
    };

    const handleMouseUp = () => {
        if (mode === "hold" && recording) stopRecording();
    };

    const handleClick = () => {
        if (mode === "toggle") {
            if (recording) stopRecording();
            else startRecording();
        }
    };

    return (
        <button
            onMouseDown={handleMouseDown}
            onMouseUp={handleMouseUp}
            onMouseLeave={() => mode === "hold" && recording && stopRecording()}
            onClick={handleClick}
            disabled={disabled || processing}
            aria-label={recording ? "Stop recording" : "Start voice input"}
            className={`
        relative w-10 h-10 rounded-full flex items-center justify-center transition-all
        ${recording
                    ? "bg-[var(--color-danger)] text-white scale-110 shadow-[0_0_20px_rgba(255,68,102,0.4)]"
                    : processing
                        ? "bg-[var(--color-glass)] text-[var(--color-rune-dim)] animate-pulse"
                        : "bg-[var(--color-glass)] text-[var(--color-rune)] hover:text-white hover:bg-[var(--color-glass-hover)]"
                }
        disabled:opacity-30 disabled:cursor-not-allowed
      `}
        >
            {processing ? (
                <span className="text-sm">⏳</span>
            ) : recording ? (
                <span className="text-sm animate-pulse">⏹️</span>
            ) : (
                <span className="text-sm">🎤</span>
            )}

            {/* Recording ring animation */}
            {recording && (
                <div className="absolute inset-0 rounded-full border-2 border-[var(--color-danger)] animate-ping opacity-40" />
            )}
        </button>
    );
}
