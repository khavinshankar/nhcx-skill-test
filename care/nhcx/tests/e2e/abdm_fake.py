"""T19 stand-in for the ABDM biometric and face-auth hosts (NHCX_TEST_ABDM_FAKE=1).

A small HTTP server in a thread of the runner's process: init answers a txnId,
verify a token pair, refresh a new token. Every request is recorded so the test
can read what the application sent. The tokens are made up for the run.
"""

from __future__ import annotations

import json
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TOKEN_SECONDS = 30


class AbdmFake:
    def __init__(self):
        self.calls: list[dict] = []
        self.issued: list[str] = []
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), self._handler())
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def base(self) -> str:
        return f"http://127.0.0.1:{self.server.server_address[1]}"

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.server.shutdown()
        self.server.server_close()

    def token(self) -> str:
        value = f"e2e-fake-token-{uuid.uuid4().hex[:12]}"
        self.issued.append(value)
        return value

    def answer(self, method, path, body) -> tuple[int, dict]:
        txn = str(uuid.uuid4())
        if path in {"/auth/init", "/faceauth/init"}:
            return 200, {"txnId": txn, "message": "stand-in: authentication initiated"}
        if path == "/capture/pid":
            return 200, {"status": "COMPLETE"}
        if path in {"/auth/verify", "/v2/auth/verify"}:
            hint = ""
            for call in reversed(self.calls[:-1]):
                if call["path"] == "/auth/init":
                    hint = (call["body"] or {}).get("loginId") or ""
                    break
            return 200, {
                "authResult": "success",
                "message": "stand-in: verified",
                "tokens": {
                    "token": self.token(),
                    "expiresIn": TOKEN_SECONDS,
                    "refreshToken": f"e2e-fake-refresh-{uuid.uuid4().hex[:12]}",
                    "refreshExpiresIn": 3600,
                },
                "accounts": [{"ABHANumber": hint.replace("-", "")}] if hint else [],
            }
        if method == "GET" and path == "/auth/refresh/token":
            return 200, {"token": self.token(), "expiresIn": TOKEN_SECONDS}
        return 404, {"message": f"stand-in has no {method} {path}"}

    def _handler(self):
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def _serve(self, method):
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length) if length else b""
                try:
                    body = json.loads(raw) if raw else None
                except ValueError:
                    body = None
                path = self.path.split("?", 1)[0]
                fake.calls.append(
                    {
                        "method": method,
                        "path": path,
                        "headers": {k.lower(): v for k, v in self.headers.items()},
                        "body": body,
                    }
                )
                status, out = fake.answer(method, path, body)
                data = json.dumps(out).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_POST(self):
                self._serve("POST")

            def do_GET(self):
                self._serve("GET")

            def log_message(self, *args):
                pass

        return Handler
