"""A10 to A13: poll each waiting leg through the G9 ledger (in-process).

A reply found in the ledger is applied through C1 ``route`` with the leg's
correlation id, so the matching, dedupe and revive rules are the callbacks'.

Public:
- ``poll_all(claim) -> poll_notes`` (A17 order; a failing poll adds its text)
- ``poll_eligibility``, ``poll_plan``, ``poll_ruling``, ``poll_preauth``,
  ``poll_predetermination(row)``, ``poll_claim``, ``poll_cancel``,
  ``poll_enquiry(row)``: each returns True when it changed something.
- ``find_reply``, ``task_replies``, ``peer_dispatch_error``,
  ``protocol_rejection``, ``nhcx_refusal`` (A11 to A13 helpers).
"""

import logging
from dataclasses import dataclass
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from care.nhcx.callbacks import dispatch
from care.nhcx.gateway import get_gateway
from care.nhcx.gateway.errors import GatewayError
from care.nhcx.services import stage
from care.nhcx.services.common import facility_profile

logger = logging.getLogger(__name__)

NOT_FOUND_CODES = {"TXN_NOT_FOUND", "LEDGER_DISABLED"}
CANCEL_REFUSED = "The payer did not accept the cancellation."
CANCEL_GRACE = timedelta(minutes=15)
PROTOCOL_SCAN = 20
CANCEL_GONE = (
    "The gateway no longer has the cancel transaction, its ledger was reset after "
    "it was sent. Cancel again."
)
PEER_PREFIX = "The payer answered, but NHCX refused its reply"
PEER_SUFFIX = (
    " Nothing more will arrive on this thread, submit again to open a new one."
)
DISPATCH_FAILED = "Dispatch to NHCX failed."


def _gone(after: str, again: str) -> str:
    return (
        "The gateway no longer has this transaction, its ledger was reset after "
        f"{after} was sent. {again}"
    )


@dataclass(frozen=True)
class Leg:
    name: str
    waiting: str
    resource: str
    route_type: str
    scan_type: str
    sent_field: str
    not_found: str
    peer_check: bool
    own_check: bool


LEGS = {
    "eligibility": Leg(
        "eligibility",
        "checking",
        "CoverageEligibilityResponse",
        "coverage",
        "coverageeligibility",
        "checked_at",
        _gone("the check", "Send the eligibility check again."),
        peer_check=False,
        own_check=True,
    ),
    "plan": Leg(
        "plan",
        "fetching",
        "InsurancePlan",
        "insurance",
        "insuranceplan",
        "requested_at",
        _gone("the request", "Fetch again."),
        peer_check=False,
        own_check=True,
    ),
    "ruling": Leg(
        "ruling",
        "checking",
        "CoverageEligibilityResponse",
        "coverage",
        "coverageeligibility",
        "requested_at",
        _gone("the check", "Check again."),
        peer_check=False,
        own_check=True,
    ),
    "preauth": Leg(
        "preauth",
        "submitting",
        "ClaimResponse",
        "preauth",
        "preauth",
        "submitted_at",
        _gone("the preauth", "Submit again."),
        peer_check=True,
        own_check=True,
    ),
    "predetermination": Leg(
        "predetermination",
        "asking",
        "ClaimResponse",
        "preauth",
        "preauth",
        "requested_at",
        "The gateway no longer has this transaction. Ask again.",
        peer_check=True,
        own_check=False,
    ),
    "claim": Leg(
        "claim",
        "submitting",
        "ClaimResponse",
        "claim",
        "claim",
        "submitted_at",
        _gone("the claim", "Submit again."),
        peer_check=True,
        own_check=True,
    ),
    "enquiry": Leg(
        "enquiry",
        "asking",
        "Task",
        "task",
        "task",
        "requested_at",
        "The gateway no longer has this transaction. Ask again.",
        peer_check=True,
        own_check=False,
    ),
}


def _s(v) -> str:
    return "" if v is None else str(v).strip()


def _ledger():
    return get_gateway().ledger


