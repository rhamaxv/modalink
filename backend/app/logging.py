import json
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import Request
from starlette.responses import Response

http_log = logging.getLogger("logicodix.http")
ai_log = logging.getLogger("logicodix.ai")

# Set explicitly rather than relying on root: the root logger defaults to
# WARNING, which would silently drop every INFO-level structured log line.
http_log.setLevel(logging.INFO)
ai_log.setLevel(logging.INFO)

_REDACTED_FIELDS = {"password", "authorization", "token"}
_REDACTED_PLACEHOLDER = "[redacted]"


def redact_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Blank out any field whose name is a known secret carrier.

    Matching is case-insensitive: HTTP headers arrive as `Authorization`,
    request bodies as `password`, and neither casing convention is guaranteed.
    """
    return {
        key: _REDACTED_PLACEHOLDER if key.lower() in _REDACTED_FIELDS else value
        for key, value in payload.items()
    }


async def log_request(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    started_at = time.perf_counter()
    response = await call_next(request)
    line = redact_payload({
        "method": request.method,
        "path": request.url.path,
        "status": response.status_code,
        "durasi_ms": round((time.perf_counter() - started_at) * 1000),
        "user_id": getattr(request.state, "user_id", None),
    })
    http_log.info(json.dumps(line))
    return response


def log_ai_call(model: str, duration_ms: int, token_count: int, valid: bool) -> None:
    """Called by the scoring service from phase 05 onward; never passed proposal content.

    Output keys stay in Indonesian (`durasi_ms`, `jumlah_token`) to match the
    vocabulary the http logger already emits and the field names phase 05's
    test asserts on; only the Python identifiers are English.
    """
    line = redact_payload({
        "model": model,
        "durasi_ms": duration_ms,
        "jumlah_token": token_count,
        "valid": valid,
    })
    ai_log.info(json.dumps(line))
