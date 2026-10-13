"""Leg services (A4 to A8, A14 to A19) with the gateway and HTTP mocked."""

import base64
from types import SimpleNamespace
from unittest import mock

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from django.test import override_settings

from care.nhcx.models import ClaimEnquiry, ClaimPreauth, ClaimSubmission
from care.nhcx.models.abha import get_abha_number
from care.nhcx.services import abha, adjudicator, biometric, draft, preauth
from care.nhcx.services import claim as claim_service
from care.nhcx.services.common import ServiceRefusal
from care.nhcx.tests.core_helpers import NhcxCoreTestBase


def refused(result_path="v1/x"):
    return SimpleNamespace(
        ok=False,
        path=result_path,
        headers={"x-hcx-correlation_id": "corr-bad"},
        response={"error": {"code": "ERR_X", "message": "Nope"}},
        ledger_id="txn-bad",
        txn_id="txn-bad",
        correlation_id="corr-bad",
        api_call_id="api-bad",
        request_id=None,
        error_code="ERR_X",
        error_message="Nope",
    )


class PreauthServiceTests(NhcxCoreTestBase):
    def test_submit_refused_until_eligible(self):
        claim = self.make_claim()
        with self.assertRaisesMessage(ServiceRefusal, preauth.NOT_ELIGIBLE):
            preauth.submit_preauth(claim)
        self.assertEqual(self.gw.sent, [])

    def test_cancel_refusals(self):
        claim = self.make_claim(status="eligible")
        with self.assertRaisesMessage(ServiceRefusal, preauth.NOTHING_TO_CANCEL):
            preauth.cancel_preauth(claim, "other", "x")
        ClaimPreauth.objects.create(
            claim=claim, status="submitting", correlation_id="corr-pa"
        )
        with self.assertRaisesMessage(ServiceRefusal, preauth.NO_CANCEL_REASON):
            preauth.cancel_preauth(claim, "made-up")
        self.assertEqual(self.gw.sent, [])

    def test_cancel_sends_task(self):
        claim = self.make_claim(status="eligible")
        row = ClaimPreauth.objects.create(
            claim=claim,
            status="submitting",
            correlation_id="corr-pa",
            claim_ref=claim.claim_no,
        )
        from care.nhcx.models.legs import CancelReason

        reason = next(v for v in CancelReason.values if v != "other")
        preauth.cancel_preauth(claim, reason)
        row.refresh_from_db()
        self.assertEqual(row.status, "cancelling")
        self.assertEqual(row.pre_cancel_status, "submitting")
        self.assertTrue(row.cancel_correlation_id)
        self.assertEqual(len(self.gw.sent), 1)
        self.assertIn("task", self.gw.sent[0][0])

    def test_status_send_failure_keeps_ids(self):
        claim = self.make_claim(status="eligible")
        ClaimPreauth.objects.create(
            claim=claim,
            status="submitting",
            correlation_id="corr-pa",
            claim_ref=claim.claim_no,
        )
        self.gw.results = [refused()]
        with self.assertRaisesMessage(ServiceRefusal, "ERR_X"):
            preauth.ask_status(claim, "preauth")
        ask = ClaimEnquiry.objects.get(claim=claim)
        self.assertEqual(ask.status, "error")
        self.assertEqual(ask.txn_id, "txn-bad")
        self.assertIn("ERR_X", ask.error_message)

    def test_status_bad_stage(self):
        claim = self.make_claim(status="eligible")
        with self.assertRaisesMessage(ServiceRefusal, preauth.BAD_STAGE):
            preauth.ask_status(claim, "payment")


class ClaimServiceTests(NhcxCoreTestBase):
    def test_claim_needs_discharge_and_preauth(self):
        claim = self.make_claim(status="eligible")
        with self.assertRaises(ServiceRefusal):
            claim_service.submit_claim(claim)
        self.assertEqual(self.gw.sent, [])

    def test_reprocess_refused_before_decision(self):
        claim = self.make_claim(status="eligible")
        ClaimSubmission.objects.create(
            claim=claim, status="submitting", correlation_id="corr-cl"
        )
        with self.assertRaisesMessage(ServiceRefusal, claim_service.NOT_DECIDED):
            claim_service.ask_reprocess(claim, "Look again", "other")

    def test_discharge_mode_required(self):
        claim = self.make_claim(status="eligible")
        with self.assertRaisesMessage(ServiceRefusal, claim_service.NO_MODE):
            claim_service.record_discharge(claim, {})


