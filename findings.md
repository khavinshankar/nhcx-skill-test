# Human-tested findings: skill-assisted NHCX implementation

Recorded: 13 October 2026 (Asia/Kolkata).

These 13 findings were identified and noted by a human while testing the AI-generated NHCX integration in CARE HMIS. They are observations from that testing, not an AI-generated certification of completeness. Preserve them as findings against the implementation as tested, even where follow-up work has since fixed a problem. Status notes below distinguish documented fixes, ongoing work, and gaps that still need verification.

The evaluation should consider the skill, the agent's use of it, its understanding of the existing HMIS and ABDM plugin, and the resulting clinical workflow. A missing feature alone does not establish which of those caused the gap. Passing automated tests did not establish that the implementation was ready for users.

## 1. Missing NHCX administration UI

**Human observation:** No UI was available to configure or update the NHCX participant code, callback endpoint, or recycle/rotate encryption keys.

**Why it matters:** Routine onboarding and maintenance depended on developer intervention. Users need an explicit facility/participant configuration flow and safe endpoint and key lifecycle operations.

**Follow-up status:** A facility NHCX settings screen and participant-code editing were subsequently added. Endpoint management and key rotation are not established as complete by the task records. The original absence and the remaining administration gaps must not be conflated. See [setup follow-ups](tasks/2026-10-13-run-server-and-ui.md).

## 2. Existing ABDM health-facility identity was bypassed

**Human observation:** NHCX introduced its own HF/HFR identity configuration instead of using the existing ABDM implementation.

**Why it matters:** Duplicate identity settings can disagree and force operators to maintain the same facility identity in two places. The requested direction is to use ABDM's existing implementation.

**Follow-up status:** A fallback to the ABDM plugin's `HealthFacility.hf_id` was added when the NHCX HFR value is blank; an explicit NHCX value still wins. This is partial reuse, not full removal of duplicate configuration. No live ABDM facility identity was configured during the recorded verification. See [setup follow-ups](tasks/2026-10-13-run-server-and-ui.md).

## 3. ABDM capabilities were implemented again

**Human observation:** NHCX implemented its own ABDM flows despite a full ABDM implementation already being available in the workspace.

**Why it matters:** Duplicate ABHA creation/verification, token management, UI and identifier persistence increase maintenance work and can produce inconsistent patient records.

**Follow-up status:** The investigation documented overlapping ABHA services, dialogs, token caches and different identifier-system values. Consolidation remains open. NHCX-specific gateway encryption, claims and callbacks are distinct capabilities and should not be counted as ABDM duplication. See the [duplication analysis](tasks/2026-10-13-run-server-and-ui.md).

## 4. First policy beneficiary selected automatically

**Human observation:** PMJAY returned three patients/beneficiaries, and the implementation selected the first without asking the user.

**Why it matters:** Response order does not express clinical intent. A user should explicitly choose the beneficiary before using beneficiary-specific data in a claim.

**Expected behavior:** Present the returned members, require a selection when ambiguous, and make the selected member visible and changeable.

**Follow-up status:** Beneficiary-selection changes were present as uncommitted work at publication. They are included as review patches, not represented as a validated or completed fix.

## 5. Automatic HMIS patient association

**Human observation:** The beneficiary was associated with an HMIS patient without explicit user direction. A shared member ID may identify a child while the existing HMIS association belongs to a parent/original owner.

**Why it matters:** An incorrect association can attach insurance and clinical activity to the wrong person. Policy-member selection and HMIS patient linking are separate decisions.

**Expected behavior:** Ask the user to confirm the actual beneficiary and HMIS patient; do not treat a matching member ID alone as proof of identity. Clearly surface ambiguous matches.

**Follow-up status:** Related beneficiary changes are ongoing. This publication does not claim that the parent/child ambiguity has been fully tested or resolved.

## 6. Large insurance-plan payloads failed

**Human observation:** The large insurance-plan response was not handled successfully. Request-body handling and decryption both caused failures, and plan fetch later took down the backend.

**Why it matters:** Real payer payloads exercise different limits from small fixtures. The entire path—proxy, HTTP transfer encoding, body limits, cryptography, database writes and logging—needs realistic payload validation.

**Verified details:** The investigation found chunked-body handling problems, Authlib's JOSE segment-size limit, and memory exhaustion from development SQL pretty-printing. The observed JWE was approximately 44.6 MB and decrypted to approximately 33.4 MB. This was not simply Django's usual body-size limit: the gateway used `request.read()` rather than `request.body`.

