"""D29 claim_enquiry: status enquiry, reprocess and release Tasks."""

from django.db import models
from django.utils import timezone

from care.nhcx.models.base import (
    LegStage,
    NhcxBaseModel,
    code_field,
    json_field,
    money_field,
    text_field,
    timestamp_field,
)


class EnquiryKind(models.TextChoices):
    status = "status"
    reprocess = "reprocess"
    release = "release"


class EnquiryStatus(models.TextChoices):
    asking = "asking"
    answered = "answered"
    error = "error"


class EnquiryAnswer(models.TextChoices):
    """Fixed answers; a status enquiry otherwise stores the payer's status."""

    not_found = "not-found"
    unknown = "unknown"
    reopened = "reopened"
    refused = "refused"


class ReprocessReasonCode(models.TextChoices):
    claimrejected = "claimrejected"
    partialpayment = "partialpayment"
    rejectiondisputed = "rejectiondisputed"


class ClaimEnquiry(NhcxBaseModel):
    """D29 claim_enquiry: one small Task exchange beside the main legs."""

    claim = models.ForeignKey(
        "nhcx.Claim", on_delete=models.CASCADE, related_name="enquiries"
    )
    kind = models.CharField(max_length=16, choices=EnquiryKind.choices)
    stage = code_field(max_length=16, choices=LegStage.choices)
    txn_id = code_field()
    correlation_id = code_field()
    requested_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(
        max_length=16, default=EnquiryStatus.asking, choices=EnquiryStatus.choices
    )
    answer = code_field()
    detail = text_field()
    amount = money_field()
    reason = text_field()
    reason_code = code_field(max_length=32, choices=ReprocessReasonCode.choices)
    document_ids = json_field()
    error_message = text_field()
    request_json = json_field()
    response_json = json_field()
    answered_at = timestamp_field()

    class Meta:
        indexes = [
            models.Index(fields=["correlation_id"], name="ix_claim_enquiry_corr"),
            models.Index(fields=["claim", "id"], name="ix_claim_enquiry_claim"),
        ]
