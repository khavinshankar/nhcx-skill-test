# A10. Transaction Related

#### A10E. ENDPOINT
In-process: `ledger.related(txn_id)`, a synchronous query of the [G9. Ledger](../gateway/G9-ledger.md). Nothing goes on the wire.

#### A10D. DESCRIPTION
Lists every ledger row on the same correlation thread as one transaction, in both directions. It is the first step of every poll: given the `txn_id` a send was acknowledged with (A2 to A6, the G7 result's `txn_id`, which is its ledger id), it shows whether the payer's reply has been taken in by [G8. Receive](../gateway/G8-receive.md).

Polling is the fallback to the callback ([C1. Callback Door](../callbacks/C1-callback-door.md)). Nothing polls on a timer. Each load of the case screen, and each read of the case state JSON (A17), runs one poll per leg still out with the payer. A reply found by a poll is applied exactly as the matching callback applies it:

| Leg | Polled while | `txnId` sent | Reply looked for | Reply |
|---|---|---|---|---|
| Eligibility check (A2) | case `checking` | the case's `txn_id` | newest inbound carrying a `CoverageEligibilityResponse` | [C2. Coverage Eligibility Verdict](../callbacks/C2-coverage-eligibility-on-check.md) |
| Insurance plan (A3) | plan `fetching` | the plan's `txn_id` | newest inbound carrying an `InsurancePlan` | [C4. Insurance Plan Reply](../callbacks/C4-insuranceplan-on-request.md) |
| Auth-requirements ruling (A2) | ruling `checking` | the ruling's `txn_id` | newest inbound carrying a `CoverageEligibilityResponse` | [C3. Authorisation Requirements Ruling](../callbacks/C3-auth-requirements-on-check.md) |
| Pre-authorisation (A4) | `submitting` | the pre-authorisation's `txn_id` | newest inbound carrying a `ClaimResponse` | [C5. Pre-auth Reply](../callbacks/C5-preauth-on-submit.md) |
| Predetermination (A4) | each quote `asking` | that quote's `txn_id` | newest inbound carrying a `ClaimResponse` | [C5. Pre-auth Reply](../callbacks/C5-preauth-on-submit.md) |
| Claim (A5) | `submitting` | the submission's `txn_id` | newest inbound carrying a `ClaimResponse`; when that reply is already applied the leg keeps waiting (after a reprocess the old verdict is still on the thread) | [C6. Claim Reply](../callbacks/C6-claim-on-submit.md) |
| Cancellation (A6) | pre-authorisation `cancelling`, or a refused cancel within 15 minutes of the refusal | the `cancel_txn_id` | every `Task` reply on the thread, both directions (see below) | [C7. Cancel Reply](../callbacks/C7-cancel-on-submit.md) |
| Status, reprocess, release (A6) | each enquiry `asking` | that enquiry's `txn_id` | newest inbound carrying a `Task` | [C8. Enquiry Reply](../callbacks/C8-enquiry-on-submit.md) |

How the rows are filtered:
- For the newest-reply legs, only `direction` `in` rows are considered, and rows whose `sender` is the facility's own participant code are skipped. When one G hosts both participants (hosted codes, [G2. Configuration and Participants](../gateway/G2-configuration.md); the sandbox loopback), the payer's inbound copy of our own request and NHCX's redeliveries of it are on the thread too, and for a Task it carries the very resource the reply is made of. Rows are read newest first (the order G9 lists them), each through A12, until one carries the resource looked for.
- For the cancellation, both directions are read (when one G hosts both participants, the payer's own outbound copy of its answer is the answer even when NHCX never delivered it inbound), our own sends are skipped, and rows repeating an `api_call_id` already seen are skipped. Every Task reply is read and an acceptance wins; a refusal is applied only when no acceptance is on the thread.
- On the pre-authorisation, predetermination, claim and enquiry legs, when no reply is found, the `direction` `out` rows other than our own `txnId` whose `status` is `failed` or `rejected` are the payer's answer that NHCX refused; A11 is asked why (see A11).

When no reply is found the poll continues with A13 (protocol rejections) and A11 (dispatch state).

#### A10Q. REQUEST

The argument passed to G9 related:

| Field | Type | Required | Value |
|---|---|---|---|
| `txn_id` | string | yes | the `txn_id` stored from the send's acknowledgement (the G7 result's `txn_id`) |

```
ledger.related("7UPG002K")
```

#### A10S. RESPONSE
An array of G9 ledger rows on the transaction's correlation id, newest first, the transaction itself included (at most 500). The fields the app reads:

| Field | Meaning |
|---|---|
| `id` | the row's own ledger id, passed to A12 or A11 |
| `direction` | `in` (taken in by G8) or `out` (sent by G7) |
| `sender` | participant code of the sender |
| `status` | the row's ledger state: `accepted`, `rejected`, `failed` (out), `delivered`, `delivery_failed`, `rejected` (in); `failed` and `rejected` on an `out` row are read as refused |
| `api_call_id` | used to drop redeliveries of one message on the cancel thread |

```json
[{"id": "01CANCEL", "direction": "out", "sender": "<facility code>", "api_call_id": "call-ours"},
 {"id": "01CANCEL-ACK", "direction": "out", "sender": "<payer code>", "api_call_id": "call-accepted"},
 {"id": "01CANCEL-NO", "direction": "in", "sender": "<payer code>", "api_call_id": "call-refused"}]
```

Errors:
- Transaction not found (G9 error `TXN_NOT_FOUND`, or `LEDGER_DISABLED` when the ledger is turned off) is final, not a hiccup: the G9 ledger no longer has the transaction (typically it was reset or pruned after the send), so no reply can ever be matched. The leg is set to `error` with, by leg:
  - eligibility: "The gateway no longer has this transaction, its ledger was reset after the check was sent. Send the eligibility check again."
  - plan: "... after the request was sent. Fetch again."
  - ruling: "... after the check was sent. Check again."
  - pre-authorisation: "... after the preauth was sent. Submit again."
  - claim: "... after the claim was sent. Submit again."
  - cancellation: "The gateway no longer has the cancel transaction, its ledger was reset after it was sent. Cancel again." (a refused cancel still in its grace window is left as it is)
  - predetermination and enquiries: "The gateway no longer has this transaction. Ask again."
- Any other failure leaves the leg waiting. On the eligibility and plan tabs it shows as the muted note "Could not poll the gateway: <error>" (the G9 error's message); the other legs show nothing and keep saying they are awaiting. The case state JSON collects these messages in `poll_notes`.

#### A10P. PSEUDOCODE

When: once per leg on every load of S6 Claim Detail (and its Refresh) and on every A17 read. No timer. One pass, no retry inside a poll.

Rows: `claim` ([D9](../database/D9-claim.md)), `claim_plan` ([D10](../database/D10-claim-plan.md)), `claim_auth` ([D13](../database/D13-claim-auth.md)), `claim_preauth` ([D18](../database/D18-claim-preauth.md)), `claim_predetermination` ([D19](../database/D19-claim-predetermination.md)), `claim_submission` ([D20](../database/D20-claim-submission.md)), `claim_enquiry` ([D29](../database/D29-claim-enquiry.md)).

```text
LEGS (row, waiting status, reply resource, applied as, protocol-scan type, send time):
  eligibility      claim                   "checking"    CoverageEligibilityResponse  C2  coverage   checked_at
  plan             claim_plan              "fetching"    InsurancePlan                C4  insurance  requested_at
  ruling           claim_auth              "checking"    CoverageEligibilityResponse  C3  coverage   requested_at
  preauth          claim_preauth           "submitting"  ClaimResponse                C5  preauth    submitted_at
  predetermination claim_predetermination  "asking"      ClaimResponse                C5  preauth    requested_at   (every row)
  claim            claim_submission        "submitting"  ClaimResponse                C6  claim      submitted_at
  enquiry          claim_enquiry           "asking"      Task                         C8  task *     requested_at   (every row)
  (* "status" instead when a status enquiry's send route ends in /status; it goes out on the task route, so "task")

POLL(leg, row):
  if row is missing or row.status != leg.waiting status or row.txn_id is blank:
      return unchanged
  try:
      related = ledger.related(row.txn_id)      # G9 Ledger, in-process
  on G9 error e:
      if e is transaction not found:
          write row: status = "error", error_message = <the leg's not-found message, A10S>
          return changed
      raise e                                   # poll failure; A17 puts e's text in poll_notes

  envelope, bundle = FIND_REPLY(related, leg.reply resource)        # A12
  if bundle found:
      claim leg only: if the reply's x-hcx-api_call_id equals row.api_call_id
                      (or, with no api_call_id and row not "submitting", the
                      reply's outcome and adjudication equal the row's):
                      return unchanged              # the verdict already taken in
      apply bundle as leg.applied-as (C2 to C8)     # same parser, same statuses as the callback
      return changed

  error = none
  if leg in (preauth, predetermination, claim, enquiry):
      error = PEER_DISPATCH_ERROR(related, row.txn_id)              # A11
  if no error:
      error = PROTOCOL_REJECTION(row.correlation_id, row.<send time>, leg.scan type)   # A13
  if no error and leg == enquiry:
      error = OWN_DISPATCH_ERROR_ENQUIRY(row.txn_id)                # A11
  if error:
      WRITE_REFUSAL(leg, row, error)
      return changed

  if leg in (eligibility, plan, ruling, preauth, claim):
      dispatch = ledger.dispatch(row.txn_id)                        # A11; a failure here is a poll failure
      if dispatch.status == "dispatch_failed":
          WRITE_REFUSAL(leg, row, dispatch.errorMessage or dispatch.errorCode
                                  or "Dispatch to NHCX failed.")
          return changed
  return unchanged                                # still waiting

WRITE_REFUSAL(leg, row, message):
  eligibility, plan, ruling, predetermination, enquiry:
      write row: status = "error", error_message = message
  preauth:
      write claim_preauth: error_message = message,
            status = "approved" if row.submission_kind in ("enhancement", "enhancement_resubmit") else "error",
            correlation_id = row.thread_correlation_id   (only when set)
  claim:
      write claim_submission: error_message = message, status = "error",
            correlation_id = row.thread_correlation_id   (only when set)
      if row.submission_kind == "claim_query_response":
            status = "queried", disposition = row.disposition or row.query_note
  a write to claim_preauth or claim_submission also re-works claim.stage and claim.sub_stage

CANCEL POLL (claim_preauth row, cancel_txn_id):
  if row missing or row.cancel_txn_id blank: return unchanged
  refused = row.status == "approved"
            and row.error_message == "The payer did not accept the cancellation."
            and row.settled_at is less than 15 minutes old
  if row.status != "cancelling" and not refused: return unchanged
  try:
      related = ledger.related(row.cancel_txn_id)
  on G9 error e:
      if e is transaction not found:
          if refused: return unchanged
          write claim_preauth: status = "error", error_message =
              "The gateway no longer has the cancel transaction, its ledger was reset after it was sent. Cancel again."
          return changed
      raise e
  replies = TASK_REPLIES(related)                  # A12, newest first
  if any reply is an acceptance (per C7):
      apply the first acceptance as C7; return changed
  if refused: return unchanged                     # keep looking for a late acceptance
  if replies not empty:
      apply the newest reply as C7; return changed
  error = PROTOCOL_REJECTION(row.cancel_correlation_id, row.cancel_requested_at, "task")   # A13
  if error:
      write claim_preauth: status = "error", error_message = error; return changed
  return unchanged
```

#### A10U. USED BY
- Screens: [S3. Policy Discovery](../screens/S3-policy-discovery.md), [S7. Insurance Plan](../screens/S7-insurance-plan.md), [S8. Line Items](../screens/S8-line-items.md), [S9. Pre-authorisation](../screens/S9-preauthorisation.md), [S11. Claim Submission](../screens/S11-claim-submission.md)
- APIs: [A2. Coverage Eligibility Check](A2-coverage-eligibility-check.md), [A3. Insurance Plan Request](A3-insurance-plan-request.md), [A4. Pre-auth Submit](A4-preauth-submit.md), [A5. Claim Submit](A5-claim-submit.md), [A6. Task Submit (cancel, status, reprocess, release)](A6-task-submit.md), [A11. Transaction Dispatch](A11-txn-dispatch.md), [A12. Transaction FHIR](A12-txn-fhir.md), [A13. Transaction List](A13-txn-list.md), [A17. Claim State](A17-claim-state.md)
- Callbacks: [C1. Callback Door](../callbacks/C1-callback-door.md)
- FHIR: [F1. Bundle](../fhir/F1-bundle.md)
- Database: [D18. claim_preauth](../database/D18-claim-preauth.md), [D19. claim_predetermination](../database/D19-claim-predetermination.md)
- Gateway: [G1. Embedding](../gateway/G1-embedding.md), [G7. Send](../gateway/G7-send.md), [G9. Ledger](../gateway/G9-ledger.md)
- Tests: [T1. Test Configuration](../tests/T1-test-configuration.md), [T2. Test Runners](../tests/T2-test-runners.md)
