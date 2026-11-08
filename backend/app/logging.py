import json
import logging
import time
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


async def catat_request(request: Request, call_next: Any) -> Response:
    mulai = time.perf_counter()
    respons = await call_next(request)
    baris = redact_payload({
        "method": request.method,
        "path": request.url.path,
        "status": respons.status_code,
        "durasi_ms": round((time.perf_counter() - mulai) * 1000),
        "user_id": getattr(request.state, "user_id", None),
    })
    http_log.info(json.dumps(baris))
    return respons


def catat_panggilan_ai(model: str, durasi_ms: int, jumlah_token: int, valid: bool) -> None:
    """Called by the scoring service from phase 05 onward; never passed proposal content."""
    baris = redact_payload({
        "model": model,
        "durasi_ms": durasi_ms,
        "jumlah_token": jumlah_token,
        "valid": valid,
    })
    ai_log.info(json.dumps(baris))
