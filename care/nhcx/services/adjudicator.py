"""A14-A16 adjudicator console (sandbox only): read the role holding a case,
take one action, or walk the PMJAY roles for one decision. Disabled unless
settings.NHCX_ADJUDICATOR_CONSOLE is on.
"""

from __future__ import annotations

import logging
import re
import time
import uuid

import requests
from django.conf import settings
from django.core.cache import cache

from care.nhcx.models import ClaimAdjudication, ClaimPreauth, ClaimSubmission
from care.nhcx.services import common, payers

logger = logging.getLogger(__name__)

ROLE_URL = "https://apisbx.abdm.gov.in/pmjay/sbxhcx/nhcxpayerservice/v1/get/user-role"
PROCESS_URL = (
    "https://apisbeta.nha.gov.in/pmjay/hcx/nhcxpayerservice/wrapper/process/case"
)
DESK = "https://nhcxai.abdm.gov.in/api/payer"
HTTP_REDIRECT = 300
TIMEOUT = 30
DESK_TOKEN_KEY = "nhcx:irdai-desk-token:{code}"

NO_DESK = (
    "{name} has no adjudication desk this EMR can drive; the decision is taken on the "
    "payer's own console."
)
NO_CASE_NUMBER = "A case number is needed to read who is holding it."
NOT_SENT = "That case was never sent from here."
NO_CORRELATION = (
    "That leg has no correlation id, it never reached the gateway, so there is nothing "
    "to decide on."
)
NO_ROLE = "Read who is holding the case before acting on it."
UNKNOWN_ROLE = "{role} is not a role in the published workflow."
ILLEGAL_ACTION = '{role} may take {actions}, not "{action}".'
IRDAI_ACTION = 'The IRDAI payer desk takes approve, reject or query, not "{action}".'
IRDAI_REMARKS = (
    "Say why, the IRDAI payer refuses a rejection or a query that says nothing."
)
BAD_DECISION = "Choose whether to approve, reject or query the case."
NO_TOKEN = (
    "No payer-service token: set the payer service token or fix the session token "
    "({code}: {message})."
)
UNREACHABLE = "{url} is unreachable, {reason}"
ROLE_WARNING = "{role} is not a role in the published workflow, read the raw response before acting."
NO_ROLE_WARNING = "the payer service returned no role field this EMR recognises, read the raw response."
IRDAI_SIGN_IN = "The IRDAI payer desk refused the token sign-in (HTTP {status}): {text}"
IRDAI_PARTICIPANT = (
    "The IRDAI payer desk would not show {code}'s cases (HTTP {status}): {text}"
)
IRDAI_LIST = "The IRDAI payer desk could not list cases (HTTP {status}): {text}"
IRDAI_NO_CASE = "The IRDAI payer holds no case under {case}."
DISABLED = "The adjudicator console is off."

WORKFLOW = [
    {
        "step": 0,
        "stage": "PREAUTH",
        "role": "PPD-Trust",
        "actions": ["Approve", "Reject", "Query"],
        "usecase": "PREAUTH",
    },
    {
        "step": 1,
        "stage": "CLAIM",
        "role": "CEX-Trust",
        "actions": ["Forward"],
        "usecase": "CLAIM",
    },
    {
        "step": 2,
        "stage": "CLAIM",
        "role": "CPD-Trust",
        "actions": ["cpdApprove", "cpdReject", "Pending"],
        "usecase": "CLAIM",
    },
    {
        "step": 3,
        "stage": "CLAIM",
        "role": "Medical Audit Committee",
        "actions": ["Approve", "Reject", "iQuery"],
        "usecase": "Medical Audit Committee",
    },
    {
        "step": 4,
        "stage": "CLAIM",
        "role": "ACO-Trust",
        "actions": ["Approve", "Reject", "Pending"],
        "usecase": "CLAIM",
    },
    {
        "step": 5,
        "stage": "CLAIM",
        "role": "SHA-Trust",
        "actions": ["Approve", "Reject", "Pending"],
        "usecase": "CLAIM",
    },
    {
        "step": 6,
        "stage": "CLAIM",
        "role": "Claim Review Committee",
        "actions": ["Approve", "Reject", "Pending"],
        "usecase": "Claim Review Committee",
    },
]
DECISIONS = {
    "PPD-Trust": ("Approve", "Reject", "Query"),
    "CEX-Trust": ("Forward", "Forward", "Forward"),
    "CPD-Trust": ("cpdApprove", "cpdReject", "Pending"),
    "Medical Audit Committee": ("Approve", "Reject", "iQuery"),
    "ACO-Trust": ("Approve", "Reject", "Pending"),
    "SHA-Trust": ("Approve", "Reject", "Pending"),
    "Claim Review Committee": ("Approve", "Reject", "Pending"),
}
DECISION_INDEX = {"approve": 0, "reject": 1, "query": 2}
ROLE_KEYS = (
    "currentuserrole",
    "currentrole",
    "userrole",
    "currentrolename",
    "assignedrole",
    "rolename",
    "role",
)
ERROR_KEYS = ("errormessage", "error", "errordesc", "errordescription")


