import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path

from config import CALENDAR_NAMES

log = logging.getLogger(__name__)

HELPER = Path(__file__).parent.parent / "helpers" / "calendar_helper"


def fetch_events() -> str:
    today = datetime.now().strftime("%Y-%m-%d")

    try:
        result = subprocess.run(
            [str(HELPER)] + CALENDAR_NAMES,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip())

        data = json.loads(result.stdout.strip())
    except Exception:
        log.exception("Failed to fetch calendar events")
        return "Calendar events unavailable."

    today_events = data.get("today", [])
    upcoming = data.get("upcoming", [])

    parts = [f"## Calendar — {today}"]

    if today_events:
        for e in today_events:
            line = f"- {e['calendar']} | {e['time']} | {e['title']}"
            if e.get("location"):
                line += f" @ {e['location']}"
            parts.append(line)
    else:
        parts.append("No events today.")

    if upcoming:
        parts.append("\n### Upcoming")
        for e in upcoming:
            line = f"- {e.get('date', '')} | {e['time']} | {e['title']}"
            if e.get("location"):
                line += f" @ {e['location']}"
            parts.append(line)

    return "\n".join(parts)
