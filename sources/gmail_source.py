import email
import email.header
import email.message
import email.utils
import imaplib
import logging
from datetime import datetime, timedelta

from config import GMAIL_ACCOUNTS, GMAIL_LOOKBACK_HOURS, GMAIL_MAX_EMAILS, IMAP_SERVER

log = logging.getLogger(__name__)


def _decode_payload(msg):
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="replace")
        # Fallback to HTML if no plain text
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == "text/html":
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="replace")
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            return payload.decode(charset, errors="replace")
    return ""


def _fetch_account(address, password):
    if not address or not password:
        log.warning("Skipping Gmail account with missing credentials")
        return []

    since = (datetime.now() - timedelta(hours=GMAIL_LOOKBACK_HOURS)).strftime("%d-%b-%Y")
    results = []

    try:
        imap = imaplib.IMAP4_SSL(IMAP_SERVER)
        imap.login(address, password)
        imap.select("INBOX", readonly=True)

        # Search for all recent emails from the lookback period
        status, data = imap.search(None, f'SINCE {since}')
        if status != "OK" or not data[0]:
            imap.logout()
            return []

        msg_ids = data[0].split()[-GMAIL_MAX_EMAILS:]

        for msg_id in msg_ids:
            status, msg_data = imap.fetch(msg_id, "(RFC822)")
            if status != "OK":
                continue

            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)

            from_header = msg.get("From", "")
            subject = msg.get("Subject", "(no subject)")
            # Decode subject if encoded
            decoded_parts = email.header.decode_header(subject)
            subject = "".join(
                part.decode(enc or "utf-8") if isinstance(part, bytes) else part
                for part, enc in decoded_parts
            )
            date_str = msg.get("Date", "")
            body = _decode_payload(msg)[:500]  # Truncate body

            results.append({
                "from": from_header,
                "subject": subject,
                "date": date_str,
                "snippet": body,
                "account": address,
            })

        imap.logout()
    except Exception:
        log.exception("Failed to fetch Gmail for %s", address)

    return results


def fetch_emails() -> str:
    all_emails = []
    for account in GMAIL_ACCOUNTS:
        emails = _fetch_account(account["address"], account["password"])
        all_emails.extend(emails)

    if not all_emails:
        return "## Email\nNo new emails in the last 24 hours."

    # Sort by date (newest first)
    all_emails.sort(key=lambda e: e.get("date", ""), reverse=True)

    lines = []
    for e in all_emails:
        # Skip our own briefing emails
        if "Morning Briefing" in e.get("subject", "") and e.get("account", "") in e.get("from", ""):
            continue
        from_addr = e["from"]
        name, addr = email.utils.parseaddr(from_addr)
        display = name if name else addr
        snippet = e["snippet"][:150].replace("\n", " ").strip()
        lines.append(f"- {e['subject']} — from {display} ({e['account']})\n  {snippet}")

    return "## Email (last 24h)\n" + "\n".join(lines)
