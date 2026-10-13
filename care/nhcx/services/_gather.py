"""What A4 and A5 gather from the draft before building a Claim bundle.

Refusals are raised in the spec's order; the D12 forms rule and the required
documents (A17 hooks) live here too.
"""

from __future__ import annotations

import uuid

from care.nhcx.fhir.inputs import DiagnosisInput, DocumentInput, FormAnswer, FormInput
from care.nhcx.models import ClaimDocument, ClaimFormAnswer
from care.nhcx.services import common, payers

SETTINGS = "Set the facility's HFR ID and NHCX participant code under Settings before submitting."
NO_ENCOUNTER = "Link the admitted patient before submitting."
NO_ADMISSION = "Enter the admission date on the preauth draft."
NO_DIAGNOSIS = "Quote at least one ICD-10 diagnosis."
NO_DOCTOR = "Add at least one doctor to the care team."
NO_LINE = "Add at least one line, the procedure being done."

CONSENT_FORMS = {
    "preauth": {
        "id": "100024",
        "title": "Authentication Consent",
        "items": [
            {
                "linkId": "100093",
                "type": "attachment",
                "text": "Medical Superintendent Declaration Form (During Admission)",
                "required": True,
                "depth": 0,
            },
            {
                "linkId": "100095",
                "type": "string",
                "text": "Remarks",
                "required": False,
                "depth": 0,
            },
        ],
    },
    "claim": {
        "id": "100466",
        "title": "Discharge Consent",
        "items": [
            {
                "linkId": "135477",
                "type": "attachment",
                "text": "Medical Superintendent Declaration Form (During Discharge)",
                "required": True,
                "depth": 0,
            }
        ],
    },
}
CONSENT_URL = "https://payer.gov.in/policy/questionnaire/{id}"
BIOMETRIC_STAGE = {"preauth": "Preauth", "claim": "Discharge"}


def _s(value) -> str:
    return "" if value is None else str(value).strip()


def _one(claim, attr):
    try:
        return getattr(claim, attr)
    except Exception:
        return None


def facility(claim, message=SETTINGS):
    data = common.facility_input(claim.facility)
    if not data.identifier_value or not data.participant_code:
        raise common.ServiceRefusal(message)
    return data


def check_draft(claim):
    """Refusals 5 to 9 of A4 (6 to 10 of A5); returns (diagnoses, practitioners, lines)."""
    if not claim.encounter_id:
        raise common.ServiceRefusal(NO_ENCOUNTER)
    if not claim.admission_date:
        raise common.ServiceRefusal(NO_ADMISSION)
    diagnoses = [
        DiagnosisInput(
            icd10_code=d.icd10_code, icd10_display=_s(d.icd10_display), seq=d.seq
        )
        for d in claim.diagnoses.order_by("seq", "id")
    ]
    if not diagnoses:
        raise common.ServiceRefusal(NO_DIAGNOSIS)
    practitioners = common.practitioner_inputs(claim)
    if not practitioners:
        raise common.ServiceRefusal(NO_DOCTOR)
    lines = common.line_inputs(claim)
    if not lines:
        raise common.ServiceRefusal(NO_LINE)
    return diagnoses, practitioners, lines


def total(lines) -> float:
    out = 0.0
    for line in lines:
        if line.amount not in (None, ""):
            out += float(line.amount)
        elif line.unit_price not in (None, ""):
            out += float(line.unit_price) * float(line.quantity or 1)
    return round(out, 2)


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


def documents(claim, stage) -> list:
    return [
        document_input(d)
        for d in ClaimDocument.objects.filter(claim=claim, stage=stage).order_by("id")
    ]


def _plan(claim):
    plan = _one(claim, "plan")
    return plan if plan is not None and plan.status == "ready" else None


def _ruling(claim):
    auth = _one(claim, "auth")
    return auth if auth is not None and auth.status == "ready" else None


def quoted_codes(claim) -> list:
    return list(dict.fromkeys(claim.lines.values_list("code", flat=True)))


