# C10. Payment Notice

#### C10E. ENDPOINT
Delivered in-process by [G8. Receive](../gateway/G8-receive.md) for NHCX route `v1/paymentnotice/request`, passed to `C1.receive` with `delivery.type` `payment`. Payer-initiated; acknowledged by A8 automatically.

#### C10D. DESCRIPTION
The one leg the payer starts: it posts a notice when money moves, often twice per payment (initiated, then cleared) [PAYER](../references/PAYERS.md#markers). For payment notice the provider exposes `paymentnotice/request` and calls `paymentnotice/on_request`, the opposite way round from every other exchange.

**Matching by claim number, not correlation id.** Nothing of ours was sent, so the notice is matched by the case number it carries. The number is read, in order, from the PaymentNotice, the PaymentReconciliation, the Task, then the first entry's own resource; on each resource an identifier typed `CLN` wins, and an untyped identifier is taken rather than ignored (the live payer sends the number with no type) [SANDBOX](../references/PAYERS.md#markers). The bundle identifier is never tried: live it is a message uuid [SANDBOX](../references/PAYERS.md#markers). The number is looked up against the case (D9 `claim_no`), then the number each leg went out under (D20 `claim_ref`, then D18 `claim_ref`), because a cancel retires a number. Nothing matching: `unmatched`.

**Redelivery.** A notice whose correlation id is already on a payment row (D21 `correlation_id`) is `ignored`.

**Same payment, further along.** A notice whose `PaymentNotice.id` is already on a payment row of the same case updates that row instead of adding one (the IRDAI sandbox payer keeps the id) [SANDBOX](../references/PAYERS.md#markers), and is acknowledged again on its new thread.

**Acknowledgement is best-effort.** The notice is recorded first, then acknowledged through A8. A failed acknowledgement is kept on the row and the result is still `settled`, so G8 accepts the message; failing it would only have NHCX deliver it again.

#### C10Q. REQUEST
`fhir` is an F1 Bundle carrying a Task (what happened, in prose), an F13 PaymentNotice (amount and `paymentStatus`) and a PaymentReconciliation (date, UTR and the `detail[]` breakdown), usually with F17 Organizations. Some payers send only the PaymentNotice and PaymentReconciliation.

#### C10P. PSEUDOCODE

```
C10(envelope, corr):
    body = payload(envelope)
    notice = read_payment_notice(body)        # raises for a ProtocolResponse too
    if corr and a D21 row has correlation_id == corr: return "ignored"
    claim = claim_for_reference(notice.claim_ref)
    if none: return "unmatched"
    earlier = D21 row with claim_id == claim.id and notice_id == notice.notice_id
              (only when notice_id is set)
    in one transaction:
        values = notice (without details) + {claim_id, correlation_id: corr or null,
                  sender_code: x-hcx-sender_code or null, workflow_id: x-hcx-workflow_id or null,
                  received_at: now, notice_json: body}
        if earlier:
            leg_write(D21, earlier, values + {ack_status: "pending", ack_txn_id: null,
                      ack_correlation_id: null, acknowledged_at: null, ack_error: null})
            delete D22 rows of that payment
            payment = earlier
        else:
            payment = insert D21 values                      # ack_status defaults to "pending"
            restamp the case stage                           # stage "payment"
        insert D22 per detail {payment_id, seq, reference, type_code, type_display, date, amount}
    try:
        send the acknowledgement through A8
        leg_write(D21, payment, {ack_status: "sent", ack_txn_id, ack_correlation_id,
                                 acknowledged_at: now, ack_error: null})
    except a G7 send error:
        leg_write(D21, payment, {ack_status: "error", ack_error: message}
                                + ack_txn_id / ack_correlation_id when the error named them)
    return "settled"

read_payment_notice(body):
    notice = first PaymentNotice or {}; recon = first PaymentReconciliation or {}
    task = first Task or {}
    if notice and recon are both empty: raise Rejected("That is not a payment notice.")
    claim_ref = identifier(notice) or identifier(recon) or identifier(task)
                or identifier(first entry's resource)
        # identifier(r): the one typed "CLN", else the first untyped one with a value
    money = notice.amount or recon.paymentAmount
    return {claim_ref,
            notice_id: notice.id or null,
            disposition: recon.disposition or task.description or paymentStatus display
                         or recon.outcome or "Payment notice",
            payment_status: notice.paymentStatus code,
            payment_date: recon.paymentDate or first 10 characters of notice.created,
            amount: money.value, currency: money.currency,
            utr: recon.paymentIdentifier.value,
            details: per recon.detail[i]: seq i, reference (id, else identifier.value),
                     type_code, type_display, date, amount}

claim_for_reference(ref):
    D9 where claim_no == ref, else claim of newest D20 where claim_ref == ref,
    else claim of newest D18 where claim_ref == ref
```

#### C10S. RESPONSE
`settled` for a new or updated notice (whether or not the acknowledgement went), `ignored` for a redelivery, `unmatched` when no case answers to the number, or `rejected` with `That is not a payment notice.` when the bundle has neither a PaymentNotice nor a PaymentReconciliation (a `ProtocolResponse` included).

State changes:

| Table | Change |
|---|---|
| D21 claim_payment | new row (or the earlier row for the same `notice_id` updated): `claim_ref`, `notice_id`, `disposition`, `payment_status`, `payment_date`, `amount`, `currency`, `utr`, `correlation_id`, `sender_code`, `workflow_id`, `received_at`, `notice_json`; then `ack_status` `sent` with `ack_txn_id`, `ack_correlation_id`, `acknowledged_at`, or `error` with `ack_error` |
| D22 claim_payment_detail | one row per reconciliation detail (replaced on an update) |
| D9 claim | `stage` `payment`, `sub_stage` `paid` or `noticed` (restamped) |

#### C10U. USED BY
- Screens: [S12. Payments](../screens/S12-payments.md)
- APIs: [A8. Payment Notice Acknowledgement](../apis/A8-paymentnotice-on-request.md), [A15. Adjudicator Process Case](../apis/A15-adjudicator-process-case.md)
- Callbacks: [C1. Callback Door](C1-callback-door.md)
- FHIR: [F1. Bundle](../fhir/F1-bundle.md), [F13. PaymentNotice](../fhir/F13-paymentnotice.md)
- Database: [D21. claim_payment](../database/D21-claim-payment.md), [D22. claim_payment_detail](../database/D22-claim-payment-detail.md)
- Gateway: [G7. Send](../gateway/G7-send.md)
- Tests: [T11. IRDAI Payment Notice and Acknowledgement](../tests/T11-irdai-payment.md), [T18. PMJAY Payment Notice, Status Refusal and Cancel](../tests/T18-pmjay-payment-status-cancel.md)
