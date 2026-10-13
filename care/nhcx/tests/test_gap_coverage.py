"""L7.3-L7.5 coverage gaps: ProtocolResponse refusals on C3, C6 and C8; the A4
predetermination, A6 reprocess/release, A14/A15 adjudicator, A16 token and
A18 biometric sends; and the D rows no other test writes (D12, D17, D19, D24,
D27, D29). No network: services run against the FakeGateway and a stubbed
``requests.request``."""

import json
from datetime import date
from decimal import Decimal
from unittest import mock

from django.test import override_settings

from care.nhcx.callbacks import dispatch
from care.nhcx.models import (
    ClaimAdjudication,
    ClaimAuth,
    ClaimEnquiry,
    ClaimPlan,
    ClaimPreauth,
    ClaimPredetermination,
    ClaimSubmission,
)
from care.nhcx.models.abha import set_abha
from care.nhcx.models.biometric import BiometricAuth
from care.nhcx.models.draft import ClaimFormAnswer, ClaimItem
from care.nhcx.services import (
    adjudicator,
    biometric,
    draft,
    eligibility,
    plan,
)
from care.nhcx.services import claim as claim_service
from care.nhcx.services import preauth as preauth_service
from care.nhcx.services.common import ServiceRefusal
from care.nhcx.tests.core_helpers import PAYER_CODE, NhcxCoreTestBase, bundle
from care.nhcx.tests.test_callbacks_legs import (
    PROTOCOL_ERROR,
    LegCallbackBase,
)

ABHA = "91-1234-1234-1234"


class Reply:
    def __init__(self, status=200, body=None):
        self.status_code = status
        self._body = body
        self.text = json.dumps(body) if body is not None else ""

    def json(self):
        if self._body is None:
            raise ValueError("no body")
        return self._body


class ProtocolRefusalTests(LegCallbackBase):
    """A ProtocolResponse (response.error) settles the matching leg as an error
    and keeps its ids, for the legs no other test refuses."""

    def test_c3_protocol_refusal(self):
        claim = self.eligible_claim()
        claim.lines.create(kind="Procedure", code="MG0111A")
        eligibility.request_auth(claim)
        ruling = ClaimAuth.objects.get(claim=claim)
        out = self.receive(dict(PROTOCOL_ERROR), ruling.correlation_id, "coverage")
        self.assertEqual(out["outcome"], dispatch.SETTLED, out)
        ruling.refresh_from_db()
        self.assertEqual(ruling.status, "error")
        self.assertIn("ERR_INVALID_SIGNATURE", ruling.error_message)
        self.assertTrue(ruling.correlation_id)

    def test_c6_protocol_refusal(self):
        claim = self.eligible_claim()
        ClaimPreauth.objects.create(claim=claim, status="approved")
        row = ClaimSubmission.objects.create(
            claim=claim, status="submitting", correlation_id="corr-cl", txn_id="t"
        )
        out = self.receive(dict(PROTOCOL_ERROR), "corr-cl", "claim")
        self.assertEqual(out["outcome"], dispatch.SETTLED, out)
        row.refresh_from_db()
        self.assertEqual(row.status, "error")
        self.assertIn("ERR_INVALID_SIGNATURE", row.error_message)
        self.assertEqual((row.correlation_id, row.txn_id), ("corr-cl", "t"))

    def test_c8_protocol_refusal(self):
        claim = self.eligible_claim()
        ClaimSubmission.objects.create(
            claim=claim, status="rejected", correlation_id="corr-cl"
        )
        ask = ClaimEnquiry.objects.create(
            claim=claim,
            kind="reprocess",
            stage="claim",
            status="asking",
            correlation_id="corr-rp",
        )
        out = self.receive(dict(PROTOCOL_ERROR), "corr-rp", "task", route="C8")
        self.assertEqual(out["outcome"], dispatch.SETTLED, out)
        ask.refresh_from_db()
        self.assertEqual(ask.status, "error")
        self.assertIn("ERR_INVALID_SIGNATURE", ask.error_message)

    def test_c2_protocol_refusal_then_redelivery(self):
        claim = self.make_claim()
        eligibility.run_check(claim, "validation", "POL-1", "PMJAY123")
        claim.refresh_from_db()
        out = self.receive(dict(PROTOCOL_ERROR), claim.correlation_id, "coverage")
        self.assertEqual(out["outcome"], dispatch.SETTLED, out)
        claim.refresh_from_db()
        self.assertEqual(claim.status, "error")
        again = self.receive(dict(PROTOCOL_ERROR), claim.correlation_id, "coverage")
        self.assertNotEqual(again["outcome"], dispatch.ERROR, again)


