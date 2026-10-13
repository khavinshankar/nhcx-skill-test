"""T7. IRDAI Query Answered."""

from care.nhcx.tests.e2e.scenarios import common as c

QUESTION = "e2e: please send the latest chest X-ray report"


def run(ctx):
    claim_id = c.prepare_irdai(ctx)
    sent = c.submit_preauth(ctx, claim_id)
    after = c.last_query_id(claim_id)
    c.decide(ctx, claim_id, "preauth", "query", QUESTION)
    query = c.wait_query(ctx, claim_id, after)
    doc = c.upload(ctx, claim_id, code="RAD", stage="preauth", label="X-ray report")
    ctx.send(
        "provider answers the question (A7)",
        "POST",
        f"claims/{claim_id}/queries/{query.external_id}/reply/",
        {"text": "e2e: X-ray report attached", "document_ids": [str(doc.external_id)]},
    )
    query.refresh_from_db()
    ctx.corr(query.reply_correlation_id)
    ctx.check(
        query.status == "answered" and not query.error_message,
        "reply goes out on the question's thread",
        f"{query.status}, reply correlation {query.reply_correlation_id}, "
        f"documents {query.reply_documents}"
        + (f", {query.error_message}" if query.error_message else ""),
        "sandbox",
    )
    case = c.desk_case(ctx, claim_id, "preauth")
    ctx.step(
        "payer desk shows the reply against the case",
        f"{case.get('id')}: {c.desk_reply_view(case)}",
    )
    c.decide(ctx, claim_id, "preauth", "approve", "e2e approval after query")
    row, how = c.wait_preauth(
        ctx,
        claim_id,
        sent.correlation_id,
        settled={"approved", "partial", "rejected", "error"},
    )
    ctx.check(
        row.status == "approved",
        "leg is approved after the answer",
        f"{row.status} by {how}, approved {row.approved_amount}",
        "sandbox",
    )
