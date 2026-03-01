import logging
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import BRIEFING_RECIPIENT, SMTP_ADDRESS, SMTP_PASSWORD, SMTP_PORT, SMTP_SERVER

log = logging.getLogger(__name__)


def send_briefing(html_body, fallback_text=None):
    today = datetime.now().strftime("%A, %B %-d")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Morning Briefing — {today}"
    msg["From"] = SMTP_ADDRESS
    msg["To"] = BRIEFING_RECIPIENT

    if fallback_text:
        msg.attach(MIMEText(fallback_text, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_ADDRESS, SMTP_PASSWORD)
            server.send_message(msg)
        log.info("Briefing sent to %s", BRIEFING_RECIPIENT)
        return True
    except Exception:
        log.exception("Failed to send briefing email")
        return False
