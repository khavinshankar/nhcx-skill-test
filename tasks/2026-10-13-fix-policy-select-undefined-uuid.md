# Fix "undefined" is not a valid UUID on policy Select

Date: 2026-10-13 (Asia/Kolkata)
Session: 292789dc-a257-4c82-b4f9-82ff663c523e

## Request

"when I click select after entering the member id, I get this error, lets fix this, also state what was the cause of this error"
(The screenshot showed the Policy search page with a toast reading "undefined" is not a valid UUID.)

## Cause

- `SearchPolicy.tsx` submits the search with
  `setQParams({ id_type, id_value, patient: qParams.patient, searched: "1" })`. When the user did not come from a
  patient, `patient` is `undefined`.
- raviger's default `useQueryParams` serializer drops only `null` values, not `undefined`. So the URL became
  `?…&patient=undefined`, and the string `"undefined"` was read back from it.
- Select posts `patient: qParams.patient || undefined`. Because `"undefined"` is a truthy string, it was sent to
  `POST /api/v1/facility/<id>/nhcx/claims/`.
- In the backend, `_patient()` ran `Patient.objects.filter(external_id="undefined")`. Django's UUIDField raised
  `ValidationError("“undefined” is not a valid UUID.")`, and that message reached the toast.
- Related bug found on the same request: the UI sends `id_type`/`id_value`, but the backend's policy branch read
  only `identifiertype`/`identifiervalue`. As a result, claims opened from the UI lost `search_id_type` and `search_id_value`.

## Changes (worktree khavinshankar-silver-sniffle, branch nhcx-integration)

- care_fe `2fdd9257d`: added `serializeQuery` in `pages/Facility/claims/utils.ts`, which drops undefined, null and
  empty values. `SearchPolicy`, `BeneficiaryDiscovery` and `InsurancePlanTab` now pass it to `useQueryParams`.
  The latter two had the same latent bug on "change patient" and "clear filters".
- care `a5426abad`: `views_core._patient`/`_encounter` validate the id and return a 400 refusal,
  "Patient id 'undefined' is not a valid UUID.", instead of a raw Django error. The policy branch also accepts
  `id_type`/`id_value`. Added regression test `test_open_claim_with_ui_payload`.

## Validation

- `python manage.py test care.nhcx.tests.test_api_core` in `care-nhcx-backend`: 9 tests OK. ruff check and format: clean.
- care_fe `tsc --noEmit`: clean. eslint: 0 errors. The 6 warnings (set-state-in-effect) predate this change.
  The pre-commit hook passed.
- Not re-clicked in the browser. The dev servers serve this worktree, so a page reload picks up the fix.
  A stale `?patient=undefined` already in the address bar is still sent by Select, and the backend now refuses it
  with a clear message. Search again or drop that parameter.

## Open items

- None. Commits are not pushed.
