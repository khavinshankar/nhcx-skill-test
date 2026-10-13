"""T13. PMJAY Eligibility, Package Master and Ruling."""

from care.nhcx.tests.e2e.scenarios import common as c


def run(ctx):
    c.free_beneficiary(ctx, "pmjay")
    claim_id, policy = c.open_claim(ctx, "pmjay")
    claim = ctx.claim(claim_id)
    ctx.check(
        bool(policy.get("abha_number")) and bool(claim.member_id),
        "search returns the PMJAY policy with the ABHA number",
        f"policy {policy.get('policy_code')}, member {claim.member_id}, "
        f"ABHA {'returned' if policy.get('abha_number') else 'missing'}",
        "sandbox",
    )
    ctx.check(
        claim.processing_id == (policy.get("processing_id") or claim.payer_id),
        "claim is addressed to the processing id",
        f"payer {claim.payer_id}, processing {claim.processing_id}",
    )
    c.eligibility(ctx, claim_id, "discovery")
    c.eligibility(ctx, claim_id, "validation")
    c.admit(ctx, claim_id)
    c.plan_once(ctx, claim_id)
    plan = c.seed_plan(ctx, claim_id)
    codes = sorted(plan.benefits.values_list("code", flat=True))
    forms = list(plan.forms.values_list("kind", flat=True))
    ctx.check(
        codes == sorted([c.PMJAY_PACKAGE, c.PMJAY_CYCLIC]),
        "package master reads ready with the two seeded packages",
        f"{plan.status}, packages {codes}, {len(forms)} forms {sorted(set(forms))}",
        "setup",
    )
    line = c.add_line(ctx, claim_id, c.PMJAY_PACKAGE)
    ctx.check(
        bool(line.get("amount")),
        "SB043F priced from the package master",
        f"{line.get('display')}, {line.get('amount')}",
    )
    auth = c.rule(ctx, claim_id)
    pre = list(auth.requirements.filter(at_preauth=True).values_list("kind", "code"))
    ctx.check(
        bool(pre),
        "ruling lists what the package needs at pre-authorisation",
        ", ".join(f"{k}:{code}" for k, code in pre[:10]),
        "sandbox",
    )
