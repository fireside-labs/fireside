/**
 * NativeHealth — TypeScript bindings for the HealthKit native module.
 *
 * Ember checks your daily stats to give you personalized wellness nudges.
 * Read-only — Ember never writes health data. Data stays on-device.
 */
import { requireNativeModule } from 'expo-modules-core';

const NativeHealthModule = requireNativeModule('NativeHealth');

export interface ActivitySummary {
    steps: number;
    calories: number;
    activeMinutes: number;
}

/** Request HealthKit permission (read-only). Returns true if granted. */
export function requestPermission(): Promise<boolean> {
    return NativeHealthModule.requestPermission();
}

/** Get step count for a given date (ISO string, e.g. '2026-03-15'). */
export function getSteps(date: string): Promise<number> {
    return NativeHealthModule.getSteps(date);
}

/** Get total sleep hours for a given date. */
export function getSleepHours(date: string): Promise<number> {
    return NativeHealthModule.getSleepHours(date);
}

/** Get today's activity summary: steps, calories, active minutes. */
export function getActivitySummary(): Promise<ActivitySummary> {
    return NativeHealthModule.getActivitySummary();
}
