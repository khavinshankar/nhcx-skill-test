# S6. Policies Screen

#### S6R. ROUTE
`/policies`

| Endpoint | Purpose |
|---|---|
| `GET policies?search=&limit=&offset=` | The products, each with its subscriber count |
| `DELETE policies/:id` | Retire a product |

"Create Policy Product" opens S7 at `/policies/new`; "Edit" opens S7 at `/policies/edit/:id`.

Breadcrumb: Policies

#### S6D. DESCRIPTION
A product is what a hospital's plan request asks about ([C3. Insurance Plan Request](../callbacks/C3-insurance-plan-request.md), [A2. Insurance Plan Answer](../apis/A2-insurance-plan-answer.md)) and what an enrolment is on. The list shows every live product; the configurator S7 edits one. What NHCX adds to a product most payer systems already carry is the UIN and aliases a hospital may quote, the two NDHM type codes, and everything S7 configures for the InsurancePlan.

**Columns**: Policy ID (monospace, `POL<...>` in the reference [REF](../references/PAYERS.md#markers)), Product Name (with the aliases in a smaller line under it), UIN (or "not filed" in italics), Type (the product type display over the plan type display, from the value sets [D4. terminology_code](../database/D4-terminology-code.md)), Status (`active` green, `retired` red, `draft` and `unknown` amber, [D12. policy](../database/D12-policy.md)), Subscribers (a count with a people icon; cover runs per enrolment, not per product, so the row reports how many people are on it rather than a period), Base Sum Insured (`₹`), Actions (Edit, Delete).

**How a plan request finds a product** ([A2. Insurance Plan Answer](../apis/A2-insurance-plan-answer.md)): by the product id, the UIN or an alias, or by an enrolment id an eligibility answer handed out; a retired product's code is answered with the default product [SANDBOX](../references/PAYERS.md#markers); an unknown code is answered with an empty plan.

Search matches name, id and UIN. Count line: "`<n>` policy products". Empty states: "No policy products match" with "Nothing matches "`<term>`". Try a different plan name or ID." and "Clear search"; "No policy products yet" with "Create a policy product to define sum insured limits and tariff rules." and "Create policy product".

**Delete** is refused while anybody is enrolled: "This cannot be removed while other records still refer to it". Toast on success: "Policy product `<id>` deleted".

**The default product** [SANDBOX](../references/PAYERS.md#markers): the reference sandbox runs on one shared product (`SANDBOX-DEFAULT-01`) that every account sees, every enrolment is on, and nobody can edit or remove ("The default policy is shared with every account and cannot be edited or removed"); its row shows no actions. A production payer has no such product.

API: [A2. Insurance Plan Answer](../apis/A2-insurance-plan-answer.md)

Callback: [C3. Insurance Plan Request](../callbacks/C3-insurance-plan-request.md)

Data: [D12. policy](../database/D12-policy.md)

Data: [D13. policy_procedure](../database/D13-policy-procedure.md)

Data: [D16. policy_alias](../database/D16-policy-alias.md)

#### S6L. LAYOUT
The arrangement below is the reference desk's [REF](../references/PAYERS.md#markers): follow the target payer system's own screen conventions. What is required is in DESCRIPTION and ACTIONS: the columns, the statuses, the search and the refusal.

```
|------------------------------------------------------------------|
| Insurance Policy Products              [(+) Create Policy Product]|
| Manage master health insurance policy configurations, sum insured|
|------------------------------------------------------------------|
| [(search) ______________________]         6 policy products      |
|------------------------------------------------------------------|
| Policy ID | Product Name    | UIN   | Type       | Status |      |
| Subscribers | Base Sum Insured | Actions                         |
|-----------|-----------------|-------|------------|--------|------|
| POL7UMV001| Sandbox Default | SANDB | Hospitali- | ACTIVE |      |
|           | Policy          | OX-.. | sation     |        |      |
|           | (aliases...)    |       | Individual |        |      |
| (o) 12    | ₹5,00,000        | [edit] [delete]                   |
|------------------------------------------------------------------|
```

- One primary action in the header; the search and the count share a row.
- A table on wide screens, stacked cards with the same fields on small ones.

#### S6A. ACTIONS
1. Create Policy Product: open the configurator S7 for a new product.
2. Edit: open S7 for that product.
3. Delete: retire the product; refused while enrolments exist.
4. Search: narrow by name, id or UIN; "Clear search" resets it.
