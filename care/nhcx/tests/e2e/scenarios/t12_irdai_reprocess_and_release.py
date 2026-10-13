"""T12. IRDAI Reprocess and Balance Release."""

import time

from care.nhcx.tests.e2e.scenarios import common as c


def _rejected_claim(ctx):
    claim_id = c.taken_over("irdai_claim_rejected")
    if claim_id and c.submission_row(ctx, claim_id).status == "rejected":
        ctx.claims.append(claim_id)
        ctx.step(
            "claim rejected at the claim stage",
            f"from T10: {ctx.claim(claim_id).claim_no}",
        )
        return claim_id
    claim_id = c.approved_preauth(ctx, label=" (rejected)")
    c.discharge(ctx, claim_id)
    row = c.submit_claim(ctx, claim_id)
    c.decide(ctx, claim_id, "claim", "reject", "e2e: bills do not match")
    row = c.wait_claim(ctx, claim_id, row.correlation_id)
    ctx.check(
        row.status == "rejected",
        "claim rejected at the claim stage",
        row.status,
        "sandbox",
    )
    return claim_id


def _part_paid_claim(ctx):
    claim_id = c.taken_over("irdai_claim_part_paid")
    # T11 pays the balance too; a claim with a second instalment has no balance left.
    if claim_id and len(c.payments(claim_id)) == 1:
        ctx.claims.append(claim_id)
        ctx.step(
            "claim paid (or approved) in part",
            f"from T10/T11: {ctx.claim(claim_id).claim_no}, {len(c.payments(claim_id))} payments",
        )
        return claim_id
    claim_id = c.approved_preauth(ctx, label=" (part paid)")
    c.discharge(ctx, claim_id)
    row = c.submit_claim(ctx, claim_id)
    c.decide(ctx, claim_id, "claim", "approve", "e2e")
    row = c.wait_claim(ctx, claim_id, row.correlation_id)
    c.pay(ctx, claim_id, float(row.approved_amount / 2), f"E2EUTR{int(time.time())}P")
    return claim_id


def run(ctx):
    rejected = _rejected_claim(ctx)
    sent = c.submission_row(ctx, rejected)
    asked = c.enquire(
        ctx,
        rejected,
        {
            "action": "reprocess",
            "leg": "claim",
            "reason_code": "claimrejected",
            "reason": "claimrejected",
            "note": "e2e: corrected bills attached",
        },
        what="reprocess on the rejected claim",
    )
    c.wait_enquiry(ctx, rejected, asked, what="payer acknowledges the reprocess (C8)")
    c.decide(ctx, rejected, "claim", "approve", "e2e approved on reprocess")

    def ready(_k):
        row = c.submission_row(ctx, rejected)
        return row.status if row.status in {"approved", "partial"} else None

    status, how = ctx.wait_for(
        "claim approved again (C6)", rejected, ready, sent.correlation_id
    )
    row = c.submission_row(ctx, rejected)
    earlier = c.thread_verdicts(sent.correlation_id)
    ctx.check(
        status == "approved" and any(v == "rejected" for _i, v in earlier),
        "claim approved again, rejection kept in its history",
        f"{status} by {how}, {row.approved_amount}; claim thread {earlier}",
        "sandbox",
    )

    part = _part_paid_claim(ctx)
    decided = c.submission_row(ctx, part).approved_amount or 0
    paid = sum((p.amount or 0) for p in c.payments(part))
    balance = max(float(decided) - float(paid), 1.0)
    asked = c.enquire(
        ctx,
        part,
        {
            "action": "release",
            "leg": "claim",
            "reason_code": "partialpayment",
            "reason": "partialpayment",
            "note": "e2e: balance pending",
            "amount": f"{balance:.2f}",
        },
        what="balance release on the partly paid claim",
    )
    c.wait_enquiry(ctx, part, asked, what="payer acknowledges the release (C8)")
