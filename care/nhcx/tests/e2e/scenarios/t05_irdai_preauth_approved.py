"""T5. IRDAI Pre-authorisation Approved."""

from care.nhcx.tests.e2e.scenarios import common as c


def run(ctx):
    claim_id = c.prepare_irdai(ctx)
    row = c.submit_preauth(ctx, claim_id)
    record = c.decide(ctx, claim_id, "preauth", "approve", "e2e approval")
    row, how = c.wait_preauth(ctx, claim_id, row.correlation_id)
    ctx.check(
        row.status == "approved" and row.approved_amount is not None,
        "provider receives the approval",
        f"{row.status} by {how}, approved {row.approved_amount} of "
        f"{row.requested_amount}",
        "sandbox",
    )
    claim = ctx.claim(claim_id)
    ctx.check(
        claim.adjudications.filter(cycle_id=record.get("cycle_id")).exists(),
        "decision recorded against the claim",
        f"cycle {record.get('cycle_id')}, {claim.adjudications.count()} adjudications",
    )
