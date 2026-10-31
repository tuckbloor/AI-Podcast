"""Bounded, public-Internet-only downloads to reduce accidental local-network access."""

from dataclasses import dataclass
import ipaddress
import socket
from urllib.parse import urljoin, urlsplit

import requests

USER_AGENT = "PodcastOutreachResearch/0.1 (contact discovery; human reviewed)"


class FetchError(Exception):
    """A remote URL could not be safely or successfully fetched."""


@dataclass(frozen=True)
class FetchedContent:
    body: bytes
    url: str
    content_type: str


def validate_public_url(url: str) -> None:
    """Reject file:, localhost, IP literals, and hosts resolving to nonpublic IPs.

    This is a useful local-machine safeguard, not a substitute for a
    fully isolated network sandbox when deploying on a server.
    """
    parts = urlsplit(url)
    if parts.scheme not in {"https", "http"} or not parts.hostname:
        raise FetchError("Only public HTTP(S) websites are allowed")
    if parts.username or parts.password:
        raise FetchError("URLs with embedded credentials are not allowed")
    host = parts.hostname.rstrip(".").lower()
    if host == "localhost" or host.endswith((".local", ".internal", ".localhost")):
        raise FetchError("Local and internal websites are not allowed")
    try:
        port = parts.port
    except ValueError as exc:
        raise FetchError("Invalid URL port") from exc
    if port not in (None, 80, 443):
        raise FetchError("Only standard website ports are allowed")
    try:
        addresses = socket.getaddrinfo(host, port or (443 if parts.scheme == "https" else 80), type=socket.SOCK_STREAM)
    except (OSError, UnicodeError) as exc:
        raise FetchError("Website hostname could not be resolved") from exc
    if not addresses:
        raise FetchError("Website hostname could not be resolved")
    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if not ip.is_global:
            raise FetchError("Private or nonpublic network address blocked")


def safe_fetch(url: str, *, max_bytes: int = 1_500_000, redirects: int = 4) -> FetchedContent:
    """Download a reasonably sized page/feed, validating every redirect target."""
    current = url
    for _ in range(redirects + 1):
        validate_public_url(current)
        try:
            with requests.get(
                current,
                timeout=(6, 16),
                headers={"User-Agent": USER_AGENT, "Accept": "text/html, application/rss+xml, application/xml, */*"},
                allow_redirects=False,
                stream=True,
                # Avoid following HTTP(S)_PROXY to internal destinations set in environment.
                proxies={"http": "", "https": ""},
            ) as response:
                if response.status_code in {301, 302, 303, 307, 308}:
                    location = response.headers.get("Location", "")
                    if not location:
                        raise FetchError("Redirect did not include a destination")
                    current = urljoin(current, location)
                    continue
                response.raise_for_status()
                data = bytearray()
                for chunk in response.iter_content(32768):
                    data.extend(chunk)
                    if len(data) > max_bytes:
                        raise FetchError("Page exceeded download size limit")
                return FetchedContent(
                    body=bytes(data),
                    url=current,
                    content_type=response.headers.get("Content-Type", "").lower(),
                )
        except requests.RequestException as exc:
            raise FetchError(f"HTTP request failed: {exc}") from exc
    raise FetchError("Too many redirects")
