"""A4 pre-authorisation (all send kinds) and predetermination; A6 cancel and
status enquiry. Registers the A17 hooks (next_send, enhancement_lines,
required_documents, required_forms) at import.
"""

from __future__ import annotations

import logging

from django.utils import timezone

from care.nhcx.fhir.build import claim as claim_builder
from care.nhcx.fhir.build import task as task_builder
from care.nhcx.fhir.inputs import ClaimInput, TaskInput
from care.nhcx.models import (
    ClaimEnquiry,
    ClaimPreauth,
    ClaimPredetermination,
)
from care.nhcx.services import _gather, common, hooks, payers, stage

logger = logging.getLogger(__name__)

PATH = "v1/preauth/submit"
TASK_PATH = "v1/task/submit"
PREDETERMINATION_WORKFLOW = "12"
STATUS_WORKFLOW = "13"

NOT_ELIGIBLE = (
    "Submit a preauth only after the payer has confirmed the policy is eligible."
)
NO_REPLY = "Write the reply to the payer's query before answering it."
DECIDED = (
    "The pre-authorisation is already decided; add a line to ask for an enhancement."
)
WITH_PAYER = (
    "The pre-authorisation is with the payer; wait for its answer before sending again."
)
QUOTE_NOT_ELIGIBLE = (
    "Ask for a quote only after the payer has confirmed the policy is eligible."
)
QUOTE_WAITING = (
    "A quote is already with the payer; wait for its answer before asking again."
)

NOTHING_TO_CANCEL = "There is no pre-authorisation to cancel."
NOT_CANCELLABLE = "A pre-authorisation that is {status} cannot be cancelled."
NO_CANCEL_REASON = "Choose why the pre-authorisation is being cancelled."
NO_OTHER_NOTE = (
    "Describe the reason, with \u201cOther reason\u201d the note is the only thing "
    "the payer can read."
)
TASK_SETTINGS = (
    "Set the facility's HFR ID and NHCX participant code under Settings first."
)
BAD_STAGE = "Ask about the pre-authorisation or the claim."
NO_STATUS = (
    "{name} answers no status enquiry over NHCX; read where the case stands on its own "
    "desk, and the verdict arrives on this thread."
)
CLAIM_NOT_SENT = "The claim has not been submitted yet."
PREAUTH_NOT_SENT = "No pre-authorisation has been sent yet."

CANCELLABLE = {"submitting", "approved", "partial", "queried"}
ENHANCEMENT_KINDS = {"enhancement", "enhancement_resubmit"}
QUERY_KINDS = {"enhancement_resubmit", "preauth_query_response"}
BUILDER_KIND = {
    "preauth": "preauth",
    "preauth_resubmit": "preauth",
    "enhancement": "enhancement",
    "enhancement_resubmit": "preauth-queryupdate",
    "preauth_query_response": "preauth-queryupdate",
}
STATUS_LABELS = {
    "submitting": "submitted",
    "cancelling": "being cancelled",
}


def _s(value) -> str:
    return "" if value is None else str(value).strip()


def existing(claim):
    return ClaimPreauth.objects.filter(claim=claim).first()


def workflow_for(adapter, kind, default=None) -> str:
    try:
        return payers.workflow_id(adapter, kind, default=default)
    except ValueError as e:
        raise common.ServiceRefusal(str(e)) from e


def build_bundle(builder, data):
    try:
        return builder.build(data)
    except common.ServiceRefusal:
        raise
    except Exception as e:  # FhirBuildError and friends: shown as written
        raise common.ServiceRefusal(str(e) or type(e).__name__) from e


# ---- send kind (A4 preauth_send_kind) ----


def sent_codes(bundle) -> set:
    """Every item productOrService and modifier code of the last sent Claim."""
    from care.nhcx.fhir import bundle as fb

    codes = set()
    if not bundle:
        return codes
    try:
        resource = fb.find_resource(bundle, "Claim")
    except Exception:
        resource = None
    for item in (resource or {}).get("item") or []:
        for concept in [item.get("productOrService"), *(item.get("modifier") or [])]:
            for c in (concept or {}).get("coding") or []:
                if c.get("code"):
                    codes.add(str(c["code"]).strip())
    return codes


