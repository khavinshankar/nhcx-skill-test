"""L7.7 dry run: one claim walked S1 to S12 through the real API endpoints, with
a real Gateway (G1) opened on a throwaway config and test keys, against a fake
NHCX and registry. Every outbound request is encrypted by G6 for the payer's
test certificate and decrypted here with the payer's test key; every payer
reply is encrypted for the facility's test key and delivered through the G8
inbound route, so the C1 dispatcher sees what NHCX would hand it.

No call leaves the process (the network guard in tests/__init__.py refuses it).
"""

import json

from django.test import override_settings

from care.nhcx.callbacks import dispatch
from care.nhcx.gateway import crypto, reset_gateway, set_gateway
from care.nhcx.gateway import headers as H  # noqa: N812
from care.nhcx.models import (
    Claim,
    ClaimAuth,
    ClaimPayment,
    ClaimPlan,
    ClaimPreauth,
    ClaimQuery,
    ClaimSubmission,
)
from care.nhcx.models.abha import set_abha
from care.nhcx.tests.core_helpers import NhcxCoreTestBase, bundle
from care.nhcx.tests.gateway_helpers import (
    FACILITY,
    PARTICIPANT_URL,
    PAYER,
    FakeResponse,
    ScratchDirMixin,
    key,
)

ABHA = "91-1234-1234-1234"
POLICY = {
    "memberid": "MEM-7781",
    "name": "Ravi Kumar",
    "payerid": PAYER,
    "policyno": "POL-7781",
    "productname": "Family Floater Gold",
    "abhanumber": ABHA,
}
PAYER_RECORD = {
    "participants": [
        {
            "participant_code": PAYER,
            "participant_name": "Acme Health Insurance",
            "status": "Active",
            "roles": ["payor"],
        }
    ]
}
# claim numbers baked into the fixture bundles, rewritten to the case's own
FIXTURE_CLAIM_NOS = (
    "NM-26-0SE00002I",
    "NM-26-0SE00002M",
    "NM-26-0SE00002L",
    "NM-26-0SF000031",
    "EO26AA2700001",
)


@override_settings(NHCX_DEFAULT_PAYER_CODE=PAYER)
class DryFlowBase(ScratchDirMixin, NhcxCoreTestBase):
    payer_name = "Acme Health Insurance"

    def setUp(self):
        super().setUp()
        record = json.loads(json.dumps(PAYER_RECORD))
        record["participants"][0]["participant_name"] = self.payer_name
        self.gw = self.open_gateway(receive=dispatch.receive)
        self.addCleanup(self.gw.stop)
        self.http.on(
            PARTICIPANT_URL + "/participant/get/policies", FakeResponse(200, [POLICY])
        )
        self.http.on(PARTICIPANT_URL + "/participant/search", FakeResponse(200, record))
        set_gateway(self.gw)
        self.addCleanup(reset_gateway)
        self.profile.participant_code = FACILITY
        self.profile.save()
        self.payer_key = crypto.parse_private_key(key("payer-private.pem"))
        self.facility_public = crypto.parse_public_key(key("facility-public.pem"))
        self.client.force_authenticate(self.user)

    # ---- API ----

    def url(self, suffix=""):
        return f"/api/v1/facility/{self.facility.external_id}/nhcx/{suffix}"

    def post(self, suffix, data=None, expect=200):
        resp = self.client.post(self.url(suffix), data or {}, format="json")
        self.assertEqual(resp.status_code, expect, getattr(resp, "data", resp))
        return resp

    def put(self, suffix, data):
        resp = self.client.put(self.url(suffix), data, format="json")
        self.assertEqual(resp.status_code, 200, getattr(resp, "data", resp))
        return resp

    def state(self, claim_id):
        resp = self.client.get(self.url(f"claims/{claim_id}/state/"))
        self.assertEqual(resp.status_code, 200, getattr(resp, "data", resp))
        return resp.data

    # ---- fake NHCX ----

    def sent(self, path_suffix):
        """The last request G6 posted to NHCX on ``path_suffix``, as the payer
        would decrypt it: (protected headers, FHIR bundle)."""
        calls = self.http.calls_to(path_suffix)
        self.assertTrue(calls, f"nothing was sent to {path_suffix}")
        data = calls[-1]["data"]
        payload = json.loads(data)["payload"]
        hdr = crypto.parse_header(payload)
        fhir = json.loads(crypto.decrypt(payload, self.payer_key))
        self.assertEqual(hdr[H.SENDER_CODE], FACILITY)
        self.assertEqual(hdr[H.RECIPIENT_CODE], PAYER)
        return hdr, fhir

    def reply(self, path, fhir, corr, *, workflow="", status="response.complete"):
        """The payer's answer, encrypted for the facility and posted to the G8
        inbound route as NHCX would. Returns the JSON acknowledgement."""
        hdr = {
            H.SENDER_CODE: PAYER,
            H.RECIPIENT_CODE: FACILITY,
            H.API_CALL_ID: H.new_id(),
            H.CORRELATION_ID: corr,
            H.REQUEST_ID: H.new_id(),
            H.TIMESTAMP: H.timestamp(),
            H.STATUS: status,
        }
        if workflow:
            hdr[H.WORKFLOW_ID] = workflow
        jwe = crypto.encrypt(json.dumps(fhir), self.facility_public, hdr)
        self.last_inbound = json.dumps({"payload": jwe}).encode()
        return self.deliver(path, self.last_inbound)

    def deliver(self, path, body):
        resp = self.client.generic(
            "POST", f"/{path}", body, content_type="application/json"
        )
        self.assertEqual(resp.status_code, 202, resp.content)
        out = json.loads(resp.content)
        self.assertIsNone(out.get("error"), out)
        return out

    def ours(self, name, claim):
        text = json.dumps(bundle(name))
        for other in FIXTURE_CLAIM_NOS:
            text = text.replace(other, claim.claim_no)
        return json.loads(text)


