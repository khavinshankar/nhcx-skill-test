# A3. Pre-auth Answer

#### A3E. ENDPOINT
In-process: `gateway.send("v1/preauth/on_submit", envelope)`, [G7. Send](../gateway/G7-send.md), which encrypts it and posts it to NHCX for the hospital, on the thread the pre-authorisation arrived on: `POST {nhcx}/v1/preauth/on_submit`. No answer to it is awaited.

It answers [C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md) in every send the hospital makes on that thread: the first pre-authorisation, an enhancement, a query resubmission. The hospital's desk takes it in as its pre-auth reply and reads the outcome and the claim-level adjudication reason together; every reply on the thread is applied, an acknowledgement leaves it waiting and a decision settles it. The same route also carries a predetermination quote, which is [A10. Predetermination Quote](A10-predetermination-quote.md).

#### A3D. DESCRIPTION
A pre-authorisation is answered **twice** on one correlation id, and never more than once with a decision.

**1. The acknowledgement**, sent by the application the moment [C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md) has filed the case: a ClaimResponse with `outcome` `queued`, adjudication `submitted`, disposition "Request acknowledged and accepted for further processing.", the case number as `preAuthRef` and the claim type on it. It decides nothing. It is sent because NHCX keeps a thread open only while it is being answered: a submission left silent is redelivered, then dropped and its correlation id retired, and the verdict a person takes hours over is refused with NHCX-1010 ("no data with given correlation id for call back request") [SANDBOX](../references/PAYERS.md#markers). The live PMJAY payer answers the same way [PAYER](../references/PAYERS.md#markers). It is best effort: a case is filed whether or not it got out, and nothing is marked answered, so the verdict still goes.

**2. The verdict**, sent by [A13. Adjudicate](A13-adjudicate.md) when an adjudicator approves or rejects the case. It goes out once per thread: the transaction it went out under is kept on the case ([D19. case](../database/D19-case.md) `nhcx_answer_txn_id`), and a case whose thread is already answered is not answered again, because the hospital settles on the first decision and ignores a second. An enhancement reopens the thread ([C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md) clears the answer transaction), so its decision goes out as a fresh verdict.

**A query is not a verdict.** When the adjudicator queries the case nothing goes on this thread: the question goes out as a CommunicationRequest on a thread of its own ([A5. Query Request](A5-query-request.md)), the submission stays open, and the ClaimResponse follows when the reply has been read and a decision made. (A scheme in `resubmit` query mode answers the query on this thread instead, `outcome` `partial` with reason `queried`, and takes the hospital's answer as a resubmission [PAYER](../references/PAYERS.md#markers); see [PAYERS.md](../references/PAYERS.md).)

**3. A withdrawal.** When a cancel Task closes a case whose pre-authorisation was still unanswered ([C7. Task Submit](../callbacks/C7-task-submit.md)), the thread is closed with a ClaimResponse adjudicated `cancelled` under PC02, beside the Task's own answer ([A9. Task Answer](A9-task-answer.md)).

**What the verdict says** ([F9. ClaimResponse](../fhir/F9-claimresponse.md)), from the case ([D19. case](../database/D19-case.md)) and its lines ([D25. case_line_item](../database/D25-case-line-item.md)):

| Decision | `outcome` | Claim-level reason | Disposition |
|---|---|---|---|
| approved in full | `complete` | `approved` | the adjudicator's remarks, else "Pre-authorisation approved for `<INR approved>`." |
| approved with cuts (`total_approved` < `total_claimed`) | `partial` | `approved` | the remarks, else "Pre-authorisation approved for `<INR approved>` of `<INR claimed>` claimed." |
| rejected | `error` | `rejected` | the remarks, else "Pre-authorisation rejected." |
| withdrawn | `error` | `cancelled` | "The pre-authorisation was withdrawn." |

Per line, four adjudications: `submitted` (claimed), `eligible` (approved), `reason` (the line's query remarks, else its remarks, else "Not payable under this policy." for a rejected line; the disposition when the line was allowed in full) and `status` (`Approved`, `Rejected`, `Queried`, `Requested`). Totals `benefit` and `eligible` are the approved total, `submitted` the claimed total. `preAuthRef` is the case number on every pre-authorisation answer, the refusal included [PAYER](../references/PAYERS.md#markers).

**Headers set by the application.**

| Header | Value |
|---|---|
| `x-hcx-sender_code` | This payer's participant code ([D1. payer](../database/D1-payer.md) `nhcx_participant_id`, else the configured code) |
| `x-hcx-recipient_code` | The case's `nhcx_sender_code`: the hospital that submitted |
| `x-hcx-correlation_id` | The case's `nhcx_correlation_id`: the pre-authorisation's thread |
| `x-hcx-workflow_id` | From the table below |
| `x-hcx-status` | `response.partial` on the acknowledgement, `response.complete` on a verdict |

Workflow ids, per scheme dialect (see [PAYERS.md](../references/PAYERS.md)) [PAYER](../references/PAYERS.md#markers):

| Send | `pmjay` | `kyrocare` (Sandbox Payer) | `generic` | `x-hcx-status` |
|---|---|---|---|---|
| Acknowledgement | 20 | 20 | 20 | `response.partial` |
| Approved (no enhancement on the case) | 21 | 21 | 21 | `response.complete` |
| Rejected (no enhancement) | 23 | 23 | 23 | `response.complete` |
| Enhancement approved (the case has had an enhancement round) | 22 | 22 | 22 | `response.complete` |
| Enhancement denied | 231 | 231 | 231 | `response.complete` |
| Withdrawn | PC02 | PC02 | PC02 | `response.complete` |

The enhancement rows are chosen by the case's `enhancement_count` being above zero, not by which send the hospital made last [REF](../references/PAYERS.md#markers). G7 completes the rest ([G5. Protocol Headers](../gateway/G5-protocol-headers.md)).

**Checks before sending.** The case must have come off the exchange (`nhcx_correlation_id` set): a case raised on the desk itself has nobody to tell, and nothing is sent. A thread already answered is left alone. A gateway that is not configured is logged, "case `<id>` was decided but no gateway is configured, so `<hospital>` was not told", and the decision stands. Nothing refuses the adjudication: the decision is made and recorded before this send, and a gateway that cannot take it does not unmake it.

**Sandbox faults.** A case pinned to a FAULT scenario has its verdict broken on the way out (held, dropped, sent twice, malformed, on a stale thread, or saying the opposite) [SANDBOX](../references/PAYERS.md#markers); see [A19. Sandbox Scenarios](A19-sandbox-scenarios.md). Everything that happens is on the exchange log.

#### A3Q. REQUEST

The arguments passed to G7 Send:

| Field | Type | Notes |
|---|---|---|
| `jwe_headers` | object | The five headers above |
| `fhir` | Bundle | The ClaimResponse bundle |

FHIR: [F1. Bundle](../fhir/F1-bundle.md), [F9. ClaimResponse](../fhir/F9-claimresponse.md) (`use: preauthorization`), [F15. Patient](../fhir/F15-patient.md) (the member), [F17. Organization](../fhir/F17-organization.md) (this payer and the hospital), [F18. Coverage](../fhir/F18-coverage.md) (the enrolment as Coverage)

Envelope, an approval:

```json
{
  "jwe_headers": {"x-hcx-sender_code": "<payer code>",
                  "x-hcx-recipient_code": "<facility code>",
                  "x-hcx-correlation_id": "f8425e75-52e0-4413-a915-39a7bad38ee2",
                  "x-hcx-workflow_id": "21",
                  "x-hcx-status": "response.complete"},
  "fhir": <F1 Bundle: F9 ClaimResponse (use preauthorization, outcome complete, adjudication status approved, preAuthRef the case number, one item per line, totals), F15 Patient, F17 payer and provider Organizations, F18 Coverage>
}
```

The acknowledgement is the same bundle with `outcome` `queued`, reason `submitted`, workflow 20 and status `response.partial`.

#### A3S. RESPONSE

**Acknowledgement** (the G7 result): `{"ok": true, "gateway_status": 202, "txn_id", "correlation_id", "request_id", "headers", "response"}`.

Recorded, for the verdict:
- [D19. case](../database/D19-case.md) `nhcx_answer_txn_id` = the result's `txn_id`. This is the guard against a second verdict on the thread.
- [D27. case_exchange_message](../database/D27-case-exchange-message.md) one exchange message, direction `out`, kind `claimresponse`, the correlation id, the transaction, the hospital as counterparty, summary "Pre-auth verdict: `<status>`, `<INR approved>` approved of `<INR claimed>`", the bundle as payload.
- [D31. audit_log](../database/D31-audit-log.md) audit `preauth.answered` on the case: "`<hospital>` told, correlation `<id>`, answer txn `<txn_id>`".

For the acknowledgement: only the [D27. case_exchange_message](../database/D27-case-exchange-message.md) message, kind `claimresponse`, summary "Pre-auth verdict: acknowledged, with an adjudicator". `nhcx_answer_txn_id` stays empty.

**Failed send.** A G7 error or a result NHCX did not accept is logged ("could not queue the pre-auth verdict on case `<id>` for `<hospital>`: `<message>`") and nothing is recorded: `nhcx_answer_txn_id` stays empty, the case keeps its correlation id, and an operator can decide again (the same decision) to send it once more. The exchange log shows the decision without a transaction. A failed acknowledgement is logged and forgotten: the verdict is what counts.

Data: [D19. case](../database/D19-case.md), [D25. case_line_item](../database/D25-case-line-item.md), [D27. case_exchange_message](../database/D27-case-exchange-message.md), [D31. audit_log](../database/D31-audit-log.md), [D1. payer](../database/D1-payer.md), [D5. member](../database/D5-member.md), [D6. subscription](../database/D6-subscription.md), [D12. policy](../database/D12-policy.md)

Reply: none on this thread. What follows is the hospital's next message: an enhancement or a resubmission ([C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md)), a cancel ([C7. Task Submit](../callbacks/C7-task-submit.md)), the claim ([C5. Claim Submit](../callbacks/C5-claim-submit.md)), a status enquiry ([C8. Status Enquiry](../callbacks/C8-status-enquiry.md)).

#### A3P. PSEUDOCODE

```
// the two legs answered by a ClaimResponse on the submission's thread; A4 uses the claim row
LEG preauth: use "preauthorization", route "v1/preauth/on_submit",
             thread D19.nhcx_correlation_id, answered D19.nhcx_answer_txn_id,
             claim_ref D19.nhcx_claim_ref, audit "preauth.answered", what "pre-auth verdict"

function VERDICT_HEADERS(case, workflow, status):
    return {x-hcx-sender_code:    payer participant code (D1.nhcx_participant_id or configured),
            x-hcx-recipient_code: case.nhcx_sender_code,
            x-hcx-correlation_id: LEG.thread(case),
            x-hcx-workflow_id:    workflow,          // left off when empty
            x-hcx-status:         status}

function verdict_workflow(leg, case):               // [PAYER](../references/PAYERS.md#markers): the pmjay column; read the adapter table
    if case.stage == cancelled or case.adjudication_status == cancelled: return "PC02"
    if leg == claim: return "291" if rejected else "26"                  // A4
    if leg == reprocess: return "253" if rejected else "252"             // A9
    enhanced = case.enhancement_count > 0
    if rejected and enhanced: return "231"
    if rejected:              return "23"
    if enhanced:              return "22"
    return "21"

// 1. the acknowledgement, called by C4 (and by C5 with leg claim) right after filing
function acknowledge_submission(case, leg):
    if case.nhcx_correlation_id empty or gateway not configured: return
    payer = D1 payer row
    bundle = F9 bundle(payer, payer code, case, cover(case), use = LEG.use,
                       claim_ref = LEG.claim_ref(case), recipient = case.nhcx_sender_code)
                       // adjudication_status pending renders outcome queued, reason submitted
    ack = SEND(LEG.route, {jwe_headers: VERDICT_HEADERS(case, "20" (preauth) or "25" (claim),
                                                       "response.partial"),
                           fhir: bundle}, case)                        // A1: SEND
        on any failure f: log "case <id> was filed but <hospital> could not be told it is in: <f>"; return
    INSERT D27 {case_id, direction: out, kind: claimresponse, correlation_id: LEG.thread(case),
                txn_id: ack.txn_id, counterparty: case.nhcx_sender_code,
                summary: "Pre-auth verdict: acknowledged, with an adjudicator", payload: bundle}

// 2. the verdict, called by A13 after the decision is stored (stage decided == preauth)
function answer_preauth(case): return send_verdict(case, preauth)

function send_verdict(case, leg):
    if case.nhcx_correlation_id empty or LEG.thread(case) empty: return ""   // not from the exchange
    if LEG.answered(case) not empty: return LEG.answered(case)                // already told; never twice
    if gateway not configured:
        log "case <id> was decided but no gateway is configured, so <hospital> was not told"; return ""
    payer = D1 payer row
    thread = LEG.thread(case); claim_ref = LEG.claim_ref(case)
    render(current) = F9 bundle(payer, payer code, current, cover(current), use = LEG.use,
                                claim_ref, recipient = case.nhcx_sender_code)
    headers = VERDICT_HEADERS(case, verdict_workflow(leg, case), "response.complete")
    summary = "<What> verdict: <adjudication_status>, <INR approved> approved of <INR claimed>"

    result = dispatch(case, render, headers, LEG.route)   // A19: applies the case's sandbox fault, else one SEND
    if result failed:
        log "could not queue the <what> on case <id> for <hospital>: <error>"; return ""
    txn = result.txn_id                                    // "fault:<kind>" when dropped or delayed [SANDBOX](../references/PAYERS.md#markers)
    UPDATE D19[case.id] SET LEG.answered column = txn
    for each ack in result.acks:
        INSERT D27 {case_id, direction: out, kind: claimresponse, correlation_id: thread,
                    txn_id: ack.txn_id, counterparty: case.nhcx_sender_code,
                    summary (+ the fault note), payload: the bundle sent}
    if no ack: INSERT D27 the same without txn_id, summary + result.note   // dropped or delayed
    INSERT D31 audit {action: LEG.audit, entity_type: case, entity_id: case.id,
                      detail: "<hospital> told, correlation <thread>, answer txn " + txn}
    return txn

function cover(case):                                  // what the bundle carries beside the case
    member = D5[case.member_id]; sub = D6[case.subscription_id]; policy = D12[sub.policy_id]
    return {member, sub, policy}, each left out when unreadable
```

#### A3U. USED BY
- Screens: [S3. Case Desk](../screens/S3-case-desk.md), [S11. FHIR Preview](../screens/S11-fhir-preview.md)
- APIs: [A4. Claim Answer](A4-claim-answer.md), [A5. Query Request](A5-query-request.md), [A8. Status Answer](A8-status-answer.md), [A9. Task Answer](A9-task-answer.md), [A13. Adjudicate](A13-adjudicate.md), [A19. Sandbox Scenarios](A19-sandbox-scenarios.md)
- Callbacks: [C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md), [C7. Task Submit](../callbacks/C7-task-submit.md), [C9. Communication](../callbacks/C9-communication.md)
- FHIR: [F1. Bundle](../fhir/F1-bundle.md), [F9. ClaimResponse](../fhir/F9-claimresponse.md)
- Database: [D19. case](../database/D19-case.md), [D27. case_exchange_message](../database/D27-case-exchange-message.md), [D31. audit_log](../database/D31-audit-log.md)
- Gateway: [G5. Protocol Headers](../gateway/G5-protocol-headers.md)
- Tests: [T6. Pre-auth Received and Approved](../tests/T6-preauth-approved.md), [T7. Pre-auth Rejected](../tests/T7-preauth-rejected.md), [T9. Enhancement Received and Approved](../tests/T9-enhancement-approved.md)
