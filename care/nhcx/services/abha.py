"""A19 ABHA create and verify (ABDM M1), run on the server.

The calls follow the nhcx-docs MCP ids ``hiecm.flow.m1-create-abha-aadhaar-otp``
and ``hiecm.flow.m1-login-by-mobile`` (and their operations). The gateway session
token, the X-token and the T-token stay in the Django cache, keyed by the flow's
``txnId`` and the signed-in user, for fifteen minutes. The page only ever holds
``txn_id``. Values the page has already sealed under the service certificate
are passed through as they are. Plain digits are checked, then sealed here.
"""

from __future__ import annotations

import base64
import logging
import re
import uuid
from datetime import UTC, datetime

import requests
from django.conf import settings
from django.core.cache import cache

from care.nhcx.models.abha import abha_digits, set_abha
from care.nhcx.services.common import ServiceRefusal

logger = logging.getLogger("care.nhcx.abha")

DEFAULT_BASE = "https://abhasbx.abdm.gov.in/abha/api/v3"
TIMEOUT = 30
HTTP_UNAUTHORIZED = 401
HTTP_REDIRECT = 300
STATE_TTL = 15 * 60
CERT_TTL = 60 * 60
CERT_KEY = "nhcx:abha:certificate"

AADHAAR_12 = "An Aadhaar number has 12 digits."
ASK_OTP = "Ask for the OTP first."
ENTER_OTP = "Enter the OTP that was sent."
MOBILE_10 = "A mobile number has 10 digits."
ABHA_14 = "An ABHA number has 14 digits."
ABHA_OR_MOBILE = "Enter the ABHA number, or the mobile it is registered against."
BAD_ADDRESS = "An ABHA address is 8 to 18 letters, digits, dots or underscores."
CHOOSE_ACCOUNT = "Choose one of the accounts listed."
LAPSED = "The login has lapsed; ask for the OTP again."
NOT_VERIFIED = "The ABHA service did not verify the OTP: "
NO_ANSWER = "The ABHA service did not answer."
NO_PATIENT = "No such patient."
NOT_LINKED = "Verify or create the ABHA before linking it."

GENDERS = {"M": "Male", "F": "Female", "O": "Other", "T": "Other"}
ADDRESS_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._]{7,17}$")


def base_url() -> str:
    return (getattr(settings, "NHCX_ABHA_BASE_URL", "") or DEFAULT_BASE).rstrip("/")


def _digits(value) -> str:
    return re.sub(r"\D", "", str(value or ""))


def _is_plain(value) -> bool:
    return bool(re.fullmatch(r"[\d\s-]+", str(value or "").strip()))


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.") + (
        f"{datetime.now(UTC).microsecond // 1000:03d}Z"
    )


# ---- service calls ----


def _session_token(refresh=False) -> str:
    from care.nhcx.gateway import get_gateway

    gw = get_gateway()
    try:
        answer = gw.refresh_token() if refresh else gw.token()
    except Exception as e:
        raise ServiceRefusal(getattr(e, "message", None) or str(e) or NO_ANSWER) from e
    return str(answer.get("token") if isinstance(answer, dict) else answer or "")


def _reason(data, status) -> str:
    """The service's ``error.code`` and ``error.message``, else the field it named."""
    if isinstance(data, list) and data and isinstance(data[0], dict):
        data = {"error": data[0]}
    if not isinstance(data, dict):
        return f"{NO_ANSWER} (HTTP {status})"
    err = data.get("error")
    if isinstance(err, dict) and (err.get("code") or err.get("message")):
        code = str(err.get("code") or "").strip().rstrip(":").strip()
        message = str(err.get("message") or "").strip()
        return f"{code}: {message}" if code and message else code or message
    for key, value in data.items():
        if key in {"timestamp", "code", "description", "example"}:
            continue
        if isinstance(value, str) and value:
            return value
    if data.get("message"):
        return str(data["message"])
    return f"{NO_ANSWER} (HTTP {status})"


def call(method, path, body=None, extra=None):
    """One ABHA service call with a fresh REQUEST-ID and TIMESTAMP; a 401 refreshes
    the gateway session token once and retries."""
    for attempt in (0, 1):
        headers = {
            "Authorization": "Bearer " + _session_token(refresh=attempt == 1),
            "REQUEST-ID": str(uuid.uuid4()),
            "TIMESTAMP": _now(),
            "Content-Type": "application/json",
        }
        headers.update(extra or {})
        try:
            resp = requests.request(
                method,
                base_url() + path,
                headers=headers,
                json=body,
                timeout=TIMEOUT,
            )
        except requests.RequestException as e:
            msg = f"{NO_ANSWER} ({type(e).__name__})"
            raise ServiceRefusal(msg) from e
        if resp.status_code == HTTP_UNAUTHORIZED and attempt == 0:
            continue
        try:
            data = resp.json()
        except ValueError:
            data = {}
        if resp.status_code >= HTTP_REDIRECT:
            raise ServiceRefusal(_reason(data, resp.status_code))
        return data if isinstance(data, dict) else {"value": data}
    return {}  # pragma: no cover