class ReadyClaimMixin:
    def ready_claim(self, **kw):
        patient = self.create_patient(name="Ravi")
        set_abha(patient, number=ABHA)
        org = self.create_facility_organization(facility=self.facility)
        enc = self.create_encounter(patient, self.facility, org)
        claim = self.make_claim(
            status="eligible",
            abha_number=ABHA,
            patient=patient,
            encounter=enc,
            admission_date=date(2026, 1, 2),
            **kw,
        )
        draft.save_draft(
            claim,
            {
                "diagnoses": [{"icd10_code": "K35.8", "icd10_display": "Appendicitis"}],
                "care_team": [{"role": "treating", "practitioner": self.user.id}],
            },
        )
        claim.lines.create(
            kind="Procedure",
            code="MG0111A",
            display="Appendicectomy",
            unit_price=Decimal(20000),
            amount=Decimal(20000),
        )
        return claim


class LegServiceGapTests(ReadyClaimMixin, NhcxCoreTestBase):
    def test_a4_predetermination_sent(self):
        claim = self.ready_claim()
        row = preauth_service.ask_predetermination(claim)
        self.assertEqual(row.status, "asking")
        self.assertTrue(row.correlation_id)
        self.assertEqual(self.gw.sent[-1][0], preauth_service.PATH)
        with self.assertRaisesMessage(ServiceRefusal, preauth_service.QUOTE_WAITING):
            preauth_service.ask_predetermination(claim)
        self.assertEqual(ClaimPredetermination.objects.filter(claim=claim).count(), 1)

    def test_a4_preauth_submit_sends_claim_bundle(self):
        claim = self.ready_claim()
        row = preauth_service.submit_preauth(claim)
        self.assertEqual((row.status, row.submission_kind), ("submitting", "preauth"))
        path, envelope = self.gw.sent[-1][:2]
        self.assertEqual(path, "v1/preauth/submit")
        self.assertEqual(envelope["fhir"]["resourceType"], "Bundle")
        claim.refresh_from_db()
        self.assertEqual((claim.stage, claim.sub_stage), ("preauth", "requested"))

    def test_a6_reprocess_and_release(self):
        claim = self.ready_claim()
        state = ClaimSubmission.objects.create(
            claim=claim,
            status="rejected",
            correlation_id="corr-cl",
            claim_ref=claim.claim_no,
            requested_amount=Decimal(20000),
        )
        with self.assertRaisesMessage(ServiceRefusal, claim_service.BAD_REPROCESS_CODE):
            claim_service.ask_reprocess(claim, "Bills attached", "bogus")
        ask = claim_service.ask_reprocess(claim, "Bills attached", "claimrejected")
        self.assertEqual((ask.kind, ask.status), ("reprocess", "asking"))
        self.assertEqual(self.gw.sent[-1][0], "v1/task/submit")
        with self.assertRaisesMessage(
            ServiceRefusal, claim_service.RELEASE_NOT_DECIDED
        ):
            claim_service.ask_release(claim, "100")
        state.status = "partial"
        state.save()
        with self.assertRaisesMessage(ServiceRefusal, claim_service.NO_AMOUNT):
            claim_service.ask_release(claim, "-1")
        release = claim_service.ask_release(claim, "5000", "balance")
        self.assertEqual((release.kind, release.amount), ("release", Decimal(5000)))
        self.assertEqual(ClaimEnquiry.objects.filter(claim=claim).count(), 2)

    def test_d17_d27_draft_rows(self):
        claim = self.ready_claim()
        draft.save_draft(
            claim,
            {
                "answers": [
                    {"form_url": "https://forms.test/q1", "link_id": "a", "answer": "y"}
                ]
            },
        )
        answer = ClaimFormAnswer.objects.get(claim=claim)
        self.assertEqual((answer.link_id, answer.answer), ("a", "y"))
        item = ClaimItem.objects.create(
            claim=claim,
            code="CM-1",
            display="Ward bed",
            unit_price=Decimal(1000),
            quantity=Decimal(2),
            amount=Decimal(2000),
        )
        self.assertEqual(list(claim.items.all()), [item])

    def test_d12_consent_form_dropped_once_verified(self):
        """A ruling naming form 100024 is not sent once a user token is held."""
        from types import SimpleNamespace

        from care.nhcx.models.plan import ClaimPlanForm
        from care.nhcx.services import _gather

        claim = self.ready_claim()
        row = ClaimPlan.objects.create(claim=claim, status="ready")
        consent = ClaimPlanForm.objects.create(
            plan=row,
            url="https://payer.test/q/100024",
            form_id="100024",
            title="Consent",
        )
        other = ClaimPlanForm.objects.create(
            plan=row,
            url="https://payer.test/q/100003",
            form_id="100003",
            title="Findings",
        )
        urls = [consent.url, other.url]
        biometric_payer = SimpleNamespace(biometric_required=True)
        with (
            mock.patch.object(_gather, "required_form_urls", return_value=urls),
            mock.patch.object(
                _gather.payers, "adapter_for_claim", return_value=biometric_payer
            ),
        ):
            with mock.patch.object(_gather, "has_token", return_value=False):
                before = [f.url for f in _gather.form_inputs(claim, "preauth")]
            with mock.patch.object(_gather, "has_token", return_value=True):
                after = [f.url for f in _gather.form_inputs(claim, "preauth")]
        self.assertEqual(before, urls)
        self.assertEqual(after, [other.url])

    def test_d17_screen_answers_round_trip(self):
        """The screens send form_answers and name a file answer by external id."""
        from care.nhcx.fhir.inputs import DocumentInput, FormInput
        from care.nhcx.models import ClaimDocument
        from care.nhcx.services import _gather
        from care.nhcx.services import state as state_service

        claim = self.ready_claim()
        doc = ClaimDocument.objects.create(
            claim=claim, content_type="application/pdf", data=b"%PDF", size=4
        )
        url = "https://forms.test/q2"
        message = draft.save_draft(
            claim,
            {
                "form_answers": [
                    {
                        "form_url": url,
                        "link_id": "t",
                        "answer": "y",
                        "stage": "preauth",
                    },
                    {
                        "form_url": url,
                        "link_id": "f",
                        "answer": str(doc.external_id),
                        "stage": "preauth",
                    },
                ]
            },
        )
        self.assertEqual(message, draft.ANSWERS_SAVED)
        form = FormInput(
            url=url,
            items=[
                {"linkId": "t", "type": "string"},
                {"linkId": "f", "type": "attachment"},
            ],
        )
        got = {a.link_id: a.answer for a in _gather.answers(claim, "preauth", [form])}
        self.assertEqual(got["t"], "y")
        self.assertIsInstance(got["f"], DocumentInput)
        rows = state_service.claim_state(claim)["form_answers"]
        self.assertEqual(
            {(r["link_id"], r["answer"]) for r in rows},
            {("t", "y"), ("f", str(doc.external_id))},
        )

    def test_a17_state_names_linked_admission(self):
        """The screens read claim.encounter / claim.patient to show the S4 link."""
        from care.nhcx.services import state as state_service

        claim = self.ready_claim()
        row = state_service.claim_state(claim)["claim"]
        self.assertEqual(row["encounter"], str(claim.encounter.external_id))
        self.assertEqual(row["patient"], str(claim.patient.external_id))
        self.assertEqual(row["encounter_id"], row["encounter"])
        self.assertIsNotNone(row["preauth_saved_at"])
        got = state_service.claim_state(claim)
        self.assertEqual([d["icd10_code"] for d in got["diagnoses"]], ["K35.8"])
        member = got["care_team"][0]
        self.assertEqual(member["practitioner"], str(self.user.external_id))
        self.assertTrue(member["practitioner_name"])
        self.assertEqual(member["role"], "treating")

    def test_d12_plan_forms(self):
        claim = self.make_claim()
        plan.request_plan(claim)
        row = ClaimPlan.objects.get(claim=claim)
        self.receive_plan(row)
        row.refresh_from_db()
        forms = list(row.forms.all())
        self.assertTrue(forms)
        self.assertTrue(all(f.url for f in forms))

    def receive_plan(self, row):
        dispatch.receive(
            self.envelope(bundle("plan-response-pmjay.json"), row.correlation_id),
            {"type": "insurance", "payload_kind": "jwe"},
        )


