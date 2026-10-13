# Database

The tables behind the desk, registry, configuration and payment screens. Screens (S), APIs (A) and callbacks (C) refer to these by D number. Each file has TABLE (T), DESCRIPTION (D), COLUMNS (C), KEYS AND INDEXES (K) and USED BY (U) sections.

D1 to D18 are tables most payer systems already have: the insurer's own record, staff and roles, the document taxonomy, members, enrolments and their wallets, products and the procedures they cover. They are extended only where NHCX needs a column (the participant codes on the payer, the ABHA number and link state on an enrolment, the package rate, treatment-guideline questions and per-phase document rules on a procedure, the SNOMED clauses and exclusions the InsurancePlan is rendered from). D19 to D32 are new for the exchange: the case and its children, the messages and deliveries, the quotes, the payments and the numbering.

Table names are written without the reference implementation's `payer_` prefix [REF](../references/PAYERS.md#markers). Primary keys are the business identifiers the desk reads out (a case id, a claim number, a payment number), allocated from [D32. id_sequence](D32-id-sequence.md) so the prefix and width are decided in one place [REF](../references/PAYERS.md#markers). Child rows that are never quoted (line items, documents, timeline entries) take short random ids [REF](../references/PAYERS.md#markers). Money is a fixed-point decimal with two places; timestamps carry a time zone and are stored in UTC.

## Master data

| # | Table | What one row is | File |
|---|---|---|---|
| [D1](D1-payer.md) | payer | The insurer this deployment is: name, IRDAI registration, ROHINI id, NHCX participant and processing codes, contact details. | [D1-payer.md](D1-payer.md) |
| [D2](D2-staff.md) | staff | A desk account's half: which payer it works for and its role (adjudicator decides, finance disburses, admin both). | [D2-staff.md](D2-staff.md) |
| [D3](D3-document-type.md) | document_type | The NHCX document taxonomy a policy may demand and a case document is filed under. | [D3-document-type.md](D3-document-type.md) |
| [D4](D4-terminology-code.md) | terminology_code | The published value sets the configurator picks codes from (plan types, SNOMED clauses, categories). | [D4-terminology-code.md](D4-terminology-code.md) |
| [D31](D31-audit-log.md) | audit_log | Every write and every exchange receipt, by whom and when. | [D31-audit-log.md](D31-audit-log.md) |

## Members and enrolments

| # | Table | What one row is | File |
|---|---|---|---|
| [D5](D5-member.md) | member | One beneficiary: name, gender, date of birth, mobile, ABHA number. | [D5-member.md](D5-member.md) |
| [D6](D6-subscription.md) | subscription | One enrolment of a member on a product: cover period, wallet balance, status, ABHA link state. | [D6-subscription.md](D6-subscription.md) |
| [D7](D7-subscription-family-member.md) | subscription_family_member | A dependant on a family floater. | [D7-subscription-family-member.md](D7-subscription-family-member.md) |
| [D8](D8-wallet-entry.md) | wallet_entry | One movement of an enrolment's wallet with the balance after it. | [D8-wallet-entry.md](D8-wallet-entry.md) |
| [D9](D9-abha-link-event.md) | abha_link_event | One link or delink attempt at ABDM, whatever it did. | [D9-abha-link-event.md](D9-abha-link-event.md) |

## Products and procedures

| # | Table | What one row is | File |
|---|---|---|---|
| [D10](D10-procedure-rule.md) | procedure_rule | One procedure in the registry: codes, category, package rate, treatment-guideline questions. | [D10-procedure-rule.md](D10-procedure-rule.md) |
| [D11](D11-procedure-rule-doc.md) | procedure_rule_doc | Which document a procedure wants at which phase. | [D11-procedure-rule-doc.md](D11-procedure-rule-doc.md) |
| [D12](D12-policy.md) | policy | One product: name, UIN, type, plan type, sum assured, status. | [D12-policy.md](D12-policy.md) |
| [D13](D13-policy-procedure.md) | policy_procedure | A procedure a policy covers. | [D13-policy-procedure.md](D13-policy-procedure.md) |
| [D14](D14-policy-coverage-clause.md) | policy_coverage_clause | A SNOMED coverage clause of a policy. | [D14-policy-coverage-clause.md](D14-policy-coverage-clause.md) |
| [D15](D15-policy-clause-benefit.md) | policy_clause_benefit | A benefit under a clause, with its limit. | [D15-policy-clause-benefit.md](D15-policy-clause-benefit.md) |
| [D16](D16-policy-alias.md) | policy_alias | An alternate name a product is filed under. | [D16-policy-alias.md](D16-policy-alias.md) |
| [D17](D17-policy-exclusion.md) | policy_exclusion | A standard exclusion clause of a policy. | [D17-policy-exclusion.md](D17-policy-exclusion.md) |
| [D18](D18-policy-sub-limit.md) | policy_sub_limit | A sub-limit of a policy on one concept. | [D18-policy-sub-limit.md](D18-policy-sub-limit.md) |

## Case

| # | Table | What one row is | File |
|---|---|---|---|
| [D19](D19-case.md) | case | One claim dossier from pre-authorisation to settlement: patient snapshot, hospital, admission, stage, totals, adjudication, and the exchange routing slips of the pre-auth, claim, query and reprocess threads. | [D19-case.md](D19-case.md) |
| [D20](D20-case-diagnosis.md) | case_diagnosis | A diagnosis on a case, at most one primary. | [D20-case-diagnosis.md](D20-case-diagnosis.md) |
| [D21](D21-case-procedure.md) | case_procedure | A procedure on a case as the hospital coded it. | [D21-case-procedure.md](D21-case-procedure.md) |
| [D22](D22-case-doctor.md) | case_doctor | A member of the treating team by HPR id, one primary. | [D22-case-doctor.md](D22-case-doctor.md) |
| [D23](D23-case-document.md) | case_document | A document on a case: code, phase, type, where the bytes are. | [D23-case-document.md](D23-case-document.md) |
| [D24](D24-case-document-file.md) | case_document_file | The bytes of a document that arrived inline. | [D24-case-document-file.md](D24-case-document-file.md) |
| [D25](D25-case-line-item.md) | case_line_item | One bill line with its claimed and approved amounts and its decision, the round it arrived in. | [D25-case-line-item.md](D25-case-line-item.md) |
| [D26](D26-case-timeline.md) | case_timeline | One event on the case's trail. | [D26-case-timeline.md](D26-case-timeline.md) |

## Exchange

| # | Table | What one row is | File |
|---|---|---|---|
| [D27](D27-case-exchange-message.md) | case_exchange_message | One message about a case, in or out, with its bundle. | [D27-case-exchange-message.md](D27-case-exchange-message.md) |
| [D28](D28-nhcx-delivery.md) | nhcx_delivery | One delivery taken in, keyed by api call id, so a redelivery is refused. | [D28-nhcx-delivery.md](D28-nhcx-delivery.md) |
| [D29](D29-predetermination-quote.md) | predetermination_quote | One predetermination priced and answered. | [D29-predetermination-quote.md](D29-predetermination-quote.md) |

## Payments

| # | Table | What one row is | File |
|---|---|---|---|
| [D30](D30-payment.md) | payment | One disbursement against a case: amount, TDS, net, mode, beneficiary, UTR, status, notice transaction and acknowledgement. | [D30-payment.md](D30-payment.md) |

## Numbering

| # | Table | What one row is | File |
|---|---|---|---|
| [D32](D32-id-sequence.md) | id_sequence | The next number of each human-readable id series. | [D32-id-sequence.md](D32-id-sequence.md) |
