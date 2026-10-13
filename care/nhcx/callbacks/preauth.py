"""C5. Pre-authorisation reply (and the predetermination quote, D19)."""

from __future__ import annotations

from django.utils import timezone

from care.nhcx.callbacks import _legs, dispatch
from care.nhcx.models import ClaimPreauth, ClaimPredetermination

ENHANCEMENT_KINDS = ("enhancement", "enhancement_resubmit")


def door_refusal(row, message) -> dict:
    values = {"status": "error", "error_message": message}
    if row.submission_kind in ENHANCEMENT_KINDS:
        values["status"] = "approved"
    if row.thread_correlation_id:
        values["correlation_id"] = row.thread_correlation_id
    return values


def handle(envelope, delivery=None):  # noqa: PLR0911
    corr = _legs.corr_of(delivery, envelope)
    row = (
        ClaimPreauth.objects.filter(correlation_id=corr)
        .order_by("-created_date", "-id")
        .first()
        if corr
        else None
    )
    if row is None:
        return quote(envelope, corr)
    if row.status == "cancelled":
        return _legs.result(dispatch.IGNORED, "The pre-authorisation is cancelled.")
    body = dispatch.payload(envelope)
    if _legs.is_protocol(body):
        dispatch.leg_write(row, **door_refusal(row, dispatch.rejection(body)))
        return _legs.result(dispatch.SETTLED, "refused at the door")
    parsed = _legs.read_claim_response(envelope, body)
    call_id = _legs.api_call_id(envelope)
    if row.status == "cancelling":
        if parsed.get("adjudication") == "cancelled":
            dispatch.leg_write(
                row,
                status="cancelled",
                settled_at=timezone.now(),
                error_message=None,
                outcome=parsed.get("outcome") or "",
                adjudication=parsed.get("adjudication") or "",
                disposition=parsed.get("disposition") or "",
                api_call_id=call_id or None,
                response_json=body,
            )
            return _legs.result(dispatch.SETTLED, "cancelled")
        return _legs.result(
            dispatch.IGNORED, "The pre-authorisation is being cancelled."
        )
    if dispatch.already_applied(row, call_id, parsed):
        return _legs.result(dispatch.IGNORED, "already applied")
    dispatch.revive(row, "submitting")
    status = parsed.get("status") or ""
    if status == "error":
        dispatch.leg_write(
            row,
            **door_refusal(row, _legs.error_text(parsed)),
            api_call_id=call_id or None,
            response_json=body,
        )
        return _legs.result(dispatch.SETTLED, "error")
    if status == "rejected" and row.submission_kind in ENHANCEMENT_KINDS:
        kept = (
            "partial"
            if (row.outcome == "partial" and row.adjudication == "approved")
            else "approved"
        )
        dispatch.leg_write(
            row,
            status=kept,
            error_message=parsed.get("query_note") or parsed.get("disposition") or "",
            api_call_id=call_id or None,
            response_json=body,
        )
        return _legs.result(dispatch.SETTLED, "enhancement denied")
    values = _legs.parsed_values(parsed, keep_preauth_ref=True)
    dispatch.leg_write(
        row,
        **values,
        status=status,
        api_call_id=call_id or None,
        settled_at=None if status == "submitting" else timezone.now(),
        error_message=None,
        response_json=body,
        thread_correlation_id=row.correlation_id,
    )
    return _legs.result(dispatch.SETTLED, status)


def quote(envelope, corr):
    row = (
        ClaimPredetermination.objects.filter(correlation_id=corr)
        .order_by("-created_date", "-id")
        .first()
        if corr
        else None
    )
    if row is None:
        return _legs.result(dispatch.UNMATCHED, "No leg is waiting on this reply.")
    if row.status != "asking" and not dispatch.failed_send(row):
        return _legs.result(dispatch.IGNORED, "The quote was already answered.")
    body = dispatch.payload(envelope)
    if _legs.is_protocol(body):
        row.status = "error"
        row.error_message = dispatch.rejection(body)
        row.save(update_fields=["status", "error_message", "modified_date"])
        return _legs.result(dispatch.SETTLED, "refused at the door")
    dispatch.revive(row, "asking")
    parsed = _legs.read_claim_response(envelope, body)
    row.status = "answered"
    row.answered_at = timezone.now()
    row.error_message = None
    row.outcome = parsed.get("outcome") or ""
    row.adjudication = parsed.get("adjudication") or ""
    row.disposition = parsed.get("disposition") or ""
    row.allowed_amount = parsed.get("approved_amount")
    row.response_json = body
    row.save()
    return _legs.result(dispatch.SETTLED, "answered")