def added_lines(claim, row=None):
    row = row if row is not None else existing(claim)
    sent = sent_codes(row.request_json if row is not None else None)
    return [line for line in claim.lines.order_by("seq", "id") if line.code not in sent]


def send_kind(claim) -> str:
    row = existing(claim)
    if row is None or row.status in {"cancelled", "error"}:
        return "preauth"
    if row.status in {"approved", "partial"}:
        if not added_lines(claim, row):
            raise common.ServiceRefusal(DECIDED)
        return "enhancement"
    if row.status == "queried":
        if (row.enhancement_no or 0) > 0 and row.submission_kind in ENHANCEMENT_KINDS:
            return "enhancement_resubmit"
        return "preauth_query_response"
    if row.status == "rejected":
        return "preauth"
    if row.status in {"submitting", "cancelling"}:
        raise common.ServiceRefusal(WITH_PAYER)
    return "preauth"


# ---- gather + build ----


def claim_input(claim, kind, *, builder_kind, reply="", with_forms=True) -> tuple:
    org = _gather.facility(claim)
    diagnoses, practitioners, lines = _gather.check_draft(claim)
    adapter = payers.adapter_for_claim(claim)
    forms = _gather.form_inputs(claim, "preauth") if with_forms else []
    data = ClaimInput(
        kind=builder_kind,
        claim_no=claim.claim_no,
        patient=common.patient_input(claim),
        facility=org,
        payer=common.payer_input(claim),
        coverage=common.coverage_input(claim),
        practitioners=practitioners,
        diagnoses=diagnoses,
        lines=lines,
        documents=_gather.documents(claim, "preauth"),
        forms=forms,
        answers=_gather.answers(claim, "preauth", forms) if forms else [],
        admission_date=claim.admission_date,
        expected_discharge_date=claim.expected_discharge_date,
        preauth_ref="",
        reply_text=reply,
        procedure_types=_gather.procedure_types(claim),
        program_code=adapter.program_code,
        procedure_factor=adapter.procedure_factor,
        created=timezone.now(),
    )
    return data, org, adapter, _gather.total(lines)


def submit_preauth(claim, reply="") -> ClaimPreauth:  # noqa: PLR0912
    claim = common.get_claim(claim)
    if claim.status != "eligible":
        raise common.ServiceRefusal(NOT_ELIGIBLE)
    row = existing(claim)
    kind = send_kind(claim)
    answer = None
    if kind in QUERY_KINDS:
        answer = _s(reply)
        if not answer:
            raise common.ServiceRefusal(NO_REPLY)

    from care.nhcx.services import eligibility

    eligibility.ensure_auth_requirements(claim)

    data, org, adapter, total = claim_input(
        claim, kind, builder_kind=BUILDER_KIND[kind], reply=answer or ""
    )
    if row is not None and kind != "preauth":
        data.preauth_ref = _s(row.preauth_ref)
    bundle = build_bundle(claim_builder, data)
    workflow = workflow_for(adapter, kind)
    extra = {"x-hcx-use_case": payers.use_case_for(kind)}
    extra.update(_gather.biometric_headers(claim, "preauth"))
    envelope = {
        "jwe_headers": common.headers(
            claim,
            workflow,
            sender=org.participant_code,
            status=payers.status_for(kind),
            extra=extra,
        ),
        "fhir": bundle,
    }
    ack = common.send(PATH, envelope, claim, label=kind)
    now = timezone.now()
    values = {
        "status": "submitting",
        "txn_id": ack.txn_id,
        "correlation_id": ack.correlation_id,
        "submitted_at": now,
        "settled_at": None,
        "error_message": None,
        "claim_ref": claim.claim_no,
        "preauth_ref": None,
        "outcome": None,
        "adjudication": None,
        "disposition": None,
        "approved_amount": None,
        "eligible_amount": None,
        "submitted_amount": None,
        "items_json": None,
        "requested_amount": total,
        "submission_kind": kind,
        "reply_text": answer,
        "workflow_id": workflow,
        "request_json": bundle,
        "response_json": None,
        "api_call_id": None,
    }
    if row is not None and kind in ENHANCEMENT_KINDS:
        values["preauth_ref"] = row.preauth_ref
        values["enhancement_no"] = (row.enhancement_no or 0) + (
            1 if kind == "enhancement" else 0
        )
    elif row is not None and kind in {"preauth_resubmit", "preauth_query_response"}:
        values["preauth_ref"] = row.preauth_ref
        values["enhancement_no"] = row.enhancement_no
    if kind in ENHANCEMENT_KINDS:
        for key in (
            "settled_at",
            "outcome",
            "adjudication",
            "disposition",
            "approved_amount",
            "eligible_amount",
            "submitted_amount",
            "items_json",
        ):
            values.pop(key, None)
    if ack.failed:
        if kind in ENHANCEMENT_KINDS and row is not None:
            values = {
                "status": row.status,
                "txn_id": ack.txn_id,
                "correlation_id": ack.correlation_id,
                "submitted_at": now,
                "error_message": ack.failed,
                "submission_kind": kind,
                "workflow_id": workflow,
                "enhancement_no": values.get("enhancement_no"),
            }
        else:
            values["status"] = "error"
            values["error_message"] = ack.failed
    if row is None:
        row = ClaimPreauth(claim=claim)
    for key, value in values.items():
        setattr(row, key, value)
    row.save()
    stage.recompute(claim)
    logger.info(
        "nhcx: preauth %s claim=%s corr=%s failed=%s",
        kind,
        claim.claim_no,
        ack.correlation_id,
        bool(ack.failed),
    )
    if ack.failed:
        raise common.ServiceRefusal(ack.failed)
    return row


