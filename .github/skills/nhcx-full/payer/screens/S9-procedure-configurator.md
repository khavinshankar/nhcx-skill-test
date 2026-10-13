# S9. Procedure Configurator Screen

#### S9R. ROUTE
`/procedures/new`, `/procedures/edit/:id`

| Endpoint | Purpose |
|---|---|
| `GET procedures/:id` | The procedure being edited |
| `POST procedures` | Create |
| `PATCH procedures/:id` | Save changes (the code cannot change) |
| `GET document-types` | The NHCX document taxonomy the matrix is built from |

Breadcrumb: Procedures (S8) > `<procedure name>` or "New Procedure"

#### S9D. DESCRIPTION
One procedure and the three things the exchange reads from it. Saving uses "Save" (header) or "Create Procedure" / "Save Procedure" (foot); "Cancel" returns to S8.

**1. Procedure Identity**

| Field | Control | Rule |
|---|---|---|
| Procedure Name | text | "Enter the procedure name" |
| Procedure Code | text, monospace; a new procedure is offered `PROC-<4 digits>` [REF](../references/PAYERS.md#markers) | "Enter a procedure code"; letters, digits, hyphens and underscores only: "Use letters, digits, hyphens and underscores only"; "A procedure code is 32 characters or fewer"; upper-cased; on edit the code cannot change: "A procedure code cannot be changed once policies point at it" with the field note "Create a new procedure instead" |
| SNOMED CT Code | text | |
| ICD-10-PCS (PCS10) | text | |
| Category | select: Surgical, Medical, Emergency, Day Care, Diagnostic, Critical Care | "Choose a category" |
| Package Rate (₹) | number, blank means unpriced; "What the policy pays for the package. It is quoted on the InsurancePlan a hospital fetches and allowed per item on an auth-requirements ruling. Blank leaves it unpriced." | "A package rate cannot be negative"; screen: "Enter the package rate as a non-negative amount, or leave it blank" |
| Clinical Description | textarea | |
| Standard Treatment Guideline, questions asked at pre-authorisation | textarea, one question per line; "These become the STG questionnaire the InsurancePlan publishes with the package; the hospital answers them in words on the pre-authorisation. Leave blank to ask only whether the pre-auth documents are attached." | blank lines dropped; "Keep each question to 300 characters"; "A guideline asks at most 25 questions" |

The questions become one required free-text item each on the questionnaire ([F6. Questionnaire](../fhir/F6-questionnaire.md)) with `linkId` `<code>/stg/<n>`; a procedure with none gets one yes/no item per document wanted at pre-authorisation, never the discharge summary or the final bill, which nobody has at that stage.

**2. Document Requirements.** A matrix of every NHCX document type ([D3. document_type](../database/D3-document-type.md)) against the three phases:

| Phase | Label | Hint |
|---|---|---|
| `preauth` | Pre-Auth | Required before approval is granted |
| `discharge` | Discharge | Collected when the patient is discharged |
| `claim` | Claim | Mandatory for final claim settlement |

Each cell is a checkbox; a document may be required at more than one phase. A stage summary above the matrix shows the count per phase with a clear button. A toolbar filters the matrix by search (name, code, category), by document category (Identity, Clinical, Financial, Administrative, Legal, Transport) and "Selected only". "Showing `<n>` of `<total>` NHCX document types". A new procedure opens with Pre-Auth: POI, CER, EST; Discharge: HDS, MB; Claim: HDS, MB, FCF [REF](../references/PAYERS.md#markers). Server rules: "Every document rule needs a document code", "Each document can only be listed once per stage"; a code not in the taxonomy: "This refers to a member, policy, procedure or document type that does not exist". Screen refusal when every phase is empty: "Select at least one document requirement".

These rules are what the InsurancePlan publishes per package and phase ([F5. InsurancePlan](../fhir/F5-insuranceplan.md)), what an auth-requirements ruling names as due at each stage ([F3. CoverageEligibilityResponse](../fhir/F3-coverage-eligibility-response.md)), and what the plan's questionnaire asks about ([F6. Questionnaire](../fhir/F6-questionnaire.md)).

**3. Review.** Three columns, one per phase, listing the chosen documents as chips (each removable) or "No documents required at this stage".

Toasts: "Procedure "`<name>`" created", "Procedure "`<name>`" updated". Screen refusals: "Procedure name is required", "Procedure code is required".

API: [A1. Eligibility Answer](../apis/A1-eligibility-answer.md)

API: [A2. Insurance Plan Answer](../apis/A2-insurance-plan-answer.md)

Data: [D3. document_type](../database/D3-document-type.md)

Data: [D10. procedure_rule](../database/D10-procedure-rule.md)

Data: [D11. procedure_rule_doc](../database/D11-procedure-rule-doc.md)

#### S9L. LAYOUT
The arrangement below is the reference desk's [REF](../references/PAYERS.md#markers): follow the target payer system's own screen conventions. What is required is in DESCRIPTION and ACTIONS: the fields, the phases, the rules and the messages.

```
|------------------------------------------------------------------|
| New Procedure                              [< Cancel] [(save) Save]|
|------------------------------------------------------------------|
| [Card] Procedure Identity                                        |
|  Procedure Name [____________]   Procedure Code [PROC-4821]      |
|  SNOMED CT Code [______]  ICD-10-PCS [______]  Category [Surg v] |
|  Package Rate (₹) [______]                                       |
|  Clinical Description [________________________________]         |
|  Standard Treatment Guideline, questions asked at pre-auth       |
|  [one question per line_________________________________]        |
|------------------------------------------------------------------|
| [Card] Document Requirements                                     |
|  [Pre-Auth 3 x] [Discharge 2 x] [Claim 3 x]                      |
|  [(search) ________] [All Categories v] [Selected only]          |
|  Document                        | Pre-Auth | Discharge | Claim  |
|  Proof of identity  POI Identity |   [x]    |    [ ]    |  [ ]   |
|  Hospital discharge summary HDS  |   [ ]    |    [x]    |  [x]   |
|  Showing 17 of 17 NHCX document types                            |
|------------------------------------------------------------------|
| [Card] Review                                                    |
|  PRE-AUTH 3          DISCHARGE 2          CLAIM 3                |
|  [POI x][CER x][EST x] [HDS x][MB x]   [HDS x][MB x][FCF x]      |
|------------------------------------------------------------------|
|                                    [Cancel] [Create Procedure]   |
|------------------------------------------------------------------|
```

- Three cards in order; save and cancel appear in the header and again at the foot.
- The matrix scrolls inside its card with a sticky header; on small screens each document is a card with three toggle buttons.

#### S9A. ACTIONS
1. Save / Create Procedure / Save Procedure: validate, save, return to S8.
2. Cancel: return to S8 without saving.
3. Tick a cell: require that document at that phase; the summary and the review update.
4. Clear (per phase): remove every document from that phase.
5. Search, category, Selected only: filter the matrix; "Reset filters" clears them.
6. Remove a chip in Review: the same as unticking it.
