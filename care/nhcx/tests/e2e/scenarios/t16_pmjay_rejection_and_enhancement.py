"""T16. PMJAY Rejection and Enhancement (the rejection needs NHCX_TEST_PMJAY_MANUAL_PACKAGE)."""

from care.nhcx.tests.e2e.cli.runner import Refused
from care.nhcx.tests.e2e.scenarios import common as c

# The first cycle and the enhancement together.
BOTH_CYCLES = 3000


def _reject(ctx):
    package = ctx.conf.get("NHCX_TEST_PMJAY_MANUAL_PACKAGE")
    if not package:
        ctx.skip(
            "payer rejects the first pre-authorisation",
            "blocked (sandbox): SB043F is auto-approved before a desk can reject it; "
            "NHCX_TEST_PMJAY_MANUAL_PACKAGE is not set",
        )
        return
    claim_id = c.prepare_pmjay(ctx, code=package, label=" (reject)")
    row = c.submit_preauth(ctx, claim_id)
    c.wait_ack(
        ctx, claim_id, row.correlation_id, "PMJAY acknowledges the pre-authorisation"
    )
    c.decide(ctx, claim_id, "preauth", "reject", "e2e: not covered")
    row, how = c.wait_preauth(ctx, claim_id, row.correlation_id)
    ctx.check(
        row.status == "rejected",
        "first leg rejected with PMJAY's reason",
        f"{row.status} by {how}: {row.disposition or row.error_message}",
        "sandbox",
    )


def run(ctx):
    _reject(ctx)
    claim_id = c.prepare_pmjay(ctx, code=c.PMJAY_CYCLIC, label=" (enhancement)")
    row, how, _record = c.pmjay_preauth(ctx, claim_id)
    ctx.check(
        row.status in {"approved", "partial"},
        "MG072C x1 approved",
        f"{row.status} by {how}, {row.approved_amount}"
        + (f", {row.error_message}" if row.error_message else ""),
        "sandbox",
    )
    first = row.correlation_id
    try:
        ctx.api(
            "POST",
            f"claims/{claim_id}/lines/",
            {"kind": "Procedure", "code": c.PMJAY_CYCLIC, "quantity": 1},
        )
    except Refused as e:
        ctx.fail(
            "provider adds a second MG072C cycle for the enhancement",
            f"refused {e.status}: {e.error} The claim keeps one line per code (D16 "
            "ux_claim_line) and an enhancement sends only new codes, while PMJAY takes a "
            "further cycle only as a new item sequence (PAYR-1274 when the quantity of the "
            "sent item is raised instead, ledger 7USL00DM)",
            "ours",
        )
    sent = c.submit_preauth(ctx, claim_id, what="provider sends the enhancement")
    ctx.check(
        sent.submission_kind == "enhancement" and sent.correlation_id != first,
        "enhancement goes out on a new correlation id",
        f"{sent.submission_kind}, workflow {sent.workflow_id}, {sent.correlation_id}",
    )
    c.wait_ack(ctx, claim_id, sent.correlation_id, "PMJAY acknowledges the enhancement")
    c.decide(ctx, claim_id, "preauth", "approve", "e2e enhancement approval")
    row, how = c.wait_preauth(ctx, claim_id, sent.correlation_id)
    ctx.check(
        row.status in {"approved", "partial"}
        and float(row.approved_amount or 0) >= BOTH_CYCLES,
        "approved total covers both cycles",
        f"{row.status} by {how}, approved {row.approved_amount}",
        "sandbox",
    )
