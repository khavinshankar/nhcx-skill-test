"""The payer-side driver both runners use (T2X "Deciding the payer's side").

A decision is always read then taken: the role or case first (A14), then the
action (A15), through ``care.nhcx.services.adjudicator`` - the IRDAI payer desk
for the IRDAI test payer, the NHCX Payer Service role walk for PMJAY. The
IRDAI desk's other acts (per-line decisions, payments) use the same desk
sign-in.
"""

from __future__ import annotations

import time

from care.nhcx.services import adjudicator as adj

NO_DATA = "no data found"
NOT_YET = ("holds no case", "not been sent", "no data found")
READ_EVERY = 5


def _claim(claim):
    from care.nhcx.services import common

    return common.get_claim(claim)


def read(claim, stage) -> dict:
    """A14: who holds the case (PMJAY) or the case itself (IRDAI)."""
    claim = _claim(claim)
    try:
        reply = adj.read_role(claim, stage)
    except adj.AdjudicatorError as e:
        return {"error": str(e), "role": ""}
    return reply


def auto_decided(reply) -> bool:
    """The PMJAY sandbox decided by itself: the role read finds no case."""
    text = f"{reply.get('error') or ''} {reply.get('response') or ''}".lower()
    return not reply.get("role") and NO_DATA in text


def read_when_there(claim, stage, seconds=60) -> dict:
    """Reads until the payer holds the case (it arrives a moment after sending).

    PMJAY's "No Data found" is read again too, but a case that never shows is
    the sandbox deciding by itself (``auto_decided``).
    """
    start = time.monotonic()
    while True:
        looked = read(claim, stage)
        text = str(looked.get("error") or looked.get("response") or "").lower()
        if looked.get("role") and looked.get("transport") == "irdai-payer":
            # The desk keeps one case per claim; until this leg's message lands
            # the case still shows the previous leg (and an action is lost).
            if _irdai_current(claim, stage):
                return looked
        elif looked.get("role") or not any(m in text for m in NOT_YET):
            return looked
        if time.monotonic() - start > seconds:
            return looked
        time.sleep(READ_EVERY)


NOT_LOGGED = "event meta log not found"


def _not_logged_yet(result) -> bool:
    """The payer service has not logged the claim yet. The cycle resumes at the
    role holding the case, so running it again repeats nothing already taken."""
    steps = result.get("steps") or []
    return (
        result.get("stopped") == "refused"
        and bool(steps)
        and NOT_LOGGED in str(steps[-1].get("error") or "").lower()
    )


def decide(claim, stage, decision, remarks="", *, read_seconds=60) -> dict:
    """A14 then A15; returns the record the report keeps for the decision."""
    claim = _claim(claim)
    looked = read_when_there(claim, stage, read_seconds)
    record = {
        "stage": stage,
        "decision": decision,
        "remarks": remarks,
        "read": {
            k: looked.get(k)
            for k in ("caseNumber", "role", "status", "error", "warning", "response")
        },
    }
    if auto_decided(looked):
        record["skipped"] = "sandbox auto-decided"
        return record
    if looked.get("error") and not looked.get("role"):
        record["error"] = looked["error"]
        return record
    start = time.monotonic()
    taken = []
    while True:
        try:
            result = adj.cycle(claim, stage, decision, remarks)
        except adj.AdjudicatorError as e:
            record["error"] = str(e)
            return record
        if not (_not_logged_yet(result) and time.monotonic() - start < read_seconds):
            break
        record.setdefault("not_logged_yet", []).append(result["cycle_id"])
        taken.extend(s for s in result["steps"] if s.get("success"))
        time.sleep(READ_EVERY * 2)
    record["cycle_id"] = result["cycle_id"]
    record["stopped"] = result["stopped"]
    record["trail"] = taken + result["steps"]
    return record


# ---- the IRDAI desk's other acts (A15 "the payer's other acts") ----


def _irdai(claim, stage):
    claim = _claim(claim)
    found = adj.leg(claim, stage)
    if found is None:
        raise adj.AdjudicatorError(adj.NOT_SENT)
    case, tok = adj._irdai_case(  # noqa: SLF001
        claim, found["case_number"], found["correlation_id"]
    )
    return claim, case, {"Authorization": "Bearer " + tok}


def _irdai_current(claim, stage) -> bool:
    claim = _claim(claim)
    found = adj.leg(claim, stage)
    try:
        case, _tok = adj._irdai_case(  # noqa: SLF001
            claim, found["case_number"], found["correlation_id"]
        )
    except adj.AdjudicatorError:
        return False
    return (case.get("exchange") or {}).get("correlation_id") == found["correlation_id"]


def irdai_case(claim, stage) -> dict:
    """The case on the desk, with its line items where the desk lists them."""
    _claim_row, case, headers = _irdai(claim, stage)
    status, data, raw = adj._http(  # noqa: SLF001
        "GET", f"{adj.DESK}/cases/{case.get('id')}", headers=headers
    )
    if status < adj.HTTP_REDIRECT and isinstance(data, dict):
        return data
    return {**case, "_detail_status": status, "_detail_raw": raw[:200]}


def _line_items(case) -> list:
    for key in ("line_items", "lineItems", "items"):
        rows = case.get(key)
        if isinstance(rows, list):
            return rows
    return []


def irdai_lines(claim, stage, decisions, remarks="e2e line decision") -> dict:
    """Decides the case's lines in order: ``decisions`` is a list of
    ``(status, approved_amount)``; ``None`` leaves that line alone."""
    _c, case, headers = _irdai(claim, stage)
    rows = _line_items(irdai_case(claim, stage))
    out = []
    for row, decision in zip(rows, decisions, strict=False):
        if decision is None:
            continue
        status_text, amount = decision
        status, _data, raw = adj._http(  # noqa: SLF001
            "PATCH",
            f"{adj.DESK}/cases/{case.get('id')}/line-items/{row.get('id')}",
            headers=headers,
            body={
                "status": status_text,
                "approved_amount": amount,
                "remarks": remarks,
            },
        )
        out.append(
            {
                "line": row.get("id"),
                "code": row.get("code"),
                "claimed": row.get("claimed_amount"),
                "decision": status_text,
                "amount": amount,
                "status": status,
                "error": None if status < adj.HTTP_REDIRECT else raw[:200],
            }
        )
    return {"case": case.get("id"), "lines": out, "listed": len(rows)}


def irdai_pay(claim, amount, utr, *, stage="claim") -> dict:
    """Raises a payment with its UTR, so the desk completes it in one step."""
    claim, case, headers = _irdai(claim, stage)
    status, data, raw = adj._http(  # noqa: SLF001
        "POST",
        f"{adj.DESK}/payments",
        headers=headers,
        body={
            "case_id": case.get("id"),
            "payment_amount": amount,
            "mode": "NEFT",
            "beneficiary": {
                "name": claim.facility.name,
                "account_no": "000123456789",
                "ifsc": "SBIN0000001",
            },
            "utr_no": utr,
        },
    )
    return {
        "case": case.get("id"),
        "amount": amount,
        "utr": utr,
        "status": status,
        "response": data if data is not None else raw[:300],
        "error": None if status < adj.HTTP_REDIRECT else raw[:300],
    }