def ask_predetermination(claim) -> ClaimPredetermination:
    claim = common.get_claim(claim)
    if claim.status != "eligible":
        raise common.ServiceRefusal(QUOTE_NOT_ELIGIBLE)
    if ClaimPredetermination.objects.filter(claim=claim, status="asking").exists():
        raise common.ServiceRefusal(QUOTE_WAITING)
    data, org, _adapter, total = claim_input(
        claim, "predetermination", builder_kind="predetermination", with_forms=False
    )
    bundle = build_bundle(claim_builder, data)
    envelope = {
        "jwe_headers": common.headers(
            claim,
            PREDETERMINATION_WORKFLOW,
            sender=org.participant_code,
            extra={"x-hcx-use_case": payers.use_case_for("predetermination")},
        ),
        "fhir": bundle,
    }
    ack = common.send(PATH, envelope, claim, label="predetermination")
    row = ClaimPredetermination.objects.create(
        claim=claim,
        status="error" if ack.failed else "asking",
        txn_id=ack.txn_id,
        correlation_id=ack.correlation_id,
        requested_at=timezone.now(),
        requested_amount=total,
        request_json=bundle,
        error_message=ack.failed,
    )
    stage.recompute(claim)
    if ack.failed:
        raise common.ServiceRefusal(ack.failed)
    return row


# ---- A6: task parties, cancel, status ----


def task_parties(claim):
    claim = common.get_claim(claim)
    org = _gather.facility(claim, TASK_SETTINGS)
    return claim, org, common.payer_input(claim)


def leg_reference(claim, leg) -> tuple:
    from care.nhcx.models import ClaimSubmission

    if leg == "claim":
        state = ClaimSubmission.objects.filter(claim=claim).first()
        if state is None or state.status == "draft":
            raise common.ServiceRefusal(CLAIM_NOT_SENT)
        return _s(state.claim_ref) or claim.claim_no, _s(state.correlation_id)
    sent = existing(claim)
    if sent is None:
        raise common.ServiceRefusal(PREAUTH_NOT_SENT)
    return _s(sent.claim_ref) or claim.claim_no, _s(sent.correlation_id)


def send_task(claim, org, workflow, data: TaskInput, *, label):
    data.facility = org
    data.authored_on = data.authored_on or timezone.now()
    bundle = build_bundle(task_builder, data)
    envelope = {
        "jwe_headers": common.headers(claim, workflow, sender=org.participant_code),
        "fhir": bundle,
    }
    return bundle, common.send(TASK_PATH, envelope, claim, label=label)


