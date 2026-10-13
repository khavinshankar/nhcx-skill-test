"""G7. Send: one FHIR payload to one encrypted NHCX message, synchronously."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from django.db import connections

from care.nhcx.gateway import crypto
from care.nhcx.gateway import headers as H  # noqa: N812
from care.nhcx.gateway.errors import (
    GatewayError,
    SendError,
    SendInTransactionError,
    as_gateway_error,
)

if TYPE_CHECKING:
    from care.nhcx.gateway.embedding import Gateway

logger = logging.getLogger("care.nhcx.gateway")

ALIASES = {
    "sender": H.SENDER_CODE,
    "recipient": H.RECIPIENT_CODE,
    "correlation_id": H.CORRELATION_ID,
    "request_id": H.REQUEST_ID,
    "api_call_id": H.API_CALL_ID,
    "workflow_id": H.WORKFLOW_ID,
    "status": H.STATUS,
}


@dataclass
class OutboundRequest:
    path: str
    headers: dict
    fhir: Any


@dataclass
class SendResult:
    ok: bool
    path: str
    url: str
    headers: dict
    gateway_status: int
    response: Any
    duration_ms: int
    ledger_id: str
    txn_id: str
    correlation_id: str
    api_call_id: str
    request_id: str
    extra: dict = field(default_factory=dict, repr=False)

    def to_dict(self) -> dict:
        out = asdict(self)
        out.pop("extra", None)
        return out

    @property
    def error_code(self) -> str | None:
        """NHCX's own error code when `ok` is false, else `GATEWAY_HTTP_<status>`."""
        if self.ok:
            return None
        err = self.response.get("error") if isinstance(self.response, dict) else None
        if isinstance(err, dict) and err.get("code"):
            return str(err["code"])
        return f"GATEWAY_HTTP_{self.gateway_status}"

    @property
    def error_message(self) -> str | None:
        if self.ok:
            return None
        err = self.response.get("error") if isinstance(self.response, dict) else None
        if isinstance(err, dict) and err.get("message"):
            return str(err["message"])
        return "NHCX did not accept the message"


def ensure_not_in_transaction() -> None:
    """Refuse to send inside a database transaction (G7D, SCAFFOLDING 8).

    Blocks opened by Django's TestCase (`_from_testcase`) are not the caller's
    transaction and are ignored, so services can be tested under TestCase.
    """
    for conn in connections.all(initialized_only=True):
        if not conn.in_atomic_block:
            continue
        if all(getattr(b, "_from_testcase", False) for b in conn.atomic_blocks):
            continue
        msg = (
            "gateway.send must not be called inside a database transaction "
            f"(connection {conn.alias!r} is in an atomic block): send first, "
            "outside any transaction, then write the leg in a transaction of its own"
        )
        raise SendInTransactionError(msg)


def _as_string(v: Any) -> str:
    if isinstance(v, str):
        return v
    return json.dumps(v).strip('"')


def _non_empty(v: Any) -> bool:
    if v is None:
        return False
    if isinstance(v, (str, dict, list)) and len(v) == 0:
        return False
    return not (isinstance(v, str) and v.strip() == "")


def parse_outbound(path: str, envelope: Any) -> OutboundRequest:
    if not isinstance(envelope, dict):
        raise SendError("INVALID_ENVELOPE", "body must be a JSON object")
    headers: dict = {}
    if "jwe_headers" in envelope:
        jh = envelope["jwe_headers"]
        if not isinstance(jh, dict):
            raise SendError("INVALID_ENVELOPE", "jwe_headers must be an object")
        headers.update(jh)
    for k in H.HCX_HEADERS:
        if k in envelope:
            headers[k] = _as_string(envelope[k])
    for alias, k in ALIASES.items():
        if alias in envelope:
            headers[k] = _as_string(envelope[alias])
    if _non_empty(envelope.get("fhir")):
        fhir = envelope["fhir"]
    elif _non_empty(envelope.get("payload")):
        fhir = envelope["payload"]
    else:
        raise SendError(
            "INVALID_ENVELOPE",
            'body needs a "fhir" object or must itself be a FHIR resource',
        )
    return OutboundRequest(path=path, headers=headers, fhir=fhir)


def _payload(fhir: Any) -> Any:
    if isinstance(fhir, (bytes, bytearray)):
        fhir = fhir.decode("utf-8", errors="replace")
    if isinstance(fhir, str):
        if fhir.strip() == "":
            raise SendError("INVALID_PAYLOAD", "fhir payload must be a JSON value")
        try:
            return json.loads(fhir)
        except ValueError as e:
            raise SendError(
                "INVALID_PAYLOAD", "fhir payload must be a JSON value"
            ) from e
    try:
        json.dumps(fhir)
    except (TypeError, ValueError) as e:
        raise SendError("INVALID_PAYLOAD", "fhir payload must be a JSON value") from e
    return fhir


