"""Leg and global NHCX routes: access, refusals, and the A19 steps (HTTP mocked)."""

from unittest import mock

from django.test import override_settings

from care.nhcx.models import ClaimPreauth
from care.nhcx.models.abha import get_abha_number
from care.nhcx.services import abha, draft, preauth
from care.nhcx.tests.core_helpers import NhcxCoreTestBase
from care.nhcx.tests.test_services_legs import FakeAbha


class LegApiTests(NhcxCoreTestBase):
    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.user)
        self.claim = self.make_claim(status="eligible")

    def url(self, suffix=""):
        return f"/api/v1/facility/{self.facility.external_id}/nhcx/{suffix}"

    def claim_url(self, suffix):
        return self.url(f"claims/{self.claim.external_id}/{suffix}")

    def test_outsider_is_403(self):
        self.client.force_authenticate(self.create_user(username="legs-outsider"))
        got = self.client.put(self.claim_url("draft/"), {}, format="json")
        self.assertEqual(got.status_code, 403)
        got = self.client.post(self.claim_url("preauth/submit/"), {}, format="json")
        self.assertEqual(got.status_code, 403)

    def grant_facility_update(self, user):
        from care.security.permissions.facility import FacilityPermissions

        org = self.create_facility_organization(facility=self.facility, org_type="root")
        role = self.create_role_with_permissions(
            [FacilityPermissions.can_update_facility.name]
        )
        self.attach_role_facility_organization_user(org, user, role)

    def test_facility_profile(self):
        got = self.client.get(self.url("profile/"))
        self.assertEqual(got.status_code, 200, got.data)
        self.assertEqual(got.data["profile"]["hfr_id"], "IN3410000001")
        self.assertEqual(got.data["effective_hfr_id"], "IN3410000001")
        self.assertEqual(got.data["hfr_id_source"], "profile")
        self.grant_facility_update(self.user)
        put = self.client.put(
            self.url("profile/"), {"email": "desk@example.org"}, format="json"
        )
        self.assertEqual(put.status_code, 200, put.data)
        self.assertTrue(put.data["can_edit"])
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.email, "desk@example.org")

    def test_facility_profile_put_needs_update_permission(self):
        got = self.client.get(self.url("profile/"))
        self.assertEqual(got.status_code, 200, got.data)
        self.assertFalse(got.data["can_edit"])
        put = self.client.put(
            self.url("profile/"), {"email": "desk@example.org"}, format="json"
        )
        self.assertEqual(put.status_code, 403)
        self.profile.refresh_from_db()
        self.assertIsNone(self.profile.email)

    def test_facility_profile_reports_abdm_hip_id(self):
        self.profile.hfr_id = None
        self.profile.save()
        with mock.patch(
            "care.nhcx.api.views_legs.abdm_hf_id", return_value="IN3410000099"
        ):
            got = self.client.get(self.url("profile/"))
        self.assertEqual(got.status_code, 200, got.data)
        self.assertEqual(got.data["profile"]["hfr_id"], "")
        self.assertEqual(got.data["abdm_hf_id"], "IN3410000099")
        self.assertEqual(got.data["effective_hfr_id"], "IN3410000099")
        self.assertEqual(got.data["hfr_id_source"], "abdm")

    def test_draft_and_refusal(self):
        got = self.client.put(
            self.claim_url("draft/"),
            {"care_team": [{"role": "treating", "practitioner": self.user.id}]},
            format="json",
        )
        self.assertEqual(got.status_code, 200, got.data)
        self.assertEqual(got.data["message"], draft.DRAFT_SAVED)
        bad = self.client.put(
            self.claim_url("draft/"), {"care_team": [{"role": "cook"}]}, format="json"
        )
        self.assertEqual(bad.status_code, 400)
        self.assertEqual(bad.data, {"ok": False, "error": draft.BAD_ROLE})

    def test_submit_refused_until_eligible(self):
        self.claim.status = "draft"
        self.claim.save()
        got = self.client.post(self.claim_url("preauth/submit/"), {}, format="json")
        self.assertEqual(got.status_code, 400)
        self.assertEqual(got.data["error"], preauth.NOT_ELIGIBLE)
        self.assertEqual(self.gw.sent, [])

    def test_cancel_route(self):
        ClaimPreauth.objects.create(
            claim=self.claim,
            status="submitting",
            correlation_id="corr-pa",
            claim_ref=self.claim.claim_no,
        )
        got = self.client.post(
            self.claim_url("preauth/cancel/"), {"reason": "x"}, format="json"
        )
        self.assertEqual(got.status_code, 400)
        self.assertEqual(got.data["error"], preauth.NO_CANCEL_REASON)

    def test_adjudicate_hidden_unless_enabled(self):
        got = self.client.post(self.claim_url("adjudicate/"), {}, format="json")
        self.assertEqual(got.status_code, 404)
        with override_settings(NHCX_ADJUDICATOR_CONSOLE=True):
            got = self.client.post(self.claim_url("adjudicate/"), {}, format="json")
        self.assertNotEqual(got.status_code, 404)


