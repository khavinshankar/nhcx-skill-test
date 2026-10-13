# S8. Procedures Screen

#### S8R. ROUTE
`/procedures`

| Endpoint | Purpose |
|---|---|
| `GET procedures?search=&category=&limit=&offset=` | The registry |
| `DELETE procedures/:id` | Remove a procedure |

"Add Procedure" opens S9 at `/procedures/new`; a row or "Edit" opens S9 at `/procedures/edit/:id`.

Breadcrumb: Procedures

#### S8D. DESCRIPTION
The procedure master. A product names the procedures it covers and inherits their rules (S7, [D13. policy_procedure](../database/D13-policy-procedure.md)); the rules themselves live here, once ([D10. procedure_rule](../database/D10-procedure-rule.md), [D11. procedure_rule_doc](../database/D11-procedure-rule-doc.md)). Three things on a procedure reach the exchange: its **package rate**, which the InsurancePlan quotes under the package and an auth-requirements ruling allows per item ([A2. Insurance Plan Answer](../apis/A2-insurance-plan-answer.md), [A1. Eligibility Answer](../apis/A1-eligibility-answer.md)); its **document rules per phase** (pre-auth, discharge, claim), which the plan publishes and the ruling names; and its **treatment-guideline questions**, which become the questionnaire the plan hangs off the package ([F6. Questionnaire](../fhir/F6-questionnaire.md)). The code is also what a hospital's line items and predeterminations are matched on ([C6. Predetermination](../callbacks/C6-predetermination.md), [A10. Predetermination Quote](../apis/A10-predetermination-quote.md)).

**Columns**: Procedure Code (monospace; the code is the id), Procedure Name, Category (Surgical, Medical, Emergency, Day Care, Diagnostic, Critical Care), SNOMED CT (or "Unmapped" in italics), ICD-10-PCS (PCS10) (or "Unmapped"), Package Rate (`₹` right-aligned, or "Unpriced": null is "not priced", which is not the same as free), Docs (a badge "`<n>` docs", the count across the three phases), Actions (Edit, Delete).

**Filters**: search matches name, code, SNOMED and PCS10; a category select (All Categories and the six). Count line: "`<n>` procedures". Empty: "No procedures match" with "No procedure in the catalog matches the current search or category filter." and "Clear filters".

**Delete** confirms "Delete procedure?": ""`<name>`" and its stage-wise document rules will be removed from the master catalog." It is refused while a product still covers it: "This cannot be removed while other records still refer to it", so cover cannot vanish from a plan without somebody deciding it should. Toast: "Procedure "`<name>`" removed".

The registry is global: it has no owner even in the reference sandbox [SANDBOX](../references/PAYERS.md#markers).

API: [A1. Eligibility Answer](../apis/A1-eligibility-answer.md)

API: [A2. Insurance Plan Answer](../apis/A2-insurance-plan-answer.md)

Data: [D10. procedure_rule](../database/D10-procedure-rule.md)

Data: [D11. procedure_rule_doc](../database/D11-procedure-rule-doc.md)

Data: [D13. policy_procedure](../database/D13-policy-procedure.md)

#### S8L. LAYOUT
The arrangement below is the reference desk's [REF](../references/PAYERS.md#markers): follow the target payer system's own screen conventions. What is required is in DESCRIPTION and ACTIONS: the columns, the filters and the refusal.

```
|------------------------------------------------------------------|
| Clinical Procedures                             [(+) Add Procedure]|
| Catalog of standardized clinical procedure master definitions    |
|------------------------------------------------------------------|
| [(search) ____________________]  [All Categories v]  5 procedures|
|------------------------------------------------------------------|
| Procedure Code | Procedure Name | Category | SNOMED CT | PCS10 | |
| Package Rate | Docs | Actions                                    |
|----------------|----------------|----------|-----------|-------|-|
| PROC-KNEE-01   | Total Knee     | Surgical | 609588000 | 0SRC0J9|
|                | Replacement    |          |           |        |
| ₹1,50,000 | [8 docs] | [edit] [delete]                          |
|------------------------------------------------------------------|
```

- One primary action in the header; the search, the category select and the count share a row.
- Rows are clickable and open the configurator; the actions repeat that at the right.
- A table on wide screens, cards with badges (category, SNOMED, PCS10, rate, docs) on small ones.

#### S8A. ACTIONS
1. Add Procedure: open the configurator S9 for a new procedure.
2. Row or Edit: open S9 for that procedure.
3. Delete: confirm, then remove; refused while a product covers it.
4. Search and Category: narrow the list; "Clear filters" resets both.
