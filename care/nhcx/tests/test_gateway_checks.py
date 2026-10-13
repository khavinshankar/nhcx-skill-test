import json
from unittest import mock

from django.test import RequestFactory, SimpleTestCase, override_settings

from care.nhcx import gateway as gateway_pkg
from care.nhcx import tasks
from care.nhcx.gateway import checks, views
from care.nhcx.gateway.errors import GatewayError, GatewayNotConfigured
from care.nhcx.tests.gateway_helpers import (
    FACILITY,
    PARTICIPANT_URL,
    SESSIONS_URL,
    FakeResponse,
    ScratchDirMixin,
    base_config,
)
from care.nhcx.tests.gateway_helpers import key as key_text
from care.nhcx.tests.test_gateway_receive import inbound_body


class BeneficiaryTests(ScratchDirMixin, SimpleTestCase):
    def test_policies_search(self):
        gw = self.open_gateway()
        self.http.on(
            PARTICIPANT_URL + "/participant/get/policies",
            FakeResponse(200, {"policies": [{"id": 1}]}),
        )
        out = gw.beneficiary.policies_search({"mobile": " 9999999999 "})
        self.assertEqual(out, {"status": 200, "body": {"policies": [{"id": 1}]}})
        sent = json.loads(self.http.calls_to("/participant/get/policies")[0]["data"])
        self.assertEqual(
            sent, {"identifiertype": "MobileNo", "identifiervalue": "9999999999"}
        )

        gw.beneficiary.policies_search({"abhaNo": "91-1"})
        sent = json.loads(self.http.calls_to("/participant/get/policies")[1]["data"])
        self.assertEqual(sent["identifiertype"], "AbhaNumber")

        gw.beneficiary.policies_search(
            {"identifiertype": "PMJAY", "identifiervalue": "X"}
        )
        sent = json.loads(self.http.calls_to("/participant/get/policies")[2]["data"])
        self.assertEqual(sent, {"identifiertype": "PMJAY", "identifiervalue": "X"})

    def test_no_identifier(self):
        gw = self.open_gateway()
        with self.assertRaises(GatewayError) as cm:
            gw.beneficiary.policies_search({})
        self.assertEqual(cm.exception.code, "NO_IDENTIFIER")

    def test_non_json_upstream(self):
        gw = self.open_gateway()
        self.http.on(
            PARTICIPANT_URL + "/participant/link/abha/policy", FakeResponse(500, "oops")
        )
        self.assertEqual(
            gw.beneficiary.abha_link({}), {"status": 500, "body": {"error": "oops"}}
        )


class CheckTests(ScratchDirMixin, SimpleTestCase):
    def test_healthz_probe(self):
        gw = self.open_gateway()
        out = gw.healthz()
        self.assertEqual(out["status"], "ok")
        self.assertEqual(out["participant"], FACILITY)
        self.assertNotIn("probe_ack", out)
        out = gw.healthz("POST", b'{"probe": "n1"}')
        key = checks.probe_key(FACILITY, "secret-1", "")
        self.assertTrue(checks.verify(key, "n1", out["probe_ack"]))
        self.assertNotIn(
            "probe_ack", gw.healthz("POST", json.dumps({"probe": "x" * 200}).encode())
        )

    def test_readyz(self):
        gw = self.open_gateway()
        self.assertEqual(gw.readyz(), (503, {"status": "no session token"}))
        gw.token()
        self.assertEqual(gw.readyz(), (200, {"status": "ready"}))

    def test_run_checks(self):
        gw = self.open_gateway()
        self.http.on(
            PARTICIPANT_URL + "/participant/search",
            FakeResponse(
                200,
                {
                    "participants": [
                        {
                            "participant_code": FACILITY,
                            "participant_name": "Test Hospital",
                            "status": "Active",
                            "endpoint_url": "https://care.test/in",
                        }
                    ]
                },
            ),
        )
        self.http.on(
            PARTICIPANT_URL + "/fetch/certs",
            FakeResponse(200, {"encryption_cert": key_text("facility-cert.pem")}),
        )
        report = checks.run_checks(gw)
        self.assertEqual(report["cert"], "match")
        self.assertEqual(report["participant"]["endpointUrl"], "https://care.test/in")
        self.assertTrue(all(c["ok"] for c in report["checks"]), report)

        self.http.routes[PARTICIPANT_URL + "/fetch/certs"] = [
            FakeResponse(200, {"encryption_cert": key_text("payer-cert.pem")})
        ]
        report = checks.run_checks(gw)
        self.assertEqual(report["cert"], "mismatch")

        self.http.routes[SESSIONS_URL] = [FakeResponse(401, "no")]
        report = gw.check()
        self.assertFalse(report["checks"][0]["ok"])
        self.assertIn("TOKEN_HTTP_401", report["checks"][0]["detail"])

    def test_test_endpoint(self):
        key = checks.probe_key(FACILITY, "secret-1", "")

        class Http:
            def post(self, url, data=None, headers=None, timeout=None, **kw):
                nonce = json.loads(data)["probe"]
                return FakeResponse(200, {"probe_ack": checks.ack(key, nonce)})

        ok, _ = checks.test_endpoint(Http(), "https://care.test/in", key)
        self.assertTrue(ok)
        ok, _ = checks.test_endpoint(Http(), "https://care.test/in", b"other")
        self.assertFalse(ok)


