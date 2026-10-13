"""F11 CommunicationRequest (D23 claim_query), and a bare payer Communication (note)."""

from care.nhcx.fhir import bundle as fb

QUERY_REASONS = ("", "additionalinfo", "questionnaire", "query")
REASON_ALIASES = {"claimarbitartion": "claimarbitration"}


def handler_for(bundle):
    """'request', 'note' or None: which handler a communication bundle goes to."""
    if fb.is_protocol_response(bundle):
        return None
    bundle = fb.unwrap(bundle)
    if bundle.get("type") == "ProtocolResponse":
        return None
    if fb.find_resource(bundle, "CommunicationRequest"):
        return "request"
    if fb.find_resource(bundle, "Communication"):
        return "note"
    return None


def references(resource):
    """Reference values from about[], basedOn[], identifier[], de-duplicated."""
    values = []
    items = (
        list(resource.get("about") or [])
        + list(resource.get("basedOn") or [])
        + list(resource.get("identifier") or [])
    )
    for item in items:
        reference = item.get("reference")
        if reference:
            values.append(reference)
            if "/" in reference:
                values.append(reference.rstrip("/").rsplit("/", 1)[-1])
        values.append(item.get("display"))
        values.append((item.get("identifier") or {}).get("value"))
        if not reference:
            values.append(item.get("value"))
    return list(dict.fromkeys(str(v) for v in values if v))


def pick_claim_ref(resource, refs):
    """identifier values first, then the first ref with no '/' and no ':'."""
    for identifier in resource.get("identifier") or []:
        if identifier.get("value") and "/" not in identifier["value"]:
            return identifier["value"]
    return next((r for r in refs if "/" not in r and ":" not in r), "")


def _entry_ids(entry, resource):
    full_url = (entry or {}).get("fullUrl") or ""
    rid = resource.get("id") or ""
    if not rid and full_url:
        rid = full_url.removeprefix("urn:uuid:").rstrip("/").rsplit("/", 1)[-1]
    return rid, full_url or (f"urn:uuid:{rid}" if rid else "")


def reason_code(task):
    reason = (task or {}).get("reasonCode")
    if isinstance(reason, list):
        reason = reason[0] if reason else None
    if not reason:
        return ""
    codings = reason.get("coding") or []
    code = (codings[0].get("code") if codings else None) or reason.get("text") or ""
    code = code.lower()
    return REASON_ALIASES.get(code, code)


def classify(intent, reason, query_mode=""):
    """'query' or 'notification', per the payer adapter's query mode and the Task."""
    if query_mode == "resubmit":
        return "notification"
    intent = (intent or "").lower()
    if intent == "proposal":
        return "notification"
    if intent == "order":
        return "query"
    return "query" if reason in QUERY_REASONS else "notification"


def _questions(request, task):
    lines = []
    for payload in request.get("payload") or []:
        text = payload.get("contentString")
        if text:
            lines += [line.strip() for line in str(text).splitlines() if line.strip()]
    if not lines:
        lines = [
            r.get("text") for r in request.get("reasonCode") or [] if r.get("text")
        ]
    if not lines and (task or {}).get("description"):
        lines = [task["description"]]
    return lines


def read(bundle, query_mode=""):
    """D23 fields of the first CommunicationRequest and the first Task.

    Returns {request_id, request_full_url, refs, claim_ref, questions, remarks, reason_code, intent,
    task_id, authored_on, kind}; {} when the bundle has no CommunicationRequest.
    """
    bundle = fb.unwrap(bundle)
    entry = fb.find_entry(bundle, "CommunicationRequest")
    if entry is None:
        return {}
    request = entry.get("resource") or {}
    request_id, full_url = _entry_ids(entry, request)
    task = fb.find_resource(bundle, "Task")
    refs = references(request)
    reason = reason_code(task)
    intent = ((task or {}).get("intent") or "").lower()
    questions = _questions(request, task)
    return {
        "request_id": request_id,
        "request_full_url": full_url,
        "refs": refs,
        "claim_ref": pick_claim_ref(request, refs),
        "questions": questions,
        "remarks": "\n".join(questions),
        "reason_code": reason,
        "intent": intent,
        "task_id": (task or {}).get("id") or "",
        "authored_on": request.get("authoredOn") or "",
        "kind": classify(intent, reason, query_mode),
    }


def read_note(bundle):
    """A bare payer Communication filed as kind 'note' (same keys as read())."""
    bundle = fb.unwrap(bundle)
    entry = fb.find_entry(bundle, "Communication")
    if entry is None:
        return {}
    note = entry.get("resource") or {}
    note_id, full_url = _entry_ids(entry, note)
    refs = references(note)
    lines = []
    for payload in note.get("payload") or []:
        text = payload.get("contentString")
        if text:
            lines += [line.strip() for line in str(text).splitlines() if line.strip()]
    return {
        "request_id": note_id,
        "request_full_url": full_url,
        "refs": refs,
        "claim_ref": pick_claim_ref(note, refs),
        "questions": lines,
        "remarks": "\n".join(lines),
        "reason_code": "",
        "intent": "",
        "task_id": "",
        "authored_on": note.get("sent") or "",
        "kind": "note",
    }
