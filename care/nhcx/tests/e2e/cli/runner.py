"""The CLI runner (T2L): runs scenarios in the application's process.

Every action goes through the application's own API views (the services the
screens use) with an in-process client signed in as the test operator; the
payer's side goes through the payer driver. Nothing here calls the gateway
over HTTP.
"""

from __future__ import annotations

import time
import traceback

from django.utils import timezone
from rest_framework.test import APIClient

HTTP_OK = 200
HTTP_REDIRECT = 300
TICK = 3
POLL_EVERY = 10


class StepFailed(Exception):  # noqa: N818
    def __init__(self, what, got, cause="ours"):
        super().__init__(f"{what}: {got}")
        self.what, self.got, self.cause = what, got, cause


class Blocked(Exception):  # noqa: N818
    def __init__(self, detail, cause="sandbox", result="blocked"):
        super().__init__(detail)
        self.detail, self.cause, self.result = detail, cause, result


class Refused(Exception):  # noqa: N818
    def __init__(self, status, error, body):
        super().__init__(f"{status}: {error}")
        self.status, self.error, self.body = status, error, body


def _short(value, n=160) -> str:
    text = str(value)
    return text if len(text) <= n else text[: n - 1] + "…"


class Ctx:
    """One test attempt: its client, its claims, its steps and its record."""

    def __init__(self, conf, test_id, runner="cli", out=print):
        from care.facility.models import Facility
        from care.users.models import User

        self.conf = conf
        self.id = test_id
        self.runner = runner
        self.out = out
        self.facility = Facility.objects.get(external_id=conf.get("NHCX_TEST_FACILITY"))
        self.user = User.objects.get(username=conf.get("NHCX_TEST_USER"))
        self.doctor = User.objects.get(username=conf.get("NHCX_TEST_DOCTOR"))
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.base = f"/api/v1/facility/{self.facility.external_id}/nhcx/"
        self.claims: list[str] = []
        self.correlation_ids: list[str] = []
        self.decisions: list[dict] = []
        self.steps: list[dict] = []
        self.skipped_checks: list[str] = []
        self.wait = conf.int("NHCX_TEST_WAIT_SECONDS")
        self.poll_after = conf.int("NHCX_TEST_POLL_AFTER_SECONDS")

    # ---- recording ----

    def step(self, what, got, result="pass"):
        at = timezone.localtime().strftime("%H:%M:%S")
        self.steps.append(
            {"at": at, "what": what, "result": result, "got": _short(got, 400)}
        )
        self.out(
            f"{at} {self.id} {self.runner} {result.upper():4} {what:44} -> {_short(got)}"
        )

    def fail(self, what, got, cause="ours"):
        self.step(what, got, "fail")
        raise StepFailed(what, got, cause)

    def check(self, ok, what, got, cause="ours"):
        if not ok:
            self.fail(what, got, cause)
        self.step(what, got)

    def skip(self, what, why):
        self.step(what, why, "skipped")
        self.skipped_checks.append(f"{what}: {why}")

    def corr(self, *ids):
        for c in ids:
            if c and c not in self.correlation_ids:
                self.correlation_ids.append(str(c))

    # ---- the application's API ----

    def api(self, method, path, data=None, *, multipart=False):
        url = self.base + path
        fn = getattr(self.client, method.lower())
        if multipart:
            resp = fn(url, data or {}, format="multipart")
        elif method.upper() == "GET":
            resp = fn(url, data or {})
        else:
            resp = fn(url, data or {}, format="json")
        body = getattr(resp, "data", None)
        if body is None:
            try:
                body = resp.json()
            except ValueError:
                body = {}
        if not HTTP_OK <= resp.status_code < HTTP_REDIRECT or (
            isinstance(body, dict) and body.get("ok") is False
        ):
            error = body.get("error") if isinstance(body, dict) else body
            raise Refused(resp.status_code, error or body, body)
        return body

    def send(self, what, method, path, data=None, *, multipart=False):
        """An action that must be accepted; a refusal fails the step."""
        try:
            return self.api(method, path, data, multipart=multipart)
        except Refused as e:
            cause = "sandbox" if _sandbox_text(e.error) else "ours"
            self.fail(what, f"refused {e.status}: {e.error}", cause)
        return None

    def state(self, claim_id) -> dict:
        return self.api("GET", f"claims/{claim_id}/state/")

    def claim(self, claim_id):
        from care.nhcx.models import Claim

        return Claim.objects.get(external_id=claim_id)

    # ---- waiting (T2X) ----

    def wait_for(self, what, claim_id, ready, corr=None, *, seconds=None):
        """Waits for ``ready(claim)`` (callbacks first, polls after a while).

        Returns (value, how) where how is "callback" or "poll".
        """
        seconds = seconds or self.wait
        start = time.monotonic()
        polled_at = None
        how = "callback"
        while True:
            claim = self.claim(claim_id)
            value = ready(claim)
            if value:
                return value, how
            elapsed = time.monotonic() - start
            if elapsed > seconds:
                c = corr(claim) if callable(corr) else corr
                ledger = ledger_ids(c)
                self.fail(
                    what,
                    f"nothing after {seconds}s; correlation {c or '-'}, "
                    f"ledger {', '.join(ledger) or '-'}",
                    "sandbox",
                )
            if elapsed > self.poll_after and (
                polled_at is None or time.monotonic() - polled_at > POLL_EVERY
            ):
                polled_at = time.monotonic()
                how = "poll"
                try:
                    self.state(claim_id)
                except Refused:
                    pass
            time.sleep(TICK)

    # ---- the report entry ----

    def entry(self, result, cause="", detail="", attempts=1) -> dict:
        ledger = []
        for c in self.correlation_ids:
            ledger += [i for i in ledger_ids(c) if i not in ledger]
        return {
            "id": self.id,
            "runner": self.runner,
            "claim": ", ".join(self.claims),
            "correlation_ids": list(self.correlation_ids),
            "ledger_ids": ledger,
            "decisions": self.decisions,
            "steps": self.steps,
            "result": result,
            "cause": cause,
            "detail": detail,
            "attempts": attempts,
        }


