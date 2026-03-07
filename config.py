import os
from pathlib import Path

BASE_DIR = Path(__file__).parent

# Load .env file
_env_path = BASE_DIR / ".env"
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())

# Anthropic
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = "claude-sonnet-4-20250514"

# Gmail accounts
GMAIL_ACCOUNTS = [
    {
        "address": os.environ.get("GMAIL1_ADDRESS", ""),
        "password": os.environ.get("GMAIL1_APP_PASSWORD", ""),
    },
    {
        "address": os.environ.get("GMAIL2_ADDRESS", ""),
        "password": os.environ.get("GMAIL2_APP_PASSWORD", ""),
    },
]

# SMTP (send from account 1)
SMTP_ADDRESS = GMAIL_ACCOUNTS[0]["address"]
SMTP_PASSWORD = GMAIL_ACCOUNTS[0]["password"]
BRIEFING_RECIPIENT = os.environ.get("BRIEFING_RECIPIENT", "andrewshea19@gmail.com")

# iMessage delivery
IMESSAGE_RECIPIENT = os.environ.get("IMESSAGE_RECIPIENT", "+13304217089")
BRIEFING_DELIVERY = os.environ.get("BRIEFING_DELIVERY", "imessage")  # "imessage" or "email"

# IMAP/SMTP servers
IMAP_SERVER = "imap.gmail.com"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# Gmail fetch limits
GMAIL_MAX_EMAILS = 20
GMAIL_LOOKBACK_HOURS = 10

# Apple Calendar — calendars to include
CALENDAR_NAMES = [
    "Calendar",
    "K&A",
    "andrewshea19@gmail.com",
    "US Holidays",
    "Holidays in United States",
    "Birthdays",
]

# Apple Reminders — lists to include
REMINDER_LISTS = [
    "To Do",
]

# iMessage
CHAT_DB_PATH = Path.home() / "Library" / "Messages" / "chat.db"
IMESSAGE_LOOKBACK_HOURS = 10

# News RSS feeds
RSS_FEEDS = [
    ("NYT Homepage", "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml"),
    ("WSJ World", "https://feeds.content.dowjones.io/public/rss/RSSWorldNews"),
    ("WSJ Business", "https://feeds.content.dowjones.io/public/rss/WSJcomUSBusiness"),
]
RSS_HEADLINES_PER_FEED = 10

# Logging
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
