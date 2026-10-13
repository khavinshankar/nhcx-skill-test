"""T17. PMJAY Claim Through the Role Walk."""

from care.nhcx.tests.e2e.cli.runner import Blocked, Refused
from care.nhcx.tests.e2e.scenarios import common as c


def _approved(ctx, label):
    claim_id = c.prepare_pmjay(ctx, label=label)
    row, how, _record = c.pmjay_preauth(ctx, claim_id)
    ctx.check(
        row.status == "approved",
        f"pre-authorisation approved{label}",
        f"{row.status} by {how}, {row.approved_amount}"
        + (f", {row.error_message}" if row.error_message else ""),
        "sandbox",
    )
    return claim_id


def _send(ctx, claim_id):
    c.discharge(ctx, claim_id)
    docs = c.attach_required(ctx, claim_id, "claim")
    forms = c.answer_forms(ctx, claim_id, "claim")
    ctx.step(
        "claim forms and documents ready",
        f"documents {docs or '-'}, forms {forms or '-'}",
    )
    row = c.submit_claim(ctx, claim_id)
    ctx.check(
        row.submission_kind == "claim" and bool(row.preauth_ref),
        "claim goes out referring to its pre-authorisation",
        f"workflow {row.workflow_id}, preauth {row.preauth_ref}, {row.correlation_id}",
    )
    c.wait_ack(ctx, claim_id, row.correlation_id, "PMJAY acknowledges the claim")
    return row


def _no_resubmit(ctx, claim_id):
    try:
        ctx.api("POST", f"claims/{claim_id}/claim/submit/", {})
    except Refused as e:
        ctx.step(
            "provider never offers a claim resubmission to PMJAY",
            f"refused {e.status}: {e.error}",
        )
        return
    ctx.fail(
        "provider never offers a claim resubmission to PMJAY", "a resubmission went out"
    )


def run(ctx):
    first = _approved(ctx, " (approve)")
    row = _send(ctx, first)
    record = c.decide(ctx, first, "claim", "approve", "e2e claim approval")
    row = c.wait_claim(ctx, first, row.correlation_id)
    ctx.check(
        row.status == "approved",
        "first claim ends approved with PMJAY's amount",
        f"{row.status}, approved {row.approved_amount} of {row.requested_amount}"
        + (f", {row.error_message}" if row.error_message else ""),
        "sandbox",
    )
    c.hand_over("pmjay_claim_approved", first)
    _no_resubmit(ctx, first)

    second = _approved(ctx, " (query)")
    row = _send(ctx, second)
    record = c.decide(
        ctx, second, "claim", "query", "e2e: attach the discharge summary"
    )
    if record.get("skipped"):
        row = c.wait_claim(ctx, second, row.correlation_id)
        msg = (
            f"the PMJAY sandbox decided the claim by itself ({row.status}); a desk query "
            "cannot be raised on an auto-decided package"
        )
        raise Blocked(msg, "sandbox")
    row = c.wait_claim(ctx, second, row.correlation_id)
    ctx.check(row.status == "queried", "second claim is queried", row.status, "sandbox")
    answer = c.submit_claim(
        ctx,
        second,
        what="provider answers the query by sending the claim again",
        body={"reply": "e2e: discharge summary attached"},
    )
    ctx.check(
        answer.submission_kind == "claim_query_response",
        "the answer goes out under PMJAY's claim query-response workflow",
        f"{answer.submission_kind}, workflow {answer.workflow_id}",
    )
    c.decide(ctx, second, "claim", "approve", "e2e claim approval after query")
    row = c.wait_claim(ctx, second, answer.correlation_id)
    ctx.check(
        row.status == "approved", "second claim ends approved", row.status, "sandbox"
    )
