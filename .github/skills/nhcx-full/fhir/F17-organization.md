# F17. Organization

#### F17R. RESOURCE
- `resourceType`: `Organization`
- Profile in `meta.profile`: `https://nrces.in/ndhm/fhir/r4/StructureDefinition/Organization`
- Direction: **sent**, as the provider (the facility) and the payer, in every outbound bundle except the InsurancePlan request (F4). **Received** in almost every payer bundle; read only to find which Organization is the facility's when a communication is answered.

#### F17D. DESCRIPTION
Two roles, one builder:

| Role | fullUrl | `type` | Identifier type | Identifier value |
|---|---|---|---|---|
| Provider | `https://nhcx.abdm.gov.in/provider` | `prov` "Healthcare Provider" | `NPI` "National provider identifier" | the facility's HFR id |
| Payer | `https://nhcx.abdm.gov.in/payer` | `pay` "Payer" | `NIIP` "National Insurance Payor Identifier (Payor)" | the payer's participant code without its `@` suffix (`<code>@hcx` goes as `<code>`) |

Both identifiers carry `system` `https://nhcx.abdm.gov.in` (not the facility's own identifier system on D1). The provider is always first, the payer second.

**Where they come from.**
- Provider: the default facility (`D1 organization` with `is_default`). Every send refuses without its HFR id and participant code ("Set the facility's HFR ID and NHCX participant code under Settings ...").
- Payer: the claim's payer (`D9 claim.payer_id`, `D9 claim.payer_name`), else the configured default payer code and name (the reference implementation defaults to the PMJAY payer, see [PAYERS.md](../references/PAYERS.md)) [REF](../references/PAYERS.md#markers). `D9 claim.payer_name` is set when the claim is opened: the payer's registered name on the participant registry (G4), cached; never the search row's name or the adapter's.
- Exception: when a notification is acknowledged and the payer named no Organization as the facility's, the payer Organization built there takes its code from the notification's `x-hcx-sender_code` (F12).

**`id` by bundle.**

| Bundle | Provider `id` | Payer `id` |
|---|---|---|
| Claim bundles (F8, A4 and A5), communication-reply stubs (F12) | `1` | `2` |
| Eligibility (F2), Task bundles (F10, F14) | none | none |
| Communication reply lifted from a sent leg, acknowledgement | as the source bundle had them | as the source bundle had them |

**Received Organizations.** Not read in eligibility, ClaimResponse, InsurancePlan, Task or payment bundles. In a CommunicationRequest bundle (F11) they are used only when the answer is built (F12):
- acknowledgement: the facility's is the one the payer's `Task.owner` or `CommunicationRequest.recipient[]` points at (by fullUrl), else the one whose `type` has a coding `prov`, else none (the facility's own is built);
- reply lifted from a sent leg: the provider is the one typed `prov`, else the one at the provider fullUrl, else the first; the payer is the next.

Payers type themselves differently: PMJAY `pay`, the Sandbox Payer `ins` "Insurance Company" with ROHINI and PRN identifiers [PAYER](../references/PAYERS.md#markers).

#### F17F. FIELDS
**Provider (sent)**

| Element path | Value or source | Notes |
|---|---|---|
| `id` | `1` in claim bundles, else absent | see table above |
| `meta.profile[0]` | `.../StructureDefinition/Organization` | |
| `identifier[0].type.coding[0]` | `http://terminology.hl7.org/CodeSystem/v2-0203` `NPI` "National provider identifier" | |
| `identifier[0].system` | `https://nhcx.abdm.gov.in` | constant |
| `identifier[0].value` | `D1 organization.identifier_value` (HFR id) | |
| `type[0].coding[0]` | `http://terminology.hl7.org/CodeSystem/organization-type` `prov` "Healthcare Provider" | |
| `name` | `D1 organization.name`, else the HFR id | |

**Payer (sent)**

| Element path | Value or source | Notes |
|---|---|---|
| `id` | `2` in claim bundles, else absent | |
| `meta.profile[0]` | `.../StructureDefinition/Organization` | |
| `identifier[0].type.coding[0]` | v2-0203 `NIIP` "National Insurance Payor Identifier (Payor)" | |
| `identifier[0].system` | `https://nhcx.abdm.gov.in` | constant |
| `identifier[0].value` | `D9 claim.payer_id` else the default payer code, cut at the first `@`, trimmed | |
| `type[0].coding[0]` | organization-type `pay` "Payer" | |
| `name` | `D9 claim.payer_name` (the registry name), else the registry name fetched now (G4), else the NIIP value | |

Not sent: `active`, `telecom`, `address` (D1 holds phone and address; they are not used).

**Received (read elements only)**

| Element path | Used for |
|---|---|
| entry `fullUrl` | matched against `Task.owner.reference` and `CommunicationRequest.recipient[].reference` |
| `type[].coding[0].code` = `prov` | marks the facility's Organization |

#### F17U. USED BY
- APIs: [A2. Coverage Eligibility Check](../apis/A2-coverage-eligibility-check.md), [A4. Pre-auth Submit](../apis/A4-preauth-submit.md), [A5. Claim Submit](../apis/A5-claim-submit.md), [A6. Task Submit (cancel, status, reprocess, release)](../apis/A6-task-submit.md), [A7. Communication Reply](../apis/A7-communication-on-request.md), [A8. Payment Notice Acknowledgement](../apis/A8-paymentnotice-on-request.md)
- Callbacks: [C2. Coverage Eligibility Verdict](../callbacks/C2-coverage-eligibility-on-check.md), [C3. Authorisation Requirements Ruling](../callbacks/C3-auth-requirements-on-check.md), [C4. Insurance Plan Reply](../callbacks/C4-insuranceplan-on-request.md), [C5. Pre-auth Reply](../callbacks/C5-preauth-on-submit.md), [C6. Claim Reply](../callbacks/C6-claim-on-submit.md), [C7. Cancel Reply](../callbacks/C7-cancel-on-submit.md), [C8. Enquiry Reply](../callbacks/C8-enquiry-on-submit.md), [C9. Payer Communication](../callbacks/C9-communication-request.md), [C10. Payment Notice](../callbacks/C10-paymentnotice-request.md)
- FHIR: [F2. CoverageEligibilityRequest](F2-coverage-eligibility-request.md), [F8. Claim](F8-claim.md), [F10. Task (claim actions)](F10-task-claim-actions.md), [F12. Communication](F12-communication.md), [F14. Payment acknowledgement](F14-payment-acknowledgement.md), [F18. Coverage](F18-coverage.md), [F19. Other bundle resources](F19-other-resources.md)
