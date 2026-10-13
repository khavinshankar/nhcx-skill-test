"""Embedded NHCX gateway (G1 to G11).

The application uses the gateway in-process through `get_gateway()`, which opens
it lazily from `settings.NHCX_GATEWAY_CONFIG` with the C1 receive callable named
by `settings.NHCX_RECEIVE_HANDLER`. Send with `get_gateway().send(path, envelope)`;
`care.nhcx.gateway.send` is the G7 module, not a function.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

from care.nhcx.gateway.errors import (
    GatewayError,
    GatewayNotConfigured,
    SendError,
    SendInTransactionError,
)

logger = logging.getLogger("care.nhcx.gateway")

DEFAULT_RECEIVE_HANDLER = "care.nhcx.callbacks.dispatch.receive"
RETRY_OPEN_SECONDS = 60

_lock = threading.Lock()
_gateway: Any = None
_error: str | None = None
_error_at: float = 0.0


def unmatched_receive(envelope: dict, delivery: dict) -> str:
    """Stand-in C1 while the real one is not importable: every message is `unmatched`."""
    return "unmatched"


class _LazyReceive:
    """Resolves the C1 callable by dotted path on first use, so import order does not matter."""

    def __init__(self, dotted: str):
        self.dotted = dotted or DEFAULT_RECEIVE_HANDLER
        self.fn = None

    def __call__(self, envelope: dict, delivery: dict) -> Any:
        if self.fn is None:
            from django.utils.module_loading import import_string

            try:
                self.fn = import_string(self.dotted)
            except ImportError:
                logger.warning(
                    "nhcx: receive handler %s is not importable; answering unmatched",
                    self.dotted,
                )
                return unmatched_receive(envelope, delivery)
        return self.fn(envelope, delivery)


def _hosted(value: Any) -> dict[str, str]:
    if isinstance(value, dict):
        return {str(k): str(v) for k, v in value.items()}
    out: dict[str, str] = {}
    for raw in str(value or "").split(","):
        item = raw.strip()
        if not item:
            continue
        code, _, name = item.partition("=")
        out[code.strip()] = name.strip()
    return out


def _shared_token_store() -> Any:
    from django.conf import settings
    from django.core.cache import caches

    if not getattr(settings, "NHCX_SHARED_TOKEN_CACHE", True):
        return None
    try:
        return caches["default"]
    except Exception:
        return None


def _open() -> Any:
    from django.conf import settings

    from care.nhcx.gateway.embedding import open_gateway

    path = (getattr(settings, "NHCX_GATEWAY_CONFIG", "") or "").strip()
    if not path:
        msg = "NHCX_GATEWAY_CONFIG is not set"
        raise GatewayNotConfigured(msg)
    gw = open_gateway(
        path,
        _LazyReceive(
            getattr(settings, "NHCX_RECEIVE_HANDLER", DEFAULT_RECEIVE_HANDLER)
        ),
        host=_hosted(getattr(settings, "NHCX_HOSTED_PARTICIPANTS", "")),
        guests=getattr(settings, "NHCX_GUESTS", None),
        version=getattr(settings, "NHCX_VERSION", "") or "embedded",
        token_store=_shared_token_store(),
    )
    gw.log_startup()
    return gw


def get_gateway() -> Any:
    """The open gateway, or raises `GatewayNotConfigured` (code `NOT_CONFIGURED`).

    A failed open is logged and retried at most once a minute, so fixing the
    configuration needs no restart; the rest of the application keeps working.
    """
    global _gateway, _error, _error_at  # noqa: PLW0603
    gw = _gateway
    if gw is not None:
        return gw
    with _lock:
        if _gateway is not None:
            return _gateway
        if _error is not None and time.monotonic() - _error_at < RETRY_OPEN_SECONDS:
            raise GatewayNotConfigured(_error)
        try:
            _gateway = _open()
        except GatewayNotConfigured as e:
            _error, _error_at = e.reason, time.monotonic()
            raise
        except Exception as e:
            _error, _error_at = str(e), time.monotonic()
            logger.error("nhcx: gateway could not be opened: %s", e)
            raise GatewayNotConfigured(_error) from e
        _error = None
        return _gateway


def gateway_status() -> tuple[Any, str | None]:
    """`(gateway, None)` when open, else `(None, cause)`; never raises."""
    try:
        return get_gateway(), None
    except GatewayNotConfigured as e:
        return None, e.reason


def set_gateway(gw: Any) -> None:
    """Install a gateway (tests, or a host that opens it itself)."""
    global _gateway, _error
    with _lock:
        _gateway, _error = gw, None


def reset_gateway() -> None:
    global _gateway, _error, _error_at
    with _lock:
        if _gateway is not None:
            _gateway.stop()
        _gateway, _error, _error_at = None, None, 0.0


__all__ = [
    "GatewayError",
    "GatewayNotConfigured",
    "SendError",
    "SendInTransactionError",
    "gateway_status",
    "get_gateway",
    "reset_gateway",
    "set_gateway",
    "unmatched_receive",
]
