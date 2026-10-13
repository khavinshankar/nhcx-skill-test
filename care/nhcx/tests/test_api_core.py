from care.nhcx.callbacks import dispatch
from care.nhcx.models import Claim, ClaimPlan
from care.nhcx.tests.core_helpers import PAYER_CODE, NhcxCoreTestBase, bundle

POLICY = {
    "memberid": "PMJAY123",
    "name": "Ravi Kumar",
    "payerid": PAYER_CODE,
    "policyno": "POL-1",
}


class ApiAuthTests(NhcxCoreTestBase):
    def url(self, suffix=""):
        return f"/api/v1/facility/{self.facility.external_id}/nhcx/{suffix}"

    def test_anonymous_is_refused(self):
        # CARE's authenticators send no WWW-Authenticate header, so DRF answers
        # NotAuthenticated with 403 rather than 401 across the platform.
        got = self.client.get(self.url("claims/"))
        self.assertIn(got.status_code, (401, 403))
        self.assertEqual(got.data["detail"].code, "not_authenticated")

    def test_outsider_is_403(self):
        self.client.force_authenticate(self.create_user(username="outsider"))
        self.assertEqual(self.client.get(self.url("claims/")).status_code, 403)
        self.assertEqual(
            self.client.post(self.url("policy-search/"), {}, format="json").status_code,
            403,
        )

    def test_unknown_facility_is_404(self):
        self.client.force_authenticate(self.user)
        url = "/api/v1/facility/00000000-0000-0000-0000-000000000000/nhcx/claims/"
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_ledger_is_superuser_only(self):
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.get(self.url("ledger/")).status_code, 403)


class ApiFlowTests(NhcxCoreTestBase):
    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.user)

    def url(self, suffix=""):
        return f"/api/v1/facility/{self.facility.external_id}/nhcx/{suffix}"

    def post(self, suffix, data=None):
        return self.client.post(self.url(suffix), data or {}, format="json")

    def test_happy_path(self):
        self.gw.policies_answer = {"status": 200, "body": [POLICY]}
        found = self.post("policy-search/", {"member_id": "PMJAY123"})
        self.assertEqual(found.status_code, 200, found.data)
        self.assertEqual(found.data["policies"][0]["member_id"], "PMJAY123")
        self.assertEqual(found.data["identifiertype"], "MemberId")

        opened = self.post(
            "claims/",
            {
                "policy": found.data["policies"][0]["raw"],
                "identifiertype": "MemberId",
                "identifiervalue": "PMJAY123",
            },
        )
        self.assertEqual(opened.status_code, 200, opened.data)
        claim_id = opened.data["claim_id"]
        claim = Claim.objects.get(external_id=claim_id)
        self.assertEqual(opened.data["message"], f"Claim {claim.claim_no} opened.")

        listed = self.client.get(self.url("claims/"), {"search": "Ravi"})
        self.assertEqual(listed.data["count"], 1)
        self.assertEqual(listed.data["results"][0]["id"], claim_id)

        checked = self.post(
            f"claims/{claim_id}/eligibility/", {"purpose": "validation"}
        )
        self.assertEqual(checked.status_code, 200, checked.data)
        self.assertEqual(
            checked.data["message"], "Eligibility request queued to the payer."
        )
        claim.refresh_from_db()
        self.assertEqual(claim.status, "checking")
        dispatch.receive(
            self.envelope(
                bundle("eligibility-response-generic.json"), claim.correlation_id
            ),
            {"type": "coverage", "payload_kind": "jwe"},
        )

        asked = self.post(f"claims/{claim_id}/plan/")
        self.assertEqual(asked.status_code, 200, asked.data)
        self.assertEqual(
            asked.data["message"], "Insurance plan requested from the payer."
        )
        plan = ClaimPlan.objects.get(claim=claim)
        dispatch.receive(
            self.envelope(bundle("plan-response-pmjay.json"), plan.correlation_id),
            {"type": "insurance", "payload_kind": "jwe"},
        )

        added = self.post(
            f"claims/{claim_id}/lines/", {"kind": "Procedure", "code": "ST009B"}
        )
        self.assertEqual(added.status_code, 200, added.data)
        self.assertEqual(added.data["line"]["code"], "ST009B")
        line_id = added.data["line"]["id"]

        state = self.client.get(self.url(f"claims/{claim_id}/state/"))
        self.assertEqual(state.status_code, 200)
        self.assertEqual(state.data["claim"]["status"], "eligible")
        self.assertEqual(state.data["plan"]["status"], "ready")
        self.assertNotIn("response_json", state.data["plan"])
        self.assertEqual([x["code"] for x in state.data["lines"]], ["ST009B"])
        listed = state.data["benefits"][0]
        self.assertEqual(listed["extras"][0]["code"], "STRAT006a")
        self.assertNotIn("conditions", listed)
        detail = self.client.get(
            self.url(f"claims/{claim_id}/plan/benefits/{listed['id']}/")
        )
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.data["conditions"]["ProcedureType"], "Conservative")
        self.assertEqual(detail.data["supporting_info"][0]["code"], "MAND0409")

        removed = self.client.delete(self.url(f"claims/{claim_id}/lines/{line_id}/"))
        self.assertEqual(removed.data["message"], "Line removed.")

    def test_refusal_is_400(self):
        claim = self.make_claim()
        bad = self.post(
            f"claims/{claim.external_id}/eligibility/", {"purpose": "bogus"}
        )
        self.assertEqual(bad.status_code, 400)
        self.assertFalse(bad.data["ok"])
        self.assertTrue(bad.data["error"])
        nothing = self.post("claims/", {})
        self.assertEqual(
            nothing.data,
            {"ok": False, "error": "Choose a policy to open the claim with."},
        )

    def test_open_claim_with_ui_payload(self):
        self.gw.policies_answer = {"status": 200, "body": [POLICY]}
        found = self.post("policy-search/", {"member_id": "PMJAY123"})
        chosen = found.data["policies"][0]
        bad = self.post(
            "claims/",
            {"policy": chosen, "id_type": "MemberId", "patient": "undefined"},
        )
        self.assertEqual(bad.status_code, 400)
        self.assertEqual(
            bad.data["error"], "Patient id 'undefined' is not a valid UUID."
        )
        self.assertFalse(Claim.objects.exists())

        opened = self.post(
            "claims/",
            {"policy": chosen, "id_type": "MemberId", "id_value": "PMJAY123"},
        )
        self.assertEqual(opened.status_code, 200, opened.data)
        claim = Claim.objects.get(external_id=opened.data["claim_id"])
        self.assertEqual(claim.search_id_type, "MemberId")
        self.assertEqual(claim.search_id_value, "PMJAY123")

    def test_unknown_claim_is_404(self):
        missing = "00000000-0000-0000-0000-000000000000"
        got = self.client.get(self.url(f"claims/{missing}/state/"))
        self.assertEqual(got.status_code, 404)
        self.assertEqual(got.data, {"error": "No such claim"})

    def test_other_facility_claim_is_404(self):
        other = self.create_facility(user=self.user)
        claim = self.make_claim(facility=other)
        got = self.client.get(self.url(f"claims/{claim.external_id}/state/"))
        self.assertEqual(got.status_code, 404)