def _own_code(claim) -> str:
    profile = facility_profile(claim.facility)
    return _s(profile.participant_code).lower() if profile else ""


def _claim_of(row):
    from care.nhcx.models import Claim

    return row if isinstance(row, Claim) else row.claim


def _bundle_of(envelope) -> dict | None:
    if not isinstance(envelope, dict):
        return None
    body = envelope.get("fhir")
    if body is None:
        body = envelope.get("payload")
    return body if isinstance(body, dict) else None


def _has(bundle, resource_type) -> bool:
    for e in bundle.get("entry") or []:
        if (
            isinstance(e, dict)
            and isinstance(e.get("resource"), dict)
            and e["resource"].get("resourceType") == resource_type
        ):
            return True
    return False


# ---- A12 ----


def find_reply(related, resource_type, own: str):
    ledger = _ledger()
    for entry in related or []:
        if entry.get("direction") != "in" or _s(entry.get("sender")).lower() == own:
            continue
        envelope = ledger.fhir(entry["id"])
        bundle = _bundle_of(envelope)
        if bundle is not None and _has(bundle, resource_type):
            return envelope, bundle
    return None


def task_replies(related, own: str) -> list:
    ledger = _ledger()
    seen, out = set(), []
    for entry in related or []:
        if _s(entry.get("sender")).lower() == own:
            continue
        key = entry.get("api_call_id") or entry.get("id")
        if key in seen:
            continue
        seen.add(key)
        envelope = ledger.fhir(entry["id"])
        bundle = _bundle_of(envelope)
        if bundle is not None and _has(bundle, "Task"):
            out.append((envelope, bundle))
    return out


# ---- A11 ----


def nhcx_refusal(entry_id) -> str | None:
    try:
        entry = _ledger().get(entry_id)
    except GatewayError:
        return None
    peer = (entry or {}).get("peer") if isinstance(entry, dict) else None
    response = peer.get("response") if isinstance(peer, dict) else None
    err = response.get("error") if isinstance(response, dict) else None
    if isinstance(err, dict) and err.get("code"):
        return f"{err['code']}: {err.get('message') or 'NHCX refused the request.'}"
    return None


def peer_dispatch_error(related, own_txn_id) -> str | None:
    for entry in related or []:
        if (
            entry.get("direction") != "out"
            or entry.get("id") == own_txn_id
            or entry.get("status") not in ("failed", "rejected")
        ):
            continue
        try:
            disp = _ledger().dispatch(entry["id"])
        except GatewayError:
            disp = None
        detail = nhcx_refusal(entry["id"])
        if not detail and isinstance(disp, dict):
            detail = disp.get("errorMessage") or disp.get("errorCode") or ""
        if detail:
            return f"{PEER_PREFIX}: {str(detail)[:300]}{PEER_SUFFIX}"
        return f"{PEER_PREFIX}.{PEER_SUFFIX}"
    return None


def own_dispatch_error_enquiry(txn_id) -> str | None:
    try:
        disp = _ledger().dispatch(txn_id)
    except GatewayError:
        return None
    if disp.get("status") != "dispatch_failed":
        return None
    return (
        nhcx_refusal(txn_id)
        or disp.get("errorMessage")
        or disp.get("errorCode")
        or DISPATCH_FAILED
    )


# ---- A13 ----


def _at(value):
    if not value:
        return None
    if hasattr(value, "tzinfo"):
        return value
    try:
        return parse_datetime(str(value))
    except (TypeError, ValueError):
        return None


def protocol_rejection(correlation_id, since, kind) -> str | None:
    if not _s(correlation_id):
        return None
    ledger = _ledger()
    try:
        rows = ledger.list()
    except GatewayError:
        return None
    since = _at(since)
    candidates = []
    for r in rows or []:
        if r.get("direction") != "in" or r.get("type") != kind:
            continue
        created = _at(r.get("created_at"))
        if since is not None and created is not None and created < since:
            continue
        candidates.append(r)
        if len(candidates) >= PROTOCOL_SCAN:
            break
    for entry in candidates:
        try:
            envelope = ledger.fhir(entry["id"])
        except GatewayError:
            continue
        body = envelope.get("fhir") if isinstance(envelope, dict) else None
        if (
            isinstance(body, dict)
            and body.get("type") == "ProtocolResponse"
            and body.get("x-hcx-correlation_id") == correlation_id
            and body.get("x-hcx-status") == "response.error"
        ):
            details = body.get("x-hcx-error_details")
            details = details if isinstance(details, dict) else {}
            code = details.get("code") or "NHCX"
            message = details.get("message") or "The gateway rejected the request."
            return f"{code}: {message}"
    return None


