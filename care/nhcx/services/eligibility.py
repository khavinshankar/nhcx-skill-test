"""A2 coverage eligibility: validation, benefits, discovery and auth-requirements.

Public:
- ``run_check(claim, purpose, policy_code, member_id, *, extra=None) -> Ack``
- ``discover(facility, payer_code, id_type, id_value, extra=None, *, patient=None)
  -> Claim``
- ``request_auth(claim) -> Ack``
- ``ensure_auth_requirements(claim) -> bool`` (A4 calls it before each
  pre-auth or enhancement send; never raises)
- ``fingerprint(claim) -> str`` (D13 ``asked_codes``)
"""

import logging
import re
from dataclasses import replace

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from care.nhcx.fhir.build import coverage_request
from care.nhcx.fhir.inputs import EligibilityInput, FhirBuildError
from care.nhcx.models import (
    Claim,
    ClaimAuth,
    ClaimStatus,
    allocate_claim_no,
)
from care.nhcx.services import hooks, stage
from care.nhcx.services.common import (
    ServiceRefusal,
    adapter,
    coverage_input,
    facility_input,
    facility_profile,
    get_claim,
    headers,
    line_inputs,
    patient_input,
    payer_input,
    send,
)

logger = logging.getLogger(__name__)

PATH = "v1/coverageeligibility/check"
AADHAAR_DIGITS = 12
MOBILE_DIGITS = 10
PURPOSES = ("validation", "benefits", "discovery")
ID_TYPES = ("MemberId", "MobileNo", "AbhaNumber")

CLAIM_NOT_FOUND = "Claim not found."
NO_HFR = "Set the facility's HFR ID under Settings before raising claims."
NO_PARTICIPANT = (
    "Set the facility's NHCX participant code under Settings before raising claims."
)
NO_ORG_AUTH = (
    "Set the facility's HFR ID and NHCX participant code under Settings "
    "before checking requirements."
)


def _s(v) -> str:
    return "" if v is None else str(v).strip()


def _workflow_id(claim) -> str:
    if _s(getattr(settings, "NHCX_ELIGIBILITY_WORKFLOW_ID", "11")) == "case":
        return claim.claim_no
    return "11"


def _facility_input(claim, profile):
    return facility_input(claim.facility)


def _check_org(facility):
    profile = facility_profile(facility)
    if profile is None or not _s(profile.hfr_id):
        raise ServiceRefusal(NO_HFR)
    if not _s(profile.participant_code):
        raise ServiceRefusal(NO_PARTICIPANT)
    return profile


def _envelope(claim, profile, bundle, purpose) -> dict:
    extra = {}
    if _s(claim.abha_number):
        extra["x-hcx-ben-abha-id"] = _s(claim.abha_number)
    extra.update(hooks.call("extra_headers", claim, purpose) or {})
    return {
        "jwe_headers": headers(
            claim,
            _workflow_id(claim),
            sender=_s(profile.participant_code),
            extra=extra,
        ),
        "fhir": bundle,
    }


def _build(data: EligibilityInput) -> dict:
    try:
        return coverage_request.build(data)
    except (FhirBuildError, ValueError) as e:
        raise ServiceRefusal(str(e)) from e


def run_check(claim, purpose, policy_code, member_id, *, extra=None):
    claim = get_claim(claim)
    purpose = _s(purpose)
    if purpose not in PURPOSES:
        raise ServiceRefusal(
            "Choose whether this check is a validation, a benefits check or a "
            "discovery."
        )
    policy_code, member_id = _s(policy_code), _s(member_id)
    if not member_id:
        raise ServiceRefusal("Member ID is required for an eligibility check.")
    if purpose in ("validation", "benefits") and not policy_code:
        msg = f"Policy code is required for a {purpose} check."
        raise ServiceRefusal(msg)
    profile = _check_org(claim.facility)

    patient = replace(patient_input(claim), member_id=member_id)
    if extra:
        patient = replace(
            patient,
            aadhaar_number=_s(extra.get("aadhaar_number")) or patient.aadhaar_number,
            mobile_number=_s(extra.get("mobile_number")) or patient.mobile_number,
        )
    coverage = replace(
        coverage_input(claim), policy_code=policy_code, member_id=member_id
    )
    data = EligibilityInput(
        purpose=purpose,
        patient=patient,
        facility=_facility_input(claim, profile),
        payer=payer_input(claim),
        coverage=coverage,
        lines=line_inputs(claim) if purpose == "benefits" else [],
    )
    bundle = _build(data)
    ack = send(
        PATH, _envelope(claim, profile, bundle, purpose), claim, label="coverage"
    )

    with transaction.atomic():
        claim.status = ClaimStatus.error if ack.failed else ClaimStatus.checking
        claim.purpose = purpose
        claim.policy_code = policy_code or claim.policy_code
        claim.member_id = member_id
        claim.txn_id = ack.txn_id
        claim.correlation_id = ack.correlation_id
        claim.checked_at = timezone.now()
        claim.error_message = ack.failed
        claim.save(
            update_fields=[
                "status",
                "purpose",
                "policy_code",
                "member_id",
                "txn_id",
                "correlation_id",
                "checked_at",
                "error_message",
                "modified_date",
            ]
        )
        stage.recompute(claim)
    if ack.failed:
        raise ServiceRefusal(ack.failed)
    return ack


