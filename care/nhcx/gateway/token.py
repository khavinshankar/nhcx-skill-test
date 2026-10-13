"""G3. Session token: one ABDM session per client id, and the authenticated POST."""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
import uuid
from datetime import UTC, datetime
from typing import Any

import requests

from care.nhcx.gateway.errors import GatewayError, clip, retryable_status

logger = logging.getLogger("care.nhcx.gateway")

FRESH_MARGIN = 60.0
HTTP_UNAUTHORIZED = 401


def utc_ms_timestamp(now: datetime | None = None) -> str:
    now = now or datetime.now(UTC)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def _first_string(out: dict, *keys: str) -> str:
    for k in keys:
        v = out.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def _first_number(out: dict, *keys: str) -> float:
    for k in keys:
        v = out.get(k)
        if isinstance(v, bool):
            continue
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            try:
                return float(v.strip())
            except ValueError:
                continue
    return 0.0


class TokenCache:
    """In-memory token map, guarded by one lock (G3D).

    `shared` is an optional Django-cache-like store (`get`/`set`) so the
    refresher in one process (the Celery role) warms the token for the web
    workers; nothing else is persisted.
    """

    def __init__(self, shared: Any = None):
        self.lock = threading.RLock()
        self.tokens: dict[str, tuple[str, float]] = {}
        self.shared = shared

    @staticmethod
    def _shared_key(key: str) -> str:
        return "nhcx:token:" + hashlib.sha256(key.encode()).hexdigest()

    def get(self, key: str) -> tuple[str, float] | None:
        e = self.tokens.get(key)
        if self.shared is not None and (
            e is None or e[1] - time.time() <= FRESH_MARGIN
        ):
            try:
                s = self.shared.get(self._shared_key(key))
            except Exception:
                s = None
            if (
                isinstance(s, (list, tuple))
                and len(s) == 2  # noqa: PLR2004
                and (e is None or s[1] > e[1])
            ):
                e = (s[0], float(s[1]))
                self.tokens[key] = e
        return e

    def put(self, key: str, token: str, expires: float) -> None:
        self.tokens[key] = (token, expires)
        if self.shared is not None:
            try:
                self.shared.set(
                    self._shared_key(key),
                    (token, expires),
                    timeout=max(int(expires - time.time()), 1),
                )
            except Exception:
                logger.warning("nhcx: shared token cache unavailable", exc_info=True)


