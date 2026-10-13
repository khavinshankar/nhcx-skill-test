"""A17 hook registry (CONTRACT "Shared hooks", A17D).

The send rules live in A4/A5 (services/preauth.py, services/claim.py), which
register their implementations at import (AppConfig.ready imports them).
Before a hook is registered the defaults below answer, so A17 keeps its shape.

Public:
- ``register(name, fn)``: install ``fn`` for a hook name in ``DEFAULTS``.
- ``call(name, *args)``: the registered function's answer, or the default;
  a hook that raises answers its default too (A17: "never raises"), except
  ``next_send``, which answers ``{"refused": "<error text>"}``.

Hooks and defaults:
- ``next_send(claim, leg)`` with leg "preauth" or "claim" -> kind or
  ``{"refused": "<reason>"}``; default ``{"refused": "not available yet"}``.
- ``enhancement_lines(claim)`` -> [line rows]; default ``[]``.
- ``required_documents(claim, stage)`` -> [{code, display, ...}]; default ``[]``.
- ``required_forms(claim, stage)`` -> [{url, title, questions}]; default ``[]``.
- ``extra_headers(claim, purpose)`` -> {header: value}; default ``{}``
  (payer-specific x-hcx headers for A2, e.g. biometric tokens from A18).
"""

import logging

logger = logging.getLogger(__name__)

NOT_AVAILABLE = "not available yet"

DEFAULTS = {
    "next_send": lambda claim, leg: {"refused": NOT_AVAILABLE},
    "enhancement_lines": lambda claim: [],
    "required_documents": lambda claim, stage: [],
    "required_forms": lambda claim, stage: [],
    "extra_headers": lambda claim, purpose: {},
}

_registry: dict = {}


def register(name: str, fn) -> None:
    if name not in DEFAULTS:
        msg = f"unknown NHCX hook {name!r}"
        raise KeyError(msg)
    _registry[name] = fn


def unregister(name: str) -> None:
    _registry.pop(name, None)


def registered(name: str) -> bool:
    return name in _registry


def call(name: str, *args):
    fn = _registry.get(name)
    if fn is None:
        return DEFAULTS[name](*args)
    try:
        return fn(*args)
    except Exception as e:
        logger.exception(
            "nhcx: hook %s failed claim=%s",
            name,
            getattr(args[0], "claim_no", None) if args else None,
        )
        if name == "next_send":
            return {"refused": str(e) or NOT_AVAILABLE}
        return DEFAULTS[name](*args)
