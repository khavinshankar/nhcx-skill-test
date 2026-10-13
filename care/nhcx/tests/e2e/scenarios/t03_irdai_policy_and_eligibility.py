"""T3. IRDAI Policy Search and Eligibility."""

from care.nhcx.tests.e2e.scenarios import common as c


def run(ctx):
    claim_id, policy = c.open_claim(ctx, "irdai")
    claim = ctx.claim(claim_id)
    ctx.check(
        claim.payer_id == c.payer_code(ctx, "irdai")
        and claim.processing_id == (policy.get("processing_id") or claim.payer_id),
        "claim is addressed to the processing id",
        f"payer {claim.payer_id}, processing {claim.processing_id}, "
        f"policy {claim.policy_code}",
    )
    discovery = c.eligibility(ctx, claim_id, "discovery")
    validation = c.eligibility(ctx, claim_id, "validation")
    ctx.check(
        discovery.correlation_id != validation.correlation_id,
        "each check travels on its own correlation id",
        f"{discovery.correlation_id} / {validation.correlation_id}",
    )
    rows = c.search(ctx, c.UNKNOWN_MEMBER, what="unknown member id")
    ctx.check(
        rows == [],
        "unknown member id finds no policy",
        f"{len(rows)} policies (registry NHCX-1016 read as none)",
    )
