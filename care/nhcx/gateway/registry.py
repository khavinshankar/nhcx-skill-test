"""G4. Registry and certificates."""

from __future__ import annotations

import json
import logging
import threading
import time
from typing import Any

from care.nhcx.gateway import crypto
from care.nhcx.gateway.errors import GatewayError, clip, retryable_status
from care.nhcx.gateway.headers import normalize_code, same_code
from care.nhcx.gateway.token import AbdmClient

logger = logging.getLogger("care.nhcx.gateway")


class CertCache:
    """Shared by every profile; keyed by lowercased code. Failures are never cached."""

    def __init__(self):
        self.lock = threading.Lock()
        self.entries: dict[str, dict] = {}


def _first(rec: dict, *keys: str) -> str:
    for k in keys:
        v = rec.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def _code_of(rec: Any) -> str:
    if not isinstance(rec, dict):
        return ""
    return _first(rec, "participant_code", "participantcode", "participantid")


def _ok(status: int) -> bool:
    return 200 <= status < 300  # noqa: PLR2004


def _parse_object(raw: bytes) -> dict | None:
    try:
        out = json.loads(raw)
    except (ValueError, TypeError):
        return None
    return out if isinstance(out, dict) else None


class RegistryClient(AbdmClient):
    def _registry_url(self, path: str) -> str:
        return self.cfg.url_participant.rstrip("/") + "/" + path.lstrip("/")

    def certificate(self, code: Any) -> tuple[Any, str]:
        code = normalize_code(code)
        if code == "":
            raise GatewayError("NO_RECIPIENT", "participant code is empty")
        cache = self.ctx.certs
        with cache.lock:
            entry = cache.entries.get(code.lower())
        if entry and time.time() < entry["expires"]:
            return entry["key"], entry["pem"]
        return self.fetch_certificate(code)

    def fetch_certificate(self, code: Any) -> tuple[Any, str]:
        code = normalize_code(code)
        if code == "":
            raise GatewayError("NO_RECIPIENT", "participant code is empty")
        status, raw = self.post_with_token(
            self._registry_url("/fetch/certs"), {"participantid": code}, "CERT_FETCH"
        )
        if not _ok(status):
            err_code = f"CERT_FETCH_HTTP_{status}"
            raise GatewayError(
                err_code,
                f"participant registry refused the certificate lookup for {code}",
                retryable=retryable_status(status),
                status=status,
                body=clip(raw),
            )
        out = _parse_object(raw)
        if out is None:
            raise GatewayError(
                "CERT_FETCH_BAD_JSON",
                "registry response is not JSON",
                retryable=True,
                status=status,
                body=clip(raw),
            )
        pem = _first(out, "encryption_cert", "encryptionCert", "cert")
        if pem == "":
            raise GatewayError(
                "CERT_NOT_FOUND",
                f"registry returned no encryption certificate for {code}",
            )
        try:
            pub = crypto.parse_public_key(pem)
        except crypto.CryptoError as e:
            raise GatewayError(
                "CERT_NOT_FOUND",
                f"registry returned no usable certificate for {code}: "
                + json.dumps(pem[:120], ensure_ascii=False),
                cause=e,
            ) from e
        profiles = self.ctx.profiles
        if profiles.owns_key(pub) and not profiles.is_local(code):
            if self.cfg.refuse_self_key:
                raise GatewayError(
                    "SELF_ENCRYPTION_KEY",
                    f"registry certificate for {code} is this adapter's own key; "
                    "a payload encrypted with it would be unreadable at the far end",
                )
            logger.warning(
                "nhcx: registry certificate is this adapter's own key participant=%s",
                code,
            )
        with self.ctx.certs.lock:
            self.ctx.certs.entries[code.lower()] = {
                "pem": pem,
                "key": pub,
                "expires": time.time() + self.cfg.cert_cache_hours * 3600,
            }
        logger.info("nhcx: certificate fetched participant=%s", code)
        return pub, pem

    def forget_certificate(self, code: Any) -> None:
        with self.ctx.certs.lock:
            self.ctx.certs.entries.pop(normalize_code(code).lower(), None)

    def own_key(self) -> Any:
        return self.profile.public_key if self.profile else None

    def fetch_participant(self, code: Any) -> dict:
        code = normalize_code(code)
        status, raw = self.post_with_token(
            self._registry_url("/participant/search"),
            {"participant_code": code, "participantcode": code, "participantid": code},
            "CERT_FETCH",
        )
        if not _ok(status):
            err_code = f"PARTICIPANT_HTTP_{status}"
            raise GatewayError(
                err_code,
                f"participant registry refused the search for {code}",
                retryable=retryable_status(status),
                status=status,
                body=clip(raw),
            )
        out = _parse_object(raw)
        if out is None:
            raise GatewayError(
                "PARTICIPANT_BAD_JSON",
                "registry response is not JSON",
                status=status,
                body=clip(raw),
            )
        rec: Any = out
        if isinstance(out.get("participants"), list):
            items = out["participants"]
            rec = next((r for r in items if same_code(_code_of(r), code)), None)
            if rec is None and items:
                rec = items[0]
        if rec is None or _code_of(rec) == "":
            raise GatewayError(
                "PARTICIPANT_NOT_FOUND", f"registry has no record for {code}"
            )
        roles = (
            [r for r in rec.get("roles") or [] if isinstance(r, str)]
            if isinstance(rec.get("roles"), list)
            else []
        )
        if not roles and isinstance(rec.get("role_code"), list):
            roles = [r for r in rec["role_code"] if isinstance(r, str)]
        return {
            "code": normalize_code(_code_of(rec)),
            "name": _first(rec, "participant_name", "participantname", "name"),
            "status": _first(rec, "status"),
            "endpointUrl": _first(rec, "endpoint_url", "endpointurl", "endpointUrl"),
            "roles": roles,
            "raw": rec,
        }

    def post_registry(self, path: str, body: Any) -> tuple[int, bytes]:
        return self.post_with_token(self._registry_url(path), body, "CERT_FETCH")
