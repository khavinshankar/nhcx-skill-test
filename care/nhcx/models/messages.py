"""D21 claim_payment, D22 claim_payment_detail, D23 claim_query,
D24 claim_adjudication."""

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


class AckStatus(models.TextChoices):
    pending = "pending"
    sent = "sent"
    error = "error"


class QueryKind(models.TextChoices):
    query = "query"
    notification = "notification"
    note = "note"


class QueryStatus(models.TextChoices):
    """D23 ``status``: query open/answered/error, notification
    open/acknowledged/error, note noted."""

    open = "open"
    answered = "answered"
    acknowledged = "acknowledged"
    noted = "noted"
    error = "error"


class QueryReasonCode(models.TextChoices):
    """Known Task.reasonCode values, lower case [PAYER]."""

    tatquery = "tatquery"
    grievance = "grievance"
    walletupdate = "walletupdate"
    policychange = "policychange"
    additionalinfo = "additionalinfo"
    claimarbitration = "claimarbitration"
    questionnaire = "questionnaire"
    query = "query"


class AdjudicationDesk(models.TextChoices):
    nhcx_payer_service = "nhcx-payer-service"
    irdai_payer = "irdai-payer"
    gateway = "gateway"


class ClaimPayment(NhcxBaseModel):
    """D21 claim_payment: one payment notice and its acknowledgement."""

    claim = models.ForeignKey(
        "nhcx.Claim", on_delete=models.CASCADE, related_name="payments"
    )
    claim_ref = code_field()
    correlation_id = code_field(unique=True)
    sender_code = code_field()
    workflow_id = code_field()
    received_at = models.DateTimeField(default=timezone.now)
    disposition = text_field()
    payment_status = code_field()
    # payer-sourced FHIR date string, kept as sent
    payment_date = code_field()
    amount = money_field()
    currency = code_field(max_length=16)
    utr = code_field()
    notice_json = json_field()
    ack_status = models.CharField(
        max_length=16, default=AckStatus.pending, choices=AckStatus.choices
    )
    ack_txn_id = code_field()
    ack_correlation_id = code_field()
    acknowledged_at = timestamp_field()
    ack_error = text_field()
    notice_id = code_field()

    class Meta:
        indexes = [models.Index(fields=["claim", "-id"], name="ix_claim_payment")]


class ClaimPaymentDetail(NhcxBaseModel):
    """D22 claim_payment_detail: one line of a reconciliation breakdown."""

    payment = models.ForeignKey(
        ClaimPayment, on_delete=models.CASCADE, related_name="details"
    )
    seq = models.IntegerField(default=1)
    reference = code_field()
    type_code = code_field()
    type_display = text_field()
    # payer-sourced FHIR date string, kept as sent
    date = code_field()
    amount = money_field()

    class Meta:
        indexes = [
            models.Index(fields=["payment", "seq"], name="ix_claim_payment_detail"),
        ]


class ClaimQuery(NhcxBaseModel):
    """D23 claim_query: one payer-started communication on a claim."""

    claim = models.ForeignKey(
        "nhcx.Claim", on_delete=models.CASCADE, related_name="queries"
    )
    stage = models.CharField(
        max_length=16, default=LegStage.preauth, choices=LegStage.choices
    )
    correlation_id = code_field(unique=True)
    request_id = code_field()
    claim_ref = code_field()
    sender_code = code_field()
    workflow_id = code_field()
    received_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(
        max_length=16, default=QueryStatus.open, choices=QueryStatus.choices
    )
    kind = models.CharField(
        max_length=16, default=QueryKind.query, choices=QueryKind.choices
    )
    reason_code = code_field()
    remarks = text_field()
    questions = json_field()
    request_json = json_field()
    reply_text = text_field()
    reply_documents = json_field()
    reply_txn_id = code_field()
    reply_correlation_id = code_field()
    answered_at = timestamp_field()
    acknowledged_at = timestamp_field()
    error_message = text_field()
    reply_json = json_field()

    class Meta:
        indexes = [models.Index(fields=["claim", "-id"], name="ix_claim_query")]


class ClaimAdjudication(NhcxBaseModel):
    """D24 claim_adjudication: one decision step sent to a payer desk."""

    claim = models.ForeignKey(
        "nhcx.Claim", on_delete=models.CASCADE, related_name="adjudications"
    )
    stage = models.CharField(max_length=16, choices=LegStage.choices)
    case_number = code_field()
    role = code_field()
    action = code_field()
    usecase = code_field()
    correlation_id = code_field()
    remarks = text_field()
    success = models.BooleanField(default=False)
    http_status = models.IntegerField(null=True, blank=True)
    response_json = json_field()
    desk = code_field(max_length=32, choices=AdjudicationDesk.choices)
    cycle_id = code_field(max_length=64)
    taken_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [
            models.Index(
                fields=["claim", "stage", "-id"], name="ix_claim_adjudication"
            ),
        ]