# ---- writes ----


def _write(row, **values) -> None:
    with transaction.atomic():
        for k, v in values.items():
            setattr(row, k, v)
        row.save()
        if row.__class__.__name__ in ("ClaimPreauth", "ClaimSubmission", "Claim"):
            claim = _claim_of(row)
            claim.refresh_from_db()
            stage.recompute(claim)


def write_refusal(leg: Leg, row, message: str) -> None:
    if leg.name == "preauth":
        values = {
            "error_message": message,
            "status": "approved"
            if row.submission_kind in ("enhancement", "enhancement_resubmit")
            else "error",
        }
        if row.thread_correlation_id:
            values["correlation_id"] = row.thread_correlation_id
        _write(row, **values)
    elif leg.name == "claim":
        values = {"error_message": message, "status": "error"}
        if row.thread_correlation_id:
            values["correlation_id"] = row.thread_correlation_id
        if row.submission_kind == "claim_query_response":
            values["status"] = "queried"
            values["disposition"] = row.disposition or row.query_note
        _write(row, **values)
    else:
        _write(row, status="error", error_message=message)
    logger.info(
        "nhcx: poll %s refused claim=%s correlation=%s txn=%s: %s",
        leg.name,
        getattr(_claim_of(row), "claim_no", None),
        row.correlation_id,
        row.txn_id,
        message,
    )


# ---- A10 ----


def _claim_already_applied(row, envelope, bundle) -> bool:
    headers = envelope.get("jwe_headers") if isinstance(envelope, dict) else None
    api_call_id = _s((headers or {}).get("x-hcx-api_call_id"))
    if api_call_id:
        return _s(row.api_call_id) == api_call_id
    if row.status == "submitting":
        return False
    try:
        from care.nhcx.fhir.read import claim_response

        parsed = claim_response.read(bundle)
    except Exception:
        return False
    return dispatch.already_applied(row, "", parsed)


def poll(leg: Leg, row) -> bool:  # noqa: PLR0911
    if row is None or row.status != leg.waiting or not _s(row.txn_id):
        return False
    claim = _claim_of(row)
    ledger = _ledger()
    try:
        related = ledger.related(row.txn_id)
    except GatewayError as e:
        if e.code in NOT_FOUND_CODES:
            _write(row, status="error", error_message=leg.not_found)
            return True
        raise
    found = find_reply(related, leg.resource, _own_code(claim))
    if found is not None:
        envelope, bundle = found
        if leg.name == "claim" and _claim_already_applied(row, envelope, bundle):
            return False
        env = {"jwe_headers": envelope.get("jwe_headers") or {}, "fhir": bundle}
        out = dispatch.route(leg.route_type, env, row.correlation_id)
        logger.info(
            "nhcx: poll %s applied claim=%s correlation=%s outcome=%s",
            leg.name,
            claim.claim_no,
            row.correlation_id,
            out.get("outcome"),
        )
        if out.get("outcome") == dispatch.ERROR:
            raise RuntimeError(out.get("detail") or "applying the reply failed")
        return out.get("outcome") == dispatch.SETTLED
    error = None
    if leg.peer_check:
        error = peer_dispatch_error(related, row.txn_id)
    if not error:
        error = protocol_rejection(
            row.correlation_id, getattr(row, leg.sent_field, None), leg.scan_type
        )
    if not error and leg.name == "enquiry":
        error = own_dispatch_error_enquiry(row.txn_id)
    if error:
        write_refusal(leg, row, error)
        return True
    if leg.own_check:
        disp = ledger.dispatch(row.txn_id)
        if disp.get("status") == "dispatch_failed":
            write_refusal(
                leg,
                row,
                disp.get("errorMessage") or disp.get("errorCode") or DISPATCH_FAILED,
            )
            return True
    return False


