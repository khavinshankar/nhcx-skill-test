# A17. Claim State

#### A17E. ENDPOINT

`GET /claims/view/:caseid/state`, inbound to the application (the application's own JSON endpoint, not a call into G). `:caseid` is the claim's numeric id.

#### A17D. DESCRIPTION

Everything the claim's tabs show, as one JSON document. It exists for scripted drivers and tests, which read a case's progress here and act through the screens' own form routes.

Before answering it runs the same [G9. Ledger](../gateway/G9-ledger.md) polls that opening the claim page runs, in this order. Each poll does nothing unless its leg is waiting:

| # | Poll | Runs when | G9 ledger queries |
|---|---|---|---|
| 1 | Eligibility reply | Only while the claim's status is `checking` and it has a transaction id | A10 for a CoverageEligibilityResponse; if none, a protocol error scan (A13, then A12 per entry); then A11 |
| 2 | Insurance plan | The plan row is `fetching` with a transaction id | A10 for an InsurancePlan; protocol error scan; A11 |
| 3 | Auth requirements ruling | The ruling row is `checking` with a transaction id | A10 for a CoverageEligibilityResponse; protocol error scan; A11 |
| 4 | Claim | The submission is `submitting` with a transaction id | A10 for a ClaimResponse; the payer's own dispatch failure when one G hosts both participants (A11); protocol error scan; A11 |
| 5 | Pre-authorisation | The pre-authorisation is `submitting` with a transaction id | Same as the claim |
| 6 | Predeterminations | Each quote that is `asking` with a transaction id | A10 for a ClaimResponse; the payer's dispatch failure; protocol error scan |
| 7 | Cancellation | The pre-authorisation is `cancelling`, or is `approved` with a refused cancellation settled less than 15 minutes ago, and has a cancel transaction id | A10 on the cancel transaction, A12 per Task reply; if none, protocol error scan |
| 8 | Enquiries | Each status or task enquiry that is `asking` with a transaction id | A10 for a Task; the payer's dispatch failure; protocol error scan; own dispatch status (A11) |

When A10 answers not found, the G9 ledger no longer has the transaction. The leg is then set to `error` with a message asking for the send to be repeated, and the poll does not fail. Any other poll failure does not fail the call either. Its message is added to `poll_notes` and the next poll runs.

After the polls the case stage is worked out again and stored on the claim, so `stage` and `sub_stage` reflect what the payer has just said.

**Hooks owned by A4 and A5.** Four keys of the answer are computed by the pre-authorisation and claim services, not by this endpoint, and A17 only calls them. Their contracts, so A17 can be written before them and the services after:

| Hook | Owner | Signature | Answers |
|---|---|---|---|
| `next_send` | A4 (`preauth_send_kind`), A5 (`claim_send_kind`) | `(case_id) -> kind or {"refused": "<reason>"}` | the kind the next send would be, or the verbatim refusal the send would meet; never raises |
| `enhancement_lines` | A4 | `(case_id) -> [line rows]` | the D16 lines whose code is not in the last sent bundle (F8 "Read back"); `[]` when nothing is decided or nothing was added |
| `required_documents` | A4 (`preauth`), A5 (`claim`) | `(case_id, stage) -> [{code, display, category, package_code, attached_document_id}]` | the ruling's requirements due at the stage, else the package master's, as S9 and S11 list them |
| `required_forms` | A4 (`preauth`), A5 (`claim`) | `(case_id, stage) -> [{url, title, questions}]` | the forms the stage has to carry by the D12 rule (ruling, packages' STG forms, policy-wide forms, the consent form when no token is held) |

Before a hook exists (phase order, L3), A17 answers `next_send` as `{"refused": "not available yet"}`, `enhancement_lines` as `[]`, and `required_documents` and `required_forms` as `{"preauth": [], "claim": []}`, so drivers written against the shape keep working and a missing hook is visible rather than a crash.

#### A17Q. REQUEST

No body, no query parameters.

```
GET /claims/42/state
```

#### A17S. RESPONSE

`200` with a JSON object. An unknown claim returns `404` `{"error": "No such claim"}`.

Row objects are the stored rows with every column, or `null` when the row does not exist. Data: [D9. claim](../database/D9-claim.md), [D10. claim_plan](../database/D10-claim-plan.md), [D11. claim_plan_benefit](../database/D11-claim-plan-benefit.md), [D4. encounter](../database/D4-encounter.md), [D16. claim_line](../database/D16-claim-line.md), [D13. claim_auth](../database/D13-claim-auth.md), [D15. claim_auth_requirement](../database/D15-claim-auth-requirement.md), [D12. claim_plan_form](../database/D12-claim-plan-form.md), [D28. claim_document](../database/D28-claim-document.md), [D18. claim_preauth](../database/D18-claim-preauth.md), [D19. claim_predetermination](../database/D19-claim-predetermination.md), [D23. claim_query](../database/D23-claim-query.md), [D20. claim_submission](../database/D20-claim-submission.md), [D21. claim_payment](../database/D21-claim-payment.md), [D29. claim_enquiry](../database/D29-claim-enquiry.md).

| Key | Type | Content |
|---|---|---|
| `claim` | object | The claim row (after the polls). |
| `plan` | object or null | The claim's insurance plan (package master) row. |
| `benefits` | array | The plan's packages, in order, a subset of each D11 row (see A17P). Empty when there is no plan. |
| `admissions` | array | Current inpatient stays of patients registered with the claim's ABHA number (compared on digits only). |
| `lines` | array | The claim's line item rows, by kind then sequence. |
| `ruling` | object or null | The auth requirements ruling row. |
| `required_documents` | object | `preauth` and `claim`: arrays of the documents the payer named for that stage. |
| `forms` | object | `preauth` and `claim`: arrays of `{"url", "title", "questions"}`, the questionnaires that stage has to carry, with each form's stored questions. |
| `documents` | array | Attachments without their payloads, a subset of each D28 row (see A17P). |
| `stage` | string | Where the case stands: `eligibility`, `preauth`, `enhancement`, `claim` or `payment`. |
| `sub_stage` | string | What was last done with it: `draft`, `checking`, `eligible`, `not-eligible`, `requested`, `resubmitted`, `answered`, `queried`, `approved`, `partial`, `rejected`, `cancelling`, `cancelled`, `refused`, `noticed` or `paid`. |
| `preauth` | object or null | The pre-authorisation row. |
| `preauth_items` | array | The payer's per-item verdict on the pre-authorisation (see below). |
| `next_send` | object | `preauth` and `claim`: the kind of the next send, or `{"refused": "<reason>"}` when nothing may be sent. Pre-authorisation kinds: `preauth`, `preauth_query_response`, `enhancement`, `enhancement_resubmit`. Claim kinds: `claim`, `claim_query_response`, `claim_resubmit`. |
| `adapter` | string | The payer adapter's key (for example `pmjay`, `kyrocare`, `generic`). |
| `desk` | string or null | Where the payer's decision is taken: `nhcx-payer-service`, `irdai-payer`, or `null` for none (see A14). |
| `predeterminations` | array | Quote rows, newest first. |
| `enhancement_lines` | array | Lines quoted since the pre-authorisation was decided. Empty when nothing was added or nothing is decided yet. |
| `queries` | array | Everything the payer has said on the claim (queries, notifications, notes), newest first, each row with a `questions` array of the payer's lines. |
| `submission` | object or null | The claim submission row. |
| `submission_items` | array | The payer's per-item verdict on the claim. |
| `payments` | array | Payment notice rows, newest first. |
| `paid_total` | number | What the payer says it has paid, counted once per UTR with the newest notice winning. |
| `enquiries` | array | Status and task enquiry rows, newest first. |
| `poll_notes` | array of strings | The error message of each poll that failed, for example a G9 error. Empty when all polls ran cleanly. |

Each per-item verdict (`preauth_items`, `submission_items`) is `{"sequence", "status", "eligible", "percent", "quantity", "deductible", "deduction_reason", "reason"}`, plus `benefit` and `submitted` when the payer sent those categories. It is an empty array before the payer has answered. FHIR: [F9. ClaimResponse](../fhir/F9-claimresponse.md).

```json
{
  "claim": {"id": 42, "claim_no": "NM-26-0SE000001", "status": "eligible", "stage": "preauth", "sub_stage": "requested"},
  "plan": null,
  "benefits": [],
  "admissions": [],
  "lines": [],
  "ruling": null,
  "required_documents": {"preauth": [], "claim": []},
  "forms": {"preauth": [], "claim": []},
  "documents": [],
  "stage": "preauth",
  "sub_stage": "requested",
  "preauth": {"id": 7, "claim_id": 42, "status": "submitting"},
  "preauth_items": [],
  "next_send": {"preauth": {"refused": "<reason>"}, "claim": {"refused": "<reason>"}},
  "adapter": "pmjay",
  "desk": "nhcx-payer-service",
  "predeterminations": [],
  "enhancement_lines": [],
  "queries": [],
  "submission": null,
  "submission_items": [],
  "payments": [],
  "paid_total": 0.0,
  "enquiries": [],
  "poll_notes": []
}
```

(Row objects abbreviated.)

#### A17P. PSEUDOCODE

When: a scripted driver or test sends `GET /claims/view/:caseid/state`. Each call runs the polls once; nothing polls on a timer.

```text
STATE(caseid):
  claim = claim row (D9) by id
  if none: respond 404 {"error": "No such claim"}

  poll_notes = []
  polls, in this order (each is the A10P loop for its leg):
    1 eligibility       only when claim.status == "checking"   reply applied as C2
    2 plan                                                     C4
    3 ruling                                                   C3
    4 claim                                                    C6
    5 preauth                                                  C5
    6 predeterminations (each asking row)                      C5
    7 cancellation                                             C7
    8 enquiries (each asking row)                              C8
  for each poll:
      try: run it                                  # it returns at once unless its leg is waiting
      on any error: append the error's text to poll_notes; go on to the next poll
      (a not-found from A10, G9 `TXN_NOT_FOUND`, is not an error here: the poll itself writes the leg to "error")

  stage, sub_stage = work out the case stage from claim, claim_preauth, claim_submission,
                     paid_total and the number of payments; when it differs, write
                     claim.stage and claim.sub_stage
  claim = claim row, read again; plan = claim_plan row

  respond 200 {
    claim:              claim row,
    plan:               plan row or null,
    benefits:           claim_plan_benefit rows of the plan ordered by seq, columns
                        id, kind, code, display, category_code, category_display, rate
                        ([] when no plan),
    admissions:         current IPD encounters (status not "finished") of patients whose ABHA
                        number has the same digits as claim.abha_number, newest period_start
                        first ([] when the claim has no ABHA digits),
    lines:              claim_line rows,
    ruling:             claim_auth row or null,
    required_documents: {preauth: [...], claim: [...]}      # the documents the payer named per stage
    forms:              {preauth: [...], claim: [...]}, each {url, title, questions}
                        from the claim_plan_form rows that stage has to carry,
    documents:          claim_document rows, columns id, code, label, filename,
                        content_type, size, stage (no payload),
    stage, sub_stage:   as worked out above,
    preauth:            claim_preauth row or null,
    preauth_items:      claim_preauth.items_json as a list, else [],
    next_send:          {preauth: <next pre-authorisation send kind>, claim: <next claim send kind>},
                        each {"refused": "<reason>"} when working it out fails,
    adapter:            the payer adapter's key,
    desk:               the payer adapter's desk or null,
    predeterminations:  claim_predetermination rows,
    enhancement_lines:  lines quoted since the pre-authorisation was decided,
    queries:            claim_query rows, each plus questions: the payer's lines,
    submission:         claim_submission row or null,
    submission_items:   claim_submission.items_json as a list, else [],
    payments:           claim_payment rows,
    paid_total:         claim_payment rows in id order whose payment_status is "paid" or
                        "cleared" (case ignored), leaving out rows with no utr whose
                        disposition contains "initiat" [PAYER](../references/PAYERS.md#markers); the last amount per utr (row id when
                        no utr) wins; summed and rounded to 2 places,
    enquiries:          claim_enquiry rows,
    poll_notes:         poll_notes
  }
```

#### A17U. USED BY
- Screens: [S6. Claim Detail](../screens/S6-claim-detail.md)
- APIs: [A10. Transaction Related](A10-txn-related.md), [A11. Transaction Dispatch](A11-txn-dispatch.md), [A12. Transaction FHIR](A12-txn-fhir.md)
- FHIR: [F6. Questionnaire](../fhir/F6-questionnaire.md)
- Database: [D9. claim](../database/D9-claim.md)
