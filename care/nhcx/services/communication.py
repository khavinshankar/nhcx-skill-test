"""A7. Reply to a payer query; acknowledge a payer notification (D23)."""

from __future__ import annotations

import logging

from django.utils import timezone

from care.nhcx.fhir.build import communication as f12
from care.nhcx.fhir.inputs import DocumentInput, FhirBuildError, ReplyInput
from care.nhcx.models import ClaimDocument, ClaimQuery
from care.nhcx.models.draft import MAX_DOCUMENT_SIZE, DocumentContentType
from care.nhcx.services import common, payers, stage

logger = logging.getLogger("care.nhcx")

PATH = "v1/communication/on_request"
NO_FILE = "Choose a PDF or image to attach."
BAD_TYPE = "Only JPEG image, PDF, PNG image, WebP image files can be attached."
EMPTY_FILE = "That file is empty."
TOO_LARGE = "A document may be at most 10 MB."


def _s(value) -> str:
    return "" if value is None else str(value).strip()


def check_upload(upload) -> None:
    """S9 upload rules; ``upload`` has filename, content_type and data."""
    if upload is None:
        raise common.ServiceRefusal(NO_FILE)
    content_type = _s(upload.get("content_type")).lower()
    if content_type not in DocumentContentType.values:
        raise common.ServiceRefusal(BAD_TYPE)
    data = upload.get("data") or b""
    if not data:
        raise common.ServiceRefusal(EMPTY_FILE)
    if len(data) > MAX_DOCUMENT_SIZE:
        raise common.ServiceRefusal(TOO_LARGE)


def store_upload(claim, stage_name, upload) -> ClaimDocument:
    check_upload(upload)
    data = bytes(upload["data"])
    return ClaimDocument.objects.create(
        claim=claim,
        filename=_s(upload.get("filename")) or "document",
        content_type=_s(upload.get("content_type")).lower(),
        label=_s(upload.get("label")) or None,
        code=_s(upload.get("code")) or None,
        category=_s(upload.get("category")) or None,
        stage=stage_name,
        size=len(data),
        data=data,
    )


def document_input(doc) -> DocumentInput:
    return DocumentInput(
        id=doc.id,
        filename=doc.filename,
        content_type=doc.content_type,
        label=_s(doc.label),
        code=_s(doc.code),
        category=_s(doc.category),
        stage=doc.stage,
        data=bytes(doc.data or b""),
        uploaded_at=doc.uploaded_at,
    )


def _leg(claim, stage_name):
    attr = "submission" if stage_name == "claim" else "preauth"
    try:
        return getattr(claim, attr)
    except Exception:
        return None


def reply_headers(asked, claim) -> dict:
    leg = _leg(claim, asked.stage)
    profile = common.facility_profile(claim.facility)
    return {
        "x-hcx-sender_code": _s(profile.participant_code) if profile else "",
        "x-hcx-recipient_code": _s(asked.sender_code) or common.recipient_code(claim),
        "x-hcx-correlation_id": _s(asked.correlation_id),
        "x-hcx-workflow_id": _s(asked.workflow_id)
        or _s(getattr(leg, "correlation_id", None))
        or claim.claim_no,
    }


def _reply_input(asked, claim, text="", documents=()) -> ReplyInput:
    leg = _leg(claim, asked.stage)
    return ReplyInput(
        claim_no=claim.claim_no,
        query_id=asked.id,
        kind=asked.kind,
        claim_ref=_s(asked.claim_ref) or claim.claim_no,
        reason_code=_s(asked.reason_code),
        request_id=_s(asked.request_id),
        reply_text=text,
        documents=list(documents),
        request_bundle=asked.request_json,
        sent_bundle=getattr(leg, "request_json", None),
        leg=asked.stage,
        payer_system=payers.adapter_for_claim(claim).payer_system,
        facility=common.facility_input(claim.facility),
        payer=common.payer_input(claim),
        patient=common.patient_input(claim),
        coverage=common.coverage_input(claim),
    )


def _query(query_id, claim=None) -> ClaimQuery:
    rows = ClaimQuery.objects.select_related("claim", "claim__facility")
    if claim is not None:
        rows = rows.filter(claim=claim)
    asked = rows.filter(id=query_id).first() if query_id else None
    if asked is None:
        raise common.ServiceRefusal(f12.QUERY_NOT_FOUND)
    return asked


