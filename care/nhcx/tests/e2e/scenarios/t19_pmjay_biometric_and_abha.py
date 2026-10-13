"""T19. PMJAY Beneficiary Verification and ABHA (biometric hosts stood in, T19S)."""

from django.test import override_settings

from care.nhcx.tests.e2e.abdm_fake import AbdmFake
from care.nhcx.tests.e2e.scenarios import common as c

CONSENT = "100024"
ABHA_HEADER = "x-hcx-ben-abha-id"
NOT_STOOD_IN = (
    "not automated: the ABHA service stand-in (A19 M1 enrolment and its sealing key) "
    "is not part of this runner"
)


# 14-digit ABHA number written 91-1234-5678-9012.
ABHA_HYPHENS = 3


def _out(corr):
    from care.nhcx.gateway import get_gateway

    ledger = get_gateway().ledger
    rows = [
        r
        for r in ledger.list_summaries(correlation_id=str(corr), limit=50)
        if r.get("direction") == "out"
    ]
    if not rows:
        return {}, {}
    got = ledger.fhir(sorted(rows, key=lambda r: r["id"])[0]["id"]) or {}
    return got.get("jwe_headers") or {}, got.get("fhir") or {}


def _consent_in(bundle) -> bool:
    for entry in (bundle or {}).get("entry") or []:
        res = entry.get("resource") or {}
        if res.get("resourceType") == "QuestionnaireResponse" and CONSENT in str(
            res.get("questionnaire") or ""
        ):
            return True
    return False


def _bio(ctx, claim_id, action, body):
    got = ctx.send(
        f"biometric {action} (A18)",
        "POST",
        f"claims/{claim_id}/biometric/{action}/",
        body,
    )
    return got.get("attempt") or {}


def run(ctx):
    """The stand-in tokens are dropped afterwards: a live one would make the other
    PMJAY tests leave out the Authentication Consent the sandbox then asks for
    (PAYR-1256), since the sandbox never issued them."""
    from django.utils import timezone

    started = timezone.now()
    try:
        _run(ctx)
    finally:
        _drop_stand_in_tokens(ctx, started)


def _drop_stand_in_tokens(ctx, since):
    from care.nhcx.models import BiometricAuth, Claim

    patients = Claim.objects.filter(external_id__in=ctx.claims).values_list(
        "patient_id", flat=True
    )
    gone, _ = BiometricAuth.objects.filter(
        patient_id__in=list(patients), created_date__gte=since
    ).delete()
    ctx.step("stand-in biometric tokens dropped", f"{gone} rows")


def _run(ctx):
    from care.nhcx.services import biometric

    ctx.skip("ABHA verify and registration from the ABHA profile (A19)", NOT_STOOD_IN)
    header = biometric.token_header().lower()
    claim_id = c.prepare_pmjay(ctx, fill=False)
    claim = ctx.claim(claim_id)
    first = claim.correlation_id
    heads, bundle = _out(first)
    ctx.check(
        bool(heads) and header not in {k.lower() for k in heads},
        "validation check before any authentication carries no user token",
        f"headers {sorted(heads)}; consent form in bundle: {_consent_in(bundle)}",
    )
    with (
        AbdmFake() as fake,
        override_settings(
            NHCX_BIOMETRIC_BASE_URL=fake.base, NHCX_FACEAUTH_BASE_URL=fake.base
        ),
    ):
        attempt = _bio(
            ctx, claim_id, "init", {"method": "FINGERPRINT", "stage": "Preauth"}
        )
        init = next((x for x in fake.calls if x["path"] == "/auth/init"), {})
        h, b = init.get("headers") or {}, init.get("body") or {}
        ctx.check(
            h.get("authorization", "").startswith("Bearer ")
            and h.get("process") == "Preauth"
            and h.get("payerid") == claim.payer_id
            and (b.get("loginId") or "").count("-") == ABHA_HYPHENS,
            "init goes to the biometric host with Authorization, process, payerid and a hyphenated ABHA",
            f"process {h.get('process')}, payerid {h.get('payerid')}, loginId {b.get('loginId')}, "
            f"bearer_auth {'bearer_auth' in h}",
        )
        attempt = _bio(
            ctx,
            claim_id,
            "verify",
            {
                "attempt_id": attempt["id"],
                "pid": '<PidData><Resp errCode="0"/></PidData>',
            },
        )
        ctx.check(
            attempt.get("status") == "verified" and attempt.get("token_valid"),
            "verify holds a live token",
            f"{attempt.get('status')}, token live {attempt.get('token_valid')}, ABHA {attempt.get('abha_number')}",
        )
        issued = fake.issued[-1]
        c.eligibility(ctx, claim_id, "validation")
        heads, _bundle = _out(ctx.claim(claim_id).correlation_id)
        low = {k.lower(): v for k, v in heads.items()}
        ctx.check(
            low.get(header) == issued and bool(low.get(ABHA_HEADER)),
            "second validation check carries the user token and the beneficiary's ABHA",
            f"{header} {'stand-in token' if low.get(header) == issued else low.get(header)}, "
            f"{ABHA_HEADER} {low.get(ABHA_HEADER)}",
        )
        c.fill_draft(ctx, claim_id)
        row = c.submit_preauth(ctx, claim_id)
        heads, _bundle = _out(row.correlation_id)
        low = {k.lower(): v for k, v in heads.items()}
        ctx.check(
            low.get(header) == issued and not _consent_in(row.request_json),
            "pre-authorisation carries the token and no Authentication Consent",
            f"token {'stand-in' if low.get(header) == issued else low.get(header)}, "
            f"{ABHA_HEADER} {low.get(ABHA_HEADER)}, consent form {_consent_in(row.request_json)}",
        )
        attempt = _bio(ctx, claim_id, "refresh", {"attempt_id": attempt["id"]})
        ctx.check(
            fake.issued[-1] != issued and attempt.get("token_valid"),
            "refresh replaces the token",
            f"{len(fake.issued)} tokens issued, live {attempt.get('token_valid')}",
        )
        listing = ctx.api("GET", f"claims/{claim_id}/biometric/")
        ctx.check(
            bool(listing.get("preauth")) and not listing.get("discharge"),
            "listing names the current Preauth attempt and none for Discharge",
            f"{len(listing.get('attempts') or [])} attempts, stage {listing.get('stage')}",
        )
    ctx.skip(
        "predetermination with the refreshed token, discharge face verify and claim",
        "not automated: the face verify needs the ABHA service's sealing key (A19 stand-in)",
    )
    c.free_beneficiary(ctx, "pmjay")
