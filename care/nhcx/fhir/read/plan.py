"""F5 InsurancePlan (D10, D11) and F6 Questionnaire (D12)."""

from care.nhcx.fhir import bundle as fb

EMPTY_MESSAGE = (
    "The payer reply carries no InsurancePlan. The payer has no package master "
    "filed under this policy."
)
CONDITION = "claimcondition"
REQUIREMENT = "claimsupportinginforequirement"
URL_KEYS = ("valueUrl", "valueUri", "valueString", "valueCanonical")


def _norm(url):
    return (url or "").replace("-", "").replace("_", "").lower()


def _tail(url):
    return (url or "").rstrip("/").rsplit("/", 1)[-1]


def _family(ext):
    url = _norm(ext.get("url"))
    if REQUIREMENT in url:
        return REQUIREMENT
    if CONDITION in url:
        return CONDITION
    return None


def _first_coding(concept):
    codings = (concept or {}).get("coding") or []
    return codings[0] if codings else {}


def _ext_value(ext):
    if "valueCodeableConcept" in ext:
        c = _first_coding(ext["valueCodeableConcept"])
        return (
            c.get("display") or c.get("code") or ext["valueCodeableConcept"].get("text")
        )
    if "valueCoding" in ext:
        return ext["valueCoding"].get("display") or ext["valueCoding"].get("code")
    if "valueReference" in ext:
        return (ext["valueReference"] or {}).get("reference")
    for key, value in ext.items():
        if key.startswith("value"):
            return value
    return None


def conditions(element):
    """Claim-Condition extensions of one element as {name: value}."""
    out = {}
    for ext in element.get("extension") or []:
        if _family(ext) != CONDITION:
            continue
        children = ext.get("extension") or []
        if not children:
            out[_tail(ext.get("url"))] = _ext_value(ext)
            continue
        named = {_tail(c.get("url")).lower(): c for c in children}
        pair_key = next((k for k in ("code", "type", "condition") if k in named), None)
        if pair_key and "value" in named:
            out[str(_ext_value(named[pair_key]))] = _ext_value(named["value"])
            continue
        for child in children:
            out[_tail(child.get("url"))] = _ext_value(child)
    return out


def _documentation_url(child):
    for key in URL_KEYS:
        if child.get(key):
            return child[key]
    return (child.get("valueReference") or {}).get("reference")


def _requirement(children):
    req = {
        "category": "",
        "category_display": "",
        "code": "",
        "display": "",
        "form": None,
    }
    for child in children:
        name = _norm(_tail(child.get("url")))
        if name in ("category", "supportinfocategory"):
            c = _first_coding(child.get("valueCodeableConcept"))
            req["category"] = c.get("code") or ""
            req["category_display"] = c.get("display") or ""
        elif name in ("code", "supportinfocode"):
            c = _first_coding(child.get("valueCodeableConcept"))
            req["code"] = c.get("code") or ""
            req["display"] = c.get("display") or ""
        elif name == "documentationurl":
            req["form"] = _documentation_url(child)
    return req if (req["code"] or req["form"]) else None


def requirements(element):
    """Claim-SupportingInfoRequirement extensions of one element."""
    out = []
    for ext in element.get("extension") or []:
        if _family(ext) != REQUIREMENT:
            continue
        children = ext.get("extension") or []
        nested = [c for c in children if c.get("extension")]
        groups = [c.get("extension") for c in nested] if nested else [children]
        for group in groups:
            req = _requirement(group)
            if req:
                out.append(req)
    return out


def _money(value):
    value = value or {}
    amount = value.get("value")
    return (
        fb.amount(amount) if amount not in (None, "") else None,
        value.get("unit") or value.get("code") or value.get("currency") or "INR",
    )


def _implant_codes(plans):
    codes = set()
    for plan in plans:
        for specific in plan.get("specificCost") or []:
            for benefit in specific.get("benefit") or []:
                for cost in benefit.get("cost") or []:
                    if _first_coding(cost.get("type")).get("code") == "Implant":
                        for q in cost.get("qualifiers") or []:
                            codes.add(_first_coding(q).get("code"))
    return codes


def _specific_rows(plan, seen):
    rows = []
    plan_conditions, plan_reqs = conditions(plan), requirements(plan)
    for specific in plan.get("specificCost") or []:
        category = _first_coding(specific.get("category"))
        for benefit in specific.get("benefit") or []:
            btype = benefit.get("type") or {}
            c = _first_coding(btype)
            code = c.get("code")
            if not code or code in seen:
                continue
            seen.add(code)
            rate, currency, cost_type, extras = None, "INR", None, []
            for cost in benefit.get("cost") or []:
                type_code = _first_coding(cost.get("type")).get("code")
                value, unit = _money(cost.get("value"))
                if type_code == "Procedure" and cost_type is None:
                    rate, currency, cost_type = value, unit, "Procedure"
                    continue
                qualifier = _first_coding((cost.get("qualifiers") or [{}])[0])
                extras.append(
                    {
                        "type": type_code,
                        "code": qualifier.get("code"),
                        "label": qualifier.get("display"),
                        "rate": value,
                        "currency": unit,
                    }
                )
            if cost_type:
                kind = "Procedure"
            elif any(e["type"] == "Implant" for e in extras):
                kind = "Implant"
            else:
                kind = None
            rows.append(
                {
                    "category_code": category.get("code") or "",
                    "category_display": category.get("display") or "",
                    "code": code,
                    "display": c.get("display") or btype.get("text") or "",
                    "kind": kind,
                    "rate": rate,
                    "currency": currency,
                    "cost_type": cost_type,
                    "requirement": None,
                    "conditions": {**plan_conditions, **conditions(benefit)},
                    "extras": extras,
                    "supporting_info": plan_reqs + requirements(benefit),
                }
            )
    return rows