@override_settings(
    NHCX_ADJUDICATOR_CONSOLE=True,
    NHCX_PAYER_ADAPTERS=json.dumps({PAYER_CODE: "pmjay"}),
)
class AdjudicatorTests(NhcxCoreTestBase):
    def setUp(self):
        super().setUp()
        self.claim = self.make_claim(status="eligible")
        ClaimPreauth.objects.create(
            claim=self.claim,
            status="queued",
            correlation_id="corr-pa",
            preauth_ref="https://payer.test/preauth/PA-77",
        )
        self.gw.token = mock.Mock(return_value={"token": "sess-1"})

    def test_a16_token_from_gateway_or_setting(self):
        self.assertEqual(adjudicator.token(self.claim), "sess-1")
        with override_settings(NHCX_PAYER_SERVICE_TOKEN="svc"):
            self.assertEqual(adjudicator.token(self.claim), "svc")
        self.gw.token = mock.Mock(side_effect=RuntimeError("down"))
        with self.assertRaises(adjudicator.AdjudicatorError):
            adjudicator.token(self.claim)

    def test_a14_role_then_a15_process(self):
        calls = []

        def fake(method, url, headers=None, json=None, timeout=None):
            calls.append((url, headers, json))
            if url == adjudicator.ROLE_URL:
                return Reply(200, {"data": {"userRole": "PPD-Trust"}})
            return Reply(200, {"status": "ok"})

        with mock.patch.object(adjudicator.requests, "request", side_effect=fake):
            found = adjudicator.read_role(self.claim, "preauth")
            self.assertEqual(found["role"], "PPD-Trust")
            self.assertEqual(found["caseNumber"], "PA-77")
            self.assertEqual(calls[0][1]["Authorization"], "Bearer sess-1")
            with self.assertRaises(adjudicator.AdjudicatorError):
                adjudicator.process(self.claim, "preauth", "PPD-Trust", "Forward")
            done = adjudicator.process(self.claim, "preauth", "PPD-Trust", "approve")
        self.assertTrue(done["success"], done)
        self.assertEqual(calls[-1][0], adjudicator.PROCESS_URL)
        self.assertEqual(calls[-1][2]["action"], "Approve")
        self.assertEqual(calls[-1][2]["correlationid"], "corr-pa")
        row = ClaimAdjudication.objects.get(claim=self.claim)
        self.assertEqual(
            (row.role, row.action, row.success), ("PPD-Trust", "Approve", True)
        )

    @override_settings(NHCX_ADJUDICATOR_ROLE_SETTLE_SECONDS=0)
    def test_a15_walk_waits_for_forwarded_case_to_move(self):
        """The payer service answers Forward before it moves the case on."""
        ClaimSubmission.objects.create(
            claim=self.claim, status="submitting", correlation_id="corr-cl"
        )
        roles = iter(
            [
                "CEX-Trust",
                "CEX-Trust",
                "CEX-Trust",
                "CPD-Trust",
                "Claim Review Committee",
            ]
        )
        with (
            mock.patch.object(
                adjudicator, "role_for", side_effect=lambda *a: {"role": next(roles)}
            ),
            mock.patch.object(
                adjudicator,
                "process",
                side_effect=lambda c, s, role, action, *a: {
                    "success": True,
                    "role": role,
                    "action": action,
                },
            ),
        ):
            done = adjudicator.cycle(self.claim, "claim", "approve")
        self.assertEqual(done["stopped"], "completed")
        self.assertEqual(
            [s["role"] for s in done["steps"]],
            ["CEX-Trust", "CPD-Trust", "Claim Review Committee"],
        )

    def test_a15_service_error_recorded(self):
        with mock.patch.object(
            adjudicator.requests,
            "request",
            return_value=Reply(500, {"errorMessage": "case locked"}),
        ):
            done = adjudicator.process(self.claim, "preauth", "PPD-Trust", "Reject")
        self.assertFalse(done["success"])
        self.assertEqual(done["error"], "case locked")
        self.assertFalse(ClaimAdjudication.objects.get(claim=self.claim).success)