SANDBOX_MARKERS = (
    "PAYR-",
    "NHCX-",
    "timed out",
    "unreachable",
    "the payer service returned 5",
    "Service Unavailable",
    "Bad Gateway",
)


def _sandbox_text(text) -> bool:
    return any(m.lower() in str(text).lower() for m in SANDBOX_MARKERS)


def ledger_ids(correlation_id) -> list:
    if not correlation_id:
        return []
    try:
        from care.nhcx.gateway import get_gateway

        thread = get_gateway().ledger.thread(str(correlation_id))
    except Exception:
        return []
    msgs = (thread or {}).get("messages") or []
    return [
        str(m.get("id") or m.get("api_call_id"))
        for m in msgs
        if m.get("id") or m.get("api_call_id")
    ]


def run_one(conf, scenario, out=print, attempts_max=3):
    """Runs one scenario up to three times; returns its report entry."""
    entry = None
    for attempt in range(1, attempts_max + 1):
        ctx = Ctx(conf, scenario.id, "cli", out)
        retry = False
        try:
            scenario.run(ctx)
            if ctx.skipped_checks and not any(s["result"] == "fail" for s in ctx.steps):
                entry = ctx.entry(
                    "pass",
                    detail="skipped checks: " + "; ".join(ctx.skipped_checks),
                    attempts=attempt,
                )
            else:
                entry = ctx.entry("pass", attempts=attempt)
        except Blocked as e:
            ctx.step("blocked", e.detail, e.result)
            entry = ctx.entry(e.result, e.cause, e.detail, attempt)
        except StepFailed as e:
            entry = ctx.entry("fail", e.cause, f"{e.what}: {e.got}", attempt)
            retry = e.cause == "sandbox"
        except Exception as e:
            tb = traceback.format_exc(limit=6)
            ctx.step("error", f"{type(e).__name__}: {e}", "fail")
            entry = ctx.entry("fail", "ours", f"{type(e).__name__}: {e}\n{tb}", attempt)
        if not retry or attempt == attempts_max:
            break
        out(
            f"{timezone.localtime():%H:%M:%S} {scenario.id} cli retry ({entry['detail'][:120]})"
        )
    return entry
