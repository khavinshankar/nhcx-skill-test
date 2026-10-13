"""C4 package master reply: replaces D10 to D12."""

import logging

from django.db import transaction
from django.utils import timezone

from care.nhcx.callbacks import dispatch
from care.nhcx.fhir.read import plan as read_plan
from care.nhcx.models import ClaimPlan, ClaimPlanBenefit, ClaimPlanForm

logger = logging.getLogger(__name__)

PLAN_COLUMNS = (
    "plan_identifier",
    "plan_title",
    "plan_type",
    "sum_insured",
    "policy_documents",
)


def _columns(model) -> set:
    names = {f.name for f in model._meta.concrete_fields}  # noqa: SLF001
    return names - {"id", "plan", "seq"}


def _corr(envelope, delivery) -> str:
    corr = (delivery or {}).get("correlation_id")
    if not corr:
        h = envelope.get("jwe_headers") if isinstance(envelope, dict) else None
        corr = h.get("x-hcx-correlation_id") if isinstance(h, dict) else ""
    return str(corr or "")


def apply_plan(row, parsed: dict, body) -> None:
    plan = parsed.get("plan") or {}
    benefits = parsed.get("benefits") or []
    forms = parsed.get("forms") or []
    benefit_cols, form_cols = _columns(ClaimPlanBenefit), _columns(ClaimPlanForm)
    with transaction.atomic():
        for column in PLAN_COLUMNS:
            setattr(row, column, plan.get(column))
        row.status = "ready" if benefits else "empty"
        row.fetched_at = timezone.now()
        row.error_message = plan.get("message") if not benefits else None
        row.response_json = body
        row.save()
        row.benefits.all().delete()
        row.forms.all().delete()
        ClaimPlanBenefit.objects.bulk_create(
            [
                ClaimPlanBenefit(
                    plan=row,
                    **{k: v for k, v in b.items() if k in benefit_cols},
                    seq=n,
                )
                for n, b in enumerate(benefits, start=1)
            ]
        )
        seen = set()
        rows = []
        for f in forms:
            if not f.get("url") or f["url"] in seen:
                continue
            seen.add(f["url"])
            rows.append(
                ClaimPlanForm(
                    plan=row, **{k: v for k, v in f.items() if k in form_cols}
                )
            )
        ClaimPlanForm.objects.bulk_create(rows)


def handle(envelope, delivery=None):
    corr = _corr(envelope, delivery)
    row = (
        ClaimPlan.objects.filter(correlation_id=corr).order_by("-id").first()
        if corr
        else None
    )
    if row is None:
        return dispatch.result(dispatch.UNMATCHED)
    if row.status != "fetching" and not dispatch.failed_send(row):
        return dispatch.result(dispatch.IGNORED, "the plan request has moved on")
    body = dispatch.payload(envelope)
    if dispatch.is_protocol_response(body):
        row.status = "error"
        row.error_message = dispatch.rejection(body)
        row.save(update_fields=["status", "error_message", "modified_date"])
        return dispatch.result(dispatch.SETTLED, row.error_message)
    dispatch.revive(row, "fetching")
    parsed = read_plan.read(body)
    apply_plan(row, parsed, body)
    return dispatch.result(dispatch.SETTLED, row.status)
