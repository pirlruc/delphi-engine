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
    for attempt in range(max(attempts, 1)):
        try:
            if verb == "POST":
                response = client.post(url, json=json_body, timeout=timeout, headers=headers)
            else:
                response = client.get(url, timeout=timeout, headers=headers)
            if response.status_code == 429:
                last = httpx.HTTPStatusError(
                    "Too Many Requests", request=response.request, response=response
                )
                time.sleep(_retry_wait(response, delay))
                delay = min(delay * 2, 4.0)
                continue
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            last = exc
            if attempt + 1 >= max(attempts, 1):
                break
            time.sleep(delay)
            delay = min(delay * 2, 4.0)
    if last is not None:
        raise last
    raise RuntimeError(f"request failed: {url}")


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