class AdjudicatorError(common.ServiceRefusal):
    pass


def enabled() -> bool:
    return bool(getattr(settings, "NHCX_ADJUDICATOR_CONSOLE", False))


def _s(value) -> str:
    return "" if value is None else str(value).strip()


def _norm(text) -> str:
    return re.sub(r"[^a-z0-9]", "", _s(text).lower())


def _bare(code) -> str:
    return _s(code).split("@", 1)[0]


def step_for(role):
    key = _norm(role)
    return (
        next((row for row in WORKFLOW if _norm(row["role"]) == key), None)
        if key
        else None
    )


# ---- A16 ----


def token(claim) -> str:
    configured = _s(getattr(settings, "NHCX_PAYER_SERVICE_TOKEN", ""))
    if configured:
        return configured
    from care.nhcx.gateway import get_gateway

    profile = common.facility_profile(claim.facility)
    participant = _s(profile.participant_code) if profile else ""
    try:
        answer = get_gateway().token(participant or None)
    except Exception as e:
        raise AdjudicatorError(
            NO_TOKEN.format(
                code=getattr(e, "code", type(e).__name__),
                message=getattr(e, "message", None) or str(e),
            )
        ) from e
    return _s(answer.get("token") if isinstance(answer, dict) else answer)


# ---- extraction ----


def _flat(payload) -> dict:
    return (
        {_norm(k): v for k, v in payload.items()} if isinstance(payload, dict) else {}
    )


def extract_role(payload) -> str:
    if isinstance(payload, list):
        return extract_role(payload[0]) if payload else ""
    if not isinstance(payload, dict):
        return ""
    flat = _flat(payload)
    for key in ROLE_KEYS:
        if isinstance(flat.get(key), str) and flat[key].strip():
            return flat[key].strip()
    for key, value in flat.items():
        if "role" in key and isinstance(value, str) and value.strip():
            return value.strip()
    for key in ("data", "result", "response", "payload"):
        found = extract_role(flat.get(key))
        if found:
            return found
    return ""


def extract_error(payload, *, failed) -> str:
    flat = _flat(payload)
    keys = ERROR_KEYS + (("message",) if failed else ())
    for key in keys:
        if isinstance(flat.get(key), str) and flat[key].strip():
            return flat[key].strip()
    return ""


def _http(method, url, *, headers=None, body=None):
    try:
        resp = requests.request(
            method, url, headers=headers, json=body, timeout=TIMEOUT
        )
    except requests.RequestException as e:
        raise AdjudicatorError(
            UNREACHABLE.format(url=url, reason=str(e) or type(e).__name__)
        ) from e
    raw = resp.text or ""
    try:
        data = resp.json()
    except ValueError:
        data = None
    return resp.status_code, data, raw


def _service_headers(tok) -> dict:
    return {
        "Content-Type": "application/json",
        "accept": "application/json",
        "Authorization": "Bearer " + tok,
        "bearer_auth": "Bearer " + tok,
    }