def _one(claim, name):
    try:
        return getattr(claim, name)
    except Exception:
        return None


def poll_eligibility(claim) -> bool:
    return poll(LEGS["eligibility"], claim)


def poll_plan(claim) -> bool:
    return poll(LEGS["plan"], _one(claim, "plan"))


def poll_ruling(claim) -> bool:
    return poll(LEGS["ruling"], _one(claim, "auth"))


def poll_preauth(claim) -> bool:
    return poll(LEGS["preauth"], _one(claim, "preauth"))


def poll_claim(claim) -> bool:
    return poll(LEGS["claim"], _one(claim, "submission"))


def poll_predetermination(row) -> bool:
    return poll(LEGS["predetermination"], row)


def poll_enquiry(row) -> bool:
    return poll(LEGS["enquiry"], row)


def _is_acceptance(envelope, bundle) -> bool:
    try:
        from care.nhcx.callbacks import enquiry
    except ImportError:
        enquiry = None
    if enquiry is not None and hasattr(enquiry, "is_cancel_acceptance"):
        return bool(enquiry.is_cancel_acceptance(envelope, bundle))
    from care.nhcx.fhir.read import claim_response

    parsed = claim_response.read_task_reply(bundle, "cancel")
    if "accepted" in parsed:
        return bool(parsed["accepted"])
    return (parsed.get("task_status") or "") in ("", "completed", "accepted") and (
        parsed.get("outcome") or ""
    ).lower() != "error"


def poll_cancel(claim) -> bool:  # noqa: PLR0911
    row = _one(claim, "preauth")
    if row is None or not _s(row.cancel_txn_id):
        return False
    refused = (
        row.status == "approved"
        and row.error_message == CANCEL_REFUSED
        and row.settled_at is not None
        and timezone.now() - row.settled_at < CANCEL_GRACE
    )
    if row.status != "cancelling" and not refused:
        return False
    try:
        related = _ledger().related(row.cancel_txn_id)
    except GatewayError as e:
        if e.code in NOT_FOUND_CODES:
            if refused:
                return False
            _write(row, status="error", error_message=CANCEL_GONE)
            return True
        raise
    corr = row.cancel_correlation_id
    replies = task_replies(related, _own_code(claim))

    def apply(envelope, bundle):
        env = {"jwe_headers": envelope.get("jwe_headers") or {}, "fhir": bundle}
        out = dispatch.route("task", env, corr)
        if out.get("outcome") == dispatch.ERROR:
            raise RuntimeError(out.get("detail") or "applying the reply failed")
        return out.get("outcome") == dispatch.SETTLED

    for envelope, bundle in replies:
        if _is_acceptance(envelope, bundle):
            return apply(envelope, bundle)
    if refused:
        return False
    if replies:
        return apply(*replies[0])
    error = protocol_rejection(corr, row.cancel_requested_at, "task")
    if error:
        _write(row, status="error", error_message=error)
        return True
    return False


def poll_all(claim) -> list:
    """Run every poll once, in A17 order; returns poll_notes."""
    notes: list = []

    def run(fn, *args):
        try:
            fn(*args)
        except Exception as e:
            logger.warning(
                "nhcx: poll %s failed claim=%s: %s", fn.__name__, claim.claim_no, e
            )
            notes.append(str(e) or type(e).__name__)

    if claim.status == "checking":
        run(poll_eligibility, claim)
    run(poll_plan, claim)
    run(poll_ruling, claim)
    run(poll_claim, claim)
    run(poll_preauth, claim)
    for row in list(claim.predeterminations.filter(status="asking").order_by("id")):
        run(poll_predetermination, row)
    run(poll_cancel, claim)
    for row in list(claim.enquiries.filter(status="asking").order_by("id")):
        run(poll_enquiry, row)
    claim.refresh_from_db()
    return notes
