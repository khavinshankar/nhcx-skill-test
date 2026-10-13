"""G2. Configuration and participants."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from care.nhcx.gateway import crypto
from care.nhcx.gateway.headers import normalize_code

DEFAULT_MAX_BODY = 100 * 1024 * 1024
DEFAULT_TIMEOUT = 30
DEFAULT_TOKEN_TTL = 1200
DEFAULT_CERT_HOURS = 24
DEFAULT_LEDGER_DIR = "data/ledger"

ENV_TABLE = {
    "sandbox": {
        "nhcx": "https://apisbx.abdm.gov.in/hcx/v1",
        "participant": "https://apisbx.abdm.gov.in/pmjay/sbxhcx/participanthcxservice",
        "sessions": "https://dev.abdm.gov.in/api/hiecm/gateway/v3/sessions",
        "cmId": "sbx",
    },
    "production": {
        "nhcx": "",
        "participant": "https://apisprod.nha.gov.in/pmjay/hcx/participanthcxservice",
        "sessions": "https://apis.abdm.gov.in/api/hiecm/gateway/v3/sessions",
        "cmId": "abdm",
    },
}

ENV_OVERRIDES = (
    ("NHCX_ENV", ("env",)),
    ("NHCX_URL", ("urls", "nhcx")),
    ("NHCX_PARTICIPANT_URL", ("urls", "participant")),
    ("NHCX_SESSIONS_URL", ("urls", "sessions")),
    ("NHCX_PUBLIC_URL", ("publicUrl",)),
    ("NHCX_CM_ID", ("cmId",)),
)

KEY_HINT = (
    "  generate one with: openssl genpkey -algorithm RSA -pkeyopt "
    "rsa_keygen_bits:2048 -out nhcx-private.pem"
)

# Strict schema. `None` accepts any JSON value: the standalone-only keys the
# embedded gateway carries but neither reads nor validates (G2D).
_ANY = None
_PARTICIPANT = {
    "participantId": str,
    "name": str,
    "clientId": str,
    "clientSecret": str,
    "privateKey": str,
    "callback": _ANY,
    "callbackUrl": _ANY,
}
_SCHEMA = {
    "env": str,
    "publicUrl": str,
    "cmId": str,
    "participant": _PARTICIPANT,
    "participants": [_PARTICIPANT],
    "guests": {"callback": _ANY},
    "ledger": {
        "enabled": bool,
        "dir": str,
        "retentionDays": int,
        "storeBodies": bool,
    },
    "certs": {"cacheHours": (int, float), "refuseSelfKey": bool},
    "outboundTimeoutSeconds": (int, float),
    "maxBodyBytes": int,
    "auth": {"mode": str, "tokenTtlSeconds": int},
    "urls": {"nhcx": str, "participant": str, "sessions": str},
    "log": {"level": str, "format": _ANY},
    "callback": _ANY,
    "apiKey": str,
    "requireApiKey": _ANY,
    "listen": _ANY,
    "tls": _ANY,
    "panel": _ANY,
    "certificate": _ANY,
}

_VAR_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


class ConfigError(Exception):
    pass


def _check(value: Any, schema: Any, where: str) -> None:
    """Reject unknown keys and wrong types. `$comment` keys are allowed anywhere."""
    if schema is _ANY:
        return
    if isinstance(schema, dict):
        if not isinstance(value, dict):
            msg = f"{where or 'config'}: expected an object"
            raise ConfigError(msg)
        for k, v in value.items():
            if k.startswith("$comment"):
                continue
            if k not in schema:
                msg = f'unknown field "{k}"' + (f" in {where}" if where else "")
                raise ConfigError(msg)
            _check(v, schema[k], f"{where}.{k}" if where else k)
        return
    if isinstance(schema, list):
        if not isinstance(value, list):
            msg = f"{where}: expected an array"
            raise ConfigError(msg)
        for i, item in enumerate(value):
            _check(item, schema[0], f"{where}[{i}]")
        return
    types = schema if isinstance(schema, tuple) else (schema,)
    if value is None:
        return
    if isinstance(value, bool) and bool not in types:
        msg = f"{where}: wrong type"
        raise ConfigError(msg)
    if not isinstance(value, types):
        msg = f"{where}: wrong type"
        raise ConfigError(msg)


@dataclass
class ParticipantEntry:
    participantId: str = ""  # noqa: N815
    name: str = ""
    clientId: str = ""  # noqa: N815
    clientSecret: str = ""  # noqa: N815
    privateKey: str = ""  # noqa: N815

    @classmethod
    def from_dict(cls, d: dict | None) -> ParticipantEntry:
        d = d or {}
        return cls(
            participantId=d.get("participantId") or "",
            name=d.get("name") or "",
            clientId=d.get("clientId") or "",
            clientSecret=d.get("clientSecret") or "",
            privateKey=d.get("privateKey") or "",
        )


@dataclass
class Config:
    path: str = ""
    env: str = ""
    publicUrl: str = ""  # noqa: N815
    cmId: str = ""  # noqa: N815
    participant: ParticipantEntry = field(default_factory=ParticipantEntry)
    participants: list[ParticipantEntry] = field(default_factory=list)
    guests: bool = False
    ledger_enabled: bool = True
    ledger_dir: str = ""
    ledger_retention_days: int = 0
    ledger_store_bodies: bool = True
    cert_cache_hours: float = 0
    refuse_self_key: bool | None = None
    outbound_timeout: float = 0
    max_body_bytes: int = 0
    auth_mode: str = ""
    token_ttl_seconds: int = 0
    url_nhcx: str = ""
    url_participant: str = ""
    url_sessions: str = ""
    log_level: str = ""
    api_key: str = ""

    def all_participants(self) -> list[ParticipantEntry]:
        out = [self.participant]
        d = self.participant
        for p in self.participants:
            q = ParticipantEntry(**p.__dict__)
            if q.clientId == "" and q.clientSecret == "":
                q.clientId, q.clientSecret = d.clientId, d.clientSecret
            if q.privateKey.strip() == "":
                q.privateKey = d.privateKey
            out.append(q)
        return out

    def codes(self) -> list[str]:
        return [p.participantId for p in self.all_participants() if p.participantId]


def _expand(raw: str) -> tuple[str, list[str]]:
    missing: list[str] = []

    def sub(m: re.Match) -> str:
        name = m.group(1)
        if name not in os.environ:
            if name not in missing:
                missing.append(name)
            return ""
        return json.dumps(os.environ[name])[1:-1]

    return _VAR_RE.sub(sub, raw), missing


def _num(v: Any, default: float) -> Any:
    return (
        v
        if isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0
        else default
    )


def load_config(path: str | os.PathLike) -> Config:
    path = str(path)
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except OSError as e:
        msg = f"read config: {e}"
        raise ConfigError(msg) from e
    text, missing = _expand(raw)
    if missing:
        msg = f"{path}: environment variable(s) not set: {', '.join(missing)}"
        raise ConfigError(msg)
    try:
        data = json.loads(text)
        _check(data, _SCHEMA, "")
    except (ValueError, ConfigError) as e:
        msg = f"{path}: parse config: {e}"
        raise ConfigError(msg) from e

    for var, fld in ENV_OVERRIDES:
        if var in os.environ:
            target = data
            for k in fld[:-1]:
                target = target.setdefault(k, {})
            target[fld[-1]] = os.environ[var].strip()

    cfg = _apply_defaults(path, data)

    base = Path(path).resolve().parent
    entries = [("participant", cfg.participant)] + [
        (f"participants[{i}]", p) for i, p in enumerate(cfg.participants)
    ]
    for label, entry in entries:
        key = entry.privateKey.strip()
        if key.startswith("@"):
            p = Path(key[1:])
            if not p.is_absolute():
                p = base / p
            try:
                entry.privateKey = p.read_text(encoding="utf-8")
            except OSError as e:
                msg = f"{label}.privateKey: {e}"
                raise ConfigError(msg) from e

    errors = validate(cfg)
    if errors:
        raise ConfigError(f"{path}: " + "\n".join(errors))
    return cfg


def _apply_defaults(path: str, data: dict) -> Config:
    ledger = data.get("ledger") or {}
    certs = data.get("certs") or {}
    auth = data.get("auth") or {}
    urls = data.get("urls") or {}
    log = data.get("log") or {}
    env = (data.get("env") or "").strip().lower() or "sandbox"
    table = ENV_TABLE["production" if env == "production" else "sandbox"]
    ledger_dir = (ledger.get("dir") or "").strip() or DEFAULT_LEDGER_DIR
    if not Path(ledger_dir).is_absolute():
        ledger_dir = str(Path(path).resolve().parent / ledger_dir)
    retention = ledger.get("retentionDays") or 0
    cfg = Config(
        path=path,
        env=env,
        publicUrl=(data.get("publicUrl") or "").strip(),
        cmId=(data.get("cmId") or "").strip() or table["cmId"],
        participant=ParticipantEntry.from_dict(data.get("participant")),
        participants=[
            ParticipantEntry.from_dict(p) for p in data.get("participants") or []
        ],
        guests=isinstance(data.get("guests"), dict),
        ledger_enabled=ledger.get("enabled") is not False,
        ledger_dir=ledger_dir,
        ledger_retention_days=max(retention, 0),
        ledger_store_bodies=ledger.get("storeBodies") is not False,
        cert_cache_hours=_num(certs.get("cacheHours"), DEFAULT_CERT_HOURS),
        refuse_self_key=certs.get("refuseSelfKey"),
        outbound_timeout=_num(data.get("outboundTimeoutSeconds"), DEFAULT_TIMEOUT),
        max_body_bytes=_num(data.get("maxBodyBytes"), DEFAULT_MAX_BODY),
        auth_mode=(auth.get("mode") or "").strip() or "sessions",
        token_ttl_seconds=_num(auth.get("tokenTtlSeconds"), DEFAULT_TOKEN_TTL),
        url_nhcx=(urls.get("nhcx") or "").strip() or table["nhcx"],
        url_participant=(urls.get("participant") or "").strip() or table["participant"],
        url_sessions=(urls.get("sessions") or "").strip(),
        log_level=(log.get("level") or "").strip() or "info",
        api_key=(data.get("apiKey") or "").strip(),
    )
    if cfg.refuse_self_key is None:
        cfg.refuse_self_key = env == "production"
    if cfg.url_sessions == "":
        cfg.url_sessions = (
            cfg.url_participant.rstrip("/") + "/get/session"
            if cfg.auth_mode == "get-session"
            else table["sessions"]
        )
    for p in [cfg.participant, *cfg.participants]:
        p.participantId = normalize_code(p.participantId.strip())
    return cfg


def url_error(u: str) -> str | None:
    if not u:
        return "is required"
    try:
        parsed = urlparse(u)
    except ValueError:
        parsed = None
    if parsed is None or parsed.scheme not in ("http", "https") or not parsed.netloc:
        return f'"{u}" is not an absolute http(s) URL'
    return None


def validate(cfg: Config) -> list[str]:  # noqa: PLR0912
    errs: list[str] = []
    if cfg.env not in ("sandbox", "production"):
        errs.append(f'env must be "sandbox" or "production", got "{cfg.env}"')
    d = cfg.participant
    if not d.participantId:
        errs.append("participant.participantId is required")
    if not d.clientId or not d.clientSecret:
        errs.append("participant.clientId and participant.clientSecret are required")
    if not d.privateKey.strip():
        errs.append(
            "participant.privateKey is required (PEM, base64 PEM, or @file)\n"
            + KEY_HINT
        )
    else:
        try:
            crypto.parse_private_key(d.privateKey)
        except crypto.CryptoError as e:
            errs.append(f"participant.privateKey is not a valid RSA private key: {e}")
    seen: dict[str, int] = {}
    for i, p in enumerate(cfg.participants):
        code = p.participantId
        if not code:
            errs.append(f"participants[{i}].participantId is required")
        else:
            low = code.lower()
            if d.participantId and low == d.participantId.lower():
                errs.append(
                    f"participants[{i}].participantId {code} duplicates participant.participantId"
                )
            elif low in seen:
                errs.append(
                    f"participants[{i}].participantId {code} duplicates participants[{seen[low]}]"
                )
            else:
                seen[low] = i
        if p.privateKey.strip():
            try:
                crypto.parse_private_key(p.privateKey)
            except crypto.CryptoError as e:
                errs.append(
                    f"participants[{i}].privateKey is not a valid RSA private key: {e}"
                )
        if bool(p.clientId) != bool(p.clientSecret):
            errs.append(
                f"participants[{i}]: clientId and clientSecret must be set together "
                "(or both left blank to inherit)"
            )
    if cfg.auth_mode not in ("sessions", "get-session"):
        errs.append(
            f'auth.mode must be "sessions" or "get-session", got "{cfg.auth_mode}"'
        )
    for name, u in (
        ("urls.nhcx", cfg.url_nhcx),
        ("urls.participant", cfg.url_participant),
        ("urls.sessions", cfg.url_sessions),
    ):
        e = url_error(u)
        if e:
            errs.append(f"{name}: {e}")
    if cfg.log_level.lower() not in ("debug", "info", "warn", "warning", "error"):
        errs.append(
            f'log.level must be debug, info, warn or error, got "{cfg.log_level}"'
        )
    return errs


def validate_serve(cfg: Config) -> list[str]:
    if cfg.publicUrl:
        e = url_error(cfg.publicUrl)
        if e:
            return [f"publicUrl: {e}"]
    return []


@dataclass
class Profile:
    participant: ParticipantEntry
    key: Any
    default: bool

    @property
    def code(self) -> str:
        return self.participant.participantId

    @property
    def public_key(self) -> Any:
        return self.key.public_key()


class Profiles:
    def __init__(self, profiles: list[Profile]):
        self.profiles = profiles
        self.default = profiles[0]
        self._index = {p.code.lower(): p for p in profiles if p.code}

    def __iter__(self):
        return iter(self.profiles)

    def codes(self) -> list[str]:
        return [p.code for p in self.profiles if p.code]

    def by_code(self, code: Any) -> Profile | None:
        c = normalize_code(code)
        return self._index.get(c.lower()) if c else None

    def resolve(self, code: Any) -> Profile:
        return self.by_code(code) or self.default

    def is_local(self, code: Any) -> bool:
        return self.by_code(code) is not None

    def owns_key(self, public_key: Any) -> bool:
        if public_key is None:
            return False
        return any(
            crypto.public_numbers_equal(p.public_key, public_key) for p in self.profiles
        )


def build_profiles(cfg: Config) -> Profiles:
    parsed: dict[str, Any] = {}
    out: list[Profile] = []
    for i, entry in enumerate(cfg.all_participants()):
        label = "participant" if i == 0 else f"participants[{i - 1}]"
        key = parsed.get(entry.privateKey)
        if key is None:
            try:
                key = crypto.parse_private_key(entry.privateKey)
            except crypto.CryptoError as e:
                msg = f"{label}.privateKey: {e}"
                raise ConfigError(msg) from e
            parsed[entry.privateKey] = key
        out.append(Profile(participant=entry, key=key, default=i == 0))
    return Profiles(out)
