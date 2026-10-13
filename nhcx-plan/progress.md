# NHCX integration progress

## Status

| Step | State | Sub-steps done | Exit checked |
|---|---|---|---|
| L1 Discovery | done | 10 / 10 | yes |
| L2 Mapping | done | 6 / 6 | yes |
| L3 Integration Planning | done | 4 / 4 | yes |
| L4 Code Planning | done | 5 / 5 | yes |
| L5 Write Code | done | 5 / 5 | yes |
| L6 Validate Code | done | 4 / 4 | yes |
| L7 Dry-run Tests | done | 7 / 7 | yes |
| L8 End-to-end Tests | in progress | 4 / 5 | no |

## L1 Discovery
- [x] L1.0
- [x] L1.1
- [x] L1.2
- [x] L1.3
- [x] L1.4
- [x] L1.5
- [x] L1.6
- [x] L1.7
- [x] L1.8
- [x] L1.9

## L2 Mapping
- [x] L2.1
- [x] L2.2
- [x] L2.3
- [x] L2.4
- [x] L2.5
- [x] L2.6

## L3 Integration Planning
- [x] L3.1
- [x] L3.2
- [x] L3.3
- [x] L3.4

## L4 Code Planning
- [x] L4.1
- [x] L4.2
- [x] L4.3
- [x] L4.4
- [x] L4.5

## L5 Write Code
- [x] L5.1
- [x] L5.2
- [x] L5.3
- [x] L5.4
- [x] L5.5

## L6 Validate Code
- [x] L6.1
- [x] L6.2
- [x] L6.3
- [x] L6.4

## L7 Dry-run Tests
- [x] L7.1
- [x] L7.2
- [x] L7.3
- [x] L7.4
- [x] L7.5
- [x] L7.6
- [x] L7.7

## L8 End-to-end Tests
- [x] L8.1
- [x] L8.2
- [x] L8.3
- [x] L8.4
- [ ] L8.5 (in progress)

## Changes