**Follow-up status:** Chunked-body middleware, larger configured upload limits, large-JWE decryption and disabling SQL printing were added. The latest cached-plan fetch returned HTTP 200 in 4.13 seconds with the backend healthy. Gzip handling, proxy/body ceilings, storage duplication and fresh large callback validation remain distinct considerations. See [payload investigation](tasks/2026-10-13-insurance-plan-callback-investigation.md) and [OOM fix](tasks/2026-10-13-fix-insurance-plan-fetch-oom.md).

## 7. Plan lifecycle is claim-centric rather than facility-centric

**Human observation / requested behavior:** Insurance plans appeared to be fetched for every claim; they should be fetched once per facility and refreshed through defined triggers and manual intervention.

**Verified nuance:** The service already tries to reuse a ready plan with the same payer, policy and facility HFR ID. It therefore does not necessarily make an external request for every claim. However, it copies the full plan into each claim's own record and has no recorded expiry/refresh policy.

**Expected direction:** A shared facility/payer/policy plan cache, explicit invalidation/refresh triggers and manual refresh, while preserving which plan version supported a claim. A facility may have multiple payer/policy combinations; one global plan per facility would be insufficient.

**Follow-up status:** Shared storage and refresh lifecycle remain open. See [fetch-scope investigation](tasks/2026-10-13-insurance-plan-callback-investigation.md).

## 8. Dengue appeared under only Cardiology

**Human observation:** Dengue had multiple categories but only Cardiology was shown. The tester explicitly requested verification against the FHIR bundle before confirming the diagnosis.

**Verified against the stored PMJAY bundle:** MG004A/B/C appear under Cardiology (MC), General Medicine (MG) and Paediatric Medical management (MP). The parser had deduplicated by package code alone.

**Follow-up status:** The parser now keys benefits by category and code, and the picker preserves the selected speciality. The recorded reparse produced 2,543 benefit rows. See [FHIR-backed findings and fix](tasks/2026-10-13-fix-insurance-plan-line-items.md).

## 9. Incorrect or missing package details

**Human observation:** Dengue line-item rate, stratification, supporting documents and claim conditions were mapped/displayed incorrectly; the concern also applied to other packages.

**Verified detail:** The database held relevant details, but the claim-state response omitted fields required by the UI. A zero base rate with ward/ICU tiers was also treated as an open price. For MG004A, the investigation recorded four tiers, 18 conditions and six supporting documents.

**Follow-up status:** Benefit detail retrieval, state fields, speciality selection, tier-aware open-price handling and line updates were corrected. Automated checks and live API verification passed; browser click-through was not recorded. See [line-item fix](tasks/2026-10-13-fix-insurance-plan-line-items.md).

## 10. ICD-10 diagnosis selector instead of SNOMED

**Human observation:** The diagnosis selector offered ICD-10 rather than the expected SNOMED workflow.

**Why it matters:** The user-facing terminology and outbound coded data should follow the agreed clinical and payer requirements. This finding records the tester's expected SNOMED behavior; it does not independently assert that ICD-10 is prohibited by every NHCX profile.

**Follow-up status:** Open. Verify the intended terminology source, selector and FHIR coding together.

## 11. No structured-data entry options

**Human observation:** The tested workflow did not offer structured-data entry options.

**Why it matters:** Required clinical or package-specific information should be captured with explicit fields and validation where the workflow calls for structured data.

**Follow-up status:** Open. Identify the missing forms/data elements with the tester and map them to the payer requirements; the original note did not enumerate them.

## 12. No enhancement option

**Human observation:** An enhancement workflow was not available through the tested UI.

**Why it matters:** Users need a discoverable way to request additional authorization against an existing case, with the relevant current authorization and added items visible.

**Follow-up status:** Open. The original implementation report also records a PMJAY enhancement failure: the local one-row-per-code rule conflicted with a new item per cycle. UI availability and backend correctness both require validation. See [original implementation report](tasks/2026-10-13-care-nhcx-integration.md).

## 13. Payments not integrated with HMIS workflows

**Human observation:** NHCX payments were not integrated with the HMIS-specific payment solution.

**Why it matters:** Claim/remittance status alone does not complete billing, payment posting and reconciliation in the host HMIS.

**Follow-up status:** Open. Agree how payer amounts, deductions, adjustments and settlement references map to the existing HMIS billing/payment records, then validate that workflow end to end.

## How to review the AI's performance

Read the original request and skill, inspect the generated code and test evidence, then compare these human-tested findings with the agent's reported completion. Distinguish the original result from later human-directed repairs. Do not use the number of passing tests as a substitute for beneficiary safety, reuse of existing modules, clinical correctness or operational readiness. Repository and transcript access instructions are in [README.md](README.md).