# ---- A14 ----


def leg(claim, stage) -> dict | None:
    model = ClaimPreauth if stage == "preauth" else ClaimSubmission
    row = (
        model.objects.filter(claim=claim)
        .exclude(correlation_id__isnull=True)
        .exclude(correlation_id="")
        .first()
    )
    if row is None:
        return None
    adapter = payers.adapter_for_claim(claim)
    case_number = _s(row.claim_ref) or claim.claim_no
    if adapter.desk == "nhcx-payer-service":
        pre = ClaimPreauth.objects.filter(claim=claim).first()
        reference = _s(pre.preauth_ref) if pre else ""
        if "/" in reference:
            case_number = reference.rsplit("/", 1)[-1]
        elif reference:
            case_number = reference
    elif (
        adapter.desk == "irdai-payer"
        and _s(getattr(row, "preauth_ref", ""))
        and stage == "preauth"
    ):
        case_number = _s(row.preauth_ref)
    return {
        "row": row,
        "stage": stage,
        "case_number": case_number,
        "payer_code": _bare(claim.payer_id or common.default_payer_code()),
        "full_payer_code": _s(claim.payer_id) or common.default_payer_code(),
        "correlation_id": _s(row.correlation_id),
        "member_id": _s(claim.member_id),
        "desk": adapter.desk,
        "adapter": adapter,
    }


def _no_desk(claim):
    name = (
        _s(claim.payer_name)
        or payers.registry_name(claim.payer_id)
        or _s(claim.payer_id)
    )
    return AdjudicatorError(NO_DESK.format(name=name))


def role_for(claim, case_number, payer_code=None, correlation_id="") -> dict:
    case_number = _s(case_number)
    if not case_number:
        raise AdjudicatorError(NO_CASE_NUMBER)
    payer_code = _bare(payer_code or claim.payer_id or common.default_payer_code())
    desk = payers.adapter_for_claim(claim).desk
    if desk == "irdai-payer":
        return irdai_role(claim, case_number, correlation_id)
    if desk != "nhcx-payer-service":
        raise _no_desk(claim)
    tok = token(claim)
    url = _s(getattr(settings, "NHCX_PAYER_SERVICE_USER_ROLE_URL", "")) or ROLE_URL
    status, data, raw = _http(
        "POST",
        url,
        headers=_service_headers(tok),
        body={"caseid": case_number, "payerid": payer_code},
    )
    reply = {
        "caseNumber": case_number,
        "payerCode": payer_code,
        "status": status,
        "response": data,
        "raw": raw if data is None else None,
        "transport": "nhcx-payer-service",
        "role": "",
    }
    if status >= HTTP_REDIRECT:
        reply["error"] = f"the payer service returned {status}: " + (
            extract_error(data, failed=True) or raw[:200]
        )
    else:
        reply["role"] = extract_role(data)
        error = extract_error(data, failed=False)
        if error:
            reply["error"] = error
    role = _s(reply["role"])
    step = step_for(role)
    if step:
        reply["step"] = step
    elif role:
        reply["warning"] = ROLE_WARNING.format(role=role)
    elif not reply.get("error"):
        reply["warning"] = NO_ROLE_WARNING
    return reply


def _desk_token(claim, payer_full) -> str:
    key = DESK_TOKEN_KEY.format(code=_norm(payer_full))
    kept = cache.get(key)
    if kept:
        return kept
    from care.nhcx.gateway import get_gateway

    try:
        session = _s(get_gateway().token().get("token"))
    except Exception as e:
        raise AdjudicatorError(
            NO_TOKEN.format(
                code=getattr(e, "code", type(e).__name__),
                message=getattr(e, "message", None) or str(e),
            )
        ) from e
    status, data, raw = _http(
        "POST", DESK + "/auth/token/login", body={"token": session}
    )
    desk_token = _s((data or {}).get("token")) if isinstance(data, dict) else ""
    if status >= HTTP_REDIRECT or not desk_token:
        raise AdjudicatorError(
            IRDAI_SIGN_IN.format(
                status=status, text=extract_error(data, failed=True) or raw[:200]
            )
        )
    status, _data, raw = _http(
        "PUT",
        DESK + "/auth/participants",
        headers={"Authorization": "Bearer " + desk_token},
        body={"participant_codes": [payer_full]},
    )
    if status >= HTTP_REDIRECT:
        raise AdjudicatorError(
            IRDAI_PARTICIPANT.format(code=payer_full, status=status, text=raw[:200])
        )
    cache.set(key, desk_token, 30 * 60)
    return desk_token


