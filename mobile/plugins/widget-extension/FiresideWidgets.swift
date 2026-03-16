import SwiftUI
import WidgetKit

// MARK: - Shared Data Model

struct FiresideWidgetData {
    let companionEmoji: String
    let companionName: String
    let companionMood: String
    let ownerName: String
    let nextEventTitle: String?
    let nextEventTime: String?
    let todayEvents: [(String, String)]  // (title, time)
    let steps: Int
    let isOnline: Bool
}

extension FiresideWidgetData {
    static func load() -> FiresideWidgetData {
        let defaults = UserDefaults(suiteName: "group.com.fablefur.fireside") ?? .standard
        return FiresideWidgetData(
            companionEmoji: defaults.string(forKey: "companion_emoji") ?? "🦊",
            companionName: defaults.string(forKey: "companion_name") ?? "Ember",
            companionMood: defaults.string(forKey: "companion_mood") ?? "Happy",
            ownerName: defaults.string(forKey: "owner_name") ?? "Friend",
            nextEventTitle: defaults.string(forKey: "next_event_title"),
            nextEventTime: defaults.string(forKey: "next_event_time"),
            todayEvents: {
                guard let data = defaults.data(forKey: "today_events"),
                      let arr = try? JSONDecoder().decode([[String]].self, from: data)
                else { return [] }
                return arr.compactMap { $0.count >= 2 ? ($0[0], $0[1]) : nil }
            }(),
            steps: defaults.integer(forKey: "today_steps"),
            isOnline: defaults.bool(forKey: "atlas_online")
        )
    }
}

// MARK: - Brand Colors

extension Color {
    static let fireAmber = Color(red: 232/255, green: 113/255, blue: 44/255)   // #E8712C
    static let fireGold  = Color(red: 245/255, green: 166/255, blue: 35/255)   // #F5A623
    static let fireBg    = Color(red: 26/255, green: 18/255, blue: 11/255)     // #1A120B
    static let fireGlass = Color(red: 42/255, green: 30/255, blue: 20/255)     // #2A1E14
    static let fireText  = Color(red: 240/255, green: 220/255, blue: 200/255)  // #F0DCC8
    static let fireDim   = Color(red: 160/255, green: 130/255, blue: 100/255)  // #A08264
}

// MARK: - Timeline Provider

struct FiresideProvider: TimelineProvider {
    func placeholder(in context: Context) -> FiresideEntry {
        FiresideEntry(date: Date(), data: .load())
    }

    func getSnapshot(in context: Context, completion: @escaping (FiresideEntry) -> Void) {
        completion(FiresideEntry(date: Date(), data: .load()))
    }

    func getTimeline(in context: Context, completion: @escaping (Timeline<FiresideEntry>) -> Void) {
        let entry = FiresideEntry(date: Date(), data: .load())
        // Refresh every 15 minutes
        let nextUpdate = Calendar.current.date(byAdding: .minute, value: 15, to: Date())!
        completion(Timeline(entries: [entry], policy: .after(nextUpdate)))
    }
}

struct FiresideEntry: TimelineEntry {
    let date: Date
    let data: FiresideWidgetData
}

// MARK: - Small Widget (2x2)

struct SmallWidgetView: View {
    let entry: FiresideEntry

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(entry.data.companionEmoji)
                    .font(.title2)
                Text(entry.data.companionName)
                    .font(.headline)
                    .foregroundColor(.fireText)
            }

            Text("😊 \(entry.data.companionMood)")
                .font(.caption)
                .foregroundColor(.fireDim)

            Spacer()

            if let title = entry.data.nextEventTitle, let time = entry.data.nextEventTime {
                Text("Next: \(time)")
                    .font(.caption2)
                    .foregroundColor(.fireAmber)
                Text(title)
                    .font(.caption)
                    .foregroundColor(.fireText)
                    .lineLimit(1)
            } else {
                Text("No more events ✨")
                    .font(.caption)
                    .foregroundColor(.fireDim)
            }
        }
        .padding(12)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .leading)
        .background(Color.fireBg)
    }
}

// MARK: - Medium Widget (4x2)

struct MediumWidgetView: View {
    let entry: FiresideEntry

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(entry.data.companionEmoji)
                    .font(.title3)
                Text("Good \(greeting), \(entry.data.ownerName)!")
                    .font(.headline)
                    .foregroundColor(.fireText)
            }

            if entry.data.todayEvents.isEmpty {
                Text("📅 No meetings today")
                    .font(.caption)
                    .foregroundColor(.fireDim)
            } else {
                ForEach(entry.data.todayEvents.prefix(3), id: \.0) { event in
                    HStack(spacing: 4) {
                        Text("📅")
                            .font(.caption2)
                        Text(event.1)
                            .font(.caption2)
                            .foregroundColor(.fireAmber)
                        Text(event.0)
                            .font(.caption2)
                            .foregroundColor(.fireText)
                            .lineLimit(1)
                    }
                }
            }

            Spacer()

            HStack {
                Text("👣 \(entry.data.steps.formatted()) steps")
                    .font(.caption)
                    .foregroundColor(.fireDim)
                Spacer()
                Text("Chat with \(entry.data.companionName) →")
                    .font(.caption)
                    .foregroundColor(.fireAmber)
            }
        }
        .padding(12)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .leading)
        .background(Color.fireBg)
    }

    var greeting: String {
        let hour = Calendar.current.component(.hour, from: Date())
        if hour < 12 { return "morning" }
        if hour < 18 { return "afternoon" }
        return "evening"
    }
}

// MARK: - Lock Screen Widget (Circular)

struct LockScreenWidgetView: View {
    let entry: FiresideEntry

    var body: some View {
        VStack(spacing: 2) {
            Text(entry.data.companionEmoji)
                .font(.body)
            if let time = entry.data.nextEventTime {
                Text(time)
                    .font(.caption2)
                    .foregroundColor(.fireAmber)
            }
        }
    }
}

// MARK: - Widget Bundle

@main
struct FiresideWidgetBundle: WidgetBundle {
    var body: some Widget {
        FiresideSmallWidget()
        FiresideMediumWidget()
        FiresideLockScreenWidget()
    }
}

struct FiresideSmallWidget: Widget {
    let kind = "FiresideSmall"
    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: FiresideProvider()) { entry in
            SmallWidgetView(entry: entry)
        }
        .configurationDisplayName("Ember")
        .description("Your companion at a glance")
        .supportedFamilies([.systemSmall])
    }
}

struct FiresideMediumWidget: Widget {
    let kind = "FiresideMedium"
    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: FiresideProvider()) { entry in
            MediumWidgetView(entry: entry)
        }
        .configurationDisplayName("Ember Daily")
        .description("Calendar, steps, and more")
        .supportedFamilies([.systemMedium])
    }
}

struct FiresideLockScreenWidget: Widget {
    let kind = "FiresideLockScreen"
    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: FiresideProvider()) { entry in
            LockScreenWidgetView(entry: entry)
        }
        .configurationDisplayName("Ember Lock")
        .description("Next event at a glance")
        .supportedFamilies([.accessoryCircular])
    }
}
