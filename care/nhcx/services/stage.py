"""D9 stage and sub_stage, recomputed after every write (D9 description).

Public:
- ``recompute(claim, *, save=True) -> (stage, sub_stage)``
- ``paid_total(claim) -> Decimal``: the amount paid so far (A17P PAID_TOTAL).
"""

from decimal import ROUND_HALF_UP, Decimal

from care.nhcx.models import ClaimStage

SUBMITTING_SUB_STAGE = {
    "preauth": "requested",
    "enhancement": "requested",
    "claim": "requested",
    "preauth_resubmit": "resubmitted",
    "claim_resubmit": "resubmitted",
    "preauth_query_response": "answered",
    "enhancement_resubmit": "answered",
    "claim_query_response": "answered",
}
QUERYABLE = {"requested", "answered", "resubmitted"}
ENHANCEMENT_KINDS = {"enhancement", "enhancement_resubmit"}


def _one(claim, name):
    try:
        return getattr(claim, name)
    except Exception:
        return None


def paid_total(claim) -> Decimal:
    """Sum of the last amount per UTR of paid or cleared notices."""
    latest: dict = {}
    for p in claim.payments.order_by("id"):
        status = (p.payment_status or "").strip().lower()
        if status not in {"paid", "cleared"}:
            continue
        utr = (p.utr or "").strip()
        if not utr and "initiat" in (p.disposition or "").lower():
            continue
        latest[utr or f"#{p.id}"] = p.amount or Decimal(0)
    total = sum(latest.values(), Decimal(0))
    return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _leg_sub_stage(claim, leg, leg_stage: str) -> str:
    status = leg.status
    if status == "submitting":
        sub = SUBMITTING_SUB_STAGE.get(leg.submission_kind or "", "requested")
    elif status == "error":
        sub = "refused"
    else:
        sub = status
    if sub in QUERYABLE:
        open_query = claim.queries.filter(
            kind="query", status__in=["open", "error"], stage=leg_stage
        ).exists()
        if open_query:
            sub = "queried"
    return sub


def compute(claim) -> tuple[str, str]:
    if claim.payments.exists():
        return ClaimStage.payment, ("paid" if paid_total(claim) > 0 else "noticed")
    submission = _one(claim, "submission")
    if submission is not None and submission.status != "draft":
        return ClaimStage.claim, _leg_sub_stage(claim, submission, "claim")
    preauth = _one(claim, "preauth")
    if preauth is not None:
        stage = (
            ClaimStage.enhancement
            if preauth.submission_kind in ENHANCEMENT_KINDS
            else ClaimStage.preauth
        )
        return stage, _leg_sub_stage(claim, preauth, "preauth")
    if claim.preauth_saved_at:
        return ClaimStage.preauth, "draft"
    status = claim.status or "draft"
    return ClaimStage.eligibility, ("draft" if status == "error" else status)


def recompute(claim, *, save: bool = True) -> tuple[str, str]:
    stage, sub_stage = compute(claim)
    stage, sub_stage = str(stage), str(sub_stage)
    if (claim.stage, claim.sub_stage) != (stage, sub_stage):
        claim.stage, claim.sub_stage = stage, sub_stage
        if save and claim.pk:
            type(claim).objects.filter(pk=claim.pk).update(
                stage=stage, sub_stage=sub_stage
            )
    return stage, sub_stage