class DryFlowTests(DryFlowBase):
    def test_claim_s1_to_s12(self):  # noqa: PLR0915
        # S1/S2, A1 via G10: policy search on the registry
        found = self.post("policy-search/", {"member_id": "MEM-7781"})
        self.assertEqual(found.data["policies"][0]["member_id"], "MEM-7781")
        asked = self.http.calls_to("/participant/get/policies")
        self.assertEqual(
            json.loads(asked[-1]["data"])
            if isinstance(asked[-1]["data"], str | bytes)
            else asked[-1]["data"],
            {"identifiertype": "MemberId", "identifiervalue": "MEM-7781"},
        )

        # S2: open the case (D9)
        opened = self.post(
            "claims/",
            {
                "policy": found.data["policies"][0]["raw"],
                "identifiertype": "MemberId",
                "identifiervalue": "MEM-7781",
            },
        )
        claim_id = opened.data["claim_id"]
        claim = Claim.objects.get(external_id=claim_id)
        self.assertEqual((claim.payer_id, claim.member_id), (PAYER, "MEM-7781"))
        self.assertEqual(claim.stage, "eligibility")

        # S3, A2 -> C2: eligibility
        checked = self.post(
            f"claims/{claim_id}/eligibility/", {"purpose": "validation"}
        )
        self.assertEqual(
            checked.data["message"], "Eligibility request queued to the payer."
        )
        claim.refresh_from_db()
        self.assertEqual(claim.status, "checking")
        hdr, fhir = self.sent("coverageeligibility/check")
        self.assertEqual(fhir["resourceType"], "Bundle")
        self.assertEqual(hdr[H.CORRELATION_ID], claim.correlation_id)
        ack = self.reply(
            "v1/coverageeligibility/on_check",
            bundle("eligibility-response-generic.json"),
            claim.correlation_id,
        )
        self.assertEqual(ack["correlation_id"], claim.correlation_id)
        claim.refresh_from_db()
        self.assertEqual(claim.status, "eligible")
        self.assertEqual(claim.abha_number, ABHA)
        self.assertEqual((claim.stage, claim.sub_stage), ("eligibility", "eligible"))
        # NHCX redelivers the same reply: acknowledged, applied once
        self.deliver("v1/coverageeligibility/on_check", self.last_inbound)
        claim.refresh_from_db()
        self.assertEqual(claim.status, "eligible")

        # S7, A3 -> C4: the payer's insurance plan (D10-D12)
        self.post(f"claims/{claim_id}/plan/")
        plan = ClaimPlan.objects.get(claim=claim)
        self.assertEqual(plan.status, "fetching")
        hdr, _ = self.sent("insuranceplan/request")
        self.reply(
            "v1/insuranceplan/on_request",
            bundle("plan-response-generic.json"),
            plan.correlation_id,
        )
        plan.refresh_from_db()
        self.assertEqual(plan.status, "ready", plan.error_message)
        self.assertTrue(plan.benefits.exists())
        code = plan.benefits.filter(kind="Procedure").order_by("seq").first().code

        # S8: a line item from the plan (D16), then the auth requirements (C3)
        added = self.post(
            f"claims/{claim_id}/lines/", {"kind": "Procedure", "code": code}
        )
        self.assertEqual(added.data["line"]["code"], code)
        self.post(f"claims/{claim_id}/auth-requirements/")
        ruling = ClaimAuth.objects.get(claim=claim)
        self.assertEqual(ruling.status, "checking")
        _, fhir = self.sent("coverageeligibility/check")
        self.reply(
            "v1/coverageeligibility/on_check",
            bundle("eligibility-auth-response-pmjay.json"),
            ruling.correlation_id,
        )
        ruling.refresh_from_db()
        self.assertEqual(ruling.status, "ready", ruling.error_message)

        # S4: link the admission and fill the draft (D25, D26)
        patient = self.create_patient(name="Ravi Kumar")
        set_abha(patient, number=ABHA)
        org = self.create_facility_organization(facility=self.facility)
        enc = self.create_encounter(patient, self.facility, org)
        enc.encounter_class = "imp"
        enc.status = "in_progress"
        enc.period = {"start": "2026-01-02T10:00:00+05:30"}
        enc.save()
        self.post(f"claims/{claim_id}/admission/", {"encounter": str(enc.external_id)})
        self.put(
            f"claims/{claim_id}/draft/",
            {
                "diagnoses": [{"icd10_code": "K35.8", "icd10_display": "Appendicitis"}],
                "care_team": [{"role": "treating", "practitioner": self.user.id}],
            },
        )
        claim.refresh_from_db()
        self.assertEqual(claim.encounter_id, enc.id)
        self.assertEqual(claim.diagnoses.count(), 1)

        # S9, A4 -> C9/A7 -> C5: pre-authorisation, a payer query, the answer
        sent = self.post(f"claims/{claim_id}/preauth/submit/")
        self.assertEqual(
            sent.data["message"], "Pre-authorisation submitted to the payer."
        )
        preauth = ClaimPreauth.objects.get(claim=claim)
        self.assertEqual(preauth.status, "submitting")
        hdr, fhir = self.sent("preauth/submit")
        self.assertEqual(hdr[H.CORRELATION_ID], preauth.correlation_id)
        self.assertEqual(fhir["resourceType"], "Bundle")
        claim.refresh_from_db()
        self.assertEqual(claim.stage, "preauth")

        with self.captureOnCommitCallbacks(execute=True):
            self.reply(
                "v1/communication/request",
                self.ours("communication-query-wf24.json", claim),
                preauth.correlation_id,
                status="request.initiated",
            )
        query = ClaimQuery.objects.get(claim=claim)
        claim.refresh_from_db()
        self.assertEqual(claim.sub_stage, "queried")
        answered = self.post(
            f"claims/{claim_id}/queries/{query.external_id}/reply/",
            {"text": "Discharge summary attached as asked.", "document_ids": []},
        )
        self.assertEqual(answered.data["message"], "Reply sent to the payer.")
        hdr, fhir = self.sent("communication/on_request")
        self.assertEqual(fhir["resourceType"], "Bundle")
        query.refresh_from_db()
        self.assertEqual(query.status, "answered")
        self.assertIsNotNone(query.answered_at)
        claim.refresh_from_db()
        # the query is answered; the request is back with the payer
        self.assertEqual(claim.sub_stage, "requested")

        self.reply(
            "v1/preauth/on_submit",
            self.ours("preauth-approved-wf21.json", claim),
            preauth.correlation_id,
        )
        preauth.refresh_from_db()
        self.assertEqual(preauth.status, "approved", preauth.error_message)
        self.assertTrue(preauth.approved_amount)
        claim.refresh_from_db()
        self.assertEqual((claim.stage, claim.sub_stage), ("preauth", "approved"))

        # S11, A5 -> C6: discharge, then the claim
        self.post(
            f"claims/{claim_id}/discharge/",
            {
                "discharge_mode": "normal",
                "discharge_stage": "After Surgery",
                "discharge_date": "2026-01-06",
            },
        )
        self.post(f"claims/{claim_id}/claim/submit/")
        submission = ClaimSubmission.objects.get(claim=claim)
        self.assertEqual(submission.status, "submitting")
        hdr, fhir = self.sent("claim/submit")
        self.assertEqual(hdr[H.CORRELATION_ID], submission.correlation_id)
        claim.refresh_from_db()
        self.assertEqual(claim.stage, "claim")
        self.reply(
            "v1/claim/on_submit",
            self.ours("claim-approved-deduction-wf26-pmjay.json", claim),
            submission.correlation_id,
        )
        submission.refresh_from_db()
        self.assertIn(submission.status, {"approved", "partial"})

        # S12, C10 -> A8: the payment notice, acknowledged
        with self.captureOnCommitCallbacks(execute=True):
            self.reply(
                "v1/paymentnotice/request",
                self.ours("payment-notice-wf30.json", claim),
                submission.correlation_id,
                status="request.initiated",
            )
        money = ClaimPayment.objects.get(claim=claim)
        self.assertTrue(self.http.calls_to("paymentnotice/on_request"))
        money.refresh_from_db()
        self.assertEqual(money.ack_status, "sent")
        claim.refresh_from_db()
        self.assertEqual(claim.stage, "payment")
        acked = self.post(f"claims/{claim_id}/payments/{money.external_id}/ack/")
        self.assertEqual(acked.data["message"], "Payment acknowledged to the payer.")
        self.sent("paymentnotice/on_request")

        # A17: the state the screens read reflects the whole walk
        final = self.state(claim_id)
        self.assertEqual(final["claim"]["status"], "eligible")
        self.assertEqual(final["plan"]["status"], "ready")
        self.assertEqual([x["code"] for x in final["lines"]], [code])
        # A13: every leg was recorded in the ledger
        self.assertGreaterEqual(len(self.gw.ledger.list(limit=100)), 14)


