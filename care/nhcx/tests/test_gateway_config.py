import json
import os
from pathlib import Path
from unittest import mock

from django.test import SimpleTestCase

from care.nhcx.gateway.config import (
    ConfigError,
    build_profiles,
    load_config,
)
from care.nhcx.gateway.embedding import open_gateway
from care.nhcx.tests.gateway_helpers import (
    FACILITY,
    KEYS,
    ScratchDirMixin,
    base_config,
    key,
)

CLEAN_ENV = {
    k: v
    for k, v in os.environ.items()
    if k
    not in (
        "NHCX_ENV",
        "NHCX_URL",
        "NHCX_PARTICIPANT_URL",
        "NHCX_SESSIONS_URL",
        "NHCX_PUBLIC_URL",
        "NHCX_CM_ID",
    )
}


@mock.patch.dict(os.environ, CLEAN_ENV, clear=True)
class ConfigTests(ScratchDirMixin, SimpleTestCase):
    def load(self, data):
        return load_config(self.write_config(data))

    def test_defaults_sandbox(self):
        cfg = self.load(base_config(urls=None, ledger=None))
        self.assertEqual(cfg.env, "sandbox")
        self.assertEqual(cfg.cmId, "sbx")
        self.assertEqual(cfg.url_nhcx, "https://apisbx.abdm.gov.in/hcx/v1")
        self.assertIn("sbxhcx/participanthcxservice", cfg.url_participant)
        self.assertEqual(
            cfg.url_sessions, "https://dev.abdm.gov.in/api/hiecm/gateway/v3/sessions"
        )
        self.assertEqual(cfg.auth_mode, "sessions")
        self.assertEqual(cfg.outbound_timeout, 30)
        self.assertEqual(cfg.max_body_bytes, 100 * 1024 * 1024)
        self.assertEqual(cfg.token_ttl_seconds, 1200)
        self.assertEqual(cfg.cert_cache_hours, 24)
        self.assertFalse(cfg.refuse_self_key)
        self.assertTrue(cfg.ledger_enabled)
        self.assertTrue(cfg.ledger_dir.endswith("data/ledger"))
        self.assertTrue(Path(cfg.ledger_dir).is_absolute())
        self.assertFalse(cfg.guests)

    def test_code_gets_hcx_suffix(self):
        data = base_config()
        data["participant"]["participantId"] = " 1000000001 "
        cfg = self.load(data)
        self.assertEqual(cfg.participant.participantId, FACILITY)

    def test_env_expansion(self):
        data = base_config()
        data["participant"]["clientSecret"] = "${NHCX_TEST_SECRET}"
        with mock.patch.dict(os.environ, {"NHCX_TEST_SECRET": 'se"cret'}):
            cfg = self.load(data)
        self.assertEqual(cfg.participant.clientSecret, 'se"cret')

    def test_missing_env_listed(self):
        data = base_config()
        data["participant"]["clientId"] = "${NHCX_NOPE_A}"
        data["participant"]["clientSecret"] = "${NHCX_NOPE_B}"
        with self.assertRaisesMessage(
            ConfigError, "environment variable(s) not set: NHCX_NOPE_A, NHCX_NOPE_B"
        ):
            self.load(data)

    def test_unknown_key_rejected(self):
        data = base_config()
        data["bogus"] = 1
        with self.assertRaisesMessage(ConfigError, 'unknown field "bogus"'):
            self.load(data)

    def test_comment_keys_allowed(self):
        data = base_config()
        data["$comment"] = "doc"
        data["participant"]["$comment_x"] = "doc"
        self.load(data)

    def test_env_override(self):
        with mock.patch.dict(
            os.environ,
            {"NHCX_URL": "https://other.test/hcx/v1", "NHCX_CM_ID": "x"},
        ):
            cfg = self.load(base_config())
        self.assertEqual(cfg.url_nhcx, "https://other.test/hcx/v1")
        self.assertEqual(cfg.cmId, "x")

    def test_private_key_file_relative(self):
        d = self.make_scratch()
        (d / "k.pem").write_text(key("facility-private.pem"))
        data = base_config()
        data["participant"]["privateKey"] = "@k.pem"
        p = d / "c.json"
        p.write_text(json.dumps(data))
        cfg = load_config(p)
        self.assertIn("PRIVATE KEY", cfg.participant.privateKey)

    def test_private_key_inline_and_pkcs1(self):
        data = base_config()
        data["participant"]["privateKey"] = key("facility-private-pkcs1.pem")
        self.load(data)

    def test_validation_messages(self):
        data = base_config(env="staging")
        data["participant"] = {"participantId": ""}
        data["auth"] = {"mode": "magic"}
        data["urls"] = {"nhcx": "nope"}
        data["log"] = {"level": "loud"}
        with self.assertRaises(ConfigError) as cm:
            self.load(data)
        msg = str(cm.exception)
        for part in (
            'env must be "sandbox" or "production", got "staging"',
            "participant.participantId is required",
            "participant.clientId and participant.clientSecret are required",
            "participant.privateKey is required",
            "openssl genpkey",
            'auth.mode must be "sessions" or "get-session", got "magic"',
            'urls.nhcx: "nope" is not an absolute http(s) URL',
            'log.level must be debug, info, warn or error, got "loud"',
        ):
            self.assertIn(part, msg)

    def test_bad_private_key(self):
        data = base_config()
        data["participant"]["privateKey"] = "not a key"
        with self.assertRaisesMessage(
            ConfigError, "participant.privateKey is not a valid RSA private key"
        ):
            self.load(data)

    def test_production_needs_nhcx_url(self):
        data = base_config(env="production", urls=None)
        with self.assertRaisesMessage(ConfigError, "urls.nhcx: is required"):
            self.load(data)
        data["urls"] = {"nhcx": "https://prod.test/hcx/v1"}
        cfg = self.load(data)
        self.assertEqual(cfg.cmId, "abdm")
        self.assertTrue(cfg.refuse_self_key)
        self.assertIn("apisprod.nha.gov.in", cfg.url_participant)

    def test_get_session_mode_url(self):
        data = base_config(auth={"mode": "get-session"})
        data["urls"].pop("sessions")
        cfg = self.load(data)
        self.assertTrue(cfg.url_sessions.endswith("participanthcxservice/get/session"))

    def test_participants_inherit_and_duplicates(self):
        data = base_config(
            participants=[
                {"participantId": "1000000002"},
                {"participantId": "1000000002@hcx"},
                {"participantId": "1000000003", "clientId": "only-id"},
            ]
        )
        with self.assertRaises(ConfigError) as cm:
            self.load(data)
        msg = str(cm.exception)
        self.assertIn("duplicates participants[0]", msg)
        self.assertIn("clientId and clientSecret must be set together", msg)

        data["participants"] = [{"participantId": "1000000002", "name": "PMJAY"}]
        cfg = self.load(data)
        everyone = cfg.all_participants()
        self.assertEqual(everyone[1].clientId, "client-1")
        self.assertEqual(everyone[1].privateKey, everyone[0].privateKey)
        profiles = build_profiles(cfg)
        self.assertEqual(profiles.codes(), [FACILITY, "1000000002@hcx"])
        self.assertTrue(profiles.is_local("1000000002"))
        self.assertEqual(profiles.resolve("unknown").code, FACILITY)

    def test_guests_section(self):
        cfg = self.load(base_config(guests={}))
        self.assertTrue(cfg.guests)

    def test_open_gateway_host_and_public_url(self):
        p = self.write_config(base_config())
        gw = open_gateway(
            str(p), lambda e, d: "settled", host={"1000000005": "Desk"}, guests=True
        )
        self.assertIn("1000000005@hcx", gw.participant_codes)
        self.assertTrue(gw.guests)
        p2 = self.write_config(base_config(publicUrl="ftp://x"))
        with self.assertRaisesMessage(ConfigError, "publicUrl:"):
            open_gateway(str(p2), lambda e, d: "settled")

    def test_example_config_documents_every_key(self):
        example = KEYS.parents[2] / "gateway" / "config.example.json"
        data = json.loads(example.read_text())
        for k in (
            "env",
            "publicUrl",
            "participant",
            "participants",
            "guests",
            "ledger",
            "certs",
            "outboundTimeoutSeconds",
            "maxBodyBytes",
            "auth",
            "cmId",
            "urls",
            "log",
        ):
            self.assertIn(k, data)
            self.assertIn(f"$comment_{k}", data)
