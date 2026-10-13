# C5. Claim Submit

#### C5E. ENDPOINT
Delivered in-process by [G8. Receive](../gateway/G8-receive.md) for NHCX route `v1/claim/submit`, passed to `C1.receive`, classified `claim` because the bundle holds a `Claim` with `use` `claim` ([F8. Claim](../fhir/F8-claim.md)). Acknowledged inside the same delivery by [A4. Claim Answer](../apis/A4-claim-answer.md) (outcome `queued`, workflow 25, `response.partial`) on `v1/claim/on_submit`; the verdict follows when a person decides ([S3. Case Desk](../screens/S3-case-desk.md), [A13. Adjudicate](../apis/A13-adjudicate.md)), on the claim's own correlation id. A query answer sent as a fresh claim (workflow 161 or 151 [PAYER](../references/PAYERS.md#markers)) arrives here too.

#### C5D. DESCRIPTION
After discharge the hospital submits the same shape as its pre-authorisation with the final bill, the discharge block and the documents. The send carries `x-hcx-use_case` (`New`, or `Resubmit` for a query answer or a resubmission); this payer does not need it and must not refuse a send for carrying it. It is filed on the case the pre-authorisation opened, and nothing is decided until a person decides.

**Proof of presence at discharge.** As on the pre-authorisation ([C4. Pre-auth Submit](C4-preauth-submit.md)), the claim may carry a user token on its headers, and under PMJAY it must be a fresh one taken at discharge (process type Discharge): the admission's token does not serve the claim, and the scheme refuses a claim with neither it nor the Discharge Consent QuestionnaireResponse (PAYR-1363; PAYR-1366 for a lapsed token). This desk records what it found and files the claim regardless [REF](../references/PAYERS.md#markers).

**Which case.** The pre-authorisation reference the claim quotes first (`Claim.related` prior, `insurance[].preAuthRef`, or an identifier typed `PAR`), then the hospital's own claim number, which most hospitals keep the same across the two legs; each is looked up as `case_for_claim_ref` (this payer's `claim_no` or case id, or the number the hospital gave the pre-auth or the claim, filed by this sender, an open case before a closed one). Only an open case (stage `preauth` or `claim`) can take a claim: a bill against a rejected, withdrawn, paid or settled case is refused, not silently reopened: "The pre-authorisation <claim_no> is <stage> and cannot take a claim" (`rejected`).

**A claim with no pre-authorisation behind it opens a case of its own**, at the claim stage, with its discharge already recorded. That is a legitimate thing for a hospital to do (an emergency admission, a reimbursement) and refusing it would dead-letter a bill. The enrolment is found as a pre-authorisation's is ([C4. Pre-auth Submit](C4-preauth-submit.md)), in force only: "No enrolment matches the patient on this claim" (`rejected`) otherwise.

**Redelivery.** A case already holding this correlation id on its claim leg ([D19. case](../database/D19-case.md) `nhcx_claim_correlation_id`, unique) is `ignored` with the case named; two deliveries racing land on the unique index.

