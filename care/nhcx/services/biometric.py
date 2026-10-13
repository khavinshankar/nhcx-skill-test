"""A18 biometric authentication: plain JSON calls to the ABDM biometric hosts
with the gateway's session token (G3); tokens live only in D31.

Registers the ``extra_headers`` hook (A2 sends carry the stage-Preauth token).
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta

import requests
from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from care.nhcx.models import BiometricAuth
from care.nhcx.models.abha import abha_digits, get_abha_number
from care.nhcx.services import common, hooks, payers

logger = logging.getLogger(__name__)

BIO_BASE = "https://apisbx.abdm.gov.in/hcx/abha/biometric"
FACE_BASE = "https://apisbx.abdm.gov.in/pmjay/sbxhcx/abdmproxy/abha/biometric"
FACE_QR = "https://phrsbx.abdm.gov.in/face-auth"
TOKEN_HEADER = "x-hcx-user-token"
TIMEOUT = 30
HTTP_BAD_REQUEST = 400
ABHA_DIGITS = 14

NO_PATIENT = "Choose a patient."
NO_PAYER = "Choose the payer the authentication is for."
NO_ABHA = "A fingerprint or iris authentication names the ABHA number, 14 digits."
NO_PID = {
    "FINGERPRINT": "Capture the fingerprint on the device and send its PID block.",
    "IRIS": "Capture the iris on the device and send its PID block.",
}
NO_AADHAAR = "An Aadhaar number has 12 digits."
REFRESH_LAPSED = "The refresh token has lapsed; authenticate the beneficiary again."
BAD_METHOD = "Choose fingerprint, iris or face authentication."
BAD_STAGE = "Choose the stage the authentication is for."
NOT_FOUND = "That authentication attempt is not on this claim."
FACE_ONLY = "Only a face authentication is captured on the phone."
NO_ANSWER = "The biometric service did not answer."

SCOPES = {
    "FINGERPRINT": ["abha-login", "aadhaar-bio-verify"],
    "IRIS": ["abha-login", "aadhaar-iris-verify"],
    "FACE_AUTH": ["abha-enrol", "face-auth"],
}


class BiometricError(common.ServiceRefusal):
    pass


def _s(value) -> str:
    return "" if value is None else str(value).strip()


def bio_base() -> str:
    return (_s(getattr(settings, "NHCX_BIOMETRIC_BASE_URL", "")) or BIO_BASE).rstrip(
        "/"
    )


def face_base() -> str:
    return (_s(getattr(settings, "NHCX_FACEAUTH_BASE_URL", "")) or FACE_BASE).rstrip(
        "/"
    )


def face_qr() -> str:
    return _s(getattr(settings, "NHCX_FACEAUTH_QR_URL", "")) or FACE_QR


def token_header() -> str:
    return _s(getattr(settings, "NHCX_BIOMETRIC_TOKEN_HEADER", "")) or TOKEN_HEADER


def hyphenate(abha: str) -> str:
    d = abha_digits(abha)
    return f"{d[:2]}-{d[2:6]}-{d[6:10]}-{d[10:14]}" if len(d) == ABHA_DIGITS else d


def session_token() -> str:
    from care.nhcx.gateway import get_gateway

    try:
        answer = get_gateway().token()
    except Exception as e:
        raise BiometricError(getattr(e, "message", None) or str(e) or NO_ANSWER) from e
    return _s(answer.get("token") if isinstance(answer, dict) else answer)


def abdm_headers(payer_code, stage, *, with_process) -> dict:
    h = {
        "Authorization": "Bearer " + session_token(),
        "Content-Type": "application/json",
    }
    if with_process:
        h["process"] = stage
        h["payerid"] = payer_code
    return h


def face_headers(h) -> dict:
    h["REQUEST-ID"] = str(uuid.uuid4())
    h["TIMESTAMP"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    return h


def _reason(body, status) -> str:
    if isinstance(body, dict):
        for key in ("message", "errorMessage", "error_description", "detail"):
            if isinstance(body.get(key), str) and body[key].strip():
                code = body.get("code") or body.get("errorCode")
                return f"{code}: {body[key].strip()}" if code else body[key].strip()
        err = body.get("error")
        if isinstance(err, dict):
            return _reason(err, status)
        if isinstance(err, str) and err.strip():
            return err.strip()
    return f"HTTP {status}" if status else NO_ANSWER


def _call(method, url, headers, body=None):
    try:
        resp = requests.request(
            method, url, headers=headers, json=body, timeout=TIMEOUT
        )
    except requests.RequestException as e:
        msg = f"{NO_ANSWER} ({type(e).__name__})"
        raise BiometricError(msg) from e
    try:
        data = resp.json()
    except ValueError:
        data = {}
    if not isinstance(data, dict):
        data = {"value": data}
    if resp.status_code >= HTTP_BAD_REQUEST:
        raise BiometricError(_reason(data, resp.status_code))
    return data


def _fail(row, message):
    row.status = "failed"
    row.message = message
    row.save()
    raise BiometricError(message)


def stage_for(claim) -> str:
    """Preauth while admitted (or before); Discharge once the encounter is discharged."""
    encounter = getattr(claim, "encounter", None)
    status = _s(getattr(encounter, "status", "")).lower()
    period = getattr(encounter, "period", None) or {}
    if status in {"discharged", "completed"} or (
        isinstance(period, dict) and period.get("end")
    ):
        return "Discharge"
    from care.nhcx.models import ClaimSubmission

    if (
        ClaimSubmission.objects.filter(claim=claim)
        .exclude(discharge_mode__isnull=True)
        .exclude(discharge_mode="")
        .exists()
    ):
        return "Discharge"
    return "Preauth"


def init(
    claim, method, *, stage=None, abha_no=None, user=None, payer_code=None
) -> tuple:
    claim = common.get_claim(claim)
    if claim.patient_id is None:
        raise BiometricError(NO_PATIENT)
    payer = _s(payer_code) or _s(claim.payer_id) or common.default_payer_code()
    if not payer:
        raise BiometricError(NO_PAYER)
    method = _s(method).upper()
    if method not in SCOPES:
        raise BiometricError(BAD_METHOD)
    stage = _s(stage) or stage_for(claim)
    if stage not in {"Preauth", "Discharge"}:
        raise BiometricError(BAD_STAGE)
    abha = abha_digits(
        abha_no or claim.abha_number or get_abha_number(claim.patient) or ""
    )
    if method != "FACE_AUTH" and len(abha) != ABHA_DIGITS:
        raise BiometricError(NO_ABHA)
    row = BiometricAuth.objects.create(
        patient=claim.patient,
        claim=claim,
        payer_code=payer,
        stage=stage,
        method=method,
        status="initiated",
        abha_number=abha or None,
        requested_by=user if getattr(user, "pk", None) else None,
    )
    try:
        if method == "FACE_AUTH":
            answer = _call(
                "POST",
                face_base() + "/faceauth/init",
                face_headers(abdm_headers(payer, stage, with_process=False)),
                {"scope": SCOPES[method]},
            )
        else:
            answer = _call(
                "POST",
                bio_base() + "/auth/init",
                abdm_headers(payer, stage, with_process=True),
                {
                    "scope": SCOPES[method],
                    "loginHint": "abha-number",
                    "loginId": hyphenate(abha),
                    "otpSystem": "aadhaar",
                    "authMode": method,
                },
            )
    except BiometricError as e:
        _fail(row, e.message)
    txn = _s(answer.get("txnId"))
    if not txn:
        _fail(row, _reason(answer, 0))
    row.txn_id = txn
    row.message = _s(answer.get("message")) or None
    row.save()
    qr = f"{face_qr()}?txnId={txn}" if method == "FACE_AUTH" else None
    return row, qr


def attempt(claim, attempt_id) -> BiometricAuth:
    qs = BiometricAuth.objects.filter(claim=claim)
    value = _s(attempt_id)
    try:
        row = (
            qs.filter(id=int(value)).first()
            if value.isdigit()
            else qs.filter(external_id=value).first()
        )
    except Exception:
        row = None
    if row is None:
        raise BiometricError(NOT_FOUND)
    return row


def capture(row) -> tuple:
    if row.method != "FACE_AUTH":
        raise BiometricError(FACE_ONLY)
    answer = _call(
        "POST",
        face_base() + "/capture/pid",
        face_headers(abdm_headers(row.payer_code, row.stage, with_process=False)),
        {"txnId": row.txn_id},
    )
    status = _s(answer.get("status")).upper()
    if status == "COMPLETE" and row.status == "initiated":
        row.status = "captured"
        row.save()
    return row, status


def _seconds(value, default):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def verify(row, *, pid="", aadhaar_encrypted="", mobile="") -> BiometricAuth:
    if row.method == "FACE_AUTH":
        sealed = _s(aadhaar_encrypted)
        if not sealed or sealed.isdigit():
            raise BiometricError(NO_AADHAAR)
        url = face_base() + "/v2/auth/verify"
        headers = face_headers(
            abdm_headers(row.payer_code, row.stage, with_process=True)
        )
        body = {
            "authData": {
                "authMethods": ["face_auth"],
                "face": {"txnId": row.txn_id, "aadhaar": sealed, "mobile": _s(mobile)},
            },
            "authMode": "FACE_AUTH",
        }
    else:
        if not _s(pid):
            raise BiometricError(NO_PID[row.method])
        key = "bio" if row.method == "FINGERPRINT" else "iris"
        pid_key = "fingerPrintAuthPid" if row.method == "FINGERPRINT" else "irisAuthPid"
        url = bio_base() + "/auth/verify"
        headers = abdm_headers(row.payer_code, row.stage, with_process=True)
        body = {
            "scope": SCOPES[row.method],
            "authData": {
                "authMethods": [key],
                key: {"txnId": row.txn_id, pid_key: pid},
            },
            "authMode": row.method,
        }
    try:
        answer = _call("POST", url, headers, body)
    except BiometricError as e:
        _fail(row, e.message)
    tokens = answer.get("tokens") if isinstance(answer.get("tokens"), dict) else answer
    result = answer.get("authResult")
    if (result is not None and _s(result).lower() != "success") or not _s(
        tokens.get("token")
    ):
        _fail(row, _reason(answer, 0))
    now = timezone.now()
    row.status = "verified"
    row.user_token = _s(tokens.get("token"))
    row.token_expires_at = now + timedelta(
        seconds=_seconds(tokens.get("expiresIn"), 1800)
    )
    row.refresh_token = _s(tokens.get("refreshToken")) or None
    row.refresh_expires_at = now + timedelta(
        seconds=_seconds(tokens.get("refreshExpiresIn"), 1296000)
    )
    accounts = (
        answer.get("accounts") if isinstance(answer.get("accounts"), list) else []
    )
    profile = (
        answer.get("ABHAProfile") if isinstance(answer.get("ABHAProfile"), dict) else {}
    )
    matched = (
        accounts[0].get("ABHANumber")
        if accounts and isinstance(accounts[0], dict)
        else None
    ) or profile.get("ABHANumber")
    row.abha_number = abha_digits(matched or row.abha_number or "") or None
    row.message = _s(answer.get("message")) or None
    row.verified_at = now
    row.save()
    return row


def refresh(row) -> BiometricAuth:
    now = timezone.now()
    if (
        not row.refresh_token
        or not row.refresh_expires_at
        or row.refresh_expires_at <= now
    ):
        raise BiometricError(REFRESH_LAPSED)
    headers = abdm_headers(row.payer_code, row.stage, with_process=True)
    headers["R-token"] = "Bearer " + row.refresh_token
    answer = _call("GET", bio_base() + "/auth/refresh/token", headers)
    if not _s(answer.get("token")):
        raise BiometricError(_reason(answer, 0))
    row.user_token = _s(answer["token"])
    row.token_expires_at = now + timedelta(
        seconds=_seconds(answer.get("expiresIn"), 1800)
    )
    if _s(answer.get("refreshToken")):
        row.refresh_token = _s(answer["refreshToken"])
        row.refresh_expires_at = now + timedelta(
            seconds=_seconds(answer.get("refreshExpiresIn"), 1296000)
        )
    row.save()
    return row


def _current_qs(patient_id, payer_code, stage):
    now = timezone.now()
    return BiometricAuth.objects.filter(
        patient_id=patient_id, payer_code=payer_code, stage=stage, status="verified"
    ).filter(Q(token_expires_at__gt=now) | Q(refresh_expires_at__gt=now))


def current(claim, stage):
    payer = _s(claim.payer_id) or common.default_payer_code()
    if claim.patient_id is None or not payer:
        return None
    return (
        _current_qs(claim.patient_id, payer, stage)
        .order_by("-created_date", "-id")
        .first()
    )


def headers_for(claim, stage) -> dict:
    row = current(claim, stage)
    if row is None:
        return {}
    if row.token_expires_at is None or row.token_expires_at <= timezone.now():
        try:
            refresh(row)
        except Exception:
            logger.info("nhcx: biometric refresh failed claim=%s", claim.claim_no)
            return {}
    out = {token_header(): row.user_token}
    if row.abha_number:
        out["x-hcx-ben-abha-id"] = row.abha_number
    return out


def describe(row) -> dict:
    """An attempt as the API shows it; tokens never leave the server."""
    now = timezone.now()
    return {
        "id": str(row.external_id),
        "stage": row.stage,
        "method": row.method,
        "status": row.status,
        "payer_code": row.payer_code,
        "txn_id": row.txn_id,
        "abha_number": row.abha_number,
        "message": row.message,
        "token_valid": bool(
            row.status == "verified"
            and row.token_expires_at
            and row.token_expires_at > now
        ),
        "token_expires_at": row.token_expires_at,
        "refresh_expires_at": row.refresh_expires_at,
        "verified_at": row.verified_at,
        "created_date": row.created_date,
    }


def listing(claim) -> dict:
    claim = common.get_claim(claim)
    rows = BiometricAuth.objects.filter(claim=claim).order_by("-created_date", "-id")
    pre = current(claim, "Preauth")
    dis = current(claim, "Discharge")
    return {
        "required": payers.adapter_for_claim(claim).biometric_required,
        "header": token_header(),
        "stage": stage_for(claim),
        "attempts": [describe(r) for r in rows],
        "preauth": describe(pre) if pre else None,
        "discharge": describe(dis) if dis else None,
    }


def _extra_headers(claim, purpose):
    return headers_for(claim, "Preauth")


hooks.register("extra_headers", _extra_headers)
