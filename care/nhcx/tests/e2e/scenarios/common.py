"""What every scenario shares: open a claim, check it, plan it, quote, send."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from care.nhcx.tests.e2e.cli.runner import Blocked, Refused

PDF = (
    b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]>>endobj\n"
    b"trailer<</Root 1 0 R>>\n%%EOF\n"
)
DIAGNOSIS = ("S68.4", "Traumatic amputation of hand at wrist level")
SETTLED_PREAUTH = {"approved", "partial", "queried", "rejected", "cancelled", "error"}
SETTLED_CLAIM = {"approved", "partial", "queried", "rejected", "error"}
OPEN_PREAUTH = {"submitting", "approved", "partial", "queried"}
UNKNOWN_MEMBER = "E2E-NOBODY-0000"
NO_COVER = "not enough cover left"


@dataclass
class Scenario:
    id: str
    payer: str
    title: str
    run: object = None
    gui: bool = True
    notes: str = ""
    extra: dict = field(default_factory=dict)


def payer_code(ctx, payer):
    return ctx.conf.get(f"NHCX_TEST_{payer.upper()}_PAYER")


def member_id(ctx, payer):
    value = ctx.conf.get(f"NHCX_TEST_{payer.upper()}_MEMBER_ID")
    if not value:
        msg = f"NHCX_TEST_{payer.upper()}_MEMBER_ID is not set; ask the integrator"
        raise Blocked(msg, "setup")
    return value


def search(ctx, member, *, what="policy search finds the member"):
    try:
        body = ctx.api(
            "POST",
            "policy-search/",
            {"identifiertype": "MemberId", "identifiervalue": member},
        )
    except Refused as e:
        ctx.fail(what, f"refused {e.status}: {e.error}", "sandbox")
    return body.get("policies") or []


def patient_for(ctx, policy):
    from care.nhcx.models.abha import find_patients_by_abha

    abha = policy.get("abha_number") or ""
    return find_patients_by_abha(abha).order_by("id").first() if abha else None


def open_claim(ctx, payer, *, label="") -> tuple[str, dict]:
    """Searches the member, picks the payer's policy and opens a claim on it."""
    member = member_id(ctx, payer)
    code = payer_code(ctx, payer)
    rows = search(ctx, member)
    wanted = ctx.conf.get(f"NHCX_TEST_{payer.upper()}_POLICY") or ""
    policy = next(
        (
            r
            for r in rows
            if r.get("payer_id") == code
            and (not wanted or wanted in {r.get("policy_code"), r.get("product_id")})
        ),
        None,
    )
    ctx.check(
        policy is not None,
        f"policy search finds {payer.upper()} member{label}",
        f"{len(rows)} policies, payers {sorted({r.get('payer_id') for r in rows})}",
        "sandbox",
    )
    patient = patient_for(ctx, policy)
    body = {
        "policy": policy,
        "identifiertype": "MemberId",
        "identifiervalue": member,
    }
    if patient is not None:
        body["patient"] = str(patient.external_id)
    opened = ctx.send("provider opens the claim", "POST", "claims/", body)
    claim_id = opened["claim_id"]
    ctx.claims.append(claim_id)
    c = ctx.claim(claim_id)
    ctx.step(
        f"claim opened{label}",
        f"{c.claim_no}, payer {c.payer_id}, processing {c.processing_id or '-'}",
    )
    return claim_id, policy


def eligibility(ctx, claim_id, purpose, *, expect="eligible"):
    before = ctx.claim(claim_id).correlation_id
    ctx.send(
        f"provider sends the {purpose} check",
        "POST",
        f"claims/{claim_id}/eligibility/",
        {"purpose": purpose},
    )
    c = ctx.claim(claim_id)
    corr = c.correlation_id
    ctx.corr(corr)
    ctx.check(
        bool(corr) and corr != before and c.status != "error",
        f"{purpose} check goes out",
        f"{c.status}, correlation {corr}"
        + (f", {c.error_message}" if c.error_message else ""),
        "sandbox",
    )
    (status, how) = ctx.wait_for(
        f"payer answers the {purpose} check",
        claim_id,
        lambda k: k.status if k.status != "checking" else None,
        corr,
    )
    c = ctx.claim(claim_id)
    ctx.check(
        status == expect and c.correlation_id == corr,
        f"payer answers the {purpose} check",
        f"{status} by {how}, inforce {c.inforce}, period {c.plan_period_start}"
        f"..{c.plan_period_end}, allowed {c.allowed_amount}"
        + (f", {c.error_message}" if c.error_message else ""),
        "sandbox",
    )
    return c


