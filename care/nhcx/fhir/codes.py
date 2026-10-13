"""NHCX code systems, fixed codings and lookups (F1, F8, F15-F18, D8)."""

import re

BASE_URL = "https://nhcx.abdm.gov.in"
PROFILE_BASE = "https://nrces.in/ndhm/fhir/r4/StructureDefinition/"
NRCES_CS = "https://nrces.in/ndhm/fhir/r4/CodeSystem/"
HL7_CS = "http://terminology.hl7.org/CodeSystem/"

# Code systems
SNOMED = "http://snomed.info/sct"
ICD10 = "http://hl7.org/fhir/sid/icd-10"
V2_0203 = HL7_CS + "v2-0203"
V2_0360 = HL7_CS + "v2-0360"
V3_ACTCODE = HL7_CS + "v3-ActCode"
ORG_TYPE = HL7_CS + "organization-type"
SUBSCRIBER_RELATIONSHIP = HL7_CS + "subscriber-relationship"
PROCESS_PRIORITY = HL7_CS + "processpriority"
CARE_TEAM_ROLE = HL7_CS + "claimcareteamrole"
DIAGNOSIS_TYPE = HL7_CS + "ex-diagnosistype"
DIAGNOSIS_ON_ADMISSION = HL7_CS + "ex-diagnosis-on-admission"
FINANCIAL_TASK_CODE = HL7_CS + "financialtaskcode"
FINANCIAL_TASK_INPUT_TYPE = HL7_CS + "financialtaskinputtype"
COMMUNICATION_CATEGORY = HL7_CS + "communication-category"
NDHM_IDENTIFIER_TYPE = NRCES_CS + "ndhm-identifier-type-code"
NDHM_TASK_INPUT_TYPE = NRCES_CS + "ndhm-task-input-type-code"
NDHM_TASK_OUTPUT_TYPE = NRCES_CS + "ndhm-task-output-type"
NDHM_TASK_OUTPUT_VALUE = NRCES_CS + "ndhm-task-output-value"
NDHM_TASK_CODES = NRCES_CS + "ndhm-task-codes"
NDHM_REASON_CODE = NRCES_CS + "ndhm-reason-code"
NDHM_PROCEDURE_CODE = NRCES_CS + "ndhm-procedure-code"
NDHM_BENEFIT_CATEGORY = NRCES_CS + "ndhm-benefit-category"
NDHM_PROGRAM_CODE = NRCES_CS + "ndhm-program-code"
NDHM_SUPPORTINGINFO_CATEGORY = NRCES_CS + "ndhm-supportinginfo-category"
NDHM_SUPPORTINGINFO_CODE = NRCES_CS + "ndhm-supportinginfo-code"
NHCX_CATEGORY_CODE = BASE_URL + "/category-code"
NHCX_PRODUCT_CODE = BASE_URL + "/product-code"
NHCX_PROCEDURE_TYPE = BASE_URL + "/procedure-type"
NHCX_DOCUMENT_CODE = BASE_URL + "/document-code"
NHCX_TASK_INPUT_TYPE = BASE_URL + "/task-input-type"
HPR_SYSTEM = "https://hpr.abdm.gov.in"

CURRENCY = "INR"


def profile(name):
    return PROFILE_BASE + name


PROFILES = {
    name: profile(name)
    for name in (
        "CoverageEligibilityRequestBundle",
        "CoverageEligibilityRequest",
        "ClaimBundle",
        "Claim",
        "TaskBundle",
        "Task",
        "Patient",
        "Practitioner",
        "PractitionerRole",
        "Organization",
        "Coverage",
        "Procedure",
        "QuestionnaireResponse",
        "Communication",
    )
}


def coding(system, code, display=None):
    out = {}
    if system:
        out["system"] = system
    out["code"] = code
    if display:
        out["display"] = display
    return out


def concept(system, code, display=None, text=None):
    out = {"coding": [coding(system, code, display)]}
    if text:
        out["text"] = text
    return out


# Identifier types (F15-F18, F8, F10)
IDENTIFIER_TYPES = {
    "PMJAY": (NDHM_IDENTIFIER_TYPE, "Pradhan Mantri Jan Aarogya Yojana (PMJAY) ID"),
    "ABHA": (NDHM_IDENTIFIER_TYPE, "Ayushman Bharat Health Account (ABHA) ID"),
    "ADN": (NDHM_IDENTIFIER_TYPE, "Adhaar number"),
    "CLN": (NDHM_IDENTIFIER_TYPE, "Claim number"),
    "HPID": (NDHM_IDENTIFIER_TYPE, "Healthcare Professional ID (HPID)"),
    "HPIN": (NDHM_IDENTIFIER_TYPE, "Health Practitioner ID issued by NDHM"),
    "MB": (V2_0203, "Member Number"),
    "MD": (V2_0203, "Medical License number"),
    "NPI": (V2_0203, "National provider identifier"),
    "NIIP": (V2_0203, "National Insurance Payor Identifier (Payor)"),
    "NH": (V2_0203, "National Health Plan Identifier"),
}


def identifier_type(code):
    system, display = IDENTIFIER_TYPES[code]
    return concept(system, code, display)


GENDERS = {"male", "female", "other", "unknown"}


def gender(value):
    """FHIR administrative gender, lower-cased; unknown words pass through lower."""
    value = (value or "").strip().lower()
    return {"m": "male", "f": "female", "o": "other", "u": "unknown"}.get(value, value)


