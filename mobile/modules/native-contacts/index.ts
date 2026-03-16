/**
 * NativeContacts — TypeScript bindings for the Contacts.framework native module.
 *
 * Ember looks up contacts when you mention someone by name,
 * so she can help you connect. Data stays on-device.
 */
import { requireNativeModule } from 'expo-modules-core';

const NativeContactsModule = requireNativeModule('NativeContacts');

export interface Contact {
    id: string;
    name: string;
    phone?: string;
    email?: string;
    organization?: string;
    lastContacted?: string;
}

/** Request contacts permission. Returns true if granted. */
export function requestPermission(): Promise<boolean> {
    return NativeContactsModule.requestPermission();
}

/** Search contacts by name (fuzzy match). Returns up to 20 results. */
export function searchByName(name: string): Promise<Contact[]> {
    return NativeContactsModule.searchByName(name);
}

/** Get recently modified contacts. */
export function getRecent(count: number): Promise<Contact[]> {
    return NativeContactsModule.getRecent(count);
}
