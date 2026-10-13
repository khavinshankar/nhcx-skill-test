"""D31 biometric_auth: ABDM biometric authentication attempts."""

from django.db import models

from care.nhcx.models.base import NhcxBaseModel, code_field, text_field, timestamp_field


class BiometricStage(models.TextChoices):
    Preauth = "Preauth"
    Discharge = "Discharge"


class BiometricMethod(models.TextChoices):
    FINGERPRINT = "FINGERPRINT"
    IRIS = "IRIS"
    FACE_AUTH = "FACE_AUTH"


class BiometricStatus(models.TextChoices):
    initiated = "initiated"
    captured = "captured"
    verified = "verified"
    failed = "failed"


class BiometricAuth(NhcxBaseModel):
    """D31 biometric_auth: one attempt to authenticate a patient's ABHA.

    ``user_token`` and ``refresh_token`` are server-only. The spec's
    ``created_at`` / ``updated_at`` are ``created_date`` / ``modified_date``;
    ``requested_by`` is a user foreign key.
    """

    patient = models.ForeignKey(
        "emr.Patient", on_delete=models.CASCADE, related_name="nhcx_biometric_auths"
    )
    claim = models.ForeignKey(
        "nhcx.Claim",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="biometric_auths",
    )
    payer_code = models.CharField(max_length=255)
    stage = models.CharField(max_length=16, choices=BiometricStage.choices)
    method = models.CharField(max_length=16, choices=BiometricMethod.choices)
    status = models.CharField(
        max_length=16,
        default=BiometricStatus.initiated,
        choices=BiometricStatus.choices,
    )
    txn_id = code_field()
    abha_number = code_field(max_length=32)
    user_token = text_field()
    token_expires_at = timestamp_field()
    refresh_token = text_field()
    refresh_expires_at = timestamp_field()
    message = text_field()
    requested_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="nhcx_biometric_auths",
    )
    verified_at = timestamp_field()

    class Meta:
        indexes = [
            models.Index(
                fields=["patient", "payer_code", "stage", "created_date"],
                name="ix_biometric_auth_current",
            ),
        ]
