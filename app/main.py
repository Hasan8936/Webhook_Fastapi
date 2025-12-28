import hmac
import hashlib
import json
from fastapi import FastAPI, Request, Header, HTTPException, Depends, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime
import re

from .config import settings
from .storage import insert_message, query_messages, stats as stats_fn, check_db_ready
from .logging_utils import request_logging_middleware
from .metrics import http_requests_total, webhook_requests_total, request_latency_seconds, metrics_endpoint


app = FastAPI()


class WebhookMessage(BaseModel):
    message_id: str = Field(...)
    from_: str = Field(..., alias="from")
    to: str = Field(..., alias="to")
    ts: str
    text: Optional[str] = Field(None, max_length=4096)

    @field_validator("message_id")
    @classmethod
    def non_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("message_id must be non-empty")
        return v

    @field_validator("from_")
    @classmethod
    def valid_from(cls, v):
        if not re.match(r"^\+\d+$", v):
            raise ValueError("from must be E.164-like")
        return v

    @field_validator("to")
    @classmethod
    def valid_to(cls, v):
        if not re.match(r"^\+\d+$", v):
            raise ValueError("to must be E.164-like")
        return v

    @field_validator("ts")
    @classmethod
    def valid_ts(cls, v):
        # must end with Z and be ISO format
        if not v.endswith("Z"):
            raise ValueError("ts must end with Z (UTC)")
        try:
            # parse
            datetime.fromisoformat(v.replace("Z", "+00:00"))
        except Exception:
            raise ValueError("ts must be ISO-8601 UTC string")
        return v


@app.middleware("http")
async def metrics_and_logging_middleware(request: Request, call_next):
    path = request.url.path
    start = datetime.utcnow()
    try:
        response = await request_logging_middleware(request, lambda req: call_next(req))
    finally:
        pass
    # update http metrics
    try:
        status = str(response.status_code)
        http_requests_total.labels(path=path, status=status).inc()
    except Exception:
        pass
    return response


def require_webhook_secret():
    if not settings.WEBHOOK_SECRET:
        raise RuntimeError("WEBHOOK_SECRET not set")


@app.post("/webhook")
async def webhook(request: Request, x_signature: Optional[str] = Header(None)):
    raw = await request.body()
    
    # First, validate JSON before checking signature
    try:
        payload = json.loads(raw)
    except Exception:
        request.state.webhook_log = {"message_id": None, "dup": False, "result": "validation_error"}
        webhook_requests_total.labels(result="validation_error").inc()
        raise HTTPException(status_code=422, detail="invalid json")
    
    # signature check
    if not settings.WEBHOOK_SECRET:
        # per spec, if missing, ready fails; here we still reject
        raise HTTPException(status_code=503, detail="server misconfigured")
    if not x_signature:
        # log
        request.state.webhook_log = {"message_id": payload.get("message_id"), "dup": False, "result": "invalid_signature"}
        webhook_requests_total.labels(result="invalid_signature").inc()
        raise HTTPException(status_code=401, detail="invalid signature")

    mac = hmac.new(settings.WEBHOOK_SECRET.encode(), raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(mac, x_signature):
        request.state.webhook_log = {"message_id": payload.get("message_id"), "dup": False, "result": "invalid_signature"}
        webhook_requests_total.labels(result="invalid_signature").inc()
        raise HTTPException(status_code=401, detail="invalid signature")

    # Validate message model
    try:
        msg = WebhookMessage(**payload)
    except Exception as e:
        request.state.webhook_log = {"message_id": payload.get("message_id"), "dup": False, "result": "validation_error"}
        webhook_requests_total.labels(result="validation_error").inc()
        raise HTTPException(status_code=422, detail="validation failed")

    created, result = insert_message(msg.message_id, msg.from_, msg.to, msg.ts, msg.text)
    request.state.webhook_log = {"message_id": msg.message_id, "dup": not created, "result": result}
    webhook_requests_total.labels(result=result).inc()

    return JSONResponse({"status": "ok"})


@app.get("/messages")
async def get_messages(limit: int = 50, offset: int = 0, from_: Optional[str] = None, since: Optional[str] = None, q: Optional[str] = None):
    # param bounds
    if limit < 1:
        limit = 1
    if limit > 100:
        limit = 100
    if offset < 0:
        offset = 0
    data, total = query_messages(limit, offset, from_, since, q)
    return {"data": data, "total": total, "limit": limit, "offset": offset}


@app.get("/stats")
async def get_stats():
    return stats_fn()


@app.get("/health/live")
async def live():
    return {"status": "ok"}


@app.get("/health/ready")
async def ready():
    if not settings.WEBHOOK_SECRET:
        return Response(status_code=503, content=b"")
    if not check_db_ready():
        return Response(status_code=503, content=b"")
    return {"status": "ok"}


@app.get("/metrics")
async def metrics():
    return metrics_endpoint()
