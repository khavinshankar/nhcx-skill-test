"""Sample inputs shared by the FHIR tests."""

from datetime import date, datetime

from care.nhcx.fhir.bundle import IST
from care.nhcx.fhir.inputs import (
    ClaimInput,
    CoverageInput,
    DiagnosisInput,
    DocumentInput,
    EligibilityInput,
    FacilityInput,
    FormAnswer,
    FormInput,
    LineInput,
    PatientInput,
    PayerInput,
    PractitionerInput,
    ReplyInput,
    TaskInput,
)

CREATED = datetime(2026, 9, 10, 10, 30, tzinfo=IST)


def facility():
    return FacilityInput(
        identifier_value="IN2910000001",
        name="Sample Hospital",
        participant_code="1000003463@sbx",
    )


def payer():
    return PayerInput(payer_id="1000002942@sbx", payer_name="Sandbox Payer")


def patient():
    return PatientInput(
        member_id="PMJAY-123",
        abha_number="91-1234-1234-1234",
        beneficiary_name="Ravi Kumar",
        patient_name="Ravi Kumar",
        mobile_number="9999999999",
        patient_gender="male",
        patient_dob=date(1985, 6, 15),
    )


def coverage():
    return CoverageInput(policy_code="POL-001", member_id="PMJAY-123")


def practitioner():
    return PractitionerInput(
        id=7,
        name="Dr. Asha Rao",
        identifier_value="71-0000-0000-0001",
        qualification_display="MBBS",
        specialty_code="394802001",
        specialty_display="General medicine",
        license_number="KMC-1234",
    )


def lines():
    return [
        LineInput(
            kind="Procedure",
            code="MG0111A",
            display="Pleural Effusion",
            category_code="MG",
            category_display="General Medicine",
            unit_price=1800,
            quantity=1,
            amount=1800,
            seq=1,
        ),
        LineInput(
            kind="Stratification",
            code="STRAT006a",
            display="Routine Ward",
            unit_price=900,
            quantity=2,
            amount=1800,
            parent_code="MG0111A",
            seq=2,
        ),
    ]


def document(stage="preauth", code="DIA", **kwargs):
    values = {
        "id": 11,
        "filename": "xray.pdf",
        "content_type": "application/pdf",
        "label": "Chest X-ray",
        "code": code,
        "category": "DIA",
        "stage": stage,
        "data": b"%PDF-1.4 sample",
        "uploaded_at": CREATED,
    }
    values.update(kwargs)
    return DocumentInput(**values)


def form():
    return FormInput(
        url="https://payer.example/Questionnaire/PROC-1",
        title="Clinical form",
        items=[
            {"linkId": "1", "type": "string", "text": "Indication", "required": True},
            {"linkId": "2", "type": "boolean", "text": "Smoker"},
        ],
    )


def claim_input(kind="preauth", **kwargs):
    values = {
        "kind": kind,
        "claim_no": "NM-26-0001",
        "patient": patient(),
        "facility": facility(),
        "payer": payer(),
        "coverage": coverage(),
        "practitioners": [practitioner()],
        "diagnoses": [DiagnosisInput("J90", "Pleural effusion", 1)],
        "lines": lines(),
        "documents": [document()],
        "forms": [form()],
        "answers": [
            FormAnswer(form().url, "1", "Breathlessness", "preauth"),
            FormAnswer(form().url, "2", "no", "preauth"),
        ],
        "admission_date": date(2026, 9, 9),
        "expected_discharge_date": date(2026, 9, 12),
        "procedure_types": {"MG0111A": "Conservative"},
        "created": CREATED,
    }
    values.update(kwargs)
    return ClaimInput(**values)


def eligibility_input(purpose="validation", **kwargs):
    values = {
        "purpose": purpose,
        "patient": patient(),
        "facility": facility(),
        "payer": payer(),
        "coverage": coverage(),
        "lines": lines(),
        "created": CREATED,
    }
    values.update(kwargs)
    return EligibilityInput(**values)


def task_input(action="cancel", **kwargs):
    values = {
        "action": action,
        "claim_no": "NM-26-0001",
        "facility": facility(),
        "payer": payer(),
        "intimation_number": "NM-26-0001",
        "authored_on": CREATED,
    }
    values.update(kwargs)
    return TaskInput(**values)


def reply_input(**kwargs):
    values = {
        "claim_no": "NM-26-0001",
        "query_id": 5,
        "kind": "query",
        "claim_ref": "NM-26-0001",
        "reason_code": "additionalinfo",
        "request_id": "req-1",
        "reply_text": "Attached the X-ray.",
        "documents": [document()],
        "payer_system": "https://payer.example",
        "facility": facility(),
        "payer": payer(),
        "patient": patient(),
        "coverage": coverage(),
    }
    values.update(kwargs)
    return ReplyInput(**values)
