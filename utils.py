import logging
import re
import subprocess
from datetime import datetime

from config import LOG_DIR


def setup_logging():
    log_file = LOG_DIR / f"briefing_{datetime.now():%Y%m%d_%H%M%S}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(),
        ],
    )
    return logging.getLogger("briefing")


def run_osascript(script: str) -> str:
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(f"osascript failed: {result.stderr.strip()}")
    return result.stdout.strip()


def normalize_phone(number: str) -> str:
    digits = re.sub(r"\D", "", number)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) == 10:
        return f"+1{digits}"
    return number
