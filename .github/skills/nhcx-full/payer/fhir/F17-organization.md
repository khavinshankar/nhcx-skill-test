# F17. Organization

#### F17R. RESOURCE
`Organization`. Direction: **sent** in every outbound bundle, as this payer and as the hospital the message is addressed to; **received** in every hospital bundle, read only for the facility's registry id, name and phone. The profile `https://nrces.in/ndhm/fhir/r4/StructureDefinition/Organization` is declared on the plan and query family (F5, F11); the case-answer family carries the `SUBSETTED` tag instead (F1).

#### F17D. DESCRIPTION
Three builders, because the two families write the payer differently [REF](../references/PAYERS.md#markers):

| Where | This payer | The hospital |
|---|---|---|
| Case answers (F3, F9, F10, F13): at `<anchor>/organization/payer/<payer id>` and `<anchor>/organization/provider/<facility id>` | typed `pay` "Payer", identifier `NIIP` "National Insurance Payor Identifier (Payor)" on `https://facility.abdm.gov.in`, `active` `true`, `name` (left off on the payment notice, as the scheme leaves it off); F3 adds the phone under `contact[0].telecom` | typed `prov` "Healthcare Provider", identifier `NPI` "National provider identifier" on the same system, `name` the hospital's name else its id |
| Plan (F5): at `urn:uuid:` | typed `ins` "Insurance Company", identifiers `ROHINI` (ndhm-identifier-type-code, system `https://rohini.iib.gov.in/`) and `PRN` "Provider number" (v2-0203, system `https://irdai.gov.in`) when the payer record holds them, `telecom` phone and email, `address` | not sent |
| Query (F11): at `urn:uuid:` | the plan builder's Organization without its address | typed `prov`, identifier `PRN` on `https://facility.ndhm.gov.in` holding the HFR id |

`https://facility.abdm.gov.in` is what the scheme writes; the hospital side sends `https://nhcx.abdm.gov.in` on its own Organizations and checks neither [PAYER](../references/PAYERS.md#markers).

**The payer id.** The identifier value in the case-answer family is this payer's participant code without its `@hcx` suffix, taken from the code the message is sent as (the recipient code of the request it answers, `D19.nhcx_recipient_code`), else `D1.nhcx_participant_id`, else `D1.code` [REF](../references/PAYERS.md#markers). The insurer Organization of the plan family is identified by name alone when neither the ROHINI id nor the IRDAI registration is recorded, and the render says so ([S12. Organisation](../screens/S12-organisation.md) is where they are entered).

**The facility id.** `D19.hospital_hfr_id` as the hospital declared it on its Claim; on an eligibility answer the `NPI` identifier of the request's provider Organization; when neither is known, the numeric part of the hospital's participant code, so the anchor still resolves [REF](../references/PAYERS.md#markers). A case with no facility id and no recipient is rendered with an unidentified hospital and a warning.

**Received.** A hospital's bundle names itself and this payer as Organizations. This payer reads the one typed `prov` (else the one the Claim's `provider` or the request's `provider` points at) for its `NPI` or `PRN` identifier value (the HFR id, kept as `D19.hospital_hfr_id`), its `name` (`D19.hospital_name`) and, on an eligibility request, its phone, which the answer echoes on the hospital Organization. The payer Organization a hospital sends is not read: this payer knows who it is. A reply addressed to a code this payer does not host is not opened at all ([G8. Receive](../gateway/G8-receive.md)).

#### F17F. FIELDS
This payer, case-answer family:

| Element written | From | Notes |
|---|---|---|
| `id` | the payer code without `@hcx` | |
| `meta.tag[0]` | `SUBSETTED` | |
| `identifier[0]` | type `NIIP` (v2-0203), `system` `https://facility.abdm.gov.in`, `value` the payer code without `@hcx` | |
| `active` | `true` | |
| `type[0].coding[0]` | `pay` "Payer" (`http://terminology.hl7.org/CodeSystem/organization-type`) | |
| `name` | `D1.name` | not on F13 |
| `contact[0].telecom[0]` | `phone`, `D1.phone` | F3 only |

This payer, plan and query family:

| Element written | From | Notes |
|---|---|---|
| `id` | UUID v5 of `Organization/<D1.id>` | |
| `meta.profile[0]` | the Organization profile | |
| `identifier[]` | `ROHINI` with `D1.rohini_id`; `PRN` with `D1.irdai_registration` | each only when set |
| `type[0].coding[0]` | `ins` "Insurance Company" | |
| `name` | `D1.name` | |
| `telecom[]` | `phone` `D1.phone`, `email` `D1.email`, `use` `work` | |
| `address[0]` | `D1.address_line`, `.city`, `.state`, `.pincode`, `.country` | F5 only; left out when empty |

The hospital, sent back:

| Element written | From | Notes |
|---|---|---|
| `id` | the facility id | case-answer family |
| `identifier[0]` | type `NPI` (case answers) or `PRN` (query), `value` `D19.hospital_hfr_id` | system per family, above |
| `active` | `true` | case answers |
| `type[0].coding[0]` | `prov` "Healthcare Provider" | |
| `name` | `D19.hospital_name`, else the facility id | |
| `contact[0].telecom[0]` | the request's phone | F3 only |

Received (read):

| Element read | Stored in | Notes |
|---|---|---|
| `type[].coding[].code` = `prov` | picks the hospital's Organization | else the one the Claim or request `provider` points at |
| `identifier[].value` typed `NPI` or `PRN`, else the first | `D19.hospital_hfr_id`; the F3 requestor id | |
| `name` | `D19.hospital_name` | |
| `contact[].telecom[]` or `telecom[]` phone | echoed on F3 | not stored |

#### F17U. USED BY
- Screens: [S12. Organisation](../screens/S12-organisation.md)
- APIs: [A1. Eligibility Answer](../apis/A1-eligibility-answer.md), [A2. Insurance Plan Answer](../apis/A2-insurance-plan-answer.md), [A3. Pre-auth Answer](../apis/A3-preauth-answer.md), [A4. Claim Answer](../apis/A4-claim-answer.md), [A5. Query Request](../apis/A5-query-request.md), [A6. Payment Notice](../apis/A6-payment-notice.md), [A7. Payment Enquiry Answer](../apis/A7-payment-enquiry-answer.md), [A8. Status Answer](../apis/A8-status-answer.md), [A9. Task Answer](../apis/A9-task-answer.md), [A10. Predetermination Quote](../apis/A10-predetermination-quote.md)
- Callbacks: [C2. Coverage Eligibility Check](../callbacks/C2-coverage-eligibility-check.md), [C3. Insurance Plan Request](../callbacks/C3-insurance-plan-request.md), [C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md), [C5. Claim Submit](../callbacks/C5-claim-submit.md), [C10. Payment Enquiry](../callbacks/C10-payment-enquiry.md)
- FHIR: [F1. Bundle](F1-bundle.md), [F2. CoverageEligibilityRequest](F2-coverage-eligibility-request.md), [F3. CoverageEligibilityResponse](F3-coverage-eligibility-response.md), [F5. InsurancePlan](F5-insuranceplan.md), [F8. Claim](F8-claim.md), [F9. ClaimResponse](F9-claimresponse.md), [F10. Task (claim actions and answers)](F10-task-claim-actions.md), [F11. CommunicationRequest](F11-communicationrequest.md), [F13. PaymentNotice](F13-paymentnotice.md), [F18. Coverage](F18-coverage.md), [F19. Other resources](F19-other-resources.md)
- Database: [D1. payer](../database/D1-payer.md), [D19. case](../database/D19-case.md)
