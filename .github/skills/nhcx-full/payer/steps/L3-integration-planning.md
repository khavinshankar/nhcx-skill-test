# L3. Integration Planning

#### L3G. GOAL
Turn discovery and mapping into an ordered integration plan for this target: phases, steps and sub-steps, each saying what changes in the target, which spec items it delivers, and what it depends on.

#### L3I. INPUTS
- `nhcx-plan/discovery.json`, `nhcx-plan/mapping.json`.
- The flow in [screens/INDEX.md](../screens/INDEX.md) and the API and callback indexes.

### L3.1 Fix the order
Build in the order a case happens, so each phase can be exercised on its own. These are the phases of [references/SCAFFOLDING.md](../references/SCAFFOLDING.md) section 12:
1. Foundation: gateway embedded (G1 to G11), configuration, ledger, the inbound route and the C1 door.
2. Data: the case, exchange log, delivery and numbering tables (D19, D27, D28, D32), and the column additions to existing tables from mapping.json (D1 participant codes, D5 ABHA, D6 wallet and ABHA link, D10 to D12 package rate, document rules, UIN and plan type).
3. Eligibility and plan: A1, A2, A16, A17; C2, C3; F2 to F6, F15 to F18; S4 to S9, S11, S12.
4. Pre-authorisation: A3, A8, A9, A10, A13; C4, C6, C7, C8; F7 to F10, F19; D20 to D26, D29; S1 to S3.
5. Queries: A5; C9; F11, F12.
6. Claim: A4; C5; the claim-stage rules on A13 (wallet debit) and the reprocess leg of A9.
7. Payment: A6, A7, A14; C10, C11; F13, F14; D30; S10.
8. Navigation: add "Cases" and "Payments" to the payer system's home screen or sidebar.

### L3.2 Describe each step for this target
For every step: what is added or changed in the target (by module and file, using discovery.json locations), which spec ids it delivers, which mapping entries it resolves, and the target-specific decisions (for example "extend the existing `claims` table instead of adding D19 case columns").

### L3.3 Record dependencies and risks
Dependencies between steps (by id), external needs (participant code, client id and secret, private key and registered certificate, public URL reachable by NHCX, the sandbox provider EMR for tests), and risks with a mitigation.

Take the production cutover and the deployment shape (one NHCX instance, its own ledger directory) from [OPERATIONS.md](../references/OPERATIONS.md): each cutover step becomes a plan step with an owner, and a target that cannot give one instance the NHCX role records that as a risk.

### L3.4 Define done per phase
For each phase, the observable check that shows it works (for example "S3 shows a case filed and acknowledged after C4 takes in a sandbox pre-authorisation").

#### L3O. OUTPUT
`nhcx-plan/plan.json`:

```json
{
  "phases": [
    {
      "id": "P3",
      "title": "Eligibility and plan",
      "done_when": "",
      "steps": [
        {
          "id": "P3.1",
          "title": "",
          "description": "specific to the target",
          "delivers": ["S5", "A1", "C2"],
          "resolves": ["D6.wallet_balance"],
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