def _patient_with_claim_abha(ctx, c):
    """The test patient under the ABHA the payer answered with (D9: it replaces the
    registry's). The PMJAY sandbox answers eligibility with another ABHA than the
    registry's search, so the test patient is moved to it, recorded as a sandbox step."""
    from care.nhcx.models.abha import abha_digits, find_patients_by_abha, set_abha

    found = find_patients_by_abha(c.abha_number).order_by("id").first()
    if found is not None or c.patient is None or not abha_digits(c.abha_number):
        return found or c.patient
    set_abha(c.patient, number=c.abha_number)
    ctx.step(
        "test patient takes the payer's ABHA",
        f"payer's Patient carries {c.abha_number}, not the registry's (sandbox)",
    )
    return c.patient


def admit(ctx, claim_id):
    from care.emr.models import Encounter

    c = ctx.claim(claim_id)
    if c.encounter_id:
        return
    patient = _patient_with_claim_abha(ctx, c)
    enc = (
        Encounter.objects.filter(
            patient=patient, facility=ctx.facility, status="in_progress"
        )
        .order_by("-id")
        .first()
    )
    if enc is None:
        raise Blocked("the test beneficiary has no open admission; run setup", "setup")
    ctx.send(
        "provider links the admission",
        "POST",
        f"claims/{claim_id}/admission/",
        {"encounter": str(enc.external_id)},
    )


def request_plan(ctx, claim_id):
    ctx.send("provider requests the plan", "POST", f"claims/{claim_id}/plan/", {})
    row = ctx.claim(claim_id).plan
    ctx.corr(row.correlation_id)
    ctx.check(
        row.status != "error",
        "plan request goes out",
        f"{row.status}, correlation {row.correlation_id}"
        + (f", {row.error_message}" if row.error_message else ""),
        "sandbox",
    )
    return row


def wait_plan(ctx, claim_id):
    row = request_plan(ctx, claim_id)
    corr = row.correlation_id
    status, how = ctx.wait_for(
        "payer sends the plan",
        claim_id,
        lambda k: k.plan.status if k.plan.status != "fetching" else None,
        corr,
        seconds=ctx.conf.int("NHCX_TEST_PLAN_WAIT_SECONDS"),
    )
    row = ctx.claim(claim_id).plan
    codes = list(row.benefits.order_by("seq").values_list("code", "rate")[:5])
    ctx.check(
        status == "ready" and bool(codes),
        "payer sends the plan",
        f"{status} by {how}, {row.plan_title or row.plan_identifier}, "
        f"{row.benefits.count()} packages e.g. {codes[:3]}"
        + (f", {row.error_message}" if row.error_message else ""),
        "sandbox",
    )
    return row


def add_line(ctx, claim_id, code, quantity=1):
    body = ctx.send(
        f"provider quotes {code} x{quantity}",
        "POST",
        f"claims/{claim_id}/lines/",
        {"kind": "Procedure", "code": code, "quantity": quantity},
    )
    line = (body or {}).get("line") or {}
    ctx.step(
        f"provider quotes {code} x{quantity}",
        f"{line.get('display') or code}, {line.get('amount')}",
    )
    return line


def first_package(ctx, claim_id):
    row = ctx.claim(claim_id).plan
    b = row.benefits.exclude(rate__isnull=True).order_by("seq").first()
    return b.code if b else None


def rule(ctx, claim_id):
    c = ctx.claim(claim_id)
    elig_corr = c.correlation_id
    ctx.send(
        "provider asks for the auth requirements",
        "POST",
        f"claims/{claim_id}/auth-requirements/",
        {},
    )
    auth = ctx.claim(claim_id).auth
    ctx.corr(auth.correlation_id)
    ctx.check(
        auth.status != "error",
        "auth-requirements check goes out",
        f"{auth.status}, correlation {auth.correlation_id}"
        + (f", {auth.error_message}" if getattr(auth, "error_message", None) else ""),
        "sandbox",
    )
    status, how = ctx.wait_for(
        "payer rules on the auth requirements",
        claim_id,
        lambda k: k.auth.status if k.auth.status != "checking" else None,
        auth.correlation_id,
    )
    auth = ctx.claim(claim_id).auth
    reqs = list(auth.requirements.values_list("kind", "code", "at_preauth"))
    ctx.check(
        status == "ready" and auth.correlation_id != elig_corr,
        "payer rules on the auth requirements",
        f"{status} by {how} on {auth.correlation_id} (not {elig_corr}); "
        f"{len(reqs)} requirements: "
        + ", ".join(f"{k}:{code}" for k, code, _ in reqs[:8]),
        "sandbox",
    )
    return auth


