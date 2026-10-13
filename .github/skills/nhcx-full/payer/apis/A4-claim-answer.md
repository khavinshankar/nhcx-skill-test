# A4. Claim Answer

#### A4E. ENDPOINT
In-process: `gateway.send("v1/claim/on_submit", envelope)`, [G7. Send](../gateway/G7-send.md), which encrypts it and posts it to NHCX for the hospital, on the thread the claim arrived on: `POST {nhcx}/v1/claim/on_submit`. No answer to it is awaited.

It answers [C5. Claim Submit](../callbacks/C5-claim-submit.md). The hospital's desk takes it in as its claim reply, reads outcome and adjudication together, and keeps the pre-authorisation reference it carries.

#### A4D. DESCRIPTION
The claim leg is answered exactly as the pre-authorisation leg ([A3. Pre-auth Answer](A3-preauth-answer.md)) is, on a different thread: the claim's own correlation id ([D19. case](../database/D19-case.md) `nhcx_claim_correlation_id`), which [C5. Claim Submit](../callbacks/C5-claim-submit.md) wrote when it filed the bill.

**1. The acknowledgement**, sent by the application when C5 has filed the claim: `outcome` `queued`, reason `submitted`, workflow 25, `x-hcx-status` `response.partial`, the case number as `preAuthRef` (PMJAY writes it on the claim's acknowledgement but not on its verdict [PAYER](../references/PAYERS.md#markers)). Same reason as on the pre-authorisation: an unanswered thread is retired and the verdict refused with NHCX-1010 [SANDBOX](../references/PAYERS.md#markers).

**2. The verdict**, sent by [A13. Adjudicate](A13-adjudicate.md) when the adjudicator approves or rejects the claim: once per thread, guarded by [D19. case](../database/D19-case.md) `nhcx_claim_answer_txn_id`. Approving a claim also draws the approved amount down from the enrolment's wallet ([A13. Adjudicate](A13-adjudicate.md), [D8. wallet_entry](../database/D8-wallet-entry.md)); the verdict carries the money as approved.

**Which thread.** A claim decided for the first time is answered here. A claim the hospital had reopened with a reprocess or release Task ([C7. Task Submit](../callbacks/C7-task-submit.md)) is answered on the Task's thread instead, as a completed Task with the ClaimResponse on its output ([A9. Task Answer](A9-task-answer.md)): the claim's own thread was completed by the verdict that was disputed, and the exchange refuses anything more on it (a 400) [SANDBOX](../references/PAYERS.md#markers). [A13. Adjudicate](A13-adjudicate.md) decides which by whether [D19. case](../database/D19-case.md) `nhcx_reprocess_correlation_id` is set.

**A query** goes out as [A5. Query Request](A5-query-request.md) on a thread of its own, and nothing on this one. **A withdrawal** of a case whose claim was still unanswered closes this thread with a ClaimResponse adjudicated `cancelled` ([C7. Task Submit](../callbacks/C7-task-submit.md)).

**What the verdict says** ([F9. ClaimResponse](../fhir/F9-claimresponse.md) with `use: claim`): as [A3. Pre-auth Answer](A3-preauth-answer.md), with "Claim" in the dispositions ("Claim approved for `<INR>`.", "Claim approved for `<INR approved>` of `<INR claimed>` claimed.", "Claim rejected.", "The claim was withdrawn."). A claim query keeps the `eligible` total that a pre-authorisation query drops, as PMJAY's does [PAYER](../references/PAYERS.md#markers). `preAuthRef` is left off the claim verdict [PAYER](../references/PAYERS.md#markers).

**Headers set by the application.**

| Header | Value |
|---|---|
| `x-hcx-sender_code` | This payer's participant code ([D1. payer](../database/D1-payer.md)) |
| `x-hcx-recipient_code` | The case's `nhcx_sender_code` |
| `x-hcx-correlation_id` | The case's `nhcx_claim_correlation_id` |
| `x-hcx-workflow_id` | From the table below |
| `x-hcx-status` | `response.partial` on the acknowledgement, `response.complete` on a verdict |

Workflow ids, per scheme dialect (see [PAYERS.md](../references/PAYERS.md)) [PAYER](../references/PAYERS.md#markers):

| Send | `pmjay` | `kyrocare` (Sandbox Payer) | `generic` | `x-hcx-status` |
|---|---|---|---|---|
| Acknowledgement | 25 | 25 | 25 | `response.partial` |
| Approved | 26 | 26 | 26 | `response.complete` |
| Rejected | 291 | 291 | 291 | `response.complete` |
| Withdrawn | PC02 | PC02 | PC02 | `response.complete` |

**Checks before sending.** The case must carry a claim thread (`nhcx_claim_correlation_id`): a bill entered on the desk has nobody to tell. An answered thread is left alone. No gateway: logged, the decision stands. Nothing refuses the adjudication.

Sandbox faults apply as on the pre-authorisation [SANDBOX](../references/PAYERS.md#markers) ([A19. Sandbox Scenarios](A19-sandbox-scenarios.md)).

#### A4Q. REQUEST

The arguments passed to G7 Send:

| Field | Type | Notes |
|---|---|---|
| `jwe_headers` | object | The five headers above |
| `fhir` | Bundle | The ClaimResponse bundle |

FHIR: [F1. Bundle](../fhir/F1-bundle.md), [F9. ClaimResponse](../fhir/F9-claimresponse.md) (`use: claim`), [F15. Patient](../fhir/F15-patient.md), [F17. Organization](../fhir/F17-organization.md), [F18. Coverage](../fhir/F18-coverage.md)

The claim number the answer carries as its identifier is the one the claim went under (`nhcx_claim_submission_ref`), else the pre-authorisation's (`nhcx_claim_ref`): the hospital's desk searches on it.

Envelope, a rejection:

```json
{
  "jwe_headers": {"x-hcx-sender_code": "<payer code>",
                  "x-hcx-recipient_code": "<facility code>",
                  "x-hcx-correlation_id": "0b398fdf-0516-4935-9ebb-a0dc90a06bb6",
                  "x-hcx-workflow_id": "291",
                  "x-hcx-status": "response.complete"},
  "fhir": <F1 Bundle: F9 ClaimResponse (use claim, outcome error, adjudication status rejected, disposition the adjudicator's remarks, every item Rejected with eligible 0), F15 Patient, F17 Organizations, F18 Coverage>
}
```

#### A4S. RESPONSE

**Acknowledgement:** the G7 result (`ok`, `gateway_status` 202, `txn_id`, `correlation_id`, `request_id`, `headers`, `response`).

Recorded, for the verdict:
- [D19. case](../database/D19-case.md) `nhcx_claim_answer_txn_id` = `txn_id`.
- [D27. case_exchange_message](../database/D27-case-exchange-message.md) exchange message, direction `out`, kind `claimresponse`, the claim thread, the transaction, summary "Claim verdict: `<status>`, `<INR approved>` approved of `<INR claimed>`".
- [D31. audit_log](../database/D31-audit-log.md) audit `claim.answered` on the case.

For the acknowledgement: the [D27. case_exchange_message](../database/D27-case-exchange-message.md) message only, "Claim verdict: acknowledged, with an adjudicator".

**Failed send.** Logged, nothing recorded; the answer column stays empty and the same decision can be sent again. The case stage has already moved (approved to `payment`, rejected to `rejected`) and stays there.

Data: [D19. case](../database/D19-case.md), [D25. case_line_item](../database/D25-case-line-item.md), [D27. case_exchange_message](../database/D27-case-exchange-message.md), [D31. audit_log](../database/D31-audit-log.md), [D1. payer](../database/D1-payer.md), [D5. member](../database/D5-member.md), [D6. subscription](../database/D6-subscription.md), [D12. policy](../database/D12-policy.md)

Reply: none on this thread. What follows: a reprocess or release Task ([C7. Task Submit](../callbacks/C7-task-submit.md)), a payment enquiry ([C10. Payment Enquiry](../callbacks/C10-payment-enquiry.md)), a status enquiry ([C8. Status Enquiry](../callbacks/C8-status-enquiry.md)); and this payer's own payment notice when finance pays ([A6. Payment Notice](A6-payment-notice.md)).

#### A4P. PSEUDOCODE

```
LEG claim: use "claim", route "v1/claim/on_submit",
           thread D19.nhcx_claim_correlation_id, answered D19.nhcx_claim_answer_txn_id,
           claim_ref D19.nhcx_claim_submission_ref or D19.nhcx_claim_ref,
           audit "claim.answered", what "claim verdict"

// the acknowledgement: A3 acknowledge_submission(case, claim), called by C5 after filing;
// workflow "25", status response.partial, summary "Claim verdict: acknowledged, with an adjudicator"

// the verdict, called by A13 when the stage decided was claim
function answer_claim(case): return send_verdict(case, claim)       // A3 send_verdict, with LEG claim

// in A13, after the decision is stored:
function answer_verdict(decided_stage, case):
    if case.adjudication_status == queried: return send_query(case)     // A5; nothing on this thread
    if decided_stage == preauth: txn = answer_preauth(case)             // A3
    if decided_stage == claim:
        if case.nhcx_reprocess_correlation_id set: txn = answer_reprocess(case)   // A9: the Task's thread
        else:                                       txn = answer_claim(case)
        if txn: UPDATE D19 SET nhcx_reprocess_correlation_id = null, nhcx_reprocess_claim_ref = null
    return case

// a withdrawal of an unanswered claim (from C7):
//   if case.nhcx_claim_correlation_id set and nhcx_claim_answer_txn_id empty: answer_claim(cancelled case)
//   renders outcome error, reason cancelled, workflow PC02
```

#### A4U. USED BY
- Screens: [S3. Case Desk](../screens/S3-case-desk.md), [S11. FHIR Preview](../screens/S11-fhir-preview.md)
- APIs: [A3. Pre-auth Answer](A3-preauth-answer.md), [A5. Query Request](A5-query-request.md), [A9. Task Answer](A9-task-answer.md), [A13. Adjudicate](A13-adjudicate.md), [A19. Sandbox Scenarios](A19-sandbox-scenarios.md)
- Callbacks: [C5. Claim Submit](../callbacks/C5-claim-submit.md), [C7. Task Submit](../callbacks/C7-task-submit.md), [C9. Communication](../callbacks/C9-communication.md)
- FHIR: [F1. Bundle](../fhir/F1-bundle.md), [F9. ClaimResponse](../fhir/F9-claimresponse.md)
- Database: [D19. case](../database/D19-case.md), [D27. case_exchange_message](../database/D27-case-exchange-message.md), [D31. audit_log](../database/D31-audit-log.md)
- Gateway: [G5. Protocol Headers](../gateway/G5-protocol-headers.md), [G7. Send](../gateway/G7-send.md)
- Tests: [T12. Claim Received and Approved](../tests/T12-claim-approved.md)