class PmjayDryFlowTests(DryFlowBase):
    """T13-T18 variant: a payer registered as an SHA gets the PMJAY adapter, so
    the procedure set is validated unasked (C3) before the pre-auth, a payer
    query comes back on the pre-auth itself (C5 queried) and is answered by
    resubmitting it (A4, workflow 19), and the PMJAY workflow ids are sent."""

    payer_name = "SHA Kerala"

    def open_case(self):
        found = self.post("policy-search/", {"member_id": "MEM-7781"})
        opened = self.post(
            "claims/",
            {
                "policy": found.data["policies"][0]["raw"],
                "identifiertype": "MemberId",
                "identifiervalue": "MEM-7781",
            },
        )
        claim_id = opened.data["claim_id"]
        claim = Claim.objects.get(external_id=claim_id)
        self.post(f"claims/{claim_id}/eligibility/", {"purpose": "validation"})
        claim.refresh_from_db()
        self.reply(
            "v1/coverageeligibility/on_check",
            bundle("eligibility-response-generic.json"),
            claim.correlation_id,
        )
        self.post(f"claims/{claim_id}/plan/")
        plan = ClaimPlan.objects.get(claim=claim)
        self.reply(
            "v1/insuranceplan/on_request",
            bundle("plan-response-pmjay.json"),
            plan.correlation_id,
        )
        plan.refresh_from_db()
        self.assertEqual(plan.status, "ready", plan.error_message)
        self.post(f"claims/{claim_id}/lines/", {"kind": "Procedure", "code": "ST009B"})
        patient = self.create_patient(name="Ravi Kumar")
        set_abha(patient, number=ABHA)
        org = self.create_facility_organization(facility=self.facility)
        enc = self.create_encounter(patient, self.facility, org)
        enc.encounter_class = "imp"
        enc.status = "in_progress"
        enc.period = {"start": "2026-01-02T10:00:00+05:30"}
        enc.save()
        self.post(f"claims/{claim_id}/admission/", {"encounter": str(enc.external_id)})
        self.put(
            f"claims/{claim_id}/draft/",
            {
                "diagnoses": [{"icd10_code": "S72.0", "icd10_display": "Hip fracture"}],
                "care_team": [{"role": "treating", "practitioner": self.user.id}],
            },
        )
        claim.refresh_from_db()
        return claim_id, claim

    def test_pmjay_claim_with_preauth_query(self):
        claim_id, claim = self.open_case()
        self.assertEqual(claim.status, "eligible")

        # A4 under PMJAY: the unasked C3 check goes out first
        checks_before = len(self.http.calls_to("coverageeligibility/check"))
        self.post(f"claims/{claim_id}/preauth/submit/")
        self.assertEqual(
            len(self.http.calls_to("coverageeligibility/check")), checks_before + 1
        )
        ruling = ClaimAuth.objects.get(claim=claim)
        self.assertEqual(ruling.status, "checking")
        hdr, _ = self.sent("preauth/submit")
        self.assertEqual(hdr[H.WORKFLOW_ID], "12")
        preauth = ClaimPreauth.objects.get(claim=claim)
        self.reply(
            "v1/coverageeligibility/on_check",
            bundle("eligibility-auth-response-pmjay.json"),
            ruling.correlation_id,
        )
        ruling.refresh_from_db()
        self.assertEqual(ruling.status, "ready", ruling.error_message)

        # C5 queried, answered by resubmitting the pre-auth (workflow 19)
        self.reply(
            "v1/preauth/on_submit",
            self.ours("preauth-queried-wf24.json", claim),
            preauth.correlation_id,
        )
        preauth.refresh_from_db()
        self.assertEqual(preauth.status, "queried", preauth.error_message)
        claim.refresh_from_db()
        self.assertEqual((claim.stage, claim.sub_stage), ("preauth", "queried"))
        refused = self.post(f"claims/{claim_id}/preauth/submit/", expect=400)
        self.assertFalse(refused.data["ok"])
        self.post(
            f"claims/{claim_id}/preauth/submit/",
            {"reply": "X-ray and ortho notes attached."},
        )
        hdr, _ = self.sent("preauth/submit")
        self.assertEqual(hdr[H.WORKFLOW_ID], "19")
        # a query answer on the submit path starts a new correlation (NHCX-1011
        # refuses response.complete there)
        self.assertEqual(hdr[H.STATUS], "request.initiated")
        preauth.refresh_from_db()
        self.assertEqual(preauth.submission_kind, "preauth_query_response")
        claim.refresh_from_db()
        self.assertEqual(claim.sub_stage, "answered")

        # C5 approved
        self.reply(
            "v1/preauth/on_submit",
            self.ours("preauth-approved-wf21.json", claim),
            preauth.correlation_id,
        )
        preauth.refresh_from_db()
        self.assertEqual(preauth.status, "approved", preauth.error_message)

        # A5 -> C6 -> C10 -> A8 (workflow 15 and 17)
        self.post(
            f"claims/{claim_id}/discharge/",
            {
                "discharge_mode": "normal",
                "discharge_stage": "After Surgery",
                "discharge_date": "2026-01-06",
            },
        )
        self.post(f"claims/{claim_id}/claim/submit/")
        hdr, _ = self.sent("claim/submit")
        self.assertEqual(hdr[H.WORKFLOW_ID], "15")
        submission = ClaimSubmission.objects.get(claim=claim)
        self.reply(
            "v1/claim/on_submit",
            self.ours("claim-approved-deduction-wf26-pmjay.json", claim),
            submission.correlation_id,
        )
        submission.refresh_from_db()
        self.assertIn(submission.status, {"approved", "partial"})
        with self.captureOnCommitCallbacks(execute=True):
            self.reply(
                "v1/paymentnotice/request",
                self.ours("payment-notice-tds-wf30-pmjay.json", claim),
                submission.correlation_id,
                status="request.initiated",
            )
        money = ClaimPayment.objects.get(claim=claim)
        hdr, _ = self.sent("paymentnotice/on_request")
        self.assertEqual(hdr[H.WORKFLOW_ID], "17")
        money.refresh_from_db()
        self.assertEqual(money.ack_status, "sent")
        claim.refresh_from_db()
        self.assertEqual(claim.stage, "payment")