def upload(ctx, claim_id, *, code="", stage="preauth", label="e2e document"):
    body = ctx.send(
        f"provider attaches {code or label}",
        "POST",
        f"claims/{claim_id}/documents/",
        {
            "file": SimpleUploadedFile(
                f"{code or 'doc'}.pdf", PDF, content_type="application/pdf"
            ),
            "code": code,
            "category": "DIA",
            "stage": stage,
            "label": label,
        },
        multipart=True,
    )
    from care.nhcx.models import ClaimDocument

    return ClaimDocument.objects.get(external_id=body["document_id"])


def _answer(ctx, claim_id, item, stage):
    kind = (item.get("type") or "").lower()
    if kind == "attachment":
        doc = upload(
            ctx, claim_id, code="ODN", stage=stage, label=item.get("text") or "form"
        )
        return str(doc.id)
    options = item.get("options") or []
    if options:
        first = options[0]
        return (
            first.get("display") or first.get("code")
            if isinstance(first, dict)
            else str(first)
        )
    if kind in {"datetime", "date"}:
        return timezone.now().date().isoformat()
    if kind in {"integer", "decimal"}:
        return "1"
    if kind == "boolean":
        return "true"
    return "e2e"


def answer_forms(ctx, claim_id, stage):
    st = ctx.state(claim_id)
    forms = (st.get("required_forms") or {}).get(stage) or []
    answers = []
    for form in forms:
        for item in form.get("questions") or []:
            if (
                not item.get("required")
                and (item.get("type") or "").lower() == "attachment"
            ):
                continue
            answers.append(
                {
                    "form_url": form["url"],
                    "link_id": item.get("linkId"),
                    "answer": _answer(ctx, claim_id, item, stage),
                    "stage": stage,
                }
            )
    if answers:
        ctx.send(
            f"provider answers the {stage} forms",
            "PUT",
            f"claims/{claim_id}/draft/",
            {"answers": answers, "stage": stage},
        )
    return [f.get("title") or f.get("url") for f in forms]


def attach_required(ctx, claim_id, stage):
    st = ctx.state(claim_id)
    docs = (st.get("required_documents") or {}).get(stage) or []
    for d in docs:
        if not d.get("attached_document_id"):
            upload(
                ctx, claim_id, code=d.get("code"), stage=stage, label=d.get("display")
            )
    return [d.get("code") for d in docs]


def fill_draft(ctx, claim_id):
    admit(ctx, claim_id)
    today = timezone.now().date()
    code, display = DIAGNOSIS
    if ctx.conf.get("NHCX_TEST_DIAGNOSIS"):
        code, _, display = ctx.conf.get("NHCX_TEST_DIAGNOSIS").partition(" ")
        display = display.strip() or code
    ctx.send(
        "provider saves the pre-authorisation draft",
        "PUT",
        f"claims/{claim_id}/draft/",
        {
            "admission_date": (today - timedelta(days=1)).isoformat(),
            "expected_discharge_date": (today + timedelta(days=3)).isoformat(),
            "diagnoses": [{"icd10_code": code, "icd10_display": display}],
            "care_team": [
                {"role": "treating", "practitioner": str(ctx.doctor.external_id)}
            ],
        },
    )
    docs = attach_required(ctx, claim_id, "preauth")
    forms = answer_forms(ctx, claim_id, "preauth")
    ctx.step(
        "pre-authorisation draft ready",
        f"diagnosis {code}, doctor {ctx.doctor.username}, "
        f"documents {docs or '-'}, forms {forms or '-'}",
    )


def preauth_row(ctx, claim_id):
    from care.nhcx.models import ClaimPreauth

    return ClaimPreauth.objects.filter(claim__external_id=claim_id).first()


