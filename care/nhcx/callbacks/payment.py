"""C10. Payment notice (D21, D22); acknowledged through A8 once recorded."""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from care.nhcx.callbacks import _legs, dispatch
from care.nhcx.fhir.inputs import FhirBuildError
from care.nhcx.fhir.read import payment as f13
from care.nhcx.models import (
    Claim,
    ClaimPayment,
    ClaimPaymentDetail,
    ClaimPreauth,
    ClaimSubmission,
)
from care.nhcx.services import stage

NOTICE_COLUMNS = (
    "claim_ref",
    "notice_id",
    "disposition",
    "payment_status",
    "payment_date",
    "amount",
    "currency",
    "utr",
)


def claim_for_reference(ref):
    if not ref:
        return None
    claim = Claim.objects.filter(claim_no=ref).first()
    if claim is not None:
        return claim
    for model in (ClaimSubmission, ClaimPreauth):
        row = model.objects.filter(claim_ref=ref).order_by("-created_date").first()
        if row is not None:
            return row.claim
    return None


def handle(envelope, delivery=None):
    corr = _legs.corr_of(delivery, envelope)
    body = dispatch.payload(envelope)
    try:
        notice = f13.read(body)
    except FhirBuildError as e:
        raise dispatch.Rejected(str(e)) from e
    if corr and ClaimPayment.objects.filter(correlation_id=corr).exists():
        return _legs.result(dispatch.IGNORED, "already recorded")
    claim = claim_for_reference(notice["claim_ref"])
    if claim is None:
        return _legs.result(dispatch.UNMATCHED, "No case answers to this number.")
    values = {key: notice.get(key) for key in NOTICE_COLUMNS}
    for key in ("notice_id", "payment_status", "utr", "claim_ref"):
        values[key] = values[key] or None
    values["payment_date"] = values["payment_date"] or None
    values.update(
        correlation_id=corr or None,
        sender_code=_legs.header(envelope, "x-hcx-sender_code") or None,
        workflow_id=_legs.header(envelope, "x-hcx-workflow_id") or None,
        received_at=timezone.now(),
        notice_json=body,
    )
    earlier = (
        ClaimPayment.objects.filter(claim=claim, notice_id=notice["notice_id"])
        .order_by("-id")
        .first()
        if notice["notice_id"]
        else None
    )
    with transaction.atomic():
        if earlier is not None:
            dispatch.leg_write(
                earlier,
                **values,
                ack_status="pending",
                ack_txn_id=None,
                ack_correlation_id=None,
                acknowledged_at=None,
                ack_error=None,
            )
            ClaimPaymentDetail.objects.filter(payment=earlier).delete()
            money = earlier
        else:
            money = ClaimPayment.objects.create(claim=claim, **values)
            stage.recompute(claim)
        ClaimPaymentDetail.objects.bulk_create(
            [
                ClaimPaymentDetail(
                    payment=money,
                    seq=d["seq"],
                    reference=d["reference"] or None,
                    type_code=d["type_code"] or None,
                    type_display=d["type_display"] or None,
                    date=d["date"] or None,
                    amount=d["amount"],
                )
                for d in notice["details"]
            ]
        )
    from care.nhcx.services import payment

    transaction.on_commit(lambda: payment.auto_acknowledge(money.id))
    return _legs.result(dispatch.SETTLED, "updated" if earlier else "recorded")