# ---- sealing ----


def certificate() -> dict:
    """``public_key`` (base64 DER) and ``expires_at``; cached for an hour."""
    held = cache.get(CERT_KEY)
    if held:
        return held
    answer = call("GET", "/profile/public/certificate")
    key = str(answer.get("publicKey") or "").strip()
    if not key:
        raise ServiceRefusal(NO_ANSWER)
    held = {
        "public_key": key,
        "algorithm": answer.get("encryptionAlgorithm")
        or "RSA/ECB/OAEPWithSHA-1AndMGF1Padding",
        "expires_at": datetime.fromtimestamp(
            datetime.now(UTC).timestamp() + CERT_TTL, UTC
        ).isoformat(),
    }
    cache.set(CERT_KEY, held, CERT_TTL)
    return held


def seal(value: str) -> str:
    """RSA/ECB/OAEPWithSHA-1AndMGF1Padding under the service certificate, base64."""
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding

    raw = certificate()["public_key"]
    der = base64.b64decode(
        re.sub(r"-----[^-]+-----|\s", "", raw),
    )
    key = serialization.load_der_public_key(der)
    sealed = key.encrypt(
        str(value).encode(),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA1()),  # noqa: S303
            algorithm=hashes.SHA1(),  # noqa: S303
            label=None,
        ),
    )
    return base64.b64encode(sealed).decode()


def _sealed(value, digits_required, message):
    """Plain digits are checked and sealed here; a value the page sealed passes."""
    if value in (None, ""):
        raise ServiceRefusal(message)
    if _is_plain(value):
        d = _digits(value)
        if digits_required and len(d) != digits_required:
            raise ServiceRefusal(message)
        if not d:
            raise ServiceRefusal(message)
        return seal(d), d
    return str(value).strip(), ""


# ---- server-side flow state ----


def _key(txn_id, user) -> str:
    return f"nhcx:abha:flow:{getattr(user, 'id', None) or 0}:{txn_id}"


def remember(txn_id, user, **state):
    held = cache.get(_key(txn_id, user)) or {}
    held.update(state)
    cache.set(_key(txn_id, user), held, STATE_TTL)


def recall(txn_id, user) -> dict | None:
    if not txn_id:
        return None
    return cache.get(_key(txn_id, user))


def audit(action, subject, detail=""):
    logger.info(
        "abha.%s entity=abha id=%s detail=%s",
        action,
        str(subject or "")[:64],
        str(detail or "")[:200],
    )


# ---- shaping ----


def format_abha(value) -> str:
    d = abha_digits(value) if value else ""
    if len(d) != 14:  # noqa: PLR2004
        return str(value or "")
    return f"{d[:2]}-{d[2:6]}-{d[6:10]}-{d[10:]}"


def _dob(data) -> str:
    dob = str(data.get("dob") or "").strip()
    m = re.fullmatch(r"(\d{1,2})-(\d{1,2})-(\d{4})", dob)
    if m:
        return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
    day, month, year = (
        data.get("dayOfBirth"),
        data.get("monthOfBirth"),
        data.get("yearOfBirth"),
    )
    if _digits(year) and _digits(month) and _digits(day):
        return f"{_digits(year)}-{int(_digits(month)):02d}-{int(_digits(day)):02d}"
    return dob


def profile_from(data) -> dict:
    data = data or {}
    name = str(data.get("name") or "").strip() or " ".join(
        str(data.get(k) or "").strip()
        for k in ("firstName", "middleName", "lastName")
        if str(data.get(k) or "").strip()
    )
    address = data.get("preferredAbhaAddress") or ""
    if not address:
        phr = data.get("phrAddress") or []
        address = phr[0] if isinstance(phr, list) and phr else ""
    mobile = str(data.get("mobile") or "")
    return {
        "abha_no": format_abha(data.get("ABHANumber") or data.get("healthIdNumber")),
        "abha_address": address,
        "name": name,
        "gender": GENDERS.get(str(data.get("gender") or "").upper()[:1], ""),
        "dob": _dob(data),
        "mobile": "" if "*" in mobile or "x" in mobile.lower() else _digits(mobile),
        "status": data.get("status") or "",
    }