def submit_preauth(
    ctx, claim_id, *, what="provider sends the pre-authorisation", body=None
):
    before = preauth_row(ctx, claim_id)
    before_corr = before.correlation_id if before else None
    ctx.send(what, "POST", f"claims/{claim_id}/preauth/submit/", body or {})
    row = preauth_row(ctx, claim_id)
    ctx.corr(row.correlation_id)
    ctx.check(
        row.status != "error"
        and row.correlation_id
        and row.correlation_id != before_corr,
        what,
        f"{row.submission_kind}, {row.status}, workflow {row.workflow_id}, "
        f"correlation {row.correlation_id}, amount {row.requested_amount}"
        + (f", {row.error_message}" if row.error_message else ""),
        "sandbox"
        if row.error_message and "PAYR" in (row.error_message or "")
        else "ours",
    )
    return row


def wait_preauth(
    ctx, claim_id, corr, *, what="provider receives the decision", settled=None
):
    settled = settled or SETTLED_PREAUTH

    def ready(k):
        row = preauth_row(ctx, claim_id)
        if row is None or row.correlation_id != corr:
            return None
        return row.status if row.status in settled else None

    _status, how = ctx.wait_for(what, claim_id, ready, corr)
    row = preauth_row(ctx, claim_id)
    return row, how


def decide(ctx, claim_id, stage, decision, remarks=""):
    from care.nhcx.tests.e2e.payer import driver

    record = driver.decide(ctx.claim(claim_id), stage, decision, remarks)
    ctx.decisions.append(record)
    read = record.get("read") or {}
    if record.get("skipped"):
        ctx.skip("payer desk reads the case", record["skipped"])
        ctx.skip(f"payer desk takes {decision}", record["skipped"])
        return record
    ctx.check(
        bool(read.get("role")),
        "payer desk reads the case",
        f"{read.get('caseNumber')}, {read.get('role')}, "
        f"{_case_view(read.get('response'))}"
        + (f", {read.get('error')}" if read.get("error") else ""),
        "sandbox",
    )
    steps = record.get("trail") or []
    # "no-role": the case left the last role after every action was taken.
    ok = record.get("stopped") in {"decided", "completed"} or (
        record.get("stopped") == "no-role"
        and bool(steps)
        and all(s.get("success") for s in steps)
    )
    trail = ", ".join(
        f"{s.get('action')} as {s.get('role')}"
        + ("" if s.get("success") else f" (refused: {s.get('error')})")
        for s in record.get("trail") or []
    )
    if not ok and NO_COVER in trail.lower():
        ctx.step(f"payer desk takes {decision}", f"blocked: {trail}", "blocked")
        msg = (
            f"payer desk refuses {decision}: the test member's cover is used up on the "
            f"sandbox ({trail}); free or reset the member's cover, or use another member"
        )
        raise Blocked(msg, "sandbox")
    ctx.check(
        ok,
        f"payer desk takes {decision}",
        f"{record.get('stopped')}, {trail or record.get('error')}, cycle {record.get('cycle_id')}",
        "sandbox",
    )
    return record


def _case_view(response):
    if not isinstance(response, dict):
        return str(response)[:80]
    keep = ("id", "stage", "adjudication", "status", "claimed_amount")
    return ", ".join(f"{k} {response[k]}" for k in keep if response.get(k) is not None)


def prepare_irdai(ctx, *, rule_it=True, label="", lines=1):
    """A claim with the IRDAI policy, eligible, plan lines and their ruling."""
    claim_id, _policy = open_claim(ctx, "irdai", label=label)
    eligibility(ctx, claim_id, "validation")
    admit(ctx, claim_id)
    wait_plan(ctx, claim_id)
    for code in packages(ctx, claim_id, lines):
        add_line(ctx, claim_id, code)
    if rule_it:
        rule(ctx, claim_id)
    fill_draft(ctx, claim_id)
    return claim_id


def approved_preauth(ctx, *, label="", lines=1):
    claim_id = prepare_irdai(ctx, label=label, lines=lines)
    row = submit_preauth(ctx, claim_id)
    decide(ctx, claim_id, "preauth", "approve", "e2e approval")
    row, how = wait_preauth(ctx, claim_id, row.correlation_id)
    ctx.check(
        row.status == "approved",
        "provider receives the approval",
        f"{row.status} by {how}, {row.approved_amount}",
        "sandbox",
    )
    return claim_id


