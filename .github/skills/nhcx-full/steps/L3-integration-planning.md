# L3. Integration Planning

#### L3G. GOAL
Turn discovery and mapping into an ordered integration plan for this target: phases, steps and sub-steps, each saying what changes in the target, which spec items it delivers, and what it depends on.

#### L3I. INPUTS
- `nhcx-plan/discovery.json`, `nhcx-plan/mapping.json`.
- The flow in [screens/INDEX.md](../screens/INDEX.md) and the API and callback indexes.

### L3.1 Fix the order
Build in the order a claim happens, so each phase can be exercised on its own. These are the phases of [references/SCAFFOLDING.md](../references/SCAFFOLDING.md) section 12:
1. Foundation: gateway embedded (G1 to G11), configuration, ledger, the inbound route (wired to a stub receive answering `unmatched` until C1 exists).
2. Data: new tables and columns from mapping.json (D), master-data fixes (ABHA, HPR, HFR, participant codes); then the C1 dispatcher and the archive, which match on D9 and the leg tables (D10, D13, D18 to D29) and so come after them, not in phase 1.
3. Policy and eligibility: S1, S2, S3, S5, S6 shell; A1, A2; C2; F2, F3, F15 to F18.
4. Plan and line items: S7, S8; A3, A2 (auth-requirements); C3, C4; F4 to F6.
5. Pre-authorisation: S4, S9; A4, A6 (cancel, status); C5, C7, C8; F7, F8, F9, F10.
6. Payer communication: S10; A7; C9; F11, F12.
7. Claim: S11; A5, A6 (reprocess, release); C6, C8.
8. Payment: S12; A8; C10; F13, F14.
9. Patient and practitioner screens where the target lacks fields: S13 to S16.
10. Navigation: add "Claims" to the HMIS home screen or sidebar.

### L3.2 Describe each step for this target
For every step: what is added or changed in the target (by module and file, using discovery.json locations), which spec ids it delivers, which mapping entries it resolves, and the target-specific decisions (for example "extend the existing `insurance_policy` table instead of adding D9 policy columns").

### L3.3 Record dependencies and risks
Dependencies between steps (by id), external needs (participant code, client id and secret, private key and registered certificate, public URL reachable by NHCX), and risks with a mitigation.

Take the production cutover and the deployment shape (one NHCX instance, its own ledger directory) from [OPERATIONS.md](../references/OPERATIONS.md): each cutover step becomes a plan step with an owner, and a target that cannot give one instance the NHCX role records that as a risk.

### L3.4 Define done per phase
For each phase, the observable check that shows it works (for example "S3 shows `eligible` after C2 settles a verdict for a sandbox policy").

#### L3O. OUTPUT
`nhcx-plan/plan.json`:

```json
{
  "phases": [
    {
      "id": "P3",
      "title": "Policy and eligibility",
      "done_when": "",
      "steps": [
        {
          "id": "P3.1",
          "title": "",
          "description": "specific to the target",
          "delivers": ["S1", "A1", "G10"],
          "resolves": ["D9.member_id"],
          "changes": [{"file": "", "lines": "", "change": "add | modify"}],
          "depends_on": ["P1.2"],
          "substeps": [{"id": "P3.1.1", "title": "", "description": ""}]
        }
      ]
    }
  ],
  "external": [{"need": "participant code", "owner": "", "status": "have | requested | missing"}],
  "risks": [{"risk": "", "mitigation": ""}],
  "corrections": []
}
```

#### L3L. LOG
Record in `nhcx-plan/progress.json` and regenerate `nhcx-plan/progress.md`, as [LOG.md](LOG.md) describes. One entry per sub-step. L3.2 logs one entry per plan step it describes (the P id as `item`), and every write to `nhcx-plan/plan.json`.

#### L3X. EXIT
- Every spec id marked `missing` or `partial` in discovery.json is delivered by exactly one step.
- Every `missing` or `conflict` mapping entry is resolved by a step.
- The dependency graph has no cycles, and every phase has a `done_when`.
- Every sub-step of L3 has its `started` and closing entries in progress.json, and every file changed is named in one.
