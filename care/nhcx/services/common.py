"""Shared service helpers (SCAFFOLDING 3.3, 8; APIs conventions).

Every outbound service (A2 to A8) uses these. Names are stable:

Errors
- ``ServiceRefusal(message)``: a refusal shown to the desk verbatim
  (the API answers ``400 {"ok": false, "error": message}``).

Sending (APIs conventions "SEND")
- ``send(path, envelope, claim, *, label="") -> Ack``: refuses inside a DB
  transaction, archives the outbound envelope and its acknowledgement, logs
  with the case number, correlation id and ledger id. A ``SendError`` that
  names ids, or a result with ``ok`` false, comes back as an ``Ack`` with
  ``failed`` set to the message to store; a ``SendError`` naming no ids (or an
  unconfigured gateway) raises ``ServiceRefusal`` since nothing went out.
- ``Ack``: txn_id, correlation_id, request_id, api_call_id, ledger_id,
  headers, response, failed (str or None).
- ``headers(claim, workflow_id, *, sender=None, status=None, extra=None)``:
  the x-hcx headers the app sets (sender, recipient, workflow id).
- ``recipient_code(claim)``: processing_id, else payer_id, else the default.
- ``default_payer_code()``: ``settings.NHCX_DEFAULT_PAYER_CODE`` ("" if unset).

FHIR inputs from models (nhcx-plan/mapping.json)
- ``facility_profile(facility) -> FacilityProfile | None``
- ``facility_input(facility) -> FacilityInput`` (D1: HFR id, name, code)
- ``payer_input(claim) -> PayerInput``
- ``patient_input(claim) -> PatientInput`` (emr.Patient, claim fallbacks)
- ``coverage_input(claim) -> CoverageInput``
- ``practitioner_input(user) -> PractitionerInput`` (PractitionerProfile)
- ``practitioner_inputs(claim) -> list[PractitionerInput]`` (D26 care team)
- ``line_inputs(claim) -> list[LineInput]`` (D16)

Lookups
- ``get_claim(claim_or_id) -> Claim``: by instance, external id or pk; raises
  ``ServiceRefusal("Claim not found.")``.

Payers
- ``payer_name(code) -> str | None``: the registry name (G4), cached; None
  when the lookup failed (retried after a few minutes).
- ``adapter(claim)``: ``services.payers.adapter_for(claim.payer_id)`` when
  that module exists, else a generic stand-in with ``key``/``desk``/
  ``auth_check_unasked``.
"""

import logging
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any

from django.conf import settings
from django.core.cache import cache

from care.nhcx import archive
from care.nhcx.fhir.inputs import (
    CoverageInput,
    FacilityInput,
    LineInput,
    PatientInput,
    PayerInput,
    PractitionerInput,
)
from care.nhcx.gateway import get_gateway
from care.nhcx.gateway.errors import GatewayError, SendError
from care.nhcx.gateway.send import ensure_not_in_transaction

logger = logging.getLogger(__name__)

PAYER_NAME_TTL = 24 * 3600
PAYER_NAME_RETRY = 5 * 60
_MISSING = "__nhcx_missing__"
CLAIM_NOT_FOUND = "Claim not found."


