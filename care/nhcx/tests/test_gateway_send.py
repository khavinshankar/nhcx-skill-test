import json
from unittest import mock

import requests
from django.test import SimpleTestCase

from care.nhcx.gateway import headers as H  # noqa: N812
from care.nhcx.gateway import send as send_module
from care.nhcx.gateway.crypto import decrypt, parse_private_key
from care.nhcx.gateway.errors import GatewayError, SendError, SendInTransactionError
from care.nhcx.tests.gateway_helpers import (
    FACILITY,
    NHCX_URL,
    PAYER,
    SESSIONS_URL,
    FakeResponse,
    ScratchDirMixin,
    key,
)

BUNDLE = {"resourceType": "Bundle", "type": "collection", "entry": []}


class TokenTests(ScratchDirMixin, SimpleTestCase):
    def test_token_cached_and_payload(self):
        gw = self.open_gateway()
        t1 = gw.token()
        t2 = gw.token(FACILITY)
        self.assertEqual(t1["token"], "tok-1")
        self.assertEqual(t1["token_type"], "Bearer")
        self.assertEqual(t1["participant"], FACILITY)
        self.assertGreater(t1["expires_in"], 1000)
        self.assertEqual(t2["token"], "tok-1")
        calls = self.http.calls_to("/sessions")
        self.assertEqual(len(calls), 1)
        h = calls[0]["headers"]
        self.assertEqual(h["X-CM-ID"], "sbx")
        self.assertIn("REQUEST-ID", h)
        body = json.loads(calls[0]["data"])
        self.assertEqual(body["clientId"], "client-1")
        self.assertEqual(body["grantType"], "client_credentials")

    def test_refresh_forces_fetch(self):
        gw = self.open_gateway()
        gw.token()
        self.http.session_token = "tok-2"
        self.assertEqual(gw.refresh_token()["token"], "tok-2")

    def test_unknown_participant(self):
        gw = self.open_gateway()
        with self.assertRaises(GatewayError) as cm:
            gw.token("999@hcx")
        self.assertEqual(cm.exception.code, "UNKNOWN_PARTICIPANT")

    def test_token_errors(self):
        gw = self.open_gateway()
        self.http.on(SESSIONS_URL, FakeResponse(401, {"error": "bad"}))
        with self.assertRaises(GatewayError) as cm:
            gw.token()
        self.assertEqual(cm.exception.code, "TOKEN_HTTP_401")
        self.assertFalse(cm.exception.retryable)

        self.http.routes[SESSIONS_URL] = [FakeResponse(200, "<html>")]
        with self.assertRaises(GatewayError) as cm:
            gw.token()
        self.assertEqual(cm.exception.code, "TOKEN_BAD_JSON")

        self.http.routes[SESSIONS_URL] = [FakeResponse(200, {"x": 1})]
        with self.assertRaises(GatewayError) as cm:
            gw.token()
        self.assertEqual(cm.exception.code, "TOKEN_MISSING")

        self.http.routes[SESSIONS_URL] = [requests.ConnectionError("down")]
        with self.assertRaises(GatewayError) as cm:
            gw.token()
        self.assertEqual(cm.exception.code, "TOKEN_UNREACHABLE")
        self.assertTrue(cm.exception.retryable)

    def test_refresh_all_counts_failures(self):
        gw = self.open_gateway()
        self.assertEqual(gw.refresh_all(), 0)
        self.http.routes[SESSIONS_URL] = [FakeResponse(500, "x")]
        gw.tokens.tokens.clear()
        self.assertEqual(gw.refresh_all(), 1)

    def test_shared_store(self):
        store = {}

        class Store:
            def get(self, k):
                return store.get(k)

            def set(self, k, v, timeout=None):
                store[k] = v

        gw = self.open_gateway()
        gw.tokens.shared = Store()
        gw.token()
        self.assertTrue(store)


