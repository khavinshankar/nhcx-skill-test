# T13. PMJAY Eligibility, Package Master and Ruling

#### T13D. DESCRIPTION

The PMJAY start of a claim, as [T3. IRDAI Policy Search and Eligibility](T3-irdai-policy-and-eligibility.md) and [T4. IRDAI Insurance Plan and Authorisation Requirements](T4-irdai-plan-and-auth-requirements.md) are for IRDAI, under the `pmjay` adapter ([PAYERS.md](../references/PAYERS.md)): the policy search ([A1. Policy Search](../apis/A1-policy-search.md)), eligibility ([A2. Coverage Eligibility Check](../apis/A2-coverage-eligibility-check.md), [C2. Coverage Eligibility Verdict](../callbacks/C2-coverage-eligibility-on-check.md)), the package master ([A3. Insurance Plan Request](../apis/A3-insurance-plan-request.md)) and the ruling on authorisation requirements ([A2. Coverage Eligibility Check](../apis/A2-coverage-eligibility-check.md) `auth-requirements`, [C3. Authorisation Requirements Ruling](../callbacks/C3-auth-requirements-on-check.md)). PMJAY messages go to the policy's processing id (for PMJAY the state health agency), which the search returns; the payer id only chooses the adapter (CORE confusions).

**The package master is requested and then left alone.** PMJAY answers a plan request in 15 to 60 minutes, or not at all within a session, and refuses a second request meanwhile (PAYR-1406) [SANDBOX](../references/PAYERS.md#markers). No test may depend on its arrival, and the seed is the only source of PMJAY STG and consent questions in a sandbox run. So this test sends [A3. Insurance Plan Request](../apis/A3-insurance-plan-request.md) once, records the correlation id, and does not wait: it seeds a package master for the claim's policy and every PMJAY test runs on that. The seed is a few fixed packages that PMJAY approves at PPD-Trust without the plan being read back (fixed rates, no tiers, no implants, no documents beyond the ruling's), so a decision can be taken on them in [T14. PMJAY Pre-authorisation Through the Payer Service](T14-pmjay-preauth-adjudicated.md) to [T18. PMJAY Payment Notice, Status Refusal and Cancel](T18-pmjay-payment-status-cancel.md). When the real plan does arrive on [C4. Insurance Plan Reply](../callbacks/C4-insuranceplan-on-request.md), it replaces the seed for that claim and the tests from then on use it.

#### T13S. SETUP

- The PMJAY test payer and the member id asked from the integrator ([T1. Test Configuration](T1-test-configuration.md)); `blocked` without it. The ABHA number is not needed: the registry returns it with the policy.
- A patient in the HMIS carrying that member id.
- The seed below, committed as `tests/nhcx/e2e/fixtures/pmjay-plan.json` (`NHCX_TEST_PMJAY_PLAN_SEED`). It is written exactly as given, not adapted: every code, name, price, flag, document and questionnaire is taken verbatim from PMJAY's own InsurancePlan answer for policy `PMJAY/HP/S/G` (the knowledge source's `fhir/C4/C4-response-pmjay.json`), cut down to two packages. Two is the most it holds, and which two is fixed:

| Package | Why it is in the seed |
|---|---|
| `SB043F` Hand (Single Stage Amputation), ₹18,600, surgical | The pre-authorisation and claim of [T14. PMJAY Pre-authorisation Through the Payer Service](T14-pmjay-preauth-adjudicated.md), [T15. PMJAY Query Answered by Resubmission](T15-pmjay-query-by-resubmission.md), [T17. PMJAY Claim Through the Role Walk](T17-pmjay-claim-adjudicated.md) and [T18. PMJAY Payment Notice, Status Refusal and Cancel](T18-pmjay-payment-status-cancel.md): a fixed rate, no tiers, no implants, approval not required, one per episode. Enhancement is not allowed on it. |
| `MG072C` Acute Haemodialysis, ₹1,500 a cycle, medical, day care | The enhancement of [T16. PMJAY Rejection and Enhancement](T16-pmjay-rejection-and-enhancement.md): enhancement is allowed, and it is cyclic (up to 6 cycles), so the enhancement is one more cycle of it. |