def discharge(ctx, claim_id, stage="claim"):
    today = timezone.now().date().isoformat()
    ctx.send(
        "provider records the discharge",
        "POST",
        f"claims/{claim_id}/discharge/",
        {
            "discharge_mode": "normal",
            "discharge_stage": "After Surgery",
            "discharge_date": today,
            "surgery_date": today,
        },
    )


def submission_row(ctx, claim_id):
    from care.nhcx.models import ClaimSubmission

    return ClaimSubmission.objects.filter(claim__external_id=claim_id).first()


def submit_claim(ctx, claim_id, *, what="provider sends the claim", body=None):
    before = submission_row(ctx, claim_id)
    before_corr = before.correlation_id if before else None
    ctx.send(what, "POST", f"claims/{claim_id}/claim/submit/", body or {})
    row = submission_row(ctx, claim_id)
    ctx.corr(row.correlation_id)
    ctx.check(
        row.status != "error"
        and bool(row.correlation_id)
        and row.correlation_id != before_corr,
        what,
        f"{row.submission_kind}, {row.status}, workflow {row.workflow_id}, "
        f"correlation {row.correlation_id}, preauth {row.preauth_ref or '-'}, "
        f"amount {row.requested_amount}"
        + (f", {row.error_message}" if row.error_message else ""),
        "sandbox" if "PAYR" in (row.error_message or "") else "ours",
    )
    return row


def wait_claim(
    ctx, claim_id, corr, *, what="provider receives the claim decision", settled=None
):
    settled = settled or SETTLED_CLAIM

    def ready(k):
        row = submission_row(ctx, claim_id)
        if row is None or row.correlation_id != corr:
            return None
        return row.status if row.status in settled else None

    ctx.wait_for(what, claim_id, ready, corr)
    return submission_row(ctx, claim_id)


# ---- more than one package, handing claims between tests ----


def packages(ctx, claim_id, n=2):
    row = ctx.claim(claim_id).plan
    codes = list(
        row.benefits.exclude(rate__isnull=True)
        .order_by("seq")
        .values_list("code", flat=True)
    )
    if len(codes) < n:
        msg = f"the plan lists {len(codes)} priced packages; {n} needed"
        raise Blocked(msg)
    return codes[:n]


def _handoff_path():
    from care.nhcx.tests.e2e import config as cfg

    return cfg.ARTIFACTS / "handoff.json"


def hand_over(key, claim_id):
    """Keeps a claim for a later test in the same run (T10 -> T11 -> T12)."""
    import json

    path = _handoff_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.loads(path.read_text()) if path.exists() else {}
    data[key] = claim_id
    path.write_text(json.dumps(data, indent=2))


def taken_over(key):
    import json

    path = _handoff_path()
    data = json.loads(path.read_text()) if path.exists() else {}
    return data.get(key)


# ---- queries, enquiries, cancels, payments ----


def wait_query(ctx, claim_id, after_id=0, *, what="question arrives (C9)"):
    from care.nhcx.models import ClaimQuery

    def ready(k):
        return ClaimQuery.objects.filter(claim=k, id__gt=after_id).order_by("id").last()

    row, how = ctx.wait_for(what, claim_id, ready)
    ctx.corr(row.correlation_id)
    ctx.check(
        bool(row.remarks or row.questions),
        what,
        f"{row.kind} by {how}, {row.status}, stage {row.stage}, "
        f"'{_text(row.remarks)}', correlation {row.correlation_id}",
        "sandbox",
    )
    return row


def _text(value, n=80):
    text = str(value or "")
    return text if len(text) <= n else text[: n - 1] + "…"


def last_query_id(claim_id):
    from care.nhcx.models import ClaimQuery

    row = ClaimQuery.objects.filter(claim__external_id=claim_id).order_by("id").last()
    return row.id if row else 0


def enquire(ctx, claim_id, body, *, what):
    from care.nhcx.models import ClaimEnquiry

    sent = ctx.send(what, "POST", f"claims/{claim_id}/enquiry/", body)
    row = ClaimEnquiry.objects.get(external_id=sent["enquiry_id"])
    ctx.corr(row.correlation_id)
    ctx.check(
        row.status != "error",
        f"{what} goes out",
        f"{row.kind} on {row.stage}, {row.status}, correlation {row.correlation_id}"
        + (f", {row.error_message}" if row.error_message else ""),
        "sandbox",
    )
    return row


