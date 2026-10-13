import shutil
from pathlib import Path
from unittest import mock

from django.test import override_settings

from care.nhcx.callbacks import dispatch
from care.nhcx.models import ClaimAuth, ClaimPlan
from care.nhcx.services import eligibility, plan
from care.nhcx.tests.core_helpers import NhcxCoreTestBase, bundle

PROTOCOL_ERROR = {
    "type": "ProtocolResponse",
    "x-hcx-status": "response.error",
    "x-hcx-error_details": {"code": "ERR_INVALID_SIGNATURE", "message": "Bad JWS"},
}


def delivery(type_, **kw):
    d = {
        "path": f"/v1/{type_}/on_x",
        "type": type_,
        "flow": "callback",
        "payload_kind": "jwe",
        "redelivery": False,
        "participant": "1000001234@hcx",
    }
    d.update(kw)
    return d


class DispatchTests(NhcxCoreTestBase):
    def checking_claim(self):
        claim = self.make_claim()
        eligibility.run_check(claim, "validation", "POL-1", "PMJAY123")
        claim.refresh_from_db()
        return claim

    def test_c2_applies_verdict(self):
        claim = self.checking_claim()
        env = self.envelope(
            bundle("eligibility-response-generic.json"), claim.correlation_id
        )
        out = dispatch.receive(env, delivery("coverage"))
        self.assertEqual(out["outcome"], dispatch.SETTLED)
        claim.refresh_from_db()
        self.assertEqual(claim.status, "eligible")
        self.assertTrue(claim.inforce)
        self.assertEqual(claim.abha_number, "91-1234-1234-1234")
        self.assertEqual(claim.plan_period_end, "2026-12-31")
        self.assertEqual((claim.stage, claim.sub_stage), ("eligibility", "eligible"))
        self.assertIsNotNone(claim.response_json)

    def test_redelivery_is_idempotent(self):
        claim = self.checking_claim()
        env = self.envelope(
            bundle("eligibility-response-generic.json"), claim.correlation_id
        )
        dispatch.receive(env, delivery("coverage"))
        claim.refresh_from_db()
        claim.disposition = "kept"
        claim.save()
        again = dispatch.receive(env, delivery("coverage", redelivery=True))
        self.assertEqual(again["outcome"], dispatch.IGNORED)
        claim.refresh_from_db()
        self.assertEqual(claim.disposition, "kept")

    def test_reply_reopens_failed_send(self):
        claim = self.checking_claim()
        claim.status, claim.error_message = "error", "timed out"
        claim.save()
        env = self.envelope(
            bundle("eligibility-response-generic.json"), claim.correlation_id
        )
        self.assertEqual(
            dispatch.receive(env, delivery("coverage"))["outcome"], dispatch.SETTLED
        )
        claim.refresh_from_db()
        self.assertEqual(claim.status, "eligible")
        self.assertIsNone(claim.error_message)

    def test_protocol_response_is_a_refusal(self):
        claim = self.checking_claim()
        body = dict(PROTOCOL_ERROR, **{"x-hcx-correlation_id": claim.correlation_id})
        out = dispatch.receive(
            self.envelope(body, claim.correlation_id), delivery("coverage")
        )
        self.assertEqual(out["outcome"], dispatch.SETTLED)
        claim.refresh_from_db()
        self.assertEqual(claim.status, "error")
        self.assertEqual(claim.error_message, "ERR_INVALID_SIGNATURE: Bad JWS")

    def test_reply_without_response_is_rejected(self):
        claim = self.checking_claim()
        body = {"resourceType": "Bundle", "type": "collection", "entry": []}
        out = dispatch.receive(
            self.envelope(body, claim.correlation_id), delivery("coverage")
        )
        self.assertEqual(out["outcome"], dispatch.REJECTED)
        self.assertIn("CoverageEligibilityResponse", out["detail"])
        claim.refresh_from_db()
        self.assertEqual(claim.status, "checking")

    def test_unmatched_and_ignored(self):
        env = self.envelope(bundle("eligibility-response-generic.json"), "nobody")
        self.assertEqual(
            dispatch.receive(env, delivery("coverage"))["outcome"], dispatch.UNMATCHED
        )
        self.assertEqual(
            dispatch.receive(env, delivery("insurance"))["outcome"],
            dispatch.UNMATCHED,
        )
        self.assertEqual(
            dispatch.receive(env, delivery("hcx_audit"))["outcome"], dispatch.IGNORED
        )
        self.assertEqual(
            dispatch.receive(env, delivery("coverage", payload_kind="json"))["outcome"],
            dispatch.IGNORED,
        )
        no_corr = self.envelope({}, "")
        self.assertEqual(
            dispatch.receive(no_corr, delivery("coverage"))["outcome"],
            dispatch.UNMATCHED,
        )
        self.assertEqual(
            dispatch.receive("junk", delivery("coverage"))["outcome"],
            dispatch.REJECTED,
        )

    def test_missing_handler_is_unmatched(self):
        claim = self.checking_claim()
        env = self.envelope({}, claim.correlation_id)
        with mock.patch.object(dispatch, "_handler", return_value=None):
            out = dispatch.receive(env, delivery("claim"))
        self.assertEqual(out["outcome"], dispatch.UNMATCHED)

    def test_routing_table(self):
        seen = []

        def fake(name):
            return lambda env, d: seen.append((name, d.get("route"))) or {
                "outcome": "settled"
            }

        with mock.patch.object(dispatch, "_handler", side_effect=fake):
            for type_ in (
                "coverage",
                "insurance",
                "preauth",
                "claim",
                "task",
                "communication",
                "payment",
            ):
                dispatch.route(type_, {}, "c-1")
        self.assertEqual(
            seen,
            [
                ("eligibility", None),
                ("plan", None),
                ("preauth", None),
                ("claim", None),
                ("enquiry", "C7"),
                ("communication", None),
                ("payment", None),
            ],
        )

    def test_handler_error_is_error(self):
        def broken(env, d):
            msg = "boom"
            raise RuntimeError(msg)

        with mock.patch.object(dispatch, "_handler", return_value=broken):
            out = dispatch.receive(self.envelope({}, "c"), delivery("coverage"))
        self.assertEqual(out, {"outcome": dispatch.ERROR, "detail": "boom"})

    def test_matching(self):
        claim = self.checking_claim()
        self.assertEqual(dispatch.claim_for_correlation(claim.correlation_id), claim)
        env = {
            "fhir": {
                "entry": [
                    {"resource": {"request": {"reference": f"Claim/{claim.claim_no}"}}}
                ]
            }
        }
        self.assertEqual(dispatch.claim_named_in(env), claim)

    def test_archive_writes_inbound(self):
        scratch = Path(__file__).parent / "_scratch_archive"
        self.addCleanup(shutil.rmtree, scratch, ignore_errors=True)
        claim = self.checking_claim()
        env = self.envelope(
            bundle("eligibility-response-generic.json"), claim.correlation_id
        )
        with override_settings(NHCX_ARCHIVE_DIR=str(scratch)):
            dispatch.receive(env, delivery("coverage"))
        files = [p.name for p in scratch.rglob("*.json")]
        self.assertTrue(any(name.endswith("-in.json") for name in files), files)
        self.assertTrue(list(scratch.rglob("transactions.txt")))


