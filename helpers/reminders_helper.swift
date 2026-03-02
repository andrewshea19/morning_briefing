#!/usr/bin/env swift
// Fetches incomplete reminders via EventKit (no Reminders.app needed).
// Usage: swift reminders_helper.swift [ListName1] [ListName2] ...
// Outputs JSON object keyed by list name to stdout.

import EventKit
import Foundation

let targetNames = Set(CommandLine.arguments.dropFirst())

let store = EKEventStore()
let sem = DispatchSemaphore(value: 0)
var accessGranted = false

store.requestFullAccessToReminders { granted, _ in
    accessGranted = granted
    sem.signal()
}
sem.wait()

guard accessGranted else {
    fputs("ERROR: Reminders access not granted. Open System Settings > Privacy & Security > Reminders and grant access to Terminal (or swift).\n", stderr)
    exit(1)
}

var ekCalendars: [EKCalendar]? = nil
if !targetNames.isEmpty {
    ekCalendars = store.calendars(for: .reminder).filter { targetNames.contains($0.title) }
}

let predicate = store.predicateForIncompleteReminders(
    withDueDateStarting: nil, ending: nil, calendars: ekCalendars
)
let fetchSem = DispatchSemaphore(value: 0)
var reminders: [EKReminder] = []

store.fetchReminders(matching: predicate) { result in
    reminders = result ?? []
    fetchSem.signal()
}
fetchSem.wait()

let dateFmt = DateFormatter()
dateFmt.dateFormat = "yyyy-MM-dd"

var results: [String: [[String: Any]]] = [:]
for reminder in reminders {
    let listName = reminder.calendar.title
    var entry: [String: Any] = ["name": reminder.title ?? "(no title)"]

    if let components = reminder.dueDateComponents,
       let date = Calendar.current.date(from: components) {
        entry["due"] = dateFmt.string(from: date)
    }

    if results[listName] == nil {
        results[listName] = []
    }
    results[listName]!.append(entry)
}

let data = try! JSONSerialization.data(withJSONObject: results, options: [])
print(String(data: data, encoding: .utf8)!)
