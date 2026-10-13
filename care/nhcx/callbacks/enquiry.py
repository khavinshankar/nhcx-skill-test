"""C7 (cancel answer, D18) and C8 (status / reprocess / release answer, D29)."""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from care.nhcx.callbacks import _legs, dispatch
from care.nhcx.fhir import bundle as fb
from care.nhcx.fhir.read import claim_response as cr
from care.nhcx.models import ClaimEnquiry, ClaimPreauth, ClaimSubmission
from care.nhcx.models.claim import allocate_claim_no

REFUSED = "The payer did not accept the cancellation."
REOPENED = ("completed", "accepted", "in-progress")


def handle(envelope, delivery=None):
    corr = _legs.corr_of(delivery, envelope)
    route = (delivery or {}).get("route")
    if route == "C8":
        return answer(envelope, corr)
    if route == "C7":
        return cancel(envelope, corr)
    if corr and ClaimEnquiry.objects.filter(correlation_id=corr).exists():
        return answer(envelope, corr)
    return cancel(envelope, corr)


# C7


def _accepted(parsed) -> bool:
    return (parsed.get("task_status") or "") in ("", "completed", "accepted") and (
        parsed.get("outcome") or ""
    ).lower() != "error"


def claim_prefix(claim_no) -> str:
    head = (claim_no or "").split("-", 1)[0]
    return head or "NM"


def cancel(envelope, corr):
    row = (
        ClaimPreauth.objects.filter(cancel_correlation_id=corr)
        .order_by("-created_date", "-id")
        .first()
        if corr
        else None
    )
    if row is None:
        return _legs.result(
            dispatch.UNMATCHED, "No cancellation is waiting on this reply."
        )
    refused = row.status != "cancelling" and row.error_message == REFUSED
    if row.status != "cancelling" and not refused and not dispatch.failed_send(row):
        return _legs.result(dispatch.IGNORED, "The cancellation was already answered.")
    body = dispatch.payload(envelope)
    if _legs.is_protocol(body):
        if refused:
            return _legs.result(dispatch.IGNORED, "already refused")
        dispatch.leg_write(
            row,
            status=row.pre_cancel_status or "approved",
            error_message=dispatch.rejection(body),
        )
        return _legs.result(dispatch.SETTLED, "refused at the door")
    parsed = _legs.read_task_reply(envelope, body, "cancel")
    ok = _accepted(parsed)
    if refused and not ok:
        return _legs.result(dispatch.IGNORED, "already refused")
    dispatch.revive(row, "cancelling")
    response = parsed.get("response") or {}
    with transaction.atomic():
        dispatch.leg_write(
            row,
            status="cancelled" if ok else (row.pre_cancel_status or "approved"),
            settled_at=timezone.now(),
            disposition=parsed.get("detail") or response.get("disposition") or "",
            outcome=parsed.get("outcome") or "",
            error_message=None if ok else REFUSED,
            response_json=body,
        )
        if ok:
            claim = row.claim
            if not row.claim_ref:
                row.claim_ref = claim.claim_no
                row.save(update_fields=["claim_ref", "modified_date"])
            claim.claim_no = allocate_claim_no(claim_prefix(claim.claim_no))
            claim.save(update_fields=["claim_no", "modified_date"])
    return _legs.result(dispatch.SETTLED, "cancelled" if ok else "refused")


# C8


def status_answer(envelope, body) -> dict:
    headers = _legs.headers(envelope)
    header = cr._status_header(headers)  # noqa: SLF001
    answer_text = str(header.get("entity_status") or "")
    detail = ""
    task = fb.find_resource(fb.unwrap(body), "Task") if isinstance(body, dict) else None
    if task:
        for output in task.get("output") or []:
            codes = [
                c.get("code") for c in (output.get("type") or {}).get("coding") or []
            ]
            if "claimStatus" in codes and output.get("valueString"):
                answer_text = answer_text or output["valueString"]
        if task.get("status") == "rejected":
            answer_text = answer_text or "not-found"
        detail = task.get("description") or ""
    if header:
        parts = [
            f"{key}: {header[key]}"
            for key in ("stage", "outcome", "total_approved", "total_paid")
            if header.get(key) not in (None, "")
        ]
        detail = "; ".join(p for p in (detail, "; ".join(parts)) if p)
    return {"answer": answer_text or "unknown", "detail": detail}


def _task_reason(body) -> str:
    task = fb.find_resource(fb.unwrap(body), "Task") or {}
    reason = task.get("statusReason") or {}
    text = reason.get("text") or ""
    if not text:
        for coding in reason.get("coding") or []:
            text = coding.get("display") or coding.get("code") or ""
            if text:
                break
    return text


def answer(envelope, corr):
    row = (
        ClaimEnquiry.objects.filter(correlation_id=corr)
        .order_by("-created_date", "-id")
        .first()
        if corr
        else None
    )
    if row is None:
        return _legs.result(dispatch.UNMATCHED, "No enquiry is waiting on this reply.")
    if row.status != "asking" and not dispatch.failed_send(row):
        return _legs.result(dispatch.IGNORED, "The enquiry was already answered.")
    body = dispatch.payload(envelope)
    if _legs.is_protocol(body):
        row.status = "error"
        row.error_message = dispatch.rejection(body)
        row.save(update_fields=["status", "error_message", "modified_date"])
        return _legs.result(dispatch.SETTLED, "refused at the door")
    values = {
        "status": "answered",
        "answered_at": timezone.now(),
        "error_message": None,
        "response_json": body,
    }
    if row.kind == "status":
        dispatch.revive(row, "asking")
        values.update(status_answer(envelope, body))
    else:
        parsed = _legs.read_task_reply(envelope, body, row.kind)
        dispatch.revive(row, "asking")
        reopened = (parsed.get("task_status") or "") in REOPENED
        values["answer"] = "reopened" if reopened else "refused"
        response = parsed.get("response") or {}
        detail = parsed.get("detail") or ""
        if not reopened:
            reason = _task_reason(body) or (response.get("error_message") or "")
            if reason and reason not in detail:
                detail = f"{detail}; {reason}" if detail else reason
        values["detail"] = detail
        if reopened:
            submission = ClaimSubmission.objects.filter(claim_id=row.claim_id).first()
            if submission is not None:
                dispatch.leg_write(
                    submission, status="submitting", settled_at=None, error_message=None
                )
    for key, value in values.items():
        setattr(row, key, value)
    row.save()
    return _legs.result(dispatch.SETTLED, values.get("answer") or "answered")