class AuthRulingTests(NhcxCoreTestBase):
    def test_c3_applies_ruling(self):
        claim = self.make_claim(status="eligible")
        claim.lines.create(kind="Procedure", code="MG0111A")
        eligibility.request_auth(claim)
        ruling = ClaimAuth.objects.get(claim=claim)
        env = self.envelope(
            bundle("eligibility-auth-response-pmjay.json"), ruling.correlation_id
        )
        out = dispatch.receive(env, delivery("coverage"))
        self.assertEqual(out["outcome"], dispatch.SETTLED)
        ruling.refresh_from_db()
        self.assertEqual(ruling.status, "ready")
        self.assertEqual(ruling.items.count(), 2)
        self.assertEqual(ruling.requirements.count(), 12)
        self.assertIsNotNone(ruling.settled_at)
        again = dispatch.receive(env, delivery("coverage", redelivery=True))
        self.assertEqual(again["outcome"], dispatch.IGNORED)
        self.assertEqual(ruling.items.count(), 2)


class PlanCallbackTests(NhcxCoreTestBase):
    def fetching(self):
        claim = self.make_claim()
        plan.request_plan(claim)
        return claim, ClaimPlan.objects.get(claim=claim)

    def test_c4_applies_plan(self):
        _claim, row = self.fetching()
        env = self.envelope(bundle("plan-response-pmjay.json"), row.correlation_id)
        out = dispatch.receive(env, delivery("insurance"))
        self.assertEqual(out["outcome"], dispatch.SETTLED)
        row.refresh_from_db()
        self.assertEqual(row.status, "ready")
        self.assertEqual(row.plan_title, "PMJAY - Universal Health Policy")
        self.assertEqual(
            list(row.benefits.order_by("seq").values_list("seq", flat=True)),
            [1, 2, 3, 4],
        )
        first = row.benefits.get(seq=1)
        self.assertEqual(first.code, "MG004A")
        self.assertEqual(first.extras[0]["type"], "Stratification")
        self.assertEqual(row.forms.count(), 2)
        self.assertEqual(
            dispatch.receive(env, delivery("insurance"))["outcome"], dispatch.IGNORED
        )

    def test_c4_refusal(self):
        _claim, row = self.fetching()
        out = dispatch.receive(
            self.envelope(dict(PROTOCOL_ERROR), row.correlation_id),
            delivery("insurance"),
        )
        self.assertEqual(out["outcome"], dispatch.SETTLED)
        row.refresh_from_db()
        self.assertEqual(
            (row.status, row.error_message),
            ("error", "ERR_INVALID_SIGNATURE: Bad JWS"),
        )
