"""T6. IRDAI Pre-authorisation Rejected and Sent Again."""

from care.nhcx.services import adjudicator as adj
from care.nhcx.tests.e2e.scenarios import common as c

REMARK = "e2e: treatment not covered under the policy"


def run(ctx):
    claim_id = c.prepare_irdai(ctx)
    first = c.submit_preauth(ctx, claim_id)
    claim = ctx.claim(claim_id)
    calls = claim.adjudications.count()
    record = c.decide_refused(ctx, claim_id, "preauth", "reject", "")
    ctx.check(
        adj.IRDAI_REMARKS in (record.get("error") or "")
        and claim.adjudications.count() == calls,
        "reject without a remark is refused before any call",
        record.get("error"),
    )
    c.decide(ctx, claim_id, "preauth", "reject", REMARK)
    row, how = c.wait_preauth(ctx, claim_id, first.correlation_id)
    ctx.check(
        row.status == "rejected",
        "first leg ends rejected (not queried)",
        f"{row.status} by {how}: {row.adjudication or row.disposition}",
        "sandbox",
    )
    second = c.submit_preauth(ctx, claim_id, what="provider sends it again")
    ctx.check(
        second.correlation_id != first.correlation_id,
        "second send travels on a new correlation id",
        f"{first.correlation_id} -> {second.correlation_id}",
    )
    c.decide(ctx, claim_id, "preauth", "approve", "e2e approval")
    row, how = c.wait_preauth(ctx, claim_id, second.correlation_id)
    history = c.preauth_history(row)
    ctx.check(
        row.status == "approved",
        "second send ends approved",
        f"{row.status} by {how}, approved {row.approved_amount}; history {history}",
        "sandbox",
    )
