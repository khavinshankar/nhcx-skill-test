"""Instance-level patient identifier configs for the ABHA number and address (D3)."""

import uuid

from django.db import migrations

ABHA_NUMBER_SYSTEM = "https://healthid.abdm.gov.in"
ABHA_ADDRESS_SYSTEM = "https://healthid.abdm.gov.in/address"


def _config(use, system, display, description, regex):
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


CONFIGS = [
    _config(
        "official",
        ABHA_NUMBER_SYSTEM,
        "ABHA Number",
        "Ayushman Bharat Health Account number (14 digits)",
        r"^\d{2}-?\d{4}-?\d{4}-?\d{4}$",
    ),
    _config(
        "secondary",
        ABHA_ADDRESS_SYSTEM,
        "ABHA Address",
        "Ayushman Bharat Health Account address",
        r"^[A-Za-z0-9._]+(@[A-Za-z0-9.]+)?$",
    ),
]


def create_abha_configs(apps, schema_editor):
    PatientIdentifierConfig = apps.get_model("emr", "PatientIdentifierConfig")
    for config in CONFIGS:
        exists = PatientIdentifierConfig.objects.filter(
            facility__isnull=True, config__system=config["system"], deleted=False
        ).exists()
        if not exists:
            PatientIdentifierConfig.objects.create(
                external_id=uuid.uuid4(),
                facility=None,
                status="active",
                config=config,
            )


class Migration(migrations.Migration):
    dependencies = [
        ("nhcx", "0001_initial"),
        ("emr", "0082_remove_encounter_encounter_class_history"),
    ]

    operations = [
        migrations.RunPython(create_abha_configs, migrations.RunPython.noop),
    ]
