import logging
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

from config import RSS_FEEDS, RSS_HEADLINES_PER_FEED

log = logging.getLogger(__name__)


def fetch_headlines() -> str:
    all_headlines = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

    for feed_name, feed_url in RSS_FEEDS:
        try:
            req = urllib.request.Request(
                feed_url,
                headers={"User-Agent": "MorningBriefing/1.0"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read()
            root = ET.fromstring(data)

            items = root.findall(".//item")
            headlines = []
            for item in items:
                title = item.findtext("title", "").strip()
                link = item.findtext("link", "").strip()
                pub_date_str = item.findtext("pubDate", "").strip()

                # Only include articles published in the last 24 hours
                if pub_date_str:
                    try:
                        pub_date = parsedate_to_datetime(pub_date_str)
                        if pub_date < cutoff:
                            continue
                    except (ValueError, TypeError):
                        pass  # Include items with unparseable dates

                if title:
                    entry = f"- {title}"
                    if link:
                        entry += f" ({link})"
                    headlines.append(entry)

                if len(headlines) >= RSS_HEADLINES_PER_FEED:
                    break

            if headlines:
                all_headlines.append(f"\n### {feed_name}\n" + "\n".join(headlines))
            else:
                log.warning("No recent headlines from %s", feed_name)

        except Exception:
            log.exception("Failed to fetch %s", feed_name)

    if not all_headlines:
        return "No news headlines available."

    return "## News Headlines\n" + "\n".join(all_headlines)
