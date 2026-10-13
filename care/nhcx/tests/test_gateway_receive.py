import json

from django.test import SimpleTestCase

from care.nhcx.gateway import crypto
from care.nhcx.gateway import headers as H  # noqa: N812
from care.nhcx.gateway.receive import not_open_answer
from care.nhcx.tests.gateway_helpers import FACILITY, PAYER, ScratchDirMixin, key

BUNDLE = {"resourceType": "Bundle", "type": "collection", "entry": []}


def inbound_body(recipient=FACILITY, public="facility-public.pem", **hdr):
    headers = {
        H.SENDER_CODE: PAYER,
        H.RECIPIENT_CODE: recipient,
        H.API_CALL_ID: H.new_id(),
        H.CORRELATION_ID: H.new_id(),
        H.REQUEST_ID: H.new_id(),
        H.TIMESTAMP: H.timestamp(),
        H.STATUS: "response.complete",
        **hdr,
    }
    jwe = crypto.encrypt(
        json.dumps(BUNDLE), crypto.parse_public_key(key(public)), headers
    )
    return json.dumps({"payload": jwe}).encode(), headers


class ReceiveTests(ScratchDirMixin, SimpleTestCase):
    def test_delivered(self):
        gw = self.open_gateway()
        body, hdr = inbound_body(**{H.WORKFLOW_ID: "11"})
        ans = gw.handle_inbound("v1/preauth/on_submit", body, "10.0.0.1", "rid-1")
        self.assertEqual(ans.status, 202)
        self.assertEqual(ans.outcome, "settled")
        self.assertEqual(ans.body["api_call_id"], hdr[H.API_CALL_ID])
        self.assertEqual(ans.body["correlation_id"], hdr[H.CORRELATION_ID])
        self.assertEqual(ans.body["result"]["entity_type"], "preauth")
        self.assertEqual(ans.body["result"]["protocol_status"], "request.queued")
        self.assertIsNone(ans.body["error"])
        lid = ans.headers["X-Nhcx-Ledger-Id"]

        envelope, delivery = self.received[0]
        self.assertEqual(envelope["fhir"], BUNDLE)
        self.assertEqual(envelope["meta"]["type"], "in")
        self.assertEqual(envelope["meta"]["payloadType"], "fhir")
        self.assertEqual(envelope["meta"]["participant"], FACILITY)
        self.assertEqual(envelope["jwe_headers"][H.SENDER_CODE], PAYER)
        self.assertEqual(delivery["type"], "preauth")
        self.assertEqual(delivery["flow"], "request")
        self.assertEqual(delivery["correlation_id"], hdr[H.CORRELATION_ID])
        self.assertFalse(delivery["redelivery"])

        row = gw.ledger.get(lid)
        self.assertEqual(row["direction"], "in")
        self.assertEqual(row["status"], "delivered")
        self.assertEqual(row["workflow_id"], "11")
        self.assertEqual(gw.ledger.fhir(lid)["fhir"], BUNDLE)

        gw.handle_inbound("v1/preauth/on_submit", body, "10.0.0.1", "rid-2")
        self.assertTrue(self.received[1][1]["redelivery"])

    def test_receive_failure_is_502(self):
        def boom(envelope, delivery):
            raise RuntimeError("db down")

        gw = self.open_gateway(receive=boom)
        body, _ = inbound_body()
        ans = gw.handle_inbound("v1/claim/on_submit", body, "", "rid")
        self.assertEqual(ans.status, 502)
        self.assertEqual(ans.body["error"]["code"], "RECEIVE_FAILED")
        self.assertTrue(ans.body["error"]["retryable"])
        self.assertEqual(ans.body["upstream_status"], 502)
        self.assertEqual(ans.body["request_id"], "rid")
        rows = gw.ledger.list()
        self.assertEqual(rows[0]["status"], "delivery_failed")

    def test_outcomes(self):
        for result, status in (
            ("unmatched", 202),
            ({"outcome": "ignored"}, 202),
            ({"outcome": "rejected", "detail": "x"}, 202),
            ({"outcome": "error", "detail": "x"}, 502),
            ("weird", 502),
        ):
            with self.subTest(result=result):
                gw = self.open_gateway(receive=lambda e, d, r=result: r)
                body, _ = inbound_body()
                self.assertEqual(
                    gw.handle_inbound("v1/claim/on_submit", body).status, status
                )

    def test_wrong_recipient(self):
        gw = self.open_gateway()
        body, _ = inbound_body(recipient="5555@hcx")
        ans = gw.handle_inbound("v1/claim/on_submit", body)
        self.assertEqual(ans.status, 400)
        self.assertEqual(ans.body["error"]["code"], "WRONG_RECIPIENT")
        self.assertIn("5555@hcx", ans.body["error"]["message"])
        self.assertEqual(gw.ledger.list()[0]["status"], "rejected")
        self.assertEqual(self.received, [])

    def test_guest_opened_with_our_key(self):
        gw = self.open_gateway(guests={})
        body, _ = inbound_body(recipient="5555@hcx")
        ans = gw.handle_inbound("v1/claim/on_submit", body)
        self.assertEqual(ans.status, 202)
        self.assertEqual(self.received[0][1]["participant"], "5555@hcx")

    def test_decrypt_failed(self):
        gw = self.open_gateway()
        body, _ = inbound_body(public="payer-public.pem")
        ans = gw.handle_inbound("v1/claim/on_submit", body)
        self.assertEqual(ans.status, 422)
        self.assertEqual(ans.body["error"]["code"], "DECRYPT_FAILED")

    def test_bad_bodies(self):
        gw = self.open_gateway()
        for body, status, code in (
            (b"nope", 400, "INVALID_BODY"),
            (b"[1]", 400, "INVALID_BODY"),
            (b'{"payload": "a.b.c"}', 400, "INVALID_JWE"),
        ):
            with self.subTest(code=code):
                ans = gw.handle_inbound("v1/claim/on_submit", body)
                self.assertEqual(ans.status, status)
                self.assertEqual(ans.body["error"]["code"], code)

    def test_protocol_message(self):
        gw = self.open_gateway()
        body = json.dumps(
            {
                "type": "ProtocolResponse",
                H.SENDER_CODE: "hcx-gateway",
                H.RECIPIENT_CODE: FACILITY,
                H.CORRELATION_ID: H.new_id(),
                H.STATUS: "response.error",
                "x-hcx-error_details": {"code": "ERR_X"},
            }
        ).encode()
        ans = gw.handle_inbound("v1/claim/on_submit", body)
        self.assertEqual(ans.status, 202)
        envelope, delivery = self.received[0]
        self.assertEqual(envelope["meta"]["payloadType"], "protocol")
        self.assertEqual(delivery["payload_kind"], "protocol")

    def test_flattened_jwe(self):
        gw = self.open_gateway()
        body, _ = inbound_body()
        p, ek, iv, ct, tag = json.loads(body)["payload"].split(".")
        flat = {
            "protected": p,
            "encrypted_key": ek,
            "iv": iv,
            "ciphertext": ct,
            "tag": tag,
        }
        ans = gw.handle_inbound(
            "v1/claim/on_submit", json.dumps({"payload": flat}).encode()
        )
        self.assertEqual(ans.status, 202)
        self.assertEqual(self.received[0][0]["fhir"], BUNDLE)

    def test_not_open_answer(self):
        body, hdr = inbound_body()
        ans = not_open_answer("v1/claim/on_submit", body)
        self.assertEqual(ans.status, 202)
        self.assertEqual(ans.outcome, "unmatched")
        self.assertEqual(ans.body["api_call_id"], hdr[H.API_CALL_ID])
