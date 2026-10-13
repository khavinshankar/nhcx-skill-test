# NHCX progress after the first implementation

The first implementation is recorded in `tasks/2026-10-13-care-nhcx-integration.md`:
- care `nhcx-integration` up to `4d9be7ffb`
- care_fe `nhcx-integration` up to `46077c631`

This file lists every change made on top of it, newest first. Each entry links to its task record.

## 2026-10-13: Insurance plan packages per speciality, tiers and documents in the UI

Task: `tasks/2026-10-13-fix-insurance-plan-line-items.md`

| Repository (branch) | Commit | Change |
| --- | --- | --- |
| care (`nhcx-integration`) | `53d6d332f` | Plan benefits are keyed on (category, code). The claim state now includes tiers and extras and no longer carries the raw bundle. New `GET plan/benefits/<id>/` endpoint. `add_line` takes `category_code`. A ₹0 package with tiers is a fixed price. |
| care_fe (`nhcx-integration`) | `8848d8cc9` | PackageDetail fetches its conditions and documents. The picker is speciality-aware. Update lines uses `PUT lines/`. |

- **Spec deviation:** D11 and F5 now merge on (category, code) instead of code alone, because PMJAY lists 545 codes under more than one speciality.
- **Open price:** a line is open-priced only when the plan names no rate, or ₹0 with no ward/ICU tiers (user decision; S8 updated).
- **Existing data:** plan 91 was re-parsed in place: 1678 rows became 2543.

## 2026-10-13: Facility NHCX settings screen and ABDM HIP ID reuse

Task: `tasks/2026-10-13-run-server-and-ui.md`

| Repository (branch) | Commit | Change |
| --- | --- | --- |
| care (`nhcx-integration`) | `47ca95532` | Blank `FacilityProfile.hfr_id` falls back to the care_abdm HIP ID. The profile API returns more fields, and PUT needs `can_update_facility`. |
| care_fe (`nhcx-integration`) | `cc39c8991` | New screen at Settings > NHCX (`/facility/<id>/settings/nhcx`). The facility profile response types are fixed. |

- **ABDM HIP ID reuse:**
  - `services.common.facility_profile()` fills a blank `hfr_id` from `abdm.HealthFacility.hf_id`.
    The value is set in memory only and never saved.
  - Every outbound FHIR payload and check that reads the profile uses this value: eligibility, plan, claim and the rest.
  - If `hfr_id` is set in the NHCX profile, it wins.
  - If the care_abdm plug is not installed, `abdm_hf_id()` returns "".
- **API change:** `GET/PUT /api/v1/facility/<id>/nhcx/profile/` now also returns
  `abdm_hf_id`, `effective_hfr_id`, `hfr_id_source` (`profile`, `abdm` or null) and `can_edit`.
- **Behaviour change:** PUT used to be open to any facility member. It now needs `can_update_facility`,
  checked with `AuthorizationController` `can_update_facility_obj`.
- **UI:** the screen edits the HFR ID, participant code, email and GSTIN, and shows the HFR ID that NHCX receives
  and where it comes from.
  - When the facility has an ABDM HIP ID, the screen shows it and offers a "Use ABDM HIP ID" button.
  - Users without update permission see the fields read-only.
- **Fix:** `nhcxApi.getFacilityProfile` and `updateFacilityProfile` were typed as a bare `FacilityProfile`,
  but the server wraps it in `{ok, message, profile}`.
- **Validation:**
  - `manage.py test care.nhcx` ran 287 tests and all passed (282 before, plus 5 new); ruff is clean.
  - care_fe: `tsc --noEmit`, eslint and prettier are clean.
  - The live GET for both facilities returned the expected fields.