def _check_extra(extra: dict) -> dict:
    out = {}
    aadhaar = re.sub(r"[\s-]", "", _s(extra.get("aadhaar_number")))
    if aadhaar:
        if not (aadhaar.isdigit() and len(aadhaar) == AADHAAR_DIGITS):
            raise ServiceRefusal("An Aadhaar number has 12 digits")
        out["aadhaar_number"] = aadhaar
    mobile = re.sub(r"[\s-]", "", _s(extra.get("mobile_number")))
    if mobile:
        if not (mobile.isdigit() and len(mobile) == MOBILE_DIGITS):
            raise ServiceRefusal("A mobile number has 10 digits")
        out["mobile_number"] = mobile
    out["member_id"] = _s(extra.get("member_id"))
    return out


def discover(facility, payer_code, id_type, id_value, extra=None, *, patient=None):
    profile = facility_profile(facility)
    if profile is None or not _s(profile.hfr_id):
        raise ServiceRefusal(NO_HFR)
    if not _s(profile.participant_code):
        raise ServiceRefusal(NO_PARTICIPANT)
    extra = _check_extra(extra or {})
    id_value = _s(id_value)
    payer_code = _s(payer_code) or None
    prefix = getattr(settings, "NHCX_CLAIM_PREFIX", "") or "NM"
    with transaction.atomic():
        claim = Claim.objects.create(
            facility=facility,
            claim_no=allocate_claim_no(prefix),
            status=ClaimStatus.draft,
            purpose="discovery",
            patient=patient,
            payer_id=payer_code,
            processing_id=payer_code,
            member_id=id_value if id_type == "MemberId" else "",
            abha_number=id_value if id_type == "AbhaNumber" else None,
            mobile_number=id_value if id_type == "MobileNo" else None,
            search_id_type=id_type if id_type in ID_TYPES else None,
            search_id_value=id_value or None,
        )
        stage.recompute(claim)
    run_check(
        claim,
        "discovery",
        "",
        extra.get("member_id") or id_value,
        extra=extra,
    )
    return claim


def fingerprint(claim) -> str:
    parts = sorted(f"{ln.kind}:{ln.code}:{ln.quantity}" for ln in claim.lines.all())
    return "|".join(parts)


def request_auth(claim):
    claim = get_claim(claim)
    if claim.status != ClaimStatus.eligible:
        raise ServiceRefusal(
            "Check the policy's eligibility before validating a procedure set "
            "against it."
        )
    lines = line_inputs(claim)
    if not lines:
        raise ServiceRefusal(
            "Choose the line items first, this checks the procedure set, so there "
            "has to be one."
        )
    profile = facility_profile(claim.facility)
    if profile is None or not _s(profile.hfr_id) or not _s(profile.participant_code):
        raise ServiceRefusal(NO_ORG_AUTH)
    data = EligibilityInput(
        purpose="auth-requirements",
        patient=patient_input(claim),
        facility=_facility_input(claim, profile),
        payer=payer_input(claim),
        coverage=coverage_input(claim),
        lines=lines,
    )
    bundle = _build(data)
    ack = send(
        PATH,
        _envelope(claim, profile, bundle, "auth-requirements"),
        claim,
        label="coverage-auth",
    )
    values = {
        "status": "error" if ack.failed else "checking",
        "txn_id": ack.txn_id,
        "correlation_id": ack.correlation_id,
        "requested_at": timezone.now(),
        "settled_at": None,
        "error_message": ack.failed,
        "outcome": None,
        "disposition": None,
        "inforce": None,
        "response_json": None,
        "asked_codes": fingerprint(claim),
    }
    with transaction.atomic():
        ruling = ClaimAuth.objects.filter(claim=claim).first()
        if ruling is None:
            ClaimAuth.objects.create(claim=claim, **values)
        else:
            ruling.items.all().delete()
            ruling.requirements.all().delete()
            for k, v in values.items():
                setattr(ruling, k, v)
            ruling.save()
    if ack.failed:
        raise ServiceRefusal(ack.failed)
    return ack


def ensure_auth_requirements(claim) -> bool:  # noqa: PLR0911
    try:
        claim = get_claim(claim)
    except ServiceRefusal:
        return False
    if claim.status != ClaimStatus.eligible or not claim.lines.exists():
        return False
    try:
        if not getattr(adapter(claim), "auth_check_unasked", False):
            return False
    except Exception:
        return False
    ruling = ClaimAuth.objects.filter(claim=claim).first()
    if (
        ruling is not None
        and ruling.status != "error"
        and (ruling.asked_codes or "") == fingerprint(claim)
    ):
        return False
    try:
        request_auth(claim)
    except Exception as e:
        logger.info(
            "nhcx: automatic auth-requirements check skipped claim=%s: %s",
            claim.claim_no,
            e,
        )
        return False
    return True
