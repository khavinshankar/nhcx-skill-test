"""C1 callback door: receive, route, and the shared rules used by C2 to C10.

``receive(envelope, delivery)`` is what G8 calls (``settings.NHCX_RECEIVE_HANDLER``)
and returns ``{"outcome": settled|unmatched|ignored|rejected|error, "detail"}``.
Polling (A10 to A13) applies a reply found in the ledger through
``route(type, envelope, corr)`` with the leg's correlation id.

Handler modules (``care.nhcx.callbacks.<name>``) expose
``handle(envelope, delivery) -> outcome or result dict``; they are imported
lazily by name, and a missing module answers ``unmatched``. ``delivery`` carries
``correlation_id`` (the leg's) and, for ``task``/``status``, ``route`` = "C7"/"C8".

Shared rules (C1P): ``Rejected``, ``payload``, ``is_protocol_response``,
``rejection``, ``failed_send``, ``revive``, ``leg_write``, ``already_applied``,
``claim_for_correlation``, ``claim_named_in``, ``result`` and the outcome
constants ``SETTLED``, ``UNMATCHED``, ``IGNORED``, ``REJECTED``, ``ERROR``.
"""

import importlib
import logging

from django.db import transaction

from care.nhcx import archive
from care.nhcx.fhir import bundle as fb

logger = logging.getLogger(__name__)

SETTLED = "settled"
UNMATCHED = "unmatched"
IGNORED = "ignored"
REJECTED = "rejected"
ERROR = "error"

TYPES = {
    "coverage",
    "insurance",
    "preauth",
    "task",
    "claim",
    "payment",
    "communication",
    "status",
}
CANCEL_REFUSED = "The payer did not accept the cancellation."
NO_PAYLOAD = "The callback carried no readable payload."


class Rejected(Exception):  # noqa: N818 - C1P's name
    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


def result(outcome, detail="") -> dict:
    return {"outcome": outcome, "detail": detail or ""}


def _as_result(value) -> dict:
    if isinstance(value, dict) and "outcome" in value:
        return {"outcome": value["outcome"], "detail": value.get("detail") or ""}
    return result(str(value or SETTLED))


# ---- shared rules ----


def payload(envelope):
    body = envelope.get("fhir") if isinstance(envelope, dict) else None
    if not isinstance(body, dict):
        raise Rejected(NO_PAYLOAD)
    return body


def is_protocol_response(body) -> bool:
    try:
        return fb.is_protocol_response(body)
    except Exception:
        return False


def rejection(body) -> str:
    details = body.get("x-hcx-error_details") if isinstance(body, dict) else None
    if isinstance(details, str):
        text = fb.protocol_error(body)
        if text and ":" in text:
            return text
        return f"NHCX: {text or 'The gateway rejected the request.'}"
    details = details if isinstance(details, dict) else {}
    code = details.get("code") or "NHCX"
    message = details.get("message") or "The gateway rejected the request."
    return f"{code}: {message}"


def failed_send(row) -> bool:
    status = getattr(row, "status", None)
    if status == "error":
        return True
    msg = getattr(row, "error_message", None)
    return (
        bool(msg)
        and msg != CANCEL_REFUSED
        and status
        in {
            "approved",
            "partial",
            "queried",
        }
    )


def _claim_of(row):
    from care.nhcx.models import Claim

    if isinstance(row, Claim):
        return row
    return getattr(row, "claim", None)


def _restamp(row) -> None:
    from care.nhcx.services import stage

    claim = _claim_of(row)
    if claim is not None:
        claim.refresh_from_db()
        stage.recompute(claim)


def revive(row, waiting_status) -> bool:
    """Reopen a leg on record as a failed send (the payer answered it)."""
    if not failed_send(row):
        return False
    row.status = waiting_status
    row.error_message = None
    row.save()
    _restamp(row)
    logger.info(
        "nhcx: revived %s claim=%s corr=%s",
        type(row).__name__,
        getattr(_claim_of(row), "claim_no", None),
        getattr(row, "correlation_id", None),
    )
    return True


def leg_write(row, **values) -> None:
    with transaction.atomic():
        for k, v in values.items():
            setattr(row, k, v)
        row.save()
        _restamp(row)


def already_applied(row, api_call_id, parsed) -> bool:
    if api_call_id:
        return (row.api_call_id or "") == api_call_id
    if row.status == "submitting":
        return False
    parsed = parsed or {}
    return (row.outcome or "") == (parsed.get("outcome") or "") and (
        row.adjudication or ""
    ) == (parsed.get("adjudication") or "")


# ---- matching ----


def _corr_lookups():
    from care.nhcx import models as m

    return [
        (m.ClaimPreauth, "correlation_id"),
        (m.ClaimPreauth, "cancel_correlation_id"),
        (m.ClaimSubmission, "correlation_id"),
        (m.ClaimPlan, "correlation_id"),
        (m.ClaimAuth, "correlation_id"),
        (m.ClaimQuery, "correlation_id"),
        (m.ClaimQuery, "reply_correlation_id"),
        (m.ClaimEnquiry, "correlation_id"),
        (m.ClaimPayment, "correlation_id"),
        (m.ClaimPayment, "ack_correlation_id"),
        (m.ClaimPredetermination, "correlation_id"),
        (m.ClaimAdjudication, "correlation_id"),
    ]


