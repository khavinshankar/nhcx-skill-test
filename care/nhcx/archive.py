"""Message archive beside each case (SCAFFOLDING 3.7, C1P archive_inbound).

Every outbound envelope (services) and every inbound one (C1) is written as
``<NHCX_ARCHIVE_DIR>/<claim_no or "unmatched">/<NNN>-<type>-<in|out>.json``
with one line per message in that folder's ``transactions.txt``. The
directory comes from ``settings.NHCX_ARCHIVE_DIR``; when it is empty the
archive is switched off and every function here is a no-op. A disk failure is
logged and never raised.

Public:
- ``archive_outbound(claim, path, envelope, ack=None, *, label="")`` -> handle
- ``archive_inbound(claim, envelope, type_, flow, corr, participant, redelivery)``
  -> handle
- ``archive_note(handle, outcome)``
A handle is ``(folder Path, file name)`` or None.
"""

import json
import logging
import re
import threading
from pathlib import Path

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

UNMATCHED = "unmatched"
_lock = threading.Lock()
_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


def archive_dir() -> Path | None:
    root = (getattr(settings, "NHCX_ARCHIVE_DIR", "") or "").strip()
    return Path(root) if root else None


def _folder_name(claim) -> str:
    claim_no = getattr(claim, "claim_no", None) if claim is not None else None
    return _SAFE.sub("_", claim_no) if claim_no else UNMATCHED


def _next_seq(folder: Path) -> int:
    highest = 0
    for p in folder.glob("[0-9][0-9][0-9]*-*.json"):
        head = p.name.split("-", 1)[0]
        if head.isdigit():
            highest = max(highest, int(head))
    return highest + 1


def _headers(envelope) -> dict:
    if not isinstance(envelope, dict):
        return {}
    h = envelope.get("jwe_headers")
    return h if isinstance(h, dict) else {}


def _write(claim, kind: str, direction: str, document, line_fields: list) -> tuple:
    root = archive_dir()
    if root is None:
        return None
    folder = root / _folder_name(claim)
    with _lock:
        folder.mkdir(parents=True, exist_ok=True)
        seq = _next_seq(folder)
        name = f"{seq:03d}-{_SAFE.sub('_', kind or 'exchange')}-{direction}.json"
        (folder / name).write_text(
            json.dumps(document, indent=2, default=str, ensure_ascii=False)
        )
        when = timezone.now().isoformat(timespec="seconds")
        fields = "  ".join(f for f in line_fields if f)
        line = f"{when}  {seq:03d}  {direction.upper()}  {fields}  file={name}\n"
        with (folder / "transactions.txt").open("a", encoding="utf-8") as fh:
            fh.write(line)
    return folder, name


def archive_outbound(claim, path: str, envelope, ack=None, *, label: str = ""):
    """Archive an outbound envelope and, when given, the send's acknowledgement."""
    try:
        h = _headers(envelope)
        kind = label or (path or "").strip("/").split("/")[-2:][0]
        ack_doc = None
        if ack is not None:
            ack_doc = ack.to_dict() if hasattr(ack, "to_dict") else ack
        document = {"path": path, "envelope": envelope, "ack": ack_doc}
        corr = getattr(ack, "correlation_id", None) or h.get("x-hcx-correlation_id")
        txn = getattr(ack, "txn_id", None)
        failed = getattr(ack, "failed", None)
        return _write(
            claim,
            kind,
            "out",
            document,
            [
                kind,
                path,
                f"workflow={h.get('x-hcx-workflow_id', '')}",
                f"recipient={h.get('x-hcx-recipient_code', '')}",
                f"correlation={corr or ''}",
                f"txn={txn or ''}",
                f"failed={failed}" if failed else "",
            ],
        )
    except Exception:
        logger.exception(
            "nhcx: archive_outbound failed claim=%s path=%s",
            getattr(claim, "claim_no", None),
            path,
        )
        return None


def archive_inbound(claim, envelope, type_, flow, corr, participant, redelivery):
    """Archive an inbound envelope unchanged (C1P archive_inbound)."""
    try:
        h = _headers(envelope)
        return _write(
            claim,
            type_ or "exchange",
            "in",
            envelope,
            [
                type_ or "exchange",
                flow or type_ or "",
                f"workflow={h.get('x-hcx-workflow_id', '')}",
                f"correlation={corr or ''}",
                f"api_call={h.get('x-hcx-api_call_id', '')}",
                f"txn={h.get('x-hcx-txn_id', '')}",
                f"participant={participant or ''}",
                f"redelivery={bool(redelivery)}",
            ],
        )
    except Exception:
        logger.exception(
            "nhcx: archive_inbound failed claim=%s corr=%s",
            getattr(claim, "claim_no", None),
            corr,
        )
        return None


def archive_note(handle, outcome) -> None:
    """Append the outcome line under an archived message."""
    if not handle:
        return
    folder, name = handle
    try:
        with _lock, (folder / "transactions.txt").open("a", encoding="utf-8") as fh:
            fh.write(f"    \u21b3 {name} outcome={outcome}\n")
    except Exception:
        logger.exception("nhcx: archive_note failed file=%s", name)