class ServiceRefusal(Exception):  # noqa: N818 - contract name
    """A refusal before (or instead of) a send; the message is shown verbatim."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

    def __str__(self) -> str:
        return self.message


@dataclass
class Ack:
    txn_id: str | None = None
    correlation_id: str | None = None
    request_id: str | None = None
    api_call_id: str | None = None
    ledger_id: str | None = None
    headers: dict = field(default_factory=dict)
    response: Any = None
    failed: str | None = None

    def to_dict(self) -> dict:
        return {
            "txn_id": self.txn_id,
            "correlation_id": self.correlation_id,
            "request_id": self.request_id,
            "api_call_id": self.api_call_id,
            "ledger_id": self.ledger_id,
            "failed": self.failed,
            "response": self.response,
        }


def _s(value) -> str:
    return "" if value is None else str(value).strip()


# ---- payer / participant codes ----


def default_payer_code() -> str:
    return _s(getattr(settings, "NHCX_DEFAULT_PAYER_CODE", ""))


def recipient_code(claim) -> str:
    return _s(claim.processing_id) or _s(claim.payer_id) or default_payer_code()


def facility_profile(facility):
    if facility is None:
        return None
    from care.nhcx.models import FacilityProfile

    return FacilityProfile.objects.filter(facility=facility).first()


def headers(claim, workflow_id, *, sender=None, status=None, extra=None) -> dict:
    if sender is None:
        profile = facility_profile(claim.facility)
        sender = _s(profile.participant_code) if profile else ""
    out = {
        "x-hcx-sender_code": sender,
        "x-hcx-recipient_code": recipient_code(claim),
        "x-hcx-workflow_id": _s(workflow_id),
    }
    if status:
        out["x-hcx-status"] = status
    if extra:
        out.update({k: v for k, v in extra.items() if v not in (None, "")})
    return out


def payer_name(code) -> str | None:
    code = _s(code)
    if not code:
        return None
    key = f"nhcx:payer-name:{code.lower()}"
    cached = cache.get(key)
    if cached is not None:
        return None if cached == _MISSING else cached
    try:
        gw = get_gateway()
        name = _s(gw.identity_for(code).fetch_participant(code).get("name")) or None
    except Exception as e:
        logger.info("nhcx: payer name lookup failed code=%s: %s", code, e)
        cache.set(key, _MISSING, PAYER_NAME_RETRY)
        return None
    cache.set(key, name or _MISSING, PAYER_NAME_TTL if name else PAYER_NAME_RETRY)
    return name


def adapter(claim):
    try:
        from care.nhcx.services import payers
    except ImportError:
        payers = None
    if payers is not None and hasattr(payers, "adapter_for"):
        return payers.adapter_for(getattr(claim, "payer_id", None) or "")
    return SimpleNamespace(key="generic", desk=None, auth_check_unasked=False)


def get_claim(claim_or_id):
    """A Claim, or one looked up by external id or pk; refuses "Claim not found."."""
    from care.nhcx.models import Claim

    if isinstance(claim_or_id, Claim):
        return claim_or_id
    claim = None
    value = _s(claim_or_id)
    if value:
        try:
            if value.isdigit():
                claim = Claim.objects.filter(pk=int(value)).first()
            else:
                claim = Claim.objects.filter(external_id=value).first()
        except Exception:
            claim = None
    if claim is None:
        raise ServiceRefusal(CLAIM_NOT_FOUND)
    return claim


# ---- FHIR inputs ----


def facility_input(facility) -> FacilityInput:
    profile = facility_profile(facility)
    return FacilityInput(
        identifier_value=_s(profile.hfr_id) if profile else "",
        name=_s(getattr(facility, "name", "")),
        participant_code=_s(profile.participant_code) if profile else "",
    )


def payer_input(claim) -> PayerInput:
    code = _s(claim.payer_id) or default_payer_code()
    return PayerInput(payer_id=code, payer_name=_s(claim.payer_name) or code)


def coverage_input(claim) -> CoverageInput:
    return CoverageInput(
        policy_code=_s(claim.policy_code), member_id=_s(claim.member_id)
    )


def patient_input(claim) -> PatientInput:
    patient = claim.patient
    abha = _s(claim.abha_number)
    name = gender = mobile = ""
    dob = None
    if patient is not None:
        from care.nhcx.models.abha import get_abha_number

        name = _s(patient.name)
        gender = _s(patient.gender)
        mobile = _s(patient.phone_number)
        dob = patient.date_of_birth
        abha = abha or _s(get_abha_number(patient))
    return PatientInput(
        member_id=_s(claim.member_id),
        abha_number=abha,
        beneficiary_name=_s(claim.beneficiary_name),
        patient_name=name or _s(claim.beneficiary_name),
        mobile_number=_s(claim.mobile_number) or mobile,
        patient_gender=gender or _s(claim.patient_gender),
        patient_dob=dob or claim.patient_dob,
    )


def practitioner_input(user) -> PractitionerInput:
    try:
        profile = user.nhcx_practitioner_profile
    except Exception:
        profile = None
    name = ""
    if hasattr(user, "get_full_name"):
        name = _s(user.get_full_name())
    name = name or _s(getattr(user, "username", ""))
    if profile is not None and profile.prefix and name:
        name = f"{profile.prefix} {name}"
    return PractitionerInput(
        id=getattr(user, "external_id", None) or getattr(user, "id", None),
        name=name,
        identifier_value=_s(profile.hpr_id) if profile else "",
        qualification_display=_s(profile.qualification_display) if profile else "",
        specialty_code=_s(profile.specialty_code) if profile else "",
        specialty_display=_s(profile.specialty_display) if profile else "",
        license_number=_s(profile.hpr_id) if profile else "",
    )


def practitioner_inputs(claim) -> list:
    rows = claim.care_team.select_related("practitioner").order_by("seq", "id")
    return [practitioner_input(r.practitioner) for r in rows if r.practitioner_id]


def line_inputs(claim) -> list:
    return [
        LineInput(
            kind=ln.kind,
            code=ln.code,
            display=_s(ln.display),
            category_code=_s(ln.category_code),
            category_display=_s(ln.category_display),
            unit_price=ln.unit_price,
            quantity=ln.quantity,
            amount=ln.amount,
            parent_code=_s(ln.parent_code),
            seq=ln.seq,
        )
        for ln in claim.lines.order_by("kind", "seq", "id")
    ]


# ---- send ----


def _log_ids(claim, path, ack: Ack, note: str) -> None:
    logger.info(
        "nhcx: send %s claim=%s correlation=%s ledger=%s %s",
        path,
        getattr(claim, "claim_no", None),
        ack.correlation_id,
        ack.ledger_id or ack.txn_id,
        note,
    )


def send(path: str, envelope: dict, claim, *, label: str = "") -> Ack:
    """APIs conventions SEND: the ids it went out under, and failed or None."""
    ensure_not_in_transaction()
    try:
        gw = get_gateway()
    except GatewayError as e:
        archive.archive_outbound(claim, path, envelope, None, label=label)
        raise ServiceRefusal(getattr(e, "reason", None) or e.message) from e
    try:
        result = gw.send(path, envelope)
    except SendError as e:
        if e.names_ids:
            ack = Ack(
                txn_id=e.txn_id,
                correlation_id=e.correlation_id,
                request_id=e.request_id,
                api_call_id=e.api_call_id,
                ledger_id=e.ledger_id,
                headers=dict(e.headers or {}),
                failed=e.message,
            )
            archive.archive_outbound(claim, path, envelope, ack, label=label)
            _log_ids(claim, path, ack, f"failed: {e.code}: {e.message}")
            return ack
        archive.archive_outbound(claim, path, envelope, None, label=label)
        logger.warning(
            "nhcx: send %s claim=%s refused before ids: %s: %s",
            path,
            getattr(claim, "claim_no", None),
            e.code,
            e.message,
        )
        raise ServiceRefusal(e.message) from e
    except GatewayError as e:
        archive.archive_outbound(claim, path, envelope, None, label=label)
        raise ServiceRefusal(e.message) from e
    ack = Ack(
        txn_id=result.txn_id,
        correlation_id=result.correlation_id,
        request_id=result.request_id,
        api_call_id=result.api_call_id,
        ledger_id=result.ledger_id,
        headers=dict(result.headers or {}),
        response=result.response,
    )
    if not result.ok:
        ack.failed = f"{result.error_code}: {result.error_message}"
    archive.archive_outbound(claim, path, envelope, ack, label=label)
    _log_ids(claim, path, ack, f"failed: {ack.failed}" if ack.failed else "accepted")
    return ack