RELATIONSHIP_SELF = coding(SUBSCRIBER_RELATIONSHIP, "self")

# F16 qualification (v2-0360)
DEGREES = {
    "RN": "Registered Nurse",
    "PHD": "Doctor of Philosophy",
    "MS": "Master of Science",
    "DO": "Doctor of Osteopathy",
    "DDS": "Doctor of Dental Surgery",
    "MD": "Doctor of Medicine",
}


def degree_code(qualification_display):
    """Map a free-text qualification to a v2-0360 degree code (F16, first match wins)."""
    text = (qualification_display or "").upper()
    parts = {p.strip(".") for p in re.split(r"[\s,()\[\]/;]+", text) if p.strip(".")}
    if "BSC" in parts and "NURS" in text:
        code = "RN"
    elif "PHD" in parts:
        code = "PHD"
    elif parts & {"MS", "MCH"}:
        code = "MS"
    elif "DO" in parts:
        code = "DO"
    elif parts & {"BDS", "MDS"}:
        code = "DDS"
    elif parts & {"RN", "GNM"}:
        code = "RN"
    else:
        code = "MD"
    return code, DEGREES[code]


# F2 eligibility purposes
ELIGIBILITY_PURPOSES = ("validation", "benefits", "discovery", "auth-requirements")

# F8 Claim
CLAIM_TYPE = concept(SNOMED, "737481003", "Inpatient care management (procedure)")
PRIORITY_NORMAL = concept(PROCESS_PRIORITY, "normal", "Normal")
PROGRAM_PMJAY = concept(
    NDHM_PROGRAM_CODE,
    "AB-PMJAY",
    "Ayushman Bharat Pradhan Mantri Jan Arogya Yojana (AB-PMJAY)",
)
SUPPORTINGINFO_CATEGORIES = {
    "INV": "Document Type - Investigation",
    "HDS": "Hospital discharge summary",
    "OTH": "Other",
    "ODN": "Other document",
    "ONS": "Period, start or end dates of aspects of the Condition. (e.g. admission, discharge etc)",
    "DIS": "Discharge status and discharge to location detail",
    "NMI": "Claim query detail",
    "INF": "Information",
    "STG": "Standard Treatment Guidelines",
}
SUPPORTINGINFO_CODES = {
    "ADDD": "Admission date -Discharge date",
    "EDT": "EncounterDateTime",
    "PSP": "PatientSurgeryPerformed(startdatetime-enddatetime)",
    "DSDE": "Discharge start-discharge end time",
    "DTM": "DischargetoMortuary",
    "CQD": "Claim query detail",
    "ODN": "Other document",
    "STG": "Standard Treatment Guidelines",
}
# discharge_mode -> (DIS code, DIS display, default valueString)
DISCHARGE_MODES = {
    "normal": (
        "DTH",
        "DischargeToHome (Discharge disposition status)",
        "Discharged to home",
    ),
    "lama": ("LAMA", "Left against medical advice", "Left against medical advice"),
    "dama": (
        "DAMA",
        "Discharged against medical advice",
        "Discharged against medical advice",
    ),
    "death": ("DTM", "Death", "Died in hospital"),
}
LAMA_DAMA_STAGES = {"before surgery", "during surgery"}
LAMA_CODE = "LM100"
LAMA_DISPLAY = "LAMA / DAMA procedure"

# F10 reason codes (ndhm-reason-code)
CANCEL_REASONS = {
    "treatmentplanchanged": "Treatment plan changed during hospitalization",
    "patientrequest": "Patient requested cancellation",
    "financialconstraints": "Financial constraints",
    "alternativetreatment": "Alternative treatment chosen",
    "duplicateclaim": "Duplicate claim / preauth",
    "administrativeerror": "Administrative error",
    "other": "Other reason",
}
REPROCESS_REASONS = {
    "claimrejected": "Reprocess request due to claim rejected by payer",
    "partialpayment": "Reprocess request due to partial payment by payer",
    "rejectiondisputed": "Rejection disputed, additional evidence provided",
}
RELEASE_REASONS = {"partialpayment": REPROCESS_REASONS["partialpayment"]}

# F11 query reason words
QUERY_REASONS = {
    "tatquery": "Turnaround time query",
    "grievance": "Grievance",
    "walletupdate": "Wallet or benefit update",
    "policychange": "Policy change",
    "additionalinfo": "Additional information request",
    "claimarbitration": "Claim arbitration intimation",
    "questionnaire": "Questionnaire",
    "query": "Query",
}


def reason_word(code):
    code = code or ""
    return QUERY_REASONS.get(code.lower(), code)


def lookups():
    """All lookup tables, for screens and services that list choices."""
    return {
        "identifier_types": {k: v[1] for k, v in IDENTIFIER_TYPES.items()},
        "degrees": dict(DEGREES),
        "eligibility_purposes": list(ELIGIBILITY_PURPOSES),
        "supportinginfo_categories": dict(SUPPORTINGINFO_CATEGORIES),
        "supportinginfo_codes": dict(SUPPORTINGINFO_CODES),
        "discharge_modes": {k: v[1] for k, v in DISCHARGE_MODES.items()},
        "cancel_reasons": dict(CANCEL_REASONS),
        "reprocess_reasons": dict(REPROCESS_REASONS),
        "release_reasons": dict(RELEASE_REASONS),
        "query_reasons": dict(QUERY_REASONS),
        "profiles": dict(PROFILES),
    }
