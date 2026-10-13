"""Setup checks run before the first test (T2S, G11)."""

from __future__ import annotations

import urllib.error
import urllib.request


def _row(check, ok, detail="") -> dict:
    return {"check": check, "result": "pass" if ok else "fail", "detail": detail}


def _reachable(url) -> tuple[bool, str]:
    try:
        with urllib.request.urlopen(url, timeout=10) as r:  # noqa: S310
            return r.status < 400, f"{url} answered {r.status}"  # noqa: PLR2004
    except urllib.error.HTTPError as e:
        return False, f"{url} answered {e.code}"
    except (OSError, ValueError) as e:
        return False, f"{url} unreachable: {e}"


def run(conf, *, gui=False) -> list:
    """The G11 checks, the test data and, for the GUI, the screens' address."""
    from care.nhcx.gateway import get_gateway
    from care.nhcx.gateway.checks import check

    rows = []
    try:
        result = check(get_gateway())
    except Exception as e:
        return [_row("gateway", ok=False, detail=f"{type(e).__name__}: {e}")]
    rows.extend(
        _row(c["name"], c["ok"], c.get("detail") or "") for c in result["checks"]
    )
    endpoint = result.get("endpoint") or {}
    rows.append(
        _row("endpoint probe", endpoint.get("ok"), endpoint.get("detail") or "")
    )
    missing = [
        key
        for key in (
            "NHCX_TEST_FACILITY",
            "NHCX_TEST_USER",
            "NHCX_TEST_PASSWORD",
            "NHCX_TEST_DOCTOR",
        )
        if not conf.get(key)
    ]
    rows.append(
        _row(
            "test data",
            not missing,
            "facility, operator and doctor set"
            if not missing
            else "run `nhcx_e2e setup`; missing " + ", ".join(missing),
        )
    )
    rows.append(_adapters(conf))
    if gui:
        ok, detail = _reachable(
            conf.get("NHCX_TEST_APP_URL") or "http://localhost:4000"
        )
        rows.append(_row("screens reachable", ok, detail))
    return rows


EXPECTED_ADAPTERS = {"IRDAI": "kyrocare", "PMJAY": "pmjay"}


def _adapters(conf) -> dict:
    """Each test payer must resolve to its adapter (PAYERS.md), else no desk."""
    from care.nhcx.services import payers

    got = {
        label: payers.adapter_for(conf.get(f"NHCX_TEST_{label}_PAYER")).key
        for label in EXPECTED_ADAPTERS
    }
    wrong = {k: v for k, v in got.items() if v != EXPECTED_ADAPTERS[k]}
    detail = ", ".join(
        f"{conf.get(f'NHCX_TEST_{k}_PAYER')} -> {v}" for k, v in got.items()
    )
    if wrong:
        detail += (
            "; set NHCX_PAYER_ADAPTERS (e.g. "
            f"{conf.get('NHCX_TEST_IRDAI_PAYER').split('@')[0]}=kyrocare)"
        )
    return _row("payer adapters", not wrong, detail)


def failed(rows) -> list:
    return [r for r in rows if r["result"] != "pass"]
