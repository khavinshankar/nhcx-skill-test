# A11. Transaction Dispatch

#### A11E. ENDPOINT
In-process: `ledger.dispatch(txn_id)`, a synchronous query of the [G9. Ledger](../gateway/G9-ledger.md), with `ledger.get(txn_id)` for NHCX's own refusal. Nothing goes on the wire.

#### A11D. DESCRIPTION
Returns what became of one transaction's dispatch to NHCX, as the G9 ledger recorded it. [G7. Send](../gateway/G7-send.md) dispatches inside the call (A2 to A6), with no queue and no retry, so by the time a transaction has an id its fate is decided: `accepted` when NHCX took it, `rejected` when NHCX answered outside 2xx (for example `NHCX-1010` when a thread is closed), `failed` when it never reached NHCX (for example `CERT_NOT_FOUND` for an unregistered recipient). Our own refused send has already come back from G7 as a failed send; this call is how a poll finds a refused dispatch on the thread, above all the payer's answer that NHCX refused, instead of waiting forever for a reply that cannot come.

It is used in two ways during a poll, always after A10 found no reply and, except where noted, after A13 found no protocol rejection:

Our own transaction (the `txn_id` of the leg):

| Leg | Asked | Read as failed when `status` is |
|---|---|---|
| Eligibility check (A2) | after A13 | `dispatch_failed` |
| Insurance plan (A3) | after A13 | `dispatch_failed` |
| Auth-requirements ruling (A2) | after A13 | `dispatch_failed` |
| Pre-authorisation (A4) | after the peer check and A13 | `dispatch_failed` |
| Claim (A5) | after the peer check and A13 | `dispatch_failed` |
| Status, reprocess, release (A6) | after the peer check and A13 | `dispatch_failed` |
| Predetermination (A4), cancellation (A6) | not asked | |

The peer's transaction (pre-authorisation, predetermination, claim and enquiry legs, checked before A13): when one G hosts both participants, the payer's outbound answer is on our thread in A10. The first `out` row that is not our own `txnId` and has `status` `failed` or `rejected` is looked up here. Its presence alone settles the leg, whatever this call returns: the pre-authorisation and claim legs record it as a refusal of their send (A4, A5), the predetermination and enquiry legs go to `error`, with "The payer answered, but NHCX refused its reply: <NHCX's `code: message` from the entry, else errorMessage or errorCode, first 300 characters>. Nothing more will arrive on this thread, submit again to open a new one." (ending "... refused its reply. Nothing more ..." when there is no detail, or when this call fails).

#### A11Q. REQUEST

The argument passed to G9 dispatch:

| Field | Type | Required | Value |
|---|---|---|---|
| `txn_id` | string | yes | the ledger row id: our leg's `txn_id`, or the peer row's `id` from A10 |

```
ledger.dispatch("7UPG002B")
```

#### A11S. RESPONSE
An object. The fields the app reads:

| Field | Meaning |
|---|---|
| `status` | `dispatch_failed` (ledger `failed` or `rejected`) means it will not be answered; `dispatched` (ledger `accepted` or `delivered`) or `delivery_failed` (an inbound row) means it is not a failed dispatch |
| `errorMessage` | the ledger's description of the failure |
| `errorCode` | the ledger's error code, used when there is no message |

The NHCX refusal itself (for example `NHCX-1010`) is not in this answer. It is on the full G9 entry, `ledger.get(txn_id).peer.response.error` (`code`, `message`), and is read from there on the peer and enquiry checks.

```json
{"txnId": "7UPG002B", "status": "dispatch_failed",
 "errorCode": "GATEWAY_HTTP_400", "errorMessage": "NHCX did not accept the message"}
```

What the leg shows when the dispatch failed:
- eligibility, plan, ruling, pre-authorisation: `errorMessage`, else `errorCode`, else "Dispatch to NHCX failed.", and the leg is `error`.
- claim: the same text, recorded as a refusal of the claim send (see A5).
- enquiries: NHCX's `<code>: <message>` from the entry's `peer.response.error` when it carries a code (message defaulting to "NHCX refused the request."), else `errorMessage`, else `errorCode`, else "Dispatch to NHCX failed.". A failure of this call itself is ignored on this leg.

A leg whose dispatch is not failed keeps waiting. Any other failure of this call on the eligibility, plan, ruling, pre-authorisation or claim legs is a poll failure (see A10).

#### A11P. PSEUDOCODE

