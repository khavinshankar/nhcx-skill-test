"""Plain inputs for the FHIR builders.

Field names follow the database columns (D tables) they are filled from, so a
service can fill them straight from model rows.
"""

from dataclasses import dataclass, field
from typing import Any


class FhirBuildError(ValueError):
    """A refusal before building: the message is shown to the desk verbatim."""


@dataclass
class FacilityInput:
    """D1 facility: HFR id and name; participant_code is the NHCX code."""

    identifier_value: str = ""
    name: str = ""
    participant_code: str = ""


@dataclass
class PayerInput:
    """D9 claim.payer_id (participant code) and payer_name."""

    payer_id: str = ""
    payer_name: str = ""


@dataclass
class PatientInput:
    """D9 claim columns plus the patient's own details when known."""

    member_id: str = ""
    abha_number: str = ""
    beneficiary_name: str = ""
    patient_name: str = ""
    mobile_number: str = ""
    patient_gender: str = ""
    patient_dob: Any = None
    aadhaar_number: str = ""


@dataclass
class CoverageInput:
    """D9 claim.policy_code and member_id."""

    policy_code: str = ""
    member_id: str = ""


@dataclass
class PractitionerInput:
    """D2 practitioner."""

    id: Any = None
    name: str = ""
    identifier_value: str = ""
    qualification_display: str = ""
    specialty_code: str = ""
    specialty_display: str = ""
    license_number: str = ""


@dataclass
class LineInput:
    """D16 claim_line. kind is Procedure, Implant or Stratification."""

    kind: str = "Procedure"
    code: str = ""
    display: str = ""
    category_code: str = ""
    category_display: str = ""
    unit_price: Any = None
    quantity: Any = 1
    amount: Any = None
    parent_code: str = ""
    seq: int = 0


@dataclass
class DiagnosisInput:
    """D25 claim_diagnosis."""

    icd10_code: str = ""
    icd10_display: str = ""
    seq: int = 0


@dataclass
class DocumentInput:
    """D28 claim_document. data is raw bytes or an already base64 str."""

    id: Any = None
    filename: str = ""
    content_type: str = ""
    label: str = ""
    code: str = ""
    category: str = ""
    stage: str = ""
    data: Any = b""
    uploaded_at: Any = None


@dataclass
class FormInput:
    """D12 claim_plan_form: items as stored ({linkId, type, text, ...})."""

    url: str = ""
    title: str = ""
    kind: str = "questionnaire"
    items: list = field(default_factory=list)


@dataclass
class FormAnswer:
    """D17 claim_form_answer. answer is text, or a DocumentInput for a file."""

    form_url: str = ""
    link_id: str = ""
    answer: Any = None
    stage: str = ""


@dataclass
class ClaimInput:
    """Everything one F8 Claim bundle needs.

    kind: preauth, enhancement, preauth-queryupdate, predetermination,
    claim or claim-queryupdate.
    documents: the leg's D28 rows; the builder drops those of another
    stage, files given as form answers, and on the claim HDS-coded files.
    procedure_types: package code -> ProcedureType condition (D11).
    lama_package: the plan's LM100 row as {display, rate, category_code,
    category_display}, or None.
    """

    kind: str = "preauth"
    claim_no: str = ""
    patient: PatientInput = field(default_factory=PatientInput)
    facility: FacilityInput = field(default_factory=FacilityInput)
    payer: PayerInput = field(default_factory=PayerInput)
    coverage: CoverageInput = field(default_factory=CoverageInput)
    practitioners: list = field(default_factory=list)
    diagnoses: list = field(default_factory=list)
    lines: list = field(default_factory=list)
    documents: list = field(default_factory=list)
    discharge_summary: DocumentInput | None = None
    forms: list = field(default_factory=list)
    answers: list = field(default_factory=list)
    admission_date: Any = None
    expected_discharge_date: Any = None
    discharge_mode: str = ""
    discharge_stage: str = ""
    discharge_date: Any = None
    surgery_date: Any = None
    death_date: Any = None
    preauth_ref: str = ""
    reply_text: str = ""
    procedure_types: dict = field(default_factory=dict)
    lama_package: dict | None = None
    program_code: bool = False
    procedure_factor: bool = False
    created: Any = None


@dataclass
class EligibilityInput:
    """F2 coverage eligibility request. tier_offers: procedure code -> tier codes."""

    purpose: str = "validation"
    patient: PatientInput = field(default_factory=PatientInput)
    facility: FacilityInput = field(default_factory=FacilityInput)
    payer: PayerInput = field(default_factory=PayerInput)
    coverage: CoverageInput = field(default_factory=CoverageInput)
    lines: list = field(default_factory=list)
    tier_offers: dict = field(default_factory=dict)
    created: Any = None


@dataclass
class TaskInput:
    """F10 claim-action Task.

    action: cancel, status, reprocess or release; leg: preauth or claim
    (status only). reason: the reason code; note: the description text.
    intimation_type: intimationNumber, or initimationNumber for a PMJAY
    cancel. member_scheme: pmjay or generic (reprocess for.identifier).
    """

    action: str = "status"
    leg: str = "preauth"
    claim_no: str = ""
    facility: FacilityInput = field(default_factory=FacilityInput)
    payer: PayerInput = field(default_factory=PayerInput)
    reason: str = ""
    note: str = ""
    intimation_number: str = ""
    intimation_type: str = "intimationNumber"
    member_id: str = ""
    member_scheme: str = "generic"
    amount: Any = None
    documents: list = field(default_factory=list)
    authored_on: Any = None


@dataclass
class ReplyInput:
    """F12 reply to a payer query (D23 claim_query + D9 claim).

    request_bundle: D23 request_json; sent_bundle: the queried leg's sent
    bundle (D18/D20 request_json), or None.
    """

    claim_no: str = ""
    query_id: Any = None
    kind: str = "query"
    claim_ref: str = ""
    reason_code: str = ""
    request_id: str = ""
    reply_text: str = ""
    documents: list = field(default_factory=list)
    request_bundle: dict | None = None
    sent_bundle: dict | None = None
    leg: str = "preauth"
    payer_system: str = ""
    facility: FacilityInput = field(default_factory=FacilityInput)
    payer: PayerInput = field(default_factory=PayerInput)
    patient: PatientInput = field(default_factory=PatientInput)
    coverage: CoverageInput = field(default_factory=CoverageInput)
