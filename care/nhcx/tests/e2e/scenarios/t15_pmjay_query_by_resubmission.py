"""T15. PMJAY Query Answered by Resubmission (needs NHCX_TEST_PMJAY_MANUAL_PACKAGE)."""

from care.nhcx.tests.e2e.cli.runner import Blocked
from care.nhcx.tests.e2e.scenarios import common as c


def run(ctx):
    package = ctx.conf.get("NHCX_TEST_PMJAY_MANUAL_PACKAGE")
    if not package:
        raise Blocked(
            "the PMJAY sandbox auto-approves SB043F before a desk can query it; "
            "set NHCX_TEST_PMJAY_MANUAL_PACKAGE to a seeded package it does not decide by itself",
            "sandbox",
        )
    claim_id = c.prepare_pmjay(ctx, code=package)
    row = c.submit_preauth(ctx, claim_id)
    c.wait_ack(
        ctx, claim_id, row.correlation_id, "PMJAY acknowledges the pre-authorisation"
    )
    c.decide(ctx, claim_id, "preauth", "query", "e2e: attach the latest reports")
    row, how = c.wait_preauth(ctx, claim_id, row.correlation_id)
    ctx.check(
        row.status == "queried", "leg is queried", f"{row.status} by {how}", "sandbox"
    )
    answer = c.submit_preauth(
        ctx,
        claim_id,
        what="provider answers by sending again",
        body={"reply": "e2e: latest reports attached"},
    )
    ctx.check(
        row.correlation_id in {answer.correlation_id, answer.thread_correlation_id},
        "answer travels on the leg's own correlation id",
        f"{answer.submission_kind}, workflow {answer.workflow_id}, {answer.correlation_id}",
    )
    c.decide(ctx, claim_id, "preauth", "approve", "e2e approval")
    row, how = c.wait_preauth(ctx, claim_id, answer.correlation_id)
    ctx.check(
        row.status == "approved",
        "leg ends approved",
        f"{row.status} by {how}",
        "sandbox",
    )
