"""G11. Startup checks, liveness and readiness."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import secrets
import threading
from typing import TYPE_CHECKING, Any

import requests

from care.nhcx.gateway import crypto
from care.nhcx.gateway.errors import GatewayError, as_gateway_error

if TYPE_CHECKING:
    from care.nhcx.gateway.embedding import Gateway

logger = logging.getLogger("care.nhcx.gateway")

SERVICE = "nhcx-adapter"
MAX_NONCE = 128
HEALTH_BODY_LIMIT = 4096
PROBE_BODY_LIMIT = 64 * 1024
PROBE_TIMEOUT = 15
CHECKS_TIMEOUT = 120
ENDPOINT_TIMEOUT = 30
HTTP_OK = 200


def probe_key(participant_id: str, client_secret: str, api_key: str) -> bytes:
    text = f"nhcx-adapter probe v1\0{participant_id}\0{client_secret}\0{api_key}"
    return hashlib.sha256(text.encode("utf-8")).digest()


def ack(key: bytes, nonce: str) -> str:
    return hmac.new(key, nonce.encode("utf-8"), hashlib.sha256).hexdigest()


def verify(key: bytes, nonce: str, answer: str) -> bool:
    return hmac.compare_digest(ack(key, nonce), answer or "")


def gateway_probe_key(gw: Gateway) -> bytes:
    d = gw.cfg.participant
    return probe_key(d.participantId, d.clientSecret, gw.cfg.api_key)


def healthz(gw: Gateway, method: str = "GET", body: bytes | None = None) -> dict:
    out = {
        "status": "ok",
        "service": SERVICE,
        "version": gw.version,
        "env": gw.cfg.env,
        "participant": gw.profiles.default.code,
    }
    if method.upper() == "POST" and body:
        try:
            req = json.loads(body[:HEALTH_BODY_LIMIT])
        except (ValueError, TypeError, UnicodeDecodeError):
            req = None
        nonce = req.get("probe") if isinstance(req, dict) else None
        if isinstance(nonce, str) and 0 < len(nonce) <= MAX_NONCE:
            out["probe_ack"] = ack(gateway_probe_key(gw), nonce)
    return out


def readyz(gw: Gateway) -> tuple[int, dict]:
    if gw.default_client.token_valid():
        return 200, {"status": "ready"}
    return 503, {"status": "no session token"}


def explain(e: BaseException) -> str:
    g = as_gateway_error(e)
    text = f"{g.code}: {g.message}"
    if g.body:
        text += f" ({g.body})"
    return text


def run_checks(gw: Gateway) -> dict:  # noqa: PLR0912, PLR0915
    report: dict[str, Any] = {"checks": [], "cert": "unknown", "participant": None}

    def add(name: str, detail: str, *, ok: bool) -> None:
        report["checks"].append({"name": name, "ok": ok, "detail": detail})

    def passed(name: str, detail: str) -> None:
        add(name, detail, ok=True)

    def failed(name: str, detail: str) -> None:
        add(name, detail, ok=False)

    client = gw.default_client
    code = gw.profiles.default.code
    try:
        client.refresh_token()
    except Exception as e:
        failed(
            "session token",
            explain(e)
            + " - check participant.clientId / clientSecret, auth.mode and urls.sessions",
        )
        return report
    passed("session token", "issued by " + gw.cfg.url_sessions)

    try:
        p = client.fetch_participant(code)
        endpoint = (
            "endpoint " + p["endpointUrl"]
            if p.get("endpointUrl")
            else "no endpoint_url registered"
        )
        passed(
            "participant record",
            f"{p['code']} · {p.get('name')} · {p.get('status')} · {endpoint}",
        )
        report["participant"] = p
    except Exception as e:
        failed("participant record", explain(e))

    try:
        pub, _ = client.fetch_certificate(code)
        if crypto.public_numbers_equal(pub, client.own_key()):
            report["cert"] = "match"
            passed("encryption certificate", "match")
        else:
            report["cert"] = "mismatch"
            failed(
                "encryption certificate",
                "mismatch: does NOT match participant.privateKey, inbound messages "
                "could not be decrypted",
            )
    except Exception as e:
        g = as_gateway_error(e)
        if g.code == "CERT_NOT_FOUND":
            report["cert"] = "missing"
            failed(
                "encryption certificate",
                "registry has no encryption certificate",
            )
        else:
            failed("encryption certificate", explain(e))

    if len(gw.profiles.profiles) > 1:
        for prof in gw.profiles.profiles[1:]:
            name = "participant " + prof.code
            c = gw.identity_for(prof.code)
            try:
                c.token()
            except Exception as e:
                failed(name, explain(e) + " - check its clientId / clientSecret")
                continue
            try:
                pub, _ = c.fetch_certificate(prof.code)
            except Exception as e:
                failed(name, explain(e))
                continue
            if crypto.public_numbers_equal(pub, prof.public_key):
                passed(name, "certificate matches · callback C1.receive (in-process)")
            else:
                failed(name, "registry certificate does not match its private key")
    return report


def test_endpoint(http: Any, endpoint_url: str, key: bytes) -> tuple[bool, str]:
    url = endpoint_url.rstrip("/") + "/healthz"
    nonce = secrets.token_hex(16)
    try:
        resp = http.post(
            url,
            data=json.dumps({"probe": nonce}),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Accept-Encoding": "identity",
                "User-Agent": "nhcx-adapter-check",
            },
            timeout=PROBE_TIMEOUT,
        )
    except requests.RequestException as e:
        return False, f"{url} unreachable from here: {e}"
    raw = (resp.content or b"")[:PROBE_BODY_LIMIT]
    try:
        ans = json.loads(raw)
    except (ValueError, TypeError):
        ans = None
    got = ans.get("probe_ack") if isinstance(ans, dict) else None
    if not isinstance(got, str) or not got:
        server = resp.headers.get("Server", "") if hasattr(resp, "headers") else ""
        excerpt = raw[:120].decode("utf-8", errors="replace")
        return False, (
            f"{url} answered {resp.status_code} (Server: {server}) without a probe "
            "acknowledgement: the proxy at that URL is not forwarding to this adapter's "
            f"listen address; body: {excerpt!r}"
        )
    if not verify(key, nonce, got):
        return False, (
            f"{url} is an nhcx-adapter, but not one running with this configuration "
            "(different participant or credentials)"
        )
    if resp.status_code != HTTP_OK:
        return False, f"{url} reaches this adapter but answered {resp.status_code}"
    return True, f"{url} reaches this adapter (probe acknowledged)"


def check(gw: Gateway) -> dict:
    """Run the setup checks and the endpoint probe; logs and returns the report, never raises."""
    holder: dict[str, Any] = {}

    def run() -> None:
        try:
            holder["report"] = run_checks(gw)
        except Exception as e:
            holder["report"] = {
                "checks": [{"name": "setup", "ok": False, "detail": explain(e)}],
                "cert": "unknown",
                "participant": None,
            }

    t = threading.Thread(target=run, name="nhcx-check", daemon=True)
    t.start()
    t.join(CHECKS_TIMEOUT)
    report = holder.get("report") or {
        "checks": [
            {"name": "setup", "ok": False, "detail": "timed out after 2 minutes"}
        ],
        "cert": "unknown",
        "participant": None,
    }
    for c in report["checks"]:
        if c["ok"]:
            logger.info("nhcx: setup check %s: %s", c["name"], c["detail"])
        else:
            logger.warning("nhcx: setup check failed %s: %s", c["name"], c["detail"])
    p = report.get("participant")
    if p and p.get("endpointUrl"):
        try:
            ok, detail = test_endpoint(gw.http, p["endpointUrl"], gateway_probe_key(gw))
        except Exception as e:
            ok, detail = False, explain(e)
        report["endpoint"] = {"ok": ok, "detail": detail}
        if ok:
            logger.info("nhcx: registered endpoint verified: %s", detail)
        else:
            logger.warning(
                "nhcx: registered endpoint check failed: %s - NHCX cannot deliver "
                "callbacks until endpoint_url reaches this gateway",
                detail,
            )
    return report


__all__ = [
    "GatewayError",
    "ack",
    "check",
    "healthz",
    "probe_key",
    "readyz",
    "run_checks",
    "test_endpoint",
    "verify",
]