def wait_enquiry(ctx, claim_id, row, *, what):
    from care.nhcx.models import ClaimEnquiry

    def ready(_k):
        r = ClaimEnquiry.objects.get(id=row.id)
        return r.status if r.status != "asking" else None

    status, how = ctx.wait_for(what, claim_id, ready, row.correlation_id)
    row = ClaimEnquiry.objects.get(id=row.id)
    ctx.check(
        status == "answered",
        what,
        f"{status} by {how}: {_text(row.answer)} {_text(row.detail)}"
        + (f", {row.error_message}" if row.error_message else ""),
        "sandbox",
    )
    return row


def cancel_preauth(ctx, claim_id, *, reason="administrativeerror", note="e2e cancel"):
    ctx.send(
        "provider cancels the pre-authorisation",
        "POST",
        f"claims/{claim_id}/preauth/cancel/",
        {"reason": reason, "note": note},
    )
    row = preauth_row(ctx, claim_id)
    ctx.corr(row.cancel_correlation_id)
    ctx.check(
        bool(row.cancel_correlation_id),
        "cancel goes out",
        f"{row.status} (was {row.pre_cancel_status}), "
        f"correlation {row.cancel_correlation_id}",
    )

    def ready(_k):
        r = preauth_row(ctx, claim_id)
        return r.status if r.status != "cancelling" else None

    _status, how = ctx.wait_for(
        "payer answers the cancel (C7)", claim_id, ready, row.cancel_correlation_id
    )
    return preauth_row(ctx, claim_id), how


def payments(claim_id):
    from care.nhcx.models import ClaimPayment

    return list(ClaimPayment.objects.filter(claim__external_id=claim_id).order_by("id"))


def pay(ctx, claim_id, amount, utr):
    """Payer side: pays with a UTR; waits for C10 and the A8 acknowledgement."""
    from care.nhcx.tests.e2e.payer import driver

    before = len(payments(claim_id))
    record = driver.irdai_pay(ctx.claim(claim_id), amount, utr)
    ctx.decisions.append({"stage": "payment", **record})
    ctx.check(
        not record.get("error"),
        f"payer pays {amount} (UTR {utr})",
        f"case {record.get('case')}, HTTP {record.get('status')}"
        + (f", {record.get('error')}" if record.get("error") else ""),
        "sandbox",
    )
    rows, how = ctx.wait_for(
        "payment notice arrives (C10)",
        claim_id,
        lambda _k: payments(claim_id)[before:] or None,
    )
    row = rows[-1]
    ctx.corr(row.correlation_id)
    ctx.check(
        row.utr == utr,
        "payment notice arrives (C10)",
        f"by {how}: {row.amount} UTR {row.utr}, {row.payment_status}, "
        f"correlation {row.correlation_id}",
        "sandbox",
    )
    import time

    from care.nhcx.models import ClaimPayment

    ack = None
    for _ in range(20):
        ack = ClaimPayment.objects.get(id=row.id).ack_status
        if ack not in (None, "", "pending"):
            break
        time.sleep(3)
    if ack in (None, "", "pending"):
        ctx.send(
            "provider acknowledges the payment (A8)",
            "POST",
            f"claims/{claim_id}/payments/{row.external_id}/ack/",
            {},
        )
    row = ClaimPayment.objects.get(id=row.id)
    ctx.corr(row.ack_correlation_id)
    ctx.check(
        row.ack_status not in (None, "", "error") and not row.ack_error,
        "acknowledgement goes out (A8)",
        f"{row.ack_status}, correlation {row.ack_correlation_id}"
        + (f", {row.ack_error}" if row.ack_error else ""),
        "sandbox",
    )
    return row


def decide_refused(ctx, claim_id, stage, decision, remarks=""):
    """A decision expected to be refused: recorded, never failing the step."""
    from care.nhcx.tests.e2e.payer import driver

    record = driver.decide(ctx.claim(claim_id), stage, decision, remarks)
    ctx.decisions.append(record)
    return record


