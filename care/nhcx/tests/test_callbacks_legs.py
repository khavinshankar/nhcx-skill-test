"""C5 to C10 leg callbacks against the package's fixture bundles (no network)."""

from care.nhcx.callbacks import dispatch
from care.nhcx.models import (
    ClaimEnquiry,
    ClaimPayment,
    ClaimPreauth,
    ClaimQuery,
    ClaimSubmission,
)
from care.nhcx.tests.core_helpers import NhcxCoreTestBase, bundle

PROTOCOL_ERROR = {
    "type": "ProtocolResponse",
    "x-hcx-status": "response.error",
    "x-hcx-error_details": {"code": "ERR_INVALID_SIGNATURE", "message": "Bad JWS"},
}


def delivery(type_, corr="", **kw):
    d = {
        "path": f"/v1/{type_}/on_x",
        "type": type_,
        "flow": "callback",
        "payload_kind": "jwe",
        "redelivery": False,
        "participant": "1000001234@hcx",
        "correlation_id": corr,
    }
    d.update(kw)
    return d


class LegCallbackBase(NhcxCoreTestBase):
    def eligible_claim(self, **kw):
        return self.make_claim(status="eligible", **kw)

    def receive(self, name_or_body, corr, type_, api_call_id="reply-api-1", **headers):
        body = bundle(name_or_body) if isinstance(name_or_body, str) else name_or_body
        env = self.envelope(body, corr, api_call_id, **headers)
        return dispatch.receive(env, delivery(type_, corr))


class PreauthCallbackTests(LegCallbackBase):
    def setUp(self):
        super().setUp()
        self.claim = self.eligible_claim(claim_no="NM-26-0SE00002M")
        self.row = ClaimPreauth.objects.create(
            claim=self.claim,
            status="submitting",
            correlation_id="corr-pa",
            txn_id="txn-pa",
            submission_kind="preauth",
        )

    def test_c5_approved_then_redelivery(self):
        out = self.receive("preauth-approved-wf21.json", "corr-pa", "preauth")
        self.assertEqual(out["outcome"], dispatch.SETTLED, out)
        self.row.refresh_from_db()
        self.assertEqual(self.row.status, "approved")
        self.assertEqual(self.row.correlation_id, "corr-pa")
        self.assertIsNotNone(self.row.response_json)
        first = self.row.modified_date

        again = self.receive("preauth-approved-wf21.json", "corr-pa", "preauth")
        self.assertEqual(again["outcome"], dispatch.IGNORED, again)
        self.row.refresh_from_db()
        self.assertEqual(self.row.status, "approved")
        self.assertEqual(self.row.modified_date, first)

    def test_c5_queried(self):
        out = self.receive("preauth-queried-wf24.json", "corr-pa", "preauth")
        self.assertEqual(out["outcome"], dispatch.SETTLED, out)
        self.row.refresh_from_db()
        self.assertEqual(self.row.status, "queried")

    def test_c5_protocol_refusal_keeps_ids(self):
        out = self.receive(PROTOCOL_ERROR, "corr-pa", "preauth")
        self.assertEqual(out["outcome"], dispatch.SETTLED, out)
        self.row.refresh_from_db()
        self.assertEqual(self.row.status, "error")
        self.assertIn("ERR_INVALID_SIGNATURE", self.row.error_message)
        self.assertEqual(self.row.txn_id, "txn-pa")

    def test_c7_cancel_accepted(self):
        self.row.status = "cancelling"
        self.row.pre_cancel_status = "queued"
        self.row.cancel_correlation_id = "corr-cancel"
        self.row.save()
        out = self.receive(
            "task-cancelled-wfPC02.json", "corr-cancel", "task", route="C7"
        )
        self.assertEqual(out["outcome"], dispatch.SETTLED, out)
        self.row.refresh_from_db()
        self.assertEqual(self.row.status, "cancelled")
        again = self.receive("task-cancelled-wfPC02.json", "corr-cancel", "task")
        self.assertIn(again["outcome"], {dispatch.IGNORED, dispatch.SETTLED})
        self.row.refresh_from_db()
        self.assertEqual(self.row.status, "cancelled")

    def test_c7_cancel_refused_restores_status(self):
        self.row.status = "cancelling"
        self.row.pre_cancel_status = "queued"
        self.row.cancel_correlation_id = "corr-cancel"
        self.row.save()
        out = self.receive(PROTOCOL_ERROR, "corr-cancel", "task")
        self.assertEqual(out["outcome"], dispatch.SETTLED, out)
        self.row.refresh_from_db()
        self.assertEqual(self.row.status, "queued")
        self.assertIn("ERR_INVALID_SIGNATURE", self.row.error_message)


