"""T8. IRDAI Enhancement."""

from care.nhcx.tests.e2e.scenarios import common as c


def run(ctx):
    claim_id = c.approved_preauth(ctx)
    first = c.preauth_row(ctx, claim_id)
    original = first.approved_amount
    extra = c.packages(ctx, claim_id, 3)[1:]
    c.add_line(ctx, claim_id, extra[0])
    one = c.submit_preauth(ctx, claim_id, what="provider sends the enhancement")
    ctx.check(
        one.submission_kind == "enhancement"
        and one.correlation_id != first.correlation_id,
        "enhancement goes out under its workflow on a new correlation id",
        f"{one.submission_kind}, workflow {one.workflow_id}, #{one.enhancement_no}",
    )
    c.decide(ctx, claim_id, "preauth", "approve", "e2e enhancement approved")
    row, how = c.wait_preauth(ctx, claim_id, one.correlation_id)
    raised = row.approved_amount
    ctx.check(
        row.status in {"approved", "partial"} and raised and raised > original,
        "approved enhancement raises the approved total",
        f"{row.status} by {how}: {original} -> {raised}",
        "sandbox",
    )
    c.add_line(ctx, claim_id, extra[1])
    two = c.submit_preauth(ctx, claim_id, what="provider sends a second enhancement")
    c.decide(ctx, claim_id, "preauth", "reject", "e2e: enhancement not justified")
    row, how = c.wait_preauth(ctx, claim_id, two.correlation_id)
    ctx.check(
        row.approved_amount == raised,
        "rejected enhancement leaves the total unchanged",
        f"{row.status} by {how}: total {row.approved_amount} (was {raised}), "
        f"{row.adjudication or row.disposition}",
        "sandbox",
    )
