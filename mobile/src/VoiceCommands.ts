/**
 * 🎙️ VoiceMode — Enhanced voice command processing.
 *
 * Sprint 3: "Extra Senses" — adds context-aware voice commands.
 *
 * Key patterns:
 *   - "Remind me when I'm at my desk" → queues task for when PC is online
 *   - "Send this to my PC" → clipboard relay
 *   - "What's my companion doing?" → heartbeat query
 *   - "Summarize [URL]" → web browse task
 */
import { companionAPI } from "./api";
import { getConnectionPref } from "./api";

export interface VoiceCommand {
    transcript: string;
    intent: VoiceIntent;
    payload?: Record<string, unknown>;
    confidence: number;
}

export type VoiceIntent =
    | "remind_at_desk"
    | "send_to_pc"
    | "heartbeat_query"
    | "summarize_url"
    | "queue_task"
    | "chat"
    | "unknown";

/**
 * Simple intent detection from transcript.
 * In production, this would use the on-device model.
 */
export function detectIntent(transcript: string): VoiceCommand {
    const lower = transcript.toLowerCase().trim();

    // "Remind me when I'm at my desk" pattern
    if (lower.includes("remind") && (lower.includes("desk") || lower.includes("home") || lower.includes("pc"))) {
        const task = lower
            .replace(/remind me (when i'm |to )?/i, "")
            .replace(/(at my desk|when i'm home|at home|at my pc)/i, "")
            .trim();
        return {
            transcript,
            intent: "remind_at_desk",
            payload: { task },
            confidence: 0.85,
        };
    }

    // "Send to PC" pattern
    if (lower.includes("send") && (lower.includes("pc") || lower.includes("desktop") || lower.includes("computer"))) {
        return {
            transcript,
            intent: "send_to_pc",
            payload: { content: transcript },
            confidence: 0.8,
        };
    }

    // "What's my companion doing" pattern
    if (lower.includes("doing") || lower.includes("status") || lower.includes("heartbeat")) {
        return {
            transcript,
            intent: "heartbeat_query",
            confidence: 0.75,
        };
    }

    // URL detection
    const urlMatch = transcript.match(/https?:\/\/\S+/i);
    if (urlMatch && (lower.includes("summarize") || lower.includes("read") || lower.includes("check"))) {
        return {
            transcript,
            intent: "summarize_url",
            payload: { url: urlMatch[0] },
            confidence: 0.9,
        };
    }

    // Generic task queuing
    if (lower.startsWith("queue") || lower.startsWith("add task") || lower.startsWith("do ")) {
        return {
            transcript,
            intent: "queue_task",
            payload: { text: transcript },
            confidence: 0.7,
        };
    }

    // Default: treat as chat message
    return {
        transcript,
        intent: "chat",
        confidence: 0.5,
    };
}

/**
 * Execute a detected voice command.
 */
export async function executeVoiceCommand(command: VoiceCommand): Promise<string> {
    switch (command.intent) {
        case "remind_at_desk": {
            const task = (command.payload?.task as string) || command.transcript;
            await companionAPI.queueTask("reminder", { text: task, trigger: "desktop_online" });
            return `Got it! I'll remind you when you're at your desk: "${task}"`;
        }

        case "send_to_pc": {
            const content = (command.payload?.content as string) || command.transcript;
            await companionAPI.queueTask("clipboard_relay", { text: content });
            return "Sent to your PC's clipboard!";
        }

        case "heartbeat_query": {
            try {
                const hb = await companionAPI.heartbeat();
                return `${hb.emoji} ${hb.activity}${hb.detail ? ` — ${hb.detail}` : ""}`;
            } catch {
                return "I can't reach the desktop right now. Your companion might be offline.";
            }
        }

        case "summarize_url": {
            const url = command.payload?.url as string;
            if (!url) return "I didn't catch the URL. Can you try again?";
            try {
                const result = await companionAPI.browseSummarize(url);
                return result.summary || "I read the page but couldn't generate a summary.";
            } catch {
                await companionAPI.queueTask("summarize", { url });
                return "I'll summarize that when your PC is available.";
            }
        }

        case "queue_task": {
            const text = (command.payload?.text as string) || command.transcript;
            await companionAPI.queueTask("user_request", { text });
            return `Task queued: "${text}"`;
        }

        case "chat":
        default: {
            try {
                const res = await companionAPI.chat(command.transcript);
                return res.reply || "I heard you, but I'm not sure what to do with that.";
            } catch {
                return "I'm in pocket mode right now. I'll remember this for later.";
            }
        }
    }
}
