"""T14. PMJAY Pre-authorisation Through the Payer Service."""

from care.nhcx.tests.e2e.scenarios import common as c


def run(ctx):
    claim_id = c.prepare_pmjay(ctx)
    row, how, record = c.pmjay_preauth(ctx, claim_id)
    ctx.check(
        row.status == "approved",
        "PMJAY's decision arrives (C5)",
        f"{row.status} by {how}, approved {row.approved_amount} of {row.requested_amount}"
        + (f", {row.error_message}" if row.error_message else ""),
        "sandbox",
    )
    if record.get("cycle_id"):
        claim = ctx.claim(claim_id)
        ctx.check(
            claim.adjudications.filter(cycle_id=record["cycle_id"]).exists(),
            "cycle trail recorded against the claim",
            f"cycle {record['cycle_id']}, stopped {record.get('stopped')}",
        )
    c.hand_over("pmjay_preauth_approved", claim_id)
