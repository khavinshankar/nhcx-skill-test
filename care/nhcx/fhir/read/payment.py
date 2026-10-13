"""F13 PaymentNotice and PaymentReconciliation (D21, D22)."""

from care.nhcx.fhir import bundle as fb
from care.nhcx.fhir.inputs import FhirBuildError

NOT_A_NOTICE = "That is not a payment notice."


def _first_coding(concept):
    codings = (concept or {}).get("coding") or []
    return codings[0] if codings else {}


def _amount(money):
    value = (money or {}).get("value")
    return fb.amount(value) if value not in (None, "") else None


def _identifiers(resource):
    value = (resource or {}).get("identifier")
    if isinstance(value, dict):
        return [value]
    return value or []


def claim_number(resource):
    """The CLN-typed identifier's value, else the first untyped one."""
    identifiers = _identifiers(resource)
    for identifier in identifiers:
        codes = [
            c.get("code") for c in (identifier.get("type") or {}).get("coding") or []
        ]
        if "CLN" in codes and identifier.get("value"):
            return identifier["value"]
    for identifier in identifiers:
        if not identifier.get("type") and identifier.get("value"):
            return identifier["value"]
    return ""


def read(bundle):
    """D21 fields with details (D22 rows). Raises FhirBuildError when no notice."""
    bundle = fb.unwrap(bundle)
    notice = fb.find_resource(bundle, "PaymentNotice")
    recon = fb.find_resource(bundle, "PaymentReconciliation")
    task = fb.find_resource(bundle, "Task")
    if notice is None and recon is None:
        raise FhirBuildError(NOT_A_NOTICE)
    entries = fb.entries(bundle)
    first = entries[0].get("resource") if entries else None
    claim_ref = ""
    for resource in (notice, recon, task, first):
        claim_ref = claim_number(resource)
        if claim_ref:
            break
    notice = notice or {}
    recon = recon or {}
    amount = _amount(notice.get("amount"))
    currency = (notice.get("amount") or {}).get("currency")
    if amount is None:
        amount = _amount(recon.get("paymentAmount"))
        currency = (recon.get("paymentAmount") or {}).get("currency")
    status = notice.get("paymentStatus") or {}
    status_coding = _first_coding(status)
    disposition = (
        recon.get("disposition")
        or (task or {}).get("description")
        or status_coding.get("display")
        or status.get("text")
        or recon.get("outcome")
        or "Payment notice"
    )
    details = []
    for n, detail in enumerate(recon.get("detail") or [], start=1):
        dtype = detail.get("type") or {}
        coding = _first_coding(dtype)
        details.append(
            {
                "seq": n,
                "reference": detail.get("id")
                or (detail.get("identifier") or {}).get("value")
                or "",
                "type_code": coding.get("code") or "",
                "type_display": coding.get("display") or dtype.get("text") or "",
                "date": detail.get("date") or "",
                "amount": _amount(detail.get("amount")),
            }
        )
    return {
        "claim_ref": claim_ref,
        "notice_id": notice.get("id") or "",
        "amount": amount,
        "currency": currency or "INR",
        "payment_status": status_coding.get("code") or "",
        "disposition": disposition,
        "payment_date": recon.get("paymentDate") or (notice.get("created") or "")[:10],
        "utr": (recon.get("paymentIdentifier") or {}).get("value") or "",
        "details": details,
    }
