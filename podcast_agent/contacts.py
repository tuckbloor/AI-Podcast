"""Find clearly published contact emails on a podcast's own website."""

import re
from urllib.parse import unquote, urljoin, urlsplit

from bs4 import BeautifulSoup

from .models import Podcast
from .network import FetchError, safe_fetch

EMAIL_RE = re.compile(r"\b[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}\b", re.I)
CONTACT_TERMS = ("contact", "get-in-touch", "get_in_touch", "about", "guest", "collaborat", "booking", "pitch", "advertis", "sponsor", "work-with", "team", "press")
EXCLUDED_PREFIXES = ("noreply", "no-reply", "donotreply", "privacy", "dpo", "abuse", "webmaster", "admin")
PREFERRED_PREFIXES = ("podcast", "contact", "hello", "info", "booking", "bookings", "guests", "guest", "editor", "team")


def _decode_cloudflare_email(encoded: str) -> str:
    """Decode Cloudflare's public email obfuscation when it appears on a page."""
    try:
        data = bytes.fromhex(encoded)
        if len(data) < 4 or len(data) > 400:
            return ""
        decoded = bytes(c ^ data[0] for c in data[1:]).decode("utf-8")
        return decoded if EMAIL_RE.fullmatch(decoded) else ""
    except (ValueError, UnicodeError):
        return ""


def find_addresses(html: str) -> list[str]:
    """Collect exact public email strings; never infer likely address formats."""
    soup = BeautifulSoup(html, "html.parser")
    found: list[str] = []
    for anchor in soup.select('a[href^="mailto:"]'):
        value = unquote(anchor.get("href", "")[7:].split("?", 1)[0]).strip()
        found.extend(EMAIL_RE.findall(value))
    for tag in soup.select("[data-cfemail]"):
        decoded = _decode_cloudflare_email(str(tag.get("data-cfemail") or ""))
        if decoded:
            found.append(decoded)
    for anchor in soup.select('a[href*="/cdn-cgi/l/email-protection#"]'):
        encoded = str(anchor.get("href", "")).split("#", 1)[-1]
        decoded = _decode_cloudflare_email(encoded)
        if decoded:
            found.append(decoded)
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    found.extend(EMAIL_RE.findall(soup.get_text(" ", strip=True)))
    seen: set[str] = set()
    usable = []
    for email in found:
        email = email.lower().strip(" .,:;()[]")
        if email in seen or email.partition("@")[0].startswith(EXCLUDED_PREFIXES):
            continue
        if email.endswith((".png", ".jpg", ".webp")):
            continue
        seen.add(email)
        usable.append(email)
    return usable


def contact_links(html: str, base_url: str) -> list[str]:
    """Find up to four likely host contact pages on the same publisher site."""
    soup = BeautifulSoup(html, "html.parser")
    host = (urlsplit(base_url).hostname or "").removeprefix("www.")
    ranked: list[tuple[int, str]] = []
    seen = {base_url.rstrip("/")}
    for anchor in soup.select("a[href]"):
        href = str(anchor.get("href") or "").strip()
        candidate = urljoin(base_url, href)
        parts = urlsplit(candidate)
        if parts.scheme not in {"https", "http"} or (parts.hostname or "").removeprefix("www.") != host:
            continue
        candidate = candidate.split("#", 1)[0]
        if candidate.rstrip("/") in seen:
            continue
        label = (anchor.get_text(" ", strip=True) + " " + parts.path).lower()
        if any(term in label for term in CONTACT_TERMS):
            seen.add(candidate.rstrip("/"))
            priority = 0 if "contact" in label or "get-in-touch" in label else 1
            ranked.append((priority, candidate))
    return [value for _, value in sorted(ranked, key=lambda x: x[0])[:4]]


def find_public_contact(podcast: Podcast) -> None:
    """Search the official site and up to four contact/about/guest pages.

    A located address is *not* equivalent to marketing consent. The CSV
    retains the page URL for manual verification before any outreach.
    """
    if not podcast.website:
        return
    try:
        home = safe_fetch(podcast.website, max_bytes=800_000)
    except FetchError as exc:
        podcast.research_notes += f" | Website unavailable: {exc}"
        return
    if "pdf" in home.content_type:
        return

    home_html = home.body.decode("utf-8", errors="replace")
    page_urls = contact_links(home_html, home.url)
    # A sourced contact form is useful even when no public email exists.
    if page_urls:
        podcast.contact_page = page_urls[0]
    pages = []
    for target in page_urls:
        try:
            page = safe_fetch(target, max_bytes=800_000)
            if "html" in page.content_type:
                pages.append(page)
        except FetchError as exc:
            podcast.research_notes += f" | Contact page inaccessible ({urlsplit(target).path[:45]}): {type(exc).__name__}"
    pages.append(home)
    # Only factual text directly fetched from the official website is allowed
    # to add location clues. This is still not automatic UK certification.
    for page in pages:
        soup = BeautifulSoup(page.body.decode("utf-8", errors="replace"), "html.parser")
        for tag in soup(["script", "style", "nav", "noscript", "svg"]):
            tag.decompose()
        podcast.location_page_text += " " + soup.get_text(" ", strip=True)[:3500]
    podcast.location_page_text = podcast.location_page_text[:8000]

    candidates: list[tuple[int, str, str]] = []
    for page in pages:
        for email in find_addresses(page.body.decode("utf-8", errors="replace")):
            local = email.partition("@")[0]
            preferred = 0 if local.startswith(PREFERRED_PREFIXES) else 1
            # A source directly labelled contact/guest gets higher priority.
            source_priority = 0 if any(term in urlsplit(page.url).path.lower() for term in ("contact", "guest", "booking", "about")) else 1
            candidates.append((preferred * 2 + source_priority, email, page.url))
    if candidates:
        candidates.sort(key=lambda e: e[0])
        _, podcast.email, podcast.contact_source = candidates[0]
