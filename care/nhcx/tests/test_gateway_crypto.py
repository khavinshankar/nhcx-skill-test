import base64
import re
from datetime import datetime, timedelta, timezone

from django.test import SimpleTestCase

from care.nhcx.gateway import crypto
from care.nhcx.gateway import headers as H  # noqa: N812
from care.nhcx.tests.gateway_helpers import key


class HeaderTests(SimpleTestCase):
    def test_normalize_code(self):
        self.assertEqual(H.normalize_code("1000"), "1000@hcx")
        self.assertEqual(H.normalize_code(" 1000@hcx "), "1000@hcx")
        self.assertEqual(H.normalize_code(""), "")
        self.assertEqual(H.normalize_code(None), "")
        self.assertTrue(H.same_code("1000", "1000@HCX"))

    def test_paths(self):
        self.assertTrue(H.is_response_path("v1/preauth/on_submit"))
        self.assertFalse(H.is_response_path("/v1/claim/submit/"))
        self.assertEqual(H.entity_type("v1/preauth/submit"), "preauth")
        self.assertEqual(H.entity_type("v1/paymentnotice/on_request"), "payment")
        self.assertEqual(
            H.entity_type("v1/coverageeligibility/on_check"), "coverageeligibility"
        )
        self.assertEqual(H.default_status("v1/claim/submit"), "request.initiated")
        self.assertEqual(H.default_status("v1/claim/on_submit"), "response.complete")

    def test_target_url(self):
        self.assertEqual(
            H.target_url("https://x/hcx/v1/", "v1/claim/submit"),
            "https://x/hcx/v1/claim/submit",
        )
        self.assertEqual(
            H.target_url("https://x/hcx", "/v1/claim/submit"),
            "https://x/hcx/v1/claim/submit",
        )

    def test_build_protected_headers_fills_defaults(self):
        out = H.build_protected_headers(
            {
                H.SENDER_CODE: "1000",
                H.RECIPIENT_CODE: " 2000 ",
                H.CORRELATION_ID: "not-a-uuid",
                H.WORKFLOW_ID: "",
                "x-hcx-extra": "",
            },
            "v1/preauth/submit",
        )
        self.assertEqual(out[H.SENDER_CODE], "1000@hcx")
        self.assertEqual(out[H.RECIPIENT_CODE], "2000@hcx")
        self.assertTrue(H.is_id(out[H.CORRELATION_ID]))
        self.assertTrue(H.is_id(out[H.REQUEST_ID]))
        self.assertTrue(H.is_id(out[H.API_CALL_ID]))
        self.assertEqual(out[H.STATUS], "request.initiated")
        self.assertNotIn(H.WORKFLOW_ID, out)
        self.assertNotIn("x-hcx-extra", out)
        self.assertRegex(
            out[H.TIMESTAMP], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{4}$"
        )

    def test_given_ids_kept(self):
        cid = H.new_id()
        out = H.build_protected_headers(
            {H.CORRELATION_ID: cid, H.STATUS: "response.partial", H.WORKFLOW_ID: "11"},
            "v1/claim/on_submit",
        )
        self.assertEqual(out[H.CORRELATION_ID], cid)
        self.assertEqual(out[H.STATUS], "response.partial")
        self.assertEqual(out[H.WORKFLOW_ID], "11")

    def test_timestamps(self):
        ist = timezone(timedelta(hours=5, minutes=30))
        t = datetime(2026, 8, 31, 10, 5, 7, 123000, tzinfo=ist)
        self.assertTrue(re.match(r"2026-08-31T\d\d:05:07[+-]\d{4}", H.timestamp(t)))
        self.assertTrue(H.ack_timestamp(t).endswith(":05:07:123"))


