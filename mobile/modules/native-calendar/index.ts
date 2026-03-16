/**
 * NativeCalendar — TypeScript bindings for the EventKit native module.
 *
 * Ember reads your calendar to remind you about upcoming meetings
 * and help you prepare. Data stays on-device.
 */
import { requireNativeModule } from 'expo-modules-core';

const NativeCalendarModule = requireNativeModule('NativeCalendar');

export interface CalendarEvent {
    id: string;
    title: string;
    startDate: string; // ISO 8601
    endDate: string;
    location?: string;
    notes?: string;
    attendees?: string[];
}

/** Request calendar permission. Returns true if granted. */
export function requestPermission(): Promise<boolean> {
    return NativeCalendarModule.requestPermission();
}

/** Get upcoming events within the next N hours. */
export function getUpcomingEvents(hours: number): Promise<CalendarEvent[]> {
    return NativeCalendarModule.getUpcomingEvents(hours);
}

/** Get the very next calendar event (within 24h). */
export function getNextEvent(): Promise<CalendarEvent | null> {
    return NativeCalendarModule.getNextEvent();
}

/** Get all events happening today. */
export function getTodayEvents(): Promise<CalendarEvent[]> {
    return NativeCalendarModule.getTodayEvents();
}