When: inside the A10 poll, after A10 found no reply. The whole loop is in A10P; the parts that call this endpoint are below. Rows written: `claim` ([D9](../database/D9-claim.md)), `claim_plan` ([D10](../database/D10-claim-plan.md)), `claim_auth` ([D13](../database/D13-claim-auth.md)), `claim_preauth` ([D18](../database/D18-claim-preauth.md)), `claim_predetermination` ([D19](../database/D19-claim-predetermination.md)), `claim_submission` ([D20](../database/D20-claim-submission.md)), `claim_enquiry` ([D29](../database/D29-claim-enquiry.md)).

```text
POLL(leg, row):                                   # outline, full version in A10P
  related = A10(row.txn_id)
  reply found -> apply as C2 to C8; stop
  error = PEER_DISPATCH_ERROR(related, row.txn_id)          # preauth, predetermination, claim, enquiry
       or PROTOCOL_REJECTION(...)                          # A13
       or OWN_DISPATCH_ERROR_ENQUIRY(row.txn_id)           # enquiry only
  error -> write the refusal (A10P WRITE_REFUSAL); stop
  eligibility, plan, ruling, preauth, claim: OWN_DISPATCH_CHECK(row)
  otherwise: still waiting

PEER_DISPATCH_ERROR(related, own_txn_id):
  for entry in related, in the order listed:
      if entry.direction != "out" or entry.id == own_txn_id
         or entry.status not in ("failed", "rejected"):
          continue
      try:
          dispatch = ledger.dispatch(entry.id)    # G9 Ledger, in-process
      on G9 error:
          dispatch = none
      detail = NHCX_REFUSAL(entry.id)
               or dispatch.errorMessage or dispatch.errorCode or ""   (when dispatch is an object)
      if detail:
          return "The payer answered, but NHCX refused its reply: " + first 300 characters of detail
                 + " Nothing more will arrive on this thread, submit again to open a new one."
      return "The payer answered, but NHCX refused its reply. Nothing more will arrive on this thread, submit again to open a new one."
  return none                                     # only the first matching row is looked at

OWN_DISPATCH_CHECK(row):                          # eligibility, plan, ruling, preauth, claim
  dispatch = ledger.dispatch(row.txn_id)
  on G9 error: raise                              # poll failure, text goes to poll_notes (A17)
  if dispatch.status == "dispatch_failed":
      message = dispatch.errorMessage or dispatch.errorCode or "Dispatch to NHCX failed."
      eligibility: write claim:            status = "error", error_message = message
      plan:        write claim_plan:       status = "error", error_message = message
      ruling:      write claim_auth:       status = "error", error_message = message
      preauth:     write claim_preauth:    status = "error", error_message = message
      claim:       write claim_submission as a refused send (A10P WRITE_REFUSAL, claim)
  else: still waiting

OWN_DISPATCH_ERROR_ENQUIRY(txn_id):
  try:
      dispatch = ledger.dispatch(txn_id)
  on G9 error:
      return none                                 # ignored on this leg
  if dispatch.status != "dispatch_failed":
      return none
  refusal = NHCX_REFUSAL(txn_id)
  if refusal: return refusal
  return dispatch.errorMessage or dispatch.errorCode or "Dispatch to NHCX failed."

NHCX_REFUSAL(id):                                 # NHCX's own refusal, off the full G9 entry
  try:
      entry = ledger.get(id)                      # G9 Ledger, in-process
  on G9 error:
      return none
  nhcx = entry.peer.response.error                # NHCX's body when it answered non-2xx
  if nhcx is an object with a code:
      return nhcx.code + ": " + (nhcx.message or "NHCX refused the request.")
  return none
```

#### A11U. USED BY
- Screens: [S3. Policy Discovery](../screens/S3-policy-discovery.md), [S7. Insurance Plan](../screens/S7-insurance-plan.md), [S8. Line Items](../screens/S8-line-items.md), [S9. Pre-authorisation](../screens/S9-preauthorisation.md), [S11. Claim Submission](../screens/S11-claim-submission.md)
- APIs: [A2. Coverage Eligibility Check](A2-coverage-eligibility-check.md), [A3. Insurance Plan Request](A3-insurance-plan-request.md), [A4. Pre-auth Submit](A4-preauth-submit.md), [A5. Claim Submit](A5-claim-submit.md), [A6. Task Submit (cancel, status, reprocess, release)](A6-task-submit.md), [A10. Transaction Related](A10-txn-related.md), [A13. Transaction List](A13-txn-list.md), [A17. Claim State](A17-claim-state.md)
- Gateway: [G9. Ledger](../gateway/G9-ledger.md)
