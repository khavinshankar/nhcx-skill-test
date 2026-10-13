"""S4/S9 draft saves (D17 answers, D25 diagnoses, D26 care team, D27 lines, dates)
and D28 document upload/removal, for the legs API."""

from __future__ import annotations

from datetime import date

from django.db import transaction
from django.utils.dateparse import parse_date

from care.nhcx.models import (
    ClaimCareTeam,
    ClaimDiagnosis,
    ClaimDocument,
    ClaimFormAnswer,
)
from care.nhcx.models.base import LegStage
from care.nhcx.models.draft import CareTeamRole
from care.nhcx.services import common, stage
from care.nhcx.services.communication import store_upload

DRAFT_SAVED = "Pre-authorisation draft saved."
ANSWERS_SAVED = "Answers saved."
BAD_ROLE = "Choose a valid care team role."
NO_ADMISSION_DATE = "Enter the admission date."
DISCHARGE_BEFORE_ADMISSION = (
    "The provisional discharge date cannot be before the admission date."
)
NO_DOCTOR = "Add at least one doctor to the care team."
UNKNOWN_DOCTOR = "That doctor is not a user of this application."
NO_ANSWER_KEY = "Each answer names its form and question."
DOCUMENT_REMOVED = "Document removed."
NO_SUCH_DOCUMENT = "That document is not on this claim."
BAD_DATE = "Enter dates as YYYY-MM-DD."


def _s(value) -> str:
    return "" if value is None else str(value).strip()


def _date(value):
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    parsed = parse_date(_s(value)[:10])
    if parsed is None:
        raise common.ServiceRefusal(BAD_DATE)
    return parsed


def _dates(claim, data, fields):
    admitted = claim.admission_date
    leaving = claim.expected_discharge_date
    if "admission_date" in data:
        admitted = _date(data.get("admission_date"))
        if admitted is None:
            raise common.ServiceRefusal(NO_ADMISSION_DATE)
        fields["admission_date"] = admitted
    if "expected_discharge_date" in data:
        leaving = _date(data.get("expected_discharge_date"))
        fields["expected_discharge_date"] = leaving
    a = admitted.date() if hasattr(admitted, "date") else admitted
    b = leaving.date() if hasattr(leaving, "date") else leaving
    if a and b and b < a:
        raise common.ServiceRefusal(DISCHARGE_BEFORE_ADMISSION)


def _diagnoses(rows):
    out = []
    for i, given in enumerate(rows or [], start=1):
        d = given or {}
        if not (_s(d.get("icd10_code")) or _s(d.get("snomed_code"))):
            continue
        out.append(
            ClaimDiagnosis(
                seq=i,
                snomed_code=_s(d.get("snomed_code")) or None,
                snomed_display=_s(d.get("snomed_display")) or None,
                icd10_code=_s(d.get("icd10_code")),
                icd10_display=_s(d.get("icd10_display")) or None,
            )
        )
    return out


def _team(rows):
    from care.users.models import User

    out = []
    for i, given in enumerate(rows or [], start=1):
        m = given or {}
        role = _s(m.get("role"))
        if role not in CareTeamRole.values:
            raise common.ServiceRefusal(BAD_ROLE)
        ref = _s(m.get("practitioner") or m.get("user_id") or m.get("user"))
        users = User.objects.all()
        user = (
            users.filter(id=int(ref)).first()
            if ref.isdigit()
            else users.filter(external_id=ref).first()
            if ref
            else None
        )
        if user is None:
            raise common.ServiceRefusal(UNKNOWN_DOCTOR)
        out.append(ClaimCareTeam(seq=i, practitioner=user, role=role))
    if rows is not None and not out:
        raise common.ServiceRefusal(NO_DOCTOR)
    return out


def _answers(claim, rows, default_stage):
    out = []
    for given in rows or []:
        a = given or {}
        url, link = _s(a.get("form_url")), _s(a.get("link_id"))
        if not url or not link:
            raise common.ServiceRefusal(NO_ANSWER_KEY)
        leg = _s(a.get("stage")) or default_stage
        if leg not in LegStage.values:
            leg = default_stage
        out.append((url, link, _s(a.get("answer")), leg))
    return out


def save_draft(claim, data) -> str:
    """Saves what the body carries; a list present replaces the saved one (S4)."""
    from care.nhcx.services import lines

    data = data or {}
    fields: dict = {}
    _dates(claim, data, fields)
    diagnoses = _diagnoses(data["diagnoses"]) if "diagnoses" in data else None
    team = _team(data["care_team"]) if "care_team" in data else None
    default_stage = _s(data.get("stage")) or LegStage.preauth
    answers = _answers(claim, data.get("answers"), default_stage)
    only_answers = bool(answers) and not (
        fields or diagnoses is not None or team is not None or data.get("items")
    )
    with transaction.atomic():
        if fields:
            for k, v in fields.items():
                setattr(claim, k, v)
            claim.save(update_fields=[*fields, "modified_date"])
        if diagnoses is not None:
            claim.diagnoses.all().delete()
            for d in diagnoses:
                d.claim = claim
            ClaimDiagnosis.objects.bulk_create(diagnoses)
        if team is not None:
            claim.care_team.all().delete()
            for m in team:
                m.claim = claim
            ClaimCareTeam.objects.bulk_create(team)
        if data.get("items"):
            lines.update_lines(claim, data["items"])
        for url, link, answer, leg in answers:
            ClaimFormAnswer.objects.update_or_create(
                claim=claim,
                form_url=url,
                link_id=link,
                defaults={"answer": answer, "stage": leg},
            )
    stage.recompute(claim)
    return ANSWERS_SAVED if only_answers else DRAFT_SAVED


def attach(claim, upload, *, code="", category="", leg="preauth", label=""):
    leg = _s(leg) or LegStage.preauth
    if leg not in LegStage.values:
        leg = LegStage.preauth
    if upload is not None:
        upload = {**upload, "code": code, "category": category, "label": label}
    doc = store_upload(claim, leg, upload)
    if code:
        # re-choosing a file replaces what is attached for that code (S9)
        ClaimDocument.objects.filter(claim=claim, code=code, stage=leg).exclude(
            id=doc.id
        ).delete()
    return doc


def remove_document(claim, doc_id) -> str:
    deleted, _ = ClaimDocument.objects.filter(claim=claim, external_id=doc_id).delete()
    if not deleted:
        raise common.ServiceRefusal(NO_SUCH_DOCUMENT)
    return DOCUMENT_REMOVED
