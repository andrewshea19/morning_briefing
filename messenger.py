import logging
import subprocess
from pathlib import Path

from config import IMESSAGE_RECIPIENT

log = logging.getLogger(__name__)

HELPER = Path(__file__).parent / "helpers" / "send_imessage"


def send_briefing_text(text):
    if not HELPER.exists():
        log.error("send_imessage helper not found at %s — run setup.sh to compile it", HELPER)
        return False

    try:
        result = subprocess.run(
            [str(HELPER), IMESSAGE_RECIPIENT],
            input=text,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip())
        log.info("Briefing sent via iMessage to %s", IMESSAGE_RECIPIENT)
        return True
    except Exception:
        log.exception("Failed to send iMessage briefing")
        return False
