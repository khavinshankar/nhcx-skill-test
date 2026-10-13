"""G8. Receive: decrypt an inbound NHCX message and hand it to C1 in-process."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from care.nhcx.gateway import crypto
from care.nhcx.gateway import headers as H  # noqa: N812
from care.nhcx.gateway.errors import GatewayError

if TYPE_CHECKING:
    from care.nhcx.gateway.embedding import Gateway

logger = logging.getLogger("care.nhcx.gateway")

STATUS = {
    "BODY_TOO_LARGE": 413,
    "BODY_READ": 400,
    "INVALID_BODY": 400,
    "INVALID_JWE": 400,
    "WRONG_RECIPIENT": 400,
    "DECRYPT_FAILED": 422,
    "RECEIVE_FAILED": 502,
    "MARSHAL_ERROR": 500,
    "INTERNAL": 500,
}
ACCEPTED = 202
ACCEPT_OUTCOMES = ("settled", "unmatched", "ignored", "rejected")
KIT_TYPES = {"insuranceplan": "insurance", "coverageeligibility": "coverage"}


@dataclass
class Inbound:
    path: str
    received_at: datetime
    remote_addr: str
    kind: str = "unknown"
    headers: dict = field(default_factory=dict)
    payload: Any = None
    profile: Any = None
    guest: str = ""
    redelivery: bool = False
    ledger_id: str = ""


@dataclass
class InboundAnswer:
    status: int
    body: dict
    headers: dict = field(default_factory=dict)
    outcome: str | None = None


def kit_type(path: str) -> str:
    e = H.entity_type(path)
    return KIT_TYPES.get(e, e)


def kit_flow(path: str) -> str:
    return "request" if H.is_response_path(path) else "on_request"


def normalise(h: dict | None) -> dict:
    out = {k: v for k, v in (h or {}).items() if v is not None}
    for k in (H.SENDER_CODE, H.RECIPIENT_CODE):
        if isinstance(out.get(k), str) and out[k].strip():
            out[k] = H.normalize_code(out[k])
    return out


def acceptance(path: str, headers: dict | None) -> dict:
    headers = headers or {}
    api = H.get_string(headers, H.API_CALL_ID)
    corr = H.get_string(headers, H.CORRELATION_ID)
    return {
        "timestamp": H.ack_timestamp(),
        "api_call_id": api if H.is_id(api) else H.new_id(),
        "correlation_id": corr if H.is_id(corr) else H.new_id(),
        "result": {
            "sender_code": H.get_string(headers, H.SENDER_CODE),
            "recipient_code": H.get_string(headers, H.RECIPIENT_CODE),
            "entity_type": H.entity_type(path),
            "protocol_status": "request.queued",
        },
        "error": None,
    }


def error_body(
    err: GatewayError, request_id: str | None, upstream: dict | None = None
) -> dict:
    out: dict[str, Any] = {
        "ok": False,
        "error": {"code": err.code, "message": err.message, "retryable": err.retryable},
        "request_id": request_id or H.new_id(),
    }
    if upstream:
        out.update(upstream)
    return out


def _jwe_of(obj: dict) -> str | None:
    p = obj.get("payload")
    if isinstance(p, str):
        return p.strip()
    return crypto.flattened_to_compact(p) or crypto.flattened_to_compact(obj)


def peek_headers(body: bytes) -> dict:
    """Protected header of an inbound body, without decrypting; `{}` when unreadable."""
    try:
        obj = json.loads(body)
    except (ValueError, TypeError):
        return {}
    if not isinstance(obj, dict):
        return {}
    jwe = _jwe_of(obj)
    if jwe:
        try:
            return crypto.parse_header(jwe)
        except crypto.CryptoError:
            return {}
    return {k: v for k, v in obj.items() if k.startswith("x-hcx-")}


def _is_encrypted(obj: dict) -> bool:
    if "payload" in obj:
        jwe = _jwe_of(obj)
        return obj.get("type") != "ProtocolResponse" or crypto.is_compact_jwe(jwe)
    return crypto.flattened_to_compact(obj) is not None


def decrypt_for(gw: Gateway, code: str, jwe: str) -> tuple[Any, bytes]:
    tried: list[Any] = []
    first = gw.profiles.by_code(code)
    candidates = ([first] if first else []) + list(gw.profiles)
    for profile in candidates:
        if (
            profile is None
            or profile.key is None
            or any(profile.key is k for k in tried)
        ):
            continue
        tried.append(profile.key)
        try:
            return profile, crypto.decrypt(jwe, profile.key)
        except crypto.CryptoError:
            continue
    raise GatewayError(
        "DECRYPT_FAILED",
        "payload could not be decrypted with any configured participant's private key",
    )


def receive(gw: Gateway, path: str, body: bytes, ip: str) -> Inbound:
    try:
        obj = json.loads(body)
    except (ValueError, TypeError) as e:
        raise GatewayError("INVALID_BODY", "body must be a JSON object", cause=e) from e
    if not isinstance(obj, dict):
        raise GatewayError("INVALID_BODY", "body must be a JSON object")
    inb = Inbound(
        path=H.clean_path(path), received_at=datetime.now(UTC), remote_addr=ip
    )
    if _is_encrypted(obj):
        jwe = _jwe_of(obj)
        if not crypto.is_compact_jwe(jwe):
            raise GatewayError("INVALID_JWE", crypto.NOT_COMPACT)
        try:
            hdr = crypto.parse_header(jwe)
        except crypto.CryptoError as e:
            raise GatewayError(
                "INVALID_JWE", "unreadable JWE protected header", cause=e
            ) from e
        rc = H.get_string(hdr, H.RECIPIENT_CODE)
        guest = rc != "" and not gw.profiles.is_local(rc)
        codes = ", ".join(gw.profiles.codes())
        if guest and not gw.guests:
            raise GatewayError(
                "WRONG_RECIPIENT",
                f"message is addressed to {H.normalize_code(rc)}, this adapter holds {codes}",
            )
        try:
            profile, plain = decrypt_for(gw, rc, jwe)
        except GatewayError as e:
            if guest:
                raise GatewayError(
                    "WRONG_RECIPIENT",
                    f"message is addressed to {H.normalize_code(rc)}, this adapter holds "
                    f"{codes}; none of its keys opens it; a guest is served once its "
                    "registry record carries this adapter's certificate",
                ) from e
            raise
        inb.profile = profile
        if guest:
            inb.guest = H.normalize_code(rc)
        try:
            payload = json.loads(plain)
        except (ValueError, TypeError):
            payload = plain.decode("utf-8", errors="replace")
        inb.kind = "fhir"
        inb.headers = normalise(hdr)
        inb.payload = payload
    else:
        inb.payload = obj
        hdrs = {k: v for k, v in obj.items() if k.startswith("x-hcx-")}
        inb.kind = "protocol" if hdrs or "type" in obj else "json"
        inb.headers = normalise(hdrs)
    try:
        inb.redelivery = gw.ledger.seen("in", H.get_string(inb.headers, H.API_CALL_ID))
    except Exception:
        logger.warning(
            "nhcx: ledger seen() failed; treating as not seen", exc_info=True
        )
        inb.redelivery = False
    return inb


def participant(inb: Inbound) -> str:
    if inb.guest:
        return inb.guest
    if inb.profile is not None:
        return inb.profile.code
    return H.get_string(inb.headers, H.RECIPIENT_CODE)


def _outcome_of(result: Any) -> str:
    if isinstance(result, dict):
        result = result.get("outcome")
    if hasattr(result, "value"):
        result = result.value
    return str(result) if result is not None else ""


def deliver(gw: Gateway, inb: Inbound) -> tuple[dict, GatewayError | None]:
    who = participant(inb)
    envelope = {
        "meta": {
            "type": "in",
            "payloadType": inb.kind,
            "path": inb.path,
            "ip": inb.remote_addr,
            "time": inb.received_at.astimezone().isoformat(timespec="seconds"),
            "redelivery": inb.redelivery,
            "participant": who,
        },
        "jwe_headers": inb.headers,
        "fhir": inb.payload,
    }
    delivery = {
        "path": inb.path,
        "type": kit_type(inb.path),
        "flow": kit_flow(inb.path),
        "payload_kind": inb.kind,
        "correlation_id": H.get_string(inb.headers, H.CORRELATION_ID),
        "api_call_id": H.get_string(inb.headers, H.API_CALL_ID),
        "redelivery": inb.redelivery,
        "participant": who,
    }
    start = time.monotonic()
    try:
        result = gw.receive(envelope, delivery)
    except Exception as e:
        logger.exception("nhcx: C1.receive raised for path=%s", inb.path)
        took = int((time.monotonic() - start) * 1000)
        return (
            {"outcome": "error", "detail": str(e), "duration": took},
            GatewayError(
                "RECEIVE_FAILED",
                "C1 could not apply the message",
                retryable=True,
                cause=e,
            ),
        )
    took = int((time.monotonic() - start) * 1000)
    outcome = _outcome_of(result)
    if outcome not in ACCEPT_OUTCOMES:
        detail = result.get("detail") if isinstance(result, dict) else None
        return (
            {"outcome": outcome or "error", "detail": detail, "duration": took},
            GatewayError(
                "RECEIVE_FAILED", "C1 could not apply the message", retryable=True
            ),
        )
    out = {"outcome": outcome, "duration": took}
    if isinstance(result, dict) and result.get("detail"):
        out["detail"] = result["detail"]
    return out, None


def record_inbound(
    gw: Gateway, inb: Inbound, result: dict | None, err: GatewayError | None
) -> None:
    if not gw.ledger.enabled:
        return
    h = inb.headers
    entry: dict[str, Any] = {
        "direction": "in",
        "created_at": inb.received_at.isoformat(),
        "path": inb.path,
        "format": inb.kind,
        "sender": H.get_string(h, H.SENDER_CODE),
        "recipient": H.get_string(h, H.RECIPIENT_CODE),
        "correlation_id": H.get_string(h, H.CORRELATION_ID),
        "api_call_id": H.get_string(h, H.API_CALL_ID),
        "request_id": H.get_string(h, H.REQUEST_ID),
        "workflow_id": H.get_string(h, H.WORKFLOW_ID) or None,
        "hcx_status": H.get_string(h, H.STATUS),
        "headers": h,
        "fhir": inb.payload,
        "redelivery": inb.redelivery,
        "duration_ms": int(
            (datetime.now(UTC) - inb.received_at).total_seconds() * 1000
        ),
    }
    if result:
        entry["peer"] = {
            "url": "C1.receive",
            "handler": "C1.receive",
            "status_code": 502 if err else ACCEPTED,
            "outcome": result.get("outcome"),
            "response": {k: v for k, v in result.items() if k != "duration"},
        }
        entry["duration_ms"] = result.get("duration", 0)
    if err is None:
        entry["status"] = "delivered"
    elif err.code == "RECEIVE_FAILED":
        entry["status"] = "delivery_failed"
        entry["error"] = {"code": err.code, "message": err.message}
    else:
        entry["status"] = "rejected"
        entry["error"] = {"code": err.code, "message": err.message}
    try:
        inb.ledger_id = gw.ledger.record(entry) or ""
    except Exception:
        logger.exception("nhcx: ledger write failed for an inbound message")


def handle_inbound(
    gw: Gateway, path: str, body: bytes, ip: str, request_id: str | None
) -> InboundAnswer:
    try:
        inb = receive(gw, path, body, ip)
    except GatewayError as e:
        refused = Inbound(
            path=H.clean_path(path),
            received_at=datetime.now(UTC),
            remote_addr=ip,
            kind="unknown",
            headers=normalise(peek_headers(body)),
        )
        record_inbound(gw, refused, None, e)
        logger.warning("nhcx: inbound refused path=%s code=%s", path, e.code)
        return InboundAnswer(STATUS.get(e.code, 500), error_body(e, request_id))
    result, err = deliver(gw, inb)
    record_inbound(gw, inb, result, err)
    if err:
        upstream = {
            "upstream_status": 502,
            "upstream_body": {k: v for k, v in result.items() if k != "duration"},
        }
        return InboundAnswer(
            STATUS[err.code],
            error_body(err, request_id, upstream),
            outcome=result.get("outcome"),
        )
    extra = {"X-Nhcx-Ledger-Id": inb.ledger_id} if inb.ledger_id else {}
    logger.info(
        "nhcx: inbound delivered path=%s outcome=%s ledger_id=%s",
        inb.path,
        result.get("outcome"),
        inb.ledger_id,
    )
    return InboundAnswer(
        ACCEPTED,
        acceptance(inb.path, inb.headers),
        extra,
        outcome=result.get("outcome"),
    )


def not_open_answer(path: str, body: bytes) -> InboundAnswer:
    """Gateway not open: 202 with an `unmatched` outcome, never 503 (G8D)."""
    return InboundAnswer(
        ACCEPTED, acceptance(path, normalise(peek_headers(body))), outcome="unmatched"
    )
