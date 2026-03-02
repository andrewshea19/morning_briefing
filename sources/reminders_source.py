import json
import logging
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from config import REMINDER_LISTS

log = logging.getLogger(__name__)

HELPER = Path(__file__).parent.parent / "helpers" / "reminders_helper.swift"


def fetch_reminders() -> str:
    try:
        result = subprocess.run(
            ["swift", str(HELPER)] + REMINDER_LISTS,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip())

        data = json.loads(result.stdout.strip())
    except Exception:
        log.exception("Failed to fetch reminders")
        return "Reminders unavailable."

    if not data:
        return "## Reminders\nNo incomplete reminders."

    cutoff = datetime.now() + timedelta(days=7)

    parts = []
    for list_name in REMINDER_LISTS:
        items = data.get(list_name, [])
        if not items:
            continue
        lines = []
        for item in items:
            if "due" in item:
                try:
                    due_dt = datetime.strptime(item["due"], "%Y-%m-%d")
                    if due_dt > cutoff:
                        continue
                    display_due = due_dt.strftime("%-m/%-d")
                except ValueError:
                    display_due = item["due"]
                lines.append(f"- {item['name']} (due: {display_due})")
            else:
                lines.append(f"- {item['name']}")
        if lines:
            parts.append(f"### {list_name}\n" + "\n".join(lines))

    if not parts:
        return "## Reminders\nNo reminders due in the next 7 days."

    return "## Reminders\n" + "\n".join(parts)
