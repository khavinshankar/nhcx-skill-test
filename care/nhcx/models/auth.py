"""D13 claim_auth, D14 claim_auth_item, D15 claim_auth_requirement."""

from django.db import models

from care.nhcx.models.base import (
    NhcxBaseModel,
    code_field,
    json_field,
    money_field,
    text_field,
    timestamp_field,
    url_field,
)


class AuthStatus(models.TextChoices):
    checking = "checking"
    ready = "ready"
    error = "error"


class AuthRequirementKind(models.TextChoices):
    document = "document"
    form = "form"


class ClaimAuth(NhcxBaseModel):
    """D13 claim_auth: the payer's auth-requirements ruling on a claim."""

    claim = models.OneToOneField(
        "nhcx.Claim", on_delete=models.CASCADE, related_name="auth"
    )
    status = models.CharField(
        max_length=32, default=AuthStatus.checking, choices=AuthStatus.choices
    )
    txn_id = code_field()
    correlation_id = code_field()
    requested_at = timestamp_field()
    settled_at = timestamp_field()
    error_message = text_field()
    outcome = code_field()
    disposition = text_field()
    inforce = models.BooleanField(null=True, blank=True)
    response_json = json_field()
    asked_codes = text_field()

    class Meta:
        indexes = [models.Index(fields=["correlation_id"], name="ix_claim_auth_corr")]


class ClaimAuthItem(NhcxBaseModel):
    """D14 claim_auth_item: the ruling on one line of the procedure set."""

    auth = models.ForeignKey(ClaimAuth, on_delete=models.CASCADE, related_name="items")
    seq = models.IntegerField(default=1)
    code = models.CharField(max_length=255, blank=True, default="")
    display = text_field()
    category_code = code_field()
    auth_required = models.BooleanField(null=True, blank=True)
    excluded = models.BooleanField(null=True, blank=True)
    benefit_type = code_field()
    allowed_amount = money_field()

    class Meta:
        indexes = [models.Index(fields=["auth", "seq"], name="ix_claim_auth_item")]


class ClaimAuthRequirement(NhcxBaseModel):
    """D15 claim_auth_requirement: one document or form the ruling asks for."""

    auth = models.ForeignKey(
        ClaimAuth, on_delete=models.CASCADE, related_name="requirements"
    )
    seq = models.IntegerField(default=1)
    kind = models.CharField(max_length=32, choices=AuthRequirementKind.choices)
    code = code_field()
    display = text_field()
    form_url = url_field()
    stage = code_field()
    for_code = code_field()
    at_preauth = models.BooleanField(default=True)

    class Meta:
        indexes = [models.Index(fields=["auth", "seq"], name="ix_claim_auth_req")]