```json
{
  "source": "PMJAY InsurancePlan for PMJAY/HP/S/G, from the NHCX package fhir/C4/C4-response-pmjay.json, cut to two packages",
  "plan": {
    "identifier": [
      {"system": "https://hcx.pmjay.gov.in/v1/InsurancePlan", "value": "100155-HOSP2P146514"},
      {"system": "https://payer.nha.gov.in", "value": "PMJAY/HP/S/G", "type": "NH"}
    ],
    "name": "PMJAY - Universal Health Policy",
    "period": {"start": "2023-04-01", "end": "2028-04-01"},
    "plan_type": {"code": "03", "display": "Group", "system": "https://nrces.in/ndhm/fhir/r4/CodeSystem/ndhm-plan-type"},
    "package_code_system": "http://hl7.org/fhir/ValueSet/procedure-category",
    "speciality_system": "https://nrces.in/ndhm/fhir/r4/ValueSet/ndhm-benefitcategory"
  },
  "packages": [
    {
      "code": "SB043F",
      "name": "Hand (Single Stage Amputation)",
      "speciality": {"code": "SG", "display": "General Surgery"},
      "kind": "procedure",
      "rate": 18600,
      "currency": "INR",
      "conditions": {
        "ProcedureType": "Surgical", "GovtReserved": "N", "ApprovalNotRequired": "Y",
        "EnhancementAllowed": "N", "ScheduledTATApproval": "Y", "QuantityAllowed": "1",
        "IsDayCare": "N", "ImplantApplicable": "N", "StratificationAllowed": "N",
        "MultipleImplantsAllowed": "N", "MultipleStratificationAllowed": "N",
        "MaximumImplantsAllowed": "1", "MaximumStratificationAllowed": "1",
        "CyclicProcedure": "N", "MaximumCyclesAllowed": "0", "Standalone": "N",
        "ParentProcedure": "NA", "Unspecified": "N"
      },
      "documents": [
        {"code": "MAND0384", "name": "MLC/ FIR if traumatic", "category": "DIA"},
        {"code": "MAND0592", "name": "X Ray of affected limb", "category": "DIA"},
        {"code": "MAND0006", "name": "Detailed discharge summary", "category": "DIA"},
        {"code": "MAND0008", "name": "Detailed Procedure / Operative Notes", "category": "DIA"},
        {"code": "MAND0112", "name": "Post Procedure clinical photgraph", "category": "DIA"},
        {"code": "MAND0582", "name": "clinical photograph of affected part", "category": "DIA"},
        {"code": "MAND0604", "name": "clinical notes justifying the indication", "category": "DIA"}
      ],
      "requirements": [{"category": "INF", "code": "STG", "display": "Standard Treatment Guidelines"}]
    },
    {
      "code": "MG072C",
      "name": "Acute Haemodialysis (Acute Haemodialysis)",
      "speciality": {"code": "MG", "display": "General Medicine"},
      "kind": "procedure",
      "rate": 1500,
      "currency": "INR",
      "conditions": {
        "ProcedureType": "Medical", "GovtReserved": "N", "ApprovalNotRequired": "Y",
        "EnhancementAllowed": "Y", "ScheduledTATApproval": "Y", "QuantityAllowed": "6",
        "IsDayCare": "Y", "ImplantApplicable": "N", "StratificationAllowed": "N",
        "MultipleImplantsAllowed": "N", "MultipleStratificationAllowed": "N",
        "MaximumImplantsAllowed": "1", "MaximumStratificationAllowed": "1",
        "CyclicProcedure": "Y", "MaximumCyclesAllowed": "6", "Standalone": "N",
        "ParentProcedure": "NA", "Unspecified": "N"
      },
      "documents": [
        {"code": "MAND0409", "name": "any investigations done", "category": "DIA"},
        {"code": "MAND0064", "name": "All investigations reports", "category": "DIA"},
        {"code": "MAND0006", "name": "Detailed discharge summary", "category": "DIA"},
        {"code": "MAND0062", "name": "Detailed ICPs", "category": "DIA"},
        {"code": "MAND0063", "name": "Treatment details", "category": "DIA"},
        {"code": "MAND0408", "name": "Clinical notes detailing history and Admission notes showing vitals and examination findings", "category": "CD"}
      ],
      "requirements": []
    }
  ],
  "questionnaires": [
    {
      "url": "https://payer.gov.in/policy/questionnaire/100020", "title": "Admission Details",
      "items": [
        {"linkId": "100075", "type": "dateTime", "text": "Admission Date", "required": true},
        {"linkId": "100074", "type": "dateTime", "text": "Surgery/Treatment Start Date", "required": true},
        {"linkId": "100073", "type": "choice", "text": "Admission Type", "required": true, "options": ["PLANNED", "EMERGENCY"]},
        {"linkId": "100076", "type": "choice", "text": "Medico Legal Case", "required": true, "options": ["Yes", "No"]}
      ]
    },
    {
      "url": "https://payer.gov.in/policy/questionnaire/100008", "title": "General Findings",
      "items": [
        {"linkId": "100019", "type": "string", "text": "Temperature"},
        {"linkId": "100020", "type": "string", "text": "Pulse Rate Per Minute"},
        {"linkId": "100021", "type": "string", "text": "Height(in CM)"},
        {"linkId": "100022", "type": "string", "text": "Weight(in KG)"},
        {"linkId": "100023", "type": "string", "text": "BMI"},
        {"linkId": "100024", "type": "choice", "text": "Cyanosis"},
        {"linkId": "100025", "type": "choice", "text": "Pallor"},
        {"linkId": "100027", "type": "choice", "text": "Malnutrition"},
        {"linkId": "100029", "type": "choice", "text": "Oedema in Feet"}
      ]
    },
    {
      "url": "https://payer.gov.in/policy/questionnaire/100010", "title": "Personal History",
      "items": [
        {"linkId": "100035", "type": "choice", "text": "Appetite"},
        {"linkId": "100038", "type": "choice", "text": "Bowels"},
        {"linkId": "100039", "type": "choice", "text": "Nutrition"},
        {"linkId": "100040", "type": "choice", "text": "Known Allergies"},
        {"linkId": "100037", "type": "choice", "text": "Diet"},
        {"linkId": "100041", "type": "choice", "text": "Habits/Addictions"}
      ]
    },
    {
      "url": "https://payer.gov.in/policy/questionnaire/100011", "title": "Family History",
      "items": [
        {"linkId": "100036", "type": "choice", "text": "Diabetes"},
        {"linkId": "100042", "type": "choice", "text": "Hypertension"},
        {"linkId": "100043", "type": "choice", "text": "Heart Disease"},
        {"linkId": "100044", "type": "choice", "text": "Stroke"},
        {"linkId": "100055", "type": "choice", "text": "Cancer"},
        {"linkId": "100056", "type": "choice", "text": "Tuberculosis"},
        {"linkId": "100057", "type": "choice", "text": "Asthma"}
      ]
    },
    {
      "url": "https://payer.gov.in/policy/questionnaire/100024", "title": "Authentication Consent",
      "items": [
        {"linkId": "100093", "type": "attachment", "text": "Medical Superintendent Declaration Form (During Admission)", "required": true},
        {"linkId": "100095", "type": "string", "text": "Remarks"}
      ]
    },
    {
      "url": "https://payer.gov.in/policy/questionnaire/100466", "title": "Discharge Consent", "stage": "claim",
      "items": [
        {"linkId": "135477", "type": "attachment", "text": "Medical Superintendent Declaration Form (During Discharge)", "required": true}
      ]
    },
    {
      "url": "https://payer.gov.in/policy/questionnaire/100005", "title": "Discharge Information", "stage": "claim",
      "items": [
        {"linkId": "100097", "type": "attachment", "text": "Post Treatment Photo with Doctor/PMAM", "required": true},
        {"linkId": "100096", "type": "attachment", "text": "Discharge Summary", "required": true},
        {"linkId": "101799", "type": "choice", "text": "Discharge Stage", "required": true, "options": ["After Surgery/Treatment"]},
        {"linkId": "100101", "type": "dateTime", "text": "Surgery/Treatment Date", "required": true},
        {"linkId": "100012", "type": "dateTime", "text": "Discharge Date", "required": true},
        {"linkId": "103045", "type": "attachment", "text": "Feedback Form", "required": true},
        {"linkId": "103119", "type": "choice", "text": "Have Hospital provided the medicines during treatment/for post operative care", "required": true, "options": ["Yes", "No"]}
      ]
    }
  ]
}
```