def _send(asked, claim, bundle) -> common.Ack:
    envelope = {"jwe_headers": reply_headers(asked, claim), "fhir": bundle}
    return common.send(PATH, envelope, claim, label=f"query-{asked.id}")


def answer_query(query_id, text="", document_ids=(), uploads=(), *, claim=None):
    """Reply to an open payer query. Raises ServiceRefusal."""
    asked = _query(query_id, claim)
    if asked.kind != "query":
        raise common.ServiceRefusal(f12.NOT_A_QUESTION)
    claim = asked.claim
    ids = [int(i) for i in document_ids or []]
    for upload in uploads or ():
        check_upload(upload)
    for upload in uploads or ():
        ids.append(store_upload(claim, asked.stage, upload).id)
    ids = list(dict.fromkeys(ids))

    facility = common.facility_input(claim.facility)
    if not facility.identifier_value or not facility.participant_code:
        raise common.ServiceRefusal(f12.REPLY_SETTINGS)
    text = _s(text)
    if not text and not ids:
        raise common.ServiceRefusal(f12.EMPTY_REPLY)
    docs = {d.id: d for d in ClaimDocument.objects.filter(claim=claim, id__in=ids)}
    if len(docs) != len(ids):
        raise common.ServiceRefusal(f12.DOCUMENT_NOT_ON_CLAIM)
    try:
        bundle = f12.build(
            _reply_input(asked, claim, text, [document_input(docs[i]) for i in ids])
        )
    except FhirBuildError as e:
        raise common.ServiceRefusal(str(e)) from e

    try:
        ack = _send(asked, claim, bundle)
    except common.ServiceRefusal as e:
        _write(
            asked,
            status="error",
            error_message=e.message,
            reply_text=text or None,
            reply_documents=ids,
        )
        raise
    if ack.failed:
        _write(
            asked,
            status="error",
            error_message=ack.failed,
            reply_text=text or None,
            reply_documents=ids,
            reply_txn_id=ack.txn_id,
            reply_correlation_id=ack.correlation_id,
        )
        raise common.ServiceRefusal(ack.failed)
    _write(
        asked,
        status="answered",
        error_message=None,
        reply_text=text or None,
        reply_documents=ids,
        reply_txn_id=ack.txn_id,
        reply_correlation_id=ack.correlation_id,
        answered_at=timezone.now(),
        reply_json=bundle,
    )
    stage.recompute(claim)
    return asked


def acknowledge_notification(query_id, *, claim=None):
    """Send the payer's notification back acknowledged. Raises ServiceRefusal."""
    asked = _query(query_id, claim)
    claim = asked.claim
    try:
        if asked.kind != "notification":
            raise common.ServiceRefusal(f12.ONLY_NOTIFICATION)
        try:
            bundle = f12.build(_reply_input(asked, claim))
        except FhirBuildError as e:
            raise common.ServiceRefusal(str(e)) from e
        ack = _send(asked, claim, bundle)
    except common.ServiceRefusal as e:
        _write(asked, status="error", error_message=e.message)
        raise
    if ack.failed:
        _write(
            asked,
            status="error",
            error_message=ack.failed,
            reply_txn_id=ack.txn_id,
            reply_correlation_id=ack.correlation_id,
        )
        raise common.ServiceRefusal(ack.failed)
    _write(
        asked,
        status="acknowledged",
        error_message=None,
        reply_txn_id=ack.txn_id,
        reply_correlation_id=ack.correlation_id,
        acknowledged_at=timezone.now(),
        reply_json=bundle,
    )
    return asked


def _write(row, **values):
    for key, value in values.items():
        setattr(row, key, value)
    row.save(update_fields=[*values.keys(), "modified_date"])


def auto_acknowledge(query_id) -> None:
    """C9: acknowledge a freshly recorded notification; never raises."""
    try:
        acknowledge_notification(query_id)
    except common.ServiceRefusal as e:
        logger.info("nhcx: notification %s not acknowledged: %s", query_id, e.message)
    except Exception:
        logger.exception("nhcx: notification %s acknowledgement failed", query_id)
        ClaimQuery.objects.filter(id=query_id).update(
            status="error", error_message="The acknowledgement could not be sent."
        )
