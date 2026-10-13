# A11. Transaction Related

#### A11E. ENDPOINT
In-process: `ledger.related(txn_id)`, a synchronous query of the [G9. Ledger](../gateway/G9-ledger.md). Nothing goes on the wire.

#### A11D. DESCRIPTION
Lists every ledger row on the same correlation thread as one transaction, in both directions. It is the first step of every poll: given the `txn_id` a payer-started send was acknowledged with (the [G7. Send](../gateway/G7-send.md) result's `txn_id`, which is its ledger id), it shows whether the hospital's reply has been taken in by [G8. Receive](../gateway/G8-receive.md).

Polling is the fallback to the callback ([C1. Callback Door](../callbacks/C1-callback-door.md)). Nothing polls on a timer. Each load of the case desk ([S3. Case Desk](../screens/S3-case-desk.md)) and the payments desk ([S10. Payments](../screens/S10-payments.md)), and each read of the exchange log ([A15. Case Exchange Log](A15-case-exchange.md)), runs one poll per thread still waiting on the hospital. A reply found by a poll is applied exactly as the matching callback applies it. The reference payer relies on the callback alone and reads only its own exchange table [REF](../references/PAYERS.md#markers); this skill adds the poll, as the provider side has it, so a missed delivery costs only speed.

This payer waits on the hospital on two kinds of thread. Everything else the hospital sends starts a thread of its own and arrives as a callback (C2 to C8, C10), so there is nothing to poll for.

| Thread | Polled while | `txn_id` sent | Reply looked for | Applied as |
|---|---|---|---|---|
| Query ([A5. Query Request](A5-query-request.md)) | the case is `queried` and D19 `nhcx_query_correlation_id` is set | D19 `nhcx_query_txn_id` | newest inbound carrying a `Communication` | [C9. Communication](../callbacks/C9-communication.md) |
| Payment notice ([A6. Payment Notice](A6-payment-notice.md)) | the payment has D30 `nhcx_notice_txn_id` and `nhcx_acknowledged_at` is null | D30 `nhcx_notice_txn_id` | newest inbound carrying a `Task` whose output status is `paymentack` | [C11. Payment Acknowledgement](../callbacks/C11-payment-acknowledgement.md) |

How the rows are filtered:
- Only `direction` `in` rows are considered, and rows whose `sender` is one of this payer's own participant codes are skipped. When one gateway hosts both participants (hosted codes, [G2. Configuration and Participants](../gateway/G2-configuration.md); the sandbox loopback), the hospital's inbound copy of our own request is on the thread too. Rows are read newest first (the order G9 lists them), each through [A12. Transaction FHIR](A12-txn-fhir.md), until one carries the resource looked for.
- A reply already applied is not applied twice: [C9. Communication](../callbacks/C9-communication.md) and [C11. Payment Acknowledgement](../callbacks/C11-payment-acknowledgement.md) each dedupe on the message's `x-hcx-api_call_id` against D28, the same rule the door applies to a redelivery.
- When no reply is found, the `direction` `out` row of our own send is read for its `status`: `failed` or `rejected` means the send never reached NHCX, and the thread is marked so on the case (below). A query the exchange refused is sent again from the desk ("Send the query again", [A5. Query Request](A5-query-request.md)).

**Worked example, the query thread.** The desk queries case `CASE-1017` at 10:14; [A5. Query Request](A5-query-request.md) sends the CommunicationRequest and stores the minted correlation id and the ledger id `7UPG002K` on the case. The hospital answers at 10:31, but the delivery to this payer's inbound route fails at the proxy, so NHCX's five redeliveries all end in `error` and the Communication is on the ledger only. At 10:40 the adjudicator opens the case: the poll reads the thread on `7UPG002K`, finds the inbound row `7UPG002R` from `<facility code>`, reads its bundle through [A12. Transaction FHIR](A12-txn-fhir.md), sees a `Communication`, and hands it to `C1.receive` as a redelivery. [C9. Communication](../callbacks/C9-communication.md) files the reply, the queried lines go back in front of the adjudicator, and the page the desk renders already shows it. Had the hospital not answered yet, the poll would have read this payer's own `out` row: `accepted` means the query is with the exchange and the thread keeps waiting; `rejected` or `failed` means the query never got through, and the desk offers "Send the query again".

**Worked example, a payment notice.** Finance completes `PAY-2026-0007` and [A6. Payment Notice](A6-payment-notice.md) records `7UPG004A` on the payment. The hospital's acknowledgement Task arrives the next morning while the application is being restarted, so it too is on the ledger only. The payments desk opens, polls every notice without `nhcx_acknowledged_at`, finds the Task with output status `paymentack`, and [C11. Payment Acknowledgement](../callbacks/C11-payment-acknowledgement.md) stamps the payment acknowledged.

#### A11Q. REQUEST

The argument passed to G9 related:

| Field | Type | Required | Value |
|---|---|---|---|
| `txn_id` | string | yes | the `txn_id` stored from the send's acknowledgement (the G7 result's `txn_id`): D19 `nhcx_query_txn_id` or D30 `nhcx_notice_txn_id` |

```
ledger.related("7UPG002K")
```

#### A11S. RESPONSE
An array of G9 ledger rows on the transaction's correlation id, newest first, the transaction itself included (at most 500). The fields the application reads:

| Field | Meaning |
|---|---|
| `id` | the row's own ledger id, passed to A12 |
| `direction` | `in` (taken in by G8) or `out` (sent by G7) |
| `sender` | participant code of the sender |
| `status` | the row's ledger state: `accepted`, `rejected`, `failed` (out), `delivered`, `delivery_failed`, `rejected` (in); `failed` and `rejected` on our own `out` row mean the send never got through |
| `api_call_id` | the message's identity, for the dedupe in C9 and C11 |

```json
[{"id": "7UPG002K", "direction": "out", "sender": "<payer code>", "status": "accepted", "api_call_id": "call-ours"},
 {"id": "7UPG002R", "direction": "in", "sender": "<facility code>", "status": "delivered", "api_call_id": "call-theirs"}]
```

Errors:
- Transaction not found (G9 error `TXN_NOT_FOUND`, or `LEDGER_DISABLED` when the ledger is turned off) is final, not a hiccup: the G9 ledger no longer has the transaction (typically it was reset or pruned after the send), so no reply can ever be matched by polling. The thread is marked on the case, by thread:
  - query: a timeline event ([D26. case_timeline](../database/D26-case-timeline.md), type `warning`) "The gateway no longer has the query transaction, its ledger was reset after the query was sent. Send the query again.", and D19 `nhcx_query_txn_id` is cleared so the desk offers "Send the query again" ([S3. Case Desk](../screens/S3-case-desk.md)).
  - payment notice: a timeline event "The gateway no longer has the payment notice transaction, its ledger was reset after the notice was sent. The hospital's acknowledgement can only arrive through the callback now." Nothing on D30 changes.
- Any other failure leaves the thread waiting. The desk shows the muted note "Could not poll the gateway: <error>" (the G9 error's message) beside the thread; the exchange log collects these messages in `poll_notes` ([A15. Case Exchange Log](A15-case-exchange.md)).

#### A11P. PSEUDOCODE

When: once per waiting thread on every load of S3 Case Desk (query thread of that case), every load of S10 Payments (every unacknowledged notice listed), and every A15 read. No timer. One pass, no retry inside a poll.

Rows: `case` ([D19. case](../database/D19-case.md)), `payment` ([D30. payment](../database/D30-payment.md)), `nhcx_delivery` ([D28. nhcx_delivery](../database/D28-nhcx-delivery.md)), `case_timeline` ([D26. case_timeline](../database/D26-case-timeline.md)).

```text
THREADS (row, waiting when, txn column, reply resource, applied as):
  query     case      adjudication_status == "queried" and nhcx_query_correlation_id set   nhcx_query_txn_id     Communication          C9
  notice    payment   nhcx_notice_txn_id set and nhcx_acknowledged_at null                nhcx_notice_txn_id    Task (paymentack)      C11   (every such payment)

POLL(thread, row):
  if row is missing or not waiting or row.<txn column> is blank:
      return unchanged
  try:
      related = ledger.related(row.<txn column>)      # G9 Ledger, in-process
  on G9 error e:
      if e is transaction not found:
          NOT_FOUND(thread, row)
          return changed
      raise e                                         # poll failure; A15 puts e's text in poll_notes

  envelope, bundle = FIND_REPLY(related, thread.reply resource)      # A12
  if bundle found:
      if D28 holds envelope.jwe_headers."x-hcx-api_call_id": return unchanged   # already taken in
      apply envelope as thread.applied-as (C9 or C11), through C1.receive with
          delivery = {path: the row's path, type from the path, correlation_id, api_call_id,
                      redelivery: true, participant: row's recipient}
      return changed                                  # C9 / C11 write D28 and the case

  own = the direction "out" row whose id == row.<txn column>
  if own and own.status in ("failed", "rejected"):
      note the thread as refused (timeline event, type "error",
           "NHCX did not take the " + ("query" if thread == query else "payment notice") +
           ": " + (own.error.message or own.error.code))
      if thread == query: clear case.nhcx_query_txn_id     # the desk offers "Send the query again"
      return changed
  return unchanged                                    # still waiting

NOT_FOUND(thread, row):
  if thread == query:
      append timeline (D26): type "warning",
          "The gateway no longer has the query transaction, its ledger was reset after the query was sent. Send the query again."
      write case: nhcx_query_txn_id = null
  else:
      append timeline (D26): type "warning",
          "The gateway no longer has the payment notice transaction, its ledger was reset after the notice was sent. The hospital's acknowledgement can only arrive through the callback now."
```

FIND_REPLY is in [A12. Transaction FHIR](A12-txn-fhir.md). A reply found here goes through the same door as a delivery ([C1. Callback Door](../callbacks/C1-callback-door.md)), so the dedupe, the archive and the outcome are the callback's.

#### A11U. USED BY
- APIs: [A5. Query Request](A5-query-request.md), [A6. Payment Notice](A6-payment-notice.md), [A12. Transaction FHIR](A12-txn-fhir.md), [A15. Case Exchange Log](A15-case-exchange.md)
- Callbacks: [C11. Payment Acknowledgement](../callbacks/C11-payment-acknowledgement.md)
- Gateway: [G1. Embedding](../gateway/G1-embedding.md), [G7. Send](../gateway/G7-send.md), [G9. Ledger](../gateway/G9-ledger.md)
- Tests: [T1. Test Configuration](../tests/T1-test-configuration.md), [T2. Test Runners](../tests/T2-test-runners.md), [T8. Pre-auth Queried and Answered](../tests/T8-preauth-queried.md), [T15. Payment Notices and Acknowledgement](../tests/T15-payment-noticed.md)
