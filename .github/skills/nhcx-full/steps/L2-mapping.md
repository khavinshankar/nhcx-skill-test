# L2. Mapping

#### L2G. GOAL
Map every field the specs need to where it lives in the target HMIS, and to the FHIR element it feeds. The result says, for each D column and each F element: take it from here, transform it like this, or it does not exist yet.

#### L2I. INPUTS
- `nhcx-plan/discovery.json` (entities, found tables and models).
- The knowledge source: `get_atom` and `get_fhir_profile` (MCP), or `mappings/` and `docs/05-FHIR Reference/` (package), for where each data element sits and which code systems apply.
- [database](../database/INDEX.md) columns (DnC), [fhir](../fhir/INDEX.md) fields (FnF), and the screen fields that feed them (SnD, SnL).

### L2.1 Map master data (D1, D2, D3, D8)
For facility, practitioner, patient and code lists: pair each spec column with the target's table and column. Pay attention to the identifiers NHCX needs: ABHA number and address (D3), HPR id, registration number and qualification (D2), HFR id and participant code (D1).

### L2.2 Map clinical and admission data (D4, D5)
Admission or encounter, dates, ward, treating doctor, diagnoses with ICD-10 codes. Note how the target marks an admission as current and how it stores diagnosis codes.

### L2.3 Map claim data (D9 to D30)
Most claim tables are new in a target without NHCX. Mark each as `new`, or pair it with an existing insurance or TPA table when one exists. Record where the target keeps policy, payer and member id today.

### L2.4 Map FHIR elements (F15 to F18 first, then F2, F8, F4, F7, F10, F12, F14)
For each element in FnF that the application fills, name its source: a D column (spec side) and the target column it comes from, or a constant. For each element the application reads (F3, F5, F6, F9, F11, F13), name the D column it lands in.

### L2.5 Map code systems
ICD-10, SNOMED, the payer's package codes, document type codes, degree codes (F16), gender and relationship codes. For each, record whether the target stores the code, only a display text, or nothing, and what transform or lookup is needed.

### L2.6 Mark gaps and conflicts
A field the target does not hold is `missing` with the proposed fix (new column, new form field on which screen). A field held with a different meaning or type is `conflict` with the resolution.

#### L2O. OUTPUT
`nhcx-plan/mapping.json`:

```json
{
  "fields": [
    {
      "spec": "D3.abha_number",
      "fhir": ["F15:identifier[1].value"],
      "target": {"table": "", "column": "", "file": "", "lines": ""},
      "transform": "digits only, 14 characters",
      "status": "mapped | new | missing | conflict",
      "resolution": "",
      "screens": ["S14"]
    }
  ],
  "codes": [
    {"system": "ICD-10", "spec": ["D25.code", "F8:diagnosis[].diagnosisCodeableConcept"],
     "target": {"table": "", "column": ""}, "status": "mapped | lookup | missing", "notes": ""}
  ],
  "tables": [
    {"spec": "D18", "status": "new | existing | extend", "target_table": ""}
  ],
  "corrections": []
}
```

#### L2L. LOG
Record in `nhcx-plan/progress.json` and regenerate `nhcx-plan/progress.md`, as [LOG.md](LOG.md) describes. One entry per sub-step, with the D and F ids it mapped. L2.6 logs each `missing` or `conflict` it recorded, and every write to `nhcx-plan/mapping.json`.

#### L2X. EXIT
- Every column in D1 to D30 and every application-filled element in the F specs has an entry.
- No entry is `mapped` without a target location.
- Every `missing` and `conflict` has a resolution that L3 can turn into work.
- Every sub-step of L2 has its `started` and closing entries in progress.json, and every file changed is named in one.
