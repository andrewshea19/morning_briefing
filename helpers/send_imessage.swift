// Sends an iMessage to a recipient.
// Usage: send_imessage <recipient_phone_or_email>
// Message body is read from stdin.
// Requires Automation permission for Messages.app.

import Foundation

guard CommandLine.arguments.count >= 2 else {
    fputs("Usage: send_imessage <recipient>\nMessage body is read from stdin.\n", stderr)
    exit(1)
}

let recipient = CommandLine.arguments[1]
let messageData = FileHandle.standardInput.readDataToEndOfFile()
guard let message = String(data: messageData, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines),
      !message.isEmpty else {
    fputs("ERROR: No message provided on stdin.\n", stderr)
    exit(1)
}

// Escape for AppleScript string literal
let escaped = message
    .replacingOccurrences(of: "\\", with: "\\\\")
    .replacingOccurrences(of: "\"", with: "\\\"")

let source = """
tell application "Messages"
    set targetService to 1st account whose service type = iMessage
    set targetBuddy to participant "\(recipient)" of targetService
    send "\(escaped)" to targetBuddy
end tell
"""

var error: NSDictionary?
guard let script = NSAppleScript(source: source) else {
    fputs("ERROR: Failed to create AppleScript.\n", stderr)
    exit(1)
}

script.executeAndReturnError(&error)

if let err = error {
    fputs("ERROR: \(err[NSAppleScript.errorMessage] ?? err)\n", stderr)
    exit(1)
}