class SendTests(ScratchDirMixin, SimpleTestCase):
    def setUp(self):
        self.gw = self.open_gateway()
        self.payer_key = parse_private_key(key("payer-private.pem"))

    def envelope(self, **extra):
        return {"recipient": PAYER, "fhir": BUNDLE, **extra}

    def test_accepted(self):
        res = self.gw.send("v1/preauth/submit", self.envelope(workflow_id="11"))
        self.assertTrue(res.ok)
        self.assertEqual(res.gateway_status, 202)
        self.assertEqual(res.url, NHCX_URL + "/preauth/submit")
        self.assertEqual(res.txn_id, res.ledger_id)
        self.assertRegex(res.ledger_id, r"^[0-9A-V]{8}$")
        self.assertTrue(H.is_id(res.correlation_id))
        self.assertIsNone(res.error_code)

        call = self.http.calls_to("/preauth/submit")[0]
        self.assertEqual(call["headers"]["Authorization"], "Bearer tok-1")
        body = json.loads(call["data"])
        self.assertNotIn("type", body)
        plain = decrypt(body["payload"], self.payer_key)
        self.assertEqual(json.loads(plain), BUNDLE)
        from care.nhcx.gateway.crypto import parse_header

        hdr = parse_header(body["payload"])
        self.assertEqual(hdr[H.SENDER_CODE], FACILITY)
        self.assertEqual(hdr[H.RECIPIENT_CODE], PAYER)
        self.assertEqual(hdr[H.WORKFLOW_ID], "11")
        self.assertEqual(hdr[H.STATUS], "request.initiated")

        row = self.gw.ledger.get(res.ledger_id)
        self.assertEqual(row["status"], "accepted")
        self.assertEqual(row["direction"], "out")
        self.assertEqual(row["fhir"], BUNDLE)
        self.assertEqual(
            self.gw.ledger.dispatch(res.ledger_id),
            {"txnId": res.ledger_id, "status": "dispatched"},
        )

    def test_response_path_threading(self):
        self.gw.ledger.record(
            {
                "direction": "in",
                "path": "v1/communication/request",
                "sender": PAYER,
                "correlation_id": "c0a80101-0000-4000-8000-000000000001",
                "api_call_id": H.new_id(),
                "workflow_id": "11",
                "status": "delivered",
            }
        )
        res = self.gw.send("v1/communication/on_request", self.envelope())
        self.assertEqual(res.correlation_id, "c0a80101-0000-4000-8000-000000000001")
        self.assertEqual(res.headers[H.WORKFLOW_ID], "11")
        self.assertEqual(res.headers[H.STATUS], "response.complete")
        body = json.loads(self.http.calls_to("/communication/on_request")[0]["data"])
        self.assertEqual(body["type"], "JWEPayload")

    def test_rejected(self):
        self.http.on(
            NHCX_URL + "/claim/submit",
            FakeResponse(400, {"error": {"code": "ERR_INVALID", "message": "bad"}}),
        )
        res = self.gw.send("v1/claim/submit", self.envelope())
        self.assertFalse(res.ok)
        self.assertEqual(res.error_code, "ERR_INVALID")
        self.assertEqual(res.error_message, "bad")
        d = self.gw.ledger.dispatch(res.ledger_id)
        self.assertEqual(d["status"], "dispatch_failed")
        self.assertEqual(d["errorCode"], "GATEWAY_HTTP_400")

    def test_401_retried_once_with_fresh_token(self):
        self.http.on(
            NHCX_URL + "/claim/submit", FakeResponse(401, "x"), FakeResponse(202, {})
        )
        res = self.gw.send("v1/claim/submit", self.envelope())
        self.assertTrue(res.ok)
        self.assertEqual(len(self.http.calls_to("/sessions")), 2)

    def test_unreachable_is_failed_row(self):
        self.http.on(NHCX_URL + "/claim/submit", requests.ConnectionError("down"))
        with self.assertRaises(SendError) as cm:
            self.gw.send("v1/claim/submit", self.envelope())
        e = cm.exception
        self.assertEqual(e.code, "GATEWAY_UNREACHABLE")
        self.assertTrue(e.retryable)
        self.assertTrue(e.ledger_id)
        self.assertTrue(H.is_id(e.correlation_id))
        d = self.gw.ledger.dispatch(e.ledger_id)
        self.assertEqual(d["status"], "dispatch_failed")
        self.assertEqual(d["errorCode"], "GATEWAY_UNREACHABLE")

    def test_cert_errors(self):
        self.http.on(
            "https://registry.test/participanthcxservice/fetch/certs",
            FakeResponse(200, {"x": 1}),
        )
        with self.assertRaises(SendError) as cm:
            self.gw.send("v1/claim/submit", self.envelope())
        self.assertEqual(cm.exception.code, "CERT_NOT_FOUND")
        self.assertTrue(cm.exception.ledger_id)

    def test_cert_cached(self):
        self.gw.send("v1/claim/submit", self.envelope())
        self.gw.send("v1/claim/submit", self.envelope())
        self.assertEqual(len(self.http.calls_to("/fetch/certs")), 1)

    def test_invalid_envelopes_write_nothing(self):
        for path, env, code in (
            ("v1/claim/submit", "x", "INVALID_ENVELOPE"),
            ("v1/claim/submit", {"recipient": PAYER}, "INVALID_ENVELOPE"),
            ("v1/claim/submit", {"jwe_headers": 1, "fhir": BUNDLE}, "INVALID_ENVELOPE"),
            ("", {"fhir": BUNDLE}, "NO_PATH"),
            ("v1/claim/submit", {"fhir": "{bad"}, "INVALID_PAYLOAD"),
        ):
            with self.subTest(code=code), self.assertRaises(SendError) as cm:
                self.gw.send(path, env)
            self.assertEqual(cm.exception.code, code)
        self.assertEqual(self.gw.ledger.list(), [])

    def test_no_recipient_is_recorded(self):
        with self.assertRaises(SendError) as cm:
            self.gw.send("v1/claim/submit", {"fhir": BUNDLE})
        self.assertEqual(cm.exception.code, "NO_RECIPIENT")
        self.assertTrue(cm.exception.ledger_id)

    def test_payload_alias_and_string(self):
        res = self.gw.send(
            "v1/claim/submit",
            {"x-hcx-recipient_code": PAYER, "payload": json.dumps(BUNDLE)},
        )
        self.assertTrue(res.ok)
        self.assertEqual(self.gw.ledger.get(res.ledger_id)["fhir"], BUNDLE)

    def test_refuses_inside_atomic_block(self):
        conn = mock.Mock(
            in_atomic_block=True, atomic_blocks=[mock.Mock(_from_testcase=False)]
        )
        conn.alias = "default"
        with mock.patch.object(send_module, "connections") as conns:
            conns.all.return_value = [conn]
            with self.assertRaises(SendInTransactionError):
                self.gw.send("v1/claim/submit", self.envelope())
        self.assertEqual(self.http.calls_to("/claim/submit"), [])

    def test_testcase_atomic_block_ignored(self):
        conn = mock.Mock(
            in_atomic_block=True, atomic_blocks=[mock.Mock(_from_testcase=True)]
        )
        with mock.patch.object(send_module, "connections") as conns:
            conns.all.return_value = [conn]
            send_module.ensure_not_in_transaction()

    def test_ledger_off(self):
        gw = self.open_gateway(ledger={"enabled": False})
        res = gw.send("v1/claim/submit", self.envelope())
        self.assertTrue(res.ok)
        self.assertEqual(res.ledger_id, "")
        with self.assertRaises(GatewayError) as cm:
            gw.ledger.dispatch("7UMV0001")
        self.assertEqual(cm.exception.code, "LEDGER_DISABLED")

    def test_send_error_dict(self):
        self.http.on(NHCX_URL + "/claim/submit", requests.ConnectionError("down"))
        with self.assertRaises(SendError) as cm:
            self.gw.send("v1/claim/submit", self.envelope())
        d = cm.exception.to_dict()
        self.assertEqual(d["code"], "GATEWAY_UNREACHABLE")
        self.assertTrue(d["retryable"])
        self.assertEqual(d["txn_id"], cm.exception.ledger_id)
        self.assertIn("correlation_id", d)
