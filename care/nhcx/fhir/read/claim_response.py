"""F9 ClaimResponse and the Task answers of F10."""

import json

from care.nhcx.fhir import bundle as fb

ACKNOWLEDGING = ("queued", "acknowledged")
ACK_REASONS = ("submitted", "acknowledged")
WORKFLOW_STATUS = {
    **dict.fromkeys(("20", "25", "18", "251", "28", "29", "37"), "submitting"),
    **dict.fromkeys(("21", "22", "26", "252"), "approved"),
    **dict.fromkeys(("23", "231", "291", "253"), "rejected"),
    **dict.fromkeys(("24", "241", "27", "254"), "queried"),
}
EMPTY_PIECES = ("", ".", "null", "none", "nil", "-")
ERROR_STATUS = "response.error"


def _first_coding(concept):
    codings = (concept or {}).get("coding") or []
    return codings[0] if codings else {}


def _category(entry):
    return (_first_coding(entry.get("category")).get("code") or "").lower()


def _amount(money):
    value = (money or {}).get("value")
    return fb.amount(value) if value not in (None, "") else None


def claim_reason(response):
    """First claim-level reason code, preferring category status, lower-cased."""
    entries = [a for a in response.get("adjudication") or [] if a.get("reason")]
    preferred = [a for a in entries if _category(a) == "status"]
    for entry in preferred + entries:
        coding = _first_coding(entry.get("reason"))
        code = coding.get("code") or coding.get("display")
        if code:
            return code.lower()
    return ""


def decide(outcome, reason):
    """The F9 table, rows tried top to bottom."""
    if outcome in ACKNOWLEDGING or reason in ACK_REASONS:
        status = "submitting"
    elif reason in ("cancelled", "rejected", "denied"):
        status = "rejected"
    elif reason == "queried":
        status = "queried"
    elif outcome == "error":
        status = "error"
    elif outcome == "partial":
        status = "partial" if reason == "approved" else "queried"
    elif outcome == "complete" and reason in ("approved", ""):
        status = "approved"
    else:
        status = "queried"
    return status


def is_error(response, status_header=None):
    if status_header == ERROR_STATUS or response.get("error"):
        return True
    reason = claim_reason(response)
    return response.get("outcome") == "error" and reason not in (
        "rejected",
        "denied",
        "cancelled",
    )


def status_for(response, workflow_id=None, status_header=None):
    outcome = response.get("outcome") or ""
    reason = claim_reason(response)
    if is_error(response, status_header):
        return "error"
    by_workflow = WORKFLOW_STATUS.get(str(workflow_id or ""))
    if by_workflow:
        if by_workflow == "approved" and outcome == "partial":
            return "partial"
        return by_workflow
    return decide(outcome, reason)


def clean_pieces(text):
    out = []
    for raw in (text or "").split("|"):
        piece = raw.strip()
        if piece.startswith(":"):
            piece = piece[1:].strip()
        if piece.lower() in EMPTY_PIECES:
            continue
        out.append(piece)
    return out


def _item_row(item):
    row = {"sequence": item.get("itemSequence")}
    for adj in item.get("adjudication") or []:
        category = _category(adj)
        reason = _first_coding(adj.get("reason"))
        if category == "eligible":
            row["eligible"] = _amount(adj.get("amount"))
        elif category == "status":
            row["status"] = reason.get("code") or reason.get("display")
        elif category == "reason":
            text = reason.get("display") or reason.get("code") or ""
            row["reason"] = "\n".join(clean_pieces(text))
        elif category == "eligpercent":
            row["percent"] = adj.get("value")
        elif category == "eligquant":
            row["quantity"] = adj.get("value")
        elif category == "deductible":
            row["deductible"] = _amount(adj.get("amount"))
            row["deduction_reason"] = ", ".join(
                p for p in (reason.get("code"), reason.get("display")) if p
            )
        elif category == "benefit":
            row["benefit"] = _amount(adj.get("amount"))
        elif category == "submitted":
            row["submitted"] = _amount(adj.get("amount"))
    return row


def query_note(response):
    pieces = []
    for item in response.get("item") or []:
        for adj in item.get("adjudication") or []:
            if _category(adj) == "reason":
                reason = _first_coding(adj.get("reason"))
                pieces += clean_pieces(reason.get("display") or reason.get("code"))
    pieces += [
        n.get("text") for n in response.get("processNote") or [] if n.get("text")
    ]
    return "\n".join(dict.fromkeys(pieces))


def error_message(response):
    lines = []
    for error in response.get("error") or []:
        code = error.get("code") or {}
        coding = _first_coding(code)
        line = " ".join(p for p in (coding.get("code"), coding.get("display")) if p)
        lines.append(line or code.get("text") or "")
    if response.get("disposition"):
        lines.append(response["disposition"])
    lines += [n.get("text") for n in response.get("processNote") or [] if n.get("text")]
    return "\n".join(line for line in lines if line)