def desk_case(ctx, claim_id, stage):
    from care.nhcx.tests.e2e.payer import driver

    try:
        return driver.irdai_case(ctx.claim(claim_id), stage)
    except Exception as e:
        return {"error": str(e)}


def desk_reply_view(case):
    if case.get("error"):
        return case["error"]
    timeline = case.get("timeline") or []
    last = timeline[-1] if timeline else {}
    docs = case.get("documents") or []
    return (
        f"{len(timeline)} timeline entries, last '{_text(last.get('title'), 60)}'; "
        f"{len(docs)} documents"
    )


def preauth_history(row):
    hist = row.history if isinstance(row.history, list) else []
    return [h.get("status") or h.get("kind") for h in hist if isinstance(h, dict)][-6:]


def item_view(row):
    items = row.items_json if isinstance(row.items_json, list) else []
    return (
        "; ".join(
            f"{i.get('code')} {i.get('approved_amount') or i.get('adjudication') or ''}"
            for i in items
            if isinstance(i, dict)
        )[:200]
        or "-"
    )


def thread_verdicts(correlation_id):
    """(ledger id, adjudication) of every complete reply on one thread, oldest first."""
    from care.nhcx.fhir import bundle as fb
    from care.nhcx.gateway import get_gateway

    ledger = get_gateway().ledger
    out = []
    rows = ledger.list_summaries(correlation_id=str(correlation_id), limit=50)
    for row in sorted(rows, key=lambda r: r["id"]):
        if row.get("direction") != "in" or row.get("hcx_status") != "response.complete":
            continue
        try:
            body = (ledger.fhir(row["id"]) or {}).get("fhir") or {}
            resp = fb.find_resource(fb.unwrap(body), "ClaimResponse") or {}
        except Exception:
            resp = {}
        verdict = ""
        for adj in resp.get("adjudication") or []:
            for coding in (adj.get("reason") or {}).get("coding") or []:
                verdict = verdict or coding.get("code") or ""
        out.append((row["id"], verdict or resp.get("outcome") or ""))
    return out


def open_preauths(payer_code_, member):
    """Pre-authorisations still holding the beneficiary's cover: open, no claim filed."""
    from care.nhcx.models import ClaimPreauth, ClaimSubmission

    # a claim the gateway refused (or never sent) did not consume the pre-auth
    filed = ClaimSubmission.objects.exclude(status__in=("draft", "error")).values_list(
        "claim_id", flat=True
    )
    return list(
        ClaimPreauth.objects.filter(
            claim__payer_id=payer_code_,
            claim__member_id=member,
            status__in=OPEN_PREAUTH,
        )
        .exclude(claim_id__in=filed)
        .select_related("claim")
        .order_by("id")
    )


def free_beneficiary(ctx, payer):
    """T2X: cancels the beneficiary's open pre-authorisations before a run."""
    code, member = payer_code(ctx, payer), member_id(ctx, payer)
    rows = open_preauths(code, member)
    sent = []
    for row in rows:
        claim_id = str(row.claim.external_id)
        try:
            ctx.api(
                "POST",
                f"claims/{claim_id}/preauth/cancel/",
                {"reason": "administrativeerror", "note": "e2e: free the beneficiary"},
            )
        except Refused as exc:
            ctx.step(f"free {row.claim.claim_no}", f"cancel not sent: {exc}", "skipped")
            continue
        row.refresh_from_db()
        if row.cancel_correlation_id:
            ctx.corr(row.cancel_correlation_id)
            sent.append(row)
    deadline = timezone.now() + timedelta(seconds=ctx.wait)
    pending = list(sent)
    while pending and timezone.now() < deadline:
        import time

        time.sleep(3)
        for row in list(pending):
            row.refresh_from_db()
            if row.status != "cancelling":
                pending.remove(row)
    done = {}
    for row in sent:
        row.refresh_from_db()
        done[row.claim.claim_no] = row.status
    ctx.step(
        f"free the {payer} beneficiary's open pre-authorisations",
        f"{len(rows)} open; {done or 'none'}",
    )
    return done


def free_beneficiary_report(conf, payers=("irdai", "pmjay")):
    from care.nhcx.tests.e2e.cli.runner import Ctx

    out = {}
    for payer in payers:
        ctx = Ctx(conf, "FREE", "cli")
        try:
            out[payer] = free_beneficiary(ctx, payer)
        except Exception as exc:
            out[payer] = f"not freed: {exc}"
    return out


