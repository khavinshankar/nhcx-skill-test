"""G1. Embedding: open the gateway inside the application process."""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import requests

from care.nhcx.gateway import beneficiary, checks, receive, send
from care.nhcx.gateway.config import (
    Config,
    ConfigError,
    ParticipantEntry,
    build_profiles,
    load_config,
    validate_serve,
)
from care.nhcx.gateway.errors import GatewayError
from care.nhcx.gateway.headers import normalize_code
from care.nhcx.gateway.ledger import Ledger
from care.nhcx.gateway.registry import CertCache, RegistryClient
from care.nhcx.gateway.token import TokenCache, token_payload

logger = logging.getLogger("care.nhcx.gateway")

TOKEN_INTERVAL = 60
SWEEP_INTERVAL = 3600

ReceiveFn = Callable[[dict, dict], Any]


class Gateway:
    """An open gateway: configuration, profiles, caches, ledger and the C1 callable."""

    def __init__(
        self,
        cfg: Config,
        receive_fn: ReceiveFn,
        *,
        version: str = "embedded",
        http: Any = None,
        token_store: Any = None,
    ):
        self.cfg = cfg
        self.receive = receive_fn
        self.version = version or "embedded"
        self.guests = cfg.guests
        self.profiles = build_profiles(cfg)
        self.http = http if http is not None else requests.Session()
        self.tokens = TokenCache(shared=token_store)
        self.certs = CertCache()
        self.ledger = Ledger(
            cfg.ledger_dir if cfg.ledger_enabled else None,
            enabled=cfg.ledger_enabled,
            store_bodies=cfg.ledger_store_bodies,
            retention_days=cfg.ledger_retention_days,
        )
        self._clients: dict[str, RegistryClient] = {}
        for p in self.profiles:
            self._clients[p.code.lower()] = RegistryClient(self, p)
        self.default_client = RegistryClient(self, self.profiles.default)
        self.registry = beneficiary.BeneficiaryRegistry(self.default_client)
        self.beneficiary = self.registry
        self._stop = threading.Event()
        self._threads: list[threading.Thread] = []

    # ---- identities ----

    def identity_for(self, code: Any) -> RegistryClient:
        c = normalize_code(code)
        if c and c.lower() in self._clients:
            return self._clients[c.lower()]
        return self.default_client

    @property
    def participant_codes(self) -> list[str]:
        return self.profiles.codes()

    # ---- G7 ----

    def parse_outbound(self, path: str, envelope: Any) -> send.OutboundRequest:
        return send.parse_outbound(path, envelope)

    def send(self, path: str, envelope: Any) -> send.SendResult:
        return send.send(self, path, envelope)

    # ---- G3 ----

    def token(self, participant: str | None = None, *, refresh: bool = False) -> dict:
        client = self.default_client
        if participant:
            if self.profiles.by_code(participant) is None:
                raise GatewayError(
                    "UNKNOWN_PARTICIPANT",
                    f"no participant {participant} is configured; this adapter holds "
                    + ", ".join(self.profiles.codes()),
                )
            client = self.identity_for(participant)
        if refresh:
            client.refresh_token()
        tok, expires = client.token_info()
        return token_payload(client, tok, expires)

    def refresh_token(self, participant: str | None = None) -> dict:
        return self.token(participant, refresh=True)

    # ---- G8 ----

    def handle_inbound(
        self, path: str, body: bytes, ip: str = "", request_id: str | None = None
    ) -> receive.InboundAnswer:
        return receive.handle_inbound(self, path, body, ip, request_id)

    # ---- G11 ----

    def healthz(self, method: str = "GET", body: bytes | None = None) -> dict:
        return checks.healthz(self, method, body)

    def readyz(self) -> tuple[int, dict]:
        return checks.readyz(self)

    def check(self) -> dict:
        return checks.check(self)

    # ---- background work (G1) ----

    def refresh_all(self, deadline: float = 30.0) -> int:
        """Ask G3 for a token for every profile, default first; returns failures."""
        failures = 0
        until = time.monotonic() + deadline
        for p in self.profiles:
            if time.monotonic() > until:
                logger.error("nhcx: session token refresh failed: deadline exceeded")
                return failures + 1
            try:
                self.identity_for(p.code).token()
            except Exception as e:
                failures += 1
                logger.error(
                    "nhcx: session token refresh failed participant=%s: %s", p.code, e
                )
        return failures

    def sweep(self, now: datetime | None = None) -> int:
        n = self.ledger.sweep(now or datetime.now(UTC))
        if n > 0:
            logger.info("nhcx: ledger pruned count=%d", n)
        return n

    def _loop(self, fn: Callable[[], Any], interval: float) -> None:
        while not self._stop.is_set():
            try:
                fn()
            except Exception:
                logger.exception("nhcx: background loop failed")
            self._stop.wait(interval)

    def start(self) -> None:
        """Start the token and pruning loops as daemon threads.

        CARE runs these as Celery beat tasks instead (care/nhcx/tasks.py); this is
        for hosts without Celery.
        """
        if self._threads:
            return
        self._stop.clear()
        specs = [("nhcx-token", self.refresh_all, TOKEN_INTERVAL)]
        if self.ledger.enabled:
            specs.append(("nhcx-sweep", self.sweep, SWEEP_INTERVAL))
        for name, fn, interval in specs:
            t = threading.Thread(
                target=self._loop, args=(fn, interval), name=name, daemon=True
            )
            t.start()
            self._threads.append(t)

    def stop(self) -> None:
        self._stop.set()
        for t in self._threads:
            t.join(timeout=5)
        self._threads = []

    def log_startup(self) -> None:
        logger.info(
            "nhcx gateway embedded nhcx=%s participants=%d",
            self.cfg.url_nhcx,
            len(self.profiles.profiles),
        )
        for p in self.profiles:
            logger.info(
                "nhcx: hosting participant code=%s name=%s default=%s",
                p.code,
                p.participant.name,
                p.default,
            )
        if self.guests:
            logger.info("nhcx: hosting guests")


def open_gateway(
    config_path: str,
    receive_fn: ReceiveFn,
    *,
    host: dict[str, str] | None = None,
    guests: bool | None = None,
    version: str = "embedded",
    http: Any = None,
    token_store: Any = None,
) -> Gateway:
    """G1 `open`. No network call; raises ConfigError with the G2 messages."""
    cfg = load_config(config_path)
    held = {c.lower() for c in cfg.codes()}
    for raw_code, name in (host or {}).items():
        code = normalize_code((raw_code or "").strip())
        if code in ("", "@hcx") or code.lower() in held:
            continue
        cfg.participants.append(ParticipantEntry(participantId=code, name=name or ""))
        held.add(code.lower())
    if guests is True:
        cfg.guests = True
    elif guests is False:
        cfg.guests = False
    errs = validate_serve(cfg)
    if errs:
        raise ConfigError(f"{config_path}: " + "\n".join(errs))
    return Gateway(cfg, receive_fn, version=version, http=http, token_store=token_store)


open = open_gateway  # noqa: A001
