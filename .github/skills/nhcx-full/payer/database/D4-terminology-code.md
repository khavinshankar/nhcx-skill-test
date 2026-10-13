# D4. terminology_code

#### D4T. TABLE
One row is one code of one published value set, with the display the code system gives it; primary key `(system_url, code)`. No parent table. The reference implementation names it `payer_terminology_codes` [REF](../references/PAYERS.md#markers).

#### D4D. DESCRIPTION
The code registry. Nothing in the system writes a code system's display text by hand: the configurators ([S7. Policy Configurator](../screens/S7-policy-configurator.md), [S9. Procedure Configurator](../screens/S9-procedure-configurator.md)) offer what is here, the policy read resolves its codes through it, and the FHIR renderers ([F5. InsurancePlan](../fhir/F5-insuranceplan.md), [F3. CoverageEligibilityResponse](../fhir/F3-coverage-eligibility-response.md)) emit what the policy resolved to. A display shown to an underwriter and a display written into a bundle cannot differ.

The value sets held [REF](../references/PAYERS.md#markers):

| System | Used for |
|---|---|
| `https://nrces.in/ndhm/fhir/r4/CodeSystem/ndhm-insuranceplan-type` | [D12. policy](D12-policy.md) `type_code` |
| `https://nrces.in/ndhm/fhir/r4/CodeSystem/ndhm-plan-type` | [D12. policy](D12-policy.md) `plan_type_code`, [D6. subscription](D6-subscription.md) `plan_type_code` |
| `https://nrces.in/ndhm/fhir/r4/CodeSystem/ndhm-claim-exclusion` | [D17. policy_exclusion](D17-policy-exclusion.md) `code` |
| `https://nrces.in/ndhm/fhir/r4/CodeSystem/ndhm-supportinginfo-category` | [D3. document_type](D3-document-type.md) `si_category` |
| `http://snomed.info/sct` | [D14. policy_coverage_clause](D14-policy-coverage-clause.md), [D15. policy_clause_benefit](D15-policy-clause-benefit.md), [D18. policy_sub_limit](D18-policy-sub-limit.md) concepts |
| a curated sub-limit category set | the concepts a sub-limit ([D18. policy_sub_limit](D18-policy-sub-limit.md)) is written against, so the picker has something to offer without the whole of SNOMED |

Create and update:
- Loaded by the seed at boot from the knowledge source's code systems; upserted on `(system_url, code)`, because published value sets gain codes between releases, so a duplicate overwrites rather than refuses.
- Read through `GET terminology?system=` by the configurators. An unknown system is an empty list, not an error.

Resolving a display:
- A code the registry does not carry resolves to an empty display, which the plan preview ([S11. FHIR Preview](../screens/S11-fhir-preview.md)) reports as an issue rather than papering over.

Delete:
- Never.

#### D4C. COLUMNS
| column | type | null/default | meaning (and allowed values) |
|---|---|---|---|
| system_url | VARCHAR(200) | primary key part | the code system's canonical URL |
| code | VARCHAR(64) | primary key part | the code |
| display | VARCHAR(300) | NOT NULL | the display the code system publishes |
| position | INTEGER | NOT NULL, default 0 | the order the picker offers the codes in |

#### D4K. KEYS AND INDEXES
- Primary key `(system_url, code)`.
- Index `idx_terminology_order` on `(system_url, position, code)`.
- Not referenced by a foreign key: [D12. policy](D12-policy.md), [D14. policy_coverage_clause](D14-policy-coverage-clause.md), [D15. policy_clause_benefit](D15-policy-clause-benefit.md), [D17. policy_exclusion](D17-policy-exclusion.md) and [D18. policy_sub_limit](D18-policy-sub-limit.md) hold the code and resolve it at read time.

#### D4U. USED BY
- Screens: [S5. Subscriptions](../screens/S5-subscriptions.md), [S6. Policies](../screens/S6-policies.md), [S7. Policy Configurator](../screens/S7-policy-configurator.md)
- FHIR: [F5. InsurancePlan](../fhir/F5-insuranceplan.md)
- Database: [D6. subscription](D6-subscription.md), [D12. policy](D12-policy.md), [D14. policy_coverage_clause](D14-policy-coverage-clause.md), [D15. policy_clause_benefit](D15-policy-clause-benefit.md), [D17. policy_exclusion](D17-policy-exclusion.md), [D18. policy_sub_limit](D18-policy-sub-limit.md)
