import logging
import sqlite3
from datetime import datetime, timedelta

from config import CHAT_DB_PATH, IMESSAGE_LOOKBACK_HOURS
from utils import normalize_phone

log = logging.getLogger(__name__)

# Apple's CoreData epoch: 2001-01-01
_APPLE_EPOCH_OFFSET = 978307200

_contact_cache = None


def _load_contacts():
    """Bulk-load all contacts via JXA. Much faster than per-number lookups."""
    global _contact_cache
    if _contact_cache is not None:
        return

    import subprocess
    import json
    import re

    _contact_cache = {}
    try:
        result = subprocess.run(
            ["osascript", "-l", "JavaScript", "-e", '''
var app = Application("Contacts");
var people = app.people;
var firstNames = people.firstName();
var lastNames = people.lastName();
var allPhones = people.phones.value();
var allEmails = people.emails.value();
var result = {};
for (var i = 0; i < firstNames.length; i++) {
    var name = ((firstNames[i] || "") + " " + (lastNames[i] || "")).trim();
    if (!name) continue;
    var phones = allPhones[i] || [];
    for (var j = 0; j < phones.length; j++) {
        if (phones[j]) result[phones[j]] = name;
    }
    var emails = allEmails[i] || [];
    for (var j = 0; j < emails.length; j++) {
        if (emails[j]) result[emails[j]] = name;
    }
}
JSON.stringify(result);
'''],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            raw = json.loads(result.stdout.strip())
            # Normalize all phone keys to +1XXXXXXXXXX
            for key, name in raw.items():
                _contact_cache[key] = name
                digits = re.sub(r"\D", "", key)
                if len(digits) == 11 and digits.startswith("1"):
                    digits = digits[1:]
                if len(digits) == 10:
                    _contact_cache[f"+1{digits}"] = name
                    _contact_cache[digits] = name
            log.info("Loaded %d contact entries", len(_contact_cache))
    except Exception:
        log.warning("Failed to bulk-load contacts", exc_info=True)


def _extract_body_text(attributed_body: bytes) -> str:
    """Extract plain text from NSAttributedString blob in attributedBody column."""
    if not attributed_body:
        return ""
    blob = bytes(attributed_body)
    # The typedstream format stores the text after a length marker.
    # Pattern: the text content appears early in the blob, preceded by a
    # length byte (or two-byte length for longer texts).
    # Look for the text between the header and the NSAttributes section.
    try:
        # Find the start of NSAttributes / NSDictionary marker to know where text ends
        attr_marker = blob.find(b"\x86\x84")
        if attr_marker == -1:
            attr_marker = len(blob)

        # The text is typically at bytes ~2..attr_marker
        # The first few bytes are typedstream header + length
        # Scan for the start of readable text
        # Skip the streamtyped header (usually ends around offset 60-70)
        # but the actual text offset varies. The simplest reliable approach:
        # find the length-prefixed string in the early part of the blob.

        # Approach: skip past "NSMutableAttributedString" / "NSAttributedString" header,
        # then read the length-prefixed UTF-8 string.
        for marker in [b"NSString\x00", b"NSObject\x00"]:
            idx = blob.find(marker)
            if idx != -1:
                start = idx + len(marker)
                # After the class hierarchy, there's a type indicator and length
                # Skip a few control bytes
                pos = start
                while pos < len(blob) and pos < start + 10:
                    b = blob[pos]
                    if b >= 0x20 and b < 0x80:  # printable ASCII start
                        break
                    if b > 0x80:  # length byte for longer texts
                        break
                    pos += 1

                # Read length
                length_byte = blob[pos] if pos < len(blob) else 0
                pos += 1

                if length_byte == 0:
                    continue

                # For texts > 127 chars, length is encoded differently
                if length_byte & 0x80:
                    # Multi-byte length
                    num_bytes = length_byte & 0x7F
                    length = int.from_bytes(blob[pos:pos + num_bytes], 'little')
                    pos += num_bytes
                else:
                    length = length_byte

                if 0 < length < 10000 and pos + length <= len(blob):
                    text = blob[pos:pos + length].decode("utf-8", errors="replace")
                    return text.strip()

        # Fallback: try splitting on \x01+ marker (works for many messages)
        parts = blob.split(b"\x01+")
        if len(parts) > 1:
            remaining = parts[1]
            # First byte(s) after \x01+ are often a length prefix
            if remaining:
                length_byte = remaining[0]
                start = 1
                if length_byte & 0x80:
                    num_bytes = length_byte & 0x7F
                    length = int.from_bytes(remaining[1:1 + num_bytes], 'little')
                    start = 1 + num_bytes
                else:
                    length = length_byte

                if 0 < length < 10000 and start + length <= len(remaining):
                    text = remaining[start:start + length].decode("utf-8", errors="replace")
                    return text.strip()

    except Exception:
        log.debug("Failed to extract attributedBody text", exc_info=True)

    return ""


def _resolve_contact(identifier):
    _load_contacts()

    if identifier in _contact_cache:
        return _contact_cache[identifier]

    if "@" in identifier:
        return identifier

    normalized = normalize_phone(identifier)
    if normalized in _contact_cache:
        return _contact_cache[normalized]

    # Try bare digits
    import re
    digits = re.sub(r"\D", "", identifier)
    if digits in _contact_cache:
        return _contact_cache[digits]

    return normalized


def fetch_messages() -> str:
    if not CHAT_DB_PATH.exists():
        log.warning("iMessage database not found at %s", CHAT_DB_PATH)
        return "iMessage data unavailable."

    cutoff = datetime.now() - timedelta(hours=IMESSAGE_LOOKBACK_HOURS)
    cutoff_ns = int((cutoff.timestamp() - _APPLE_EPOCH_OFFSET) * 1_000_000_000)

    query = """
    SELECT
        m.text,
        m.attributedBody,
        m.date,
        m.is_from_me,
        m.associated_message_type,
        COALESCE(h.id, '') as handle_id
    FROM message m
    LEFT JOIN handle h ON m.handle_id = h.ROWID
    WHERE m.date > ?
      AND m.is_from_me = 0
      AND m.associated_message_type = 0
    ORDER BY m.date DESC
    LIMIT 100
    """

    try:
        conn = sqlite3.connect(f"file:{CHAT_DB_PATH}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(query, (cutoff_ns,)).fetchall()
        conn.close()
    except Exception:
        log.exception("Failed to read iMessage database")
        return "iMessage data unavailable."

    if not rows:
        return "## iMessage\nNo new messages in the last 24 hours."

    # Group messages by sender
    conversations = {}
    for row in rows:
        handle = row["handle_id"]
        if not handle:
            continue

        # Try text column first, fall back to attributedBody
        text = (row["text"] or "").strip()
        if not text and row["attributedBody"]:
            text = _extract_body_text(row["attributedBody"])

        if not text:
            continue

        name = _resolve_contact(handle)
        conversations.setdefault(name, []).append(text)

    if not conversations:
        return "## iMessage\nNo new messages in the last 24 hours."

    output_parts = []
    for sender, messages in conversations.items():
        msgs = messages[:10]
        msg_text = "\n".join(f"  - {m[:200]}" for m in msgs)
        output_parts.append(f"### {sender} ({len(messages)} message{'s' if len(messages) != 1 else ''})\n{msg_text}")

    return "## iMessage (last 24h)\n" + "\n\n".join(output_parts)