def _irdai_case(claim, case_number, correlation_id=""):
    payer_full = _s(claim.payer_id) or common.default_payer_code()
    desk_token = _desk_token(claim, payer_full)
    status, data, raw = _http(
        "GET",
        f"{DESK}/cases?search={case_number}",
        headers={"Authorization": "Bearer " + desk_token},
    )
    if status >= HTTP_REDIRECT:
        cache.delete(DESK_TOKEN_KEY.format(code=_norm(payer_full)))
        raise AdjudicatorError(IRDAI_LIST.format(status=status, text=raw[:200]))
    rows = data.get("items") if isinstance(data, dict) else data
    # The desk numbers its cases itself (claim_no "CL/26/..."); the provider's
    # reference travels as exchange.claim_ref.
    matches = [
        r
        for r in rows or []
        if isinstance(r, dict)
        and case_number
        in {
            _s(r.get("claim_no")),
            _s(r.get("id")),
            _s((r.get("exchange") or {}).get("claim_ref")),
        }
    ]
    # One reference can carry several cases (pre-auth, enhancement, claim):
    # the leg's correlation id picks its own.
    found = next(
        (
            r
            for r in matches
            if correlation_id
            and _s((r.get("exchange") or {}).get("correlation_id")) == correlation_id
        ),
        matches[0] if matches else None,
    )
    if found is None:
        raise AdjudicatorError(IRDAI_NO_CASE.format(case=case_number))
    return found, desk_token


def irdai_role(claim, case_number, correlation_id="") -> dict:
    found, _tok = _irdai_case(claim, case_number, correlation_id)
    stage = _s(found.get("stage"))
    return {
        "caseNumber": case_number,
        "status": 200,
        "transport": "irdai-payer",
        "role": "Adjudicator",
        "step": {
            "stage": stage.upper() or "CASE",
            "usecase": stage,
            "role": "Adjudicator",
            "actions": ["approve", "reject", "query"],
        },
        "response": {
            "id": found.get("id"),
            "stage": stage,
            "adjudication": found.get("adjudication"),
        },
    }


def read_role(claim, stage) -> dict:
    claim = common.get_claim(claim)
    found = leg(claim, stage)
    if found is None:
        raise AdjudicatorError(NOT_SENT)
    return role_for(
        claim, found["case_number"], found["payer_code"], found["correlation_id"]
    )


# ---- A15 ----


def _record(claim, found, reply, remarks, cycle_id):
    ClaimAdjudication.objects.create(
        claim=claim,
        stage=found["stage"],
        case_number=found["case_number"],
        role=reply.get("role") or None,
        action=reply.get("action") or None,
        usecase=reply.get("usecase") or None,
        correlation_id=found["correlation_id"] or None,
        remarks=_s(remarks) or None,
        success=bool(reply.get("success")),
        http_status=reply.get("status"),
        response_json=reply,
        desk=reply.get("transport"),
        cycle_id=cycle_id or None,
    )


def _leg_or_fail(claim, stage):
    found = leg(claim, stage)
    if found is None:
        model = ClaimPreauth if stage == "preauth" else ClaimSubmission
        if model.objects.filter(claim=claim).exists():
            raise AdjudicatorError(NO_CORRELATION)
        raise AdjudicatorError(NOT_SENT)
    return found


