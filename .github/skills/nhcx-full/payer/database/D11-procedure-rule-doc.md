# D11. procedure_rule_doc

#### D11T. TABLE
One row is one document a procedure ([D10. procedure_rule](D10-procedure-rule.md)) wants at one phase of the claim; primary key `(procedure_id, phase, doc_code)`. Parent tables [D10. procedure_rule](D10-procedure-rule.md) and [D3. document_type](D3-document-type.md). The reference implementation names it `payer_procedure_rule_docs` [REF](../references/PAYERS.md#markers).

#### D11D. DESCRIPTION
One row per (procedure, phase, document), so "is the pre-authorisation dossier complete" is a join rather than a walk over a JSON blob. The same document may be demanded at pre-authorisation and again at claim; listing it twice in one phase says nothing extra, and the key forbids it.

What NHCX reads from the rows:
- The InsurancePlan ([F5. InsurancePlan](../fhir/F5-insuranceplan.md)) carries each covered procedure's documents per phase as supporting-information requirements, with the document's name and NDHM category from [D3. document_type](D3-document-type.md).
- An auth-requirements ruling ([F3. CoverageEligibilityResponse](../fhir/F3-coverage-eligibility-response.md), [A1. Eligibility Answer](../apis/A1-eligibility-answer.md)) lists, per quoted package, the documents due at each stage, the `pre` ones in the dialect the hospital reads as due at pre-authorisation [PAYER](../references/PAYERS.md#markers).
- The treatment-guideline form of a procedure with no `stg_questions` ([F6. Questionnaire](../fhir/F6-questionnaire.md)) asks one yes/no question per `preauth` document here.

Phases, exact strings: `preauth`, `discharge`, `claim`. `required` false marks a document the plan lists as optional.

Create, update, delete:
- Written with the procedure ([S9. Procedure Configurator](../screens/S9-procedure-configurator.md)): deleted and rewritten in the procedure's transaction, in the order given per phase. A `doc_code` not in [D3. document_type](D3-document-type.md) is refused ("invalid reference"). Cascades with the procedure.

#### D11C. COLUMNS
| column | type | null/default | meaning (and allowed values) |
|---|---|---|---|
| procedure_id | VARCHAR(32) | primary key part | the procedure ([D10. procedure_rule](D10-procedure-rule.md)) |
| phase | VARCHAR(32) | primary key part | `preauth`, `discharge`, `claim` |
| doc_code | VARCHAR(24) | primary key part | the document type ([D3. document_type](D3-document-type.md)) |
| required | BOOLEAN | NOT NULL, default true | whether the document is mandatory at that phase |
| position | INTEGER | NOT NULL, default 0 | order within the phase |

#### D11K. KEYS AND INDEXES
- Primary key `(procedure_id, phase, doc_code)`.
- Foreign keys: `procedure_id` references [D10. procedure_rule](D10-procedure-rule.md) `id` (`ON DELETE CASCADE`); `doc_code` references [D3. document_type](D3-document-type.md) `code` (`ON DELETE RESTRICT`).
- Check `ck_procedure_docs_phase`.
- Indexes: `idx_procedure_docs_order` on `(procedure_id, phase, position)`; `idx_procedure_docs_code` on `doc_code`.

#### D11U. USED BY
- Screens: [S8. Procedures](../screens/S8-procedures.md), [S9. Procedure Configurator](../screens/S9-procedure-configurator.md)
- APIs: [A1. Eligibility Answer](../apis/A1-eligibility-answer.md), [A2. Insurance Plan Answer](../apis/A2-insurance-plan-answer.md), [A10. Predetermination Quote](../apis/A10-predetermination-quote.md)
- Callbacks: [C2. Coverage Eligibility Check](../callbacks/C2-coverage-eligibility-check.md)
- FHIR: [F3. CoverageEligibilityResponse](../fhir/F3-coverage-eligibility-response.md), [F5. InsurancePlan](../fhir/F5-insuranceplan.md), [F6. Questionnaire](../fhir/F6-questionnaire.md)
- Database: [D3. document_type](D3-document-type.md), [D10. procedure_rule](D10-procedure-rule.md), [D13. policy_procedure](D13-policy-procedure.md)
