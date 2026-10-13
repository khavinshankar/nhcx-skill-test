"""Gateway error shape shared by G3, G4, G7, G8, G9 and G10 (G3S)."""

from __future__ import annotations

import json
from typing import Any

BODY_CLIP = 4096


def clip(text: Any, limit: int = BODY_CLIP) -> str:
    if text is None:
        return ""
    if isinstance(text, bytes):
        text = text.decode("utf-8", errors="replace")
    text = str(text)
    if len(text) > limit:
        return text[:limit] + "…"
    return text


def json_or_text(raw: Any) -> Any:
    """Upstream body as JSON when it parses, else its clipped text."""
    if raw is None or raw in ("", b""):
        return None
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return clip(raw)


def retryable_status(status: int) -> bool:
    return status >= 500 or status == 429  # noqa: PLR2004


class GatewayError(Exception):
    """`{code, message, retryable, status, body, cause}` (G3S)."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        retryable: bool = False,
        status: int | None = None,
        body: Any = None,
        cause: Any = None,
    ):
        self.code = code
        self.message = message
        self.retryable = retryable
        self.status = status
        self.body = clip(body) if body is not None else None
        self.cause = cause
        super().__init__(str(self))

    def __str__(self) -> str:
        if self.cause:
            return f"{self.code}: {self.message}: {self.cause}"
        return f"{self.code}: {self.message}"

    def to_dict(self) -> dict:
        out = {"code": self.code, "message": self.message, "retryable": self.retryable}
        if self.status is not None:
            out["status"] = self.status
        if self.body is not None:
            out["body"] = self.body
        if self.cause:
            out["cause"] = str(self.cause)
        return out


def as_gateway_error(exc: BaseException) -> GatewayError:
    if isinstance(exc, GatewayError):
        return exc
    return GatewayError("INTERNAL", "internal error", cause=exc)


class GatewayNotConfigured(GatewayError):  # noqa: N818
    """Raised by `get_gateway()` while the configuration cannot be opened (G1D)."""

    def __init__(self, cause: str):
        self.reason = cause
        super().__init__(
            "NOT_CONFIGURED", f"The NHCX gateway is not configured: {cause}"
        )

    def __str__(self) -> str:
        return self.message


class SendError(GatewayError):
    """G7S `SendError`: code, message, retryable, upstream status/body and the ids."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        retryable: bool = False,
        upstream_status: int | None = None,
        upstream_body: Any = None,
        cause: Any = None,
        ledger_id: str | None = None,
        headers: dict | None = None,
    ):
        super().__init__(
            code,
            message,
            retryable=retryable,
            status=upstream_status,
            body=None,
            cause=cause,
        )
        self.upstream_status = upstream_status
        self.upstream_body = (
            json_or_text(upstream_body)
            if isinstance(upstream_body, (str, bytes))
            else upstream_body
        )
        self.ledger_id = ledger_id
        self.txn_id = ledger_id
        self.headers = headers
        h = headers or {}
        self.correlation_id = h.get("x-hcx-correlation_id")
        self.api_call_id = h.get("x-hcx-api_call_id")
        self.request_id = h.get("x-hcx-request_id") or None

    @property
    def names_ids(self) -> bool:
        return self.headers is not None

    @classmethod
    def from_error(
        cls, err: BaseException, *, ledger_id=None, headers=None
    ) -> SendError:
        g = as_gateway_error(err)
        return cls(
            g.code,
            g.message,
            retryable=g.retryable,
            upstream_status=g.status,
            upstream_body=g.body,
            cause=g.cause,
            ledger_id=ledger_id,
            headers=headers,
        )

    def to_dict(self) -> dict:
        out = {"code": self.code, "message": self.message, "retryable": self.retryable}
        if self.upstream_status is not None:
            out["upstream_status"] = self.upstream_status
        if self.upstream_body is not None:
            out["upstream_body"] = self.upstream_body
        if self.headers is not None:
            out["ledger_id"] = self.ledger_id or ""
            out["txn_id"] = self.ledger_id or ""
            out["headers"] = self.headers
            out["correlation_id"] = self.correlation_id
            out["api_call_id"] = self.api_call_id
            if self.request_id:
                out["request_id"] = self.request_id
        return out


class SendInTransactionError(RuntimeError):
    """`gateway.send` called inside a database transaction (G7D, SCAFFOLDING 8)."""
