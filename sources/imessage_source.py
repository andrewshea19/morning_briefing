import json
import logging
import subprocess
from pathlib import Path

from config import IMESSAGE_LOOKBACK_HOURS

log = logging.getLogger(__name__)

HELPER = Path(__file__).parent.parent / "helpers" / "imessage_helper"


def fetch_messages() -> str:
    if not HELPER.exists():
        log.error("iMessage helper not found at %s — run setup.sh to compile it", HELPER)
        return "iMessage data unavailable (helper not compiled)."

    try:
        result = subprocess.run(
            [str(HELPER), str(IMESSAGE_LOOKBACK_HOURS)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip())

        conversations = json.loads(result.stdout.strip())
    except Exception:
        log.exception("Failed to fetch iMessages")
        return "iMessage data unavailable."

    if not conversations:
        return "## iMessage\nNo new messages in the last 24 hours."

    output_parts = []
    for conv in conversations:
        sender = conv["sender"]
        count = conv["count"]
        msgs = conv["messages"][:10]
        msg_text = "\n".join(f"  - {m[:200]}" for m in msgs)
        label = f"{count} message{'s' if count != 1 else ''}"
        output_parts.append(f"### {sender} ({label})\n{msg_text}")

    return "## iMessage (last 24h)\n" + "\n\n".join(output_parts)
