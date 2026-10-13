"""T11. IRDAI Payment Notice and Acknowledgement."""

import time

from care.nhcx.tests.e2e.scenarios import common as c

INSTALMENTS = 2


def run(ctx):
    claim_id = c.taken_over("irdai_claim_approved")
    if (
        claim_id
        and c.submission_row(ctx, claim_id).status == "approved"
        and not c.payments(claim_id)
    ):
        ctx.claims.append(claim_id)
        ctx.step(
            "claim approved at the claim stage",
            f"from T10: {ctx.claim(claim_id).claim_no}",
        )
    else:
        claim_id = c.approved_preauth(ctx)
        c.discharge(ctx, claim_id)
        row = c.submit_claim(ctx, claim_id)
        c.decide(ctx, claim_id, "claim", "approve", "e2e claim approved")
        row = c.wait_claim(ctx, claim_id, row.correlation_id)
        ctx.check(
            row.status == "approved",
            "claim approved at the claim stage",
            row.status,
            "sandbox",
        )
    approved = c.submission_row(ctx, claim_id).approved_amount
    first = (approved * 6 / 10).quantize(approved)
    stamp = int(time.time())
    one = c.pay(ctx, claim_id, float(first), f"E2EUTR{stamp}A")
    c.hand_over("irdai_claim_part_paid", claim_id)
    two = c.pay(ctx, claim_id, float(approved - first), f"E2EUTR{stamp}B")
    rows = c.payments(claim_id)
    total = sum((r.amount or 0) for r in rows)
    ctx.check(
        len(rows) == INSTALMENTS
        and one.id != two.id
        and {r.utr for r in rows} == {one.utr, two.utr},
        "second instalment recorded beside the first",
        f"{len(rows)} payments, UTRs {[r.utr for r in rows]}, total {total} of {approved}",
    )
    state = ctx.state(claim_id)
    ctx.step(
        "claim shows paid once the instalments cover the approval",
        f"status {state.get('claim', {}).get('status')}, payments {len(state.get('payments') or [])}",
    )
