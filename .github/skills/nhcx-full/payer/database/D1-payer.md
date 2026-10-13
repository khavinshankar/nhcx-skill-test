# D1. payer

#### D1T. TABLE
One row is the insurer this deployment belongs to; primary key `id`. One row in practice: a table so the payer on every screen and every bundle has somewhere to come from. No parent table. The reference implementation names it `payer_payers` [REF](../references/PAYERS.md#markers).

#### D1D. DESCRIPTION
The payer's own record. It is the payer Organization ([F17. Organization](../fhir/F17-organization.md)) on every bundle this system sends, the `x-hcx-sender_code` of every answer ([A1. Eligibility Answer](../apis/A1-eligibility-answer.md) to [A10. Predetermination Quote](../apis/A10-predetermination-quote.md)), and the `payerid` on an ABHA policy link ([A16. ABHA Policy Link](../apis/A16-abha-policy-link.md)).

Create:
- Written once when the deployment is set up (the reference seeds it at first boot with a name, a code, a city and a state [REF](../references/PAYERS.md#markers)). Only `id`, `name` and `code` are required.

Update:
- Edited from the Organisation screen ([S12. Organisation](../screens/S12-organisation.md)) through `PATCH payer`: every column but `id` and `created_at`. The participant codes are stored the way the exchange spells them, with the `@hcx` suffix added when it was left off, so what the screen shows is what goes on the wire. A `code` already taken by another row is refused with "That payer code is already registered".

Read:
- Every outbound answer reads this row for the sender code and the Organization. `nhcx_participant_id` empty falls back to the gateway's configured default participant ([G2. Configuration and Participants](../gateway/G2-configuration.md)); `nhcx_processing_id` empty means the payer processes its own claims.
- The cases a signed-in account sees are those addressed to a participant code it works; the deployment's own code here is the default when an account names none [SANDBOX](../references/PAYERS.md#markers).

Delete:
- Never.

#### D1C. COLUMNS
| column | type | null/default | meaning (and allowed values) |
|---|---|---|---|
| id | VARCHAR(32) | primary key | the payer's row id |
| name | VARCHAR(160) | NOT NULL | the insurer's name, `Organization.name` on every bundle |
| code | CITEXT, at most 64 | NOT NULL, UNIQUE | this deployment's own label for the insurer; goes on no wire |
| irdai_registration | VARCHAR(64) | null | IRDAI registration number, an identifier on the payer Organization |
| rohini_id | VARCHAR(64) | null | ROHINI id, an identifier on the payer Organization |
| nhcx_participant_id | CITEXT, at most 64 | null | the payer's NHCX participant code, `<payer code>` form; empty falls back to the gateway's default participant |
| nhcx_processing_id | CITEXT, at most 64 | null | the participant that processes this payer's claims (a TPA, or the payer itself); empty means `nhcx_participant_id` |
| phone | VARCHAR(32) | null | contact telephone, `Organization.telecom` |
| email | VARCHAR(190) | null | contact email |
| address_line | VARCHAR(300) | null | street address |
| city | VARCHAR(80) | null | city |
| state | VARCHAR(80) | null | state |
| pincode | VARCHAR(12) | null | postal code |
| country | VARCHAR(80) | NOT NULL, default `'India'` | country |
| created_at | TIMESTAMPTZ | NOT NULL, default now | when the row was written |

#### D1K. KEYS AND INDEXES
- Primary key `id`.
- Unique `uq_payers_code` on `code`.
- Checks: `code` at most 64 characters; `nhcx_participant_id` and `nhcx_processing_id` at most 64 characters each.
- Referenced by [D2. staff](D2-staff.md) `payer_id` (`ON DELETE RESTRICT`).

#### D1U. USED BY
- Screens: [S12. Organisation](../screens/S12-organisation.md)
- APIs: [A1. Eligibility Answer](../apis/A1-eligibility-answer.md), [A2. Insurance Plan Answer](../apis/A2-insurance-plan-answer.md), [A3. Pre-auth Answer](../apis/A3-preauth-answer.md), [A4. Claim Answer](../apis/A4-claim-answer.md), [A5. Query Request](../apis/A5-query-request.md), [A6. Payment Notice](../apis/A6-payment-notice.md), [A7. Payment Enquiry Answer](../apis/A7-payment-enquiry-answer.md), [A8. Status Answer](../apis/A8-status-answer.md), [A9. Task Answer](../apis/A9-task-answer.md), [A12. Transaction FHIR](../apis/A12-txn-fhir.md), [A15. Case Exchange Log](../apis/A15-case-exchange.md), [A16. ABHA Policy Link](../apis/A16-abha-policy-link.md), [A17. Participant Lookup](../apis/A17-participant-lookup.md)
- Callbacks: [C1. Callback Door](../callbacks/C1-callback-door.md)
- FHIR: [F1. Bundle](../fhir/F1-bundle.md), [F5. InsurancePlan](../fhir/F5-insuranceplan.md), [F9. ClaimResponse](../fhir/F9-claimresponse.md), [F10. Task (claim actions and answers)](../fhir/F10-task-claim-actions.md), [F17. Organization](../fhir/F17-organization.md)
- Database: [D2. staff](D2-staff.md)
