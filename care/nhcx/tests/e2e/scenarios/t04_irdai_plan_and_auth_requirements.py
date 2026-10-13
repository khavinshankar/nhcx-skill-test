"""T4. IRDAI Insurance Plan and Authorisation Requirements."""

from care.nhcx.tests.e2e.scenarios import common as c


def run(ctx):
    claim_id, _policy = c.open_claim(ctx, "irdai")
    c.eligibility(ctx, claim_id, "validation")
    plan = c.wait_plan(ctx, claim_id)
    ctx.check(
        bool(plan.policy_code or plan.plan_identifier),
        "plan names the policy",
        f"policy {plan.policy_code}, plan {plan.plan_identifier} {plan.plan_title}",
    )
    code = c.first_package(ctx, claim_id)
    c.add_line(ctx, claim_id, code)
    c.rule(ctx, claim_id)
    state = ctx.state(claim_id)
    ruling = state.get("ruling") or {}
    ctx.check(
        bool(ruling.get("items")) or bool(ruling.get("requirements")),
        "ruling is held against the lines",
        f"{len(ruling.get('items') or [])} items, "
        f"{len(ruling.get('requirements') or [])} requirements, "
        f"next send {state.get('next_send', {}).get('preauth')}",
    )