class ViewTests(ScratchDirMixin, SimpleTestCase):
    def setUp(self):
        self.rf = RequestFactory()
        self.addCleanup(gateway_pkg.reset_gateway)

    def test_routes_resolve(self):
        from django.urls import resolve

        self.assertEqual(
            resolve("/in/v1/claim/on_submit").kwargs, {"path": "v1/claim/on_submit"}
        )
        self.assertEqual(
            resolve("/v1/claim/on_submit").kwargs,
            {"path": "claim/on_submit", "prefix": "v1/"},
        )
        self.assertEqual(resolve("/in/healthz").url_name, "nhcx-in-healthz")
        self.assertEqual(resolve("/api/gateway/readyz").url_name, "nhcx-readyz")

    def test_inbound_view(self):
        gw = self.open_gateway()
        gateway_pkg.set_gateway(gw)
        body, _ = inbound_body()
        req = self.rf.post(
            "/v1/claim/on_submit",
            body,
            content_type="application/json",
            HTTP_X_REQUEST_ID="r1",
        )
        resp = views.inbound(req, path="claim/on_submit", prefix="v1/")
        self.assertEqual(resp.status_code, 202)
        self.assertEqual(resp["X-Request-Id"], "r1")
        self.assertTrue(resp["X-Nhcx-Ledger-Id"])
        self.assertEqual(self.received[0][1]["path"], "v1/claim/on_submit")

    def test_inbound_too_large(self):
        gw = self.open_gateway(maxBodyBytes=10)
        gateway_pkg.set_gateway(gw)
        req = self.rf.post("/in/x", b"x" * 50, content_type="application/json")
        resp = views.inbound(req, path="x")
        self.assertEqual(resp.status_code, 413)
        self.assertEqual(json.loads(resp.content)["error"]["code"], "BODY_TOO_LARGE")

    def test_inbound_get_not_allowed(self):
        gateway_pkg.set_gateway(self.open_gateway())
        self.assertEqual(views.inbound(self.rf.get("/in/x"), path="x").status_code, 405)

    def test_internal_error(self):
        gw = self.open_gateway()
        gateway_pkg.set_gateway(gw)
        with mock.patch.object(gw, "handle_inbound", side_effect=RuntimeError("x")):
            resp = views.inbound(
                self.rf.post("/in/x", b"{}", content_type="application/json"), path="x"
            )
        self.assertEqual(resp.status_code, 500)
        self.assertEqual(json.loads(resp.content)["error"]["code"], "INTERNAL")

    @override_settings(NHCX_GATEWAY_CONFIG="")
    def test_not_configured(self):
        gateway_pkg.reset_gateway()
        with self.assertRaises(GatewayNotConfigured):
            gateway_pkg.get_gateway()
        body, _ = inbound_body()
        resp = views.inbound(
            self.rf.post("/in/x", body, content_type="application/json"), path="x"
        )
        self.assertEqual(resp.status_code, 202)
        resp = views.readyz(self.rf.get("/readyz"))
        self.assertEqual(resp.status_code, 503)
        self.assertIn("not configured", json.loads(resp.content)["status"])
        resp = views.healthz(self.rf.get("/healthz"))
        self.assertEqual(resp.status_code, 200)

    def test_health_views(self):
        gateway_pkg.set_gateway(self.open_gateway())
        resp = views.healthz(
            self.rf.post("/healthz", b'{"probe":"n"}', content_type="application/json")
        )
        self.assertIn("probe_ack", json.loads(resp.content))
        self.assertEqual(views.readyz(self.rf.get("/readyz")).status_code, 503)

    def test_get_gateway_from_settings(self):
        path = self.write_config(base_config())
        with override_settings(
            NHCX_GATEWAY_CONFIG=str(path),
            NHCX_RECEIVE_HANDLER="care.nhcx.does_not_exist.receive",
            NHCX_HOSTED_PARTICIPANTS="1000000007=Desk",
            NHCX_SHARED_TOKEN_CACHE=False,
        ):
            gateway_pkg.reset_gateway()
            gw = gateway_pkg.get_gateway()
            self.assertIs(gateway_pkg.get_gateway(), gw)
            self.assertIn("1000000007@hcx", gw.participant_codes)
            self.assertEqual(gw.receive({}, {}), "unmatched")


class TaskTests(ScratchDirMixin, SimpleTestCase):
    def setUp(self):
        self.addCleanup(gateway_pkg.reset_gateway)

    @override_settings(NHCX_ROLE=False, NHCX_GATEWAY_CONFIG="x")
    def test_noop_without_role(self):
        self.assertIsNone(tasks.refresh_tokens())
        self.assertIsNone(tasks.prune_ledger())

    def test_runs_with_role(self):
        gw = self.open_gateway()
        gateway_pkg.set_gateway(gw)
        with override_settings(NHCX_ROLE=True, NHCX_GATEWAY_CONFIG="set"):
            self.assertEqual(tasks.refresh_tokens(), 0)
            self.assertEqual(tasks.prune_ledger(), 0)
        self.assertEqual(len(self.http.calls_to("/sessions")), 1)
        self.assertEqual(self.http.calls[0]["url"], SESSIONS_URL)