def account_from(data) -> dict:
    return {
        "abha_no": str(data.get("ABHANumber") or ""),
        "name": data.get("name") or "",
        "abha_address": data.get("preferredAbhaAddress") or "",
        "status": data.get("status") or "",
    }


def profile_with(x_token) -> dict:
    return profile_from(
        call("GET", "/profile/account", extra={"X-token": "Bearer " + x_token})
    )


# ---- create from an Aadhaar OTP ----


def enrol_otp(user, aadhaar, txn_id=None) -> dict:
    sealed, d = _sealed(aadhaar, 12, AADHAAR_12)
    body = {
        "scope": ["abha-enrol"],
        "loginHint": "aadhaar",
        "loginId": sealed,
        "otpSystem": "aadhaar",
    }
    if txn_id:
        body["txnId"] = txn_id
    answer = call("POST", "/enrollment/request/otp", body)
    txn = answer.get("txnId") or txn_id or ""
    remember(txn, user, flow="enrol")
    audit("enrol_otp_sent", txn, "aadhaar ending " + d[8:] if d else "aadhaar sealed")
    return {"txn_id": txn, "message": answer.get("message") or ""}


def enrol_verify(user, txn_id, otp, mobile=None) -> dict:
    if not txn_id:
        raise ServiceRefusal(ASK_OTP)
    if recall(txn_id, user) is None:
        raise ServiceRefusal(LAPSED)
    sealed, _ = _sealed(otp, 0, ENTER_OTP)
    block = {"txnId": txn_id, "otpValue": sealed}
    if mobile:
        m = _digits(mobile)[-10:]
        if len(m) != 10:  # noqa: PLR2004
            raise ServiceRefusal(MOBILE_10)
        block["mobile"] = m
    answer = call(
        "POST",
        "/enrollment/enrol/byAadhaar",
        {
            "authData": {"authMethods": ["otp"], "otp": block},
            "consent": {"code": "abha-enrollment", "version": "1.4"},
        },
    )
    profile = profile_from(answer.get("ABHAProfile") or answer)
    txn = answer.get("txnId") or txn_id
    tokens = answer.get("tokens") or {}
    remember(
        txn,
        user,
        flow="enrol",
        token=tokens.get("token") or "",
        x=True,
        profile=profile,
    )
    is_new = bool(answer.get("isNew"))
    audit("enrolled", profile["abha_no"], f"new={is_new}")
    return {
        "txn_id": txn,
        "is_new": is_new,
        "profile": profile,
        "message": answer.get("message") or "",
    }


def suggestions(user, txn_id) -> dict:
    if recall(txn_id, user) is None:
        raise ServiceRefusal(LAPSED)
    answer = call(
        "GET", "/enrollment/enrol/suggestion", extra={"TRANSACTION_ID": txn_id}
    )
    return {"txn_id": txn_id, "addresses": answer.get("abhaAddressList") or []}


def enrol_address(user, txn_id, address) -> dict:
    state = recall(txn_id, user)
    if state is None:
        raise ServiceRefusal(LAPSED)
    a = str(address or "").strip()
    for suffix in ("@sbx", "@abdm"):
        if a.lower().endswith(suffix):
            a = a[: -len(suffix)]
    if not ADDRESS_RE.fullmatch(a):
        raise ServiceRefusal(BAD_ADDRESS)
    answer = call(
        "POST",
        "/enrollment/enrol/abha-address",
        {"txnId": txn_id, "abhaAddress": a, "preferred": 1},
    )
    number = format_abha(answer.get("healthIdNumber"))
    chosen = answer.get("preferredAbhaAddress") or a
    profile = dict(state.get("profile") or {})
    if number:
        profile["abha_no"] = number
    profile["abha_address"] = chosen
    remember(txn_id, user, profile=profile)
    audit("address_set", number, chosen)
    return {"txn_id": txn_id, "abha_no": number, "abha_address": chosen}


# ---- verify an existing ABHA ----


def login_otp(user, abha_no=None, mobile=None) -> dict:
    if abha_no:
        hint = "abha-number"
        sealed, _ = _sealed(abha_no, 14, ABHA_14)
    elif mobile:
        hint = "mobile"
        if _is_plain(mobile):
            mobile = _digits(mobile)[-10:] if len(_digits(mobile)) > 10 else mobile  # noqa: PLR2004
        sealed, _ = _sealed(mobile, 10, MOBILE_10)
    else:
        raise ServiceRefusal(ABHA_OR_MOBILE)
    answer = call(
        "POST",
        "/profile/login/request/otp",
        {
            "scope": ["abha-login", "mobile-verify"],
            "loginHint": hint,
            "loginId": sealed,
            "otpSystem": "abdm",
        },
    )
    txn = answer.get("txnId") or ""
    remember(txn, user, flow="login", hint=hint)
    audit("login_otp_sent", txn, hint)
    return {"txn_id": txn, "message": answer.get("message") or "", "hint": hint}