class DraftServiceTests(NhcxCoreTestBase):
    def test_save_and_refusals(self):
        claim = self.make_claim(status="eligible")
        message = draft.save_draft(
            claim,
            {
                "admission_date": "2026-10-01",
                "diagnoses": [{"icd10_code": "K35.8", "icd10_display": "Appendicitis"}],
                "care_team": [{"role": "treating", "practitioner": self.user.id}],
            },
        )
        self.assertEqual(message, draft.DRAFT_SAVED)
        claim.refresh_from_db()
        self.assertEqual(str(claim.admission_date), "2026-10-01")
        self.assertEqual(claim.diagnoses.count(), 1)
        self.assertEqual(claim.care_team.count(), 1)
        with self.assertRaisesMessage(ServiceRefusal, draft.BAD_ROLE):
            draft.save_draft(claim, {"care_team": [{"role": "cook"}]})
        with self.assertRaisesMessage(ServiceRefusal, draft.NO_DOCTOR):
            draft.save_draft(claim, {"care_team": []})
        self.assertEqual(
            draft.save_draft(
                claim, {"answers": [{"form_url": "f", "link_id": "1", "answer": "y"}]}
            ),
            draft.ANSWERS_SAVED,
        )


class SmallServiceTests(NhcxCoreTestBase):
    def test_adjudicator_off_by_default(self):
        self.assertFalse(adjudicator.enabled())
        with override_settings(NHCX_ADJUDICATOR_CONSOLE=True):
            self.assertTrue(adjudicator.enabled())

    def test_biometric_needs_patient(self):
        claim = self.make_claim(status="eligible", patient=None)
        with self.assertRaisesMessage(ServiceRefusal, biometric.NO_PATIENT):
            biometric.init(claim, "FINGERPRINT")


def _public_key():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    der = key.public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return base64.b64encode(der).decode()


PUBLIC_KEY = _public_key()


class FakeAbha:
    """URL-routed stand-in for the ABHA service."""

    def __init__(self):
        self.calls = []
        self.unauthorised_once = False
        self.routes = {
            "/profile/public/certificate": {"publicKey": PUBLIC_KEY},
            "/enrollment/request/otp": {"txnId": "txn-e", "message": "OTP sent"},
            "/enrollment/enrol/byAadhaar": {
                "txnId": "txn-e",
                "isNew": True,
                "tokens": {"token": "x-e"},
                "ABHAProfile": {
                    "firstName": "Asha",
                    "lastName": "Rao",
                    "gender": "F",
                    "dob": "01-02-1990",
                    "ABHANumber": "91-1234-5678-9012",
                    "phrAddress": ["asha.rao@sbx"],
                },
            },
            "/enrollment/enrol/suggestion": {"abhaAddressList": ["asharao90"]},
            "/enrollment/enrol/abha-address": {
                "healthIdNumber": "91-1234-5678-9012",
                "preferredAbhaAddress": "asharao90@sbx",
            },
            "/profile/login/request/otp": {"txnId": "txn-l", "message": "sent"},
            "/profile/login/verify": {
                "authResult": "success",
                "token": "t-token",
                "accounts": [
                    {"ABHANumber": "xx-xxxx-xxxx-9012", "name": "Asha Rao"},
                    {"ABHANumber": "xx-xxxx-xxxx-1111", "name": "Other"},
                ],
            },
            "/profile/login/verify/user": {"token": "x-l"},
            "/profile/account": {
                "ABHANumber": "91-1234-5678-9012",
                "preferredAbhaAddress": "asharao90@sbx",
                "name": "Asha Rao",
                "gender": "F",
                "dob": "01-02-1990",
                "mobile": "9876543210",
            },
        }

    def __call__(self, method, url, headers=None, json=None, timeout=None):
        path = url.split("/abha/api/v3", 1)[-1]
        self.calls.append((method, path, headers, json))
        if self.unauthorised_once:
            self.unauthorised_once = False
            return mock.Mock(status_code=401, json=dict)
        body = self.routes[path]
        return mock.Mock(status_code=200, json=lambda: body)


