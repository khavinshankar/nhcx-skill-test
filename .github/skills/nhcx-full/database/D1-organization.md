# D1. organization

#### D1T. TABLE
One row is the healthcare facility this installation represents; primary key `id`; no parent table.

#### D1D. DESCRIPTION
The facility row is the provider on every NHCX message. Its `participant_code` is the `x-hcx-sender_code` on every outbound send. Its `identifier_value` (the HFR / facility ID) is the `providerId` on the eligibility check, the InsurancePlan discovery Task and the pre-auth and claim bundles. `name` and `phone` fill the provider Organization.

Lifecycle:
- Created once, by seeding, when the table is empty. The seeded row has `is_default = 1`, `type_code = 'prov'` and no `participant_code`.
- The application reads "the facility" as the first row ordered by `is_default DESC, id`. No screen adds a second row.
- Updated from the facility settings screen: every column except `id` and `is_default` is overwritten on save. `name` and `identifier_value` are required. `identifier_type_code` defaults to `NHRR`, `identifier_system` to `https://facility.abdm.gov.in`, `type_code` to `prov`, `country` to `India`.
- Never deleted. It is a master table and survives the "clear transactional data" reset.

Guards that read it:
- The eligibility check refuses to send while `identifier_value` is blank ("Set the facility's HFR ID under Settings before raising claims.") or `participant_code` is blank ("Set the facility's NHCX participant code under Settings before raising claims."). The InsurancePlan request refuses the same way, ending "before fetching a package master." instead.
- The session token call (A16, served by [G3. Session Token](../gateway/G3-session-token.md)) and the payer adjudication calls (A15) use `participant_code` to name the participant.

Payers are not rows in this table. A claim carries its payer on [D9. claim](D9-claim.md) (`payer_id`, `payer_name`), and the payer's participant code is mapped to a payer adapter by the `payer_adapter` kind of [D8. terminology](D8-terminology.md).

#### D1C. COLUMNS
| column | type | null/default | meaning (and allowed values) |
|---|---|---|---|
| id | INTEGER | primary key | row id |
| name | TEXT | NOT NULL | facility name; Organization.name |
| identifier_type_system | TEXT | NOT NULL | code system of the identifier type (NDHM identifier type code system, or HL7 v2-0203) |
| identifier_type_code | TEXT | NOT NULL | identifier type: `NHRR`, `ROHINI`, `PMJAY`, `OIN`, `PRN` |
| identifier_type_display | TEXT | NOT NULL | display for the type, for example "National Health Resource Repository (NHRR) ID" |
| identifier_system | TEXT | NOT NULL | identifier namespace; default on save `https://facility.abdm.gov.in` |
| identifier_value | TEXT | NOT NULL | the HFR / facility ID; sent as `providerId` |
| participant_code | TEXT | null | the facility's NHCX participant code; `x-hcx-sender_code` on every send. Added by migration on older databases |
| type_code | TEXT | NOT NULL, default `'prov'` | HL7 organization-type: `prov`, `dept`, `team`, `ins`, `other` |
| type_display | TEXT | NOT NULL, default `'Healthcare Provider'` | display of `type_code` |
| phone | TEXT | null | facility phone; provider telecom on the eligibility check |
| email | TEXT | null | facility email |
| address_line | TEXT | null | street address |
| city | TEXT | null | city |
| district | TEXT | null | district |
| state | TEXT | null | Indian state or union territory name |
| postal_code | TEXT | null | PIN code |
| country | TEXT | NOT NULL, default `'India'` | country |
| gstin | TEXT | null | GST number (billing only) |
| is_default | INTEGER | NOT NULL, default `0` | `1` marks the facility row the application uses |

#### D1K. KEYS AND INDEXES
- Primary key `id` (integer).
- No foreign keys out.
- Referenced by [D3. patient](D3-patient.md) `managing_org_id`, and by EMR tables outside this spec (lab and invoice issuers).
- No unique constraints or indexes beyond the primary key.

#### D1U. USED BY
- APIs: [A12. Transaction FHIR](../apis/A12-txn-fhir.md), [A14. Adjudicator User Role](../apis/A14-adjudicator-user-role.md), [A15. Adjudicator Process Case](../apis/A15-adjudicator-process-case.md), [A16. Gateway Token](../apis/A16-gateway-token.md)
- FHIR: [F2. CoverageEligibilityRequest](../fhir/F2-coverage-eligibility-request.md), [F4. Task (InsurancePlan discovery)](../fhir/F4-task-insuranceplan.md), [F14. Payment acknowledgement](../fhir/F14-payment-acknowledgement.md), [F17. Organization](../fhir/F17-organization.md), [F19. Other bundle resources](../fhir/F19-other-resources.md)
- Database: [D3. patient](D3-patient.md), [D10. claim_plan](D10-claim-plan.md)
- Tests: [T1. Test Configuration](../tests/T1-test-configuration.md)
