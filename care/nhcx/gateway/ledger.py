"""G9. Ledger: one JSON file per message under dated folders, indexed in memory.

Multi-process: CARE runs several web workers and a Celery worker against one
ledger directory. An `flock` on `<dir>/.lock` serialises id allocation, entry
writes and index appends; each process re-reads what the others appended to the
`index.jsonl` files (tracked per file by byte offset) before every read and
before allocating an id, and drops day folders another process pruned.
"""

from __future__ import annotations

import contextlib
import fcntl
import json
import logging
import os
import re
import shutil
import threading
from bisect import insort
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from care.nhcx.gateway.errors import GatewayError
from care.nhcx.gateway.headers import (
    clean_path,
    entity_type,
    is_response_path,
    same_code,
)

logger = logging.getLogger("care.nhcx.gateway")

ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUV"
ID_LEN = 8
LEGACY_ID_MIN = 24
RELATED_LIMIT = 500
LIST_MAX = 500
LIST_DEFAULT = 200
DAY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ID_RE = re.compile(r"^[0-9A-V]{8}$")
LEGACY_RE = re.compile(r"^\d{8}[A-Za-z0-9_-]{16,}$")

SUMMARY_FIELDS = (
    "id",
    "direction",
    "created_at",
    "path",
    "entity",
    "action",
    "kind",
    "format",
    "sender",
    "recipient",
    "correlation_id",
    "api_call_id",
    "request_id",
    "workflow_id",
    "hcx_status",
    "status",
    "error",
    "redelivery",
    "duration_ms",
)
ROW_FIELDS = (
    "id",
    "direction",
    "status",
    "sender",
    "recipient",
    "correlation_id",
    "api_call_id",
)


def b32(n: int, width: int) -> str:
    out = ""
    while n > 0:
        out = ALPHABET[n % 32] + out
        n //= 32
    return out.rjust(width, "0")


def unb32(s: str) -> int:
    n = 0
    for ch in s:
        n = n * 32 + ALPHABET.index(ch)
    return n


def day_code(t: datetime) -> str:
    t = t.astimezone(UTC)
    return b32((t.year % 100) * 10000 + t.month * 100 + t.day, 4)


def day_of_id(entry_id: str) -> str | None:
    """`YYYY-MM-DD` folder of an id (either scheme), or None if it is not an id."""
    if not isinstance(entry_id, str) or "/" in entry_id or "\\" in entry_id:
        return None
    if ID_RE.match(entry_id):
        n = unb32(entry_id[:4])
        yy, mm, dd = n // 10000, (n // 100) % 100, n % 100
        try:
            return date(2000 + yy, mm, dd).isoformat()
        except ValueError:
            return None
    if len(entry_id) >= LEGACY_ID_MIN and LEGACY_RE.match(entry_id):
        s = entry_id[:8]
        try:
            return date(int(s[:4]), int(s[4:6]), int(s[6:8])).isoformat()
        except ValueError:
            return None
    return None


def now_rfc3339(t: datetime | None = None) -> str:
    return (t or datetime.now(UTC)).astimezone().isoformat(timespec="milliseconds")


def parse_time(s: Any) -> datetime | None:
    if isinstance(s, datetime):
        return s if s.tzinfo else s.replace(tzinfo=UTC)
    if not isinstance(s, str) or not s:
        return None
    try:
        t = datetime.fromisoformat(s)
    except ValueError:
        return None
    return t if t.tzinfo else t.replace(tzinfo=UTC)


def summarize(fhir: Any) -> dict | None:
    """`{resource_type, bundle_type, entries, resource_types, focus, identifier, patient, outcome}`."""
    if not isinstance(fhir, dict):
        return None
    out: dict[str, Any] = {"resource_type": fhir.get("resourceType")}
    resources = []
    if fhir.get("resourceType") == "Bundle":
        out["bundle_type"] = fhir.get("type")
        for e in fhir.get("entry") or []:
            r = e.get("resource") if isinstance(e, dict) else None
            if isinstance(r, dict):
                resources.append(r)
        out["entries"] = len(fhir.get("entry") or [])
    else:
        resources = [fhir]
    types: list[str] = []
    for r in resources:
        rt = r.get("resourceType")
        if isinstance(rt, str) and rt not in types:
            types.append(rt)
    out["resource_types"] = types
    focus = next(
        (
            r
            for r in resources
            if r.get("resourceType")
            in (
                "Claim",
                "ClaimResponse",
                "CoverageEligibilityRequest",
                "CoverageEligibilityResponse",
                "Task",
                "Communication",
                "CommunicationRequest",
                "PaymentNotice",
                "PaymentReconciliation",
                "InsurancePlan",
            )
        ),
        None,
    )
    if focus:
        out["focus"] = focus.get("resourceType")
        ident = focus.get("identifier")
        if isinstance(ident, list) and ident and isinstance(ident[0], dict):
            out["identifier"] = ident[0].get("value")
        elif isinstance(ident, dict):
            out["identifier"] = ident.get("value")
        pat = focus.get("patient")
        if isinstance(pat, dict):
            out["patient"] = pat.get("reference")
        if focus.get("outcome") is not None:
            out["outcome"] = focus.get("outcome")
    return out


