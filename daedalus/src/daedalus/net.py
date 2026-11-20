"""Outbound URL checks for operator-configured fetchers."""

from urllib.parse import urlparse

__all__ = ["UrlNotAllowed", "assert_allowed_url"]

_ALLOWED_HOSTS = frozenset({
    "api.lens.org",
    "api.openalex.org",
    "connect.patsnap.com",
    "ops.epo.org",
    "patentscope.wipo.int",
    "search.patentsview.org",
})


class UrlNotAllowed(ValueError):
    """Raised when a fetcher URL is not on the host allowlist."""


def assert_allowed_url(url: str) -> None:
    """Require https and a host the prototype is willing to call.

    Args:
        url: Absolute URL from configuration.

    Raises:
        UrlNotAllowed: Scheme or host is outside the allowlist.
    """
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or host not in _ALLOWED_HOSTS:
        raise UrlNotAllowed(f"refusing URL host {host or '(missing)'}")
