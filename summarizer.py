import logging
from datetime import datetime

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL

log = logging.getLogger(__name__)

SYSTEM_PROMPT_HTML = """You are a personal assistant creating a morning briefing email.
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

SYSTEM_PROMPT_TEXT = """You are a personal assistant creating a morning briefing delivered as an iMessage text.
Transform the raw data into a concise, scannable plain text message.

Format rules:
- Plain text only. No HTML, no markdown.
- Every line item MUST start with "- " (dash space).
- Use blank lines between sections, but NO blank line between a section header and its first item.
- Section headers: just the name in caps on its own line (e.g. "SCHEDULE"), immediately followed by the first "- " item on the next line.
- Keep it SHORT. Target under 1500 characters total. Be ruthlessly concise.
- NO intro, greeting, or sign-off. Jump straight into content.
- If a section has no data or says "unavailable", omit it entirely.
Content rules:
- Present sections in this order: Schedule, Reminders, Messages, Email, News.
- Schedule: list events chronologically. Lead with time: "9:00a - Amazon returns". Include upcoming events with their date: "Thu 3/5 8:00a - MAE Panel".
- Reminders: lead with due date: "3/4 - Mutual of Omaha check in". Flag items due today or overdue with ⚠️.
- Email: one line per important email, max 5. Exclude spam, OTPs, 2FA, transactional emails.
- Messages: one line per conversation summarizing the key point. Note if reply seems needed.
- News: VERY tight. Max 4-5 bullets total. Only the biggest stories of the day — front-page, breaking, or market-moving. Include major business/market news if it's front-page caliber (e.g. crashes, major earnings, big policy shifts, notable corporate moves). Skip routine small deals, minor corporate stories, and lifestyle/feature pieces. Each bullet is one sentence with the key headline linked as a URL in parentheses. Always include the article URL from the raw data so it's tappable in iMessage."""


def summarize(raw_sections, output_format="html"):
    """Summarize raw source data into a briefing.

    Args:
        raw_sections: dict of source name -> raw content
        output_format: "html" for email, "text" for iMessage

    Returns (body, raw_combined).
    """
    today = datetime.now().strftime("%A, %B %-d, %Y")

    combined = f"# Morning Briefing Data — {today}\n\n"
    for source_name, content in raw_sections.items():
        combined += f"\n---\n{content}\n"

    if output_format == "text":
        system_prompt = SYSTEM_PROMPT_TEXT
        user_msg = f"Here is today's raw data. Create the plain text briefing.\n\n{combined}"
        max_tokens = 1024
    else:
        system_prompt = SYSTEM_PROMPT_HTML
        user_msg = f"Here is today's raw data. Create the HTML briefing email.\n\n{combined}"
        max_tokens = 4096

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": user_msg,
                }
            ],
        )
        body = response.content[0].text

        if output_format == "html":
            # If Claude wrapped it in ```html fences, strip them
            if body.startswith("```html"):
                body = body[7:]
            if body.startswith("```"):
                body = body[3:]
            if body.endswith("```"):
                body = body[:-3]

        body = body.strip()
        return body, combined

    except Exception:
        log.exception("Claude API summarization failed, using plain-text fallback")
        if output_format == "text":
            return combined, combined
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