def claim_for_correlation(corr):
    if not corr:
        return None
    from care.nhcx.models import Claim

    claim = Claim.objects.filter(correlation_id=corr).order_by("-id").first()
    if claim is not None:
        return claim
    for model, column in _corr_lookups():
        row = (
            model.objects.filter(**{column: corr})
            .select_related("claim")
            .order_by("-id")
            .first()
        )
        if row is not None:
            return row.claim
    return None


def _collect(node, out: list) -> None:
    if isinstance(node, dict):
        ident_type = node.get("type")
        if isinstance(ident_type, dict) and "value" in node:
            coding = ident_type.get("coding")
            if (
                isinstance(coding, list)
                and coding
                and isinstance(coding[0], dict)
                and coding[0].get("code") == "CLN"
                and isinstance(node.get("value"), str)
            ):
                out.append(node["value"].strip())
        for key, value in node.items():
            if key == "display" and isinstance(value, str):
                out.append(value.strip())
            elif key == "reference" and isinstance(value, str):
                out.append(value.rstrip("/").rsplit("/", 1)[-1].strip())
            else:
                _collect(value, out)
    elif isinstance(node, list):
        for item in node:
            _collect(item, out)


def claim_named_in(envelope):
    try:
        from care.nhcx.models import Claim

        values: list = []
        _collect((envelope or {}).get("fhir"), values)
        candidates = [v for v in dict.fromkeys(values) if v]
        if not candidates:
            return None
        held = {
            c.claim_no: c for c in Claim.objects.filter(claim_no__in=candidates[:500])
        }
        for v in candidates:
            if v in held:
                return held[v]
    except Exception:
        logger.exception("nhcx: claim_named_in failed")
    return None


# ---- routing ----


def _handler(name):
    try:
        module = importlib.import_module(f"care.nhcx.callbacks.{name}")
    except ImportError as e:
        if getattr(e, "name", "") and not e.name.endswith(name):
            raise
        return None
    return getattr(module, "handle", None)


def _call(name, envelope, corr, delivery, **extra) -> dict:
    fn = _handler(name)
    if fn is None:
        return result(UNMATCHED, f"no handler for {name}")
    d = dict(delivery or {})
    d["correlation_id"] = corr
    d.update(extra)
    return _as_result(fn(envelope, d))


def _enquiry_waits(corr) -> bool:
    from care.nhcx.models import ClaimEnquiry

    return ClaimEnquiry.objects.filter(correlation_id=corr).exists()


def route(type_, envelope, corr, delivery=None) -> dict:  # noqa: PLR0911
    if type_ == "payment":
        return _call("payment", envelope, corr, delivery)
    if type_ == "communication":
        return _call("communication", envelope, corr, delivery)
    if not corr:
        return result(UNMATCHED, "no correlation id")
    if type_ in {"status", "task"} and _enquiry_waits(corr):
        return _call("enquiry", envelope, corr, delivery, route="C8")
    if type_ == "status":
        return result(UNMATCHED)
    if type_ == "insurance":
        return _call("plan", envelope, corr, delivery)
    if type_ == "preauth":
        return _call("preauth", envelope, corr, delivery)
    if type_ == "task":
        return _call("enquiry", envelope, corr, delivery, route="C7")
    if type_ == "claim":
        return _call("claim", envelope, corr, delivery)
    if type_ == "coverage":
        return _call("eligibility", envelope, corr, delivery)
    return result(IGNORED, f"type {type_} is not handled")


def _accept(envelope, delivery) -> dict:
    type_ = delivery.get("type")
    if delivery.get("payload_kind") == "json" or type_ not in TYPES:
        return result(IGNORED)
    h = envelope.get("jwe_headers")
    corr = h.get("x-hcx-correlation_id") if isinstance(h, dict) else None
    corr = str(corr).strip() if corr else ""
    claim = None
    try:
        claim = claim_for_correlation(corr) or claim_named_in(envelope)
    except Exception:
        logger.exception("nhcx: matching for the archive failed corr=%s", corr)
    handle = archive.archive_inbound(
        claim,
        envelope,
        type_,
        delivery.get("flow"),
        corr,
        delivery.get("participant"),
        delivery.get("redelivery"),
    )
    out = route(type_, envelope, corr, delivery)
    archive.archive_note(handle, out["outcome"])
    logger.info(
        "nhcx: received %s claim=%s correlation=%s api_call=%s outcome=%s %s",
        type_,
        getattr(claim, "claim_no", None),
        corr,
        delivery.get("api_call_id"),
        out["outcome"],
        out.get("detail") or "",
    )
    return out


def receive(envelope, delivery=None) -> dict:
    try:
        if not isinstance(envelope, dict):
            raise Rejected("Expected a JSON object.")
        return _accept(envelope, dict(delivery or {}))
    except Rejected as why:
        return result(REJECTED, why.detail)
    except Exception as why:
        logger.exception("nhcx: receive failed")
        return result(ERROR, str(why) or type(why).__name__)
