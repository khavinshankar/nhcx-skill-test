"""G5. Protocol headers: the `x-hcx-*` set, ids, paths, codes and timestamps."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from django.utils import timezone

API_CALL_ID = "x-hcx-api_call_id"
REQUEST_ID = "x-hcx-request_id"
CORRELATION_ID = "x-hcx-correlation_id"
TIMESTAMP = "x-hcx-timestamp"
STATUS = "x-hcx-status"
SENDER_CODE = "x-hcx-sender_code"
RECIPIENT_CODE = "x-hcx-recipient_code"
WORKFLOW_ID = "x-hcx-workflow_id"

HCX_HEADERS = (
    SENDER_CODE,
    RECIPIENT_CODE,
    CORRELATION_ID,
    REQUEST_ID,
    API_CALL_ID,
    WORKFLOW_ID,
    STATUS,
    TIMESTAMP,
)

STATUS_REQUEST = "request.initiated"
STATUS_RESPONSE = "response.complete"
HCX_SUFFIX = "@hcx"
UUID_LENGTH = 36


def normalize_code(code: Any) -> str:
    code = (code or "").strip() if isinstance(code, str) else ""
    if code == "" or code.lower().endswith(HCX_SUFFIX):
        return code
    return code + HCX_SUFFIX


def same_code(a: Any, b: Any) -> bool:
    return normalize_code(a).lower() == normalize_code(b).lower()


def clean_path(path: Any) -> str:
    return (path or "").strip().strip("/") if isinstance(path, str) else ""


def new_id() -> str:
    return str(uuid.uuid4())


def is_id(s: Any) -> bool:
    if not isinstance(s, str):
        return False
    s = s.strip()
    if len(s) != UUID_LENGTH:
        return False
    try:
        uuid.UUID(s)
    except ValueError:
        return False
    return True


def ensure_id(s: Any) -> str:
    return s.strip() if is_id(s) else new_id()


def _segments(path: str) -> list[str]:
    return clean_path(path).split("/")


def is_response_path(path: Any) -> bool:
    return _segments(path)[-1].startswith("on_")


def default_status(path: Any) -> str:
    return STATUS_RESPONSE if is_response_path(path) else STATUS_REQUEST


def entity_type(path: Any) -> str:
    segs = _segments(path)
    if len(segs) == 1:
        e = segs[0]
    else:
        e = segs[-2]
        if e == "v1":
            e = segs[-1]
    e = e.removeprefix("on_")
    return "payment" if e == "paymentnotice" else e


def get_string(headers: Any, key: str) -> str:
    if not isinstance(headers, dict):
        return ""
    v = headers.get(key)
    return v.strip() if isinstance(v, str) else ""


def build_protected_headers(given: Any, path: str) -> dict:
    out: dict = {}
    for k, v in (given or {}).items():
        if isinstance(v, str):
            if v.strip() != "":
                out[k] = v.strip()
        elif v is not None:
            out[k] = v
    for k in (SENDER_CODE, RECIPIENT_CODE):
        c = normalize_code(get_string(out, k))
        if c:
            out[k] = c
        else:
            out.pop(k, None)
    out[CORRELATION_ID] = ensure_id(get_string(out, CORRELATION_ID))
    out[REQUEST_ID] = ensure_id(get_string(out, REQUEST_ID))
    out[API_CALL_ID] = ensure_id(get_string(out, API_CALL_ID))
    if get_string(out, STATUS) == "":
        out[STATUS] = default_status(path)
    if get_string(out, TIMESTAMP) == "":
        out[TIMESTAMP] = timestamp()
    if get_string(out, WORKFLOW_ID) == "":
        out.pop(WORKFLOW_ID, None)
    return out


def timestamp(now: datetime | None = None) -> str:
    """`YYYY-MM-DDThh:mm:ss+hhmm` in the Django time zone (Asia/Kolkata in CARE)."""
    now = timezone.localtime(now or timezone.now())
    return now.strftime("%Y-%m-%dT%H:%M:%S%z")


def ack_timestamp(t: datetime | None = None) -> str:
    """`DD/MM/YYYY hh:mm:ss:mmm` for the 202 acceptance body (G8)."""
    t = timezone.localtime(t or timezone.now())
    return t.strftime("%d/%m/%Y %H:%M:%S") + f":{t.microsecond // 1000:03d}"


def target_url(base: str, path: str) -> str:
    base = (base or "").strip().rstrip("/")
    path = clean_path(path)
    if path == "":
        return base
    if base.endswith("/v1") and path.startswith("v1/"):
        base = base[: -len("/v1")]
    return base + "/" + path
