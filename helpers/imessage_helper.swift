// Fetches recent iMessages via SQLite3 and resolves contacts via Contacts framework.
// Requires Full Disk Access for the compiled binary.
// Usage: imessage_helper [lookback_hours]
// Outputs JSON array to stdout.

import Foundation
import SQLite3
import Contacts

// --- Arguments ---
let lookbackHours = Int(CommandLine.arguments.dropFirst().first ?? "10") ?? 10
let dbPath = NSHomeDirectory() + "/Library/Messages/chat.db"

// --- Load Contacts (best-effort, skip if no permission) ---
let contactStore = CNContactStore()
let cSem = DispatchSemaphore(value: 0)
var cGranted = false
contactStore.requestAccess(for: .contacts) { g, _ in cGranted = g; cSem.signal() }

// Timeout after 5s — avoids hanging if TCC dialog can't be shown (launchd)
if cSem.wait(timeout: .now() + 5) == .timedOut {
    cGranted = false
}

var contactMap: [String: String] = [:]
if cGranted {
    let keys: [CNKeyDescriptor] = [
        CNContactGivenNameKey as CNKeyDescriptor,
        CNContactFamilyNameKey as CNKeyDescriptor,
        CNContactPhoneNumbersKey as CNKeyDescriptor,
        CNContactEmailAddressesKey as CNKeyDescriptor,
    ]
    let req = CNContactFetchRequest(keysToFetch: keys)
    try? contactStore.enumerateContacts(with: req) { c, _ in
        let name = [c.givenName, c.familyName]
            .joined(separator: " ")
            .trimmingCharacters(in: .whitespaces)
        guard !name.isEmpty else { return }
        for phone in c.phoneNumbers {
            let raw = phone.value.stringValue
            let digits = raw.unicodeScalars
                .filter(CharacterSet.decimalDigits.contains)
                .map(String.init).joined()
            contactMap[raw] = name
            contactMap[digits] = name
            if digits.count == 11, digits.hasPrefix("1") {
                contactMap["+1" + String(digits.dropFirst())] = name
            } else if digits.count == 10 {
                contactMap["+1" + digits] = name
            }
        }
        for email in c.emailAddresses {
            contactMap[email.value as String] = name
        }
    }
}

func resolve(_ id: String) -> String {
    if let n = contactMap[id] { return n }
    if id.contains("@") { return id }
    let digits = id.unicodeScalars
        .filter(CharacterSet.decimalDigits.contains)
        .map(String.init).joined()
    if let n = contactMap[digits] { return n }
    let norm: String
    if digits.count == 11, digits.hasPrefix("1") {
        norm = "+1" + String(digits.dropFirst())
    } else if digits.count == 10 {
        norm = "+1" + digits
    } else {
        return id
    }
    if let n = contactMap[norm] { return n }
    return norm
}

// --- Open Messages Database ---
var db: OpaquePointer?
guard sqlite3_open_v2(dbPath, &db, SQLITE_OPEN_READONLY, nil) == SQLITE_OK else {
    fputs("ERROR: Cannot open \(dbPath). Grant Full Disk Access to this binary in System Settings > Privacy & Security > Full Disk Access.\n", stderr)
    exit(1)
}

let appleEpoch: Double = 978307200
let cutoff = (Date().timeIntervalSince1970 - appleEpoch - Double(lookbackHours * 3600)) * 1_000_000_000

let sql = """
    SELECT m.text, COALESCE(h.id, '') as handle_id
    FROM message m
    LEFT JOIN handle h ON m.handle_id = h.ROWID
    WHERE m.date > ?1
      AND m.is_from_me = 0
      AND m.associated_message_type = 0
      AND m.text IS NOT NULL AND m.text != ''
    ORDER BY m.date DESC
    LIMIT 100
    """

var stmt: OpaquePointer?
guard sqlite3_prepare_v2(db, sql, -1, &stmt, nil) == SQLITE_OK else {
    fputs("ERROR: \(String(cString: sqlite3_errmsg(db)))\n", stderr)
    sqlite3_close(db)
    exit(1)
}
sqlite3_bind_double(stmt, 1, cutoff)

var conversations: [String: [String]] = [:]
var order: [String] = []  // preserve first-seen order

while sqlite3_step(stmt) == SQLITE_ROW {
    guard let tCStr = sqlite3_column_text(stmt, 0),
          let hCStr = sqlite3_column_text(stmt, 1) else { continue }

    let text = String(cString: tCStr).trimmingCharacters(in: .whitespacesAndNewlines)
    let handle = String(cString: hCStr)
    guard !handle.isEmpty, !text.isEmpty else { continue }

    let sender = resolve(handle)
    if conversations[sender] == nil { order.append(sender) }
    conversations[sender, default: []].append(text)
}

sqlite3_finalize(stmt)
sqlite3_close(db)

// Build output preserving sender order
var result: [[String: Any]] = []
for sender in order {
    guard let messages = conversations[sender] else { continue }
    result.append([
        "sender": sender,
        "count": messages.count,
        "messages": Array(messages.prefix(10)),
    ])
}

let jsonData = try! JSONSerialization.data(withJSONObject: result, options: [])
print(String(data: jsonData, encoding: .utf8)!)
