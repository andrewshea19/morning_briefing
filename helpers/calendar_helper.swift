#!/usr/bin/env swift
// Fetches today's calendar events via EventKit (no Calendar.app needed).
// Usage: swift calendar_helper.swift [CalendarName1] [CalendarName2] ...
// Outputs JSON array to stdout.

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
sem.wait()

guard accessGranted else {
    fputs("ERROR: Calendar access not granted. Open System Settings > Privacy & Security > Calendars and grant access to Terminal (or swift).\n", stderr)
    exit(1)
}

let cal = Calendar.current
let startOfDay = cal.startOfDay(for: Date())
let endOfDay = cal.date(byAdding: .day, value: 1, to: startOfDay)!

var ekCalendars: [EKCalendar]? = nil
if !targetNames.isEmpty {
    ekCalendars = store.calendars(for: .event).filter { targetNames.contains($0.title) }
}

let predicate = store.predicateForEvents(withStart: startOfDay, end: endOfDay, calendars: ekCalendars)
let events = store.events(matching: predicate).sorted { $0.startDate < $1.startDate }

let timeFmt = DateFormatter()
timeFmt.dateFormat = "h:mm a"

var results: [[String: Any]] = []
for event in events {
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
    if let loc = event.location, !loc.isEmpty {
        entry["location"] = loc
    }
    results.append(entry)
}

let data = try! JSONSerialization.data(withJSONObject: results, options: [])
print(String(data: data, encoding: .utf8)!)
