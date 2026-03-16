import ExpoModulesCore
import Contacts

public class NativeContactsModule: Module {
    private let store = CNContactStore()

    public func definition() -> ModuleDefinition {
        Name("NativeContacts")

        /// Request contacts permission on first use
        AsyncFunction("requestPermission") { () -> Bool in
            return await withCheckedContinuation { continuation in
                self.store.requestAccess(for: .contacts) { granted, _ in
                    continuation.resume(returning: granted)
                }
            }
        }

        /// Search contacts by name (fuzzy match)
        AsyncFunction("searchByName") { (name: String) -> [[String: Any?]] in
            let granted = await self.requestAccess()
            guard granted else { return [] }

            let keysToFetch: [CNKeyDescriptor] = [
                CNContactIdentifierKey as CNKeyDescriptor,
                CNContactGivenNameKey as CNKeyDescriptor,
                CNContactFamilyNameKey as CNKeyDescriptor,
                CNContactPhoneNumbersKey as CNKeyDescriptor,
                CNContactEmailAddressesKey as CNKeyDescriptor,
                CNContactOrganizationNameKey as CNKeyDescriptor,
                CNContactDatesKey as CNKeyDescriptor,
            ]

            let predicate = CNContact.predicateForContacts(matchingName: name)
            do {
                let contacts = try self.store.unifiedContacts(matching: predicate, keysToFetch: keysToFetch)
                return contacts.prefix(20).map { self.contactToDict($0) }
            } catch {
                return []
            }
        }

        /// Get recently modified contacts
        AsyncFunction("getRecent") { (count: Int) -> [[String: Any?]] in
            let granted = await self.requestAccess()
            guard granted else { return [] }

            let keysToFetch: [CNKeyDescriptor] = [
                CNContactIdentifierKey as CNKeyDescriptor,
                CNContactGivenNameKey as CNKeyDescriptor,
                CNContactFamilyNameKey as CNKeyDescriptor,
                CNContactPhoneNumbersKey as CNKeyDescriptor,
                CNContactEmailAddressesKey as CNKeyDescriptor,
                CNContactOrganizationNameKey as CNKeyDescriptor,
            ]

            let fetchRequest = CNContactFetchRequest(keysToFetch: keysToFetch)
            fetchRequest.sortOrder = .userDefault

            var contacts: [[String: Any?]] = []
            do {
                try self.store.enumerateContacts(with: fetchRequest) { contact, stop in
                    contacts.append(self.contactToDict(contact))
                    if contacts.count >= min(count, 50) {
                        stop.pointee = true
                    }
                }
            } catch {}

            return contacts
        }
    }

    // MARK: - Private Helpers

    private func requestAccess() async -> Bool {
        return await withCheckedContinuation { continuation in
            store.requestAccess(for: .contacts) { granted, _ in
                continuation.resume(returning: granted)
            }
        }
    }

    private func contactToDict(_ contact: CNContact) -> [String: Any?] {
        let fullName = "\(contact.givenName) \(contact.familyName)".trimmingCharacters(in: .whitespaces)
        return [
            "id": contact.identifier,
            "name": fullName.isEmpty ? "Unknown" : fullName,
            "phone": contact.phoneNumbers.first?.value.stringValue,
            "email": contact.emailAddresses.first?.value as String?,
            "organization": contact.organizationName.isEmpty ? nil : contact.organizationName,
        ]
    }
}
