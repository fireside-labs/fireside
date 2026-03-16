import ActivityKit
import SwiftUI
import WidgetKit

// MARK: - Live Activity Attributes

struct MeetingActivityAttributes: ActivityAttributes {
    /// Static data that doesn't change during the activity
    struct ContentState: Codable, Hashable {
        let minutesElapsed: Int
        let lastMeetingContext: String?
    }

    let meetingTitle: String
    let startTime: Date
    let attendees: [String]
    let companionEmoji: String
    let companionName: String
}

// MARK: - Live Activity UI

struct MeetingLiveActivityView: View {
    let context: ActivityViewContext<MeetingActivityAttributes>

    var body: some View {
        HStack(spacing: 12) {
            // Companion emoji
            Text(context.attributes.companionEmoji)
                .font(.title)

            VStack(alignment: .leading, spacing: 4) {
                // Meeting title
                Text("Meeting: \(context.attributes.meetingTitle)")
                    .font(.headline)
                    .foregroundColor(.fireText)
                    .lineLimit(1)

                // Attendees + elapsed time
                HStack(spacing: 4) {
                    Text("Started \(context.state.minutesElapsed) min ago")
                        .font(.caption)
                        .foregroundColor(.fireDim)

                    if !context.attributes.attendees.isEmpty {
                        Text("·")
                            .foregroundColor(.fireDim)
                        let names = context.attributes.attendees.prefix(2).joined(separator: ", ")
                        let extra = context.attributes.attendees.count > 2
                            ? " + \(context.attributes.attendees.count - 2)"
                            : ""
                        Text("\(names)\(extra)")
                            .font(.caption)
                            .foregroundColor(.fireDim)
                    }
                }

                // Last meeting context (if available)
                if let lastContext = context.state.lastMeetingContext {
                    Text("Last time: \(lastContext)")
                        .font(.caption2)
                        .foregroundColor(.fireAmber)
                        .lineLimit(1)
                }
            }

            Spacer()
        }
        .padding(16)
        .background(Color.fireBg)
    }
}

// MARK: - Brand Colors (shared with Widgets)

extension Color {
    // Note: These are defined in FiresideWidgets.swift as well.
    // In a production build, use a shared color asset catalog.
}

// MARK: - Widget Configuration for Live Activity

struct MeetingLiveActivity: Widget {
    let kind = "FiresideMeeting"

    var body: some WidgetConfiguration {
        ActivityConfiguration(for: MeetingActivityAttributes.self) { context in
            // Lock screen / banner presentation
            MeetingLiveActivityView(context: context)
        } dynamicIsland: { context in
            DynamicIsland {
                // Expanded view
                DynamicIslandExpandedRegion(.leading) {
                    Text(context.attributes.companionEmoji)
                        .font(.title2)
                }
                DynamicIslandExpandedRegion(.center) {
                    VStack(alignment: .leading, spacing: 2) {
                        Text(context.attributes.meetingTitle)
                            .font(.caption)
                            .foregroundColor(.fireText)
                            .lineLimit(1)
                        Text("\(context.state.minutesElapsed)m elapsed")
                            .font(.caption2)
                            .foregroundColor(.fireDim)
                    }
                }
                DynamicIslandExpandedRegion(.trailing) {
                    Text("🔥")
                }
            } compactLeading: {
                Text(context.attributes.companionEmoji)
                    .font(.caption)
            } compactTrailing: {
                Text("\(context.state.minutesElapsed)m")
                    .font(.caption2)
                    .foregroundColor(.fireAmber)
            } minimal: {
                Text(context.attributes.companionEmoji)
                    .font(.caption2)
            }
        }
    }
}
