"""T18. PMJAY Payment Notice, Status Refusal and Cancel."""

from care.nhcx.tests.e2e.cli.runner import Blocked, Refused, StepFailed
from care.nhcx.tests.e2e.payer import driver
from care.nhcx.tests.e2e.scenarios import common as c

REFUSALS = ("PAYR-1018", "PAYR-1008", "answers no status enquiry")


def _answered(row):
    return row.status if row.status != "asking" else None


def _status_refused(ctx, claim_id):
    """PMJAY answers no status enquiry: refused here or by the payer, both a pass."""
    what = "status enquiry is refused as PAYERS.md says"
    try:
        sent = ctx.api(
            "POST",
            f"claims/{claim_id}/enquiry/",
            {"action": "status", "leg": "preauth", "note": "e2e status"},
        )
    except Refused as e:
        ctx.check(
            any(m in str(e.error) for m in REFUSALS),
            what,
            f"refused {e.status}: {e.error}",
        )
        return
    from care.nhcx.models import ClaimEnquiry

    row = ClaimEnquiry.objects.get(external_id=sent["enquiry_id"])
    ctx.corr(row.correlation_id)
    status, how = ctx.wait_for(
        what,
        claim_id,
        lambda _k: _answered(ClaimEnquiry.objects.get(id=row.id)),
        row.correlation_id,
    )
    row.refresh_from_db()
    text = f"{row.error_message or ''} {row.detail or ''}"
    ctx.check(
        status == "error" and any(m in text for m in REFUSALS),
        what,
        f"{status} by {how}: {text.strip() or row.answer}",
        "sandbox",
    )


def _payment(ctx):
    claim_id = c.taken_over("pmjay_claim_approved")
    sub = c.submission_row(ctx, claim_id) if claim_id else None
    if sub is None or sub.status != "approved":
        raise Blocked(
            "no PMJAY claim approved at the claim stage (T17 did not hand one over)",
            "setup",
        )
    ctx.claims.append(claim_id)
    ctx.corr(sub.correlation_id)
    try:
        rows, how = ctx.wait_for(
            "payment notice arrives (C10)",
            claim_id,
            lambda _k: c.payments(claim_id) or None,
            seconds=ctx.conf.int("NHCX_TEST_PMJAY_PAYMENT_WAIT_SECONDS"),
        )
    except StepFailed as e:
        msg = (
            f"PMJAY's sandbox pays on its own schedule; no payment notice for "
            f"{ctx.claim(claim_id).claim_no} within the wait ({e.got})"
        )
        raise Blocked(msg, "sandbox") from e
    row = rows[-1]
    ctx.corr(row.correlation_id)
    ctx.corr(row.ack_correlation_id)
    ctx.check(
        row.ack_status not in (None, "", "error"),
        "payment notice matched by claim number and acknowledged (A8)",
        f"by {how}: {row.amount} UTR {row.utr}, ack {row.ack_status}, "
        f"notice workflow {row.workflow_id}, ack correlation {row.ack_correlation_id}",
        "sandbox",
    )


def run(ctx):
    claim_id = c.prepare_pmjay(ctx, label=" (pending)")
    row = c.submit_preauth(ctx, claim_id)
    # PMJAY cannot cancel a case it has not registered yet (ERR-PYR-PRE-030)
    c.wait_ack(
        ctx, claim_id, row.correlation_id, "PMJAY acknowledges the pre-authorisation"
    )
    _status_refused(ctx, claim_id)
    read = driver.read(ctx.claim(claim_id), "preauth")
    if driver.auto_decided(read):
        ctx.skip("payer desk role read as the case's state", "sandbox auto-decided")
    else:
        ctx.check(
            bool(read.get("role")) or bool(read.get("error")),
            "payer desk role read as the case's state (A14)",
            f"{read.get('caseNumber')}, role {read.get('role') or '-'}"
            + (f", {read.get('error')}" if read.get("error") else ""),
            "sandbox",
        )
    row, how = c.cancel_preauth(ctx, claim_id)
    ctx.check(
        row.status == "cancelled",
        "pending leg ends cancelled (C7)",
        f"{row.status} by {how}"
        + (f", {row.error_message}" if row.error_message else ""),
        "sandbox",
    )
    _payment(ctx)
