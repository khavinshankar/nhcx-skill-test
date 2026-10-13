# C6. Predetermination

#### C6E. ENDPOINT
Delivered in-process by [G8. Receive](../gateway/G8-receive.md) for NHCX route `v1/preauth/submit` (the route the exchange offers; NHA also lists `v1/predetermination/submit`, which the reference never saw used [REF](../references/PAYERS.md#markers)), passed to `C1.receive`, classified `predetermination` because the bundle holds a `Claim` with `use` `predetermination` ([F8. Claim](../fhir/F8-claim.md)). Answered inside the same delivery by [A10. Predetermination Quote](../apis/A10-predetermination-quote.md) on `v1/preauth/on_submit`, on the request's own correlation id, with a ClaimResponse whose `use` is `predetermination`.

#### C6D. DESCRIPTION
"What would you pay for this?" The same shape as a pre-authorisation, asked before anybody is admitted. It is the one message this payer decides by rules: priced at once and answered with a ClaimResponse that binds nobody. The hospital learns what the policy would allow and what it would cut, no case opens, and the only thing recorded is the quote ([D29. predetermination_quote](../database/D29-predetermination-quote.md)).

**Who it is about.** The enrolment is found as a pre-authorisation's is ([C4. Pre-auth Submit](C4-preauth-submit.md)): in force first, else the most recent cover the person had. A person this payer does not cover is still answered, because the hospital's poll is waiting either way: the quote then says no enrolment matched and allows nothing.

**Pricing.** A transient case is shaped from the submission (lines given ids of their own, every line pending) and read against the pricing rules ([A10. Predetermination Quote](../apis/A10-predetermination-quote.md)): the enrolment and its product, the member, the member's other cases. The rules produce a verdict (`approve`, `partial`, `reject`, `query`) and findings, one per thing noticed (which rule, how bad, where in the Claim it points, what was sent against what was required, and for a reduction what the engine would allow on the line). The findings become the per-item adjudication and process notes of the answer ([F9. ClaimResponse](../fhir/F9-claimresponse.md)).

**Redelivery.** A quote already holds this correlation id ([D29. predetermination_quote](../database/D29-predetermination-quote.md) `correlation_id`, unique): `ignored`, with the quote and its verdict named.

**Sandbox scenarios.** The member id may select a scenario and a fault; the answer is then broken on its way out (held, dropped, doubled, malformed, sent on a stale thread, or saying the opposite of the verdict) and the quote records which [SANDBOX](../references/PAYERS.md#markers) ([A19. Sandbox Scenarios](../apis/A19-sandbox-scenarios.md)).

#### C6Q. REQUEST
`fhir` is an [F1. Bundle](../fhir/F1-bundle.md) Bundle carrying [F8. Claim](../fhir/F8-claim.md) Claim (`use: predetermination`) with the same resources as a pre-authorisation, without answered forms. Headers read: `x-hcx-sender_code`, `x-hcx-recipient_code`, `x-hcx-correlation_id`, `x-hcx-workflow_id` (echoed; hospitals send 12 [PAYER](../references/PAYERS.md#markers)).

#### C6P. PSEUDOCODE

```
C6(in, submission):                                       # submission = F8 parse, use predetermination
    existing = D29 where correlation_id == in.corr
    if existing: return "ignored"                          # outcome {status: duplicate, quote_id, verdict}

    subscription, member = none, none
    found = find_enrolment(submission.handles())           # C1 shared rule; none is still answered
    if found: subscription = found; member = D5[subscription.member_id]

    record = transient_case(case_from_submission(submission, subscription, member, in))   # never stored
    record.documents, _ = resolve_documents(submission.documents)
    if record.member_id == "": record.member_id = submission.member_id or submission.subscriber_id

    evaluation = A10.price(record, stage "predetermination")   # rules: verdict, findings; refuse on no rules loaded
        on failure: raise Error("The predetermination could not be priced")

    cover = {member, subscription, policy: D12[subscription.policy_id] if any}
    bundle = A10.quote_response({payer: in.payer, payer_code: in.recipient, case: record, cover,
                                 use: "predetermination", claim_ref: submission.claim_ref,
                                 recipient: in.sender, findings: evaluation.findings})
    ack = answer(in, bundle, "v1/preauth/on_submit",
                 workflow = in.workflow_id, status = "response.complete", what = "predetermination")
        # under a sandbox fault scenario the send is dispatched through A19 instead [SANDBOX](../references/PAYERS.md#markers)

    D29.insert {correlation_id: in.corr, sender_code: in.sender, claim_ref: submission.claim_ref,
                member_id: subscription.member_id, subscription_id: subscription.id,
                patient_name: record.patient_name, total_claimed: record.total_claimed,
                total_quoted: record.total_approved, verdict: evaluation.verdict,
                findings: evaluation.findings, answer_txn_id: ack.txn_id, scenario,
                request: payload(in.envelope), response: bundle}
    D31 audit {action: "predetermination.answered", entity: "nhcx_txn", id: in.ledger_id,
               detail: "<sender> asked, correlation <corr>, <verdict> quoted <quoted> of <claimed>, answer txn <ack.txn_id>"}
    return "settled"                                       # outcome {status: quoted, quote_id, verdict, total_quoted, findings, txn_id}
```

#### C6S. RESPONSE
`settled` when the quote went back; `ignored` for a redelivery; `rejected` when the bundle cannot be read or the gateway refuses the answer; `error` when the rules are not loaded, the gateway is not configured, or it is unreachable, so NHCX redelivers.

State changes: one [D29. predetermination_quote](../database/D29-predetermination-quote.md) row (the request, the answer, the verdict and findings, the answer transaction); one [D31. audit_log](../database/D31-audit-log.md) audit row. No case, no line, no document is written. The quotes are listed on the desk ([S3. Case Desk](../screens/S3-case-desk.md) lists them beside the cases in the reference [REF](../references/PAYERS.md#markers)).

#### C6U. USED BY
- Screens: [S8. Procedures](../screens/S8-procedures.md)
- APIs: [A10. Predetermination Quote](../apis/A10-predetermination-quote.md), [A18. Provider Driver](../apis/A18-provider-driver.md)
- Callbacks: [C1. Callback Door](C1-callback-door.md)
- FHIR: [F1. Bundle](../fhir/F1-bundle.md), [F8. Claim](../fhir/F8-claim.md)
- Database: [D29. predetermination_quote](../database/D29-predetermination-quote.md)
- Tests: [T11. Predetermination Quoted](../tests/T11-predetermination-quoted.md)
