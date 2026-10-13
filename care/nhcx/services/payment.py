"""A8. Acknowledge a payment notice (D21)."""

from __future__ import annotations

import logging

from django.utils import timezone

from care.nhcx.fhir.build import payment_ack
from care.nhcx.models import ClaimPayment
from care.nhcx.services import common, payers, stage

logger = logging.getLogger("care.nhcx")

PATH = "v1/paymentnotice/on_request"
NOT_FOUND = "Payment notice not found."
SETTINGS = "Set the facility's HFR ID and NHCX participant code under Settings first."


def _s(value) -> str:
    return "" if value is None else str(value).strip()


def _write(money, **values):
    for key, value in values.items():
        setattr(money, key, value)
    money.save(update_fields=[*values.keys(), "modified_date"])
    stage.recompute(money.claim)


def acknowledge_payment(payment_id, *, claim=None) -> ClaimPayment:
    rows = ClaimPayment.objects.select_related("claim", "claim__facility")
    if claim is not None:
        rows = rows.filter(claim=claim)
    money = rows.filter(id=payment_id).first() if payment_id else None
    if money is None:
        raise common.ServiceRefusal(NOT_FOUND)
    case = money.claim
    try:
        facility = common.facility_input(case.facility)
        if not facility.identifier_value or not facility.participant_code:
            raise common.ServiceRefusal(SETTINGS)
        claim_no = _s(money.claim_ref) or case.claim_no
        bundle = payment_ack.build(claim_no, facility, common.payer_input(case))
        adapter = payers.adapter_for_claim(case)
        try:
            workflow = payers.workflow_id(adapter, "payment_ack")
        except ValueError:
            workflow = ""
        workflow = (
            workflow or _s(money.workflow_id) or _s(money.claim_ref) or case.claim_no
        )
        envelope = {
            "jwe_headers": {
                "x-hcx-sender_code": facility.participant_code,
                "x-hcx-recipient_code": _s(money.sender_code)
                or common.recipient_code(case),
                "x-hcx-workflow_id": workflow,
                "x-hcx-correlation_id": _s(money.correlation_id),
            },
            "fhir": bundle,
        }
        ack = common.send(PATH, envelope, case, label=f"payment-{money.id}")
    except common.ServiceRefusal as e:
        _write(money, ack_status="error", ack_error=e.message)
        raise
    if ack.failed:
        _write(
            money,
            ack_status="error",
            ack_error=ack.failed,
            ack_txn_id=ack.txn_id,
            ack_correlation_id=ack.correlation_id,
        )
        raise common.ServiceRefusal(ack.failed)
    _write(
        money,
        ack_status="sent",
        ack_txn_id=ack.txn_id,
        ack_correlation_id=ack.correlation_id,
        acknowledged_at=timezone.now(),
        ack_error=None,
    )
    return money


def auto_acknowledge(payment_id) -> None:
    """C10: acknowledge a freshly recorded notice; never raises."""
    try:
        acknowledge_payment(payment_id)
    except common.ServiceRefusal as e:
        logger.info("nhcx: payment %s not acknowledged: %s", payment_id, e.message)
    except Exception:
        logger.exception("nhcx: payment %s acknowledgement failed", payment_id)
        ClaimPayment.objects.filter(id=payment_id).update(
            ack_status="error", ack_error="The acknowledgement could not be sent."
        )