class CryptoTests(SimpleTestCase):
    def setUp(self):
        self.priv = crypto.parse_private_key(key("facility-private.pem"))
        self.pub = crypto.parse_public_key(key("facility-public.pem"))

    def test_roundtrip(self):
        headers = {"x-hcx-sender_code": "a@hcx", "alg": "none", "enc": "x", "typ": "y"}
        jwe = crypto.encrypt('{"resourceType":"Bundle"}', self.pub, headers)
        self.assertTrue(crypto.is_compact_jwe(jwe))
        hdr = crypto.parse_header(jwe)
        self.assertEqual(hdr["alg"], "RSA-OAEP-256")
        self.assertEqual(hdr["enc"], "A256GCM")
        self.assertEqual(hdr["x-hcx-sender_code"], "a@hcx")
        self.assertNotIn("typ", hdr)
        self.assertEqual(crypto.decrypt(jwe, self.priv), b'{"resourceType":"Bundle"}')

    def test_wrong_key(self):
        jwe = crypto.encrypt("{}", crypto.parse_public_key(key("payer-cert.pem")), {})
        with self.assertRaises(crypto.CryptoError):
            crypto.decrypt(jwe, self.priv)

    def _large(self) -> bytes:
        return b'{"x":"' + b"a" * (crypto.AUTHLIB_SEGMENT_LIMIT * 2) + b'"}'

    def test_large_payload_beyond_authlib_segment_limit(self):
        payload = self._large()
        jwe = crypto.encrypt(payload, self.pub, {})
        self.assertGreater(len(jwe.split(".")[3]), crypto.AUTHLIB_SEGMENT_LIMIT)
        self.assertEqual(crypto.decrypt(jwe, self.priv), payload)

    def test_large_payload_other_algorithms(self):
        from authlib.jose import JsonWebEncryption

        payload = self._large()
        for alg in crypto.IN_ALGS:
            for enc in crypto.IN_ENCS:
                jwe = JsonWebEncryption(algorithms=[alg, enc]).serialize_compact(
                    {"alg": alg, "enc": enc}, payload, self.pub
                )
                with self.subTest(alg=alg, enc=enc):
                    self.assertEqual(crypto.decrypt(jwe.decode(), self.priv), payload)

    def test_large_payload_tampered_or_wrong_key(self):
        payload = self._large()
        jwe = crypto.encrypt(payload, self.pub, {})
        parts = jwe.split(".")
        parts[4] = "A" * len(parts[4])
        with self.assertRaisesMessage(crypto.CryptoError, "tag mismatch"):
            crypto.decrypt(".".join(parts), self.priv)
        other = crypto.encrypt(
            payload, crypto.parse_public_key(key("payer-cert.pem")), {}
        )
        with self.assertRaises(crypto.CryptoError):
            crypto.decrypt(other, self.priv)

    def test_not_compact(self):
        with self.assertRaisesMessage(crypto.CryptoError, crypto.NOT_COMPACT):
            crypto.decrypt("a.b.c", self.priv)

    def test_disallowed_alg(self):
        jwe = crypto.encrypt("{}", self.pub, {})
        parts = jwe.split(".")
        hdr = base64.urlsafe_b64encode(b'{"alg":"RSA1_5","enc":"A256GCM"}').rstrip(b"=")
        parts[0] = hdr.decode()
        with self.assertRaises(crypto.CryptoError):
            crypto.decrypt(".".join(parts), self.priv)

    def test_key_formats(self):
        for name in ("facility-private.pem", "facility-private-pkcs1.pem"):
            k = crypto.parse_private_key(key(name))
            self.assertTrue(crypto.public_numbers_equal(k.public_key(), self.pub))
        b64 = base64.b64encode(key("facility-private.pem").encode()).decode()
        crypto.parse_private_key(b64)
        cert = crypto.parse_public_key(key("facility-cert.pem"))
        self.assertTrue(crypto.public_numbers_equal(cert, self.pub))
        with self.assertRaises(crypto.CryptoError):
            crypto.parse_private_key("garbage")
        with self.assertRaises(crypto.CryptoError):
            crypto.parse_public_key("garbage")

    def test_flattened(self):
        jwe = crypto.encrypt("{}", self.pub, {})
        p, ek, iv, ct, tag = jwe.split(".")
        flat = {
            "protected": p,
            "encrypted_key": ek,
            "iv": iv,
            "ciphertext": ct,
            "tag": tag,
        }
        self.assertEqual(crypto.flattened_to_compact(flat), jwe)
        self.assertIsNone(crypto.flattened_to_compact({"x": 1}))
