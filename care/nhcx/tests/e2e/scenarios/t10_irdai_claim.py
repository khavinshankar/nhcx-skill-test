"""T10. IRDAI Claim Approved, Part-approved and Rejected."""

from decimal import Decimal

from care.nhcx.tests.e2e.payer import driver
from care.nhcx.tests.e2e.scenarios import common as c

LINES = 2


def _send(ctx, claim_id):
    c.discharge(ctx, claim_id)
    row = c.submit_claim(ctx, claim_id)
    ctx.check(
        row.submission_kind == "claim" and bool(row.preauth_ref),
        "claim goes out under the claim workflow, referring to its pre-auth",
        f"workflow {row.workflow_id}, preauth {row.preauth_ref}, {row.correlation_id}",
    )
    return row


def run(ctx):
    full = c.approved_preauth(ctx, label=" (approve)")
    row = _send(ctx, full)
    c.decide(ctx, full, "claim", "approve", "e2e claim approved")
    row = c.wait_claim(ctx, full, row.correlation_id)
    ctx.check(
        row.status == "approved" and row.approved_amount == row.requested_amount,
        "first claim approved for the claimed amount",
        f"{row.status}: {row.approved_amount} of {row.requested_amount}",
        "sandbox",
    )
    c.hand_over("irdai_claim_approved", full)

    part = c.approved_preauth(ctx, label=" (part)", lines=2)
    row = _send(ctx, part)
    case = driver.irdai_case(ctx.claim(part), "claim")
    lines = driver._line_items(case)  # noqa: SLF001
    ctx.check(
        len(lines) >= LINES,
        "payer desk lists both claim lines",
        f"{len(lines)} lines on {case.get('id')}",
        "sandbox",
    )
    first_amt = Decimal(str(lines[0].get("claimed_amount")))
    second_amt = Decimal(str(lines[1].get("claimed_amount")))
    allowed = (second_amt / 2).quantize(Decimal(1))
    decided = driver.irdai_lines(
        ctx.claim(part),
        "claim",
        [("approved", float(first_amt)), ("partially_approved", float(allowed))],
    )
    ctx.decisions.append({"stage": "claim", "decision": "lines", **decided})
    ctx.check(
        all(d["error"] is None for d in decided["lines"]),
        "payer decides the lines",
        "; ".join(
            f"{d['code']} {d['decision']} {d['amount']} (HTTP {d['status']})"
            for d in decided["lines"]
        ),
        "sandbox",
    )
    c.decide(ctx, part, "claim", "approve", "e2e claim part-approved")
    row = c.wait_claim(ctx, part, row.correlation_id)
    expect = first_amt + allowed
    ctx.check(
        row.status in {"approved", "partial"} and row.approved_amount == expect,
        "second claim approved at the sum of the allowed lines",
        f"{row.status}: {row.approved_amount} (expected {expect}) of {row.requested_amount}; "
        f"items {c.item_view(row)}",
        "sandbox",
    )
    c.hand_over("irdai_claim_partial", part)

    rejected = c.approved_preauth(ctx, label=" (reject)")
    row = _send(ctx, rejected)
    c.decide(ctx, rejected, "claim", "reject", "e2e: bills do not match the approval")
    row = c.wait_claim(ctx, rejected, row.correlation_id)
    ctx.check(
        row.status == "rejected",
        "third claim rejected with its reason (outcome complete is not approval)",
        f"{row.status}, outcome {row.outcome}: {row.adjudication or row.disposition}",
        "sandbox",
    )
    c.hand_over("irdai_claim_rejected", rejected)
