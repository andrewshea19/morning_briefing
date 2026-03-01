import logging
import urllib.request
import xml.etree.ElementTree as ET

from config import RSS_FEEDS, RSS_HEADLINES_PER_FEED

log = logging.getLogger(__name__)


def fetch_headlines() -> str:
    all_headlines = []

    for feed_name, feed_url in RSS_FEEDS:
        try:
            req = urllib.request.Request(
                feed_url,
                headers={"User-Agent": "MorningBriefing/1.0"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read()
            root = ET.fromstring(data)

            items = root.findall(".//item")[:RSS_HEADLINES_PER_FEED]
            headlines = []
            for item in items:
                title = item.findtext("title", "").strip()
                link = item.findtext("link", "").strip()
                if title:
                    headlines.append(f"- {title}")
                    if link:
                        headlines[-1] += f" ({link})"

            if headlines:
                all_headlines.append(f"\n### {feed_name}\n" + "\n".join(headlines))
            else:
                log.warning("No headlines from %s", feed_name)

        except Exception:
            log.exception("Failed to fetch %s", feed_name)

    if not all_headlines:
        return "No news headlines available."

    return "## News Headlines\n" + "\n".join(all_headlines)
