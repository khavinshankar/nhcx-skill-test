"""A5 claim (incl. the LAMA / DAMA rule), S11 discharge, A6 reprocess,
release and claim-leg status. The claim leg's next_send answer is served by
services.preauth's hook through :func:`send_kind`.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from care.nhcx.fhir.build import claim as claim_builder
from care.nhcx.fhir.inputs import ClaimInput, TaskInput
from care.nhcx.models import ClaimDocument, ClaimPreauth, ClaimSubmission
from care.nhcx.services import _gather, common, payers, stage
from care.nhcx.services import preauth as preauth_service

logger = logging.getLogger(__name__)

PATH = "v1/claim/submit"

NO_REPLY = "Write the reply to the payer's query before answering it."
NO_DISCHARGE = "Record how the patient was discharged before claiming."
NO_PREAUTH = "A claim goes in against an approved pre-authorisation."
DECIDED = (
    "The payer has decided this claim; it goes back for another look as a reprocess "
    "request, not as a claim sent again."
)
WITH_PAYER = "The claim is with the payer; wait for its answer before sending again."

DISCHARGE_LOCKED = (
    "The claim is with the payer; wait for its answer before changing the discharge."
)
NO_MODE = "Choose how the patient was discharged."
NO_STAGE = "Choose whether that was before, during or after surgery."
NO_DISCHARGE_DATE = "Enter the discharge date."
DISCHARGE_BEFORE_ADMISSION = "The discharge date cannot be before the admission date."
SURGERY_BEFORE_ADMISSION = "The surgery date cannot be before the admission date."
DISCHARGE_BEFORE_SURGERY = "The discharge date cannot be before the surgery date."
NO_DEATH = "Enter the date and time of death."
NO_DEATH_TIME = "Enter the time of death as well as the date."
DISCHARGE_RECORDED = "Discharge recorded."

NOT_DECIDED = "Only a claim the payer has decided can be sent back for reprocessing."
PAID_IN_FULL = "A claim that has been paid in full cannot be reprocessed."
NO_REPROCESS_REASON = "Say why the claim should be looked at again."
BAD_REPROCESS_CODE = "Choose why the claim is being sent back."
FOREIGN_DOCUMENT = "That document is not on this claim."
RELEASE_NOT_DECIDED = "Only a decided claim can have its balance asked for."
NO_BALANCE = "A claim that has been paid in full has no balance."
NO_AMOUNT = "Say how much of the claim is still owed."

DECIDED_STATES = {"rejected", "partial", "approved"}
LAMA_MODES = {"lama", "dama"}
EARLY_STAGES = {"Before Surgery", "During Surgery"}


def _s(value) -> str:
    return "" if value is None else str(value).strip()


def submission(claim):
    return ClaimSubmission.objects.filter(claim=claim).first()


def send_kind(claim) -> str:
    state = submission(claim)
    if state is None or state.status == "draft":
        return "claim"
    if state.status == "error":
        if state.submission_kind in {"claim_query_response", "claim_resubmit"}:
            return state.submission_kind
        return "claim"
    if state.status == "queried":
        return "claim_query_response"
    if state.status in DECIDED_STATES:
        if not payers.has_workflow(payers.adapter_for_claim(claim), "claim_resubmit"):
            raise common.ServiceRefusal(DECIDED)
        return "claim_resubmit"
    if state.status == "submitting":
        raise common.ServiceRefusal(WITH_PAYER)
    return "claim"


def is_lama(state) -> bool:
    return (
        state is not None
        and state.discharge_mode in LAMA_MODES
        and state.discharge_stage in EARLY_STAGES
    )


# ---- S11 discharge ----


def _moment(value):
    if value in (None, ""):
        return None, False
    if isinstance(value, datetime):
        return value, True
    if isinstance(value, date):
        return timezone.make_aware(datetime(value.year, value.month, value.day)), False  # noqa: DTZ001
    text = _s(value)
    moment = parse_datetime(text)
    if moment is not None:
        if timezone.is_naive(moment):
            moment = timezone.make_aware(moment)
        return moment, True
    day = parse_date(text[:10])
    if day is None:
        return None, False
    return timezone.make_aware(datetime(day.year, day.month, day.day)), False  # noqa: DTZ001


def _day(value):
    if value is None:
        return None
    return value.date() if isinstance(value, datetime) else value


def record_discharge(claim, data) -> ClaimSubmission:  # noqa: PLR0912
    """S11 discharge card: validates, saves; opens the claim in draft."""
    from care.nhcx.models.legs import DischargeMode, DischargeStage

    claim = common.get_claim(claim)
    state = submission(claim)
    if state is not None and state.status == "submitting":
        raise common.ServiceRefusal(DISCHARGE_LOCKED)
    mode = _s(data.get("discharge_mode"))
    if mode not in DischargeMode.values:
        raise common.ServiceRefusal(NO_MODE)
    when = _s(data.get("discharge_stage"))
    if when not in DischargeStage.values:
        raise common.ServiceRefusal(NO_STAGE)
    discharge, _ = _moment(data.get("discharge_date"))
    if discharge is None:
        raise common.ServiceRefusal(NO_DISCHARGE_DATE)
    admission = _day(claim.admission_date)
    if admission and _day(discharge) < admission:
        raise common.ServiceRefusal(DISCHARGE_BEFORE_ADMISSION)
    surgery, _ = _moment(data.get("surgery_date"))
    if surgery is not None:
        if admission and _day(surgery) < admission:
            raise common.ServiceRefusal(SURGERY_BEFORE_ADMISSION)
        if _day(discharge) < _day(surgery):
            raise common.ServiceRefusal(DISCHARGE_BEFORE_SURGERY)
    death = None
    if mode == "death":
        raw = data.get("death_date")
        death, timed = _moment(raw)
        if death is None:
            raise common.ServiceRefusal(NO_DEATH)
        if not timed:
            raise common.ServiceRefusal(NO_DEATH_TIME)
    if state is None:
        state = ClaimSubmission(claim=claim, status="draft")
    elif state.status == "error":
        state.status = "draft"
    state.discharge_mode = mode
    state.discharge_stage = when
    state.discharge_date = discharge
    state.surgery_date = surgery
    state.death_date = death
    state.save()
    stage.recompute(claim)
    return state


# ---- A5 ----


def submit_claim(claim, reply="") -> ClaimSubmission:
    claim = common.get_claim(claim)
    kind = send_kind(claim)
    state = submission(claim)
    answering = kind == "claim_query_response"
    question = (
        (_s(state.query_note) or _s(state.disposition)) if answering and state else ""
    )
    answer = None
    if answering:
        answer = _s(reply)
        if not answer:
            raise common.ServiceRefusal(NO_REPLY)
    if state is None or not state.discharge_mode:
        raise common.ServiceRefusal(NO_DISCHARGE)
    granted = ClaimPreauth.objects.filter(claim=claim).first()
    if granted is None or granted.status not in {"approved", "queried"}:
        raise common.ServiceRefusal(NO_PREAUTH)
    org = _gather.facility(claim)
    diagnoses, practitioners, lines = _gather.check_draft(claim)
    adapter = payers.adapter_for_claim(claim)
    forms = _gather.form_inputs(claim, "claim")
    lama = is_lama(state)
    data = ClaimInput(
        kind="claim-queryupdate" if answering else "claim",
        claim_no=claim.claim_no,
        patient=common.patient_input(claim),
        facility=org,
        payer=common.payer_input(claim),
        coverage=common.coverage_input(claim),
        practitioners=practitioners,
        diagnoses=diagnoses,
        lines=lines,
        documents=_gather.documents(claim, "claim"),
        discharge_summary=_gather.discharge_summary(claim),
        forms=forms,
        answers=_gather.answers(claim, "claim", forms) if forms else [],
        admission_date=claim.admission_date,
        expected_discharge_date=claim.expected_discharge_date,
        discharge_mode=_s(state.discharge_mode),
        discharge_stage=_s(state.discharge_stage),
        discharge_date=state.discharge_date,
        surgery_date=state.surgery_date,
        death_date=state.death_date,
        preauth_ref=_s(granted.preauth_ref),
        reply_text=answer or "",
        procedure_types=_gather.procedure_types(claim),
        lama_package=_gather.lama_package(claim) if lama else None,
        program_code=adapter.program_code,
        procedure_factor=adapter.procedure_factor,
        created=timezone.now(),
    )
    bundle = preauth_service.build_bundle(claim_builder, data)
    total = claim_total(bundle, lines)
    workflow = preauth_service.workflow_for(adapter, kind)
    extra = {"x-hcx-use_case": payers.use_case_for(kind)}
    extra.update(_gather.biometric_headers(claim, "claim"))
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
    values = {
        "status": "submitting",
        "txn_id": ack.txn_id,
        "correlation_id": ack.correlation_id,
        "submitted_at": timezone.now(),
        "settled_at": None,
        "error_message": None,
        "claim_ref": claim.claim_no,
        "outcome": None,
        "adjudication": None,
        "disposition": None,
        "approved_amount": None,
        "eligible_amount": None,
        "submitted_amount": None,
        "items_json": None,
        "requested_amount": total,
        "submission_kind": kind,
        "workflow_id": workflow,
        "request_json": bundle,
        "response_json": None,
        "reply_text": answer,
        "api_call_id": None,
        "preauth_ref": _s(granted.preauth_ref) or None,
    }
    if question:
        values["query_note"] = question
    if ack.failed:
        values["status"] = "error"
        values["error_message"] = ack.failed
        if kind == "claim_query_response":
            values["status"] = "queried"
            values["disposition"] = question or None
    for key, value in values.items():
        setattr(state, key, value)
    state.save()
    stage.recompute(claim)
    logger.info(
        "nhcx: claim %s claim=%s corr=%s failed=%s",
        kind,
        claim.claim_no,
        ack.correlation_id,
        bool(ack.failed),
    )
    if ack.failed:
        raise common.ServiceRefusal(ack.failed)
    return state


def claim_total(bundle, lines):
    """The Claim's own total (it reflects the LAMA collapse), else the lines'."""
    from care.nhcx.fhir import bundle as fb

    try:
        resource = fb.find_resource(bundle, "Claim") or {}
        value = (resource.get("total") or {}).get("value")
        if value is not None:
            return Decimal(str(value))
    except Exception:
        logger.debug("nhcx: claim total unreadable", exc_info=True)
    return Decimal(str(_gather.total(lines)))


# ---- A6 reprocess, release, status ----


def _paid_in_full(state) -> bool:
    paid = stage.paid_total(state.claim)
    return (
        bool(paid)
        and state.requested_amount is not None
        and paid >= state.requested_amount
    )


def ask_reprocess(claim, reason, reason_code, document_ids=None):
    from care.nhcx.models.enquiry import ReprocessReasonCode

    claim = common.get_claim(claim)
    state = submission(claim)
    if state is None or state.status not in DECIDED_STATES:
        raise common.ServiceRefusal(NOT_DECIDED)
    if _paid_in_full(state):
        raise common.ServiceRefusal(PAID_IN_FULL)
    reason = _s(reason)
    if not reason:
        raise common.ServiceRefusal(NO_REPROCESS_REASON)
    claim, org, payer = preauth_service.task_parties(claim)
    adapter = payers.adapter_for_claim(claim)
    reason_code = _s(reason_code)
    if (
        reason_code not in ReprocessReasonCode.values
        or reason_code not in adapter.reprocess_reasons
    ):
        raise common.ServiceRefusal(BAD_REPROCESS_CODE)
    claim_ref, _thread = preauth_service.leg_reference(claim, "claim")
    ids = [_s(i) for i in (document_ids or []) if _s(i)]
    documents = []
    for doc_id in ids:
        doc = _document(claim, doc_id)
        if doc is None:
            raise common.ServiceRefusal(FOREIGN_DOCUMENT)
        documents.append(_gather.document_input(doc))
    data = TaskInput(
        action="reprocess",
        leg="claim",
        claim_no=claim_ref,
        payer=payer,
        reason=reason_code,
        note=reason,
        intimation_number=claim_ref,
        intimation_type=payers.intimation_input(adapter, "reprocess"),
        member_id=_s(claim.member_id),
        member_scheme=adapter.member_scheme,
        documents=documents,
    )
    return preauth_service.send_enquiry(
        claim,
        "reprocess",
        "claim",
        org,
        preauth_service.workflow_for(adapter, "reprocess"),
        data,
        reason,
        reason_code=reason_code,
        document_ids=ids,
    )


def _document(claim, doc_id):
    qs = ClaimDocument.objects.filter(claim=claim)
    try:
        if doc_id.isdigit():
            return qs.filter(id=int(doc_id)).first()
        return qs.filter(external_id=doc_id).first()
    except Exception:
        return None


def ask_release(claim, amount, note=""):
    claim = common.get_claim(claim)
    state = submission(claim)
    if state is None or state.status not in {"approved", "partial"}:
        raise common.ServiceRefusal(RELEASE_NOT_DECIDED)
    if _paid_in_full(state):
        raise common.ServiceRefusal(NO_BALANCE)
    try:
        value = Decimal(_s(amount))
    except (InvalidOperation, ValueError):
        value = None
    if value is None or not value.is_finite() or value <= 0:
        raise common.ServiceRefusal(NO_AMOUNT)
    claim, org, payer = preauth_service.task_parties(claim)
    adapter = payers.adapter_for_claim(claim)
    claim_ref, _thread = preauth_service.leg_reference(claim, "claim")
    note = _s(note)
    data = TaskInput(
        action="release",
        leg="claim",
        claim_no=claim_ref,
        payer=payer,
        note=note,
        amount=value,
        intimation_number=claim_ref,
        intimation_type=payers.intimation_input(adapter, "release"),
        member_id=_s(claim.member_id),
        member_scheme=adapter.member_scheme,
    )
    return preauth_service.send_enquiry(
        claim,
        "release",
        "claim",
        org,
        preauth_service.workflow_for(adapter, "release"),
        data,
        note,
        amount=value,
    )


def ask_status(claim, leg="claim"):
    return preauth_service.ask_status(claim, leg)


def enquire(
    claim,
    action,
    leg="",
    reason="",
    note="",
    amount=None,
    reason_code="",
    document_ids=None,
):
    """The enquiry endpoint's single door."""
    if action == "status":
        return preauth_service.ask_status(claim, _s(leg))
    if action == "reprocess":
        return ask_reprocess(claim, reason or note, reason_code, document_ids)
    if action == "release":
        return ask_release(claim, amount, note or reason)
    raise common.ServiceRefusal(preauth_service.BAD_STAGE)
