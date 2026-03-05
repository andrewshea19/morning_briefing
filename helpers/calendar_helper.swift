// Fetches today's calendar events + next 5 upcoming via EventKit.
// Usage: calendar_helper [CalendarName1] [CalendarName2] ...
// Outputs JSON with "today" and "upcoming" arrays to stdout.

import EventKit
import Foundation

let targetNames = Set(CommandLine.arguments.dropFirst())

let store = EKEventStore()
let sem = DispatchSemaphore(value: 0)
var accessGranted = false

store.requestFullAccessToEvents { granted, _ in
    accessGranted = granted
    sem.signal()
}

if sem.wait(timeout: .now() + 5) == .timedOut || !accessGranted {
    fputs("ERROR: Calendar access not granted. Run this binary once from Terminal to trigger the permission prompt, then grant access in System Settings > Privacy & Security > Calendars.\n", stderr)
    exit(1)
}

let cal = Calendar.current
let startOfDay = cal.startOfDay(for: Date())
let endOfDay = cal.date(byAdding: .day, value: 1, to: startOfDay)!

var ekCalendars: [EKCalendar]? = nil
if !targetNames.isEmpty {
    ekCalendars = store.calendars(for: .event).filter { targetNames.contains($0.title) }
}

let timeFmt = DateFormatter()
timeFmt.dateFormat = "h:mm a"

let dateFmt = DateFormatter()
dateFmt.dateFormat = "E M/d"

func eventToDict(_ event: EKEvent, includeDate: Bool = false) -> [String: Any] {
    var entry: [String: Any] = [
        "calendar": event.calendar.title,
        "title": event.title ?? "(no title)",
        "allDay": event.isAllDay,
    ]
    if event.isAllDay {
        entry["time"] = "All day"
    } else {
        entry["time"] = timeFmt.string(from: event.startDate) + " - " + timeFmt.string(from: event.endDate)
    }
    if includeDate {
        entry["date"] = dateFmt.string(from: event.startDate)
    }
    if let loc = event.location, !loc.isEmpty {
        entry["location"] = loc
    }
    return entry
}

// Today's events
let todayPredicate = store.predicateForEvents(withStart: startOfDay, end: endOfDay, calendars: ekCalendars)
let todayEvents = store.events(matching: todayPredicate).sorted { $0.startDate < $1.startDate }

// Next 5 upcoming events (after today, look ahead 90 days)
let lookAhead = cal.date(byAdding: .day, value: 90, to: endOfDay)!
let futurePredicate = store.predicateForEvents(withStart: endOfDay, end: lookAhead, calendars: ekCalendars)
let futureEvents = store.events(matching: futurePredicate)
    .sorted { $0.startDate < $1.startDate }
    .prefix(5)

let output: [String: Any] = [
    "today": todayEvents.map { eventToDict($0) },
    "upcoming": futureEvents.map { eventToDict($0, includeDate: true) },
]

let data = try! JSONSerialization.data(withJSONObject: output, options: [])
print(String(data: data, encoding: .utf8)!)
