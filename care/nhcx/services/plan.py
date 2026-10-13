"""A3 package master: request the payer's InsurancePlan, or reuse one held.

Public:
- ``request_plan(claim, refresh=False) -> Ack | None`` (None when reused)
- ``reuse_plan(claim) -> bool``
- ``copy_columns(model) -> [field names]`` (every column but keys and audit)
"""

import logging

from django.db import transaction
from django.utils import timezone

from care.nhcx.fhir.build import plan_task
from care.nhcx.fhir.inputs import FhirBuildError
from care.nhcx.models import ClaimPlan, ClaimPlanBenefit, ClaimPlanForm
from care.nhcx.services.common import (
    ServiceRefusal,
    facility_profile,
    get_claim,
    headers,
    send,
)

logger = logging.getLogger(__name__)

PATH = "v1/insuranceplan/request"
NO_PLAN_INPUT = "A plan request needs a policy code or the facility's HFR ID."
SKIP = {
    "id",
    "claim",
    "plan",
    "external_id",
    "created_date",
    "modified_date",
    "deleted",
    "history",
    "meta",
    "created_by",
    "updated_by",
}


def _s(v) -> str:
    return "" if v is None else str(v).strip()


def copy_columns(model) -> list:
    return [f.name for f in model._meta.concrete_fields if f.name not in SKIP]  # noqa: SLF001


def reuse_plan(claim) -> bool:
    claim = get_claim(claim)
    profile = facility_profile(claim.facility)
    hfr = _s(profile.hfr_id) if profile else ""
    policy_code = _s(claim.policy_code)
    if not hfr or not policy_code:
        return False
    source = (
        ClaimPlan.objects.filter(
            status="ready",
            policy_code=policy_code,
            provider_id=hfr,
            claim__payer_id=claim.payer_id,
        )
        .exclude(claim=claim)
        .order_by("-fetched_at", "-id")
        .first()
    )
    if source is None:
        return False
    values = {name: getattr(source, name) for name in copy_columns(ClaimPlan)}
    with transaction.atomic():
        plan = ClaimPlan.objects.filter(claim=claim).first()
        if plan is None:
            plan = ClaimPlan.objects.create(claim=claim, **values)
        else:
            plan.benefits.all().delete()
            plan.forms.all().delete()
            for k, v in values.items():
                setattr(plan, k, v)
            plan.save()
        benefit_cols = copy_columns(ClaimPlanBenefit)
        ClaimPlanBenefit.objects.bulk_create(
            [
                ClaimPlanBenefit(plan=plan, **{c: getattr(b, c) for c in benefit_cols})
                for b in source.benefits.order_by("seq", "id")
            ]
        )
        form_cols = copy_columns(ClaimPlanForm)
        ClaimPlanForm.objects.bulk_create(
            [
                ClaimPlanForm(plan=plan, **{c: getattr(f, c) for c in form_cols})
                for f in source.forms.order_by("id")
            ]
        )
    logger.info(
        "nhcx: plan reused claim=%s from claim=%s",
        claim.claim_no,
        source.claim.claim_no,
    )
    return True


def request_plan(claim, refresh: bool = False):
    claim = get_claim(claim)
    if not refresh and reuse_plan(claim):
        return None
    profile = facility_profile(claim.facility)
    if profile is None or not _s(profile.hfr_id):
        raise ServiceRefusal(
            "Set the facility's HFR ID under Settings before fetching a package master."
        )
    if not _s(profile.participant_code):
        raise ServiceRefusal(
            "Set the facility's NHCX participant code under Settings before "
            "fetching a package master."
        )
    provider_id = _s(profile.hfr_id)
    policy_code = _s(claim.policy_code)
    if not policy_code and not provider_id:
        raise ServiceRefusal(NO_PLAN_INPUT)
    try:
        bundle = plan_task.build(policy_code, provider_id)
    except (FhirBuildError, ValueError) as e:
        raise ServiceRefusal(str(e)) from e
    envelope = {
        "jwe_headers": headers(
            claim, claim.claim_no, sender=_s(profile.participant_code)
        ),
        "fhir": bundle,
    }
    ack = send(PATH, envelope, claim, label="insuranceplan")
    values = {
        "status": "error" if ack.failed else "fetching",
        "txn_id": ack.txn_id,
        "correlation_id": ack.correlation_id,
        "requested_at": timezone.now(),
        "fetched_at": None,
        "error_message": ack.failed,
        "policy_code": policy_code or None,
        "provider_id": provider_id,
        "plan_identifier": None,
        "plan_title": None,
        "plan_type": None,
        "sum_insured": None,
        "policy_documents": None,
        "response_json": None,
    }
    with transaction.atomic():
        plan = ClaimPlan.objects.filter(claim=claim).first()
        if plan is None:
            ClaimPlan.objects.create(claim=claim, **values)
        else:
            plan.benefits.all().delete()
            for k, v in values.items():
                setattr(plan, k, v)
            plan.save()
    if ack.failed:
        raise ServiceRefusal(ack.failed)
    return ack