class AbdmClient:
    """The ABDM client acting as one profile (G2 `identity_for`)."""

    def __init__(self, gateway_ctx: Any, profile: Any):
        self.ctx = gateway_ctx
        self.profile = profile

    @property
    def code(self) -> str:
        return self.profile.code

    @property
    def cfg(self):
        return self.ctx.cfg

    def credentials(self) -> tuple[str, str, str]:
        cid, secret = (
            self.profile.participant.clientId,
            self.profile.participant.clientSecret,
        )
        if cid == "":
            d = self.cfg.participant
            cid, secret = d.clientId, d.clientSecret
        key = cid if cid != "" else "\0" + self.code
        return cid, secret, key

    # ---- tokens ----

    def token(self) -> str:
        cache = self.ctx.tokens
        with cache.lock:
            _, _, key = self.credentials()
            e = cache.get(key)
            if e and e[0] and e[1] - time.time() > FRESH_MARGIN:
                return e[0]
            return self._fetch_locked()

    def refresh_token(self) -> str:
        with self.ctx.tokens.lock:
            return self._fetch_locked()

    def token_info(self) -> tuple[str, float]:
        self.token()
        cache = self.ctx.tokens
        with cache.lock:
            _, _, key = self.credentials()
            return cache.tokens[key]

    def token_valid(self) -> bool:
        cache = self.ctx.tokens
        with cache.lock:
            _, _, key = self.credentials()
            e = cache.get(key)
        return bool(e and e[0] and time.time() < e[1])

    def _fetch_locked(self) -> str:
        cfg = self.cfg
        cid, secret, key = self.credentials()
        started = time.monotonic()
        headers = {"Accept": "application/json"}
        try:
            if cfg.auth_mode == "get-session":
                headers["Content-Type"] = "application/x-www-form-urlencoded"
                kwargs = {
                    "data": {
                        "client_id": cid,
                        "client_secret": secret,
                        "grant_type": "client_credentials",
                    }
                }
            else:
                headers.update(
                    {
                        "Content-Type": "application/json",
                        "REQUEST-ID": str(uuid.uuid4()),
                        "TIMESTAMP": utc_ms_timestamp(),
                        "X-CM-ID": cfg.cmId,
                    }
                )
                kwargs = {
                    "data": json.dumps(
                        {
                            "clientId": cid,
                            "clientSecret": secret,
                            "grantType": "client_credentials",
                        }
                    )
                }
        except (TypeError, ValueError) as e:
            raise GatewayError("TOKEN_REQUEST", "build session request", cause=e) from e
        try:
            resp = self.ctx.http.post(
                cfg.url_sessions,
                headers=headers,
                timeout=cfg.outbound_timeout,
                **kwargs,
            )
        except requests.RequestException as e:
            raise GatewayError(
                "TOKEN_UNREACHABLE",
                "session endpoint unreachable",
                retryable=True,
                cause=e,
            ) from e
        raw = resp.content
        status = resp.status_code
        if not 200 <= status < 300:  # noqa: PLR2004
            err_code = f"TOKEN_HTTP_{status}"
            raise GatewayError(
                err_code,
                "session endpoint rejected the credentials",
                retryable=retryable_status(status),
                status=status,
                body=clip(raw),
            )
        try:
            out = json.loads(raw)
            if not isinstance(out, dict):
                raise ValueError("not an object")
        except ValueError as e:
            raise GatewayError(
                "TOKEN_BAD_JSON",
                "session response is not JSON",
                retryable=True,
                status=status,
                body=clip(raw),
                cause=e,
            ) from e
        token = _first_string(out, "accessToken", "access_token")
        if token == "":
            raise GatewayError(
                "TOKEN_MISSING",
                "session response carried no access token",
                status=status,
            )
        ttl = float(cfg.token_ttl_seconds)
        n = _first_number(out, "expiresIn", "expires_in")
        if n > 0:
            ttl = n
        self.ctx.tokens.put(key, token, time.time() + ttl)
        logger.info(
            "nhcx: session token refreshed participant=%s mode=%s ttl=%s took_ms=%d",
            self.code,
            cfg.auth_mode,
            int(ttl),
            int((time.monotonic() - started) * 1000),
        )
        return token

    # ---- authenticated POST ----

    def post_with_token(
        self, url: str, body: Any, label: str = "CERT_FETCH"
    ) -> tuple[int, bytes]:
        try:
            payload = json.dumps(body)
        except (TypeError, ValueError) as e:
            raise GatewayError("MARSHAL_ERROR", "encode request body", cause=e) from e
        for attempt in (0, 1):
            token = self.token()
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "bearer_auth": "Bearer " + token,
                "Authorization": "Bearer " + token,
            }
            try:
                resp = self.ctx.http.post(
                    url,
                    data=payload,
                    headers=headers,
                    timeout=self.cfg.outbound_timeout,
                )
            except (
                requests.exceptions.InvalidURL,
                requests.exceptions.MissingSchema,
            ) as e:
                err_code = f"{label}_REQUEST"
                raise GatewayError(err_code, "build request", cause=e) from e
            except requests.RequestException as e:
                err_code = f"{label}_UNREACHABLE"
                raise GatewayError(
                    err_code,
                    f"{url} unreachable",
                    retryable=True,
                    cause=e,
                ) from e
            try:
                raw = resp.content
            except Exception as e:
                err_code = f"{label}_READ_ERROR"
                raise GatewayError(
                    err_code, "read response", retryable=True, cause=e
                ) from e
            if resp.status_code == HTTP_UNAUTHORIZED and attempt == 0:
                logger.warning("nhcx: upstream answered 401, refreshing session token")
                self.refresh_token()
                continue
            return resp.status_code, raw
        return resp.status_code, raw  # pragma: no cover


def token_payload(client: AbdmClient, token: str, expires: float) -> dict:
    exp = datetime.fromtimestamp(expires, UTC).replace(microsecond=0)
    return {
        "token": token,
        "token_type": "Bearer",
        "expires_at": exp.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "expires_in": max(int(expires - time.time()), 0),
        "participant": client.code,
    }
