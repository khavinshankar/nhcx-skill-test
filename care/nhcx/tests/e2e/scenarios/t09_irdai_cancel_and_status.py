"""T9. IRDAI Status Enquiry and Cancel."""

from care.nhcx.tests.e2e.scenarios import common as c


def run(ctx):
    first = c.prepare_irdai(ctx, label=" (first)")
    sent = c.submit_preauth(ctx, first)
    second = c.prepare_irdai(ctx, label=" (second)")
    c.submit_preauth(ctx, second)

    before = c.preauth_row(ctx, first).status
    asked = c.enquire(
        ctx,
        first,
        {"action": "status", "leg": "preauth", "note": "e2e status"},
        what="status enquiry on the first claim",
    )
    asked = c.wait_enquiry(ctx, first, asked, what="payer answers the status (C8)")
    after = c.preauth_row(ctx, first).status
    ctx.check(
        after == before,
        "status answer leaves the leg's status alone",
        f"{before} -> {after}; answer {asked.answer}",
    )

    row, how = c.cancel_preauth(ctx, second)
    ctx.check(
        row.status == "cancelled",
        "second leg ends cancelled",
        f"{row.status} by {how}",
        "sandbox",
    )

    c.decide(ctx, first, "preauth", "approve", "e2e approval")
    row, how = c.wait_preauth(ctx, first, sent.correlation_id)
    ctx.check(
        row.status == "approved",
        "first leg approved",
        f"{row.status} by {how}",
        "sandbox",
    )
    row, how = c.cancel_preauth(ctx, first, note="e2e cancel after approval")
    if row.status == "approved":
        ctx.step(
            "payer refuses the cancel of a decided case",
            f"back to {row.status} by {how}: {row.error_message or row.disposition}",
        )
    elif row.status == "cancelled":
        ctx.skip(
            "payer refuses the cancel of a decided case",
            f"the sandbox payer accepted the cancel ({how}); recorded, not a pass",
        )
    else:
        ctx.fail(
            "payer answers the cancel of a decided case",
            f"{row.status} by {how} (expected approved or cancelled)",
        )
