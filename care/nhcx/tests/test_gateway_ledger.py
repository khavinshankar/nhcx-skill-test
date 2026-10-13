from datetime import UTC, datetime, timedelta

from django.test import SimpleTestCase

from care.nhcx.gateway import headers as H  # noqa: N812
from care.nhcx.gateway.errors import GatewayError
from care.nhcx.gateway.ledger import Ledger, day_code, day_of_id, summarize
from care.nhcx.tests.gateway_helpers import ScratchDirMixin

CORR = "c0a80101-0000-4000-8000-000000000001"


class LedgerTests(ScratchDirMixin, SimpleTestCase):
    def setUp(self):
        self.dir = self.make_scratch() / "ledger"
        self.ledger = Ledger(self.dir, retention_days=2)

    def entry(self, **kw):
        e = {
            "direction": "out",
            "path": "v1/preauth/submit",
            "sender": "1@hcx",
            "recipient": "2@hcx",
            "correlation_id": CORR,
            "api_call_id": H.new_id(),
            "status": "accepted",
            "headers": {"x": "y"},
            "fhir": {
                "resourceType": "Bundle",
                "entry": [
                    {
                        "resource": {
                            "resourceType": "Claim",
                            "identifier": [{"value": "C-1"}],
                        }
                    }
                ],
            },
        }
        e.update(kw)
        return e

    def test_ids(self):
        t = datetime(2026, 8, 31, 12, tzinfo=UTC)
        self.assertEqual(day_code(t), "7UMV")
        self.assertEqual(day_of_id("7UMV0001"), "2026-08-31")
        self.assertIsNone(day_of_id("../etc"))
        self.assertIsNone(day_of_id("short"))
        a = self.ledger.record(self.entry(created_at=t.isoformat()))
        b = self.ledger.record(self.entry(created_at=t.isoformat()))
        self.assertEqual((a, b), ("7UMV0001", "7UMV0002"))
        self.assertTrue((self.dir / "2026-08-31" / "7UMV0001.json").exists())

    def test_queries(self):
        a = self.ledger.record(self.entry())
        b = self.ledger.record(
            self.entry(direction="in", path="v1/preauth/on_submit", status="delivered")
        )
        self.ledger.record(self.entry(correlation_id=H.new_id()))
        rel = self.ledger.related(a)
        self.assertEqual([r["id"] for r in rel], [b, a])
        self.assertEqual(rel[0]["type"], "preauth")
        self.assertEqual(rel[0]["flow"], "on_submit")
        self.assertEqual(
            set(rel[0]),
            {
                "id",
                "direction",
                "status",
                "sender",
                "recipient",
                "correlation_id",
                "api_call_id",
                "type",
                "flow",
                "created_at",
            },
        )
        env = self.ledger.fhir(b)
        self.assertEqual(env["meta"]["type"], "in")
        self.assertEqual(env["jwe_headers"], {"x": "y"})
        self.assertEqual(self.ledger.dispatch(b)["status"], "dispatched")
        self.assertEqual(len(self.ledger.list()), 3)
        self.assertEqual(len(self.ledger.list(1)), 1)
        self.assertEqual(len(self.ledger.list(0)), 3)
        row = self.ledger.get(a)
        self.assertEqual(row["fhir_summary"]["focus"], "Claim")
        self.assertEqual(row["fhir_summary"]["identifier"], "C-1")
        thread = self.ledger.thread(CORR)
        self.assertEqual(thread["state"], "completed")
        self.assertEqual(thread["role"], "initiator")

    def test_errors(self):
        for txn, code in (
            ("", "NO_TXN_ID"),
            ("7UMV0099", "TXN_NOT_FOUND"),
            ("x/y", "TXN_NOT_FOUND"),
        ):
            with self.subTest(txn=txn), self.assertRaises(GatewayError) as cm:
                self.ledger.dispatch(txn)
            self.assertEqual(cm.exception.code, code)
        self.assertIsNone(self.ledger.get("nope"))

    def test_failed_dispatch(self):
        a = self.ledger.record(
            self.entry(
                status="failed", error={"code": "CERT_NOT_FOUND", "message": "m"}
            )
        )
        self.assertEqual(
            self.ledger.dispatch(a),
            {
                "txnId": a,
                "status": "dispatch_failed",
                "errorCode": "CERT_NOT_FOUND",
                "errorMessage": "m",
            },
        )

    def test_second_instance_sees_writes(self):
        other = Ledger(self.dir)
        a = self.ledger.record(self.entry())
        b = other.record(self.entry())
        self.assertNotEqual(a, b)
        self.assertEqual({r["id"] for r in self.ledger.list()}, {a, b})
        self.assertTrue(other.seen("out", self.ledger.get(a)["api_call_id"]))

    def test_store_bodies_off(self):
        ledger = Ledger(self.dir, store_bodies=False)
        a = ledger.record(self.entry())
        row = ledger.get(a)
        self.assertIsNone(row["fhir"])
        self.assertEqual(row["fhir_summary"]["focus"], "Claim")

    def test_sweep(self):
        now = datetime.now(UTC)
        old = self.ledger.record(
            self.entry(created_at=(now - timedelta(days=5)).isoformat())
        )
        new = self.ledger.record(self.entry(created_at=now.isoformat()))
        self.assertEqual(self.ledger.sweep(now), 1)
        self.assertIsNone(self.ledger.get(old))
        self.assertIsNotNone(self.ledger.get(new))
        self.assertEqual([r["id"] for r in self.ledger.list()], [new])
        self.assertEqual(Ledger(self.dir, retention_days=0).sweep(now), 0)

    def test_disabled(self):
        ledger = Ledger(None, enabled=False)
        self.assertIsNone(ledger.record(self.entry()))
        self.assertEqual(ledger.list(), [])
        with self.assertRaises(GatewayError) as cm:
            ledger.related("7UMV0001")
        self.assertEqual(cm.exception.code, "LEDGER_DISABLED")

    def test_summarize_non_bundle(self):
        self.assertEqual(summarize({"resourceType": "Task"})["focus"], "Task")
        self.assertIsNone(summarize("x"))
