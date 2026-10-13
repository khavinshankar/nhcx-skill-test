# L2. Mapping

#### L2G. GOAL
Map every field the specs need to where it lives in the target payer system, and to the FHIR element it feeds or is read from. The result says, for each D column and each F element: take it from here, transform it like this, or it does not exist yet.

#### L2I. INPUTS
- `nhcx-plan/discovery.json` (entities, found tables and models).
- The knowledge source: `get_atom` and `get_fhir_profile` (MCP), or `mappings/` and `docs/05-FHIR Reference/` (package), for where each data element sits and which code systems apply.
- [database](../database/INDEX.md) columns (DnC), [fhir](../fhir/INDEX.md) fields (FnF), and the screen fields that feed them (SnD, SnL).

### L2.1 Map master data (D1 to D4)
For the payer's own record, staff roles, document types and terminology: pair each spec column with the target's table and column. Pay attention to the identifiers NHCX needs: the payer's participant code and processing code, IRDAI registration and ROHINI id (D1); the NHCX document taxonomy a case document is filed under (D3); the plan type and SNOMED code sets the plan is written in (D4).

### L2.2 Map members and enrolments (D5 to D9)
Member with the ABHA number the exchange matches on (D5); the enrolment with its cover period, wallet balance and status (D6); dependants (D7); the wallet ledger (D8); ABHA link attempts (D9). Note how the target marks cover as in force today and how it keeps what is left of the sum assured.

### L2.3 Map products and procedures (D10 to D18)
The procedure registry with package rate, treatment-guideline questions and document rules per phase (D10, D11); the product with UIN, plan type and sum assured (D12) and its covered procedures, coverage clauses, benefits, aliases, exclusions and sub-limits (D13 to D18). These feed the InsurancePlan (F5) and the ruling (F3); record where the target keeps tariffs and coverage wording today.

### L2.4 Map case and payment data (D19 to D32)
Most case tables are new in a target without NHCX. Mark each as `new`, or pair it with an existing claim, intimation or settlement table when one exists. Record where the target keeps the hospital's claim number, the adjudication decision per line, documents, disbursements and UTRs today.

### L2.5 Map FHIR elements (F15 to F18 first, then F3, F5, F6, F9, F10, F11, F13, F14)
For each element in FnF that the application fills, name its source: a D column (spec side) and the target column it comes from, or a constant. For each element the application reads (F2, F4, F7, F8, F10 received side, F12, F13 enquiry, F16, F19), name the D column it lands in.

### L2.6 Map code systems
ICD-10, SNOMED (coverage clauses, benefits, sub-limits), the package codes this payer publishes, document type codes, plan and insurance plan type codes, gender and relationship codes. For each, record whether the target stores the code, only a display text, or nothing, and what transform or lookup is needed.

### L2.7 Mark gaps and conflicts
A field the target does not hold is `missing` with the proposed fix (new column, new form field on which screen). A field held with a different meaning or type is `conflict` with the resolution.

#### L2O. OUTPUT
`nhcx-plan/mapping.json`:

```json
{
  "fields": [
    {
      "spec": "D5.abha_no",
      "fhir": ["F15:identifier[].value"],
      "target": {"table": "", "column": "", "file": "", "lines": ""},
      "transform": "digits only, 14 characters",
      "status": "mapped | new | missing | conflict",
      "resolution": "",
      "screens": ["S4"]
    }
  ],
  "codes": [
    {"system": "ICD-10", "spec": ["D20.code", "F8:diagnosis[].diagnosisCodeableConcept"],
     "target": {"table": "", "column": ""}, "status": "mapped | lookup | missing", "notes": ""}
  ],
  "tables": [
    {"spec": "D19", "status": "new | existing | extend", "target_table": ""}
  ],
  "corrections": []
}
```

#### L2L. LOG
Record in `nhcx-plan/progress.json` and regenerate `nhcx-plan/progress.md`, as [LOG.md](LOG.md) describes. One entry per sub-step, with the D and F ids it mapped. L2.7 logs each `missing` or `conflict` it recorded, and every write to `nhcx-plan/mapping.json`.

#### L2X. EXIT
- Every column in D1 to D32 and every application-filled element in the F specs has an entry.
- No entry is `mapped` without a target location.
- Every `missing` and `conflict` has a resolution that L3 can turn into work.
- Every sub-step of L2 has its `started` and closing entries in progress.json, and every file changed is named in one.
