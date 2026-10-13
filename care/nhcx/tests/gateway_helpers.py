"""Shared fixtures for the gateway tests: test keys, a fake HTTP client, a config."""

from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path
from typing import Any

from care.nhcx.gateway.embedding import open_gateway

KEYS = Path(__file__).parent / "fixtures" / "keys"
SCRATCH = Path(__file__).parent / "_scratch"

SESSIONS_URL = "https://sessions.test/v3/sessions"
NHCX_URL = "https://nhcx.test/hcx/v1"
PARTICIPANT_URL = "https://registry.test/participanthcxservice"

FACILITY = "1000000001@hcx"
PAYER = "1000000099@hcx"


def key(name: str) -> str:
    return (KEYS / name).read_text()


class FakeResponse:
    def __init__(
        self, status: int = 200, body: Any = None, headers: dict | None = None
    ):
        self.status_code = status
        if isinstance(body, (bytes, str)):
            self.content = body.encode() if isinstance(body, str) else body
        elif body is None:
            self.content = b""
        else:
            self.content = json.dumps(body).encode()
        self.headers = headers or {}


class FakeHttp:
    """Answers `post(url, ...)` from a per-URL queue (or a default)."""

    def __init__(self):
        self.routes: dict[str, list] = {}
        self.calls: list[dict] = []
        self.session_token = "tok-1"

    def on(self, url: str, *responses) -> None:
        self.routes.setdefault(url, []).extend(responses)

    def post(self, url, data=None, headers=None, timeout=None, **kwargs):
        self.calls.append({"url": url, "data": data, "headers": headers or {}})
        queue = self.routes.get(url)
        if queue:
            r = queue.pop(0) if len(queue) > 1 else queue[0]
            if isinstance(r, BaseException):
                raise r
            if callable(r):
                return r(url, data, headers)
            return r
        if url == SESSIONS_URL:
            return FakeResponse(
                200, {"accessToken": self.session_token, "expiresIn": 1200}
            )
        if url.endswith("/fetch/certs"):
            return FakeResponse(200, {"encryption_cert": key("payer-cert.pem")})
        return FakeResponse(202, {"timestamp": "now"})

    def calls_to(self, suffix: str) -> list[dict]:
        return [c for c in self.calls if c["url"].endswith(suffix)]


def base_config(**overrides) -> dict:
    cfg = {
        "env": "sandbox",
        "publicUrl": "https://care.test/in",
        "participant": {
            "participantId": FACILITY,
            "name": "Test Hospital",
            "clientId": "client-1",
            "clientSecret": "secret-1",
            "privateKey": "@" + str(KEYS / "facility-private.pem"),
        },
        "ledger": {"enabled": True, "dir": "ledger", "retentionDays": 2},
        "urls": {
            "nhcx": NHCX_URL,
            "participant": PARTICIPANT_URL,
            "sessions": SESSIONS_URL,
        },
    }
    for k, v in overrides.items():
        if v is None:
            cfg.pop(k, None)
        else:
            cfg[k] = v
    return cfg


class ScratchDirMixin:
    """A per-test directory inside the project (never /tmp), removed afterwards."""

    def make_scratch(self) -> Path:
        d = SCRATCH / uuid.uuid4().hex
        d.mkdir(parents=True)
        # cleanups run last-in first-out: the folder goes before its parent
        self.addCleanup(_remove_if_empty, SCRATCH)
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        return d

    def write_config(self, data: dict | str, name: str = "nhcx.json") -> Path:
        d = self.make_scratch()
        p = d / name
        p.write_text(data if isinstance(data, str) else json.dumps(data))
        return p

    def open_gateway(self, receive=None, http=None, **overrides):
        path = self.write_config(base_config(**overrides))
        self.http = http or FakeHttp()
        self.received: list = []

        def default_receive(envelope, delivery):
            self.received.append((envelope, delivery))
            return {"outcome": "settled"}

        return open_gateway(str(path), receive or default_receive, http=self.http)


def _remove_if_empty(p: Path) -> None:
    try:
        p.rmdir()
    except OSError:
        pass