def send_enquiry(claim, kind, leg, org, workflow, data, reason="", **extra):
    bundle, ack = send_task(claim, org, workflow, data, label=kind)
    row = ClaimEnquiry.objects.create(
        claim=claim,
        kind=kind,
        stage=leg,
        txn_id=ack.txn_id,
        correlation_id=ack.correlation_id,
        requested_at=timezone.now(),
        status="error" if ack.failed else "asking",
        reason=reason or None,
        request_json=bundle,
        error_message=ack.failed,
        **extra,
    )
    if ack.failed:
        raise common.ServiceRefusal(ack.failed)
    return row


def _status_label(status) -> str:
    return STATUS_LABELS.get(status, _s(status).lower() or "unsent")


def cancel_preauth(claim, reason, note="") -> ClaimPreauth:
    from care.nhcx.models.legs import CancelReason

    claim = common.get_claim(claim)
    sent = existing(claim)
    if sent is None:
        raise common.ServiceRefusal(NOTHING_TO_CANCEL)
    if sent.status not in CANCELLABLE:
        raise common.ServiceRefusal(
            NOT_CANCELLABLE.format(status=_status_label(sent.status))
        )
    reason = _s(reason)
    if reason not in CancelReason.values:
        raise common.ServiceRefusal(NO_CANCEL_REASON)
    note = _s(note)
    if reason == "other" and not note:
        raise common.ServiceRefusal(NO_OTHER_NOTE)
    claim, org, payer = task_parties(claim)
    adapter = payers.adapter_for_claim(claim)
    data = TaskInput(
        action="cancel",
        leg="preauth",
        claim_no=claim.claim_no,
        payer=payer,
        reason=reason,
        note=note,
        intimation_number=claim.claim_no,
        intimation_type=payers.intimation_input(adapter, "cancel"),
    )
    _bundle, ack = send_task(
        claim, org, workflow_for(adapter, "cancel"), data, label="cancel"
    )
    sent.pre_cancel_status = sent.status
    sent.status = "error" if ack.failed else "cancelling"
    sent.cancel_txn_id = ack.txn_id
    sent.cancel_correlation_id = ack.correlation_id
    sent.cancel_requested_at = timezone.now()
    sent.cancel_reason = reason
    sent.cancel_note = note or None
    sent.error_message = ack.failed
    sent.save()
    stage.recompute(claim)
    if ack.failed:
        raise common.ServiceRefusal(ack.failed)
    return sent


def ask_status(claim, leg) -> ClaimEnquiry:
    claim = common.get_claim(claim)
    if leg not in {"preauth", "claim"}:
        raise common.ServiceRefusal(BAD_STAGE)
    adapter = payers.adapter_for_claim(claim)
    if not adapter.status_enquiry:
        raise common.ServiceRefusal(NO_STATUS.format(name=adapter.name))
    claim_ref, thread = leg_reference(claim, leg)
    claim, org, payer = task_parties(claim)
    data = TaskInput(action="status", leg=leg, claim_no=claim_ref, payer=payer)
    return send_enquiry(claim, "status", leg, org, thread or STATUS_WORKFLOW, data)


# ---- A17 hooks ----


def _next_send(claim, leg):
    try:
        if leg == "claim":
            from care.nhcx.services import claim as claim_service

            return claim_service.send_kind(claim)
        return send_kind(claim)
    except common.ServiceRefusal as e:
        return {"refused": e.message}


def _enhancement_lines(claim):
    row = existing(claim)
    if row is None or row.status not in {"approved", "partial"}:
        return []
    return added_lines(claim, row)


def _required_documents(claim, leg_stage):
    return _gather.required_documents(claim, leg_stage)


def _required_forms(claim, leg_stage):
    return _gather.required_forms(claim, leg_stage)


hooks.register("next_send", _next_send)
hooks.register("enhancement_lines", _enhancement_lines)
hooks.register("required_documents", _required_documents)
hooks.register("required_forms", _required_forms)

# A18 registers the extra_headers hook at import; preauth is loaded by AppConfig.ready
from care.nhcx.services import biometric as _biometric  # noqa: E402, F401