**What the filing does.** The bill replaces the estimate rather than adding to it: the claim is the whole of what is being asked for, and adding it to the pre-authorised lines would ask for both. Every line goes in pending in round 0, whatever was decided about the estimate is cleared (adjudication `pending`), the case moves to stage `claim`, the documents are filed at phase `claim`, and the routing slip of the claim leg is written (`nhcx_claim_correlation_id`, `nhcx_claim_submission_ref`, the sender kept when the case had none). The claim carries its own discharge, so a case whose discharge nobody recorded is discharged by it rather than refused: the date from the `DSDE` or `DSCHD` supporting information or `billablePeriod.end` (today when it carries none, never before the admission), the type from the `DIS` code (`NORMAL` or `DTH` Normal Discharge; `LAMA` or `DAMA` LAMA; `DTM`, `DEATH` or `DECEASED` Deceased; `TRANSFER` or `TRF` Transfer; else Normal Discharge). A `DTM` date alone also means a death. In the sandbox a LAMA or DAMA claim and a death-case claim tick their own checklist steps [SANDBOX](../references/PAYERS.md#markers).

**A case that has moved past adjudication** (stage `payment`, `settled`, `rejected`, `cancelled`) answers "That case has moved past adjudication and cannot take a claim" (`rejected`).

**Documents and forms.** As [C4. Pre-auth Submit](C4-preauth-submit.md): codes resolved against [D3. document_type](../database/D3-document-type.md), unknown codes filed as `ODN` with a timeline warning, inline bytes kept ([D24. case_document_file](../database/D24-case-document-file.md)), answered forms ([F7. QuestionnaireResponse](../fhir/F7-questionnaireresponse.md)) read later from the archived bundle ([A15. Case Exchange Log](../apis/A15-case-exchange.md)).

**Acknowledged at once**, for the same reason a pre-authorisation is ([C4. Pre-auth Submit](C4-preauth-submit.md)): [A4. Claim Answer](../apis/A4-claim-answer.md) sends outcome `queued` under workflow 25, `response.partial`, best-effort, marking nothing answered.

#### C5Q. REQUEST
`fhir` is an [F1. Bundle](../fhir/F1-bundle.md) Bundle carrying [F8. Claim](../fhir/F8-claim.md) Claim (`use: claim`, `billablePeriod`, the discharge block in `supportingInfo`, the pre-auth reference) with [F15. Patient](../fhir/F15-patient.md) Patient, [F17. Organization](../fhir/F17-organization.md) Organizations, [F18. Coverage](../fhir/F18-coverage.md) Coverage, [F16. Practitioner](../fhir/F16-practitioner.md) Practitioners, [F19. Other resources](../fhir/F19-other-resources.md) Procedures and [F7. QuestionnaireResponse](../fhir/F7-questionnaireresponse.md) QuestionnaireResponses. Headers read: `x-hcx-sender_code`, `x-hcx-recipient_code`, `x-hcx-correlation_id`, `x-hcx-workflow_id` (15 claim, 161 or 151 query answer [PAYER](../references/PAYERS.md#markers)).

#### C5P. PSEUDOCODE

```
C5(in, submission):                                       # submission = F8 parse, use claim
    existing = D19 where nhcx_claim_correlation_id == in.corr
    if existing: return "ignored"                          # a redelivery; outcome names the case

    documents, dropped = resolve_documents(submission.documents)
    lines = submission.line_items with claimed_amount rounded to 2 places
    origin = {sender_code: in.sender, recipient_code: in.recipient,
              claim_correlation_id: in.corr, claim_submission_ref: submission.claim_ref}

    case, matched = none, false
    for ref in [submission.preauth_ref, submission.claim_ref] if not blank:
        case = case_for_claim_ref(ref, in.sender)         # C1 shared rule
        if case: matched = true; break

    if matched and case.stage not in {preauth, claim}:
        raise Rejected("The pre-authorisation <case.claim_no> is <case.stage> and cannot take a claim")
    if matched:
        filed = D19.submit_exchange_claim(case, {remarks: "Claim <claim_ref> received from <sender> over NHCX.",
                    line_items: lines, documents, discharge_date: submission.discharge_date,
                    discharge_type: submission.discharge_type, exchange: origin})
            # discharge written when the case has none; nhcx_claim_correlation_id, nhcx_claim_submission_ref set,
            # nhcx_claim_answer_txn_id cleared; D25 replaced, pending, round 0; documents filed;
            # stage claim, adjudication pending; D26 "Claim Submitted"
    else:
        subscription = D6 in force today matched by submission.handles()
        if none: raise Rejected("No enrolment matches the patient on this claim")
        member = D5[subscription.member_id]
        input = case_from_submission(submission, subscription, member, in)   # as C4
        input.stage = "claim"; input.documents = documents; input.line_items = lines
        input.discharge_date = submission.discharge_date or input.admitted_on
        input.discharge_type = submission.discharge_type if valid else "Normal Discharge"
        input.exchange = origin
        filed = D19.create(input)                          # D26 "Claim Filed Directly"
    on conflict (unique claim correlation id):
        existing = D19 where nhcx_claim_correlation_id == in.corr
        if existing: return "ignored"
    on closed: raise Rejected("That case has moved past adjudication and cannot take a claim")

    if dropped: D26 event "Attachments Filed as Other" (as C4)
    exchange_message(filed, "in", "claim", in.corr, in.ledger_id, in.sender,
                     "Claim <claim_ref> for <total>: <n> line(s), <m> document(s)", payload(in.envelope))
    D31 audit {action: "claim.received", entity: "nhcx_txn", id: in.ledger_id,
               detail: "<sender> submitted claim <claim_ref>, correlation <corr>, filed on <filed.id>"}
    A4.acknowledge(filed, "claim")                         # queued, workflow 25, response.partial; best-effort
    return "settled"                                       # outcome {status: filed, case_id, claim_no, stage}
```

#### C5S. RESPONSE
`settled` when the bill was filed on its case or a direct case opened (and acknowledged, best-effort); `ignored` for a redelivery; `rejected` when the case is closed, has moved past adjudication, or no enrolment matches a direct claim; `error` on an unexpected failure.

State changes:

| Filing | Writes |
|---|---|
| on the pre-authorised case | [D19. case](../database/D19-case.md) stage `claim`, adjudication `pending`, `discharge_date` and `discharge_type` when unset, `nhcx_claim_correlation_id`, `nhcx_claim_submission_ref`, `nhcx_claim_answer_txn_id` null; [D25. case_line_item](../database/D25-case-line-item.md) replaced by the bill, pending, round 0; [D23. case_document](../database/D23-case-document.md) documents at phase `claim` with [D24. case_document_file](../database/D24-case-document-file.md) bytes; totals; [D26. case_timeline](../database/D26-case-timeline.md) "Claim Submitted"; [D27. case_exchange_message](../database/D27-case-exchange-message.md) the inbound message; [D31. audit_log](../database/D31-audit-log.md) `claim.received` |
| direct claim | a new [D19. case](../database/D19-case.md) row at stage `claim` with the discharge, and its children as [C4. Pre-auth Submit](C4-preauth-submit.md); [D26. case_timeline](../database/D26-case-timeline.md) "Claim Filed Directly"; [D27. case_exchange_message](../database/D27-case-exchange-message.md); [D31. audit_log](../database/D31-audit-log.md) |
| acknowledgement | [D27. case_exchange_message](../database/D27-case-exchange-message.md) the outbound `claimresponse` "acknowledged, with an adjudicator" (A4) |

#### C5U. USED BY
- Screens: [S2. Cases](../screens/S2-cases.md), [S3. Case Desk](../screens/S3-case-desk.md)
- APIs: [A3. Pre-auth Answer](../apis/A3-preauth-answer.md), [A4. Claim Answer](../apis/A4-claim-answer.md), [A13. Adjudicate](../apis/A13-adjudicate.md), [A18. Provider Driver](../apis/A18-provider-driver.md)
- Callbacks: [C1. Callback Door](C1-callback-door.md), [C9. Communication](C9-communication.md)
- FHIR: [F1. Bundle](../fhir/F1-bundle.md), [F7. QuestionnaireResponse](../fhir/F7-questionnaireresponse.md), [F8. Claim](../fhir/F8-claim.md), [F9. ClaimResponse](../fhir/F9-claimresponse.md)
- Database: [D3. document_type](../database/D3-document-type.md), [D19. case](../database/D19-case.md), [D21. case_procedure](../database/D21-case-procedure.md), [D22. case_doctor](../database/D22-case-doctor.md), [D23. case_document](../database/D23-case-document.md), [D24. case_document_file](../database/D24-case-document-file.md), [D25. case_line_item](../database/D25-case-line-item.md), [D26. case_timeline](../database/D26-case-timeline.md), [D27. case_exchange_message](../database/D27-case-exchange-message.md), [D31. audit_log](../database/D31-audit-log.md)
- Tests: [T12. Claim Received and Approved](../tests/T12-claim-approved.md), [T13. LAMA and Death Claims](../tests/T13-claim-lama-death.md), [T18. Redelivery and Duplicates](../tests/T18-redelivery-ignored.md)
