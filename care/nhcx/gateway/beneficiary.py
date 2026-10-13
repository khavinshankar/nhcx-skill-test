"""G10. Beneficiary registry: policy search and ABHA link pass-through."""

from __future__ import annotations

import json
from typing import Any

from care.nhcx.gateway.errors import GatewayError


def _s(v: Any) -> str:
    return v.strip() if isinstance(v, str) else ""


class BeneficiaryRegistry:
    """Runs as the default participant, whichever facility asks (G10D)."""

    def __init__(self, client: Any):
        self.client = client

    def post_registry(self, path: str, body: Any) -> dict:
        status, raw = self.client.post_registry(path, body)
        try:
            parsed = json.loads(raw)
        except (ValueError, TypeError):
            text = (
                raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
            )
            parsed = {"error": text or ""}
        return {"status": status, "body": parsed}

    def policies_search(self, query: dict) -> dict:
        query = query or {}
        kind, value = _s(query.get("identifiertype")), _s(query.get("identifiervalue"))
        if kind == "":
            if _s(query.get("mobile")):
                kind, value = "MobileNo", _s(query.get("mobile"))
            elif _s(query.get("abhaNo")):
                kind, value = "AbhaNumber", _s(query.get("abhaNo"))
        if value == "":
            raise GatewayError(
                "NO_IDENTIFIER", "identifiervalue (or mobile / abhaNo) is required"
            )
        return self.post_registry(
            "participant/get/policies",
            {"identifiertype": kind, "identifiervalue": value},
        )

    def abha_link(self, body: Any) -> dict:
        return self.post_registry("participant/link/abha/policy", body)

    def abha_delink(self, body: Any) -> dict:
        return self.post_registry("participant/delink/abha/policy", body)
