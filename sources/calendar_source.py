import logging
from datetime import datetime

from config import CALENDAR_NAMES
from utils import run_osascript

log = logging.getLogger(__name__)


def fetch_events() -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    cal_list = ", ".join(f'"{c}"' for c in CALENDAR_NAMES)

    script = f'''
set targetCalNames to {{{cal_list}}}
set today to current date
set time of today to 0
set tomorrow to today + (1 * days)
set output to ""

tell application "Calendar"
    repeat with cal in calendars
        if name of cal is in targetCalNames then
            set evts to (every event of cal whose start date >= today and start date < tomorrow)
            repeat with e in evts
                set eStart to start date of e
                set eEnd to end date of e
                set eSummary to summary of e
                set eLoc to ""
                try
                    set eLoc to location of e
                end try
                set isAllDay to allday event of e
                if isAllDay then
                    set timeStr to "All day"
                else
                    set timeStr to time string of eStart & " - " & time string of eEnd
                end if
                set output to output & name of cal & " | " & timeStr & " | " & eSummary
                if eLoc is not "" and eLoc is not missing value then
                    set output to output & " @ " & eLoc
                end if
                set output to output & linefeed
            end repeat
        end if
    end repeat
end tell

return output
'''

    try:
        result = run_osascript(script)
    except Exception:
        log.exception("Failed to fetch calendar events")
        return "Calendar events unavailable."

    if not result.strip():
        return f"## Calendar — {today}\nNo events today."

    lines = []
    for line in result.strip().splitlines():
        line = line.strip()
        if line:
            lines.append(f"- {line}")

    return f"## Calendar — {today}\n" + "\n".join(lines)
