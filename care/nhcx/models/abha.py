"""D3 extension: a patient's ABHA number and address as CARE patient identifiers.

Both live in ``emr.PatientIdentifier`` under instance-level
``emr.PatientIdentifierConfig`` rows (created by migration 0002) whose
``config.system`` is :data:`ABHA_NUMBER_SYSTEM` / :data:`ABHA_ADDRESS_SYSTEM`.
ABHA numbers are compared digits only.
"""

import re

from django.db import models, transaction

from care.emr.models.patient import (
    Patient,
    PatientIdentifier,
    PatientIdentifierConfig,
    PatientIdentifierConfigCache,
)

ABHA_NUMBER_SYSTEM = "https://healthid.abdm.gov.in"
ABHA_ADDRESS_SYSTEM = "https://healthid.abdm.gov.in/address"
ABHA_NUMBER_REGEX = r"^\d{2}-?\d{4}-?\d{4}-?\d{4}$"
ABHA_ADDRESS_REGEX = r"^[A-Za-z0-9._]+(@[A-Za-z0-9.]+)?$"
DUPLICATE_ABHA_MESSAGE = "Another patient is already registered with that ABHA number"


def _identifier_config(use, system, display, description, regex):
    return {
        "use": use,
        "description": description,
        "system": system,
        "required": False,
        "unique": True,
        "regex": regex,
        "display": display,
        "retrieve_config": {
            "retrieve_with_dob": False,
            "retrieve_with_year_of_birth": True,
            "retrieve_with_otp": False,
            "retrieve_partial_search": False,
        },
        "default_value": None,
        "auto_maintained": False,
    }


ABHA_NUMBER_CONFIG = _identifier_config(
    "official",
    ABHA_NUMBER_SYSTEM,
    "ABHA Number",
    "Ayushman Bharat Health Account number (14 digits)",
    ABHA_NUMBER_REGEX,
)
ABHA_ADDRESS_CONFIG = _identifier_config(
    "secondary",
    ABHA_ADDRESS_SYSTEM,
    "ABHA Address",
    "Ayushman Bharat Health Account address",
    ABHA_ADDRESS_REGEX,
)


def abha_digits(value) -> str:
    return re.sub(r"\D", "", value or "")


def _get_config(system: str, config: dict) -> PatientIdentifierConfig:
    found = PatientIdentifierConfig.objects.filter(
        facility__isnull=True, config__system=system
    ).first()
    if found:
        return found
    created = PatientIdentifierConfig.objects.create(
        facility=None, status="active", config=config
    )
    PatientIdentifierConfigCache.clear_cache()
    return created


def get_abha_number_config() -> PatientIdentifierConfig:
    return _get_config(ABHA_NUMBER_SYSTEM, ABHA_NUMBER_CONFIG)


def get_abha_address_config() -> PatientIdentifierConfig:
    return _get_config(ABHA_ADDRESS_SYSTEM, ABHA_ADDRESS_CONFIG)


def _value(patient, system: str) -> str | None:
    identifier = (
        PatientIdentifier.objects.filter(
            patient=patient,
            config__facility__isnull=True,
            config__config__system=system,
        )
        .order_by("-modified_date")
        .first()
    )
    return identifier.value if identifier else None


def get_abha_number(patient) -> str | None:
    """The patient's ABHA number as stored (with or without dashes)."""
    return _value(patient, ABHA_NUMBER_SYSTEM)


def get_abha_address(patient) -> str | None:
    return _value(patient, ABHA_ADDRESS_SYSTEM)


def _digits_only(expression):
    return models.Func(
        expression,
        models.Value(r"[^0-9]"),
        models.Value(""),
        models.Value("g"),
        function="regexp_replace",
        output_field=models.CharField(),
    )


def find_patients_by_abha(number):
    """Patients whose ABHA number equals ``number``, compared digits only."""
    digits = abha_digits(number)
    if not digits:
        return Patient.objects.none()
    patient_ids = (
        PatientIdentifier.objects.filter(
            config__facility__isnull=True, config__config__system=ABHA_NUMBER_SYSTEM
        )
        .annotate(digits=_digits_only(models.F("value")))
        .filter(digits=digits)
        .values("patient_id")
    )
    return Patient.objects.filter(id__in=patient_ids)


def _put(patient, config, value):
    identifier = PatientIdentifier.objects.filter(
        patient=patient, config=config
    ).first()
    if not value:
        if identifier:
            identifier.delete()
        return
    if identifier:
        identifier.value = value
        identifier.save(update_fields=["value", "modified_date"])
    else:
        PatientIdentifier.objects.create(patient=patient, config=config, value=value)


def set_abha(patient, number=None, address=None):
    """Write the patient's ABHA number and/or address (``None`` leaves it as
    is, ``""`` removes it) and rebuild the patient's identifier cache.

    Raises ``ValueError`` with the spec's message when another patient holds
    the same ABHA number.
    """
    with transaction.atomic():
        if number is not None:
            if number and find_patients_by_abha(number).exclude(id=patient.id).exists():
                raise ValueError(DUPLICATE_ABHA_MESSAGE)
            _put(patient, get_abha_number_config(), number.strip())
        if address is not None:
            _put(patient, get_abha_address_config(), address.strip())
        patient.build_instance_identifiers()
        patient.save()
