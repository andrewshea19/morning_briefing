import json
import logging
import subprocess
from datetime import datetime, timedelta

from config import REMINDER_LISTS

log = logging.getLogger(__name__)


def fetch_reminders() -> str:
    list_names_json = json.dumps(REMINDER_LISTS)

    # Use bulk property access (.name(), .completed(), .dueDate()) which is
    # orders of magnitude faster than per-item access or .whose() filters.
    jxa_script = f'''
var app = Application("Reminders");
var targetNames = {list_names_json};
var results = {{}};

for (var i = 0; i < targetNames.length; i++) {{
    var listName = targetNames[i];
    try {{
        var rList = app.lists.byName(listName);
        var names = rList.reminders.name();
        var completed = rList.reminders.completed();
        var dueDates = [];
        try {{ dueDates = rList.reminders.dueDate(); }} catch(e) {{}}

        var items = [];
        for (var j = 0; j < names.length; j++) {{
            if (!completed[j]) {{
                var item = {{name: names[j]}};
                if (dueDates[j]) {{
                    item.due = dueDates[j].toISOString();
                }}
                items.push(item);
            }}
        }}
        if (items.length > 0) {{
            results[listName] = items;
        }}
    }} catch(e) {{}}
}}

JSON.stringify(results);
'''

    try:
        result = subprocess.run(
            ["osascript", "-l", "JavaScript", "-e", jxa_script],
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
            # Filter: include items with no due date, or due within 7 days
            if "due" in item:
                try:
                    due_dt = datetime.fromisoformat(item["due"].replace("Z", "+00:00"))
                    if due_dt.replace(tzinfo=None) > cutoff:
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
