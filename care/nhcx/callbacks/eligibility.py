"""C2 eligibility verdict and C3 auth-requirements ruling (coverage replies)."""

import logging

from django.db import transaction
from django.utils import timezone

from care.nhcx.callbacks import dispatch
from care.nhcx.fhir import bundle as fb
from care.nhcx.fhir.read import eligibility as read_elig
from care.nhcx.models import Claim, ClaimAuth, ClaimAuthItem, ClaimAuthRequirement
from care.nhcx.services import stage
from care.nhcx.services.common import adapter

logger = logging.getLogger(__name__)

NO_RESPONSE = "The payer reply carries no CoverageEligibilityResponse."

VERDICT_COLUMNS = (
    "inforce",
    "outcome",
    "disposition",
    "auth_required",
    "allowed_amount",
    "used_amount",
    "beneficiary_name",
    "patient_gender",
    "patient_dob",
    "patient_address",
    "abha_number",
    "patient_photo",
    "plan_name",
    "plan_period_start",
    "plan_period_end",
    "relationship",
    "status",
)


def _corr(envelope, delivery) -> str:
    corr = (delivery or {}).get("correlation_id")
    if not corr:
        h = envelope.get("jwe_headers") if isinstance(envelope, dict) else None
        corr = h.get("x-hcx-correlation_id") if isinstance(h, dict) else ""
    return str(corr or "")


def handle(envelope, delivery=None):
    corr = _corr(envelope, delivery)
    row = (
        Claim.objects.filter(correlation_id=corr).order_by("-id").first()
        if corr
        else None
    )
    if row is not None:
        return on_check(row, envelope)
    return on_auth(corr, envelope)


def _has_response(body) -> bool:
    return fb.find_resource(body, "CoverageEligibilityResponse") is not None


def on_check(row, envelope):
    """C2: apply the eligibility verdict to the case (D9)."""
    if row.status != "checking" and not dispatch.failed_send(row):
        return dispatch.result(dispatch.IGNORED, "the check has moved on")
    body = dispatch.payload(envelope)
    if dispatch.is_protocol_response(body):
        row.status = "error"
        row.error_message = dispatch.rejection(body)
        row.save(update_fields=["status", "error_message", "modified_date"])
        return dispatch.result(dispatch.SETTLED, row.error_message)
    if not _has_response(body):
        raise dispatch.Rejected(NO_RESPONSE)
    verdict = read_elig.read_verdict(body)
    with transaction.atomic():
        dispatch.revive(row, "checking")
        row.refresh_from_db()
        for column in VERDICT_COLUMNS:
            if column in verdict:
                setattr(row, column, verdict[column])
        row.response_json = body
        row.save()
        stage.recompute(row)
    return dispatch.result(dispatch.SETTLED, row.status)


def on_auth(corr, envelope):
    """C3: apply the auth-requirements ruling to D13 to D15."""
    row = (
        ClaimAuth.objects.filter(correlation_id=corr)
        .select_related("claim")
        .order_by("-id")
        .first()
        if corr
        else None
    )
    if row is None:
        return dispatch.result(dispatch.UNMATCHED)
    if row.status != "checking" and not dispatch.failed_send(row):
        return dispatch.result(dispatch.IGNORED, "the ruling has moved on")
    body = dispatch.payload(envelope)
    if dispatch.is_protocol_response(body):
        row.status = "error"
        row.error_message = dispatch.rejection(body)
        row.save(update_fields=["status", "error_message", "modified_date"])
        return dispatch.result(dispatch.SETTLED, row.error_message)
    # read before any write, so a rejected reply leaves the ruling as it was
    if not _has_response(body):
        raise dispatch.Rejected(NO_RESPONSE)
    stages = tuple(getattr(adapter(row.claim), "preauth_document_stages", ("pre",)))
    ruling = read_elig.read_auth(body, stages)
    with transaction.atomic():
        dispatch.revive(row, "checking")
        row.outcome = ruling.get("outcome")
        row.disposition = ruling.get("disposition")
        row.inforce = ruling.get("inforce")
        row.status = "ready"
        row.settled_at = timezone.now()
        row.error_message = None
        row.response_json = body
        row.save()
        row.items.all().delete()
        row.requirements.all().delete()
        ClaimAuthItem.objects.bulk_create(
            [ClaimAuthItem(auth=row, **item) for item in ruling.get("items") or []]
        )
        ClaimAuthRequirement.objects.bulk_create(
            [
                ClaimAuthRequirement(auth=row, **req)
                for req in ruling.get("requirements") or []
            ]
        )
    return dispatch.result(dispatch.SETTLED, "ready")