def _benefits(plan, claim):
    """One plan row per quoted code, preferring the line's speciality."""
    if plan is None:
        return []
    wanted = {}
    for code, category in claim.lines.order_by("seq").values_list(
        "code", "category_code"
    ):
        wanted.setdefault(code, category or "")
    if not wanted:
        return []
    picked = {}
    for benefit in plan.benefits.filter(code__in=wanted).order_by("seq", "id"):
        have = picked.get(benefit.code)
        if have is None or (
            have.category_code != wanted[benefit.code]
            and benefit.category_code == wanted[benefit.code]
        ):
            picked[benefit.code] = benefit
    return sorted(picked.values(), key=lambda b: (b.seq or 0, b.id))


def procedure_types(claim) -> dict:
    out = {}
    for benefit in _benefits(_one(claim, "plan"), claim):
        conditions = benefit.conditions or {}
        if isinstance(conditions, dict):
            value = conditions.get("ProcedureType") or conditions.get("procedureType")
            if value:
                out[benefit.code] = _s(value).lower()
    return out


def lama_package(claim):
    plan = _one(claim, "plan")
    if plan is None:
        return None
    row = plan.benefits.filter(code="LM100").order_by("seq", "id").first()
    if row is None:
        return None
    return {
        "display": _s(row.display),
        "rate": float(row.rate or 0),
        "category_code": _s(row.category_code),
        "category_display": _s(row.category_display),
    }


def has_token(claim, stage) -> bool:
    from care.nhcx.services import biometric

    return biometric.current(claim, BIOMETRIC_STAGE[stage]) is not None


def biometric_headers(claim, stage) -> dict:
    from care.nhcx.services import biometric

    try:
        return biometric.headers_for(claim, BIOMETRIC_STAGE[stage])
    except Exception:
        return {}


def required_form_urls(claim, stage) -> list:
    """The D12 rule: urls (in order) a leg must carry; [] unless the plan is ready."""
    plan = _plan(claim)
    if plan is None:
        return []
    urls = []
    ruling = _ruling(claim)
    if ruling is not None:
        urls += [
            _s(r.form_url)
            for r in ruling.requirements.filter(
                kind="form", at_preauth=(stage == "preauth")
            ).order_by("seq", "id")
            if _s(r.form_url)
        ]
    for benefit in _benefits(plan, claim):
        for info in benefit.supporting_info or []:
            if isinstance(info, dict) and _s(info.get("form")):
                urls.append(_s(info["form"]))
    for doc in plan.policy_documents or []:
        if isinstance(doc, dict) and _s(doc.get("form")):
            urls.append(_s(doc["form"]))
    return list(dict.fromkeys(urls))


def _is_consent(form, stage) -> bool:
    spec_id = CONSENT_FORMS[stage]["id"]
    return _s(form.form_id) == spec_id or _s(form.url).rstrip("/").endswith(spec_id)


def _verified(claim, stage) -> bool:
    """A biometric payer holding a live user token takes no consent form (D12)."""
    return payers.adapter_for_claim(claim).biometric_required and has_token(
        claim, stage
    )


def _consent_form(claim, stage, plan):
    if not payers.adapter_for_claim(claim).biometric_required:
        return None
    if has_token(claim, stage):
        return None
    spec = CONSENT_FORMS[stage]
    for form in plan.forms.all():
        if _is_consent(form, stage):
            return FormInput(
                url=form.url,
                title=_s(form.title),
                kind=_s(form.kind) or "questionnaire",
                items=list(form.items or []),
            )
    return FormInput(
        url=CONSENT_URL.format(id=spec["id"]),
        title=spec["title"],
        kind="questionnaire",
        items=list(spec["items"]),
    )


def form_inputs(claim, stage) -> list:
    """FormInput per required form of the leg (D12 rule)."""
    plan = _plan(claim)
    if plan is None:
        return []
    by_url = {f.url: f for f in plan.forms.all()}
    verified = _verified(claim, stage)
    forms = []
    for url in required_form_urls(claim, stage):
        row = by_url.get(url)
        if row is None or (verified and _is_consent(row, stage)):
            continue
        forms.append(
            FormInput(
                url=row.url,
                title=_s(row.title),
                kind=_s(row.kind) or "questionnaire",
                items=list(row.items or []),
            )
        )
    consent = _consent_form(claim, stage, plan)
    if consent is not None and consent.url not in {f.url for f in forms}:
        forms.append(consent)
    return forms


