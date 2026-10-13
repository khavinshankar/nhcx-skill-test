import json
from datetime import date, datetime

from django.test import SimpleTestCase

from care.nhcx.fhir import bundle as fb
from care.nhcx.fhir.codes import PROFILES


class BundleTests(SimpleTestCase):
    def test_kinds_have_ids_profiles_and_anchors(self):
        expected = {
            "coverage-validation": "coverage-validation-request-generic",
            "coverage-auth-requirements": "coverage-authrequirements-request-generic",
            "insurance-plan": "insurance-request-generic",
            "preauth": "preauth-request-generic",
            "enhancement": "preauth-enhancement-request-generic",
            "claim": "claim-request-generic",
            "preauth-cancel": "preauth-cancel-request-generic",
            "claim-reprocess": "claim-reprocess-request-generic",
            "payment-ack": "payment-notice-ack-generic",
        }
        for kind, bundle_id in expected.items():
            with self.subTest(kind=kind):
                self.assertEqual(fb.KINDS[kind][0], bundle_id)
                self.assertIn(fb.KINDS[kind][1], PROFILES)
        self.assertEqual(
            fb.anchor_url("preauth"), "https://nhcx.abdm.gov.in/preauth/request"
        )

    def test_wrap_puts_anchor_first_with_absolute_urls(self):
        out = fb.wrap(
            "claim",
            [
                ("ignored", {"resourceType": "Claim"}),
                ("/patient", {"resourceType": "Patient"}),
            ],
        )
        self.assertEqual(out["resourceType"], "Bundle")
        self.assertEqual(out["type"], "collection")
        self.assertEqual(out["id"], "claim-request-generic")
        self.assertEqual(out["meta"]["profile"], [PROFILES["ClaimBundle"]])
        self.assertEqual(
            [e["fullUrl"] for e in out["entry"]],
            [
                "https://nhcx.abdm.gov.in/claim/request",
                "https://nhcx.abdm.gov.in/patient",
            ],
        )
        self.assertEqual(
            fb.ref("payer", "Payer"),
            {
                "reference": "https://nhcx.abdm.gov.in/payer",
                "display": "Payer",
            },
        )

    def test_unwrap_and_find(self):
        bundle = {
            "resourceType": "Bundle",
            "entry": [
                {
                    "fullUrl": "urn:uuid:a",
                    "resource": {"resourceType": "Task", "id": "a"},
                },
                {
                    "fullUrl": "https://x/ClaimResponse/b",
                    "resource": {"resourceType": "ClaimResponse", "id": "b"},
                },
                {"resource": {"resourceType": "ClaimResponse", "id": "c"}},
            ],
        }
        self.assertEqual(fb.unwrap(json.dumps(bundle)), bundle)
        self.assertEqual(fb.find_resource(bundle, "ClaimResponse")["id"], "b")
        self.assertEqual(
            fb.find_resource(bundle, "ClaimResponse", last=True)["id"], "c"
        )
        self.assertIsNone(fb.find_resource(bundle, "Claim"))
        self.assertEqual(
            fb.resolve_reference(bundle, "https://x/ClaimResponse/b")["id"], "b"
        )
        self.assertEqual(fb.resolve_reference(bundle, "urn:uuid:c")["id"], "c")
        self.assertEqual(fb.resolve_reference(bundle, "ClaimResponse/c")["id"], "c")

    def test_protocol_response(self):
        payload = {
            "type": "ProtocolResponse",
            "x-hcx-error_details": {"code": "ERR-1", "message": "Bad"},
        }
        self.assertTrue(fb.is_protocol_response(payload))
        self.assertEqual(fb.protocol_error(payload), "ERR-1: Bad")
        self.assertFalse(fb.is_protocol_response({"resourceType": "Bundle"}))

    def test_values(self):
        self.assertEqual(fb.to_instant(date(2026, 9, 9)), "2026-09-09T00:00:00+05:30")
        self.assertEqual(fb.to_instant("2026-09-09"), "2026-09-09T00:00:00+05:30")
        self.assertEqual(
            fb.to_instant(datetime(2026, 9, 9, 4, 30, tzinfo=fb.UTC)),
            "2026-09-09T10:00:00+05:30",
        )
        self.assertEqual(fb.to_date("2026-09-09T23:00:00+05:30"), "2026-09-09")
        self.assertEqual(fb.amount("1500.00"), 1500)
        self.assertEqual(fb.amount(12.345), 12.35)
        self.assertIsNone(fb.amount(None))
        self.assertEqual(fb.money(10), {"value": 10, "currency": "INR"})
        self.assertEqual(fb.b64(b"ab"), "YWI=")
