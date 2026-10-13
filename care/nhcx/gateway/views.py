"""NHCX-facing HTTP routes (G1, G8, G11): no auth, CSRF exempt, no request transaction."""

from __future__ import annotations

import functools
import logging
import uuid

from django.db import transaction
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from care.nhcx.gateway import gateway_status
from care.nhcx.gateway.errors import GatewayError
from care.nhcx.gateway.receive import error_body, not_open_answer

logger = logging.getLogger("care.nhcx.gateway")

MAX_REQUEST_ID = 128
DEFAULT_MAX_BODY = 100 * 1024 * 1024
HEALTH_BODY_LIMIT = 4096


class _BodyTooLargeError(Exception):
    pass


def _request_id(request: HttpRequest) -> str:
    rid = (request.headers.get("X-Request-Id") or "").strip()
    if rid and len(rid) <= MAX_REQUEST_ID:
        return rid
    return str(uuid.uuid4())


def _answer(
    status: int, body: dict, rid: str, headers: dict | None = None
) -> JsonResponse:
    resp = JsonResponse(body, status=status, json_dumps_params={"ensure_ascii": False})
    resp["X-Request-Id"] = rid
    for k, v in (headers or {}).items():
        resp[k] = v
    return resp


def _read_body(request: HttpRequest, limit: int) -> bytes:
    try:
        declared = int(request.headers.get("Content-Length") or 0)
    except ValueError:
        declared = 0
    if declared > limit:
        raise _BodyTooLargeError
    data = request.read(limit + 1)
    if len(data) > limit:
        raise _BodyTooLargeError
    return data


def gateway_route(view):
    """Panic recovery, then the request id; the body cap is applied in each view."""

    @functools.wraps(view)
    def wrapped(request: HttpRequest, *args, **kwargs):
        rid = _request_id(request)
        request.nhcx_request_id = rid
        try:
            return view(request, rid, *args, **kwargs)
        except Exception:
            logger.exception("nhcx: gateway route failed path=%s", request.path)
            return _answer(
                500,
                {
                    "ok": False,
                    "error": {"code": "INTERNAL", "message": "internal error"},
                },
                rid,
            )

    return csrf_exempt(transaction.non_atomic_requests(wrapped))


@gateway_route
@require_http_methods(["POST"])
def inbound(request: HttpRequest, rid: str, path: str = "", prefix: str = ""):
    gw, _ = gateway_status()
    limit = gw.cfg.max_body_bytes if gw else DEFAULT_MAX_BODY
    full_path = prefix + path
    try:
        body = _read_body(request, limit)
    except _BodyTooLargeError:
        err = GatewayError("BODY_TOO_LARGE", f"request body exceeds {limit} bytes")
        return _answer(413, error_body(err, rid), rid)
    except OSError as e:
        err = GatewayError("BODY_READ", "request body could not be read", cause=e)
        return _answer(400, error_body(err, rid), rid)
    ip = request.META.get("REMOTE_ADDR", "")
    ans = (
        gw.handle_inbound(full_path, body, ip, rid)
        if gw
        else not_open_answer(full_path, body)
    )
    return _answer(ans.status, ans.body, rid, ans.headers)


@gateway_route
@require_http_methods(["GET", "POST"])
def healthz(request: HttpRequest, rid: str):
    gw, cause = gateway_status()
    body = b""
    if request.method == "POST":
        try:
            body = request.read(HEALTH_BODY_LIMIT)
        except OSError:
            body = b""
    if gw is None:
        return _answer(
            200,
            {
                "status": "ok",
                "service": "nhcx-adapter",
                "version": "embedded",
                "gateway": f"gateway not configured: {cause}",
            },
            rid,
        )
    return _answer(200, gw.healthz(request.method, body), rid)


@gateway_route
@require_http_methods(["GET"])
def readyz(request: HttpRequest, rid: str):
    gw, cause = gateway_status()
    if gw is None:
        return _answer(503, {"status": f"gateway not configured: {cause}"}, rid)
    status, body = gw.readyz()
    return _answer(status, body, rid)
