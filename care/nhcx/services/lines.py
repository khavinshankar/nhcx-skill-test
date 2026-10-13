"""S8 line items (D16) and the S4 admission link (D9 encounter).

Public:
- ``add_line(claim, kind, code, parent_code=None) -> (line, message)``
- ``update_lines(claim, changes) -> message``; ``changes`` is a list of
  ``{id, quantity?, unit_price?}`` (id = line external_id).
- ``remove_line(claim, line_id) -> message``
- ``link_admission(claim, encounter_id) -> message``; ``unlink_admission``.
Each refuses with ``ServiceRefusal(<S8/S4 verbatim message>)``.
"""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Max

from care.nhcx.models import ClaimLine
from care.nhcx.services.common import ServiceRefusal

KINDS = ("Procedure", "Implant", "Stratification")
NOT_QUOTABLE = "That is not something a preauth can quote."
NOTHING_SELECTED = "Nothing was selected."
PLAN_NOT_READY = (
    "Fetch the payer's insurance plan first, the preauth quotes its packages and "
    "its rates."
)
UNKNOWN_PARENT = "Pick the procedure this ward tier belongs to."
TIER_NOT_OFFERED = "That ward tier is not offered for this package."
NO_SUCH_LINE = "No such line."
NOT_ELIGIBLE_LINK = (
    "Link an admission only after the payer has confirmed the policy is eligible."
)
NOT_A_MATCH = (
    "That admission is not a current IPD stay of a patient with this claim's ABHA "
    "number."
)
CENT = Decimal("0.01")


def _s(v) -> str:
    return "" if v is None else str(v).strip()


def _money(v) -> Decimal:
    return Decimal(v or 0).quantize(CENT, rounding=ROUND_HALF_UP)


def _ready_plan(claim):
    try:
        plan = claim.plan
    except Exception:
        plan = None
    if plan is None or plan.status != "ready":
        raise ServiceRefusal(PLAN_NOT_READY)
    return plan


def _extras(benefit, type_) -> list:
    return [
        e
        for e in (benefit.extras if isinstance(benefit.extras, list) else [])
        if isinstance(e, dict) and e.get("type") == type_
    ]


def _quote(plan, kind, code, parent_code):
    """(display, category_code, category_display, rate, parent_code) from the plan."""
    benefits = plan.benefits.all()
    if kind == "Stratification":
        parent_code = _s(parent_code)
        parent = (
            benefits.filter(code=parent_code).order_by("seq", "id").first()
            if parent_code
            else None
        )
        if parent is None:
            raise ServiceRefusal(UNKNOWN_PARENT)
        for tier in _extras(parent, "Stratification"):
            if _s(tier.get("code")) == code:
                return (
                    tier.get("label") or code,
                    parent.category_code,
                    parent.category_display,
                    tier.get("rate"),
                    parent_code,
                )
        raise ServiceRefusal(TIER_NOT_OFFERED)
    benefit = benefits.filter(code=code, kind=kind).order_by("seq", "id").first()
    if benefit is not None:
        return (
            benefit.display,
            benefit.category_code,
            benefit.category_display,
            benefit.rate,
            None,
        )
    if kind == "Implant":
        for b in benefits.order_by("seq", "id"):
            for extra in _extras(b, "Implant"):
                if _s(extra.get("code")) == code:
                    return (
                        extra.get("label") or code,
                        None,
                        None,
                        extra.get("rate"),
                        None,
                    )
    msg = f"{code} is not a {kind.lower()} in this plan."
    raise ServiceRefusal(msg)