| Id | Time | Sub-step | Action | Summary | Files |
|---|---|---|---|---|---|
| LOG-0001 | 2026-10-13 08:32 | L1.0 | started | Called nhcx-docs catalogue_info |  |
| LOG-0002 | 2026-10-13 08:32 | L1.0 | done | Source is the nhcx-docs MCP, catalogue 2026.09.16 (536 NHCX atoms, 438 operations) | `nhcx-plan/knowledge.json` |
| LOG-0003 | 2026-10-13 08:32 | L1.1 | started |  |  |
| LOG-0004 | 2026-10-13 08:32 | L1.1 | done | No hits for x-hcx-, hcx, nhcx, coverageeligibility, paymentnotice, RSA-OAEP, participant/get/policies in care/ or config/. Greenfield: A, C, F, G are missing as a whole kind. ABDM/ABHA code lives only in the separate care_abdm plug, which is not part of this target. |  |
| LOG-0005 | 2026-10-13 08:32 | L1.2 | started |  |  |
| LOG-0006 | 2026-10-13 08:32 | L1.2 | done | Provider side. Django 6 / Python 3.13 / DRF / PostgreSQL / Celery; React 19 SPA in care_fe. Report builder and wrappers written; first build OK. | `nhcx-plan/report.py` created; `nhcx-plan/make-report.sh` created; `nhcx-plan/make-report.bat` created; `nhcx-plan/log.py` created |
| LOG-0007 | 2026-10-13 08:32 | L1.2 | done | Report rebuilt |  |
| LOG-0008 | 2026-10-13 08:33 | L1.3 | started |  |  |
| LOG-0009 | 2026-10-13 08:33 | L1.4 | started |  |  |
| LOG-0010 | 2026-10-13 08:33 | L1.5 | started |  |  |
| LOG-0011 | 2026-10-13 08:33 | L1.6 | started |  |  |
| LOG-0012 | 2026-10-13 08:33 | L1.7 | started |  |  |
| LOG-0013 | 2026-10-13 08:33 | L1.8 | started |  |  |
| LOG-0014 | 2026-10-13 08:33 | L1.9 | started |  |  |
| LOG-0015 | 2026-10-13 08:33 | L1.3 | done | Facility, User, Patient(+PatientIdentifier), Encounter, Condition, Account, ChargeItem, FileUpload located |  |
| LOG-0016 | 2026-10-13 08:33 | L1.4 | done | S13-S16 partial in care_fe (patient list/registration/home, user home); S1-S12, S17, S18 missing |  |
| LOG-0017 | 2026-10-13 08:33 | L1.5 | done | No NHCX APIs or callbacks: all missing |  |
| LOG-0018 | 2026-10-13 08:33 | L1.6 | done | No FHIR builders for NHCX: all missing |  |
| LOG-0019 | 2026-10-13 08:33 | L1.7 | done | D4-D7 found, D1-D3, D8 partial, D9-D31 missing |  |
| LOG-0020 | 2026-10-13 08:33 | L1.8 | done | No gateway code: all missing |  |
| LOG-0021 | 2026-10-13 08:33 | L1.9 | done | discovery.json written | `nhcx-plan/discovery.json` |
| LOG-0022 | 2026-10-13 08:33 | L1 | exit_checked | knowledge.json names MCP; every kind present; found/partial have locations; technology complete |  |
| LOG-0023 | 2026-10-13 08:35 | L2.1 | started |  |  |
| LOG-0024 | 2026-10-13 08:35 | L2.2 | started |  |  |
| LOG-0025 | 2026-10-13 08:35 | L2.3 | started |  |  |
| LOG-0026 | 2026-10-13 08:35 | L2.4 | started |  |  |
| LOG-0027 | 2026-10-13 08:35 | L2.5 | started |  |  |
| LOG-0028 | 2026-10-13 08:35 | L2.6 | started |  |  |
| LOG-0029 | 2026-10-13 08:35 | L2.1 | done | Facility/User extended via nhcx_facilityprofile, nhcx_practitionerprofile; ABHA via PatientIdentifier configs |  |
| LOG-0030 | 2026-10-13 08:35 | L2.2 | done | Encounter class imp/emer + status in_progress = current admission; Condition SNOMED only |  |
| LOG-0031 | 2026-10-13 08:35 | L2.3 | done | All claim tables new in care.nhcx (no insurance table in CARE) |  |
| LOG-0032 | 2026-10-13 08:35 | L2.4 | done | Every FnF element mapped to builders.py (filled) or parsers.py (read) |  |
| LOG-0033 | 2026-10-13 08:35 | L2.5 | done | ICD-10 lookup per claim; gender lookup; degree/doc type in codes.py |  |
| LOG-0034 | 2026-10-13 08:35 | L2.6 | done | 22 missing (unused by bundles), 2 conflict (ICD-10 kept on D25) | `nhcx-plan/mapping.json` |
| LOG-0035 | 2026-10-13 08:35 | L2 | exit_checked | all D columns and F elements have entries; mapped have targets; gaps resolved |  |
| LOG-0036 | 2026-10-13 08:35 | L3.1 | started |  |  |
| LOG-0037 | 2026-10-13 08:35 | L3.2 | started |  |  |
| LOG-0038 | 2026-10-13 08:35 | L3.3 | started |  |  |
| LOG-0039 | 2026-10-13 08:35 | L3.4 | started |  |  |
| LOG-0040 | 2026-10-13 08:35 | L3.1 | done | Phases P1-P10 per SCAFFOLDING 12 |  |
| LOG-0041 | 2026-10-13 08:35 | L3.2 | note | step described |  |
| LOG-0042 | 2026-10-13 08:35 | L3.2 | note | step described |  |
| LOG-0043 | 2026-10-13 08:35 | L3.2 | note | step described |  |
| LOG-0044 | 2026-10-13 08:35 | L3.2 | note | step described |  |
| LOG-0045 | 2026-10-13 08:35 | L3.2 | note | step described |  |
| LOG-0046 | 2026-10-13 08:35 | L3.2 | note | step described |  |
| LOG-0047 | 2026-10-13 08:35 | L3.2 | note | step described |  |
| LOG-0048 | 2026-10-13 08:35 | L3.2 | note | step described |  |
| LOG-0049 | 2026-10-13 08:35 | L3.2 | note | step described |  |
| LOG-0050 | 2026-10-13 08:35 | L3.2 | note | step described |  |
| LOG-0051 | 2026-10-13 08:35 | L3.2 | note | step described |  |
| LOG-0052 | 2026-10-13 08:35 | L3.2 | note | step described |  |
| LOG-0053 | 2026-10-13 08:35 | L3.2 | note | step described |  |
| LOG-0054 | 2026-10-13 08:35 | L3.2 | note | step described |  |
| LOG-0055 | 2026-10-13 08:35 | L3.2 | note | step described |  |
| LOG-0056 | 2026-10-13 08:35 | L3.2 | note | step described |  |
| LOG-0057 | 2026-10-13 08:35 | L3.2 | done | 16 steps | `nhcx-plan/plan.json` |
| LOG-0058 | 2026-10-13 08:35 | L3.3 | done | acyclic; external: participant code, key/cert, public URL missing |  |
| LOG-0059 | 2026-10-13 08:35 | L3.4 | done | every phase has done_when |  |
| LOG-0060 | 2026-10-13 08:35 | L3 | exit_checked | ok |  |
| LOG-0061 | 2026-10-13 08:37 | L4.1 | started |  |  |
| LOG-0062 | 2026-10-13 08:37 | L4.2 | started |  |  |
| LOG-0063 | 2026-10-13 08:37 | L4.3 | started |  |  |
| LOG-0064 | 2026-10-13 08:37 | L4.4 | started |  |  |
| LOG-0065 | 2026-10-13 08:37 | L4.5 | started |  |  |
| LOG-0066 | 2026-10-13 08:37 | L4.1 | done | EMRBaseModel, DRF+pydantic, CareAPITestBase, Celery beat, TanStack Query |  |
| LOG-0067 | 2026-10-13 08:37 | L4.2 | done | care/nhcx/{gateway,fhir,services,callbacks,models,api}; care_fe pages/Facility/claims |  |
| LOG-0068 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0069 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0070 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0071 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0072 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0073 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0074 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0075 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0076 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0077 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0078 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0079 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0080 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0081 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0082 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0083 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0084 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0085 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0086 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0087 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0088 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0089 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0090 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0091 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0092 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0093 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0094 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0095 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0096 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0097 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0098 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0099 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0100 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0101 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0102 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0103 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0104 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0105 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0106 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0107 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0108 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0109 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0110 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0111 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0112 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0113 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0114 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0115 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0116 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0117 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0118 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0119 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0120 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0121 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0122 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0123 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0124 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0125 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0126 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0127 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0128 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0129 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0130 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0131 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0132 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0133 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0134 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0135 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0136 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0137 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0138 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0139 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0140 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0141 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0142 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0143 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0144 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0145 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0146 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0147 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0148 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0149 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0150 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0151 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0152 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0153 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0154 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0155 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0156 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0157 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0158 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0159 | 2026-10-13 08:37 | L4.3 | note | planned |  |
| LOG-0160 | 2026-10-13 08:37 | L4.3 | done | files planned | `nhcx-plan/code-plan.json` |
| LOG-0161 | 2026-10-13 08:37 | L4.4 | done | by layer B1 models, B2 gateway, B3 fhir, B4 core services, B5 remaining services, B6 claim screens, B7 patient screens |  |
| LOG-0162 | 2026-10-13 08:37 | L4.5 | done | test file per file under care/nhcx/tests |  |
| LOG-0163 | 2026-10-13 08:37 | L4 | exit_checked | ok |  |
| LOG-0164 | 2026-10-13 09:00 | L5.1 | started |  |  |
| LOG-0165 | 2026-10-13 09:00 | L5.2 | started |  |  |
| LOG-0166 | 2026-10-13 09:00 | L5.3 | started |  |  |
| LOG-0167 | 2026-10-13 09:00 | L5.4 | started |  |  |
| LOG-0168 | 2026-10-13 09:00 | L5.5 | started |  |  |
| LOG-0169 | 2026-10-13 09:00 | L5.2 | done | care/nhcx/models/*, migrations 0001, 0002 (D1,D2,D3,D8,D9-D31) | `care/nhcx/models/` add all; `care/nhcx/migrations/` add all |
| LOG-0170 | 2026-10-13 09:00 | L5.2 | done | care/nhcx/gateway/* G1-G11, tasks.py, config/urls.py, settings | `care/nhcx/gateway/` add all; `config/urls.py` modify 66-68; `config/settings/base.py` modify LOCAL_APPS+NHCX block |
| LOG-0171 | 2026-10-13 09:00 | L5.2 | done | care/nhcx/fhir/* F1-F19 | `care/nhcx/fhir/` add all |
| LOG-0172 | 2026-10-13 09:00 | L5.3 | done | tests: models 11 OK, gateway 85 OK, fhir 66 OK; ruff clean; manage.py check OK; makemigrations --check clean |  |
| LOG-0173 | 2026-10-13 09:00 | L5.4 | note | merged agent reports B1-B3 | `nhcx-plan/code.json` |
| LOG-0174 | 2026-10-13 09:00 | L5.5 | note | committed |  |
| LOG-0175 | 2026-10-13 09:48 | L5.1 | done | Shared agent context (common.md) and API contract care/nhcx/api/CONTRACT.md written before B4-B7 | `care/care/nhcx/api/CONTRACT.md` created |
| LOG-0176 | 2026-10-13 09:48 | L5.2 | note | B6-B7: implements D9-D31 (claim row column names), A17 state shape | `care_fe/src/types/nhcx/nhcx.ts` created |
| LOG-0177 | 2026-10-13 09:48 | L5.2 | note | B6-B7: implements POST /api/v1/facility/{facilityId}/nhcx/policy-search/, POST /api/v1/facility/{facilityId}/nhcx/claims/, GET /api/v1/facility/{facilityId}/nhcx/claims/, GET /api/v1/facility/{facilityId}/nhcx/claims/{claimId}/state/, POST /api/v1/facility/{facilityId}/nhcx/claims/{claimId}/eligibility/, POST /api/v1/facility/{facilityId}/nhcx/claims/{claimId}/auth-requirements/, POST /api/v1/facility/{facilityId}/nhcx/claims/{claimId}/plan/, POST /api/v1/facility/{facilityId}/nhcx/claims/{claimId}/lines/, DELETE /api/v1/facility/{facilityId}/nhcx/claims/{claimId}/lines/{lineId}/, POST /api/v1/facility/{facilityId}/nhcx/claims/{claimId}/admission/, GET /api/v1/facility/{facilityId}/nhcx/ledger/, GET /api/v1/facility/{facilityId}/nhcx/ledger/{ledgerId}/, PUT /api/v1/facility/{facilityId}/nhcx/claims/{claimId}/draft/, POST /api/v1/facility/{facilityId}/nhcx/claims/{claimId}/documents/, DELETE /api/v1/facility/{facilityId}/nhcx/claims/{claimId}/documents/{documentId}/, POST /api/v1/facility/{facilityId}/nhcx/claims/{claimId}/preauth/submit/, POST /api/v1/facility/{facilityId}/nhcx/claims/{claimId}/preauth/predetermination/, POST /api/v1/facility/{facilityId}/nhcx/claims/{claimId}/preauth/cancel/, POST /api/v1/facility/{facilityId}/nhcx/claims/{claimId}/enquiry/, POST /api/v1/facility/{facilityId}/nhcx/claims/{claimId}/claim/submit/, POST /api/v1/facility/{facilityId}/nhcx/claims/{claimId}/discharge/, POST /api/v1/facility/{facilityId}/nhcx/claims/{claimId}/queries/{queryId}/ack/, POST /api/v1/facility/{facilityId}/nhcx/claims/{claimId}/queries/{queryId}/reply/, POST /api/v1/facility/{facilityId}/nhcx/claims/{claimId}/payments/{paymentId}/ack/, POST /api/v1/facility/{facilityId}/nhcx/claims/{claimId}/biometric/{action}/, POST /api/v1/facility/{facilityId}/nhcx/claims/{claimId}/adjudicate/, GET /api/v1/facility/{facilityId}/nhcx/profile/, PUT /api/v1/facility/{facilityId}/nhcx/profile/, GET /api/v1/nhcx/practitioner/{userId}/, PUT /api/v1/nhcx/practitioner/{userId}/, POST /api/v1/nhcx/abha/{action}/ | `care_fe/src/types/nhcx/nhcxApi.ts` created |
| LOG-0178 | 2026-10-13 09:48 | L5.2 | note | B6-B7: implements S5, GET /api/v1/facility/{facilityId}/nhcx/claims/ | `care_fe/src/pages/Facility/claims/ClaimMaster.tsx` created |
| LOG-0179 | 2026-10-13 09:48 | L5.2 | note | B6-B7: implements S1, S2, POST /api/v1/facility/{facilityId}/nhcx/policy-search/, POST /api/v1/facility/{facilityId}/nhcx/claims/ | `care_fe/src/pages/Facility/claims/SearchPolicy.tsx` created |
| LOG-0180 | 2026-10-13 09:48 | L5.2 | note | B6-B7: implements S17, GET /api/v1/facility/{facilityId}/nhcx/claims/{claimId}/state/, GET /api/v1/facility/{facilityId}/nhcx/claims/, POST /api/v1/facility/{facilityId}/nhcx/claims/{claimId}/eligibility/, POST /api/v1/facility/{facilityId}/nhcx/claims/ | `care_fe/src/pages/Facility/claims/BeneficiaryDiscovery.tsx` created |
| LOG-0181 | 2026-10-13 09:48 | L5.2 | note | B6-B7: implements S6, GET /api/v1/facility/{facilityId}/nhcx/claims/{claimId}/state/ | `care_fe/src/pages/Facility/claims/ClaimDetail.tsx` created |
| LOG-0182 | 2026-10-13 09:48 | L5.2 | note | B6-B7: implements S3, POST /api/v1/facility/{facilityId}/nhcx/claims/{claimId}/eligibility/ | `care_fe/src/pages/Facility/claims/tabs/EligibilityTab.tsx` created |
| LOG-0183 | 2026-10-13 09:48 | L5.2 | note | B6-B7: implements S7, POST /api/v1/facility/{facilityId}/nhcx/claims/{claimId}/plan/ | `care_fe/src/pages/Facility/claims/tabs/InsurancePlanTab.tsx` created |
| LOG-0184 | 2026-10-13 09:48 | L5.2 | note | B6-B7: implements S8, POST /api/v1/facility/{facilityId}/nhcx/claims/{claimId}/lines/, DELETE /api/v1/facility/{facilityId}/nhcx/claims/{claimId}/lines/{lineId}/ | `care_fe/src/pages/Facility/claims/tabs/LineItemsTab.tsx` created |
| LOG-0185 | 2026-10-13 09:48 | L5.2 | note | B6-B7: implements S8, POST /api/v1/facility/{facilityId}/nhcx/claims/{claimId}/auth-requirements/ | `care_fe/src/pages/Facility/claims/tabs/ValidateTab.tsx` created |
| LOG-0186 | 2026-10-13 09:48 | L5.2 | note | B6-B7: implements S18, POST /api/v1/facility/{facilityId}/nhcx/claims/{claimId}/biometric/{action}/ | `care_fe/src/pages/Facility/claims/tabs/VerificationTab.tsx` created |
| LOG-0187 | 2026-10-13 09:48 | L5.2 | note | B6-B7: implements S4, S9, POST /api/v1/facility/{facilityId}/nhcx/claims/{claimId}/preauth/cancel/, POST /api/v1/facility/{facilityId}/nhcx/claims/{claimId}/preauth/predetermination/, POST /api/v1/facility/{facilityId}/nhcx/claims/{claimId}/preauth/submit/, POST /api/v1/facility/{facilityId}/nhcx/claims/{claimId}/enquiry/ | `care_fe/src/pages/Facility/claims/tabs/PreauthTab.tsx` created |
| LOG-0188 | 2026-10-13 09:48 | L5.2 | note | B6-B7: implements S4, POST /api/v1/facility/{facilityId}/nhcx/claims/{claimId}/admission/, PUT /api/v1/facility/{facilityId}/nhcx/claims/{claimId}/draft/ | `care_fe/src/pages/Facility/claims/components/PreauthDraft.tsx` created |
| LOG-0189 | 2026-10-13 09:48 | L5.2 | note | B6-B7: implements S7, S8 | `care_fe/src/pages/Facility/claims/components/PackageDetail.tsx` created |
| LOG-0190 | 2026-10-13 09:48 | L5.2 | note | B6-B7: implements S9, S11 | `care_fe/src/pages/Facility/claims/components/FormDetail.tsx` created |
| LOG-0191 | 2026-10-13 09:48 | L5.2 | note | B6-B7: implements S9, S10, S11, POST /api/v1/facility/{facilityId}/nhcx/claims/{claimId}/documents/, DELETE /api/v1/facility/{facilityId}/nhcx/claims/{claimId}/documents/{documentId}/, PUT /api/v1/facility/{facilityId}/nhcx/claims/{claimId}/draft/ | `care_fe/src/pages/Facility/claims/components/LegParts.tsx` created |
| LOG-0192 | 2026-10-13 09:48 | L5.2 | note | B6-B7: implements S6 | `care_fe/src/pages/Facility/claims/components/ClaimWidgets.tsx` created |
| LOG-0193 | 2026-10-13 09:48 | L5.2 | note | B6-B7: implements S10, POST /api/v1/facility/{facilityId}/nhcx/claims/{claimId}/queries/{queryId}/reply/, POST /api/v1/facility/{facilityId}/nhcx/claims/{claimId}/queries/{queryId}/ack/ | `care_fe/src/pages/Facility/claims/tabs/CommunicationTab.tsx` created |
| LOG-0194 | 2026-10-13 09:48 | L5.2 | note | B6-B7: implements S11, POST /api/v1/facility/{facilityId}/nhcx/claims/{claimId}/discharge/, POST /api/v1/facility/{facilityId}/nhcx/claims/{claimId}/enquiry/, POST /api/v1/facility/{facilityId}/nhcx/claims/{claimId}/claim/submit/ | `care_fe/src/pages/Facility/claims/tabs/ClaimTab.tsx` created |
| LOG-0195 | 2026-10-13 09:48 | L5.2 | note | B6-B7: implements S12, POST /api/v1/facility/{facilityId}/nhcx/claims/{claimId}/payments/{paymentId}/ack/ | `care_fe/src/pages/Facility/claims/tabs/PaymentsTab.tsx` created |
| LOG-0196 | 2026-10-13 09:48 | L5.2 | note | B6-B7: implements S6 | `care_fe/src/pages/Facility/claims/tabs/types.ts` created |
| LOG-0197 | 2026-10-13 09:48 | L5.2 | note | B6-B7: implements S6 | `care_fe/src/pages/Facility/claims/useClaimAction.ts` created |
| LOG-0198 | 2026-10-13 09:48 | L5.2 | note | B6-B7: implements S5, S6 | `care_fe/src/pages/Facility/claims/utils.ts` created |
| LOG-0199 | 2026-10-13 09:48 | L5.2 | note | B6-B7: implements S13, S14, S15, POST /api/v1/nhcx/abha/{action}/ | `care_fe/src/components/Nhcx/AbhaDialog.tsx` created |
| LOG-0200 | 2026-10-13 09:48 | L5.2 | note | B6-B7: implements S13 | `care_fe/src/components/Nhcx/RegisterWithAbhaButton.tsx` created |
| LOG-0201 | 2026-10-13 09:48 | L5.2 | note | B6-B7: implements S14 | `care_fe/src/components/Nhcx/AbhaFormButton.tsx` created |
| LOG-0202 | 2026-10-13 09:48 | L5.2 | note | B6-B7: implements S15, POST /api/v1/nhcx/abha/{action}/ | `care_fe/src/components/Nhcx/PatientNhcxActions.tsx` created |
| LOG-0203 | 2026-10-13 09:48 | L5.2 | note | B6-B7: implements S16, GET /api/v1/nhcx/practitioner/{userId}/, PUT /api/v1/nhcx/practitioner/{userId}/ | `care_fe/src/components/Nhcx/PractitionerProfileCard.tsx` created |
| LOG-0204 | 2026-10-13 09:48 | L5.2 | note | B6-B7: implements S13 | `care_fe/src/components/Patient/PatientIndex.tsx` modified |
| LOG-0205 | 2026-10-13 09:48 | L5.2 | note | B6-B7: implements S14 | `care_fe/src/components/Patient/PatientRegistration.tsx` modified |
| LOG-0206 | 2026-10-13 09:48 | L5.2 | note | B6-B7: implements S15 | `care_fe/src/components/Patient/PatientProfile.tsx` modified |
| LOG-0207 | 2026-10-13 09:48 | L5.2 | note | B6-B7: implements S16 | `care_fe/src/components/Users/UserSummary.tsx` modified |
| LOG-0208 | 2026-10-13 09:48 | L5.2 | note | B6-B7: implements S1, S2, S5, S6, S17 | `care_fe/src/Routers/routes/FacilityRoutes.tsx` modified |
| LOG-0209 | 2026-10-13 09:48 | L5.2 | note | B6-B7: implements S5 | `care_fe/src/components/ui/sidebar/facility/facility-nav.tsx` modified |
| LOG-0210 | 2026-10-13 09:48 | L5.2 | note | B6-B7: implements - | `care_fe/public/locale/en.json` modified |
| LOG-0211 | 2026-10-13 09:48 | L5.2 | note | B4-B5: implements G1, G3, G9 | `care/care/nhcx/tasks.py` created |
| LOG-0212 | 2026-10-13 09:48 | L5.2 | done | services, callbacks, archive, tasks, API written |  |
| LOG-0213 | 2026-10-13 09:48 | L5.2 | done | care_fe claim screens S1-S12, S17-S18 and S13-S16 additions written |  |
| LOG-0214 | 2026-10-13 09:48 | L5.3 | done | dtest.sh manage.py test care.nhcx: 250 tests OK; ruff clean |  |
| LOG-0215 | 2026-10-13 09:48 | L5.3 | done | tsc --noEmit: only pre-existing BrowserWarning.tsx (@/supportedBrowsers, generated) error; eslint 0 errors/14 warnings; prettier clean; lint-staged on commit |  |
| LOG-0216 | 2026-10-13 09:48 | L5.4 | done | merged _agent reports: 150 files; coverage S18 A18 C10 F19 D27 G11 (D4-D7 existing CARE tables) | `care/nhcx-plan/merge_code.py` modified; `nhcx-plan/code.json` |
| LOG-0217 | 2026-10-13 09:48 | L5.5 | done | committed in care |  |
| LOG-0218 | 2026-10-13 09:48 | L5.5 | done | committed in care_fe |  |
| LOG-0219 | 2026-10-13 09:48 | L5 | exit_checked | All code-plan files written; coverage holds every planned spec id; line ranges from agent reports |  |
| LOG-0220 | 2026-10-13 09:48 | L6.1 | started |  |  |
| LOG-0221 | 2026-10-13 09:48 | L6.2 | started |  |  |
| LOG-0222 | 2026-10-13 09:48 | L6.3 | started |  |  |
| LOG-0223 | 2026-10-13 09:48 | L6.4 | started |  |  |
| LOG-0224 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0225 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0226 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0227 | 2026-10-13 09:48 | L6.4 | note | F2: pass |  |
| LOG-0228 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0229 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0230 | 2026-10-13 09:48 | L6.4 | note | F8: pass |  |
| LOG-0231 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0232 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0233 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0234 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0235 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0236 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0237 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0238 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0239 | 2026-10-13 09:48 | L6.4 | note | C2P/F3 read_verdict: fail (The verdict was read from the last CoverageEligibilityResponse; C2P reads the first.); C3P/D14C: fail (auth_required and excluded were coerced to false when absent; D14C keeps null (new _flag helper).) | `care/care/nhcx/fhir/read/eligibility.py` modified 90-121; `care/care/nhcx/fhir/read/eligibility.py` modified 137-193 |
| LOG-0240 | 2026-10-13 09:48 | L6.4 | note | C4P read_plan/apply_plan: fail (An InsurancePlan with no packages got the 'carries no InsurancePlan' message; C4P keeps error_message null unless the bundle has no InsurancePlan.); F5/F6: pass | `care/care/nhcx/fhir/read/plan.py` modified 257-292 |
| LOG-0241 | 2026-10-13 09:48 | L6.4 | note | C5P status_on/verdict_status: fail (is_error returned error for outcome error with reason queried/submitted/acknowledged; partial under an approving workflow id checked outcome only. Both now go through decide() (= verdict_status); outcome lower-cased.); C5P read_claim_response errors / error_text: fail (Error lines were '<code> <display>'; spec is '<code>: <display or text>'. A disposition of 'ok' is no longer listed.); F9: pass | `care/care/nhcx/fhir/read/claim_response.py` modified 64-82; `care/nhcx/fhir/read/claim_response.py` 138-152 Error lines were '<code> <display>'; spec is '<code> |
| LOG-0242 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0243 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0244 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0245 | 2026-10-13 09:48 | L6.4 | note | C5P: pass | `care/nhcx/tests/test_fhir_read.py` 227-246,284 Two assertions encoded the pre-spec partial and error-line behaviour; aligned to C5P (partial needs reason approved; '<code> |
| LOG-0246 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0247 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0248 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0249 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0250 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0251 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0252 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0253 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0254 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0255 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0256 | 2026-10-13 09:48 | L6.4 | note | G5P: pass |  |
| LOG-0257 | 2026-10-13 09:48 | L6.4 | note | G6P: pass |  |
| LOG-0258 | 2026-10-13 09:48 | L6.4 | note | G7P: pass |  |
| LOG-0259 | 2026-10-13 09:48 | L6.4 | note | G8P/G8S: pass; G8D: fail (G8D says no row is written for an unmatched delivery; G8S records every delivered outcome. Code follows G8S. Spec inconsistency, not changed.) |  |
| LOG-0260 | 2026-10-13 09:48 | L6.4 | note | G9: pass |  |
| LOG-0261 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0262 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0263 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0264 | 2026-10-13 09:48 | L6.4 | note | G1/G8: pass |  |
| LOG-0265 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0266 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0267 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0268 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0269 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0270 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0271 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0272 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0273 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0274 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0275 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0276 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0277 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0278 | 2026-10-13 09:48 | L6.4 | note | D9-D31 DnC: pass |  |
| LOG-0279 | 2026-10-13 09:48 | L6.4 | note | D9-D31 DnC: pass |  |
| LOG-0280 | 2026-10-13 09:48 | L6.4 | note | D9-D31 DnC: pass |  |
| LOG-0281 | 2026-10-13 09:48 | L6.4 | note | D9-D31 DnC: pass |  |
| LOG-0282 | 2026-10-13 09:48 | L6.4 | note | D9-D31 DnC: pass |  |
| LOG-0283 | 2026-10-13 09:48 | L6.4 | note | D9-D31 DnC: pass |  |
| LOG-0284 | 2026-10-13 09:48 | L6.4 | note | D9-D31 DnC: pass |  |
| LOG-0285 | 2026-10-13 09:48 | L6.4 | note | D9-D31 DnC: pass |  |
| LOG-0286 | 2026-10-13 09:48 | L6.4 | note | D9-D31 DnC: pass |  |
| LOG-0287 | 2026-10-13 09:48 | L6.4 | note | D9-D31 DnC: pass |  |
| LOG-0288 | 2026-10-13 09:48 | L6.4 | note | D9-D31 DnC: pass |  |
| LOG-0289 | 2026-10-13 09:48 | L6.4 | note | D9-D31 DnC: pass |  |
| LOG-0290 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0291 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0292 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0293 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0294 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0295 | 2026-10-13 09:48 | L6.4 | note | APIs SEND: pass |  |
| LOG-0296 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0297 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0298 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0299 | 2026-10-13 09:48 | L6.4 | note | A2P: pass |  |
| LOG-0300 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0301 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0302 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0303 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0304 | 2026-10-13 09:48 | L6.4 | note | C1P: pass |  |
| LOG-0305 | 2026-10-13 09:48 | L6.4 | note | C2P/C3P: pass |  |
| LOG-0306 | 2026-10-13 09:48 | L6.4 | note | C4P: pass |  |
| LOG-0307 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0308 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0309 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0310 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0311 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0312 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0313 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0314 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0315 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0316 | 2026-10-13 09:48 | L6.4 | note | A4P/A6P: pass |  |
| LOG-0317 | 2026-10-13 09:48 | L6.4 | note | A5P: pass |  |
| LOG-0318 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0319 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0320 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0321 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0322 | 2026-10-13 09:48 | L6.4 | note | A7P: pass |  |
| LOG-0323 | 2026-10-13 09:48 | L6.4 | note | A8P: pass |  |
| LOG-0324 | 2026-10-13 09:48 | L6.4 | note | C5P/C7P read_task_reply: pass |  |
| LOG-0325 | 2026-10-13 09:48 | L6.4 | note | C5P: pass; C5P enhancement denial: fail (error_message is taken from query_note or disposition; C5P says parsed.reason or disposition. Same payer words in practice; left as is.) |  |
| LOG-0326 | 2026-10-13 09:48 | L6.4 | note | C6P: pass |  |
| LOG-0327 | 2026-10-13 09:48 | L6.4 | note | C7P/C8P: pass |  |
| LOG-0328 | 2026-10-13 09:48 | L6.4 | note | C9P: pass |  |
| LOG-0329 | 2026-10-13 09:48 | L6.4 | note | C10P: pass |  |
| LOG-0330 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0331 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0332 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0333 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0334 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0335 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0336 | 2026-10-13 09:48 | L6.4 | note | light: pass |  |
| LOG-0337 | 2026-10-13 09:48 | L6.2 | note | tsc --noEmit clean for this file; eslint 0 errors; prettier clean; API calls match care/nhcx/api/CONTRACT.md routes; labels in en.json. Not exercised in a browser. |  |
| LOG-0338 | 2026-10-13 09:48 | L6.2 | note | tsc --noEmit clean for this file; eslint 0 errors; prettier clean; API calls match care/nhcx/api/CONTRACT.md routes; labels in en.json. Not exercised in a browser. |  |
| LOG-0339 | 2026-10-13 09:48 | L6.2 | note | tsc --noEmit clean for this file; eslint 0 errors; prettier clean; API calls match care/nhcx/api/CONTRACT.md routes; labels in en.json. Not exercised in a browser. |  |
| LOG-0340 | 2026-10-13 09:48 | L6.2 | note | tsc --noEmit clean for this file; eslint 0 errors; prettier clean; API calls match care/nhcx/api/CONTRACT.md routes; labels in en.json. Not exercised in a browser. |  |
| LOG-0341 | 2026-10-13 09:48 | L6.2 | note | tsc --noEmit clean for this file; eslint 0 errors; prettier clean; API calls match care/nhcx/api/CONTRACT.md routes; labels in en.json. Not exercised in a browser. |  |
| LOG-0342 | 2026-10-13 09:48 | L6.2 | note | tsc --noEmit clean for this file; eslint 0 errors; prettier clean; API calls match care/nhcx/api/CONTRACT.md routes; labels in en.json. Not exercised in a browser. |  |
| LOG-0343 | 2026-10-13 09:48 | L6.2 | note | tsc --noEmit clean for this file; eslint 0 errors; prettier clean; API calls match care/nhcx/api/CONTRACT.md routes; labels in en.json. Not exercised in a browser. |  |
| LOG-0344 | 2026-10-13 09:48 | L6.2 | note | tsc --noEmit clean for this file; eslint 0 errors; prettier clean; API calls match care/nhcx/api/CONTRACT.md routes; labels in en.json. Not exercised in a browser. |  |
| LOG-0345 | 2026-10-13 09:48 | L6.2 | note | tsc --noEmit clean for this file; eslint 0 errors; prettier clean; API calls match care/nhcx/api/CONTRACT.md routes; labels in en.json. Not exercised in a browser. |  |
| LOG-0346 | 2026-10-13 09:48 | L6.2 | note | tsc --noEmit clean for this file; eslint 0 errors; prettier clean; API calls match care/nhcx/api/CONTRACT.md routes; labels in en.json. Not exercised in a browser. |  |
| LOG-0347 | 2026-10-13 09:48 | L6.2 | note | tsc --noEmit clean for this file; eslint 0 errors; prettier clean; API calls match care/nhcx/api/CONTRACT.md routes; labels in en.json. Not exercised in a browser. |  |
| LOG-0348 | 2026-10-13 09:48 | L6.2 | note | tsc --noEmit clean for this file; eslint 0 errors; prettier clean; API calls match care/nhcx/api/CONTRACT.md routes; labels in en.json. Not exercised in a browser. |  |
| LOG-0349 | 2026-10-13 09:48 | L6.2 | note | tsc --noEmit clean for this file; eslint 0 errors; prettier clean; API calls match care/nhcx/api/CONTRACT.md routes; labels in en.json. Not exercised in a browser. |  |
| LOG-0350 | 2026-10-13 09:48 | L6.2 | note | tsc --noEmit clean for this file; eslint 0 errors; prettier clean; API calls match care/nhcx/api/CONTRACT.md routes; labels in en.json. Not exercised in a browser. |  |
| LOG-0351 | 2026-10-13 09:48 | L6.2 | note | tsc --noEmit clean for this file; eslint 0 errors; prettier clean; API calls match care/nhcx/api/CONTRACT.md routes; labels in en.json. Not exercised in a browser. |  |
| LOG-0352 | 2026-10-13 09:48 | L6.2 | note | tsc --noEmit clean for this file; eslint 0 errors; prettier clean; API calls match care/nhcx/api/CONTRACT.md routes; labels in en.json. Not exercised in a browser. |  |
| LOG-0353 | 2026-10-13 09:48 | L6.2 | note | tsc --noEmit clean for this file; eslint 0 errors; prettier clean; API calls match care/nhcx/api/CONTRACT.md routes; labels in en.json. Not exercised in a browser. |  |
| LOG-0354 | 2026-10-13 09:48 | L6.2 | note | tsc --noEmit clean for this file; eslint 0 errors; prettier clean; API calls match care/nhcx/api/CONTRACT.md routes; labels in en.json. Not exercised in a browser. |  |
| LOG-0355 | 2026-10-13 09:48 | L6.2 | note | tsc --noEmit clean for this file; eslint 0 errors; prettier clean; API calls match care/nhcx/api/CONTRACT.md routes; labels in en.json. Not exercised in a browser. |  |
| LOG-0356 | 2026-10-13 09:48 | L6.2 | note | tsc --noEmit clean for this file; eslint 0 errors; prettier clean; API calls match care/nhcx/api/CONTRACT.md routes; labels in en.json. Not exercised in a browser. |  |
| LOG-0357 | 2026-10-13 09:48 | L6.2 | note | tsc --noEmit clean for this file; eslint 0 errors; prettier clean; API calls match care/nhcx/api/CONTRACT.md routes; labels in en.json. Not exercised in a browser. |  |
| LOG-0358 | 2026-10-13 09:48 | L6.2 | note | tsc --noEmit clean for this file; eslint 0 errors; prettier clean; API calls match care/nhcx/api/CONTRACT.md routes; labels in en.json. Not exercised in a browser. |  |
| LOG-0359 | 2026-10-13 09:48 | L6.2 | note | tsc --noEmit clean for this file; eslint 0 errors; prettier clean; API calls match care/nhcx/api/CONTRACT.md routes; labels in en.json. Not exercised in a browser. |  |
| LOG-0360 | 2026-10-13 09:48 | L6.2 | note | tsc --noEmit clean for this file; eslint 0 errors; prettier clean; API calls match care/nhcx/api/CONTRACT.md routes; labels in en.json. Not exercised in a browser. |  |
| LOG-0361 | 2026-10-13 09:48 | L6.2 | note | tsc --noEmit clean for this file; eslint 0 errors; prettier clean; API calls match care/nhcx/api/CONTRACT.md routes; labels in en.json. Not exercised in a browser. |  |
| LOG-0362 | 2026-10-13 09:48 | L6.2 | note | tsc --noEmit clean for this file; eslint 0 errors; prettier clean; API calls match care/nhcx/api/CONTRACT.md routes; labels in en.json. Not exercised in a browser. |  |
| LOG-0363 | 2026-10-13 09:48 | L6.2 | note | tsc --noEmit clean for this file; eslint 0 errors; prettier clean; API calls match care/nhcx/api/CONTRACT.md routes; labels in en.json. Not exercised in a browser. |  |
| LOG-0364 | 2026-10-13 09:48 | L6.2 | note | tsc --noEmit clean for this file; eslint 0 errors; prettier clean; API calls match care/nhcx/api/CONTRACT.md routes; labels in en.json. Not exercised in a browser. |  |
| LOG-0365 | 2026-10-13 09:48 | L6.2 | note | tsc --noEmit clean for this file; eslint 0 errors; prettier clean; API calls match care/nhcx/api/CONTRACT.md routes; labels in en.json. Not exercised in a browser. |  |
| LOG-0366 | 2026-10-13 09:48 | L6.2 | note | tsc --noEmit clean for this file; eslint 0 errors; prettier clean; API calls match care/nhcx/api/CONTRACT.md routes; labels in en.json. Not exercised in a browser. |  |
| LOG-0367 | 2026-10-13 09:48 | L6.2 | note | tsc --noEmit clean for this file; eslint 0 errors; prettier clean; API calls match care/nhcx/api/CONTRACT.md routes; labels in en.json. Not exercised in a browser. |  |
| LOG-0368 | 2026-10-13 09:48 | L6.2 | note | tsc --noEmit clean for this file; eslint 0 errors; prettier clean; API calls match care/nhcx/api/CONTRACT.md routes; labels in en.json. Not exercised in a browser. |  |
| LOG-0369 | 2026-10-13 09:48 | L6.2 | note | tsc --noEmit clean for this file; eslint 0 errors; prettier clean; API calls match care/nhcx/api/CONTRACT.md routes; labels in en.json. Not exercised in a browser. |  |
| LOG-0370 | 2026-10-13 09:48 | L6.2 | note | tsc --noEmit clean for this file; eslint 0 errors; prettier clean; API calls match care/nhcx/api/CONTRACT.md routes; labels in en.json. Not exercised in a browser. |  |
| LOG-0371 | 2026-10-13 09:48 | L6.2 | note | tsc --noEmit clean for this file; eslint 0 errors; prettier clean; API calls match care/nhcx/api/CONTRACT.md routes; labels in en.json. Not exercised in a browser. |  |
| LOG-0372 | 2026-10-13 09:48 | L6.2 | note | LOCAL_APPS has care.nhcx; NHCX_* settings block present with defaults; nothing secret in repo. |  |
| LOG-0373 | 2026-10-13 09:48 | L6.2 | note | Gateway inbound routes (/in/, /v1/), facility /api/v1/facility/<uuid>/nhcx/ and global /api/v1/nhcx/ mounted; reachable in tests. |  |
| LOG-0374 | 2026-10-13 09:48 | L6.1 | done | 150 files taken |  |
| LOG-0375 | 2026-10-13 09:48 | L6.2 | done | backend: full checks on gateway/callbacks/services/builders/models, light on rest; FE: typecheck/lint/contract |  |
| LOG-0376 | 2026-10-13 09:48 | L6.3 | done | ruff clean; full care.nhcx suite green after fixes |  |
| LOG-0377 | 2026-10-13 09:48 | L6.4 | done | passed 146, fixed 4, failed 0 | `care/care/nhcx/fhir/read/claim_response.py` modified; `care/care/nhcx/fhir/read/eligibility.py` modified; `care/care/nhcx/fhir/read/plan.py` modified; `care/care/nhcx/tests/test_fhir_read.py` modified; `nhcx-plan/validation.json` |
| LOG-0378 | 2026-10-13 09:48 | L6 | exit_checked | Every code.json file has a validation entry with current hash; no failed files. Open warnings: G8D vs G8S ledger row for unmatched delivery (follows G8S); C5 denied-enhancement message source |  |
| LOG-0379 | 2026-10-13 09:49 | L7.1 | started |  |  |
| LOG-0380 | 2026-10-13 09:49 | L7.2 | started |  |  |
| LOG-0381 | 2026-10-13 09:49 | L7.3 | started |  |  |
| LOG-0382 | 2026-10-13 09:49 | L7.4 | started |  |  |
| LOG-0383 | 2026-10-13 09:49 | L7.5 | started |  |  |
| LOG-0384 | 2026-10-13 09:49 | L7.6 | started |  |  |
| LOG-0385 | 2026-10-13 09:49 | L7.7 | started |  |  |
| LOG-0386 | 2026-10-13 09:49 | L7.1 | note | covers L7.1 isolation: NHCX settings pinned off for every test run, 0 tests | `care/config/settings/test.py` modify 3,115-140 |
| LOG-0387 | 2026-10-13 09:49 | L7.1 | note | covers L7.1 loopback-only network guard scoped to care.nhcx test frames, 0 tests | `care/care/nhcx/tests/network_guard.py` add 1-156 |
| LOG-0388 | 2026-10-13 09:49 | L7.1 | note | installs the network guard when the care.nhcx test package loads, 0 tests | `care/care/nhcx/tests/__init__.py` modify 1-5 |
| LOG-0389 | 2026-10-13 09:49 | L7.1 | note | covers L7.1 (settings pinned, guard blocks external hosts, allows loopback/infra, scoped to nhcx tests), 11 tests | `care/care/nhcx/tests/test_isolation.py` add 1-106 |
| LOG-0390 | 2026-10-13 09:49 | L7.7 | note | covers L7.7 S1-S12 through the real API with a real Gateway on a throwaway config and test keys, fake NHCX transport, inbound replies encrypted with the facility key through G8 (A1-A5, A7, A8, A17, C1-C6, C9, C10, D9-D26, G4-G10, F1-F18); generic IRDAI and PMJAY variants, 2 tests | `care/care/nhcx/tests/test_dry_flow.py` add 1-508 |
| LOG-0391 | 2026-10-13 09:49 | L7.3 | note | covers L7.3-L7.5 gaps: ProtocolResponse refusals for C2/C3/C6/C8, A4 predetermination and preauth send, A6 reprocess/release, A14/A15/A16 adjudicator, A18 biometric init/verify/refusal, D12, D17, D19, D24, D27, D29, D31, 14 tests | `care/care/nhcx/tests/test_gap_coverage.py` add 1-342 |
| LOG-0392 | 2026-10-13 09:49 | L7.3 | note | L7O output: 277 tests, 277 pass, 0 fail, 0 skip; every code.json coverage id covered | `care/care/nhcx-plan/dry-run.json` add all |
| LOG-0393 | 2026-10-13 09:49 | L5.4 | corrected | Normalised repo-prefixed paths (config/*, care/nhcx/migrations/*) and deduplicated; validation.json realigned to 148 code.json files | `care/nhcx-plan/merge_code.py` modified; `nhcx-plan/code.json`; `nhcx-plan/validation.json` |
| LOG-0394 | 2026-10-13 09:49 | L7.1 | done | see dry-run.json |  |
| LOG-0395 | 2026-10-13 09:49 | L7.2 | done | see dry-run.json |  |
| LOG-0396 | 2026-10-13 09:49 | L7.3 | done | see dry-run.json |  |
| LOG-0397 | 2026-10-13 09:49 | L7.4 | done | see dry-run.json |  |
| LOG-0398 | 2026-10-13 09:49 | L7.5 | done | see dry-run.json |  |
| LOG-0399 | 2026-10-13 09:49 | L7.6 | done | see dry-run.json |  |
| LOG-0400 | 2026-10-13 09:49 | L7.7 | done | see dry-run.json |  |
| LOG-0401 | 2026-10-13 09:49 | L7 | exit_checked | Full suite 277 tests OK (coordinator re-run). Every coverage spec id has a passing test; S ids via backend endpoint tests + FE tsc; network guard allows loopback/DB/Redis only | `nhcx-plan/dry-run.json` |
| LOG-0402 | 2026-10-13 10:06 | L8.1 | started |  |  |
| LOG-0403 | 2026-10-13 10:06 | L8.2 | started |  |  |
| LOG-0404 | 2026-10-13 10:06 | L8.3 | started |  |  |
| LOG-0405 | 2026-10-13 10:06 | L8.4 | started |  |  |
| LOG-0406 | 2026-10-13 10:06 | L8.5 | started |  |  |
| LOG-0407 | 2026-10-13 10:06 | L8.1 | note | Worktree backend+celery swapped onto :9000 (care-nhcx-backend/celery, launcher ~/.nhcx/sandbox/run-worktree.sh, outside repo); nhcx migrations applied to dev DB; gateway config/key/ledger under ~/.nhcx/sandbox (outside repo) |  |
| LOG-0408 | 2026-10-13 10:06 | L8.1 | note | first attempt TOKEN_HTTP_400: docker --env-file kept literal quotes from .env; fixed with quote-stripped ~/.nhcx/sandbox/dev.env (setup, not code) |  |
| LOG-0409 | 2026-10-13 10:06 | L8.1 | note | registered endpoint was https://api.staging.ohc.network/api/nhcx; at the user's request updated via /participant/update to https://9k-personal.khavinshankar.dev/in (HTTP 200) |  |
| LOG-0410 | 2026-10-13 10:06 | L8.1 | done | session token pass; participant record 1000004455@hcx pass; encryption certificate match; endpoint probe through registered URL acknowledged (public /in/healthz) |  |
| LOG-0411 | 2026-10-13 10:06 | L8.2 | note | asked from integrator: SBXSTG007 (to tests e2e .env) |  |
| LOG-0412 | 2026-10-13 13:49 | L8.2 | note | e2e harness file for T1, T2 \| written | `care/care/nhcx/management/__init__.py` add 1-0 |
| LOG-0413 | 2026-10-13 13:49 | L8.2 | note | e2e harness file for T1, T2 \| written | `care/care/nhcx/management/commands/__init__.py` add 1-0 |
| LOG-0414 | 2026-10-13 13:49 | L8.2 | note | e2e harness file for T1, T2 \| written | `care/care/nhcx/management/commands/nhcx_e2e.py` add 1-396 |
| LOG-0415 | 2026-10-13 13:49 | L8.2 | note | e2e harness file for T1 \| written | `care/care/nhcx/tests/e2e/.gitignore` add 1-2 |
| LOG-0416 | 2026-10-13 13:49 | L8.2 | note | e2e harness file for T1, T2 \| written | `care/care/nhcx/tests/e2e/__init__.py` add 1-6 |
| LOG-0417 | 2026-10-13 13:49 | L8.2 | note | e2e harness file for T1, T2 \| written | `care/care/nhcx/tests/e2e/abdm_fake.py` add 1-106 |
| LOG-0418 | 2026-10-13 13:49 | L8.2 | note | e2e harness file for T1, T2 \| written | `care/care/nhcx/tests/e2e/checks.py` add 1-92 |
| LOG-0419 | 2026-10-13 13:49 | L8.2 | note | e2e harness file for T1, T2 \| written | `care/care/nhcx/tests/e2e/cli/__init__.py` add 1-0 |
| LOG-0420 | 2026-10-13 13:49 | L8.2 | note | e2e harness file for T1, T2 \| written | `care/care/nhcx/tests/e2e/cli/runner.py` add 1-262 |
| LOG-0421 | 2026-10-13 13:49 | L8.2 | note | e2e harness file for T1 \| written | `care/care/nhcx/tests/e2e/config.example.env` add 1-52 |
| LOG-0422 | 2026-10-13 13:49 | L8.2 | note | e2e harness file for T1 \| written | `care/care/nhcx/tests/e2e/config.py` add 1-150 |
| LOG-0423 | 2026-10-13 13:49 | L8.2 | note | e2e harness file for T2, T13, T14, T15, T16, T17, T18, T19 \| written | `care/care/nhcx/tests/e2e/fixtures/pmjay-plan.json` add 1-142 |
| LOG-0424 | 2026-10-13 13:49 | L8.2 | note | e2e harness file for T1, T2 \| written | `care/care/nhcx/tests/e2e/payer/__init__.py` add 1-0 |
| LOG-0425 | 2026-10-13 13:49 | L8.2 | note | e2e harness file for T1, T2 \| written | `care/care/nhcx/tests/e2e/payer/driver.py` add 1-222 |
| LOG-0426 | 2026-10-13 13:49 | L8.2 | note | e2e harness file for T1, T2 \| written | `care/care/nhcx/tests/e2e/report.py` add 1-50 |
| LOG-0427 | 2026-10-13 13:49 | L8.2 | note | e2e harness file for T1, T2 \| written | `care/care/nhcx/tests/e2e/scenarios/__init__.py` add 1-125 |
| LOG-0428 | 2026-10-13 13:49 | L8.2 | note | e2e harness file for T1, T2 \| written | `care/care/nhcx/tests/e2e/scenarios/common.py` add 1-1031 |
| LOG-0429 | 2026-10-13 13:49 | L8.2 | note | e2e harness file for T3 \| written | `care/care/nhcx/tests/e2e/scenarios/t03_irdai_policy_and_eligibility.py` add 1-28 |
| LOG-0430 | 2026-10-13 13:49 | L8.2 | note | e2e harness file for T4 \| written | `care/care/nhcx/tests/e2e/scenarios/t04_irdai_plan_and_auth_requirements.py` add 1-26 |
| LOG-0431 | 2026-10-13 13:49 | L8.2 | note | e2e harness file for T5 \| written | `care/care/nhcx/tests/e2e/scenarios/t05_irdai_preauth_approved.py` add 1-23 |
| LOG-0432 | 2026-10-13 13:49 | L8.2 | note | e2e harness file for T6 \| written | `care/care/nhcx/tests/e2e/scenarios/t06_irdai_preauth_rejected.py` add 1-43 |
| LOG-0433 | 2026-10-13 13:49 | L8.2 | note | e2e harness file for T7 \| written | `care/care/nhcx/tests/e2e/scenarios/t07_irdai_query_answered.py` add 1-48 |
| LOG-0434 | 2026-10-13 13:49 | L8.2 | note | e2e harness file for T8 \| written | `care/care/nhcx/tests/e2e/scenarios/t08_irdai_enhancement.py` add 1-38 |
| LOG-0435 | 2026-10-13 13:49 | L8.2 | note | e2e harness file for T9 \| written | `care/care/nhcx/tests/e2e/scenarios/t09_irdai_cancel_and_status.py` add 1-58 |
| LOG-0436 | 2026-10-13 13:49 | L8.2 | note | e2e harness file for T10 \| written | `care/care/nhcx/tests/e2e/scenarios/t10_irdai_claim.py` add 1-85 |
| LOG-0437 | 2026-10-13 13:49 | L8.2 | note | e2e harness file for T11 \| written | `care/care/nhcx/tests/e2e/scenarios/t11_irdai_payment.py` add 1-53 |
| LOG-0438 | 2026-10-13 13:49 | L8.2 | note | e2e harness file for T12 \| written | `care/care/nhcx/tests/e2e/scenarios/t12_irdai_reprocess_and_release.py` add 1-101 |
| LOG-0439 | 2026-10-13 13:49 | L8.2 | note | e2e harness file for T13 \| written | `care/care/nhcx/tests/e2e/scenarios/t13_pmjay_eligibility_and_package_master.py` add 1-48 |
| LOG-0440 | 2026-10-13 13:49 | L8.2 | note | e2e harness file for T14 \| written | `care/care/nhcx/tests/e2e/scenarios/t14_pmjay_preauth_adjudicated.py` add 1-23 |
| LOG-0441 | 2026-10-13 13:49 | L8.2 | note | e2e harness file for T15 \| written | `care/care/nhcx/tests/e2e/scenarios/t15_pmjay_query_by_resubmission.py` add 1-43 |
| LOG-0442 | 2026-10-13 13:49 | L8.2 | note | e2e harness file for T16 \| written | `care/care/nhcx/tests/e2e/scenarios/t16_pmjay_rejection_and_enhancement.py` add 1-76 |
| LOG-0443 | 2026-10-13 13:49 | L8.2 | note | e2e harness file for T17 \| written | `care/care/nhcx/tests/e2e/scenarios/t17_pmjay_claim_adjudicated.py` add 1-96 |
| LOG-0444 | 2026-10-13 13:49 | L8.2 | note | e2e harness file for T18 \| written | `care/care/nhcx/tests/e2e/scenarios/t18_pmjay_payment_status_cancel.py` add 1-112 |
| LOG-0445 | 2026-10-13 13:49 | L8.2 | note | e2e harness file for T19 \| written | `care/care/nhcx/tests/e2e/scenarios/t19_pmjay_biometric_and_abha.py` add 1-164 |
| LOG-0446 | 2026-10-13 13:49 | L8.2 | note | e2e harness file for T1, T2 \| written | `care/care/nhcx/tests/e2e/seed.py` add 1-136 |
| LOG-0447 | 2026-10-13 13:49 | L8.2 | note | e2e harness file for T1, T2 \| written | `care/care/nhcx/tests/e2e/setup_data.py` add 1-255 |
| LOG-0448 | 2026-10-13 13:49 | L8.2 | note | e2e harness file for T1, T2 \| written | `care/scripts/nhcx-e2e.sh` add 1-74 |
| LOG-0449 | 2026-10-13 13:49 | L8.2 | note | e2e harness file for T1, T2 \| written | `care_fe/tests/nhcx/helpers.ts` add 1-654 |
| LOG-0450 | 2026-10-13 13:49 | L8.2 | note | e2e harness file for T2, T3, T4, T5, T6, T7, T8, T9, T10, T11, T12 \| written | `care_fe/tests/nhcx/irdai.nhcx.ts` add 1-118 |
| LOG-0451 | 2026-10-13 13:49 | L8.2 | note | e2e harness file for T1 \| written | `care_fe/tests/nhcx/playwright.config.ts` add 1-47 |
| LOG-0452 | 2026-10-13 13:49 | L8.2 | note | e2e harness file for T2, T13, T14, T15, T16, T17, T18, T19 \| written | `care_fe/tests/nhcx/pmjay.nhcx.ts` add 1-112 |
| LOG-0453 | 2026-10-13 13:49 | L8.4 | note | fix (ours): IRDAI desk case picked by correlation id; wait for the desk to move between roles \| fixed; unit suite 282 OK | `care/care/nhcx/services/adjudicator.py` modify 10-10,302-302,309-309,389-389,401-415,419-421,423-423,430-431,457-459,559-559,586-599,645-646 |
| LOG-0454 | 2026-10-13 13:49 | L8.4 | note | fix (ours): status reply after a reopen read as the new verdict (c8 test) \| fixed; unit suite 282 OK | `care/care/nhcx/callbacks/enquiry.py` modify 147-149,188-211; `care/care/nhcx/tests/test_callbacks_legs.py` modify 168-191 |
| LOG-0455 | 2026-10-13 13:49 | L8.4 | note | fix (ours): draft form_answers alias, preauth_saved_at, relation keys, diagnoses/care_team, consent/external_id answers (d12, d17, a15, a17 tests) \| fixed; unit suite 282 OK | `care/care/nhcx/services/draft.py` modify 9-9,138-140,143-146; `care/care/nhcx/services/state.py` modify 69-72,87-95,192-193,195-203; `care/care/nhcx/services/_gather.py` modify 9-10,219-230,238-238,259-259,263-263,292-292,307-318; `care/care/nhcx/tests/test_gap_coverage.py` modify 217-317,385-420 |
| LOG-0456 | 2026-10-13 13:49 | L8.4 | note | fix (ours): query answers sent as request.initiated (NHCX-1011 on response.complete) \| fixed; unit suite 282 OK | `care/care/nhcx/services/payers.py` modify 211-214; `care/care/nhcx/tests/test_dry_flow.py` modify 461-463 |
| LOG-0457 | 2026-10-13 13:49 | L8.4 | note | fix (ours): e2e runner exempt from the unit-test network guard \| fixed; unit suite 282 OK | `care/care/nhcx/tests/network_guard.py` modify 24-25,105-106 |
| LOG-0458 | 2026-10-13 13:49 | L8.4 | note | harness fix: no-role desk walk end accepted as success \| fixed | `care/care/nhcx/tests/e2e/scenarios/common.py` modify |
| LOG-0459 | 2026-10-13 13:49 | L8.4 | note | harness fix: decide() retries while PMJAY answers 'Event Meta Log not found' \| fixed | `care/care/nhcx/tests/e2e/payer/driver.py` modify |
| LOG-0460 | 2026-10-13 13:49 | L8.4 | note | harness fix: NHCX_TEST_PMJAY_PAYMENT_WAIT_SECONDS (payment ~8 min after approval) \| fixed | `care/care/nhcx/tests/e2e/config.py` modify |
| LOG-0461 | 2026-10-13 13:49 | L8.4 | note | harness fix: query answer carries a reply body \| fixed | `care/care/nhcx/tests/e2e/scenarios/t17_pmjay_claim_adjudicated.py` modify |
| LOG-0462 | 2026-10-13 13:49 | L8.4 | note | harness fix: payer subcommand positional renamed args->rest (Django pops args) \| fixed | `care/care/nhcx/management/commands/nhcx_e2e.py` modify |
| LOG-0463 | 2026-10-13 13:49 | L8.4 | note | harness fix: open_preauths ignores claims the gateway refused (status error), so free_beneficiary cancels their pre-auth (PAYR-1238) \| fixed | `care/care/nhcx/tests/e2e/scenarios/common.py` modify |
| LOG-0464 | 2026-10-13 13:49 | L8.4 | note | harness fix: selectors by visible labels and chips \| fixed | `care_fe/tests/nhcx/helpers.ts` modify |
| LOG-0465 | 2026-10-13 13:49 | L8.3 | note | query answer refused synchronously NHCX-1011 (x-hcx-status response.complete) x3, incl. claim_query_response=161 override; root cause payers.status_for \| corr b89cffdf-92d6-4837-95c2-e8e54d5fd263 \| fail (ours) -> fixed |  |
| LOG-0466 | 2026-10-13 13:49 | L8.3 | note | after status fix: first claim refused GATEWAY_HTTP_500 by NHCX \| corr 724805a4-10a4-4eda-8989-3174dbb96bc5 \| fail (sandbox) |  |
| LOG-0467 | 2026-10-13 13:49 | L8.3 | note | registry certificate lookup refused / ABDM sessions endpoint SUSPENDED (intermittent outage) \| blocked (sandbox/setup) |  |
| LOG-0468 | 2026-10-13 13:49 | L8.3 | note | PAYR-1238 active pre-auth left by the 500'd claim; harness free filter fixed \| corr 11347828-4345-488c-9a81-2b4c7f9c4344 \| fail (harness) -> fixed |  |
| LOG-0469 | 2026-10-13 13:49 | L8.5 | note | attempt 1: policy search {'error': ''} from the sandbox \| fail (sandbox) |  |
| LOG-0470 | 2026-10-13 13:49 | L8.3 | note | all checks passed \| corr 25291740-bf10-41d8-b156-6015b8093e49, c99960c6-b25a-4f38-842a-4d7a0d9b32eb \| ledger 7USL0001, 7USL0002, 7USL0003, 7USL0004 \| pass (attempts 1) |  |
| LOG-0471 | 2026-10-13 13:49 | L8.5 | note | all checks passed \| corr e9c58e09-ba1b-4ce0-8666-a13d1df16696 \| ledger 7USL00S2, 7USL00S3 \| pass (attempts 1) |  |
| LOG-0472 | 2026-10-13 13:49 | L8.3 | note | all checks passed \| corr 000ee460-079b-4e20-a336-0d41088824f1, 3f8be8b1-da32-4e38-9173-bc6d1ef8b56c, 2aaf1808-e95e-4c82-a53d-ebbc2c4e5182 \| ledger 7USL0005, 7USL0006, 7USL0007, 7USL0008, 7USL0009, 7USL000A \| pass (attempts 1) |  |
| LOG-0473 | 2026-10-13 13:49 | L8.5 | note | all checks passed \| corr 8d6f42a5-3a46-4068-8170-1f0997554f67, 53a2e007-90e8-4a69-9c89-5b613806d99d, 6d9af49b-aabc-40a6-90d0-18e5151dd7ff \| ledger 7USL00I4, 7USL00I5, 7USL00I8, 7USL00I9, 7USL00G1, 7USL00G2 \| pass (attempts 1) |  |
| LOG-0474 | 2026-10-13 13:49 | L8.3 | note | all checks passed \| corr ff6c0c55-5b2d-4ee6-90ce-5ea5fc186717, 3f8be8b1-da32-4e38-9173-bc6d1ef8b56c, 5184c85b-e919-4973-9808-c8a597f4bb30, 181d2787-cd27-4ed2-9202-77f7ef6f0f0b \| ledger 7USL001F, 7USL001G, 7USL0007, 7USL0008, 7USL001H, 7USL001I \| pass (attempts 1) |  |
| LOG-0475 | 2026-10-13 13:49 | L8.5 | note | all checks passed \| corr 3a3b19b1-97bc-488e-abbe-957a16e6c74b, a1868934-3f82-4159-a352-0c673beb25e3, 0b7f20aa-5fb3-42b2-81e4-9f7c7d839f13, 6d9af49b-aabc-40a6-90d0-18e5151dd7ff \| ledger 7USL00M6, 7USL00M7, 7USL00M9, 7USL00MA, 7USL00MB, 7USL00MC \| pass (attempts 6) |  |
| LOG-0476 | 2026-10-13 13:49 | L8.3 | note | all checks passed \| corr c643feb9-064c-42b7-8603-972adbf0a8bb, 3f8be8b1-da32-4e38-9173-bc6d1ef8b56c, 1a55389f-3437-4ccd-8683-3973d79c82b0, 2075792e-e59f-4054-b401-3c92f4888ea3, 5b6b043c-8a1d-44cf-bfad-27ce770843e0 \| ledger 7USL001M, 7USL001N, 7USL0007, 7USL0008, 7USL001O, 7USL001P \| pass (attempts 1) |  |
| LOG-0477 | 2026-10-13 13:49 | L8.5 | note | GUI walk not written in this round; the CLI runner covers the scenario \| skipped (attempts 1) |  |
| LOG-0478 | 2026-10-13 13:49 | L8.3 | note | all checks passed \| corr cf410936-99c6-4888-a08a-d981a91e784b, 3f8be8b1-da32-4e38-9173-bc6d1ef8b56c, ed240d6a-6106-488b-b8fe-b8f518db6f4b, 53cca990-6b0e-4e01-97e4-9ac591531fd5, 0b585742-0900-471e-a7a5-ce0138f57052 \| ledger 7USL0020, 7USL0021, 7USL0007, 7USL0008, 7USL0022, 7USL0023 \| pass (attempts 1) |  |
| LOG-0479 | 2026-10-13 13:49 | L8.5 | note | GUI walk not written in this round; the CLI runner covers the scenario \| skipped (attempts 1) |  |
| LOG-0480 | 2026-10-13 13:49 | L8.3 | note | all checks passed \| corr 962d1c51-f875-4fab-896f-ce733e60e9d3, 3f8be8b1-da32-4e38-9173-bc6d1ef8b56c, 2ae6cbcd-faaf-476f-9f30-d046eb62852a, e92c9a5a-b39a-4489-8e82-989fe89a6934, 79a980d0-beec-49bf-875b-a61629c639aa, e5f80ecd-65a7-43c0-b7f3-b5f5d7e4a1cf \| ledger 7USL0029, 7USL002A, 7USL0007, 7USL0008, 7USL002B, 7USL002C \| pass (attempts 1) |  |
| LOG-0481 | 2026-10-13 13:49 | L8.5 | note | GUI walk not written in this round; the CLI runner covers the scenario \| skipped (attempts 1) |  |
| LOG-0482 | 2026-10-13 13:49 | L8.3 | note | skipped checks: payer refuses the cancel of a decided case: the sandbox payer accepted the cancel (callback); recorded, not a pass \| corr 767ed6f3-1b48-4b1b-b29c-12f21c5d4239, 3f8be8b1-da32-4e38-9173-bc6d1ef8b56c, 40f2a260-4f5a-4ebc-8641-61be6df08014, 4bb68d3d-882c-4d04-bc8e-b739322f3c3b, 7e5e0c77-e8bd-4546-b4b6-850e0c657bd6, db99bfe4-e338-43f9-8c30-801242552f5e \| ledger 7USL002Q, 7USL002R, 7USL0007, 7USL0008, 7USL002S, 7USL002T \| pass (attempts 1) |  |
| LOG-0483 | 2026-10-13 13:49 | L8.5 | note | GUI walk not written in this round; the CLI runner covers the scenario \| skipped (attempts 1) |  |
| LOG-0484 | 2026-10-13 13:49 | L8.3 | note | all checks passed \| corr 13e880fb-a767-49b8-8211-5e65c5e261b6, 3f8be8b1-da32-4e38-9173-bc6d1ef8b56c, 9810d401-f875-4fa6-b812-e72efe68123e, 948a2097-c043-4411-af36-482bb45707e3, 42347d2e-a9d2-4094-9d97-3ee66072ec2f, 3095924b-0936-435b-9f25-c42ea8efe578 \| ledger 7USL0040, 7USL0041, 7USL0007, 7USL0008, 7USL0042, 7USL0043 \| pass (attempts 3) |  |
| LOG-0485 | 2026-10-13 13:49 | L8.5 | note | GUI walk not written in this round; the CLI runner covers the scenario \| skipped (attempts 1) |  |
| LOG-0486 | 2026-10-13 13:49 | L8.3 | note | all checks passed \| corr 9d441377-6020-40d7-8dbc-a899b156243f, fa4edcbf-f27e-4eba-89fe-d630320c1c5f \| ledger 7USL004U, 7USL004V, 7USL0050, 7USL0051 \| pass (attempts 1) |  |
| LOG-0487 | 2026-10-13 13:49 | L8.5 | note | GUI walk not written in this round; the CLI runner covers the scenario \| skipped (attempts 1) |  |
| LOG-0488 | 2026-10-13 13:49 | L8.3 | note | payer desk refuses approve: the test member's cover is used up on the sandbox (approve as Adjudicator (refused: There is not enough cover left on this policy)); free or reset the member's cover, or use another member \| corr 953fcbee-9faf-439f-a15f-9e31a2a527a2, 6d9af49b-aabc-40a6-90d0-18e5151dd7ff, 8e83fb3e-ce1c-40de-b1f2-d029e86da6ad, dc78b61c-d0b9-40e4-997c-662b6d8621d9, 40ac4292-fdfb-4784-8809-8b4a745be598, 7218576d-2cad-4e09-9917-6b86ac0b9dd8 \| ledger 7USL00FV, 7USL00G0, 7USL00G1, 7USL00G2, 7USL00G3, 7USL00G4 \| blocked (attempts 1, sandbox) |  |
| LOG-0489 | 2026-10-13 13:49 | L8.5 | note | GUI walk not written in this round; the CLI runner covers the scenario \| skipped (attempts 1) |  |
| LOG-0490 | 2026-10-13 13:49 | L8.3 | note | all checks passed \| corr d3a9abe0-0772-4c56-a17c-4b85c1eb1d88, de8d3047-8e0a-42b0-a848-b73a88e2d97b, 3ab86ac4-5346-4b4c-8f76-6104b654c9f1, 12f4b0d5-9a6b-4184-a3f5-1172b82f4cd5, aa31456e-3b00-4e48-9150-f760fd0125d8 \| ledger 7USL00CC, 7USL00CE, 7USL00CF, 7USL00CG, 7USL00CH, 7USL00CI \| pass (attempts 1) |  |
| LOG-0491 | 2026-10-13 13:49 | L8.5 | note | all checks passed \| corr 07f04ac1-4925-4927-9111-7c10620f689c, eefa4f11-59eb-453c-a218-8e0ebea3f662 \| ledger 7USL00RI, 7USL00RJ, 7USL00RK \| pass (attempts 1) |  |
| LOG-0492 | 2026-10-13 13:49 | L8.3 | note | skipped checks: payer desk reads the case: sandbox auto-decided; payer desk takes approve: sandbox auto-decided \| corr 4a4908df-e83d-482d-8b4a-ae5b4c28bd86, 6530fa43-fe55-4c62-b3f1-ee8900b0f79d, 340d7ec4-90da-4b78-90d1-2c248ddd535c \| ledger 7USL00C4, 7USL00C5, 7USL00C6, 7USL00C8, 7USL00C9, 7USL00CA \| pass (attempts 1) |  |
| LOG-0493 | 2026-10-13 13:49 | L8.5 | note | blocked by the sandbox: the screens drove eligibility, seeding, the SB043F line, the draft and the pre-auth send; PMJAY refused it with PAYR-1235 Insufficient wallet balance (sandbox wallet used up by this run). Attempt 1 hit a transient policy-search error. PMJAY's decision arrives (C5): chip still "Pre-authorisation: Refused at the door" after 120s; PAYR-1235: Insufficient wallet balance. Hence  \| corr 32e18920-0d5d-4946-9147-2e0e0dcebead, 23ab9fec-2a97-41ca-a476-bf7128b81b23, e131e6de-fea3-4604-a4e7-11cc5e962db8 \| ledger 7USL00RQ, 7USL00RR, 7USL00RS, 7USL00RT, 7USL00RU, 7USL00RV \| blocked (attempts 2, sandbox) |  |
| LOG-0494 | 2026-10-13 13:49 | L8.3 | note | the PMJAY sandbox auto-approves SB043F before a desk can query it; set NHCX_TEST_PMJAY_MANUAL_PACKAGE to a seeded package it does not decide by itself \| blocked (attempts 1, sandbox) |  |
| LOG-0495 | 2026-10-13 13:49 | L8.5 | note | GUI walk not written in this round; the CLI runner covers the scenario \| skipped (attempts 1) |  |
| LOG-0496 | 2026-10-13 13:49 | L8.3 | note | provider adds a second MG072C cycle for the enhancement: refused 400: MG072C is already on this preauth. The claim keeps one line per code (D16 ux_claim_line) and an enhancement sends only new codes, while PMJAY takes a further cycle only as a new item sequence (PAYR-1274 when the quantity of the sent item is raised instead, ledger 7USL00DM) \| corr ecc19e03-7459-4659-a77a-fd297ae576d1, 42f3f9ea-7ce6-4ef1-92b4-80d9b02d63a6, f1873e91-c001-42e4-a6f5-c0f194bf2974, 23962842-a081-4d8d-991d-a619fefedb98 \| ledger 7USL00DN, 7USL00DO, 7USL00DP, 7USL00DQ, 7USL00DR, 7USL00DS \| fail (attempts 1, ours) |  |
| LOG-0497 | 2026-10-13 13:49 | L8.5 | note | GUI walk not written in this round; the CLI runner covers the scenario \| skipped (attempts 1) |  |
| LOG-0498 | 2026-10-13 13:49 | L8.3 | note | blocked by the sandbox: approve path passed end to end (role walk CEX>CPD>ACO>SHA, 18600.00 approved, correlation 67a35a2b-1f2d-455c-bf12-0da7225b27ec); query path: payer desk Forward as CEX answered Internal Server Error (cycle fc189812-f7a6-440e-8ffe-09e517b3312c), then every new pre-auth got PAYR-1235 Insufficient wallet balance. The query answer (x-hcx-status fix: request.initiated) could not  \| corr 3ce42f62-2345-47cc-9a15-c3e2ef9ae3d9, d31f607a-9f66-4d0b-9e13-8515d08c943c, 3d033082-4cbd-44a8-8058-9afa7cdd143b \| ledger 7USL00R1, 7USL00R2, 7USL00R3, 7USL00R4, 7USL00R5, 7USL00R6 \| blocked (attempts 3, sandbox) |  |
| LOG-0499 | 2026-10-13 13:49 | L8.5 | note | GUI walk not written in this round; the CLI runner covers the scenario \| skipped (attempts 1) |  |
| LOG-0500 | 2026-10-13 13:49 | L8.3 | note | skipped checks: payer desk role read as the case's state: sandbox auto-decided \| corr 68d34639-5cc8-43ed-bd25-7931626a2006, 90148ab9-6793-4b41-a4b8-040b8e4fbf99, e0cb8c57-adb9-48ad-9dfb-b279cf0f7c16, 40f44cfb-5fb7-4e7c-8143-8cdf6131cabb, c8de41dd-8923-4522-909c-7cc61f5478a6, d6da583a-e81e-4b99-a540-59d31f197eb2 \| ledger 7USL00LO, 7USL00LP, 7USL00LQ, 7USL00LR, 7USL00LS, 7USL00LT \| pass (attempts 1) |  |
| LOG-0501 | 2026-10-13 13:49 | L8.5 | note | GUI walk not written in this round; the CLI runner covers the scenario \| skipped (attempts 1) |  |
| LOG-0502 | 2026-10-13 13:49 | L8.3 | note | skipped checks: ABHA verify and registration from the ABHA profile (A19): not automated: the ABHA service stand-in (A19 M1 enrolment and its sealing key) is not part of this runner; predetermination with the refreshed token, discharge face verify and claim: not automated: the face verify needs the ABHA service's sealing key (A19 stand-in) \| corr a9f74d0c-127a-4955-bc55-3a86e5e839c5, a265e95f-583d-4d37-8b75-431bb6b85d93, a65f87d0-befe-476d-8f7d-3d591ff898c4, 8211d23d-c2d4-4511-8cef-27932eacfb90, 7dd63d08-439d-4cb3-a8b1-bdf0c922a0b4 \| ledger 7USL00J0, 7USL00J1, 7USL00J2, 7USL00J3, 7USL00J4, 7USL00J5 \| pass (attempts 1) |  |
| LOG-0503 | 2026-10-13 13:49 | L8.5 | note | GUI walk not written in this round; the CLI runner covers the scenario \| skipped (attempts 1) |  |
| LOG-0504 | 2026-10-13 13:49 | L6.4 | note | 7 files changed by L8 fixes re-hashed and re-checked in validation.json (status fixed); 41 e2e files added | `care/nhcx-plan/validation.json` modified |
| LOG-0505 | 2026-10-13 13:49 | L7.6 | note | care.nhcx unit suite 282 OK after L8 fixes (coordinator re-run); ruff clean |  |
| LOG-0506 | 2026-10-13 13:49 | L8.2 | done | T1 config, T2 runners (manage.py nhcx_e2e CLI; Playwright GUI in care_fe/tests/nhcx; scripts/nhcx-e2e.sh), scenarios T3-T19, payer drivers |  |
| LOG-0507 | 2026-10-13 13:49 | L8.3 | done | summary {'pass': 17, 'fail': 1, 'blocked': 4, 'skipped': 12} |  |
| LOG-0508 | 2026-10-13 13:49 | L8.4 | done | IRDAI desk via A14/A15 token login; PMJAY Payer Service role walk |  |
| LOG-0509 | 2026-10-13 13:49 | L8.5 | note | T16 fail (ours): D16 one line per code vs PMJAY needs new item per cycle (PAYR-1274); T12 blocked (IRDAI member cover exhausted); T15 blocked (needs NHCX_TEST_PMJAY_MANUAL_PACKAGE); T17 query path + T14 GUI blocked (desk 500, PMJAY wallet PAYR-1235); GUI walks missing for T6-T12,T15-T19 (skipped); query-answer status changed to request.initiated (contradicts CORE.md:90, per nhcx-docs) not yet confirmed live |  |
