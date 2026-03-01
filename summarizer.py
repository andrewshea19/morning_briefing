import logging
from datetime import datetime

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a personal assistant creating a morning briefing email.
Transform the raw data below into a compact, scannable HTML email digest.

Layout rules:
- COMPACT: minimize whitespace, padding, and margins. Use tight line-height (1.3). Small font (13px body, 11px secondary). No large gaps between sections. The goal is minimal scrolling.
- Use a single-column layout, max-width 600px, with inline CSS only.
- Section headers: plain text, not bold, not colored. Use a thin #ddd bottom border to separate sections. Keep margins tight (8px above, 4px below).
- Do NOT bold or color any text anywhere in the email. Plain black/dark gray text only. No colored backgrounds, no highlights.
- NO intro sentence, greeting, or sign-off. Jump straight into the first section.
- If a section has no data or says "unavailable", omit it entirely.

Content rules:
- LINKS: Make everything clickable where possible.
  - News headlines MUST be hyperlinked to their article URLs (the URLs are in the raw data).
  - Calendar events: link the event title to the location (Google Maps search URL) if a location is provided.
  - Reminders: just display inline, no links needed.
  - iMessage: no links needed.
  - Gmail: no links needed.
- Present sections in this order: Schedule, Reminders, Messages, Email, News.
- Schedule and Reminders MUST use identical formatting: plain bulleted lists, same font size, same style. Consider combining them under one header if it reads better.
- Schedule: list events chronologically. Always lead with time: "9:00a — Amazon returns", "12:00p — Rental tour @ location". Never put the description before the time.
- Reminders: always lead with the due date: "2/28 — Sell clothes", "3/4 — Mutual of Omaha check in". Items without a due date can just be listed plainly. Flag items due today or tomorrow.
- Email: summarize briefly, one bullet per important email. ALWAYS exclude verification codes, OTPs, 2FA codes, security alerts, login notifications, password resets, and automated transactional emails.
- Messages: use a bulleted list. One bullet per conversation, summarized in one sentence. Note anything that seems to need a reply. ALWAYS exclude verification codes, OTPs, 2FA messages, and automated short-code messages.
- News: Include major news, breaking news, front-page stories, and large exclusives/investigations. Slightly prefer WSJ sources over NYT when covering the same story. Ignore quizzes, lifestyle, profiles, fluff, and minor feature stories. For Markets/Business, include genuinely market-moving news (major earnings, crashes, policy changes, large-scale economic shifts, and major corporate news like spin-offs or strategic moves by notable companies like Trump Media). Skip routine small deals and minor corporate stories. Group into 3-5 topic categories (e.g. "Middle East", "Markets", "Tech"). Each category on its own line/bullet. For each category write a 1-2 sentence summary with key linked headlines woven inline. Do NOT list every headline — curate for significance.
- The email must render well in Gmail web and mobile."""


def summarize(raw_sections):
    """Summarize raw source data into an HTML briefing.

    Returns (html_body, plain_text_fallback).
    """
    today = datetime.now().strftime("%A, %B %-d, %Y")

    combined = f"# Morning Briefing Data — {today}\n\n"
    for source_name, content in raw_sections.items():
        combined += f"\n---\n{content}\n"

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"Here is today's raw data. Create the HTML briefing email.\n\n{combined}",
                }
            ],
        )
        html = response.content[0].text

        # If Claude wrapped it in ```html fences, strip them
        if html.startswith("```html"):
            html = html[7:]
        if html.startswith("```"):
            html = html[3:]
        if html.endswith("```"):
            html = html[:-3]
        html = html.strip()

        return html, combined

    except Exception:
        log.exception("Claude API summarization failed, using plain-text fallback")
        return _plain_fallback(raw_sections, today), combined


def _plain_fallback(sections, today):
    body = f"<html><body style='font-family: -apple-system, sans-serif; max-width: 600px; margin: auto; padding: 20px;'>"
    body += f"<h1 style='color: #333;'>Morning Briefing — {today}</h1>"
    body += "<p style='color: #999;'><em>Claude summarization unavailable. Raw data below.</em></p><hr>"

    for name, content in sections.items():
        body += f"<h2 style='color: #555;'>{name}</h2>"
        body += f"<pre style='white-space: pre-wrap; font-size: 13px;'>{content}</pre><hr>"

    body += "</body></html>"
    return body