class BiometricTests(ReadyClaimMixin, NhcxCoreTestBase):
    def test_a18_fingerprint_init_verify_and_headers(self):
        claim = self.ready_claim()
        self.gw.token = mock.Mock(return_value={"token": "sess-1"})
        calls = []

        def fake(method, url, headers=None, json=None, timeout=None):
            calls.append((url, headers, json))
            if url.endswith("/auth/init"):
                return Reply(200, {"txnId": "bio-txn", "message": "ok"})
            return Reply(
                200,
                {
                    "authResult": "success",
                    "tokens": {"token": "user-tok", "expiresIn": 1800},
                    "accounts": [{"ABHANumber": ABHA}],
                },
            )

        with mock.patch.object(biometric.requests, "request", side_effect=fake):
            row, qr = biometric.init(claim, "FINGERPRINT")
            self.assertIsNone(qr)
            self.assertEqual((row.status, row.txn_id), ("initiated", "bio-txn"))
            self.assertEqual(calls[0][2]["loginId"], ABHA)
            self.assertEqual(calls[0][1]["process"], row.stage)
            with self.assertRaises(biometric.BiometricError):
                biometric.verify(row)
            row = biometric.verify(row, pid="<PidData/>")
        self.assertEqual((row.status, row.user_token), ("verified", "user-tok"))
        headers = biometric.headers_for(claim, row.stage)
        self.assertEqual(headers[biometric.token_header()], "user-tok")
        self.assertEqual(headers["x-hcx-ben-abha-id"], row.abha_number)

    def test_a18_service_refusal_fails_the_attempt(self):
        claim = self.ready_claim()
        self.gw.token = mock.Mock(return_value={"token": "sess-1"})
        with (
            mock.patch.object(
                biometric.requests,
                "request",
                return_value=Reply(400, {"code": "ABDM-1001", "message": "bad abha"}),
            ),
            self.assertRaises(biometric.BiometricError),
        ):
            biometric.init(claim, "IRIS")
        row = BiometricAuth.objects.get(claim=claim)
        self.assertEqual(row.status, "failed")