def dispatch(client: Any, path: str, jwe: str) -> dict:
    url = H.target_url(client.cfg.url_nhcx, path)
    body: dict = {"payload": jwe}
    if H.is_response_path(path):
        body["type"] = "JWEPayload"
    start = time.monotonic()
    status, raw = client.post_with_token(url, body, label="GATEWAY")
    duration = int((time.monotonic() - start) * 1000)
    if raw in (None, b"", ""):
        parsed = None
    else:
        try:
            parsed = json.loads(raw)
        except (ValueError, TypeError):
            parsed = (
                raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
            )
    return {"url": url, "status": status, "body": parsed, "duration": duration}


def send(gw: Gateway, path: str, envelope: Any) -> SendResult:  # noqa: PLR0915
    ensure_not_in_transaction()
    req = parse_outbound(path, envelope)
    path = H.clean_path(req.path)
    if path == "":
        raise SendError("NO_PATH", "path is required (for example v1/preauth/submit)")
    fhir = _payload(req.fhir)

    hdrs = req.headers
    ledger = gw.ledger
    if (
        ledger.enabled
        and H.is_response_path(path)
        and not H.is_id(H.get_string(hdrs, H.CORRELATION_ID))
    ):
        try:
            prev = ledger.last_inbound_request(
                H.entity_type(path),
                H.get_string(hdrs, H.RECIPIENT_CODE) or None,
                H.get_string(hdrs, H.WORKFLOW_ID) or None,
            )
        except Exception:
            logger.warning("nhcx: response threading lookup failed", exc_info=True)
            prev = None
        if prev:
            hdrs[H.CORRELATION_ID] = prev["correlation_id"]
            if prev.get("workflow_id") and not H.get_string(hdrs, H.WORKFLOW_ID):
                hdrs[H.WORKFLOW_ID] = prev["workflow_id"]

    headers = H.build_protected_headers(hdrs, path)
    if not H.get_string(headers, H.SENDER_CODE):
        headers[H.SENDER_CODE] = gw.profiles.default.code
    sender = gw.identity_for(headers[H.SENDER_CODE])
    recipient = H.get_string(headers, H.RECIPIENT_CODE)
    started_at = datetime.now(UTC)
    start = time.monotonic()
    entry = {
        "direction": "out",
        "created_at": started_at.isoformat(),
        "path": path,
        "format": "fhir",
        "sender": headers[H.SENDER_CODE],
        "recipient": recipient,
        "correlation_id": headers[H.CORRELATION_ID],
        "api_call_id": headers[H.API_CALL_ID],
        "request_id": headers[H.REQUEST_ID],
        "workflow_id": H.get_string(headers, H.WORKFLOW_ID) or None,
        "hcx_status": H.get_string(headers, H.STATUS),
        "headers": headers,
        "fhir": fhir,
    }

    def record() -> str:
        try:
            return ledger.record(entry) or ""
        except Exception:
            logger.exception("nhcx: ledger write failed for an outbound message")
            return ""

    def fail(err: BaseException) -> SendError:
        g = as_gateway_error(err)
        entry["status"] = "failed"
        entry["error"] = {"code": g.code, "message": g.message}
        entry["duration_ms"] = int((time.monotonic() - start) * 1000)
        ledger_id = record()
        logger.warning(
            "nhcx: send failed path=%s code=%s correlation_id=%s",
            path,
            g.code,
            headers[H.CORRELATION_ID],
        )
        return SendError.from_error(g, ledger_id=ledger_id, headers=headers)

    if recipient == "":
        raise fail(GatewayError("NO_RECIPIENT", "x-hcx-recipient_code is required"))
    try:
        pub, _ = sender.certificate(recipient)
    except Exception as e:
        raise fail(e) from e
    try:
        jwe = crypto.encrypt(
            json.dumps(fhir, separators=(",", ":"), ensure_ascii=False), pub, headers
        )
    except Exception as e:
        raise fail(GatewayError("ENCRYPT_ERROR", str(e), cause=e)) from e
    try:
        res = dispatch(sender, path, jwe)
    except Exception as e:
        raise fail(e) from e

    ok = 200 <= res["status"] < 300  # noqa: PLR2004
    entry["duration_ms"] = res["duration"]
    entry["peer"] = {
        "url": res["url"],
        "status_code": res["status"],
        "response": res["body"],
    }
    if ok:
        entry["status"] = "accepted"
    else:
        entry["status"] = "rejected"
        entry["error"] = {
            "code": f"GATEWAY_HTTP_{res['status']}",
            "message": "NHCX did not accept the message",
        }
    ledger_id = record()
    logger.info(
        "nhcx: sent path=%s status=%s ledger_id=%s correlation_id=%s",
        path,
        res["status"],
        ledger_id,
        headers[H.CORRELATION_ID],
    )
    return SendResult(
        ok=ok,
        path=path,
        url=res["url"],
        headers=headers,
        gateway_status=res["status"],
        response=res["body"],
        duration_ms=res["duration"],
        ledger_id=ledger_id,
        txn_id=ledger_id,
        correlation_id=headers[H.CORRELATION_ID],
        api_call_id=headers[H.API_CALL_ID],
        request_id=headers[H.REQUEST_ID],
    )