How the seed is used:

- It is written into the claim's [D10. claim_plan](../database/D10-claim-plan.md) (status `ready`, its source marked as the test seed) and [D11. claim_plan_benefit](../database/D11-claim-plan-benefit.md) rows, and the questionnaires into [D12. claim_plan_form](../database/D12-claim-plan-form.md), through the same code path [C4. Insurance Plan Reply](../callbacks/C4-insuranceplan-on-request.md) uses, so the screens and services see an ordinary plan. Never written where a real plan is already `ready`; removed when the run ends.
- The pre-authorisation of [T14. PMJAY Pre-authorisation Through the Payer Service](T14-pmjay-preauth-adjudicated.md), [T15. PMJAY Query Answered by Resubmission](T15-pmjay-query-by-resubmission.md), [T17. PMJAY Claim Through the Role Walk](T17-pmjay-claim-adjudicated.md) and [T18. PMJAY Payment Notice, Status Refusal and Cancel](T18-pmjay-payment-status-cancel.md) quotes `SB043F` once, ₹18,600. The claim of [T17. PMJAY Claim Through the Role Walk](T17-pmjay-claim-adjudicated.md) bills the same.
- The enhancement of [T16. PMJAY Rejection and Enhancement](T16-pmjay-rejection-and-enhancement.md) is on a claim that quoted `MG072C`: one cycle at pre-authorisation, and the enhancement adds a second cycle (₹1,500), which the package allows (cyclic, up to 6). `SB043F` is never enhanced: PMJAY does not allow it.
- Documents: the tests attach one small PDF under each document code the chosen package lists, at the `pre` stage, before sending ([S9. Pre-authorisation](../screens/S9-preauthorisation.md)). The `Discharge Information` and `Discharge Consent` questionnaires and their attachments belong to the claim stage ([S11. Claim Submission](../screens/S11-claim-submission.md)); the other five (`Admission Details`, `General Findings`, `Personal History`, `Family History`, `Authentication Consent`) are answered at pre-authorisation, the required items with the options given, attachments with a small PDF, the rest with plain values.
- **The consent questionnaires are not optional in the seed.** A PMJAY pre-authorisation or claim sent without a biometric token ([A18. Biometric Authentication](../apis/A18-biometric-authentication.md), [T19. PMJAY Beneficiary Verification and ABHA](T19-pmjay-biometric-and-abha.md)) is refused unless the Authentication Consent (`100024`, items `100093` attachment and `100095` string) rides on the pre-authorisation and the Discharge Consent (`100466`, item `135477` attachment) on the claim: PAYR-1256 and PAYR-1363 otherwise. They are answered as in the knowledge package's `fhir/D4/D4-request.json` and `fhir/D9/D9-request.json`. PMJAY's ruling names `100024` at pre-authorisation and nothing names `100466`, which is why the forms card offers a consent form whenever no token is held ([S9. Pre-authorisation](../screens/S9-preauthorisation.md), [S11. Claim Submission](../screens/S11-claim-submission.md)).

