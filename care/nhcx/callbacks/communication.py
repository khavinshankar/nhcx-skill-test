"""C9. Payer communication: a query, a notification or a note (D23)."""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from care.nhcx.callbacks import _legs, dispatch
from care.nhcx.fhir import bundle as fb
from care.nhcx.fhir.read import communication as f11
from care.nhcx.models import (
    Claim,
    ClaimPreauth,
    ClaimQuery,
    ClaimSubmission,
)
from care.nhcx.services import payers, stage

NO_REQUEST = "The payer message carries no CommunicationRequest."
NO_NOTE = "The payer message carries no Communication."


def handle(envelope, delivery=None):
    corr = _legs.corr_of(delivery, envelope)
    body = dispatch.payload(envelope)
    if _legs.is_protocol(body):
        return _legs.result(dispatch.IGNORED, "ProtocolResponse")
    unwrapped = fb.unwrap(body)
    carried = {
        (e.get("resource") or {}).get("resourceType") for e in fb.entries(unwrapped)
    }
    sender = _legs.header(envelope, "x-hcx-sender_code")
    workflow = _legs.header(envelope, "x-hcx-workflow_id")
    if "CommunicationRequest" in carried:
        return record_query(unwrapped, corr, sender, workflow)
    if "Communication" in carried:
        return record_note(unwrapped, corr, sender, workflow)
    return _legs.result(dispatch.IGNORED, "neither a request nor a note")


def leg_asked_about(claim) -> str:
    submission = ClaimSubmission.objects.filter(claim=claim).first()
    if submission is not None and submission.status and submission.status != "draft":
        return "claim"
    return "preauth"


def match_claim(references, corr, workflow):
    """C9 matching; (claim, stage or "") or (None, "")."""
    claim = None
    leg = ""
    refs = [r for r in dict.fromkeys(references) if r]
    for ref in refs:
        claim = Claim.objects.filter(claim_no=ref).first()
        if claim is None:
            row = (
                ClaimSubmission.objects.filter(claim_ref=ref)
                .order_by("-created_date")
                .first()
            ) or ClaimPreauth.objects.filter(claim_ref=ref).order_by(
                "-created_date"
            ).first()
            claim = row.claim if row else None
        if claim is not None:
            break
    if claim is None:
        for ref in refs:
            held = (
                ClaimQuery.objects.filter(request_id=ref)
                .select_related("claim")
                .order_by("-id")
                .first()
            )
            if held is not None:
                claim, leg = held.claim, held.stage
                break
    if claim is None and corr:
        claim = dispatch.claim_for_correlation(corr)
    if workflow:
        for model, name in ((ClaimSubmission, "claim"), (ClaimPreauth, "preauth")):
            row = (
                model.objects.filter(correlation_id=workflow)
                .select_related("claim")
                .first()
            )
            if row is not None and (claim is None or row.claim_id == claim.id):
                claim, leg = row.claim, leg or name
                break
    return claim, leg


def _adapter(sender, claim):
    if sender:
        return payers.adapter_for(sender)
    return payers.adapter_for_claim(claim)


def record_query(body, corr, sender, workflow):
    parsed = f11.read(body)
    if not parsed:
        raise dispatch.Rejected(NO_REQUEST)
    if corr and ClaimQuery.objects.filter(correlation_id=corr).exists():
        return _legs.result(dispatch.IGNORED, "already recorded")
    claim, leg = match_claim(parsed["refs"], corr, workflow)
    if claim is None:
        return _legs.result(dispatch.UNMATCHED, "No case answers to this message.")
    adapter = _adapter(sender, claim)
    kind = f11.classify(parsed["intent"], parsed["reason_code"], adapter.query_mode)
    asked = ClaimQuery.objects.create(
        claim=claim,
        stage=leg or leg_asked_about(claim),
        kind=kind,
        reason_code=parsed["reason_code"] or None,
        correlation_id=corr or None,
        request_id=parsed["request_id"] or None,
        claim_ref=next((r for r in parsed["refs"] if "/" not in r), None),
        sender_code=sender or None,
        workflow_id=workflow or None,
        received_at=timezone.now(),
        status="open",
        remarks="\n".join(parsed["questions"]),
        questions=parsed["questions"],
        request_json=body,
    )
    if kind == "query":
        stage.recompute(claim)
    else:
        from care.nhcx.services import communication

        transaction.on_commit(lambda: communication.auto_acknowledge(asked.id))
    return _legs.result(dispatch.SETTLED, kind)


def _note_refs(note) -> list:
    refs = list(f11.references(note))
    for key in ("inResponseTo", "partOf"):
        for item in note.get(key) or []:
            reference = item.get("reference")
            if reference:
                refs.append(reference)
                if "/" in reference:
                    refs.append(reference.rstrip("/").rsplit("/", 1)[-1])
            if item.get("display"):
                refs.append(item["display"])
            value = (item.get("identifier") or {}).get("value")
            if value:
                refs.append(value)
    return list(dict.fromkeys(str(r) for r in refs if r))


def _note_lines(note) -> list:
    lines = []
    for item in note.get("payload") or []:
        text = item.get("contentString")
        if text:
            lines += [line.strip() for line in str(text).splitlines() if line.strip()]
        attachment = item.get("contentAttachment")
        if attachment is not None:
            title = attachment.get("title") or attachment.get("contentType")
            lines.append(f"Attachment: {title}" if title else "Attachment")
    for annotation in note.get("note") or []:
        if annotation.get("text"):
            lines.append(annotation["text"])
    return list(dict.fromkeys(lines))


def record_note(body, corr, sender, workflow):
    entry = fb.find_entry(body, "Communication")
    if entry is None:
        raise dispatch.Rejected(NO_NOTE)
    parsed = f11.read_note(body)
    note = entry.get("resource") or {}
    refs = _note_refs(note)
    claim, leg = match_claim(refs, corr, workflow)
    if claim is None:
        return _legs.result(dispatch.UNMATCHED, "No case answers to this message.")
    note_id = parsed.get("request_id") or ""
    if (
        note_id
        and ClaimQuery.objects.filter(
            claim=claim, kind="note", request_id=note_id
        ).exists()
    ):
        return _legs.result(dispatch.IGNORED, "already recorded")
    thread = (
        corr
        if corr and not ClaimQuery.objects.filter(correlation_id=corr).exists()
        else None
    )
    task = fb.find_resource(body, "Task")
    reason = f11.reason_code(task) or f11.reason_code(note)
    lines = _note_lines(note)
    ClaimQuery.objects.create(
        claim=claim,
        stage=leg or leg_asked_about(claim),
        kind="note",
        reason_code=reason or None,
        correlation_id=thread,
        request_id=note_id or None,
        claim_ref=parsed.get("claim_ref")
        or next((r for r in refs if "/" not in r), None),
        sender_code=sender or None,
        workflow_id=workflow or None,
        received_at=timezone.now(),
        status="noted",
        remarks="\n".join(lines),
        questions=lines,
        request_json=body,
    )
    return _legs.result(dispatch.SETTLED, "note")
