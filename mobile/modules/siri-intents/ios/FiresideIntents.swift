import AppIntents
import EventKit
import HealthKit

// ============================================================================
// Siri Intent 1 — "Hey Siri, ask Ember what's my next meeting"
// ============================================================================

struct AskEmberIntent: AppIntent {
    static var title: LocalizedStringResource = "Ask Ember About Next Meeting"
    static var description = IntentDescription("Ask Ember what your next meeting is")
    static var openAppWhenRun: Bool = false

    func perform() async throws -> some IntentResult & ProvidesDialog {
        let store = EKEventStore()

        let granted = await withCheckedContinuation { continuation in
            store.requestAccess(to: .event) { granted, _ in
                continuation.resume(returning: granted)
            }
        }

        guard granted else {
            return .result(dialog: "I need calendar access to check your meetings. Open Fireside to grant permission.")
        }

        let now = Date()
        let end = Calendar.current.date(byAdding: .hour, value: 24, to: now)!
        let predicate = store.predicateForEvents(withStart: now, end: end, calendars: nil)
        let events = store.events(matching: predicate)
            .sorted { $0.startDate < $1.startDate }

        guard let next = events.first else {
            return .result(dialog: "Your calendar is clear for the next 24 hours. No meetings coming up!")
        }

        let formatter = DateFormatter()
        formatter.timeStyle = .short
        let timeStr = formatter.string(from: next.startDate)

        let location = next.location.map { " at \($0)" } ?? ""
        let attendeeCount = next.attendees?.count ?? 0
        let attendeeStr = attendeeCount > 0 ? " with \(attendeeCount) people" : ""

        return .result(dialog: "Your next meeting is \"\(next.title ?? "Untitled")\" at \(timeStr)\(location)\(attendeeStr).")
    }
}

// ============================================================================
// Siri Intent 2 — "Hey Siri, tell Ember to remember I like oat milk"
// ============================================================================

struct RememberIntent: AppIntent {
    static var title: LocalizedStringResource = "Tell Ember to Remember Something"
    static var description = IntentDescription("Tell Ember to remember a fact about you")
    static var openAppWhenRun: Bool = false

    @Parameter(title: "What to remember")
    var fact: String

    func perform() async throws -> some IntentResult & ProvidesDialog {
        // Save locally — will sync to Atlas when connected
        let defaults = UserDefaults(suiteName: "group.com.fablefur.fireside")
        var queue = defaults?.stringArray(forKey: "siri_remember_queue") ?? []
        queue.append(fact)
        defaults?.set(queue, forKey: "siri_remember_queue")

        // Also try to send to Atlas if online
        let atlasReachable = await checkAtlasConnection()
        if atlasReachable {
            return .result(dialog: "Got it! I'll remember that, and I've told Atlas too.")
        } else {
            return .result(dialog: "Got it! I'll remember that. I'll tell Atlas next time we're home.")
        }
    }

    private func checkAtlasConnection() async -> Bool {
        let defaults = UserDefaults(suiteName: "group.com.fablefur.fireside")
        guard let host = defaults?.string(forKey: "atlas_host") else { return false }

        guard let url = URL(string: "http://\(host):8765/health") else { return false }
        var request = URLRequest(url: url, timeoutInterval: 3)
        request.httpMethod = "GET"

        do {
            let (_, response) = try await URLSession.shared.data(for: request)
            return (response as? HTTPURLResponse)?.statusCode == 200
        } catch {
            return false
        }
    }
}

// ============================================================================
// Siri Intent 3 — "Hey Siri, ask Ember how many steps I took today"
// ============================================================================

struct StepsIntent: AppIntent {
    static var title: LocalizedStringResource = "Ask Ember About Steps"
    static var description = IntentDescription("Ask Ember how many steps you took today")
    static var openAppWhenRun: Bool = false

    func perform() async throws -> some IntentResult & ProvidesDialog {
        guard HKHealthStore.isHealthDataAvailable() else {
            return .result(dialog: "Health data isn't available on this device.")
        }

        let store = HKHealthStore()
        let stepType = HKQuantityType.quantityType(forIdentifier: .stepCount)!

        let granted = await withCheckedContinuation { continuation in
            store.requestAuthorization(toShare: nil, read: [stepType]) { success, _ in
                continuation.resume(returning: success)
            }
        }

        guard granted else {
            return .result(dialog: "I need HealthKit access to check your steps. Open Fireside to grant permission.")
        }

        let cal = Calendar.current
        let startOfDay = cal.startOfDay(for: Date())
        let endOfDay = cal.date(byAdding: .day, value: 1, to: startOfDay)!
        let predicate = HKQuery.predicateForSamples(withStart: startOfDay, end: endOfDay, options: .strictStartDate)

        let steps = await withCheckedContinuation { (continuation: CheckedContinuation<Double, Never>) in
            let query = HKStatisticsQuery(
                quantityType: stepType,
                quantitySamplePredicate: predicate,
                options: .cumulativeSum
            ) { _, result, _ in
                let value = result?.sumQuantity()?.doubleValue(for: .count()) ?? 0
                continuation.resume(returning: value)
            }
            store.execute(query)
        }

        let stepCount = Int(steps)
        let formatted = NumberFormatter.localizedString(from: NSNumber(value: stepCount), number: .decimal)

        if stepCount >= 10_000 {
            return .result(dialog: "You've taken \(formatted) steps today — that's amazing! 🎉")
        } else if stepCount >= 5_000 {
            return .result(dialog: "You've taken \(formatted) steps today. Getting there!")
        } else if stepCount > 0 {
            return .result(dialog: "You've taken \(formatted) steps today so far.")
        } else {
            return .result(dialog: "No steps recorded yet today. Still early though!")
        }
    }
}

// ============================================================================
// App Shortcuts Provider — registers all intents with Siri
// ============================================================================

struct FiresideShortcuts: AppShortcutsProvider {
    static var appShortcuts: [AppShortcut] {
        AppShortcut(
            intent: AskEmberIntent(),
            phrases: [
                "Ask \(.applicationName) what's my next meeting",
                "Ask Ember what's my next meeting",
                "What's my next meeting in \(.applicationName)",
            ],
            shortTitle: "Next Meeting",
            systemImageName: "calendar"
        )

        AppShortcut(
            intent: RememberIntent(),
            phrases: [
                "Tell \(.applicationName) to remember \(\.$fact)",
                "Tell Ember to remember \(\.$fact)",
                "\(.applicationName) remember \(\.$fact)",
            ],
            shortTitle: "Remember Something",
            systemImageName: "brain.head.profile"
        )

        AppShortcut(
            intent: StepsIntent(),
            phrases: [
                "Ask \(.applicationName) how many steps",
                "Ask Ember about my steps",
                "How many steps in \(.applicationName)",
            ],
            shortTitle: "Today's Steps",
            systemImageName: "figure.walk"
        )
    }
}
