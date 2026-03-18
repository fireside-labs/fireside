/**
 * 📇 ContactsBridge — iOS Contacts integration stub.
 *
 * Sprint 3: "Extra Senses" — lets the companion access contacts
 * with explicit user permission.
 *
 * NOTE: Requires `expo-contacts` to be installed.
 * Install with: `npx expo install expo-contacts`
 * If not installed, all functions gracefully return empty/null.
 *
 * Privacy: contacts are NEVER sent to the cloud. They're processed
 * on-device by Qwen 0.5B for context (e.g., "call mom" → resolves
 * to the correct contact).
 */

export interface FiresideContact {
    id: string;
    name: string;
    phone?: string;
    email?: string;
    nickname?: string;
}

let Contacts: any = null;

// Try to load expo-contacts dynamically
try {
    Contacts = require("expo-contacts");
} catch {
    // expo-contacts not installed — functions will return safe defaults
}

/**
 * Request permission and load contacts.
 * Returns null if permission denied or expo-contacts not installed.
 */
export async function loadContacts(): Promise<FiresideContact[] | null> {
    if (!Contacts) return null;

    const { status } = await Contacts.requestPermissionsAsync();
    if (status !== "granted") return null;

    const { data } = await Contacts.getContactsAsync({
        fields: [
            Contacts.Fields.Name,
            Contacts.Fields.PhoneNumbers,
            Contacts.Fields.Emails,
            Contacts.Fields.Nickname,
        ],
        sort: Contacts.SortTypes.FirstName,
    });

    return data.map((c: any) => ({
        id: c.id || String(Math.random()),
        name: c.name || "Unknown",
        phone: c.phoneNumbers?.[0]?.number,
        email: c.emails?.[0]?.email,
        nickname: c.nickname || undefined,
    }));
}

/**
 * Find contacts matching a query (name, nickname, etc).
 * Used by the companion for natural language contact resolution.
 */
export function searchContacts(contacts: FiresideContact[], query: string): FiresideContact[] {
    const lower = query.toLowerCase();
    return contacts.filter((c) => {
        return (
            c.name.toLowerCase().includes(lower) ||
            c.nickname?.toLowerCase().includes(lower) ||
            c.phone?.includes(query) ||
            c.email?.toLowerCase().includes(lower)
        );
    });
}

/**
 * Resolve a natural language reference to a contact.
 * e.g., "mom" → finds contact with nickname "Mom" or name containing "Mom"
 */
export function resolveContactRef(contacts: FiresideContact[], ref: string): FiresideContact | null {
    const matches = searchContacts(contacts, ref);
    return matches.length > 0 ? matches[0] : null;
}