#### T13G. GUI

1. [S5. Claim Master](../screens/S5-claim-master.md), [S1. Search Policy](../screens/S1-search-policy.md), [S2. Select Policy](../screens/S2-select-policy.md): new claim, search by the PMJAY member id, pick the PMJAY policy.
2. [S3. Policy Discovery](../screens/S3-policy-discovery.md): discovery, then validation.
3. [S7. Insurance Plan](../screens/S7-insurance-plan.md): request the package master once; read "fetching" and move on. Seed the package master (payer driver, [T2. Test Runners](T2-test-runners.md)); reload [S7. Insurance Plan](../screens/S7-insurance-plan.md) and read it as `ready`.
4. [S8. Line Items](../screens/S8-line-items.md): add `SB043F` from the seed; [S8.2](../screens/S8-line-items.md): validate.

#### T13L. CLI

1. [A1. Policy Search](../apis/A1-policy-search.md) with the member id; pick the PMJAY row; read the ABHA number the registry returned.
2. [A2. Coverage Eligibility Check](../apis/A2-coverage-eligibility-check.md) `discovery` and `validation`; wait for [C2. Coverage Eligibility Verdict](../callbacks/C2-coverage-eligibility-on-check.md) each.
3. [A3. Insurance Plan Request](../apis/A3-insurance-plan-request.md) once; record the correlation id; do not wait. Seed the package master for the claim's policy.
4. Add a line for `SB043F`; [A2. Coverage Eligibility Check](../apis/A2-coverage-eligibility-check.md) `auth-requirements`; wait for [C3. Authorisation Requirements Ruling](../callbacks/C3-auth-requirements-on-check.md).

#### T13X. EXPECT

- The search returns the PMJAY policy with both ids and the beneficiary's ABHA number, and every message is addressed to the processing id (read off the opened claim, as [T3. IRDAI Policy Search and Eligibility](T3-irdai-policy-and-eligibility.md) does).
- Both eligibility checks are answered; every claim line carries the programme code `AB-PMJAY` ([PAYERS.md](../references/PAYERS.md)) and PMJAY's own code system; the facility is named by the HFR id on its own record.
- The plan request went out (NHCX 202) exactly once for this policy in the run; its correlation id is in the report. Its answer is not waited for. If it arrives, [S7. Insurance Plan](../screens/S7-insurance-plan.md) shows the real plan in place of the seed.
- The seeded package master reads `ready` on [S7. Insurance Plan](../screens/S7-insurance-plan.md) with exactly the two packages, their rates and documents as given, and the seven questionnaires: five at pre-authorisation (the four clinical forms and the Authentication Consent) and two at the claim (Discharge Information, Discharge Consent); [S8. Line Items](../screens/S8-line-items.md) lists both packages.
- The ruling arrives on the auth-requirements correlation id and lists what the chosen package needs at the `pre` stage.
