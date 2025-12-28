import time
import uuid
import json
import logging
from typing import Callable
from fastapi import Request
from starlette.types import ASGIApp
from .config import settings


# Configure logging to use JSON
logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL, logging.INFO))
logger = logging.getLogger(__name__)


class JSONRequestLogger:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope, receive, send):
        await self.app(scope, receive, send)


async def request_logging_middleware(request: Request, call_next: Callable):
    request_id = str(uuid.uuid4())
    start = time.time()
    # attach request_id
    request.state.request_id = request_id
    try:
        response = await call_next(request)
        status = response.status_code
    except Exception as exc:
        status = 500
        raise
    finally:
        end = time.time()
        latency_ms = int((end - start) * 1000)
        log = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "level": settings.LOG_LEVEL or "INFO",
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status": status,
            "latency_ms": latency_ms,
        }
        # webhook-specific fields
        w = getattr(request.state, "webhook_log", None)
        if w:
            log.update(w)

        print(json.dumps(log, separators=(",", ":")))

    return response
