"""Podcast discovery using the public Apple Podcasts Search API."""

import requests

from .models import Podcast

APPLE_SEARCH = "https://itunes.apple.com/search"


class DiscoveryError(Exception):
    pass


def search_apple(term: str, *, country: str = "gb", limit: int = 18) -> list[Podcast]:
    """Search for podcast shows, not individual episodes."""
    try:
        response = requests.get(
            APPLE_SEARCH,
            params={"term": term, "country": country, "media": "podcast", "entity": "podcast", "limit": limit},
            headers={"User-Agent": "PodcastOutreachResearch/0.1"},
            timeout=(6, 20),
        )
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise DiscoveryError(f"Apple Podcasts search failed: {exc}") from exc

    podcasts = []
    for item in data.get("results", []):
        if not isinstance(item, dict):
            continue
        feed = item.get("feedUrl") or ""
        title = item.get("collectionName") or ""
        if not feed or not title:
            continue
        podcasts.append(
            Podcast(
                title=str(title),
                feed_url=str(feed),
                apple_url=str(item.get("collectionViewUrl") or ""),
                description=str(item.get("artistName") or ""),
            )
        )
    return podcasts


def unique_podcasts(groups: list[list[Podcast]], *, limit: int) -> list[Podcast]:
    """Interleave result groups so each search term contributes candidates."""
    found: list[Podcast] = []
    seen: set[str] = set()
    for i in range(max((len(g) for g in groups), default=0)):
        for group in groups:
            if i >= len(group):
                continue
            podcast = group[i]
            key = podcast.feed_url.lower().strip().rstrip("/")
            if key in seen:
                continue
            seen.add(key)
            found.append(podcast)
            if len(found) >= limit:
                return found
    return found


# Optional independent podcast directory. Users supply their own credentials;
# the API secret is never transmitted or included in logging.
def search_podcast_index(term: str, *, limit: int = 25,
                         api_key: str = "", api_secret: str = "") -> list[Podcast]:
    """Look up podcast feeds on Podcast Index (requires a free API key/secret)."""
    import hashlib
    import os
    import time

    key = api_key or os.getenv("PODCAST_INDEX_API_KEY", "")
    secret = api_secret or os.getenv("PODCAST_INDEX_API_SECRET", "")
    if not key or not secret:
        return []
    stamp = str(int(time.time()))
    auth = hashlib.sha1((key + secret + stamp).encode("utf-8")).hexdigest()
    try:
        response = requests.get(
            "https://api.podcastindex.org/api/1.0/search/byterm",
            params={"q": term[:110], "max": max(1, min(50, limit))},
            headers={"User-Agent": "PodcastOutreachAI/1.1", "X-Auth-Key": key,
                     "X-Auth-Date": stamp, "Authorization": auth},
            timeout=(5, 16),
        )
        response.raise_for_status()
        result = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise DiscoveryError(f"Podcast Index unavailable: {type(exc).__name__}: {str(exc)[:100]}") from exc
    podcasts = []
    for entry in result.get("feeds", []):
        if not isinstance(entry, dict):
            continue
        url = str(entry.get("url") or "")
        title = str(entry.get("title") or "")
        if not title or not url.startswith(("https://", "http://")):
            continue
        podcasts.append(Podcast(
            title=title[:240], feed_url=url,
            apple_url="",
            description=str(entry.get("description") or "")[:1800],
            website=str(entry.get("link") or ""),
            discovery_source="Podcast Index",
        ))
    return podcasts


def search_open_web(term: str, *, limit: int = 5) -> list[Podcast]:
    """Best-effort public web discovery, using a search RSS feed and page feed links.

    This is intentionally conservative: web search previews alone do NOT create
    podcast records. An original webpage must expose a genuine podcast RSS URL.
    If Bing RSS is blocked, callers fall back to the two directories.
    """
    from urllib.parse import urlencode, urljoin, urlsplit
    from xml.etree import ElementTree as ET
    from bs4 import BeautifulSoup
    from .network import safe_fetch, FetchError

    search_url = "https://www.bing.com/search?" + urlencode({
        "q": term[:110] + " podcast official RSS", "format": "rss", "count": max(3, min(8, limit * 2))})
    try:
        search_data = safe_fetch(search_url, max_bytes=250_000)
        root = ET.fromstring(search_data.body)
    except (FetchError, ET.ParseError) as exc:
        raise DiscoveryError(f"Web discovery unavailable: {type(exc).__name__}") from exc
    shows = []
    for item in root.findall("./channel/item")[:max(4, limit * 2)]:
        link = item.findtext("link") or ""
        if not link.startswith(("https://", "http://")):
            continue
        try:
            page = safe_fetch(link, max_bytes=450_000)
        except FetchError:
            continue
        if "html" not in page.content_type:
            continue
        soup = BeautifulSoup(page.body, "html.parser")
        for tag in soup.select('link[rel="alternate"]'):
            if not any(x in str(tag.get("type", "")).lower() for x in ("rss", "atom", "xml")):
                continue
            feed = urljoin(page.url, str(tag.get("href", "")))
            if urlsplit(feed).scheme not in ("https", "http"):
                continue
            title = (soup.title.get_text(" ", strip=True) if soup.title else item.findtext("title")) or "Unknown show"
            shows.append(Podcast(title=title[:240], feed_url=feed, website=page.url,
                                 description=(soup.find("meta", attrs={"name": "description"}) or {}).get("content", "")[:1200],
                                 discovery_source="Public web (RSS verified)"))
            break
        if len(shows) >= limit:
            break
    return shows
