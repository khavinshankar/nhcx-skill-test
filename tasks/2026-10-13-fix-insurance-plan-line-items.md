# Fix insurance plan line-item mapping

Date: 2026-10-13 (Asia/Kolkata)
Session: 54642942-8c13-4ae7-a23f-355474803734

## Request

The user reviewed the line items in the claims UI and reported two problems:
1. Dengue sits under several specialities but only one (Cardiology) is shown. The user asked for this to be checked against the FHIR bundle before confirming.
2. For Dengue, and for every other line item, the rate, stratification, supporting documents and claim conditions are mapped wrongly.

## Findings (checked against the PMJAY bundle for NM-26-0VL00003S, plan 91)

- **Specialities (confirmed):** the parser removed duplicates by package code alone.
  - In the bundle, MG004A/B/C each appear under Cardiology (MC), General Medicine (MG) and Paediatric Medical management (MP).
  - Across the bundle, 545 of 1537 codes appear in more than one speciality, giving 2365 (category, code) pairs in `specificCost`.
  - `coverage` adds 178 implant pairs.
  - The cost and extensions of a package are the same in every speciality it is listed under.
- **Tiers, conditions and documents:**
  - The database already held them correctly. For MG004A that is rate 0, 4 STRAT tiers, 18 conditions and 6 documents.
  - The claim state sent only kind, code, display, category and rate, so PackageDetail and the line picker always saw empty `extras`, `conditions` and `supporting_info`. Tier and implant suggestions never appeared for the same reason.
- **Rate:**
  - All 369 zero-rate PMJAY packages carry ward/ICU tiers (MG004A: ₹1800/2700/3600/4500 per day). ₹0 is the payer's real base rate.
  - The UI treated ₹0 as an open price.
- **Update lines (found during the fix):** the button POSTed each changed line to `add_line`, which refuses with "<code> is already on this preauth." The backend `PUT lines/` was never used.
- **Payload (found during the fix):** the claim state shipped the plan's raw `response_json` (about 35 MB for this plan) on every claim load.

## Decisions and rationale

- **Benefits keyed on (category_code, code):** this is a deliberate change to the D11/F5 rule of one row per code, made because the payer data lists packages under several specialities. Plan 91 now has 2543 rows instead of 1678.
  - The specs D11, F5, C4 and S8 are updated to match.
  - An implant that `coverage` repeats within one speciality, once per parent procedure, is kept as one row. Its `ParentProcedure` values are joined with "; " (46 such cases).
- **Open price:** the user chose this option when asked. ₹0 with tiers is a fixed price, and the money is charged through the tier lines. A line is open-priced only when the plan names no rate, or the rate is ₹0 and there are no tiers. S8 is updated.
- **Payload split:**
  - The state's benefits now include `seq`, `currency`, `cost_type`, `requirement` and `extras`.
  - `conditions` and `supporting_info` add about 2.3 MB on the PMJAY plan, so they are served per package by the new `GET claims/<id>/plan/benefits/<benefit_id>/`. PackageDetail loads them from there.
- **Speciality of a line:**
  - `add_line` takes an optional `category_code`. The picker sends the row's speciality, and implant suggestions send the speciality of their parent procedure.
  - A tier takes the speciality of its procedure line.
  - `_gather._benefits` picks one plan row per quoted code, preferring the line's speciality.
- **Raw bundle removed from the state:** `response_json` is dropped from `plan` in the claim state (no screen reads it). The state for plan 91 goes from 36 MB to 1.24 MB.
- **Existing data:** ready plans that have a stored bundle were re-parsed in place from `response_json`, with `fetched_at` left unchanged. Plan 91 went from 1678 to 2543 rows. Fixture plans kept 16 rows. Seeded plans have no bundle and were left untouched.

## Repository changes

| Repository | Final commit | Changes |
| --- | --- | --- |
| care (`nhcx-integration`, silver-sniffle worktree) | `53d6d332f` | Parser per (category, code) with implant merge; benefit detail endpoint; `category_code` on add_line; tier-aware open price; `_benefits` category preference; state columns; `response_json` dropped from the state; tests |
| care_fe (`nhcx-integration`, silver-sniffle worktree) | `8848d8cc9` | PackageDetail fetches its detail; picker uses the speciality and the new open-price rule; Update lines uses `PUT lines/`; types and routes `getPlanBenefit`, `updateLines` |
| parent | this commit | Specs D11, F5, C4 and S8; this record; PROGRESS.md |

## Validation

- `ruff format` and `ruff check care/nhcx`: clean.
- `python manage.py test care.nhcx`: 293 tests OK. New tests cover the per-speciality parse, the implant merge, speciality choice for lines and tiers, `_benefits` preference, tier-backed ₹0 not being open-priced, and the benefit detail API.
- Parser run on the real 33 MB bundle: 2543 unique (category, code) rows. MG004A is listed under MC, MG and MP, each with rate 0, 4 tiers, 18 conditions and 6 documents.
- Live API check against plan 91: the detail endpoint returned 200 for MG004A/MG with ProcedureType Conservative and 6 MAND documents. The claim state is 1.24 MB.
- care_fe: `tsc --noEmit` passed. eslint shows only 2 warnings, both pre-existing (setState in effect). prettier applied.
- Not tested: clicking through the UI in a browser.

## Open items

- Lines quoted before this fix keep the speciality they were given then (the first row).
- The package master lists a multi-speciality package once per speciality. Add still refuses a second copy of a code already quoted, by design.
