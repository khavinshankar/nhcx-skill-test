# Screens

Each file has ROUTE (R), DESCRIPTION (D), LAYOUT (L) and ACTIONS (A) sections. DESCRIPTION and ACTIONS are required behaviour; LAYOUT is the reference desk's arrangement [REF](../references/PAYERS.md#markers) and follows the target payer system's own conventions. S4 to S9 are screens most payer systems already have (members, enrolments, products, procedures): only their NHCX additions are built, which are the fields and rules the exchange answers from.

## Desk

| # | Screen | Route | File |
|---|---|---|---|
| [S1](S1-overview.md) | Overview | `/` | [S1-overview.md](S1-overview.md) |
| [S2](S2-cases.md) | Cases | `/cases` | [S2-cases.md](S2-cases.md) |
| [S3](S3-case-desk.md) | Case Desk | `/cases/:id` | [S3-case-desk.md](S3-case-desk.md) |

## Registry

| # | Screen | Route | File |
|---|---|---|---|
| [S4](S4-members.md) | Members | `/members` | [S4-members.md](S4-members.md) |
| [S5](S5-subscriptions.md) | Subscriptions | `/subscriptions` | [S5-subscriptions.md](S5-subscriptions.md) |

## Configuration

| # | Screen | Route | File |
|---|---|---|---|
| [S6](S6-policies.md) | Policies | `/policies` | [S6-policies.md](S6-policies.md) |
| [S7](S7-policy-configurator.md) | Policy Configurator | `/policies/new`, `/policies/edit/:id` | [S7-policy-configurator.md](S7-policy-configurator.md) |
| [S8](S8-procedures.md) | Procedures | `/procedures` | [S8-procedures.md](S8-procedures.md) |
| [S9](S9-procedure-configurator.md) | Procedure Configurator | `/procedures/new`, `/procedures/edit/:id` | [S9-procedure-configurator.md](S9-procedure-configurator.md) |
| [S11](S11-fhir-preview.md) | FHIR Preview | `/fhir` | [S11-fhir-preview.md](S11-fhir-preview.md) |
| [S12](S12-organisation.md) | Organisation | `/organisation` | [S12-organisation.md](S12-organisation.md) |

## Finance

| # | Screen | Route | File |
|---|---|---|---|
| [S10](S10-payments.md) | Payments | `/payments` | [S10-payments.md](S10-payments.md) |

## Flow

S1 Overview, then S2 Cases, then S3 the case desk, which carries one case from the pre-authorisation a hospital sent to settlement: filing, per-line decisions, the verdict, queries and their replies, the claim, reprocessing. S10 Payments is the money: raising a disbursement against an approved case, recording the UTR, and the notices that tell the hospital. The registry screens (S4 Members, S5 Subscriptions) and the configuration screens (S6 to S9, S12) hold what the exchange answers from: an eligibility check is answered from an enrolment, a plan request from a product and its procedures, and every bundle names the payer of S12. S11 shows what any of them would put on the wire right now.

Screens this skill does not hold are specified in the skill named beside them.

## Left out on purpose

The reference desk also has a sandbox integration checklist (what a hospital's traffic has proved, ticked by the exchange) and a flow console that stands in for a hospital on the exchange. Both are sandbox tooling for integrators testing against this payer, not part of a payer system, and are not specified here [SANDBOX](../references/PAYERS.md#markers). Sign-in, sign-up with an ABDM token and the account screens are the target's own.
