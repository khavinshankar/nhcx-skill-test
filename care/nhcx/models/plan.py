"""D10 claim_plan, D11 claim_plan_benefit, D12 claim_plan_form."""

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


class PlanStatus(models.TextChoices):
    fetching = "fetching"
    ready = "ready"
    empty = "empty"
    error = "error"


class BenefitKind(models.TextChoices):
    Procedure = "Procedure"
    Implant = "Implant"


class BenefitExtraType(models.TextChoices):
    Stratification = "Stratification"
    Implant = "Implant"
    Limit = "Limit"


class PlanFormKind(models.TextChoices):
    questionnaire = "questionnaire"
    stgquestionnaire = "stgquestionnaire"


class ClaimPlan(NhcxBaseModel):
    """D10 claim_plan: the payer's package master for one claim."""

    claim = models.OneToOneField(
        "nhcx.Claim", on_delete=models.CASCADE, related_name="plan"
    )
    status = models.CharField(
        max_length=32, default=PlanStatus.fetching, choices=PlanStatus.choices
    )
    txn_id = code_field()
    correlation_id = code_field()
    requested_at = timestamp_field()
    fetched_at = timestamp_field()
    error_message = text_field()
    policy_code = code_field()
    provider_id = code_field()
    plan_identifier = code_field()
    plan_title = text_field()
    plan_type = code_field()
    sum_insured = money_field()
    policy_documents = json_field()
    response_json = json_field()

    class Meta:
        indexes = [models.Index(fields=["correlation_id"], name="ix_claim_plan_corr")]


class ClaimPlanBenefit(NhcxBaseModel):
    """D11 claim_plan_benefit: one package or benefit of a package master."""

    plan = models.ForeignKey(
        ClaimPlan, on_delete=models.CASCADE, related_name="benefits"
    )
    seq = models.IntegerField(default=1)
    category_code = code_field()
    category_display = text_field()
    code = models.CharField(max_length=255)
    display = text_field()
    kind = code_field(choices=BenefitKind.choices)
    rate = money_field()
    currency = code_field()
    cost_type = code_field()
    requirement = code_field()
    conditions = json_field()
    extras = json_field()
    supporting_info = json_field()

    class Meta:
        indexes = [
            models.Index(fields=["plan", "seq"], name="ix_claim_plan_benefit"),
        ]


class ClaimPlanForm(NhcxBaseModel):
    """D12 claim_plan_form: one payer questionnaire of a package master."""

    plan = models.ForeignKey(ClaimPlan, on_delete=models.CASCADE, related_name="forms")
    url = url_field(null=False, blank=False)
    form_id = code_field()
    title = text_field()
    kind = code_field(choices=PlanFormKind.choices)
    items = models.JSONField(default=list)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["plan", "url"], name="ux_claim_plan_form"),
        ]
