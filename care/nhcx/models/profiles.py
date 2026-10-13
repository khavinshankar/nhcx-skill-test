"""D1 and D2 extensions: NHCX fields of a CARE facility and practitioner."""

from django.db import models

from care.nhcx.models.base import NhcxBaseModel, code_field, url_field

NDHM_IDENTIFIER_TYPE_SYSTEM = (
    "https://nrces.in/ndhm/fhir/r4/CodeSystem/ndhm-identifier-type-code"
)
HL7_V2_0203_SYSTEM = "http://terminology.hl7.org/CodeSystem/v2-0203"
FACILITY_IDENTIFIER_SYSTEM = "https://facility.abdm.gov.in"
DOCTOR_IDENTIFIER_SYSTEM = "https://doctor.abdm.gov.in"


class FacilityIdentifierType(models.TextChoices):
    NHRR = "NHRR"
    ROHINI = "ROHINI"
    PMJAY = "PMJAY"
    OIN = "OIN"
    PRN = "PRN"


class OrganizationType(models.TextChoices):
    prov = "prov"
    dept = "dept"
    team = "team"
    ins = "ins"
    other = "other"


class FacilityProfile(NhcxBaseModel):
    """D1 organization: NHCX identity of one CARE facility.

    ``name``, ``phone`` and the address come from ``facility.Facility``.
    ``hfr_id`` is the spec's ``identifier_value`` (the ``providerId``).
    """

    facility = models.OneToOneField(
        "facility.Facility", on_delete=models.CASCADE, related_name="nhcx_profile"
    )
    hfr_id = code_field()
    participant_code = code_field()
    identifier_type_system = url_field(default=NDHM_IDENTIFIER_TYPE_SYSTEM)
    identifier_type_code = code_field(
        default=FacilityIdentifierType.NHRR, choices=FacilityIdentifierType.choices
    )
    identifier_type_display = code_field(
        default="National Health Resource Repository (NHRR) ID"
    )
    identifier_system = url_field(default=FACILITY_IDENTIFIER_SYSTEM)
    type_code = code_field(
        default=OrganizationType.prov, choices=OrganizationType.choices
    )
    type_display = code_field(default="Healthcare Provider")
    email = code_field()
    gstin = code_field()

    def __str__(self):
        return f"NHCX profile of {self.facility_id}"


class PractitionerIdentifierType(models.TextChoices):
    HPID = "HPID"
    MD = "MD"
    OIN = "OIN"


class PractitionerProfile(NhcxBaseModel):
    """D2 practitioner: NHCX fields of one CARE user.

    ``name``, ``gender``, ``phone`` and ``email`` come from ``users.User``.
    ``hpr_id`` is the spec's ``identifier_value`` (HPR id or registration number).
    """

    user = models.OneToOneField(
        "users.User",
        on_delete=models.CASCADE,
        related_name="nhcx_practitioner_profile",
    )
    prefix = code_field(default="Dr")
    identifier_type_system = url_field(default=NDHM_IDENTIFIER_TYPE_SYSTEM)
    identifier_type_code = code_field(
        default=PractitionerIdentifierType.HPID,
        choices=PractitionerIdentifierType.choices,
    )
    identifier_type_display = code_field(default="Healthcare Professional ID (HPID)")
    identifier_system = url_field(default=DOCTOR_IDENTIFIER_SYSTEM)
    hpr_id = code_field()
    qualification_code = code_field(default="BS")
    qualification_display = code_field()
    qualification_system = url_field(default=HL7_V2_0203_SYSTEM)
    role_code = code_field(default="158965000")
    role_display = code_field(default="Medical practitioner")
    specialty_code = code_field()
    specialty_display = code_field()
    department = code_field()
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"NHCX practitioner profile of {self.user_id}"
