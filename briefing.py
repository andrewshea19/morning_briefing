#!/usr/bin/env python3
"""Morning Briefing — Daily email digest orchestrator."""

import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import setup_logging
from summarizer import summarize
from emailer import send_briefing

from sources.gmail_source import fetch_emails
from sources.calendar_source import fetch_events
from sources.reminders_source import fetch_reminders
from sources.imessage_source import fetch_messages
from sources.news_source import fetch_headlines

log = setup_logging()

SOURCES = {
    "Schedule": fetch_events,
    "Reminders": fetch_reminders,
    "Email": fetch_emails,
    "Messages": fetch_messages,
    "News": fetch_headlines,
}

# Presentation order for Claude
SECTION_ORDER = ["Schedule", "Reminders", "Messages", "Email", "News"]


def gather_sources():
    results = {}

    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(fn): name for name, fn in SOURCES.items()}

        try:
            for future in as_completed(futures, timeout=90):
                name = futures[future]
                try:
                    results[name] = future.result(timeout=60)
                    log.info("✓ %s fetched", name)
                except Exception:
                    log.exception("✗ %s failed", name)
                    results[name] = f"{name} data unavailable."
        except TimeoutError:
            log.error("gather_sources timed out after 90s")

    # Mark any sources that didn't complete in time
    for name in SOURCES:
        if name not in results:
            log.error("✗ %s timed out", name)
            results[name] = f"{name} data unavailable."

    # Return in presentation order
    return {k: results[k] for k in SECTION_ORDER if k in results}


def main():
    log.info("Starting morning briefing")

    # 1. Gather all sources in parallel
    raw = gather_sources()

    # 2. Summarize with Claude
    log.info("Summarizing with Claude...")
    html_body, plain_text = summarize(raw)

    # 3. Send email
    log.info("Sending briefing email...")
    success = send_briefing(html_body, fallback_text=plain_text)

    if success:
        log.info("Briefing complete!")
    else:
        log.error("Briefing failed to send")
        sys.exit(1)


if __name__ == "__main__":
    main()
