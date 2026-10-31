"""Read bounded RSS/Atom editorial metadata without harvesting RSS owner emails."""

import xml.etree.ElementTree as ET
from datetime import timezone
from email.utils import parsedate_to_datetime

from bs4 import BeautifulSoup

from .models import Podcast
from .network import FetchError, safe_fetch

ITUNES = "{http://www.itunes.com/dtds/podcast-1.0.dtd}"
ATOM = "{http://www.w3.org/2005/Atom}"


def _clean(value: str | None, max_chars: int) -> str:
    return BeautifulSoup(value or "", "html.parser").get_text(" ", strip=True)[:max_chars]


def _first(*values: str | None) -> str:
    return next((value.strip() for value in values if value and value.strip()), "")


def enrich_from_feed(podcast: Podcast) -> None:
    """Update a show from RSS/Atom. Missing or invalid feeds don't stop research."""
    try:
        downloaded = safe_fetch(podcast.feed_url, max_bytes=12_000_000)
        root = ET.fromstring(downloaded.body)
        channel = root.find("channel")
        if channel is not None:  # RSS 2.0
            podcast.title = _first(channel.findtext("title"), podcast.title)[:240]
            description = _first(
                channel.findtext("description"),
                channel.findtext(ITUNES + "summary"),
                channel.findtext(ITUNES + "subtitle"),
            )
            podcast.description = _clean(description or podcast.description, 1800)
            website = _first(channel.findtext("link"))
            items = channel.findall("item")[:12]
            podcast.episodes = [_clean(item.findtext("title"), 160)
                                for item in items[:5] if item.findtext("title")]
            dates = []
            for item in items:
                raw_date = item.findtext("pubDate")
                if not raw_date:
                    continue
                try:
                    parsed = parsedate_to_datetime(raw_date)
                    if parsed.tzinfo is None:
                        parsed = parsed.replace(tzinfo=timezone.utc)
                    dates.append(parsed)
                except (TypeError, ValueError, OverflowError):
                    continue
            if dates:
                podcast.latest_episode_date = max(dates).date().isoformat()
        elif root.tag in (ATOM + "feed", "feed"):  # Atom 1.0
            podcast.title = _first(root.findtext(ATOM + "title"), podcast.title)[:240]
            podcast.description = _clean(
                _first(root.findtext(ATOM + "subtitle"), podcast.description), 1800
            )
            website = ""
            for link in root.findall(ATOM + "link"):
                if link.attrib.get("rel", "alternate") == "alternate":
                    website = link.attrib.get("href", "")
                    break
            entries = root.findall(ATOM + "entry")[:12]
            podcast.episodes = [_clean(entry.findtext(ATOM + "title"), 160)
                                for entry in entries[:5]]
            dates = []
            for entry in entries:
                raw_date = _first(entry.findtext(ATOM + "updated"), entry.findtext(ATOM + "published"))
                if raw_date:
                    try:
                        from datetime import datetime
                        dates.append(datetime.fromisoformat(raw_date.replace("Z", "+00:00")))
                    except ValueError:
                        continue
            if dates:
                podcast.latest_episode_date = max(dates).date().isoformat()
        else:
            podcast.research_notes = "RSS feed contained no usable show information"
            return

        if website.startswith(("https://", "http://")):
            podcast.website = website
    except (FetchError, ET.ParseError, ValueError, TypeError) as exc:
        podcast.research_notes = f"RSS not available: {exc}"
