"""Payer adapters (PAYERS.md): what differs by payer, kept in one place.

A configuration row maps a payer participant code to an adapter key
(``settings.NHCX_PAYER_ADAPTERS``: JSON object or ``code=key,code=key``). A
payer with no row whose registered name starts with ``SHA`` gets ``pmjay``;
every other payer gets ``generic``. Codes are matched on their numeric part.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field

from django.conf import settings

logger = logging.getLogger("care.nhcx")

NO_WORKFLOW = "No workflow id is defined for '{kind}'."

PMJAY_WORKFLOWS = {
    "preauth": "12",
    "preauth_resubmit": "121",
    "preauth_query_response": "19",
    "enhancement": "13",
    "enhancement_resubmit": "131",
    "predetermination": "12",
    "cancel": "PC01",
    "claim": "15",
    "claim_query_response": "151",
    "payment_ack": "17",
    "reprocess": "36",
    "release": "36",
}
OTHER_WORKFLOWS = {
    **{k: v for k, v in PMJAY_WORKFLOWS.items() if k != "payment_ack"},
    "claim_resubmit": "16",
    # the notice's own workflow id is echoed back
    "payment_ack": None,
}

USE_CASES = {
    "preauth": "New",
    "predetermination": "New",
    "claim": "New",
    "enhancement": "Enhancement",
    "preauth_resubmit": "Resubmit",
    "preauth_query_response": "Resubmit",
    "enhancement_resubmit": "Resubmit",
    "claim_query_response": "Resubmit",
    "claim_resubmit": "Resubmit",
}
RESPONSE_KINDS = {
    "preauth_query_response",
    "enhancement_resubmit",
    "claim_query_response",
}


@dataclass(frozen=True)
class Adapter:
    key: str
    name: str
    payer_system: str
    program_code: bool = False
    procedure_factor: bool = False
    auth_check_unasked: bool = False
    query_mode: str = "communication"
    cancel_intimation: str = "intimationNumber"
    reprocess_intimation: str = "intimationNumber"
    status_enquiry: bool = True
    biometric_required: bool = False
    member_scheme: str = "generic"
    desk: str | None = None
    preauth_document_stages: tuple = ("pre",)
    reprocess_reasons: tuple = ("claimrejected", "partialpayment", "rejectiondisputed")
    workflows: dict = field(default_factory=dict)

    @property
    def is_pmjay(self) -> bool:
        return self.key == "pmjay"


ADAPTERS = {
    "pmjay": Adapter(
        key="pmjay",
        name="PMJAY",
        payer_system="https://payer.pmjay.nha.gov.in",
        program_code=True,
        procedure_factor=True,
        auth_check_unasked=True,
        query_mode="resubmit",
        cancel_intimation="initimationNumber",
        status_enquiry=False,
        biometric_required=True,
        member_scheme="pmjay",
        desk="nhcx-payer-service",
        workflows=PMJAY_WORKFLOWS,
    ),
    "kyrocare": Adapter(
        key="kyrocare",
        name="Sandbox Payer",
        payer_system="https://kyro.care/fhir",
        procedure_factor=True,
        auth_check_unasked=True,
        desk="irdai-payer",
        workflows=OTHER_WORKFLOWS,
    ),
    "generic": Adapter(
        key="generic",
        name="Generic",
        payer_system="https://nhcx.abdm.gov.in",
        workflows=OTHER_WORKFLOWS,
    ),
}


def code_key(code) -> str:
    """The numeric part of a participant code (``1518@hcx`` -> ``1518``)."""
    text = str(code or "").strip()
    digits = re.match(r"\d+", text)
    return digits.group(0) if digits else text.split("@")[0].lower()


def _mapping(value) -> dict:
    if isinstance(value, dict):
        return {str(k): str(v) for k, v in value.items()}
    text = str(value or "").strip()
    if not text:
        return {}
    if text.startswith("{"):
        try:
            return {str(k): str(v) for k, v in json.loads(text).items()}
        except ValueError:
            logger.warning("nhcx: unreadable JSON mapping %r", text[:80])
            return {}
    out = {}
    for raw in text.split(","):
        key, _, val = raw.partition("=")
        if key.strip() and val.strip():
            out[key.strip()] = val.strip()
    return out


def configured_adapters() -> dict:
    """``{numeric code: adapter key}`` from settings."""
    rows = _mapping(getattr(settings, "NHCX_PAYER_ADAPTERS", ""))
    return {code_key(k): v for k, v in rows.items()}


def registry_name(payer_code) -> str:
    """The payer's registered name (G4 registry, cached by services.common)."""
    from care.nhcx.services.common import payer_name

    try:
        return payer_name(payer_code) or ""
    except Exception:
        logger.info("nhcx: registry name lookup failed for %s", payer_code)
        return ""


def adapter_for(payer_code, *, name: str | None = None) -> Adapter:
    """The adapter for a payer participant code (a configuration row wins)."""
    row = configured_adapters().get(code_key(payer_code))
    if row and row in ADAPTERS:
        return ADAPTERS[row]
    if payer_code or name:
        registered = name if name is not None else registry_name(payer_code)
        if (registered or "").lstrip().upper().startswith("SHA"):
            return ADAPTERS["pmjay"]
    return ADAPTERS["generic"]


def adapter_for_claim(claim) -> Adapter:
    return adapter_for(getattr(claim, "payer_id", "") or "")


def workflow_overrides() -> dict:
    return _mapping(getattr(settings, "NHCX_WORKFLOW_OVERRIDES", ""))


def workflow_id(adapter: Adapter, kind: str, *, default: str | None = None) -> str:
    """Environment override, else the adapter's table, else the PMJAY table.

    Raises ``ValueError`` with the spec's message when no table defines it
    (and no ``default`` is given).
    """
    override = workflow_overrides().get(kind)
    if override:
        return override
    if kind in adapter.workflows:
        value = adapter.workflows[kind]
    else:
        value = PMJAY_WORKFLOWS.get(kind)
    if value:
        return value
    if default:
        return default
    raise ValueError(NO_WORKFLOW.format(kind=kind))


def has_workflow(adapter: Adapter, kind: str) -> bool:
    if workflow_overrides().get(kind):
        return True
    if kind in adapter.workflows:
        return bool(adapter.workflows[kind])
    return bool(PMJAY_WORKFLOWS.get(kind))


def use_case_for(kind: str) -> str:
    return USE_CASES.get(kind, "New")


def status_for(kind: str) -> str:
    return "response.complete" if kind in RESPONSE_KINDS else "request.initiated"


def intimation_input(adapter: Adapter, action: str) -> str:
    if action == "cancel":
        return adapter.cancel_intimation
    return adapter.reprocess_intimation


__all__ = [
    "ADAPTERS",
    "Adapter",
    "adapter_for",
    "adapter_for_claim",
    "code_key",
    "has_workflow",
    "intimation_input",
    "registry_name",
    "status_for",
    "use_case_for",
    "workflow_id",
]