def add_line(claim, kind, code, parent_code=None):
    kind, code = _s(kind), _s(code)
    if kind not in KINDS:
        raise ServiceRefusal(NOT_QUOTABLE)
    if not code:
        raise ServiceRefusal(NOTHING_SELECTED)
    plan = _ready_plan(claim)
    display, cat_code, cat_display, rate, parent = _quote(plan, kind, code, parent_code)
    if claim.lines.filter(kind=kind, code=code).exists():
        msg = f"{code} is already on this preauth."
        raise ServiceRefusal(msg)
    price = _money(rate)
    with transaction.atomic():
        seq = (claim.lines.aggregate(m=Max("seq"))["m"] or 0) + 1
        line = ClaimLine.objects.create(
            claim=claim,
            seq=seq,
            kind=kind,
            code=code,
            display=display,
            category_code=cat_code,
            category_display=cat_display,
            unit_price=price,
            quantity=Decimal(1),
            amount=price,
            parent_code=parent,
        )
    return line, f"{code} added."


def _open_price(claim, line) -> bool:
    try:
        plan = claim.plan
    except Exception:
        return False
    if plan is None:
        return False
    try:
        _, _, _, rate, _ = _quote(plan, line.kind, line.code, line.parent_code)
    except ServiceRefusal:
        return False
    return not rate


def _quantity(line, raw):
    if raw is None or _s(raw) == "":
        return line.quantity
    try:
        q = Decimal(_s(raw))
    except InvalidOperation:
        msg = f"Enter a quantity for {line.code}."
        raise ServiceRefusal(msg) from None
    if not q.is_finite() or q <= 0:
        msg = f"Enter a quantity for {line.code}."
        raise ServiceRefusal(msg)
    if q != q.to_integral_value():
        msg = f"The quantity of {line.code} must be a whole number."
        raise ServiceRefusal(msg)
    return q


def _price(line, raw):
    try:
        p = Decimal(_s(raw))
    except InvalidOperation:
        msg = f"Enter a price for {line.code}."
        raise ServiceRefusal(msg) from None
    if not p.is_finite():
        msg = f"Enter a price for {line.code}."
        raise ServiceRefusal(msg)
    if p < 0:
        msg = f"The price of {line.code} cannot be negative."
        raise ServiceRefusal(msg)
    return _money(p)


def update_lines(claim, changes) -> str:
    by_id = {str(ln.external_id): ln for ln in claim.lines.all()}
    pending = []
    for change in changes or []:
        line = by_id.get(_s((change or {}).get("id")))
        if line is None:
            raise ServiceRefusal(NO_SUCH_LINE)
        price = line.unit_price
        if "unit_price" in change and _open_price(claim, line):
            price = _price(line, change.get("unit_price"))
        quantity = _quantity(line, change.get("quantity"))
        pending.append((line, price, quantity))
    with transaction.atomic():
        for line, price, quantity in pending:
            line.unit_price = price
            line.quantity = quantity
            line.amount = _money(price * quantity)
            line.save(
                update_fields=["unit_price", "quantity", "amount", "modified_date"]
            )
    return "Lines updated."


def remove_line(claim, line_id) -> str:
    line = claim.lines.filter(external_id=line_id).first()
    if line is None:
        raise ServiceRefusal(NO_SUCH_LINE)
    line.delete()
    return "Line removed."


def link_admission(claim, encounter_id) -> str:
    from care.nhcx.services.state import admissions

    if claim.status != "eligible":
        raise ServiceRefusal(NOT_ELIGIBLE_LINK)
    if _s(encounter_id) not in {a["id"] for a in admissions(claim)}:
        raise ServiceRefusal(NOT_A_MATCH)
    from care.emr.models import Encounter

    encounter = Encounter.objects.select_related("patient").get(
        external_id=encounter_id
    )
    fields = ["encounter", "patient", "modified_date"]
    claim.encounter = encounter
    claim.patient = encounter.patient
    start = _s((encounter.period or {}).get("start"))[:10]
    if claim.admission_date is None and start:
        claim.admission_date = start
        fields.append("admission_date")
    claim.save(update_fields=fields)
    return "Admission linked to the claim."


def unlink_admission(claim) -> str:
    claim.encounter = None
    claim.patient = None
    claim.save(update_fields=["encounter", "patient", "modified_date"])
    return "Admission unlinked."
