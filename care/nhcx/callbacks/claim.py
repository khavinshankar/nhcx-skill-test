"""C6. Claim reply (D20)."""

from __future__ import annotations

from django.utils import timezone

from care.nhcx.callbacks import _legs, dispatch
from care.nhcx.models import ClaimSubmission


def claim_door_refusal(row, message) -> dict:
    values = {"status": "error", "error_message": message}
    if row.submission_kind == "claim_query_response":
        values["status"] = "queried"
        values["disposition"] = row.disposition or row.query_note
    if row.thread_correlation_id:
        values["correlation_id"] = row.thread_correlation_id
    return values


def handle(envelope, delivery=None):
    corr = _legs.corr_of(delivery, envelope)
    row = (
        ClaimSubmission.objects.filter(correlation_id=corr)
        .order_by("-created_date", "-id")
        .first()
        if corr
        else None
    )
    if row is None:
        return _legs.result(dispatch.UNMATCHED, "No claim is waiting on this reply.")
    body = dispatch.payload(envelope)
    if _legs.is_protocol(body):
        dispatch.leg_write(row, **claim_door_refusal(row, dispatch.rejection(body)))
        return _legs.result(dispatch.SETTLED, "refused at the door")
    parsed = _legs.read_claim_response(envelope, body)
    call_id = _legs.api_call_id(envelope)
    if dispatch.already_applied(row, call_id, parsed):
        return _legs.result(dispatch.IGNORED, "already applied")
    dispatch.revive(row, "submitting")
    status = parsed.get("status") or ""
    if status == "error":
        dispatch.leg_write(
            row,
            **claim_door_refusal(row, _legs.error_text(parsed)),
            api_call_id=call_id or None,
            response_json=body,
        )
        return _legs.result(dispatch.SETTLED, "error")
    dispatch.leg_write(
        row,
        **_legs.parsed_values(parsed),
        status=status,
        api_call_id=call_id or None,
        settled_at=None if status == "submitting" else timezone.now(),
        error_message=None,
        response_json=body,
        thread_correlation_id=row.correlation_id,
    )
    return _legs.result(dispatch.SETTLED, status)