def answers(claim, stage, forms) -> list:
    """D17 answers of the forms; a file question's answer becomes its document."""
    types = {}
    for form in forms:
        for item in form.items or []:
            types[(form.url, _s(item.get("linkId")))] = _s(item.get("type")).lower()
    rows = ClaimFormAnswer.objects.filter(
        claim=claim, form_url__in=[f.url for f in forms]
    )
    out = []
    for row in rows.order_by("id"):
        value = row.answer
        if types.get((row.form_url, row.link_id)) == "attachment":
            doc = _answer_document(claim, value)
            if doc is None:
                continue
            value = document_input(doc)
        out.append(
            FormAnswer(
                form_url=row.form_url,
                link_id=row.link_id,
                answer=value,
                stage=row.stage or stage,
            )
        )
    return out


def _answer_document(claim, value):
    """A file answer names its document by id, or by external id as the screens do."""
    value = _s(value)
    if value.isdigit():
        return ClaimDocument.objects.filter(claim=claim, id=int(value)).first()
    try:
        ref = uuid.UUID(value)
    except ValueError:
        return None
    return ClaimDocument.objects.filter(claim=claim, external_id=ref).first()


def required_forms(claim, stage) -> list:
    """A17 hook shape: [{url, title, questions}]."""
    return [
        {"url": f.url, "title": f.title, "questions": f.items}
        for f in form_inputs(claim, stage)
    ]


def required_documents(claim, stage) -> list:
    """A17 hook: [{code, display, category, package_code, attached_document_id}]."""
    attached = {}
    for doc in ClaimDocument.objects.filter(claim=claim, stage=stage).order_by("id"):
        if doc.code:
            attached[doc.code] = doc.external_id
    out = []
    ruling = _ruling(claim)
    if ruling is not None:
        for r in ruling.requirements.filter(
            kind="document", at_preauth=(stage == "preauth")
        ).order_by("seq", "id"):
            out.append(
                {
                    "code": _s(r.code),
                    "display": _s(r.display),
                    "category": "",
                    "package_code": _s(r.for_code),
                    "attached_document_id": attached.get(_s(r.code)),
                }
            )
        return [_stringify(d) for d in out]
    plan = _one(claim, "plan")
    if stage != "preauth":
        return []
    seen = set()
    for benefit in _benefits(plan, claim):
        for info in benefit.supporting_info or []:
            if not isinstance(info, dict):
                continue
            code = _s(info.get("code"))
            if not code or code.upper() == "STG" or _s(info.get("form")):
                continue
            if (code, benefit.code) in seen:
                continue
            seen.add((code, benefit.code))
            out.append(
                {
                    "code": code,
                    "display": _s(info.get("display")),
                    "category": _s(info.get("category")),
                    "package_code": benefit.code,
                    "attached_document_id": attached.get(code),
                }
            )
    return [_stringify(d) for d in out]


def _stringify(row):
    if row.get("attached_document_id") is not None:
        row["attached_document_id"] = str(row["attached_document_id"])
    return row


def discharge_summary(claim):
    """The claim-stage document the ruling or plan names a discharge summary, else HDS."""
    codes = []
    ruling = _ruling(claim)
    if ruling is not None:
        codes += [
            _s(r.code)
            for r in ruling.requirements.filter(kind="document")
            if "discharge summary" in _s(r.display).lower() and _s(r.code)
        ]
    for benefit in _benefits(_one(claim, "plan"), claim):
        for info in benefit.supporting_info or []:
            if (
                isinstance(info, dict)
                and "discharge summary" in _s(info.get("display")).lower()
                and _s(info.get("code"))
            ):
                codes.append(_s(info["code"]))
    docs = ClaimDocument.objects.filter(claim=claim, stage="claim").order_by("-id")
    for code in dict.fromkeys(codes):
        doc = docs.filter(code=code).first()
        if doc is not None:
            return document_input(doc)
    doc = docs.filter(code__iexact="HDS").first()
    return document_input(doc) if doc is not None else None