def login_verify(user, txn_id, otp) -> dict:
    if not txn_id:
        raise ServiceRefusal(ASK_OTP)
    state = recall(txn_id, user)
    if state is None:
        raise ServiceRefusal(LAPSED)
    sealed, _ = _sealed(otp, 0, ENTER_OTP)
    answer = call(
        "POST",
        "/profile/login/verify",
        {
            "scope": ["abha-login", "mobile-verify"],
            "authData": {
                "authMethods": ["otp"],
                "otp": {"txnId": txn_id, "otpValue": sealed},
            },
        },
    )
    if str(answer.get("authResult") or "").lower() != "success":
        raise ServiceRefusal(NOT_VERIFIED + str(answer.get("message") or ""))
    raw = [a for a in answer.get("accounts") or [] if isinstance(a, dict)]
    accounts = [account_from(a) for a in raw]
    hint = state.get("hint") or "mobile"
    token = answer.get("token") or ""
    if hint == "mobile":
        # T-token: only good for verify/user
        remember(txn_id, user, token=token, x=False, accounts=raw, hint=hint)
        return {"txn_id": txn_id, "accounts": accounts, "hint": hint}
    profile = None
    if token:
        try:
            profile = profile_with(token)
        except ServiceRefusal:
            profile = None
    if profile is None:
        profile = profile_from(raw[0]) if raw else {}
    remember(
        txn_id, user, token=token, x=True, accounts=raw, hint=hint, profile=profile
    )
    audit("login_verified", txn_id, "by ABHA number")
    return {"txn_id": txn_id, "accounts": accounts, "hint": hint, "profile": profile}


def _choose(accounts, abha_no):
    given = str(abha_no or "").strip()
    if not given:
        return None
    for account in accounts:
        if str(account.get("ABHANumber") or "") == given:
            return account
    typed = _digits(given)
    if len(typed) != 14:  # noqa: PLR2004
        return None
    for account in accounts:
        listed = str(account.get("ABHANumber") or "")
        tail = _digits(listed)
        if tail and typed.endswith(tail):
            return account
    return None


def login_select(user, txn_id, abha_no) -> dict:
    state = recall(txn_id, user)
    if state is None or not state.get("token"):
        raise ServiceRefusal(LAPSED)
    chosen = _choose(state.get("accounts") or [], abha_no)
    if chosen is None:
        raise ServiceRefusal(CHOOSE_ACCOUNT)
    answer = call(
        "POST",
        "/profile/login/verify/user",
        {"ABHANumber": chosen.get("ABHANumber"), "txnId": txn_id},
        extra={"T-token": "Bearer " + state["token"]},
    )
    token = answer.get("token") or ""
    profile = profile_with(token) if token else profile_from(chosen)
    remember(txn_id, user, token=token, x=True, profile=profile)
    audit("login_selected", abha_no, "by mobile")
    return {"txn_id": txn_id, "profile": profile}


def profile(user, txn_id, abha_no=None) -> dict:
    """The verified profile of the flow: chooses the account on the mobile path
    when ``abha_no`` is given, else reads the held X-token's profile."""
    state = recall(txn_id, user)
    if state is None:
        raise ServiceRefusal(LAPSED)
    if not state.get("x"):
        return login_select(user, txn_id, abha_no)
    if state.get("profile"):
        return {"txn_id": txn_id, "profile": state["profile"]}
    if not state.get("token"):
        raise ServiceRefusal(LAPSED)
    found = profile_with(state["token"])
    remember(txn_id, user, profile=found)
    return {"txn_id": txn_id, "profile": found}


def link(user, txn_id, patient) -> dict:
    """Write the verified ABHA number and address onto the patient (D3)."""
    state = recall(txn_id, user)
    if state is None:
        raise ServiceRefusal(LAPSED)
    found = state.get("profile") if state.get("x") else None
    if not found or not found.get("abha_no"):
        raise ServiceRefusal(NOT_LINKED)
    try:
        set_abha(
            patient,
            number=format_abha(found["abha_no"]),
            address=found.get("abha_address") or None,
        )
    except ValueError as e:
        raise ServiceRefusal(str(e)) from e
    audit("linked", found["abha_no"], str(patient.external_id))
    cache.delete(_key(txn_id, user))
    return {
        "txn_id": txn_id,
        "abha_no": found["abha_no"],
        "abha_address": found.get("abha_address") or "",
        "patient_id": str(patient.external_id),
    }
