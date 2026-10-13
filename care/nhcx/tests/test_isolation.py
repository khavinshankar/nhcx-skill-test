"""L7.1: the NHCX tests run isolated from the real gateway, its keys and the
network."""

import os
import socket
import threading

from django.conf import settings
from django.test import SimpleTestCase

from care.nhcx import tasks
from care.nhcx.gateway import GatewayNotConfigured, get_gateway, reset_gateway
from care.nhcx.tests import network_guard


class SettingsPinnedTests(SimpleTestCase):
    def test_gateway_settings_off(self):
        self.assertEqual(settings.NHCX_GATEWAY_CONFIG, "")
        self.assertFalse(settings.NHCX_ROLE)
        self.assertFalse(settings.NHCX_SHARED_TOKEN_CACHE)
        self.assertEqual(settings.NHCX_ARCHIVE_DIR, "")
        self.assertFalse(settings.NHCX_ADJUDICATOR_CONSOLE)
        self.assertEqual(settings.NHCX_HOSTED_PARTICIPANTS, "")

    def test_env_overrides_scrubbed(self):
        for name in (
            "NHCX_ENV",
            "NHCX_URL",
            "NHCX_PARTICIPANT_URL",
            "NHCX_SESSIONS_URL",
            "NHCX_PUBLIC_URL",
            "NHCX_CM_ID",
        ):
            self.assertNotIn(name, os.environ)

    def test_real_gateway_never_opens(self):
        reset_gateway()
        self.addCleanup(reset_gateway)
        with self.assertRaises(GatewayNotConfigured):
            get_gateway()

    def test_scheduled_work_is_off(self):
        self.assertIsNone(tasks._gateway())  # noqa: SLF001
        self.assertIsNone(tasks.refresh_tokens())
        self.assertIsNone(tasks.prune_ledger())


class NetworkGuardTests(SimpleTestCase):
    def test_installed(self):
        self.assertTrue(network_guard.installed())

    def test_external_lookup_blocked(self):
        with self.assertRaises(network_guard.NetworkBlockedError):
            socket.getaddrinfo("apisbx.abdm.gov.in", 443)

    def test_external_connect_blocked(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.addCleanup(sock.close)
        with self.assertRaises(network_guard.NetworkBlockedError):
            sock.connect(("203.0.113.10", 443))
        with self.assertRaises(network_guard.NetworkBlockedError):
            sock.connect_ex(("8.8.8.8", 53))

    def test_requests_cannot_swallow_the_block(self):
        import requests

        with self.assertRaises(network_guard.NetworkBlockedError):
            requests.get("https://apis.abdm.gov.in/", timeout=1)

    def test_loopback_allowed(self):
        self.assertTrue(socket.getaddrinfo("127.0.0.1", 9))
        self.assertTrue(socket.getaddrinfo("localhost", 9))
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.addCleanup(sock.close)
        sock.settimeout(0.5)
        self.assertIsInstance(sock.connect_ex(("127.0.0.1", 9)), int)

    def test_allow_rules(self):
        self.assertTrue(network_guard.allowed("127.0.0.1"))
        self.assertTrue(network_guard.allowed("::1"))
        self.assertTrue(network_guard.allowed(None))
        self.assertFalse(network_guard.allowed("nhcx.test"))
        self.assertFalse(network_guard.allowed("10.1.2.3"))

    def test_scoped_to_nhcx_tests(self):
        # A stack with no care/nhcx/tests frame (another app's tests) is let
        # through; this file's frames are inside the scope.
        code = compile(
            "def wrapper():\n"
            "    return guard._from_nhcx_test()\n"
            "def probe():\n"
            "    out.append(wrapper())\n",
            "/elsewhere/other_test.py",
            "exec",
        )
        scope = {"guard": network_guard, "out": []}
        exec(code, scope)  # noqa: S102
        worker = threading.Thread(target=scope["probe"])
        worker.start()
        worker.join()
        self.assertEqual(scope["out"], [False])

        def wrapper():
            return network_guard._from_nhcx_test()  # noqa: SLF001

        self.assertTrue(wrapper())