def _coverage_rows(coverage, seen, implants):
    rows = []
    category = _first_coding(coverage.get("type"))
    cov_conditions, cov_reqs = conditions(coverage), requirements(coverage)
    for benefit in coverage.get("benefit") or []:
        btype = benefit.get("type") or {}
        c = _first_coding(btype)
        code = c.get("code")
        if not code or code in seen:
            continue
        seen.add(code)
        rate, currency, extras, rate_taken = None, "INR", [], False
        for limit in benefit.get("limit") or []:
            limit_code = _first_coding(limit.get("code")).get("code")
            value, unit = _money(limit.get("value"))
            if not rate_taken and limit_code in (None, "", code):
                rate, currency, rate_taken = value, unit, True
                continue
            extras.append(
                {
                    "type": "Limit",
                    "code": limit_code,
                    "label": _first_coding(limit.get("code")).get("display"),
                    "rate": value,
                    "currency": unit,
                }
            )
        requirement = benefit.get("requirement")
        rows.append(
            {
                "category_code": category.get("code") or "",
                "category_display": category.get("display") or "",
                "code": code,
                "display": c.get("display") or btype.get("text") or "",
                "kind": "Implant" if code in implants else "Procedure",
                "rate": rate,
                "currency": currency,
                "cost_type": requirement,
                "requirement": requirement,
                "conditions": {**cov_conditions, **conditions(benefit)},
                "extras": extras,
                "supporting_info": cov_reqs + requirements(benefit),
            }
        )
    return rows


def read_benefits(bundle):
    """D11 rows: specificCost first, coverage[] adds only unseen codes."""
    plan = fb.find_resource(bundle, "InsurancePlan")
    if plan is None:
        return []
    seen, rows = set(), []
    plans = plan.get("plan") or []
    for element in plans:
        rows += _specific_rows(element, seen)
    implants = _implant_codes(plans)
    for coverage in plan.get("coverage") or []:
        rows += _coverage_rows(coverage, seen, implants)
    for n, row in enumerate(rows, start=1):
        row["seq"] = n
    return rows


def read_plan(bundle, benefits=None):
    """D10 fields; status ready, or empty with the empty message."""
    bundle = fb.unwrap(bundle)
    plan = fb.find_resource(bundle, "InsurancePlan")
    if plan is None:
        return {"status": "empty", "message": EMPTY_MESSAGE}
    if benefits is None:
        benefits = read_benefits(bundle)
    identifiers = plan.get("identifier") or []
    plan_type = ""
    types = plan.get("type") or []
    if types:
        plan_type = _first_coding(types[0]).get("display") or types[0].get("text") or ""
    plans = plan.get("plan") or []
    if not plan_type:
        for element in plans:
            display = _first_coding(element.get("type")).get("display")
            if display:
                plan_type = display
                break
    sum_insured = None
    for element in plans:
        for general in element.get("generalCost") or []:
            value = (general.get("cost") or {}).get("value")
            if value not in (None, "") and sum_insured is None:
                sum_insured = fb.amount(value)
    out = {
        "plan_identifier": (identifiers[0].get("value") if identifiers else None)
        or plan.get("id")
        or "",
        "plan_title": plan.get("name") or "",
        "plan_type": plan_type,
        "sum_insured": sum_insured,
        "policy_documents": requirements(plan),
        "status": "ready" if benefits else "empty",
    }
    if not benefits:
        out["message"] = EMPTY_MESSAGE
    return out


def _flatten(items, depth=0):
    for item in items or []:
        options, initial = [], None
        for option in item.get("answerOption") or []:
            if "valueString" in option:
                value = option["valueString"]
            else:
                coding = option.get("valueCoding") or {}
                value = coding.get("display") or coding.get("code")
            if value is None:
                continue
            options.append(value)
            if option.get("initialSelected") and initial is None:
                initial = value
        yield {
            "linkId": item.get("linkId"),
            "type": item.get("type"),
            "text": item.get("prefix") or item.get("text") or "",
            "required": bool(item.get("required")),
            "depth": depth,
            "options": options,
            "initial": initial,
        }
        yield from _flatten(item.get("item"), depth + 1)


def form_kind(url):
    head, _, _ = (url or "").rstrip("/").rpartition("/")
    return head.rpartition("/")[2] if head else ""


def read_forms(bundle):
    """D12 rows, one per distinct Questionnaire url (first wins)."""
    forms, seen = [], set()
    for resource in fb.find_resources(bundle, "Questionnaire"):
        url = resource.get("url")
        if not url or url in seen:
            continue
        seen.add(url)
        forms.append(
            {
                "url": url,
                "form_id": resource.get("id") or "",
                "title": resource.get("title") or resource.get("name") or url,
                "kind": form_kind(url),
                "items": list(_flatten(resource.get("item"))),
            }
        )
    return forms


def read(bundle):
    """{plan: D10 fields, benefits: D11 rows, forms: D12 rows}."""
    bundle = fb.unwrap(bundle)
    benefits = read_benefits(bundle)
    return {
        "plan": read_plan(bundle, benefits),
        "benefits": benefits,
        "forms": read_forms(bundle),
    }
