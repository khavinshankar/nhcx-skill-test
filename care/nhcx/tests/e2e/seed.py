"""The PMJAY package master seed (T13): written through C4's own code path."""

from __future__ import annotations

import json
from pathlib import Path

from care.nhcx.tests.e2e import config as cfg

SEED_SOURCE = "test seed"


def load(conf=None) -> dict:
    conf = conf or cfg.load()
    path = Path(conf.get("NHCX_TEST_PMJAY_PLAN_SEED"))
    if not path.is_absolute():
        path = cfg.CARE_ROOT / path
    return json.loads(path.read_text())


def _identifier(plan) -> str:
    rows = plan.get("identifier") or []
    return next((r.get("value") for r in rows if r.get("type") != "NH"), "") or ""


def parsed(seed: dict) -> dict:
    """The seed in the shape ``care.nhcx.fhir.read.plan.read`` gives C4."""
    plan = seed.get("plan") or {}
    benefits = []
    for p in seed.get("packages") or []:
        speciality = p.get("speciality") or {}
        info = [
            {
                "category": d.get("category"),
                "category_display": "",
                "code": d.get("code"),
                "display": d.get("name"),
                "form": None,
            }
            for d in p.get("documents") or []
        ]
        info += [
            {
                "category": r.get("category"),
                "category_display": "",
                "code": r.get("code"),
                "display": r.get("display"),
                "form": None,
            }
            for r in p.get("requirements") or []
        ]
        benefits.append(
            {
                "category_code": speciality.get("code"),
                "category_display": speciality.get("display"),
                "code": p.get("code"),
                "display": p.get("name"),
                "kind": "Procedure",
                "rate": p.get("rate"),
                "currency": p.get("currency") or "INR",
                "cost_type": "Procedure",
                "requirement": None,
                "conditions": p.get("conditions") or {},
                "extras": [],
                "supporting_info": info,
            }
        )
    forms = [
        {
            "url": q.get("url"),
            "form_id": (q.get("url") or "").rstrip("/").rsplit("/", 1)[-1],
            "title": q.get("title"),
            "kind": "questionnaire",
            "items": [
                {
                    "linkId": i.get("linkId"),
                    "type": i.get("type"),
                    "text": i.get("text"),
                    "required": bool(i.get("required")),
                    "depth": 0,
                    "options": i.get("options") or [],
                    "initial": None,
                }
                for i in q.get("items") or []
            ],
        }
        for q in seed.get("questionnaires") or []
    ]
    return {
        "plan": {
            "plan_identifier": _identifier(plan),
            "plan_title": plan.get("name"),
            "plan_type": (plan.get("plan_type") or {}).get("display"),
            "sum_insured": None,
            "policy_documents": [],
        },
        "benefits": benefits,
        "forms": forms,
    }


def is_seeded(row) -> bool:
    body = row.response_json if row is not None else None
    return isinstance(body, dict) and body.get("source") == SEED_SOURCE


def apply(claim, conf=None) -> tuple[bool, str]:
    """Seeds the claim's plan unless a real plan is already ready."""
    from care.nhcx.callbacks.plan import apply_plan
    from care.nhcx.models import ClaimPlan

    seed = load(conf)
    row = ClaimPlan.objects.filter(claim=claim).order_by("-id").first()
    if row is not None and row.status == "ready" and not is_seeded(row):
        return False, "the payer's own plan is ready; the seed is not written"
    if row is None:
        row = ClaimPlan.objects.create(
            claim=claim, status="fetching", policy_code=claim.policy_code
        )
    apply_plan(row, parsed(seed), {"source": SEED_SOURCE, "seed": seed})
    row.refresh_from_db()
    return (
        True,
        f"{row.status}, {row.benefits.count()} packages, {row.forms.count()} forms",
    )


def remove(claims) -> int:
    from care.nhcx.models import ClaimPlan

    gone = 0
    for row in ClaimPlan.objects.filter(claim__in=claims):
        if is_seeded(row):
            row.delete()
            gone += 1
    return gone
