"""F3 CoverageEligibilityResponse: the verdict (D9) and the auth ruling (D13-D15)."""

import re

from care.nhcx.fhir import bundle as fb

FULL_URL = re.compile(r"fullUrl:\s*(\S+)", re.IGNORECASE)
STAGE = re.compile(r"Type:\s*([^\n\r]*)", re.IGNORECASE)
FOR_CODE = re.compile(r"Procedure Code:\s*([^\s,;]+)", re.IGNORECASE)
WALLET_CODES = ("benefit", "30")


def _first_coding(concept):
    codings = (concept or {}).get("coding") or []
    return codings[0] if codings else {}


def _value(money):
    value = (money or {}).get("value")
    return fb.amount(value) if value not in (None, "") else None


def _insurance(response):
    insurance = (response or {}).get("insurance") or []
    return insurance[0] if insurance else {}


def _wallet(items):
    benefits = [b for item in items for b in item.get("benefit") or []]
    for code in WALLET_CODES:
        for benefit in benefits:
            codes = [
                c.get("code") for c in (benefit.get("type") or {}).get("coding") or []
            ]
            if code in codes:
                return benefit
    return benefits[0] if benefits else None


def _patient_fields(resource):
    if not resource:
        return {}
    out = {}
    names = resource.get("name") or []
    if names:
        name = names[0]
        out["beneficiary_name"] = (
            name.get("text") or " ".join(name.get("given") or []) or name.get("family")
        )
    out["patient_gender"] = resource.get("gender")
    out["patient_dob"] = resource.get("birthDate")
    addresses = resource.get("address") or []
    if addresses:
        a = addresses[0]
        parts = [
            *(a.get("line") or []),
            a.get("district"),
            a.get("state"),
            a.get("postalCode"),
        ]
        out["patient_address"] = ", ".join(p for p in parts if p)
    for identifier in resource.get("identifier") or []:
        if _first_coding(identifier.get("type")).get("code") == "ABHA":
            out["abha_number"] = identifier.get("value")
            break
    photos = resource.get("photo") or []
    if photos:
        out["patient_photo"] = photos[0].get("data") or photos[0].get("url")
    return out


def _coverage_fields(resource):
    if not resource:
        return {}
    classes = resource.get("class") or []
    period = resource.get("period") or {}
    relationship = _first_coding(resource.get("relationship"))
    return {
        "plan_name": classes[0].get("name") if classes else None,
        "plan_period_start": period.get("start"),
        "plan_period_end": period.get("end"),
        "relationship": relationship.get("display") or relationship.get("code"),
    }


def read_verdict(bundle):
    """D9 claim fields from an eligibility reply; empty values are left out."""
    bundle = fb.unwrap(bundle)
    response = fb.find_resource(bundle, "CoverageEligibilityResponse", last=True)
    if response is None:
        return {}
    insurance = _insurance(response)
    items = insurance.get("item") or []
    out = {
        "outcome": response.get("outcome"),
        "disposition": response.get("disposition"),
    }
    if "inforce" in insurance:
        out["inforce"] = bool(insurance.get("inforce"))
    for item in items:
        if "authorizationRequired" in item:
            out["auth_required"] = bool(item["authorizationRequired"])
    wallet = _wallet(items)
    if wallet:
        allowed = _value(wallet.get("allowedMoney"))
        used = _value(wallet.get("usedMoney"))
        if allowed is not None or used is not None:
            out["allowed_amount"] = fb.amount((allowed or 0) + (used or 0))
        if used is not None:
            out["used_amount"] = used
    out.update(_patient_fields(fb.find_resource(bundle, "Patient", last=True)))
    out.update(_coverage_fields(fb.find_resource(bundle, "Coverage", last=True)))
    if out.get("outcome") == "error":
        out["status"] = "error"
    else:
        out["status"] = "eligible" if out.get("inforce") else "not-eligible"
    return {k: v for k, v in out.items() if v not in (None, "", [], {})}


def parse_requirement_text(text):
    """(form_url, stage, for_code) from an authorizationSupporting text."""
    text = text or ""
    form = FULL_URL.search(text)
    stage = STAGE.search(text)
    for_code = FOR_CODE.search(text)
    return (
        form.group(1) if form else "",
        stage.group(1).strip().lower() if stage else "",
        for_code.group(1) if for_code else "",
    )


def read_auth(bundle, preauth_stages=("pre",)):
    """D13 ruling with D14 items and D15 requirements, from the last response."""
    bundle = fb.unwrap(bundle)
    response = fb.find_resource(bundle, "CoverageEligibilityResponse", last=True)
    if response is None:
        return {}
    insurance = _insurance(response)
    ruling = {
        "outcome": response.get("outcome"),
        "disposition": response.get("disposition"),
        "inforce": bool(insurance.get("inforce")),
        "status": "ready",
    }
    items, requirements, seen = [], [], set()
    for n, item in enumerate(insurance.get("item") or [], start=1):
        product = item.get("productOrService") or {}
        product_coding = _first_coding(product)
        code = product_coding.get("code") or ""
        benefits = item.get("benefit") or []
        benefit = benefits[0] if benefits else {}
        items.append(
            {
                "seq": n,
                "code": code,
                "display": product_coding.get("display") or product.get("text") or "",
                "category_code": _first_coding(item.get("category")).get("code") or "",
                "auth_required": bool(item.get("authorizationRequired")),
                "excluded": bool(item.get("excluded")),
                "benefit_type": _first_coding(benefit.get("type")).get("code") or "",
                "allowed_amount": _value(benefit.get("allowedMoney")),
            }
        )
        for supporting in item.get("authorizationSupporting") or []:
            req_coding = _first_coding(supporting)
            form_url, stage, for_code = parse_requirement_text(supporting.get("text"))
            kind = "form" if form_url else "document"
            if kind == "document" and not stage:
                stage = "pre"
            key = (kind, req_coding.get("code") or "", form_url)
            if key in seen:
                continue
            seen.add(key)
            requirements.append(
                {
                    "seq": len(requirements) + 1,
                    "kind": kind,
                    "code": req_coding.get("code") or "",
                    "display": req_coding.get("display") or "",
                    "form_url": form_url,
                    "stage": stage,
                    "for_code": for_code or code,
                    "at_preauth": kind == "form" or stage in preauth_stages,
                }
            )
    ruling["items"] = items
    ruling["requirements"] = requirements
    return ruling


def read(bundle, preauth_stages=("pre",)):
    """Verdict plus, when the reply is an auth-requirements ruling, the ruling."""
    bundle = fb.unwrap(bundle)
    out = {"verdict": read_verdict(bundle), "auth": None}
    response = fb.find_resource(bundle, "CoverageEligibilityResponse", last=True)
    if response and "auth-requirements" in (response.get("purpose") or []):
        out["auth"] = read_auth(bundle, preauth_stages)
    return out
