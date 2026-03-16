import ExpoModulesCore
import EventKit

public class NativeCalendarModule: Module {
    private let store = EKEventStore()

    public func definition() -> ModuleDefinition {
        Name("NativeCalendar")

        /// Request calendar permission on first use — never upfront
        AsyncFunction("requestPermission") { () -> Bool in
            return await withCheckedContinuation { continuation in
                self.store.requestAccess(to: .event) { granted, _ in
                    continuation.resume(returning: granted)
                }
            }
        }

        /// Get upcoming events within the next N hours
        AsyncFunction("getUpcomingEvents") { (hours: Double) -> [[String: Any?]] in
            let granted = await self.requestAccess()
            guard granted else { return [] }

            let now = Date()
            let end = Calendar.current.date(byAdding: .hour, value: Int(hours), to: now)!
            let predicate = self.store.predicateForEvents(withStart: now, end: end, calendars: nil)
            let events = self.store.events(matching: predicate)

            return events.map { self.eventToDict($0) }
        }

        /// Get the next calendar event (closest upcoming)
        AsyncFunction("getNextEvent") { () -> [String: Any?]? in
            let granted = await self.requestAccess()
            guard granted else { return nil }

            let now = Date()
            let end = Calendar.current.date(byAdding: .hour, value: 24, to: now)!
            let predicate = self.store.predicateForEvents(withStart: now, end: end, calendars: nil)
            let events = self.store.events(matching: predicate)
                .sorted { $0.startDate < $1.startDate }

            guard let next = events.first else { return nil }
            return self.eventToDict(next)
        }

        /// Get all events happening today
        AsyncFunction("getTodayEvents") { () -> [[String: Any?]] in
            let granted = await self.requestAccess()
            guard granted else { return [] }

            let cal = Calendar.current
            let startOfDay = cal.startOfDay(for: Date())
            let endOfDay = cal.date(byAdding: .day, value: 1, to: startOfDay)!
            let predicate = self.store.predicateForEvents(withStart: startOfDay, end: endOfDay, calendars: nil)
            let events = self.store.events(matching: predicate)
                .sorted { $0.startDate < $1.startDate }

            return events.map { self.eventToDict($0) }
        }
    }

    // MARK: - Private Helpers

    private func requestAccess() async -> Bool {
        return await withCheckedContinuation { continuation in
            store.requestAccess(to: .event) { granted, _ in
                continuation.resume(returning: granted)
            }
        }
    }

    private func eventToDict(_ event: EKEvent) -> [String: Any?] {
        let formatter = ISO8601DateFormatter()
        var dict: [String: Any?] = [
            "id": event.eventIdentifier,
            "title": event.title,
            "startDate": formatter.string(from: event.startDate),
            "endDate": formatter.string(from: event.endDate),
            "location": event.location,
            "notes": event.notes,
        ]

        if let attendees = event.attendees {
            dict["attendees"] = attendees.compactMap { $0.name }
        }

        return dict
    }
}