def process(claim, stage, role, action, remarks="", cycle_id="") -> dict:
    claim = common.get_claim(claim)
    found = _leg_or_fail(claim, stage)
    if found["desk"] == "irdai-payer":
        return irdai_process(claim, found, action, remarks, cycle_id)
    if found["desk"] != "nhcx-payer-service":
        raise _no_desk(claim)
    role = _s(role)
    if not role:
        raise AdjudicatorError(NO_ROLE)
    step = step_for(role)
    if step is None:
        raise AdjudicatorError(UNKNOWN_ROLE.format(role=role))
    spelled = next((a for a in step["actions"] if _norm(a) == _norm(action)), None)
    if spelled is None:
        raise AdjudicatorError(
            ILLEGAL_ACTION.format(
                role=role, actions=", ".join(step["actions"]), action=_s(action)
            )
        )
    profile = common.facility_profile(claim.facility)
    sender = _bare(profile.participant_code) if profile else ""
    tok = token(claim)
    body = {
        "casenumber": found["case_number"],
        "action": spelled,
        "receivercode": found["payer_code"],
        "usecase": step["usecase"],
        "correlationid": found["correlation_id"],
        "sendercode": sender,
        "memberid": found["member_id"],
        "remarks": _s(remarks) or "ok",
    }
    url = (
        _s(getattr(settings, "NHCX_PAYER_SERVICE_PROCESS_CASE_URL", "")) or PROCESS_URL
    )
    status, data, raw = _http("POST", url, headers=_service_headers(tok), body=body)
    service_error = extract_error(data, failed=False) if status < HTTP_REDIRECT else ""
    reply = {
        "success": status < HTTP_REDIRECT and not service_error,
        "status": status,
        "action": spelled,
        "role": step["role"],
        "usecase": step["usecase"],
        "correlationId": found["correlation_id"],
        "request": body,
        "response": data,
        "raw": raw if data is None else None,
        "transport": "nhcx-payer-service",
    }
    if not reply["success"]:
        reply["error"] = (
            service_error
            or extract_error(data, failed=True)
            or f"the payer service returned {status}: {raw[:200]}"
        )
    _record(claim, found, reply, remarks, cycle_id)
    return reply


def irdai_process(claim, found, action, remarks, cycle_id) -> dict:
    action = _s(action).lower()
    if action not in DECISION_INDEX:
        raise AdjudicatorError(IRDAI_ACTION.format(action=action))
    if action in {"reject", "query"} and not _s(remarks):
        raise AdjudicatorError(IRDAI_REMARKS)
    case, desk_token = _irdai_case(claim, found["case_number"], found["correlation_id"])
    status, data, raw = _http(
        "POST",
        f"{DESK}/cases/{case.get('id')}/adjudicate",
        headers={"Authorization": "Bearer " + desk_token},
        body={"action": action, "remarks": _s(remarks)},
    )
    reply = {
        "success": status < HTTP_REDIRECT,
        "status": status,
        "action": action,
        "role": "Adjudicator",
        "usecase": _s(case.get("stage")),
        "correlationId": found["correlation_id"],
        "response": data,
        "raw": raw if data is None else None,
        "transport": "irdai-payer",
        "cycle_id": cycle_id or None,
    }
    if not reply["success"]:
        reply["error"] = (
            extract_error(data, failed=True) or f"HTTP {status}: {raw[:200]}"
        )
    _record(claim, found, reply, remarks, cycle_id)
    return reply


def _await_move(claim, found, seen, role):
    """The payer service moves a forwarded case a few seconds after it answers."""
    if not (seen and role and _norm(seen[-1]) == _norm(role)):
        return role
    tries = int(getattr(settings, "NHCX_ADJUDICATOR_ROLE_SETTLE_TRIES", 5))
    pause = float(getattr(settings, "NHCX_ADJUDICATOR_ROLE_SETTLE_SECONDS", 3))
    for _ in range(tries):
        time.sleep(pause)
        now = _s(role_for(claim, found["case_number"], found["payer_code"]).get("role"))
        if _norm(now) != _norm(role):
            return now
    return role