# ---- PMJAY ----

PMJAY_PACKAGE = "SB043F"
PMJAY_CYCLIC = "MG072C"
PMJAY_PROGRAMME = "AB-PMJAY"
PLAN_ASKED = "pmjay_plan_correlation"


def seed_plan(ctx, claim_id):
    from care.nhcx.tests.e2e import seed

    wrote, detail = seed.apply(ctx.claim(claim_id), ctx.conf)
    row = ctx.claim(claim_id).plan
    ctx.check(
        row is not None and row.status == "ready",
        "package master seeded" if wrote else "payer's own package master is ready",
        detail,
        "setup",
    )
    return row


def plan_once(ctx, claim_id):
    """T13: the plan request goes out once per run; its answer is never waited for."""
    asked = taken_over(PLAN_ASKED)
    if asked:
        ctx.corr(asked)
        ctx.step("plan request already sent this run", f"correlation {asked}")
        return asked
    try:
        ctx.api("POST", f"claims/{claim_id}/plan/", {})
    except Refused as e:
        ctx.step("plan request goes out", f"refused {e.status}: {e.error}", "skipped")
        return ""
    row = ctx.claim(claim_id).plan
    ctx.corr(row.correlation_id)
    ctx.check(
        row.status != "error",
        "plan request goes out (not waited for)",
        f"{row.status}, correlation {row.correlation_id}"
        + (f", {row.error_message}" if row.error_message else ""),
        "sandbox",
    )
    hand_over(PLAN_ASKED, row.correlation_id)
    return row.correlation_id


def prepare_pmjay(ctx, *, code=PMJAY_PACKAGE, quantity=1, label="", fill=True):
    """A PMJAY claim: beneficiary freed, eligible, seeded plan, one line, its ruling."""
    free_beneficiary(ctx, "pmjay")
    claim_id, _policy = open_claim(ctx, "pmjay", label=label)
    eligibility(ctx, claim_id, "validation")
    admit(ctx, claim_id)
    seed_plan(ctx, claim_id)
    add_line(ctx, claim_id, code, quantity)
    rule(ctx, claim_id)
    if fill:
        fill_draft(ctx, claim_id)
    return claim_id


def program_codes(row) -> list:
    from care.nhcx.fhir import bundle as fb

    body = row.request_json if isinstance(row.request_json, dict) else {}
    claim = fb.find_resource(fb.unwrap(body), "Claim") or {}
    out = []
    for item in claim.get("item") or []:
        codes = item.get("programCode") or [{}]
        coding = (codes[0].get("coding") or [{}])[0]
        out.append(coding.get("code") or "")
    return out


def pmjay_decision(ctx, claim_id, stage, decision, remarks=""):
    """Reads the role and runs the cycle unless the sandbox decided by itself."""
    return decide(ctx, claim_id, stage, decision, remarks)


def pmjay_preauth(ctx, claim_id, *, decision="approve", remarks="e2e approval"):
    """Sends, waits for the acknowledgement, walks the roles, waits for the verdict."""
    row = submit_preauth(ctx, claim_id)
    ctx.check(
        program_codes(row) and all(c == PMJAY_PROGRAMME for c in program_codes(row)),
        "every line carries the AB-PMJAY programme code",
        f"{program_codes(row)}, workflow {row.workflow_id}",
    )
    wait_ack(
        ctx, claim_id, row.correlation_id, "PMJAY acknowledges the pre-authorisation"
    )
    record = pmjay_decision(ctx, claim_id, "preauth", decision, remarks)
    row, how = wait_preauth(ctx, claim_id, row.correlation_id)
    return row, how, record


def inbound(correlation_id) -> list:
    from care.nhcx.gateway import get_gateway

    rows = get_gateway().ledger.list_summaries(
        correlation_id=str(correlation_id), limit=50
    )
    return sorted(
        (r for r in rows if r.get("direction") == "in"), key=lambda r: r["id"]
    )


def wait_ack(ctx, claim_id, corr, what):
    """The first reply on the thread (an acknowledgement or the verdict itself)."""
    got, how = ctx.wait_for(what, claim_id, lambda _k: inbound(corr) or None, corr)
    first = got[0]
    ctx.step(what, f"{first['id']} {first.get('hcx_status')} by {how}")
    return got
