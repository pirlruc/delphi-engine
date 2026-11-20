"""HTTP JSON helpers with exponential backoff (PROD-002 subset)."""

from __future__ import annotations

import time
from typing import Any

import httpx

__all__ = ["request_json"]

_MAX_SLEEP = 8.0


def request_json(
    client: httpx.Client,
    method: str,
    url: str,
    *,
    attempts: int = 3,
    json_body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 30.0,
) -> object:
    """GET or POST JSON, retrying on errors and HTTP 429.

    Args:
        client: HTTP client.
        method: GET or POST.
        url: Request URL.
        attempts: Total tries.
        json_body: POST body.
        headers: Optional extra headers.
        timeout: Per-request timeout.

    Returns:
        Parsed JSON.

    Raises:
        httpx.HTTPError: When every attempt fails.
        ValueError: When the body is not JSON.
    """
    delay = 0.05
    last: Exception | None = None
    verb = method.upper()
    tries = max(attempts, 1)
    for attempt in range(tries):
        try:
            if verb == "POST":
                response = client.post(url, json=json_body, timeout=timeout, headers=headers)
            else:
                response = client.get(url, timeout=timeout, headers=headers)
        except httpx.TransportError as exc:
            last = exc
            if attempt + 1 >= tries:
                break
            time.sleep(delay)
            delay = min(delay * 2, 4.0)
            continue
        if response.status_code == 429 or response.status_code >= 500:
            last = httpx.HTTPStatusError(
                "retryable status", request=response.request, response=response
            )
            if attempt + 1 >= tries:
                break
            wait = _retry_wait(response, delay) if response.status_code == 429 else delay
            time.sleep(wait)
            delay = min(delay * 2, 4.0)
            continue
        response.raise_for_status()
        return response.json()
    if last is None:  # pragma: no cover
        raise RuntimeError(f"request failed: {url}")
    raise last


def _retry_wait(response: httpx.Response, fallback: float) -> float:
    """Parse Retry-After seconds, else use ``fallback``.

    Args:
        response: 429 response.
        fallback: Default delay.

    Returns:
        Sleep seconds, capped.
    """
    raw = response.headers.get("Retry-After", "")
    try:
        return min(float(raw), _MAX_SLEEP)
    except ValueError:
        return min(fallback, _MAX_SLEEP)