def cycle(claim, stage, decision, remarks="") -> dict:
    claim = common.get_claim(claim)
    decision = _s(decision).lower()
    if decision not in DECISION_INDEX:
        raise AdjudicatorError(BAD_DECISION)
    found = leg(claim, stage)
    if found is None:
        raise AdjudicatorError(NOT_SENT)
    if found["desk"] == "irdai-payer":
        cid = str(uuid.uuid4())
        reply = irdai_process(claim, found, decision, remarks, cid)
        return {
            "cycle_id": cid,
            "decision": decision,
            "steps": [
                {
                    "role": reply["role"],
                    "action": decision,
                    "success": reply["success"],
                    "error": reply.get("error"),
                }
            ],
            "stopped": "decided" if reply["success"] else "refused",
            "final_role": None,
        }
    if found["desk"] != "nhcx-payer-service":
        raise _no_desk(claim)
    cid = str(uuid.uuid4())
    steps, seen = [], []
    stopped, final_role = "exhausted", None
    for _ in range(8):
        lookup = role_for(claim, found["case_number"], found["payer_code"])
        role = _s(lookup.get("role"))
        final_role = role or None
        if lookup.get("error") and not role:
            steps.append(
                {
                    "role": None,
                    "action": None,
                    "success": False,
                    "error": lookup["error"],
                }
            )
            stopped = "role-unreadable"
            break
        role = _await_move(claim, found, seen, role)
        final_role = role or None
        if not role:
            stopped = "no-role"
            break
        step = step_for(role)
        if step is None:
            steps.append(
                {
                    "role": role,
                    "action": None,
                    "success": False,
                    "error": lookup.get("warning"),
                }
            )
            stopped = "unknown-role"
            break
        if seen and _norm(seen[-1]) == _norm(role):
            stopped = "not-moved"
            break
        seen.append(role)
        action = DECISIONS[step["role"]][DECISION_INDEX[decision]]
        reply = process(claim, stage, role, action, remarks, cid)
        steps.append(
            {
                "role": reply.get("role") or role,
                "action": reply.get("action") or action,
                "success": reply["success"],
                "error": reply.get("error"),
            }
        )
        if not reply["success"]:
            stopped = "refused"
            break
        if decision != "approve" and step["role"] != "CEX-Trust":
            stopped = "decided"
            break
        if step["role"] == "Claim Review Committee" or (
            stage == "preauth" and step["role"] == "PPD-Trust"
        ):
            stopped = "completed"
            break
    return {
        "cycle_id": cid,
        "decision": decision,
        "steps": steps,
        "stopped": stopped,
        "final_role": final_role,
    }


REASONS = {
    "completed": "the case went through every role",
    "decided": "the decision was taken at the role holding it",
    "no-role": "nobody holds the case any more",
    "not-moved": "the payer service kept the case at the same role",
    "refused": "the payer service refused the last action",
    "role-unreadable": "the role could not be read",
    "unknown-role": "the role holding it is not in the published workflow",
    "exhausted": "the step limit was reached",
}


def cycle_flash(result) -> str:
    taken = ", ".join(
        f"{s['action']} as {s['role']}" for s in result["steps"] if s.get("action")
    )
    tail = f" Taken: {taken}." if taken else " Nothing was taken."
    return f"Cycle {result['stopped']}: {REASONS.get(result['stopped'], '')}.{tail}"


def adjudicate(claim, data) -> dict:
    """The API door: {action: role|process|cycle, stage, role?, decision?, remarks?}."""
    action = _s(data.get("action")) or "role"
    stage = _s(data.get("stage")) or "preauth"
    if action == "role":
        return {"reply": read_role(claim, stage)}
    if action == "cycle":
        result = cycle(claim, stage, data.get("decision"), data.get("remarks"))
        ok = result["stopped"] in {"completed", "decided", "no-role"}
        return {"cycle": result, "message": cycle_flash(result), "success": ok}
    reply = process(
        claim,
        stage,
        data.get("role"),
        data.get("take") or data.get("decision"),
        data.get("remarks"),
    )
    msg = (
        "Decision sent to the payer service."
        if reply["success"]
        else (reply.get("error") or "The payer service refused it.")
    )
    return {"reply": reply, "message": msg, "success": reply["success"]}
