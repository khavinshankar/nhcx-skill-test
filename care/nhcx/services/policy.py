"""A1 beneficiary policy search and opening a case (S1, S2).

Public:
- ``search_policies(id_type, id_value) -> [normalised row]``
- ``normalise(row) -> dict``
- ``open_case(facility, policy, id_type, id_value, *, patient=None) -> (claim, flash)``
"""

import logging

from django.conf import settings
from django.db import transaction

from care.nhcx.gateway import get_gateway
from care.nhcx.gateway.errors import GatewayError
from care.nhcx.models import Claim, ClaimStatus, allocate_claim_no
from care.nhcx.services import stage
from care.nhcx.services.common import ServiceRefusal, payer_name

logger = logging.getLogger(__name__)

ID_TYPES = ("MemberId", "MobileNo", "AbhaNumber")
HTTP_OK = 200
HTTP_REDIRECT = 300
NO_POLICIES = "No policies found"

FIELDS = {
    "member_id": ("memberid", "member_id", "memberId", "pmjayid"),
    "name": (
        "name",
        "membername",
        "patient_name",
        "patientName",
        "beneficiaryname",
        "beneficiaryName",
    ),
    "policy_code": (
        "policy_number",
        "policyNumber",
        "policyno",
        "policyNo",
        "policycode",
        "productid",
    ),
    "payer_id": ("payerid", "payerId", "insurer_code"),
    "processing_id": ("processingid", "processingId", "processingID"),
    "product_id": ("productid", "productId"),
    "product_name": ("productname", "productName"),
    "abha_number": ("abhanumber", "abhaNumber", "abha_number"),
    "mobile_number": ("mobilenumber", "mobileNumber", "mobile"),
    "photo": ("photo", "photoUrl", "beneficiaryphoto", "memberphoto"),
}


def _first(row: dict, names) -> str | None:
    for n in names:
        v = row.get(n)
        if v not in (None, ""):
            s = str(v).strip()
            if s:
                return s
    return None


def normalise(row: dict) -> dict:
    out = {key: _first(row, names) for key, names in FIELDS.items()}
    out["payer_name"] = payer_name(out["payer_id"]) if out["payer_id"] else None
    out["raw"] = row
    return out


def _error_text(body) -> str:
    if isinstance(body, dict):
        err = body.get("error")
        if isinstance(err, dict):
            return str(err.get("message") or err.get("code") or err)
        for k in ("error", "message", "errorMessage"):
            if body.get(k):
                return str(body[k])
    return str(body or "") or "The registry refused the search."


def search_policies(id_type, id_value) -> list:
    if id_type not in ID_TYPES:
        raise ServiceRefusal("Choose what kind of identifier you are searching with.")
    id_value = (id_value or "").strip()
    if not id_value:
        raise ServiceRefusal("Enter an identifier value to search for.")
    try:
        answer = get_gateway().beneficiary.policies_search(
            {"identifiertype": id_type, "identifiervalue": id_value}
        )
        status = int(answer.get("status") or 0)
        body = answer.get("body")
        if not HTTP_OK <= status < HTTP_REDIRECT:
            code = f"REGISTRY_HTTP_{status}"
            raise GatewayError(code, _error_text(body))
    except GatewayError as e:
        if NO_POLICIES.lower() in (e.message or "").lower():
            return []
        logger.warning("nhcx: policy search failed: %s: %s", e.code, e.message)
        raise ServiceRefusal(e.message) from e
    if isinstance(body, list):
        rows = body
    elif isinstance(body, dict):
        rows = body.get("policies") or body.get("result") or body.get("data") or []
    else:
        rows = []
    if not isinstance(rows, list):
        rows = []
    return [normalise(r) for r in rows if isinstance(r, dict)]


def open_case(facility, policy: dict, id_type, id_value, *, patient=None):
    """S2 Select: a new draft claim around the chosen policy (no NHCX call)."""
    policy = policy or {}
    if isinstance(policy.get("raw"), dict):
        raw, norm = policy["raw"], dict(policy)
    else:
        raw, norm = policy, normalise(policy)
    if not norm.get("member_id"):
        raise ServiceRefusal(
            "That policy has no member ID; a claim cannot be raised without one."
        )
    prefix = getattr(settings, "NHCX_CLAIM_PREFIX", "") or "NM"
    with transaction.atomic():
        claim = Claim.objects.create(
            facility=facility,
            claim_no=allocate_claim_no(prefix),
            status=ClaimStatus.draft,
            search_id_type=id_type if id_type in ID_TYPES else None,
            search_id_value=(id_value or "").strip() or None,
            member_id=norm["member_id"],
            policy_code=norm.get("policy_code"),
            beneficiary_name=norm.get("name"),
            abha_number=norm.get("abha_number"),
            mobile_number=norm.get("mobile_number"),
            processing_id=norm.get("processing_id"),
            payer_id=norm.get("payer_id"),
            payer_name=norm.get("payer_name") or policy.get("payer_name"),
            product_id=norm.get("product_id"),
            product_name=norm.get("product_name"),
            patient_photo=norm.get("photo"),
            policy_json=raw,
            patient=patient,
        )
        stage.recompute(claim)
    return claim, f"Claim {claim.claim_no} opened."
