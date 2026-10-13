"""F1 Bundle: message kinds, wrapping, unwrapping and shared value helpers."""

import base64
import copy
import json
import uuid
from datetime import UTC, date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal

from care.nhcx.fhir.codes import BASE_URL, PROFILES

IST = timezone(timedelta(hours=5, minutes=30))

# kind -> (bundle id, bundle profile, anchor path)
KINDS = {
    "coverage-validation": (
        "coverage-validation-request-generic",
        "CoverageEligibilityRequestBundle",
        "/coverage-eligibility/request",
    ),
    "coverage-benefits": (
        "coverage-benefits-request-generic",
        "CoverageEligibilityRequestBundle",
        "/coverage-eligibility/request",
    ),
    "coverage-discovery": (
        "coverage-discovery-request-generic",
        "CoverageEligibilityRequestBundle",
        "/coverage-eligibility/request",
    ),
    "coverage-auth-requirements": (
        "coverage-authrequirements-request-generic",
        "CoverageEligibilityRequestBundle",
        "/coverage-eligibility/request",
    ),
    "insurance-plan": ("insurance-request-generic", "TaskBundle", "/insurance/request"),
    "preauth": ("preauth-request-generic", "ClaimBundle", "/preauth/request"),
    "enhancement": (
        "preauth-enhancement-request-generic",
        "ClaimBundle",
        "/preauth/enhancement",
    ),
    "preauth-queryupdate": (
        "preauth-queryupdate-request-generic",
        "ClaimBundle",
        "/preauth/queryupdate",
    ),
    "predetermination": (
        "predetermination-request-generic",
        "ClaimBundle",
        "/predetermination/request",
    ),
    "claim": ("claim-request-generic", "ClaimBundle", "/claim/request"),
    "claim-queryupdate": (
        "claim-queryupdate-request-generic",
        "ClaimBundle",
        "/claim/queryupdate",
    ),
    "preauth-cancel": (
        "preauth-cancel-request-generic",
        "TaskBundle",
        "/preauth/cancel",
    ),
    "preauth-status": (
        "preauth-status-request-generic",
        "TaskBundle",
        "/preauth/status",
    ),
    "claim-status": ("claim-status-request-generic", "TaskBundle", "/claim/status"),
    "claim-reprocess": (
        "claim-reprocess-request-generic",
        "TaskBundle",
        "/claim/reprocess",
    ),
    "claim-release": ("claim-release-request-generic", "TaskBundle", "/claim/release"),
    "payment-ack": ("payment-notice-ack-generic", "TaskBundle", "/payment/notice-ack"),
}


def url(path):
    """Absolute NHCX fullUrl / reference for a path such as /patient."""
    return BASE_URL + (path if path.startswith("/") else "/" + path)


def ref(path, display=None):
    out = {"reference": url(path)}
    if display:
        out["display"] = display
    return out


def anchor_url(kind):
    return url(KINDS[kind][2])


def wrap(kind, entries):
    """Wrap (path, resource) pairs into the kind's collection bundle.

    The anchor resource must come first; it is given the anchor fullUrl.
    Other paths are made absolute under https://nhcx.abdm.gov.in.
    """
    bundle_id, bundle_profile, anchor = KINDS[kind]
    out = []
    for i, (path, resource) in enumerate(entries):
        full_url = url(anchor if i == 0 else path)
        out.append({"fullUrl": full_url, "resource": resource})
    return {
        "resourceType": "Bundle",
        "id": bundle_id,
        "meta": {"profile": [PROFILES[bundle_profile]]},
        "type": "collection",
        "entry": out,
    }


def unwrap(payload):
    """Return the bundle dict from a dict or JSON text (a ProtocolResponse too)."""
    if isinstance(payload, bytes | bytearray):
        payload = payload.decode()
    if isinstance(payload, str):
        payload = json.loads(payload) if payload.strip() else {}
    return payload or {}


def entries(bundle):
    return [e for e in (unwrap(bundle).get("entry") or []) if isinstance(e, dict)]


def find_resources(bundle, resource_type):
    return [
        e["resource"]
        for e in entries(bundle)
        if isinstance(e.get("resource"), dict)
        and e["resource"].get("resourceType") == resource_type
    ]


def find_resource(bundle, resource_type, last=False):
    found = find_resources(bundle, resource_type)
    if not found:
        return None
    return found[-1] if last else found[0]


def find_entry(bundle, resource_type, last=False):
    found = [
        e
        for e in entries(bundle)
        if (e.get("resource") or {}).get("resourceType") == resource_type
    ]
    if not found:
        return None
    return found[-1] if last else found[0]


def resolve_reference(bundle, reference):
    """Find the resource a reference points at, by fullUrl or by id."""
    if isinstance(reference, dict):
        reference = reference.get("reference")
    if not reference:
        return None
    for e in entries(bundle):
        if e.get("fullUrl") == reference:
            return e.get("resource")
    key = reference.removeprefix("urn:uuid:")
    tail = key.rstrip("/").rsplit("/", 1)[-1]
    for e in entries(bundle):
        res = e.get("resource") or {}
        rid = str(res.get("id") or "")
        if rid and rid in (key, tail):
            return res
    return None


def is_protocol_response(payload):
    payload = unwrap(payload)
    return payload.get("type") == "ProtocolResponse" or (
        "x-hcx-error_details" in payload and payload.get("resourceType") != "Bundle"
    )


def protocol_error(payload):
    """'<code>: <message>' of a ProtocolResponse, else ''."""
    payload = unwrap(payload)
    details = payload.get("x-hcx-error_details") or {}
    if isinstance(details, str):
        try:
            details = json.loads(details)
        except ValueError:
            return details
    code = details.get("code") or ""
    message = details.get("message") or ""
    return f"{code}: {message}" if code and message else (code or message)


# value helpers


def new_uuid():
    return str(uuid.uuid4())


def _parse(value):
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=IST)
    text = str(value).strip()
    if len(text) == len("YYYY-MM-DD"):
        return datetime.fromisoformat(text).replace(tzinfo=IST)
    return datetime.fromisoformat(text.replace("Z", "+00:00"))  # noqa: FURB162


def to_instant(value):
    """YYYY-MM-DDThh:mm:ss+05:30; a bare date becomes midnight IST."""
    moment = _parse(value)
    if moment is None:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=IST)
    return moment.astimezone(IST).replace(microsecond=0).isoformat()


def to_date(value):
    """YYYY-MM-DD (IST calendar date)."""
    instant = to_instant(value)
    return instant[:10] if instant else None


def now_instant():
    return to_instant(datetime.now(UTC))


def amount(value):
    """Round to 2 decimals; an int when whole."""
    if value is None or value == "":
        return None
    number = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return int(number) if number == number.to_integral_value() else float(number)


def money(value):
    return {"value": amount(value) or 0, "currency": "INR"}


def b64(data):
    if data is None:
        return ""
    if isinstance(data, str):
        return data
    return base64.b64encode(bytes(data)).decode()


def deep_copy(value):
    return copy.deepcopy(value)
