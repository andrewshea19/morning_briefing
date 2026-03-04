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

        events = json.loads(result.stdout.strip())
    except Exception:
        log.exception("Failed to fetch calendar events")
        return "Calendar events unavailable."

    if not events:
        return f"## Calendar — {today}\nNo events today."

    lines = []
    for e in events:
        time_str = e.get("time", "")
        title = e.get("title", "")
        cal = e.get("calendar", "")
        loc = e.get("location", "")

        line = f"- {cal} | {time_str} | {title}"
        if loc:
            line += f" @ {loc}"
        lines.append(line)

    return f"## Calendar — {today}\n" + "\n".join(lines)