def read_response(response, workflow_id=None, status_header=None):
    """D18/D20 fields from one ClaimResponse resource."""
    totals = {}
    for total in response.get("total") or []:
        totals.setdefault(_category(total), _amount(total.get("amount")))
    status = status_for(response, workflow_id, status_header)
    return {
        "outcome": response.get("outcome") or "",
        "adjudication": claim_reason(response),
        "status": status,
        "disposition": response.get("disposition") or "",
        "preauth_ref": response.get("preAuthRef") or "",
        "approved_amount": totals.get("benefit"),
        "eligible_amount": totals.get("eligible"),
        "submitted_amount": totals.get("submitted"),
        "items_json": [_item_row(item) for item in response.get("item") or []],
        "query_note": query_note(response),
        "error_message": error_message(response) if status == "error" else "",
        "form": response.get("form"),
    }


def read(bundle, workflow_id=None, status_header=None):
    """The first ClaimResponse of a bundle; a ProtocolResponse is a refusal."""
    if fb.is_protocol_response(bundle):
        return {
            "status": "error",
            "error_message": fb.protocol_error(bundle),
            "refused": True,
        }
    bundle = fb.unwrap(bundle)
    response = fb.find_resource(bundle, "ClaimResponse")
    if response is None:
        return {
            "status": "error" if status_header == ERROR_STATUS else "",
            "error_message": "The reply carries no ClaimResponse.",
        }
    return read_response(response, workflow_id, status_header)


def read_predetermination(bundle, workflow_id=None, status_header=None):
    """D19 fields; the reply is an answer whatever it says."""
    out = read(bundle, workflow_id, status_header)
    return {
        "outcome": out.get("outcome", ""),
        "adjudication": out.get("adjudication", ""),
        "disposition": out.get("disposition", ""),
        "allowed_amount": out.get("approved_amount"),
        "status": "answered",
    }


def _task_response(bundle, task):
    for output in (task or {}).get("output") or []:
        reference = (output.get("valueReference") or {}).get("reference")
        if reference:
            resource = fb.resolve_reference(bundle, reference)
            if resource and resource.get("resourceType") == "ClaimResponse":
                return resource
    return fb.find_resource(bundle, "ClaimResponse")


def _status_header(headers):
    value = (headers or {}).get("x-hcx-status_response")
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            value = {}
    return value if isinstance(value, dict) else {}


def _output_value(task, code):
    for output in (task or {}).get("output") or []:
        codes = [c.get("code") for c in (output.get("type") or {}).get("coding") or []]
        if code in codes or (output.get("type") or {}).get("text") == code:
            for key, value in output.items():
                if key.startswith("value"):
                    if isinstance(value, dict):
                        coding = _first_coding(value)
                        return coding.get("code") or value.get("text")
                    return value
    return None


def read_task_reply(bundle, action, headers=None):
    """F10: the payer's answer to a cancel, reprocess, release or status Task.

    Returns {action, task_status, outcome, accepted (cancel) or answer, detail,
    response (F9 fields of the referenced ClaimResponse or None)}.
    """
    if fb.is_protocol_response(bundle):
        return {"action": action, "refused": True, "detail": fb.protocol_error(bundle)}
    bundle = fb.unwrap(bundle)
    task = fb.find_resource(bundle, "Task")
    response = _task_response(bundle, task)
    fields = read_response(response) if response else None
    task_status = (task or {}).get("status") or ""
    outcome = (response or {}).get("outcome") or ""
    description = (task or {}).get("description") or ""
    out = {
        "action": action,
        "task_status": task_status,
        "outcome": outcome,
        "response": fields,
    }
    if action == "cancel":
        out["accepted"] = (
            task_status in ("", "completed", "accepted") and outcome != "error"
        )
        out["detail"] = (response or {}).get("disposition") or description
    elif action in ("reprocess", "release"):
        out["answer"] = (
            "reopened"
            if task_status in ("completed", "accepted", "in-progress")
            else "refused"
        )
        out["detail"] = (response or {}).get("disposition") or description
    else:
        header = _status_header(headers)
        entity = header.get("entity_status") or _output_value(task, "claimStatus")
        if not entity:
            entity = "not-found" if task_status == "rejected" else "unknown"
        out["answer"] = entity
        parts = [
            f"{label}: {header[key]}"
            for label, key in (
                ("stage", "stage"),
                ("outcome", "outcome"),
                ("total_approved", "total_approved"),
                ("total_paid", "total_paid"),
            )
            if header.get(key) not in (None, "")
        ]
        out["detail"] = "; ".join(p for p in [description, *parts] if p)
    return out
