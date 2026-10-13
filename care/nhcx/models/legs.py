"""D18 claim_preauth, D19 claim_predetermination, D20 claim_submission."""

from django.db import models
from django.utils import timezone

from care.nhcx.models.base import (
    NhcxBaseModel,
    code_field,
    json_field,
    money_field,
    text_field,
    timestamp_field,
)


class ResponseOutcome(models.TextChoices):
    """ClaimResponse.outcome."""

    queued = "queued"
    acknowledged = "acknowledged"
    complete = "complete"
    error = "error"
    partial = "partial"


class PreauthStatus(models.TextChoices):
    submitting = "submitting"
    approved = "approved"
    partial = "partial"
    queried = "queried"
    rejected = "rejected"
    cancelling = "cancelling"
    cancelled = "cancelled"
    error = "error"


class PreauthSubmissionKind(models.TextChoices):
    preauth = "preauth"
    preauth_query_response = "preauth_query_response"
    enhancement = "enhancement"
    enhancement_resubmit = "enhancement_resubmit"
    # recognised when reading, never chosen by the sender [REF]
    preauth_resubmit = "preauth_resubmit"


class CancelReason(models.TextChoices):
    treatmentplanchanged = "treatmentplanchanged"
    patientrequest = "patientrequest"
    financialconstraints = "financialconstraints"
    alternativetreatment = "alternativetreatment"
    duplicateclaim = "duplicateclaim"
    administrativeerror = "administrativeerror"
    other = "other"


class PredeterminationStatus(models.TextChoices):
    asking = "asking"
    answered = "answered"
    error = "error"


class SubmissionStatus(models.TextChoices):
    draft = "draft"
    submitting = "submitting"
    approved = "approved"
    partial = "partial"
    queried = "queried"
    rejected = "rejected"
    error = "error"


class SubmissionKind(models.TextChoices):
    claim = "claim"
    claim_query_response = "claim_query_response"
    claim_resubmit = "claim_resubmit"


class DischargeMode(models.TextChoices):
    normal = "normal"
    lama = "lama"
    dama = "dama"
    death = "death"


class DischargeStage(models.TextChoices):
    before_surgery = "Before Surgery"
    during_surgery = "During Surgery"
    after_surgery = "After Surgery"


class ClaimPreauth(NhcxBaseModel):
    """D18 claim_preauth: the pre-authorisation leg of a claim."""

    claim = models.OneToOneField(
        "nhcx.Claim", on_delete=models.CASCADE, related_name="preauth"
    )
    status = models.CharField(
        max_length=32,
        default=PreauthStatus.submitting,
        choices=PreauthStatus.choices,
    )
    txn_id = code_field()
    correlation_id = code_field()
    submitted_at = timestamp_field()
    settled_at = timestamp_field()
    error_message = text_field()
    claim_ref = code_field(db_index=True)
    preauth_ref = code_field()
    api_call_id = code_field()
    adjudication = code_field()
    query_note = text_field()
    outcome = code_field(choices=ResponseOutcome.choices)
    disposition = text_field()
    approved_amount = money_field()
    eligible_amount = money_field()
    submitted_amount = money_field()
    requested_amount = money_field()
    items_json = json_field()
    submission_kind = code_field(choices=PreauthSubmissionKind.choices)
    workflow_id = code_field()
    request_json = json_field()
    response_json = json_field()
    cancel_txn_id = code_field()
    cancel_correlation_id = code_field(db_index=True)
    cancel_requested_at = timestamp_field()
    cancel_reason = code_field(choices=CancelReason.choices)
    cancel_note = text_field()
    pre_cancel_status = code_field(choices=PreauthStatus.choices)
    enhancement_no = models.IntegerField(null=True, blank=True)
    thread_correlation_id = code_field()
    reply_text = text_field()

    class Meta:
        indexes = [
            models.Index(fields=["correlation_id"], name="ix_claim_preauth_corr"),
        ]


class ClaimPredetermination(NhcxBaseModel):
    """D19 claim_predetermination: one non-binding quote asked of the payer."""

    claim = models.ForeignKey(
        "nhcx.Claim", on_delete=models.CASCADE, related_name="predeterminations"
    )
    status = models.CharField(
        max_length=32,
        default=PredeterminationStatus.asking,
        choices=PredeterminationStatus.choices,
    )
    txn_id = code_field()
    correlation_id = code_field()
    requested_at = models.DateTimeField(default=timezone.now)
    answered_at = timestamp_field()
    error_message = text_field()
    outcome = code_field(choices=ResponseOutcome.choices)
    adjudication = code_field()
    disposition = text_field()
    allowed_amount = money_field()
    requested_amount = money_field()
    request_json = json_field()
    response_json = json_field()

    class Meta:
        indexes = [
            models.Index(
                fields=["correlation_id"], name="ix_claim_predetermination_corr"
            ),
            models.Index(fields=["claim", "id"], name="ix_claim_predet_claim"),
        ]


class ClaimSubmission(NhcxBaseModel):
    """D20 claim_submission: the claim leg (discharge, last send, verdict)."""

    claim = models.OneToOneField(
        "nhcx.Claim", on_delete=models.CASCADE, related_name="submission"
    )
    status = models.CharField(
        max_length=32,
        default=SubmissionStatus.draft,
        choices=SubmissionStatus.choices,
    )
    discharge_mode = code_field(max_length=16, choices=DischargeMode.choices)
    discharge_stage = code_field(max_length=32, choices=DischargeStage.choices)
    discharge_date = timestamp_field()
    surgery_date = timestamp_field()
    death_date = timestamp_field()
    txn_id = code_field()
    correlation_id = code_field()
    submitted_at = timestamp_field()
    settled_at = timestamp_field()
    error_message = text_field()
    claim_ref = code_field(db_index=True)
    preauth_ref = code_field()
    api_call_id = code_field()
    adjudication = code_field()
    query_note = text_field()
    outcome = code_field(choices=ResponseOutcome.choices)
    disposition = text_field()
    approved_amount = money_field()
    eligible_amount = money_field()
    submitted_amount = money_field()
    requested_amount = money_field()
    items_json = json_field()
    submission_kind = code_field(choices=SubmissionKind.choices)
    workflow_id = code_field()
    request_json = json_field()
    response_json = json_field()
    thread_correlation_id = code_field()
    reply_text = text_field()

    class Meta:
        indexes = [
            models.Index(fields=["correlation_id"], name="ix_claim_submission_corr"),
        ]
