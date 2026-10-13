"""A17: everything the claim's tabs show, as one JSON document.

Public:
- ``claim_state(claim) -> dict`` runs the A10 to A13 polls (services.polling),
  works the stage out again and answers the A17 shape.
- ``row(obj, columns=None) -> dict``: a stored row with every column, ``id`` as
  the row's external_id, foreign keys as ``<name>_id`` external ids.
- ``admissions(claim) -> [dict]``: current inpatient stays matched on ABHA.
"""

import datetime
import uuid
from decimal import Decimal

from django.db import models
from django.db.models import F

from care.nhcx.services import hooks, polling, stage
from care.nhcx.services.common import adapter

SKIP_FIELDS = {"id", "external_id", "history", "meta", "deleted", "data"}
LINE_KIND_ORDER = ("Procedure", "Implant", "Stratification")
BENEFIT_COLUMNS = (
    "kind",
    "code",
    "display",
    "category_code",
    "category_display",
    "rate",
)
DOCUMENT_COLUMNS = (
    "code",
    "label",
    "filename",
    "content_type",
    "size",
    "stage",
)
IPD_CLASSES = ("imp", "emer", "obsenc")
FINISHED = ("completed", "discharged", "cancelled", "entered_in_error", "discontinued")


def _value(v):
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, datetime.datetime | datetime.date):
        return v.isoformat()
    if isinstance(v, uuid.UUID):
        return str(v)
    if isinstance(v, bytes | memoryview):
        return None
    return v


def row(obj, columns=None) -> dict | None:
    if obj is None:
        return None
    out = {"id": str(obj.external_id)}
    for field in obj._meta.concrete_fields:  # noqa: SLF001
        if field.name in SKIP_FIELDS or isinstance(field, models.BinaryField):
            continue
        if columns is not None and field.name not in columns:
            continue
        if field.is_relation:
            if field.name in ("created_by", "updated_by"):
                continue
            target = getattr(obj, field.name, None)
            ext = getattr(target, "external_id", None) if target is not None else None
            value = str(ext) if ext is not None else None
            # D column name (what the screens read), plus the older *_id alias.
            out[field.name] = value
            out[f"{field.name}_id"] = value
            continue
        out[field.name] = _value(getattr(obj, field.attname))
    if "created_date" in out:
        out["created_at"] = out["created_date"]
    return out


def _one(claim, name):
    try:
        return getattr(claim, name)
    except Exception:
        return None


def _member(m) -> dict:
    out = row(m)
    user = m.practitioner
    out["practitioner_name"] = (
        user.get_full_name() or user.username if user is not None else None
    )
    return out


def _items(value) -> list:
    return value if isinstance(value, list) else []


def admissions(claim) -> list:
    from care.emr.models import Encounter
    from care.nhcx.models.abha import abha_digits, find_patients_by_abha

    if not abha_digits(claim.abha_number):
        return []
    rows = (
        Encounter.objects.filter(
            patient__in=find_patients_by_abha(claim.abha_number),
            encounter_class__in=IPD_CLASSES,
        )
        .exclude(status__in=FINISHED)
        .select_related("patient", "facility")
        .order_by(F("period__start").desc(nulls_last=True), "-id")
    )
    return [
        {
            "id": str(e.external_id),
            "patient_id": str(e.patient.external_id),
            "patient_name": e.patient.name,
            "facility_id": str(e.facility.external_id),
            "kind": "IPD",
            "status": e.status,
            "encounter_class": e.encounter_class,
            "period_start": (e.period or {}).get("start"),
            "period_end": (e.period or {}).get("end"),
        }
        for e in rows
    ]


def _lines(claim) -> list:
    order = {k: i for i, k in enumerate(LINE_KIND_ORDER)}
    lines = sorted(
        claim.lines.all(), key=lambda r: (order.get(r.kind, 9), r.kind, r.seq, r.id)
    )
    return [row(r) for r in lines]


def _ruling(claim):
    auth = _one(claim, "auth")
    if auth is None:
        return None
    out = row(auth)
    out["items"] = [row(i) for i in auth.items.order_by("seq", "id")]
    out["requirements"] = [row(r) for r in auth.requirements.order_by("seq", "id")]
    return out


def _query(q) -> dict:
    out = row(q)
    out["questions"] = _items(q.questions)
    return out


def _hook_rows(value) -> list:
    out = []
    for v in value or []:
        out.append(row(v) if isinstance(v, models.Model) else v)
    return out


def claim_state(claim) -> dict:
    poll_notes = polling.poll_all(claim)
    stage.recompute(claim)
    claim.refresh_from_db()

    plan = _one(claim, "plan")
    preauth = _one(claim, "preauth")
    submission = _one(claim, "submission")
    ad = adapter(claim)
    required_forms = {
        s: _hook_rows(hooks.call("required_forms", claim, s))
        for s in ("preauth", "claim")
    }
    return {
        "claim": row(claim),
        "plan": row(plan),
        "benefits": [
            row(b, BENEFIT_COLUMNS) for b in plan.benefits.order_by("seq", "id")
        ]
        if plan is not None
        else [],
        "admissions": admissions(claim),
        "lines": _lines(claim),
        "ruling": _ruling(claim),
        "required_documents": {
            s: _hook_rows(hooks.call("required_documents", claim, s))
            for s in ("preauth", "claim")
        },
        "forms": required_forms,
        "required_forms": required_forms,
        "diagnoses": [row(d) for d in claim.diagnoses.order_by("seq", "id")],
        "care_team": [_member(m) for m in claim.care_team.order_by("seq", "id")],
        "documents": [row(d, DOCUMENT_COLUMNS) for d in claim.documents.order_by("id")],
        "form_answers": [
            {
                "form_url": a.form_url,
                "link_id": a.link_id,
                "answer": a.answer,
                "stage": a.stage,
            }
            for a in claim.form_answers.order_by("id")
        ],
        "stage": claim.stage,
        "sub_stage": claim.sub_stage,
        "preauth": row(preauth),
        "preauth_items": _items(preauth.items_json) if preauth else [],
        "next_send": {
            s: hooks.call("next_send", claim, s) for s in ("preauth", "claim")
        },
        "adapter": getattr(ad, "key", "generic"),
        "desk": getattr(ad, "desk", None) or None,
        "predeterminations": [row(p) for p in claim.predeterminations.order_by("-id")],
        "enhancement_lines": _hook_rows(hooks.call("enhancement_lines", claim)),
        "queries": [_query(q) for q in claim.queries.order_by("-id")],
        "submission": row(submission),
        "submission_items": _items(submission.items_json) if submission else [],
        "payments": [row(p) for p in claim.payments.order_by("-id")],
        "paid_total": float(round(stage.paid_total(claim), 2)),
        "enquiries": [row(e) for e in claim.enquiries.order_by("-id")],
        "poll_notes": poll_notes,
    }
