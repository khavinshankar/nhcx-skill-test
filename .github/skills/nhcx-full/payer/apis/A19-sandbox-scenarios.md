# A19. Sandbox Scenarios

#### A19E. ENDPOINT

Inbound to the application (the desk's own JSON endpoints), behind a signed-in session with a payer desk role. Sandbox only: a production target does not build this [SANDBOX](../references/PAYERS.md#markers).

| Call | Does |
|---|---|
| `GET /scenarios` | every preset, with the member id a hospital submits under to play it, and the delay the delay fault holds an answer for |
| `POST /cases/:id/scenario` | pins a scenario on one case, overriding what its member id implies, or clears it |

#### A19D. DESCRIPTION

A sandbox is for rehearsing what goes wrong. A scenario is a named preset of member and policy state, keyed on the member id a hospital submits under: `MBR-OK-0001` is a member whose cover is in order, `MBR-EXPIRED-0001` one whose cover lapsed, `MBR-PKG-0001` one whose plan covers only the cataract package. The seed writes that state on every boot (idempotent: each record is looked up by its handle before it is written), and the ordinary rules and desk produce the outcome. Nothing in the adjudication path looks at the prefix.

**The presets**, keyed on the longest prefix the member id starts with:

| Id | Prefix | State the seed writes | Expected outcome |
|---|---|---|---|
| `OK` | `MBR-OK-` | cover in force on the default policy, wallet untouched | approve |
| `PARTIAL` | `MBR-PARTIAL-` | INR 50,000 of cover left | partial: the lines cut to what remains (`sum_insured_cap`) |
| `QUERY` | `MBR-QUERY-` | a plan that demands past medical history and prescription notes on every pre-auth | query (`required_documents`) |
| `EXPIRED` | `MBR-EXPIRED-` | cover ran 2024-01-01 to 2024-12-31 | reject (`policy_validity`) |
| `EXHAUSTED` | `MBR-EXHAUSTED-` | nothing left in the wallet | reject (`sum_insured_cap`) |
| `PKG` | `MBR-PKG-` | a plan covering only `PROC-CAT-03` | reject (`package_mismatch`) |
| `CLIN` | `MBR-CLIN-` | cover in order; submit a package with a diagnosis that does not indicate it | query (`clinical_mismatch`) |
| `DUP` | `MBR-DUP-` | a knee replacement already filed a week ago | reject (`duplicate_claim_window`) |
| `APPEAL` | `MBR-APPEAL-` | cover began ten days ago, inside the 30-day waiting period | reject; a reprocess Task reopens it for a person (`waiting_period`) |

The reference sandbox runs every preset on one default policy (`SANDBOX-DEFAULT-01`, INR 5,00,000, every registry package) [REF](../references/PAYERS.md#markers). The expected outcome is what the rules find on a predetermination ([A10. Predetermination Quote](A10-predetermination-quote.md)); a pre-authorisation or a claim still waits for a person, and the tests take that decision through [A13. Adjudicate](A13-adjudicate.md).

**The faults**, `FAULT-<KIND>` presets on cover in order, applied to this payer's answers on their way out. Everything that happens is on the trail ([D27. case_exchange_message](../database/D27-case-exchange-message.md)): a dropped answer is recorded as dropped, a delayed one as delayed and then as sent, so an operator reading the case can tell a fault from a failure.

| Kind | Level | What becomes of the answer |
|---|---|---|
| `delay` | response | sent after the configured hold (default 30 s), then recorded |
| `drop` | response | never sent; the trail records the drop, and the transaction is recorded as `fault:drop` so the next decision does not send it either |
| `duplicate` | response | sent twice under the same correlation id |
| `malformed` | response | sent without its required elements (`status`, `outcome`, `insurer`, `total`, `type`, `use`, `created`, `adjudication` stripped from the focal resource; the bundle's `type` stripped) |
| `stale-correlation` | response | sent under a fresh correlation id that matches nothing |
| `wrong-outcome` | response | the opposite of what was decided: an approval sent as a rejection, anything else as an approval in full |
| `invalid-signature` | transport | handed to the gateway with `fault: invalid-signature`: encrypted for a key the recipient does not hold |
| `expired-token` | transport | sent under a bearer token the exchange rejects |
| `malformed-jwe` | transport | a JWE truncated in transit |
| `timeout` | transport | never dispatched by the gateway |

Response-level faults are applied by the application to the verdicts ([A3. Pre-auth Answer](A3-preauth-answer.md), [A4. Claim Answer](A4-claim-answer.md), [A9. Task Answer](A9-task-answer.md)) and the quote ([A10. Predetermination Quote](A10-predetermination-quote.md)). Transport-level faults are named on the envelope (`fault`) and applied by [G7. Send](../gateway/G7-send.md) [REF](../references/PAYERS.md#markers); the embedded gateway must accept the name and refuse an unknown one.

**Pinning.** An operator may pin a scenario on one case from the desk ([S3. Case Desk](../screens/S3-case-desk.md)), overriding the member id, or clear it with a blank. A pinned scenario is stored on the case ([D19. case](../database/D19-case.md) `scenario`) and shown beside the hospital.

**Messages, verbatim.** "Choose one of the scenarios GET /api/scenarios lists, or blank to clear" (422); "No case with that id" (404).

Data: [D19. case](../database/D19-case.md), [D5. member](../database/D5-member.md), [D6. subscription](../database/D6-subscription.md), [D12. policy](../database/D12-policy.md), [D31. audit_log](../database/D31-audit-log.md).

#### A19Q. REQUEST

`GET /scenarios`: no parameters.

`POST /cases/:id/scenario`:

| Field | Type | Required | Notes |
|---|---|---|---|
| `scenario` | string | yes | a preset id, case-insensitive; blank clears the pin |

```json
{"scenario": "FAULT-DELAY"}
```

#### A19S. RESPONSE

`GET /scenarios`, `200`:

```json
{"items": [
  {"id": "OK", "memberId": "MBR-OK-0001", "prefix": "MBR-OK-",
   "description": "Cover in force on the standard plan, wallet untouched. Submit any covered package with a matching diagnosis.",
   "expectedOutcome": "approve", "expectedFindings": [], "policyUin": "SANDBOX-DEFAULT-01"},
  {"id": "FAULT-DROP", "memberId": "MBR-FAULT-DROP-0001", "prefix": "MBR-FAULT-DROP-",
   "description": "Cover in order on the standard plan; the answer is subjected to the drop fault (response level).",
   "expectedOutcome": "approve, never sent, the trail records the drop", "expectedFindings": [],
   "fault": "drop", "faultLevel": "response", "policyUin": "SANDBOX-DEFAULT-01"}
 ], "total": 19, "faultDelaySeconds": 30}
```

`POST /cases/:id/scenario`, `200` with the case ([D19. case](../database/D19-case.md)) as the desk shows it, `scenario` set or cleared; `422` "Choose one of the scenarios GET /api/scenarios lists, or blank to clear"; `404` "No case with that id".

#### A19P. PSEUDOCODE

When: the seed on every boot; `GET /scenarios` from the desk and the tests ([T1. Test Configuration](../tests/T1-test-configuration.md) reads the member ids from it rather than hard-coding them); the pin from the case desk; and every outbound answer, which asks which scenario its case plays.

```text
SEED():                                   # every boot, idempotent
    registry = D10 procedures; if none: return   # the starter dataset has not run
    policy = D12 by uin "SANDBOX-DEFAULT-01", created when missing: every registry package,
             INR 500000, standard sub-limits, default coverage clauses and exclusions
    for scenario in Scenarios (index i):
        member = D5 by scenario.member_id, created when missing:
                 name "Sandbox <Id words>", DOB 1985-06-15, mobile "+91 90000 <10001+i>", abha "92" + 12 digits of (1+i)
        sub = D6 for the member, created when missing: policy, Individual, period last January to next December,
              except EXPIRED 2024-01-01 to 2024-12-31; EXHAUSTED wallet 0; PARTIAL wallet 50000;
              APPEAL period from 10 days ago
        if scenario == DUP and the member has no case: D19 a knee replacement (PROC-KNEE-01) admitted 7 days ago

RESOLVE(case):                            # which scenario a case plays
    if case.scenario set: return that id, or "" when unknown
    return the id whose prefix is the longest prefix of upper(case.member_id), else ""

PIN(case_id, scenario, actor):
    id = upper(trim(scenario))
    if id and id not a preset: refuse 422 fields {scenario: "Choose one of the scenarios GET /api/scenarios lists, or blank to clear"}
    write D19: scenario = id or null              or refuse 404 "No case with that id"
    audit (D31): "case.scenario", entity case, detail id
    return 200 D19[case_id]

DISPATCH(answer):                         # every verdict and quote leaves through this (A3, A4, A9, A10)
    kind, level = fault of RESOLVE(answer.case)
    bundle = answer.render(answer.case)
    if kind == "": return SEND(answer.headers, bundle)
    if level == transport: return SEND(answer.headers, bundle, fault = kind)          # G7 applies it
    switch kind:
        drop:      record txn "fault:drop"; trail note "dropped deliberately (scenario <id>)"; send nothing
        delay:     trail note "held back for <hold> (scenario <id>)"; record txn "fault:delay";
                   after the hold: SEND, then record the txn and trail row "sent after the deliberate delay"
        duplicate: first = SEND; second = SEND with the same headers; trail note "sent twice under the same correlation id"
        malformed: SEND(headers, MALFORM(bundle)); trail note "sent without its required elements"
        stale-correlation: SEND with x-hcx-correlation_id = new UUID; trail note "sent under a fresh correlation id <id> that matches nothing"
        wrong-outcome: SEND(headers, answer.render(FLIP(answer.case))); trail note "sent saying <flipped> where the decision was <decided>"
    each SEND is gateway.send (G7); its ack is written on the trail (D27) with the note

MALFORM(bundle): delete status, outcome, insurer, total, type, use, created, adjudication from the first entry's resource; delete bundle.type
FLIP(case):      approved -> rejected with every line rejected at 0; anything else -> approved with every line approved in full
```

#### A19U. USED BY
- Screens: [S3. Case Desk](../screens/S3-case-desk.md)
- APIs: [A3. Pre-auth Answer](A3-preauth-answer.md), [A4. Claim Answer](A4-claim-answer.md), [A9. Task Answer](A9-task-answer.md), [A10. Predetermination Quote](A10-predetermination-quote.md), [A13. Adjudicate](A13-adjudicate.md), [A18. Provider Driver](A18-provider-driver.md)
- Callbacks: [C6. Predetermination](../callbacks/C6-predetermination.md)
- Database: [D19. case](../database/D19-case.md)
- Tests: [T11. Predetermination Quoted](../tests/T11-predetermination-quoted.md)
