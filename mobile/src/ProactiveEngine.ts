/**
 * ProactiveEngine.ts — Ember's contextual awareness engine.
 *
 * Runs proactive checks using native iOS APIs to generate
 * contextual alerts. Called from BGAppRefreshTask or on app foreground.
 *
 * "The small brain's value isn't intelligence — it's ACCESS."
 *
 * No data leaves the phone unless user explicitly taps "Ask Atlas."
 */
import * as NativeCalendar from '../modules/native-calendar';
import * as NativeHealth from '../modules/native-health';
import AsyncStorage from '@react-native-async-storage/async-storage';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type AlertType =
    | 'meeting_prep'
    | 'guardian_time'
    | 'morning_briefing'
    | 'step_goal'
    | 'sleep_check';

export interface ProactiveAlert {
    type: AlertType;
    message: string;
    event?: NativeCalendar.CalendarEvent;
    events?: NativeCalendar.CalendarEvent[];
    steps?: number;
    sleepHours?: number;
    timestamp: string;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function minutesUntil(isoDate: string): number {
    const target = new Date(isoDate).getTime();
    const now = Date.now();
    return Math.floor((target - now) / 60_000);
}

function today(): string {
    return new Date().toISOString().split('T')[0];
}

async function briefedToday(): Promise<boolean> {
    const key = `briefed_${today()}`;
    const val = await AsyncStorage.getItem(key);
    return val === 'true';
}

async function markBriefed(): Promise<void> {
    const key = `briefed_${today()}`;
    await AsyncStorage.setItem(key, 'true');
}

// ---------------------------------------------------------------------------
// Proactive Engine
// ---------------------------------------------------------------------------

/**
 * Run all proactive checks. Returns alerts Ember should surface.
 * Designed to run in ~30 seconds (iOS BGAppRefreshTask limit).
 */
export async function runProactiveChecks(): Promise<ProactiveAlert[]> {
    const alerts: ProactiveAlert[] = [];
    const now = new Date();
    const hour = now.getHours();
    const timestamp = now.toISOString();

    // 1. Meeting prep — next meeting in < 30 min?
    try {
        const next = await NativeCalendar.getNextEvent();
        if (next && minutesUntil(next.startDate) < 30 && minutesUntil(next.startDate) > 0) {
            const mins = minutesUntil(next.startDate);
            const location = next.location ? ` at ${next.location}` : '';
            alerts.push({
                type: 'meeting_prep',
                message: `Heads up — "${next.title}" starts in ${mins} minutes${location}. Want me to help you prepare?`,
                event: next,
                timestamp,
            });
        }
    } catch { }

    // 2. Guardian nudge — late night (11 PM - 5 AM)
    if (hour >= 23 || hour < 5) {
        alerts.push({
            type: 'guardian_time',
            message: hour >= 23
                ? "It's getting late... maybe sleep on it? 🌙"
                : "You're up early — or still up. Either way, I'm here. ☕",
            timestamp,
        });
    }

    // 3. Morning briefing (7-9 AM, once per day)
    if (hour >= 7 && hour <= 9 && !(await briefedToday())) {
        try {
            const events = await NativeCalendar.getTodayEvents();
            let steps = 0;
            try {
                steps = await NativeHealth.getSteps(today());
            } catch { }

            const eventCount = events.length;
            const firstEvent = events[0];
            let message = `Good morning! `;

            if (eventCount === 0) {
                message += `Your calendar is clear today. `;
            } else if (eventCount === 1) {
                message += `You have 1 event today: "${firstEvent.title}". `;
            } else {
                message += `You have ${eventCount} events today. First up: "${firstEvent.title}". `;
            }

            if (steps > 0) {
                message += `Yesterday you hit ${steps.toLocaleString()} steps.`;
            }

            alerts.push({
                type: 'morning_briefing',
                message: message.trim(),
                events,
                steps,
                timestamp,
            });

            await markBriefed();
        } catch { }
    }

    // 4. Step goal celebration (afternoon check, > 10k steps)
    if (hour >= 14 && hour <= 18) {
        try {
            const steps = await NativeHealth.getSteps(today());
            if (steps >= 10_000) {
                alerts.push({
                    type: 'step_goal',
                    message: `🎉 ${steps.toLocaleString()} steps today! You crushed it.`,
                    steps,
                    timestamp,
                });
            }
        } catch { }
    }

    // 5. Sleep check (morning, check previous night)
    if (hour >= 8 && hour <= 10) {
        try {
            const sleepHours = await NativeHealth.getSleepHours(today());
            if (sleepHours > 0 && sleepHours < 6) {
                alerts.push({
                    type: 'sleep_check',
                    message: `You only got ${sleepHours.toFixed(1)} hours of sleep last night. Take it easy today. 💤`,
                    sleepHours,
                    timestamp,
                });
            }
        } catch { }
    }

    return alerts;
}

/**
 * Get a single proactive greeting for app foreground.
 * Returns the highest-priority alert, or a default greeting.
 */
export async function getGreeting(): Promise<string> {
    try {
        const alerts = await runProactiveChecks();
        if (alerts.length > 0) {
            // Priority: meeting_prep > morning_briefing > guardian > others
            const priority: AlertType[] = ['meeting_prep', 'morning_briefing', 'guardian_time', 'sleep_check', 'step_goal'];
            for (const type of priority) {
                const alert = alerts.find(a => a.type === type);
                if (alert) return alert.message;
            }
            return alerts[0].message;
        }
    } catch { }

    // Default greetings by time of day
    const hour = new Date().getHours();
    if (hour < 12) return "Good morning! What's on your mind?";
    if (hour < 17) return "Hey! Need anything this afternoon?";
    if (hour < 21) return "Good evening. How'd your day go?";
    return "Still up? I'm here if you need me.";
}