class ClaimCallbackTests(LegCallbackBase):
    def setUp(self):
        super().setUp()
        self.claim = self.eligible_claim(claim_no="NM-26-0SE00002L")
        ClaimPreauth.objects.create(
            claim=self.claim, status="approved", correlation_id="corr-pa"
        )
        self.row = ClaimSubmission.objects.create(
            claim=self.claim,
            status="submitting",
            correlation_id="corr-cl",
            txn_id="txn-cl",
        )

    def test_c6_approved_then_redelivery(self):
        out = self.receive(
            "claim-approved-deduction-wf26-pmjay.json", "corr-cl", "claim"
        )
        self.assertEqual(out["outcome"], dispatch.SETTLED, out)
        self.row.refresh_from_db()
        self.assertIn(self.row.status, {"approved", "partial"})
        status = self.row.status
        again = self.receive(
            "claim-approved-deduction-wf26-pmjay.json", "corr-cl", "claim"
        )
        self.assertEqual(again["outcome"], dispatch.IGNORED, again)
        self.row.refresh_from_db()
        self.assertEqual(self.row.status, status)

    def test_c6_rejected(self):
        out = self.receive("claim-rejected-wf291.json", "corr-cl", "claim")
        self.assertEqual(out["outcome"], dispatch.SETTLED, out)
        self.row.refresh_from_db()
        self.assertNotEqual(self.row.status, "submitting")

    def test_c8_reprocess_answer(self):
        self.row.status = "rejected"
        self.row.save()
        ask = ClaimEnquiry.objects.create(
            claim=self.claim,
            kind="reprocess",
            stage="claim",
            status="asking",
            correlation_id="corr-rp",
        )
        out = self.receive("task-reprocess-wf37.json", "corr-rp", "task", route="C8")
        self.assertEqual(out["outcome"], dispatch.SETTLED, out)
        ask.refresh_from_db()
        self.assertEqual(ask.status, "answered")
        answered_at = ask.answered_at
        again = self.receive("task-reprocess-wf37.json", "corr-rp", "task", route="C8")
        self.assertIn(again["outcome"], {dispatch.IGNORED, dispatch.SETTLED})
        ask.refresh_from_db()
        self.assertEqual(ask.answered_at, answered_at)

    def test_c8_reprocess_verdict_on_reprocess_thread(self):
        self.row.status = "rejected"
        self.row.save()
        ClaimEnquiry.objects.create(
            claim=self.claim,
            kind="reprocess",
            stage="claim",
            status="asking",
            correlation_id="corr-rp",
        )
        self.receive("task-reprocess-wf37.json", "corr-rp", "task", route="C8")
        self.row.refresh_from_db()
        self.assertEqual(self.row.status, "submitting")
        out = self.receive(
            "claim-approved-deduction-wf26-pmjay.json",
            "corr-rp",
            "task",
            api_call_id="reply-api-2",
            route="C8",
        )
        self.assertEqual(out["outcome"], dispatch.SETTLED, out)
        self.row.refresh_from_db()
        self.assertIn(self.row.status, {"approved", "partial"})

    def test_unmatched_claim_reply(self):
        out = self.receive("claim-rejected-wf291.json", "corr-unknown", "claim")
        self.assertEqual(out["outcome"], dispatch.UNMATCHED, out)


class CommunicationCallbackTests(LegCallbackBase):
    def setUp(self):
        super().setUp()
        self.claim = self.eligible_claim(claim_no="NM-26-0SE00002I")
        ClaimPreauth.objects.create(
            claim=self.claim,
            status="queued",
            correlation_id="corr-pa",
            claim_ref="NM-26-0SE00002I",
        )

    def test_c9_query_recorded_once(self):
        with self.captureOnCommitCallbacks(execute=True):
            out = self.receive(
                "communication-query-wf24.json", "corr-q", "communication"
            )
        self.assertEqual(out["outcome"], dispatch.SETTLED, out)
        self.assertEqual(ClaimQuery.objects.filter(claim=self.claim).count(), 1)
        self.assertEqual(self.gw.sent, [])
        with self.captureOnCommitCallbacks(execute=True):
            again = self.receive(
                "communication-query-wf24.json", "corr-q", "communication"
            )
        self.assertEqual(again["outcome"], dispatch.IGNORED, again)
        self.assertEqual(ClaimQuery.objects.filter(claim=self.claim).count(), 1)

    def test_c9_notification_acknowledged(self):
        with self.captureOnCommitCallbacks(execute=True):
            out = self.receive(
                "communication-notification-wfN02-pmjay.json",
                "corr-pa",
                "communication",
            )
        self.assertEqual(out["outcome"], dispatch.SETTLED, out)
        note = ClaimQuery.objects.get(claim=self.claim)
        self.assertEqual(len(self.gw.sent), 1)
        self.assertIn("communication", self.gw.sent[0][0])
        note.refresh_from_db()
        self.assertIsNotNone(note.acknowledged_at)


class PaymentCallbackTests(LegCallbackBase):
    def setUp(self):
        super().setUp()
        self.claim = self.eligible_claim(claim_no="NM-26-0SE00002L")
        ClaimSubmission.objects.create(
            claim=self.claim, status="approved", correlation_id="corr-cl"
        )

    def test_c10_recorded_acknowledged_and_redelivery(self):
        with self.captureOnCommitCallbacks(execute=True):
            out = self.receive("payment-notice-wf30.json", "corr-pay", "payment")
        self.assertEqual(out["outcome"], dispatch.SETTLED, out)
        money = ClaimPayment.objects.get(claim=self.claim)
        self.assertEqual(len(self.gw.sent), 1)
        self.assertIn("paymentnotice", self.gw.sent[0][0])
        money.refresh_from_db()
        self.assertEqual(money.ack_status, "sent")
        with self.captureOnCommitCallbacks(execute=True):
            again = self.receive("payment-notice-wf30.json", "corr-pay", "payment")
        self.assertEqual(again["outcome"], dispatch.IGNORED, again)
        self.assertEqual(ClaimPayment.objects.filter(claim=self.claim).count(), 1)
        self.assertEqual(len(self.gw.sent), 1)

    def test_c10_unmatched(self):
        self.claim.claim_no = "NM-OTHER"
        self.claim.save()
        ClaimSubmission.objects.filter(claim=self.claim).delete()
        out = self.receive("payment-notice-wf30.json", "corr-pay", "payment")
        self.assertEqual(out["outcome"], dispatch.UNMATCHED, out)
