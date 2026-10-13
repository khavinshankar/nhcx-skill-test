"""The e2e report (T2X): one entry per test and runner, merged into one file."""

from __future__ import annotations

import json
from pathlib import Path

from django.utils import timezone

RESULTS = ("pass", "fail", "blocked", "skipped")


def read(path: Path) -> dict:
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        data = {}
    return data if isinstance(data, dict) else {}


def summary(tests) -> dict:
    out = dict.fromkeys(RESULTS, 0)
    for t in tests:
        if t.get("result") in out:
            out[t["result"]] += 1
    return out


def _order(entry) -> tuple:
    tid = str(entry.get("id") or "")
    digits = "".join(ch for ch in tid if ch.isdigit())
    return (int(digits or 0), entry.get("runner") != "cli")


def merge(path: Path, config: dict, setup_checks=None, entries=()) -> dict:
    """Writes ``entries`` over any earlier entry of the same (id, runner)."""
    data = read(path)
    data["run_at"] = timezone.now().isoformat()
    data["config"] = config
    if setup_checks is not None:
        data["setup_checks"] = setup_checks
    data.setdefault("setup_checks", [])
    keep = {(t.get("id"), t.get("runner")): t for t in data.get("tests") or []}
    for e in entries:
        keep[(e.get("id"), e.get("runner"))] = e
    data["tests"] = sorted(keep.values(), key=_order)
    data["summary"] = summary(data["tests"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str) + "\n")
    return data