class GlobalApiTests(NhcxCoreTestBase):
    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.user)
        self.gw.token = lambda *a, **k: {"token": "sess"}
        self.gw.refresh_token = mock.Mock(return_value={"token": "sess2"})
        patcher = mock.patch.object(abha.requests, "request", FakeAbha())
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_needs_login(self):
        self.client.force_authenticate(None)
        got = self.client.get("/api/v1/nhcx/practitioner/me/")
        self.assertIn(got.status_code, (401, 403))

    def test_practitioner_profile(self):
        got = self.client.get("/api/v1/nhcx/practitioner/me/")
        self.assertEqual(got.status_code, 200, got.data)
        put = self.client.put(
            "/api/v1/nhcx/practitioner/me/",
            {"hpr_id": "71-1234-5678-9012"},
            format="json",
        )
        self.assertEqual(put.status_code, 200, put.data)
        again = self.client.get("/api/v1/nhcx/practitioner/me/")
        self.assertEqual(again.data["profile"]["hpr_id"], "71-1234-5678-9012")
        other = self.create_user()
        denied = self.client.put(
            f"/api/v1/nhcx/practitioner/{other.external_id}/", {}, format="json"
        )
        self.assertEqual(denied.status_code, 403)

    def test_abha_steps(self):
        cert = self.client.get("/api/v1/nhcx/abha/certificate/")
        self.assertEqual(cert.status_code, 200, cert.data)
        self.assertTrue(cert.data["public_key"])
        bad = self.client.post(
            "/api/v1/nhcx/abha/aadhaar-otp/", {"aadhaar": "12"}, format="json"
        )
        self.assertEqual(bad.status_code, 400)
        self.assertEqual(bad.data["error"], abha.AADHAAR_12)
        sent = self.client.post(
            "/api/v1/nhcx/abha/aadhaar-otp/",
            {"aadhaar": "123456789012"},
            format="json",
        )
        self.assertEqual(sent.status_code, 200, sent.data)
        txn = sent.data["txn_id"]
        made = self.client.post(
            "/api/v1/nhcx/abha/aadhaar-verify/",
            {"txn_id": txn, "otp": "123456"},
            format="json",
        )
        self.assertEqual(made.status_code, 200, made.data)
        self.assertNotIn("token", str(made.data))
        self.user.is_superuser = True
        self.user.save()
        patient = self.create_patient()
        linked = self.client.post(
            "/api/v1/nhcx/abha/link/",
            {"txn_id": txn, "patient": str(patient.external_id)},
            format="json",
        )
        self.assertEqual(linked.status_code, 200, linked.data)
        self.assertEqual(get_abha_number(patient), "91-1234-5678-9012")
