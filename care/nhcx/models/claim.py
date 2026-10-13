"""D9 claim (the case) and D30 counter with number allocation."""

from django.db import models, transaction
from django.utils import timezone

from care.nhcx.models.base import (
    NhcxBaseModel,
    code_field,
    json_field,
    money_field,
    text_field,
    timestamp_field,
)


class ClaimStatus(models.TextChoices):
    """D9 ``status``: the eligibility status of the case."""

    draft = "draft"
    checking = "checking"
    eligible = "eligible"
    not_eligible = "not-eligible"
    error = "error"


class ClaimStage(models.TextChoices):
    eligibility = "eligibility"
    preauth = "preauth"
    enhancement = "enhancement"
    claim = "claim"
    payment = "payment"


class ClaimSubStage(models.TextChoices):
    draft = "draft"
    checking = "checking"
    eligible = "eligible"
    not_eligible = "not-eligible"
    requested = "requested"
    resubmitted = "resubmitted"
    answered = "answered"
    queried = "queried"
    approved = "approved"
    partial = "partial"
    rejected = "rejected"
    cancelling = "cancelling"
    cancelled = "cancelled"
    refused = "refused"
    noticed = "noticed"
    paid = "paid"


class SearchIdType(models.TextChoices):
    MemberId = "MemberId"
    MobileNo = "MobileNo"
    AbhaNumber = "AbhaNumber"


class EligibilityPurpose(models.TextChoices):
    validation = "validation"
    benefits = "benefits"
    discovery = "discovery"


class EligibilityOutcome(models.TextChoices):
    complete = "complete"
    error = "error"
    partial = "partial"


class CaseType(models.TextChoices):
    package = "package"
    nonpackage = "nonpackage"


class Claim(NhcxBaseModel):
    """D9 claim: one claim episode around one selected policy.

    ``external_id`` (UUID, from the base) is the ``:caseid`` of every route.
    The spec's ``created_at`` is ``created_date`` of the base.
    """

    facility = models.ForeignKey(
        "facility.Facility", on_delete=models.PROTECT, related_name="nhcx_claims"
    )
    claim_no = models.CharField(max_length=64, unique=True)
    status = models.CharField(
        max_length=32, default=ClaimStatus.draft, choices=ClaimStatus.choices
    )
    search_id_type = code_field(choices=SearchIdType.choices)
    search_id_value = code_field()
    member_id = models.CharField(max_length=255)
    policy_code = code_field()
    beneficiary_name = code_field()
    abha_number = code_field()
    mobile_number = code_field()
    processing_id = code_field()
    payer_id = code_field()
    payer_name = code_field()
    product_id = code_field()
    product_name = code_field()
    policy_json = json_field()
    purpose = code_field(choices=EligibilityPurpose.choices)
    txn_id = code_field()
    correlation_id = code_field(db_index=True)
    checked_at = timestamp_field()
    error_message = text_field()
    inforce = models.BooleanField(null=True, blank=True)
    outcome = code_field(choices=EligibilityOutcome.choices)
    disposition = text_field()
    auth_required = models.BooleanField(null=True, blank=True)
    allowed_amount = money_field()
    used_amount = money_field()
    plan_name = code_field()
    # payer-sourced FHIR date strings are kept as sent
    plan_period_start = code_field()
    plan_period_end = code_field()
    relationship = code_field()
    patient_gender = code_field()
    patient_dob = code_field()
    patient_address = text_field()
    patient_photo = text_field()
    response_json = json_field()
    patient = models.ForeignKey(
        "emr.Patient",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="nhcx_claims",
    )
    encounter = models.ForeignKey(
        "emr.Encounter",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="nhcx_claims",
    )
    admission_date = models.DateField(null=True, blank=True)
    expected_discharge_date = models.DateField(null=True, blank=True)
    case_type = code_field(choices=CaseType.choices)
    package_code = code_field()
    package_name = text_field()
    preauth_total = money_field()
    preauth_saved_at = timestamp_field()
    stage = code_field(choices=ClaimStage.choices)
    sub_stage = code_field(choices=ClaimSubStage.choices)

    class Meta:
        indexes = [
            models.Index(fields=["facility", "status", "-id"], name="ix_claim_status"),
        ]

    def __str__(self):
        return self.claim_no


class Counter(models.Model):
    """D30 counter: one named number series and the last value handed out."""

    name = models.CharField(max_length=100, primary_key=True)
    value = models.BigIntegerField(default=0)

    def __str__(self):
        return f"{self.name}={self.value}"


def next_number(name: str) -> int:
    """Allocate the next number of a series (the first is 1).

    Joins an open transaction, so a write that rolls back does not use up a
    number; concurrent callers are serialised by a row lock.
    """
    with transaction.atomic():
        Counter.objects.bulk_create(
            [Counter(name=name, value=0)], ignore_conflicts=True
        )
        counter = Counter.objects.select_for_update().get(name=name)
        counter.value += 1
        counter.save(update_fields=["value"])
        return counter.value


def next_value(name: str, prefix: str = "", width: int = 5) -> str:
    """Next number of a series as ``<prefix><number left-padded to width>``."""
    return f"{prefix}{next_number(name):0{width}d}"


CLAIM_COUNTER = "claim"
BASE32_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUV"


def to_base32(number: int, width: int) -> str:
    chars = []
    for _ in range(width):
        number, rest = divmod(number, 32)
        chars.append(BASE32_ALPHABET[rest])
    if number:
        msg = f"value does not fit in {width} base32 characters"
        raise ValueError(msg)
    return "".join(reversed(chars))


def format_claim_no(prefix: str, serial: int, when) -> str:
    """``<prefix>-<yy>-<mmdd in 3 base32><serial in 6 base32>`` (D30)."""
    mmdd = to_base32(when.month * 100 + when.day, 3)
    return f"{prefix}-{when:%y}-{mmdd}{to_base32(serial, 6)}"


def allocate_claim_no(prefix: str, when=None) -> str:
    """Take a fresh claim number from the ``claim`` series (D9, D30)."""
    when = when or timezone.localtime()
    return format_claim_no(prefix, next_number(CLAIM_COUNTER), when)
