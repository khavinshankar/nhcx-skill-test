"""D16 claim_line, D17 claim_form_answer, D25 claim_diagnosis,
D26 claim_care_team, D27 claim_item, D28 claim_document."""

from decimal import Decimal

from django.db import models
from django.utils import timezone

from care.nhcx.models.base import (
    LegStage,
    NhcxBaseModel,
    code_field,
    quantity_field,
    text_field,
    url_field,
)


class LineKind(models.TextChoices):
    Procedure = "Procedure"
    Implant = "Implant"
    Stratification = "Stratification"


class CareTeamRole(models.TextChoices):
    admitting = "admitting", "Admitting physician"
    treating = "treating", "Treating doctor"
    surgeon = "surgeon", "Surgeon"
    anaesthetist = "anaesthetist", "Anaesthetist"
    nurse = "nurse", "Nursing lead"


class DocumentContentType(models.TextChoices):
    pdf = "application/pdf"
    jpeg = "image/jpeg"
    png = "image/png"
    webp = "image/webp"


MAX_DOCUMENT_SIZE = 10 * 1024 * 1024


class DocumentCode(models.TextChoices):
    """Common codes offered on every upload (D28) [PAYER]."""

    CD = "CD", "Clinical document"
    HDS = "HDS", "Hospital discharge summary"
    DIA = "DIA", "Diagnostic and laboratory reports"
    RAD = "RAD", "Radiology / scan reports"
    PRE = "PRE", "Doctor's prescription notes"
    CER = "CER", "Medical certificate / referral"
    EST = "EST", "Cost estimate"
    MB = "MB", "Medical and pharmacy bills"
    INV = "INV", "Final hospital invoice"
    OTR = "OTR", "Operation theatre notes"
    ICU = "ICU", "ICU chart"
    IMP = "IMP", "Implant invoice and sticker"
    POI = "POI", "Proof of identity"
    KYC = "KYC", "KYC / bank proof"
    FCF = "FCF", "Filled claim form"
    PAU = "PAU", "Pre-authorisation approval letter"
    ODN = "ODN", "Other document"


class DocumentCategory(models.TextChoices):
    INV = "INV"
    HDS = "HDS"


def _amount_field():
    return models.DecimalField(max_digits=20, decimal_places=2, default=Decimal(0))


class ClaimLine(NhcxBaseModel):
    """D16 claim_line: one procedure, implant or tier quoted from the plan."""

    claim = models.ForeignKey(
        "nhcx.Claim", on_delete=models.CASCADE, related_name="lines"
    )
    seq = models.IntegerField(default=1)
    kind = models.CharField(max_length=32, choices=LineKind.choices)
    code = models.CharField(max_length=255)
    display = text_field()
    category_code = code_field()
    category_display = text_field()
    unit_price = _amount_field()
    quantity = quantity_field(default=Decimal(1))
    amount = _amount_field()
    parent_code = code_field()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["claim", "kind", "code"], name="ux_claim_line"
            ),
        ]


class ClaimFormAnswer(NhcxBaseModel):
    """D17 claim_form_answer: the answer to one question of one payer form."""

    claim = models.ForeignKey(
        "nhcx.Claim", on_delete=models.CASCADE, related_name="form_answers"
    )
    form_url = url_field(null=False, blank=False)
    link_id = models.CharField(max_length=255)
    answer = text_field()
    stage = code_field(max_length=16, choices=LegStage.choices)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["claim", "form_url", "link_id"], name="ux_claim_form_answer"
            ),
        ]


class ClaimDiagnosis(NhcxBaseModel):
    """D25 claim_diagnosis: one diagnosis on the pre-auth draft."""

    claim = models.ForeignKey(
        "nhcx.Claim", on_delete=models.CASCADE, related_name="diagnoses"
    )
    seq = models.IntegerField(default=1)
    snomed_code = code_field()
    snomed_display = text_field()
    icd10_code = models.CharField(max_length=64)
    icd10_display = text_field()

    class Meta:
        indexes = [models.Index(fields=["claim", "seq"], name="ix_claim_dx")]


class ClaimCareTeam(NhcxBaseModel):
    """D26 claim_care_team: one doctor on the pre-auth draft's team."""

    claim = models.ForeignKey(
        "nhcx.Claim", on_delete=models.CASCADE, related_name="care_team"
    )
    seq = models.IntegerField(default=1)
    practitioner = models.ForeignKey(
        "users.User", on_delete=models.PROTECT, related_name="nhcx_care_teams"
    )
    role = models.CharField(max_length=32, choices=CareTeamRole.choices)

    class Meta:
        indexes = [models.Index(fields=["claim", "seq"], name="ix_claim_team")]


class ClaimItem(NhcxBaseModel):
    """D27 claim_item: one charge-master item on a non-package draft."""

    claim = models.ForeignKey(
        "nhcx.Claim", on_delete=models.CASCADE, related_name="items"
    )
    seq = models.IntegerField(default=1)
    code = models.CharField(max_length=255)
    display = models.TextField()
    unit_price = _amount_field()
    quantity = quantity_field(default=Decimal(1))
    amount = _amount_field()

    class Meta:
        indexes = [models.Index(fields=["claim", "seq"], name="ix_claim_item")]


class ClaimDocument(NhcxBaseModel):
    """D28 claim_document: one supporting file stored inline."""

    claim = models.ForeignKey(
        "nhcx.Claim", on_delete=models.CASCADE, related_name="documents"
    )
    filename = models.CharField(max_length=512, default="document")
    content_type = models.CharField(max_length=64, choices=DocumentContentType.choices)
    label = text_field()
    code = code_field()
    category = code_field(max_length=16, choices=DocumentCategory.choices)
    stage = models.CharField(
        max_length=16, default=LegStage.preauth, choices=LegStage.choices
    )
    size = models.IntegerField(default=0)
    data = models.BinaryField()
    uploaded_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [models.Index(fields=["claim", "id"], name="ix_claim_doc")]