class _FileLock:
    def __init__(self, path: Path):
        self.path = path
        self.local = threading.RLock()
        self.depth = 0
        self.fd: int | None = None

    def __enter__(self):
        self.local.acquire()
        if self.depth == 0:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.fd = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o640)
            fcntl.flock(self.fd, fcntl.LOCK_EX)
        self.depth += 1
        return self

    def __exit__(self, *exc):
        self.depth -= 1
        if self.depth == 0 and self.fd is not None:
            try:
                fcntl.flock(self.fd, fcntl.LOCK_UN)
            finally:
                os.close(self.fd)
                self.fd = None
        self.local.release()


class Ledger:
    def __init__(
        self,
        directory: str | os.PathLike | None,
        *,
        enabled: bool = True,
        store_bodies: bool = True,
        retention_days: int = 0,
    ):
        self.enabled = bool(enabled and directory)
        self.dir = Path(directory) if directory else None
        self.store_bodies = store_bodies
        self.retention_days = max(int(retention_days or 0), 0)
        self.mu = threading.RLock()
        self.summaries: dict[str, dict] = {}
        self.ids: list[str] = []
        self.by_corr: dict[str, list[str]] = {}
        self.seen_set: set[str] = set()
        self.day_ids: dict[str, list[str]] = {}
        self.offsets: dict[str, int] = {}
        self.flock = _FileLock(self.dir / ".lock") if self.dir else None
        if self.enabled:
            self.dir.mkdir(parents=True, exist_ok=True)
            self.refresh()

    # ---- index maintenance ----

    def _drop_day(self, day: str) -> None:
        for i in self.day_ids.pop(day, []):
            s = self.summaries.pop(i, None)
            with contextlib.suppress(ValueError):
                self.ids.remove(i)
            if s:
                c = s.get("correlation_id") or ""
                lst = self.by_corr.get(c)
                if lst and i in lst:
                    lst.remove(i)
                    if not lst:
                        self.by_corr.pop(c, None)
                if s.get("api_call_id"):
                    self.seen_set.discard(
                        f"{s.get('direction')}:{s.get('api_call_id')}"
                    )
        self.offsets.pop(day, None)

    def _index(self, s: dict, day: str) -> None:
        i = s.get("id")
        if not i or i in self.summaries:
            return
        self.summaries[i] = s
        if not self.ids or i > self.ids[-1]:
            self.ids.append(i)
        else:
            insort(self.ids, i)
        self.day_ids.setdefault(day, []).append(i)
        c = s.get("correlation_id") or ""
        if c:
            insort(self.by_corr.setdefault(c, []), i)
        if s.get("api_call_id"):
            self.seen_set.add(f"{s.get('direction')}:{s.get('api_call_id')}")

    def refresh(self) -> None:
        """Bring the in-memory indexes up to date with every process's appends."""
        if not self.enabled:
            return
        with self.mu:
            try:
                days = sorted(
                    p.name
                    for p in self.dir.iterdir()
                    if p.is_dir() and DAY_RE.match(p.name)
                )
            except FileNotFoundError:
                days = []
            for gone in set(self.offsets) - set(days):
                self._drop_day(gone)
            for day in days:
                idx = self.dir / day / "index.jsonl"
                off = self.offsets.get(day, 0)
                try:
                    size = idx.stat().st_size
                except FileNotFoundError:
                    continue
                if size < off:
                    self._drop_day(day)
                    off = 0
                if size == off:
                    self.offsets[day] = off
                    continue
                with idx.open("rb") as f:
                    f.seek(off)
                    data = f.read()
                end = data.rfind(b"\n") + 1
                for line in data[:end].splitlines():
                    if not line.strip():
                        continue
                    try:
                        s = json.loads(line)
                    except ValueError:
                        logger.warning("nhcx: unreadable ledger index line in %s", idx)
                        continue
                    if isinstance(s, dict):
                        self._index(s, day)
                self.offsets[day] = off + end

    # ---- writing ----

    def _next_id(self, t: datetime) -> str:
        day = day_code(t)
        top = 0
        lo = day + "0000"
        hi = day + "VVVV"
        for i in reversed(self.ids):
            if i <= hi and len(i) == ID_LEN:
                if i >= lo:
                    top = unb32(i[4:])
                break
        return day + b32(top + 1, 4)

    def record(self, e: dict) -> str | None:
        """Write one entry; returns its id. Errors propagate (the caller only logs)."""
        if not self.enabled:
            return None
        e = dict(e)
        t = parse_time(e.get("created_at")) or datetime.now(UTC)
        e["created_at"] = now_rfc3339(t)
        e["path"] = clean_path(e.get("path"))
        e["entity"] = e.get("entity") or entity_type(e["path"])
        e["action"] = e.get("action") or e["path"].split("/")[-1]
        e["kind"] = e.get("kind") or (
            "response" if is_response_path(e["path"]) else "request"
        )
        if e.get("fhir") is not None and not e.get("fhir_summary"):
            e["fhir_summary"] = summarize(e.get("fhir"))
        if not self.store_bodies:
            e["fhir"] = None
            if isinstance(e.get("peer"), dict):
                e["peer"] = {**e["peer"], "response": None}
        e.setdefault("redelivery", False)
        e.setdefault("duration_ms", 0)
        day = t.astimezone(UTC).date().isoformat()
        with self.mu, self.flock:
            self.refresh()
            if not e.get("id"):
                e["id"] = self._next_id(t)
            folder = self.dir / day
            folder.mkdir(parents=True, exist_ok=True)
            path = folder / f"{e['id']}.json"
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o640)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(e, f, indent=2, ensure_ascii=False, default=str)
            summary = {k: e.get(k) for k in SUMMARY_FIELDS}
            with (folder / "index.jsonl").open("ab") as f:
                f.write(
                    json.dumps(summary, ensure_ascii=False, default=str).encode()
                    + b"\n"
                )
            self.refresh()
        return e["id"]

    # ---- reads ----

    def _require(self) -> None:
        if not self.enabled:
            raise GatewayError("LEDGER_DISABLED", "the ledger is off")

    def get(self, entry_id: str) -> dict | None:
        self._require()
        day = day_of_id((entry_id or "").strip())
        if day is None:
            return None
        path = self.dir / day / f"{entry_id.strip()}.json"
        try:
            raw = path.read_bytes()
        except (FileNotFoundError, NotADirectoryError):
            return None
        try:
            out = json.loads(raw)
        except ValueError as e:
            raise GatewayError(
                "LEDGER_CORRUPT", f"ledger entry {entry_id} is corrupt"
            ) from e
        return out

    def _entry(self, txn_id: str) -> dict:
        self._require()
        txn_id = (txn_id or "").strip() if isinstance(txn_id, str) else ""
        if not txn_id:
            raise GatewayError("NO_TXN_ID", "txn_id is required")
        e = self.get(txn_id)
        if e is None:
            raise GatewayError(
                "TXN_NOT_FOUND", f"no transaction {txn_id} in the ledger"
            )
        return e

    @staticmethod
    def row(s: dict) -> dict:
        out = {k: s.get(k) for k in ROW_FIELDS}
        out["type"] = s.get("entity")
        out["flow"] = s.get("action")
        out["created_at"] = s.get("created_at")
        return out

    def list_summaries(
        self, correlation_id: str | None = None, limit: int = 50
    ) -> list[dict]:
        self.refresh()
        with self.mu:
            ids = self.by_corr.get(correlation_id, []) if correlation_id else self.ids
            return [
                self.summaries[i] for i in reversed(ids[-limit:]) if i in self.summaries
            ]

    def related(self, txn_id: str) -> list[dict]:
        e = self._entry(txn_id)
        return [
            self.row(s)
            for s in self.list_summaries(e.get("correlation_id") or None, RELATED_LIMIT)
        ]

    def fhir(self, txn_id: str) -> dict:
        e = self._entry(txn_id)
        return {
            "meta": {
                "type": "in" if e.get("direction") == "in" else "out",
                "payloadType": e.get("format"),
                "path": e.get("path"),
                "time": e.get("created_at"),
            },
            "jwe_headers": e.get("headers"),
            "fhir": e.get("fhir"),
        }

    def dispatch(self, txn_id: str) -> dict:
        e = self._entry(txn_id)
        status = e.get("status")
        out: dict[str, Any] = {"txnId": e.get("id"), "status": status}
        if status in ("failed", "rejected"):
            out["status"] = "dispatch_failed"
        elif status in ("accepted", "delivered"):
            out["status"] = "dispatched"
        err = e.get("error")
        if isinstance(err, dict) and err:
            out["errorCode"] = err.get("code")
            out["errorMessage"] = err.get("message")
        return out

    def list(self, limit: Any = LIST_DEFAULT) -> list[dict]:
        if not self.enabled:
            return []
        if (
            not isinstance(limit, int)
            or isinstance(limit, bool)
            or not 1 <= limit <= LIST_MAX
        ):
            limit = LIST_DEFAULT
        return [self.row(s) for s in self.list_summaries(None, limit)]

    def seen(self, direction: str, api_call_id: str) -> bool:
        if not self.enabled or not api_call_id:
            return False
        self.refresh()
        with self.mu:
            return f"{direction}:{api_call_id}" in self.seen_set

    def last_inbound_request(
        self, entity: str, sender: str | None = None, workflow_id: str | None = None
    ) -> dict | None:
        if not self.enabled:
            return None
        self.refresh()
        with self.mu:
            for i in reversed(self.ids):
                s = self.summaries.get(i) or {}
                if (
                    s.get("direction") != "in"
                    or s.get("kind") != "request"
                    or s.get("entity") != entity
                    or not s.get("correlation_id")
                ):
                    continue
                if sender and not same_code(s.get("sender"), sender):
                    continue
                if workflow_id and s.get("workflow_id") != workflow_id:
                    continue
                return dict(s)
        return None

    def thread(self, correlation_id: str) -> dict | None:
        self._require()
        msgs = (
            list(reversed(self.list_summaries(correlation_id, 10**6)))
            if correlation_id
            else []
        )
        if not msgs:
            return None
        first = msgs[0]
        first_out = first.get("direction") == "out"
        if first.get("kind") == "response":
            first_out = not first_out
        state = "unknown"
        for m in msgs:
            hs = m.get("hcx_status") or ""
            is_resp = m.get("kind") == "response"
            if (
                m.get("status") in ("failed", "rejected")
                or (is_resp and m.get("status") == "delivery_failed")
                or m.get("format") == "protocol"
                or "error" in hs
            ):
                state = "error"
            elif not is_resp and m.get("direction") == "out":
                state = "awaiting_response"
            elif not is_resp and m.get("direction") == "in":
                state = "awaiting_our_response"
            elif is_resp and hs == "response.partial":
                state = "partial"
            elif is_resp:
                state = "completed"
        last = msgs[-1]
        counterparty = (
            first.get("recipient")
            if first.get("direction") == "out"
            else first.get("sender")
        )
        return {
            "correlation_id": correlation_id,
            "entity": first.get("entity"),
            "workflow_id": next(
                (m.get("workflow_id") for m in msgs if m.get("workflow_id")), None
            ),
            "counterparty": counterparty,
            "role": "initiator" if first_out else "responder",
            "state": state,
            "started": first.get("created_at"),
            "updated": last.get("created_at"),
            "messages": msgs,
        }

    def sweep(self, now: datetime | None = None) -> int:
        """Delete day folders older than the retention period; returns how many."""
        if not self.enabled or self.retention_days == 0:
            return 0
        now = now or datetime.now(UTC)
        cutoff = (
            (now.astimezone(UTC) - timedelta(days=self.retention_days))
            .date()
            .isoformat()
        )
        removed = 0
        with self.mu, self.flock:
            for p in sorted(self.dir.iterdir()):
                if p.is_dir() and DAY_RE.match(p.name) and p.name < cutoff:
                    shutil.rmtree(p, ignore_errors=True)
                    self._drop_day(p.name)
                    removed += 1
        if removed:
            logger.info(
                "nhcx: ledger pruned %d day folder(s) before %s", removed, cutoff
            )
        return removed
