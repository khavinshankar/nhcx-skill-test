# F3. CoverageEligibilityResponse

#### F3R. RESOURCE
`CoverageEligibilityResponse`. Direction: received on `coverageeligibility/on_check`. No NRCeS profile is required or checked. PMJAY sends `meta.profile` `http://hl7.org/fhir/StructureDefinition/CoverageEligibilityResponse` [PAYER](../references/PAYERS.md#markers).

#### F3D. DESCRIPTION
The payer's answer to F2, carried in a bundle that repeats the request's seven entries and then appends the payer's own `CoverageEligibilityResponse`, `Patient`, `Coverage` and Organizations. Where a resource type repeats, the **last** one in the bundle is the payer's. A reply may also carry only the response, Patient and Coverage.

The same resource is read two ways, depending on which exchange the correlation id belongs to:

**Eligibility verdict** (answer to `validation`, `benefits`, `discovery`; C2). Read into the case row, D9 `claim`:
- `insurance[0].inforce` decides eligible or not. `outcome: error` makes the case `error`, else `inforce` true makes it `eligible`, else `not-eligible`.
- The wallet. Every `insurance[0].item[].benefit[]` that has `allowedMoney` is a candidate. The one typed `benefit` wins, then the one typed `30` ("Health Benefit Plan Coverage"), then the first [PAYER](../references/PAYERS.md#markers). `allowedMoney` is what is left on the wallet and `usedMoney` what has gone. The sum insured is stored as left plus used, so the balance shown (sum insured minus used) equals `allowedMoney`.
- `item[].authorizationRequired`: the last item that states it wins.
- The payer's Patient (the last Patient in the bundle): name, gender, birth date, address, ABHA, photo.
- The payer's Coverage (the last Coverage): plan name, period, relationship.

**Authorisation-requirements ruling** (answer to `auth-requirements`; C3). Read into D13 `claim_auth`, one D14 `claim_auth_item` per `insurance[0].item`, and one D15 `claim_auth_requirement` per distinct `authorizationSupporting` entry:
- Each item answers one quoted line: `authorizationRequired`, `excluded`, the first benefit's type and `allowedMoney`.
- `authorizationSupporting[]` is a list of CodeableConcepts whose free-text `text` says what each is; the text conventions below are the PMJAY dialect [PAYER](../references/PAYERS.md#markers). A text holding `fullUrl: <url>` is a **form** to answer (a Questionnaire, F6, from the plan, F5). Any other is a **document**, and its `Type: <stage>` says when it is due (a document with no `Type:` is due `pre`). `Procedure Code: <code>` names the package it is for. Matching is case-insensitive.
- A requirement is due at pre-authorisation when it is a form, or when its stage is in the adapter's pre-authorisation stages (see [PAYERS.md](../references/PAYERS.md)) [PAYER](../references/PAYERS.md#markers). All others are due with the claim.
- Requirements are de-duplicated on (kind, code, form url) across items.
- A ruling with no `authorizationSupporting` at all is valid. It asks for nothing beyond the package master's own list.

A ProtocolResponse in place of the bundle (F1) turns the case, or the ruling, to `error` with `<code>: <message>`.

#### F3F. FIELDS
Eligibility verdict, into D9 `claim`:

| Element read | Stored in | Notes |
|---|---|---|
| `outcome` | `claim.outcome` | `error` sets `claim.status` = `error` |
| `disposition` | `claim.disposition` | for example "Policy is currently in-force" |
| `insurance[0].inforce` | `claim.inforce` (1/0) | true sets `claim.status` = `eligible`, else `not-eligible` |
| `insurance[0].item[].authorizationRequired` | `claim.auth_required` (1/0) | last item stating it |
| `insurance[0].item[].benefit[].type.coding[].code` | chooses the wallet | `benefit`, then `30`, then first |
| wallet `allowedMoney.value` + `usedMoney.value` | `claim.allowed_amount` | the sum insured |
| wallet `usedMoney.value` | `claim.used_amount` | |
| last Patient `name[0].text`, else `given` joined, else `family` | `claim.beneficiary_name` | |
| last Patient `gender` / `birthDate` | `claim.patient_gender` / `claim.patient_dob` | |
| last Patient `address[0]`: `line[]`, `district`, `state`, `postalCode` | `claim.patient_address` | joined with ", " |
| last Patient `identifier[]` with type code `ABHA` | `claim.abha_number` | |
| last Patient `photo[0].data`, else `.url` | `claim.patient_photo` | |
| last Coverage `class[0].name` | `claim.plan_name` | |
| last Coverage `period.start` / `period.end` | `claim.plan_period_start` / `claim.plan_period_end` | |
| last Coverage `relationship.coding[0].display`, else `.code` | `claim.relationship` | |
| the whole bundle | `claim.response_json` | |

Empty values are not written, so a reply without a Patient keeps what the case already had.

Authorisation-requirements ruling, the **last** CoverageEligibilityResponse in the bundle:

| Element read | Stored in | Notes |
|---|---|---|
| `outcome`, `disposition` | D13 `claim_auth.outcome`, `.disposition` | `claim_auth.status` = `ready` |
| `insurance[0].inforce` | D13 `claim_auth.inforce` (1/0) | |
| `insurance[0].item[].productOrService.coding[0]` code / display (else `text`) | D14 `claim_auth_item.code` / `.display` | one row per item, `seq` from 1 |
| `item[].category.coding[0].code` | D14 `claim_auth_item.category_code` | |
| `item[].authorizationRequired` | D14 `claim_auth_item.auth_required` (1/0) | |
| `item[].excluded` | D14 `claim_auth_item.excluded` (1/0) | |
| `item[].benefit[0].type.coding[0].code` | D14 `claim_auth_item.benefit_type` | for example `Procedure` |
| `item[].benefit[0].allowedMoney.value` | D14 `claim_auth_item.allowed_amount` | |
| `item[].authorizationSupporting[].coding[0].code` / `.display` | D15 `claim_auth_requirement.code` / `.display` | |
| `authorizationSupporting[].text`, `fullUrl: <url>` | D15 `.kind` = `form`, `.form_url` = the url | |
| `authorizationSupporting[].text`, no `fullUrl:` | D15 `.kind` = `document` | |
| `authorizationSupporting[].text`, `Type: <stage>` | D15 `.stage` (lower case) | a document with none is `pre`, a form `""` |
| `authorizationSupporting[].text`, `Procedure Code: <code>` | D15 `.for_code` | else the item's own code |
| computed | D15 `.at_preauth` (1/0) | form, or stage in the adapter's pre-authorisation stages |
| the whole bundle | D13 `claim_auth.response_json` | |

#### F3U. USED BY
- Callbacks: [C2. Coverage Eligibility Verdict](../callbacks/C2-coverage-eligibility-on-check.md), [C3. Authorisation Requirements Ruling](../callbacks/C3-auth-requirements-on-check.md)
- FHIR: [F1. Bundle](F1-bundle.md), [F2. CoverageEligibilityRequest](F2-coverage-eligibility-request.md), [F5. InsurancePlan](F5-insuranceplan.md), [F6. Questionnaire](F6-questionnaire.md)
