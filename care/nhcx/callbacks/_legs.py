"""Helpers shared by the leg callbacks (C5 to C10).

The C1 shared rules (payload, rejection, failed_send, revive, leg_write,
already_applied) live in ``callbacks.dispatch``; this module adds the reading
helpers the leg callbacks have in common.
"""

from __future__ import annotations

from care.nhcx.callbacks import dispatch
from care.nhcx.fhir import bundle as fb
from care.nhcx.fhir.read import claim_response as cr

NO_CLAIM_RESPONSE = "The payer reply carries no ClaimResponse."
NO_TASK = "The payer reply carries no Task."
NO_REASON = "The payer answered with an error and gave no reason"
PARSED_COLUMNS = (
    "outcome",
    "adjudication",
    "disposition",
    "preauth_ref",
    "approved_amount",
    "eligible_amount",
    "submitted_amount",
    "items_json",
    "query_note",
)


def headers(envelope) -> dict:
    value = (envelope or {}).get("jwe_headers")
    return value if isinstance(value, dict) else {}


def header(envelope, name) -> str:
    value = headers(envelope).get(name)
    return str(value) if value not in (None, "") else ""


def result(outcome, detail=""):
    return {"outcome": outcome, "detail": detail}


def is_protocol(body) -> bool:
    return fb.is_protocol_response(body)


def read_claim_response(envelope, body) -> dict:
    """F9 fields of the reply's first ClaimResponse; Rejected when it has none."""
    if fb.find_resource(fb.unwrap(body), "ClaimResponse") is None:
        raise dispatch.Rejected(NO_CLAIM_RESPONSE)
    parsed = cr.read(
        body,
        workflow_id=header(envelope, "x-hcx-workflow_id") or None,
        status_header=header(envelope, "x-hcx-status") or None,
    )
    parsed.setdefault("outcome", "")
    parsed.setdefault("adjudication", "")
    return parsed


def error_text(parsed) -> str:
    lines = [
        line
        for line in (parsed.get("error_message") or "").splitlines()
        if line.strip() and line.strip().lower() != "ok"
    ]
    return "\n".join(lines) or NO_REASON


def parsed_values(parsed, *, keep_preauth_ref=False) -> dict:
    values = {key: parsed.get(key) for key in PARSED_COLUMNS}
    for key in ("outcome", "adjudication", "disposition", "query_note"):
        values[key] = values[key] or ""
    values["preauth_ref"] = values["preauth_ref"] or ""
    if keep_preauth_ref and not values["preauth_ref"]:
        values.pop("preauth_ref")
    return values


def read_task_reply(envelope, body, action) -> dict:
    """F10 answer; Rejected when the bundle carries no Task."""
    if fb.find_resource(fb.unwrap(body), "Task") is None:
        raise dispatch.Rejected(NO_TASK)
    return cr.read_task_reply(body, action, headers(envelope))


def corr_of(delivery, envelope=None) -> str:
    corr = (delivery or {}).get("correlation_id") or ""
    if not corr and envelope is not None:
        corr = header(envelope, "x-hcx-correlation_id")
    return str(corr or "")


def api_call_id(envelope) -> str:
    return header(envelope, "x-hcx-api_call_id")