class AbhaServiceTests(NhcxCoreTestBase):
    def setUp(self):
        super().setUp()
        self.gw.token = lambda *a, **k: {"token": "sess"}
        self.gw.refresh_token = mock.Mock(return_value={"token": "sess2"})
        self.http = FakeAbha()
        patcher = mock.patch.object(abha.requests, "request", self.http)
        patcher.start()
        self.addCleanup(patcher.stop)

    def paths(self):
        return [c[1] for c in self.http.calls]

    def test_create_via_aadhaar(self):
        sent = abha.enrol_otp(self.user, "1234 5678 9012")
        self.assertEqual(sent["txn_id"], "txn-e")
        otp_call = self.http.calls[-1]
        self.assertNotIn("123456789012", str(otp_call[3]))
        self.assertEqual(otp_call[2]["Authorization"], "Bearer sess")
        made = abha.enrol_verify(self.user, "txn-e", "123456", "9876543210")
        self.assertTrue(made["is_new"])
        self.assertEqual(made["profile"]["abha_no"], "91-1234-5678-9012")
        self.assertEqual(made["profile"]["dob"], "1990-02-01")
        self.assertEqual(
            abha.suggestions(self.user, "txn-e")["addresses"], ["asharao90"]
        )
        chosen = abha.enrol_address(self.user, "txn-e", "asharao90@sbx")
        self.assertEqual(chosen["abha_address"], "asharao90@sbx")
        patient = self.create_patient()
        abha.link(self.user, "txn-e", patient)
        self.assertEqual(get_abha_number(patient), "91-1234-5678-9012")
        with self.assertRaisesMessage(ServiceRefusal, abha.LAPSED):
            abha.link(self.user, "txn-e", patient)

    def test_verify_via_mobile(self):
        abha.login_otp(self.user, mobile="9876543210")
        found = abha.login_verify(self.user, "txn-l", "123456")
        self.assertEqual(len(found["accounts"]), 2)
        with self.assertRaisesMessage(ServiceRefusal, abha.CHOOSE_ACCOUNT):
            abha.login_select(self.user, "txn-l", "xx-xxxx-xxxx-0000")
        picked = abha.profile(self.user, "txn-l", "xx-xxxx-xxxx-9012")
        self.assertEqual(picked["profile"]["abha_no"], "91-1234-5678-9012")
        select_call = next(
            c for c in self.http.calls if c[1] == "/profile/login/verify/user"
        )
        self.assertEqual(select_call[2]["T-token"], "Bearer t-token")
        account_call = next(c for c in self.http.calls if c[1] == "/profile/account")
        self.assertEqual(account_call[2]["X-token"], "Bearer x-l")
        patient = self.create_patient()
        abha.link(self.user, "txn-l", patient)
        self.assertEqual(get_abha_number(patient), "91-1234-5678-9012")

    def test_refusals_and_retry(self):
        with self.assertRaisesMessage(ServiceRefusal, abha.AADHAAR_12):
            abha.enrol_otp(self.user, "1234")
        with self.assertRaisesMessage(ServiceRefusal, abha.LAPSED):
            abha.login_verify(self.user, "txn-unknown", "123456")
        with self.assertRaisesMessage(ServiceRefusal, abha.ABHA_OR_MOBILE):
            abha.login_otp(self.user)
        other = self.create_user()
        abha.login_otp(self.user, mobile="9876543210")
        with self.assertRaisesMessage(ServiceRefusal, abha.LAPSED):
            abha.login_verify(other, "txn-l", "123456")
        self.http.unauthorised_once = True
        self.assertEqual(abha.enrol_otp(self.user, "123456789012")["txn_id"], "txn-e")
        self.gw.refresh_token.assert_called_once()
        self.assertEqual(self.http.calls[-1][2]["Authorization"], "Bearer sess2")

    def test_service_error_is_refusal(self):
        self.http.routes["/enrollment/request/otp"] = None

        def failing(method, url, headers=None, json=None, timeout=None):
            if url.endswith("/enrollment/request/otp"):
                return mock.Mock(
                    status_code=400,
                    json=lambda: {"error": {"code": "ABDM-1204", "message": "Bad"}},
                )
            return FakeAbha()(method, url, headers, json, timeout)

        with (
            mock.patch.object(abha.requests, "request", failing),
            self.assertRaisesMessage(ServiceRefusal, "ABDM-1204: Bad"),
        ):
            abha.enrol_otp(self.user, "123456789012")
