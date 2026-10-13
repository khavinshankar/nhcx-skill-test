# C4. Pre-auth Submit

#### C4E. ENDPOINT
Delivered in-process by [G8. Receive](../gateway/G8-receive.md) for NHCX route `v1/preauth/submit`, passed to `C1.receive`, classified `preauth` because the bundle holds a `Claim` with `use` `preauthorization` ([F8. Claim](../fhir/F8-claim.md)). Acknowledged inside the same delivery by [A3. Pre-auth Answer](../apis/A3-preauth-answer.md) (outcome `queued`, workflow 20, `response.partial`) on `v1/preauth/on_submit`; the verdict follows when a person decides on the desk ([S3. Case Desk](../screens/S3-case-desk.md), [A13. Adjudicate](../apis/A13-adjudicate.md)), on the same correlation id.

#### C4D. DESCRIPTION
The hospital's send carries `x-hcx-use_case` (`New`, `Enhancement` or `Resubmit`) on every pre-authorisation. This payer does not need it, since it tells a comeback from a first filing by the case the Claim names, and must not refuse a send for carrying it.

The one inbound flow that is not decided where it arrives. A hospital submits a Claim; this payer files it as a case ([D19. case](../database/D19-case.md)) and a person approves, queries or rejects it hours later. The verdict is a ClaimResponse addressed with the correlation id the submission arrived under, which sits on the case until then.

**Acknowledged at once, decided later.** NHCX keeps a thread open only while it is being answered: a submission left silent is redelivered, then dropped, its correlation id retired, and the real verdict is refused minutes later with NHCX-1010 ("no data with given correlation id for call back request"). So the filing is followed at once by [A3. Pre-auth Answer](../apis/A3-preauth-answer.md) sending a ClaimResponse with outcome `queued` under workflow 20 and `x-hcx-status` `response.partial`: received, not decided. The live PMJAY payer answers the same way [PAYER](../references/PAYERS.md#markers), and hospitals built from the provider skill read a queued answer as an acknowledgement, not a decision. The acknowledgement is best-effort: a case is filed whether or not it got out, nothing is marked answered by it, and the verdict still goes.

**Proof of presence.** The send may carry the beneficiary's user token on its protected headers (the header its onboarding names, default `x-hcx-user-token`, with `x-hcx-ben-abha-id`), from a biometric authentication the hospital did against ABHA; a hospital may send it to any payer. This payer records it on the case's exchange. Under the `pmjay` profile the live scheme refuses a pre-authorisation that carries neither a valid token nor the Authentication Consent QuestionnaireResponse (PAYR-1256; PAYR-1272 for a lapsed token): this desk files the case regardless and notes on its timeline which of the two it found, so a hospital built from the provider skill sees the same refusal only where the scheme would give it [REF](../references/PAYERS.md#markers).

**Three things a pre-authorisation Claim can be.** In this order:

1. **A redelivery.** A case already holds this correlation id ([D19. case](../database/D19-case.md) `nhcx_correlation_id`, unique): `ignored`, with the case named. Two deliveries racing land on the unique index, and the loser reads the winner's case.
2. **A comeback**: an enhancement or a resubmission answering a query, on a pre-authorisation already on file. The reference shape is the whole pre-authorisation again under the same claim number, the added lines beside the original ones; an older sender names the prior on `Claim.related` (relationship `prior`), `insurance[].preAuthRef` or an identifier typed `PAR` and carries the added lines alone. Either way the new lines go on the existing case for a fresh decision; no second case opens. Which case (`case_come_back_to`): a prior named outright is the only thing looked up when there is one; otherwise the claim number itself, as long as that case is past its first filing: from the same sender, addressed to this participant, open (stage `preauth` or `claim`), not cancelled, and not a pending case being sent new lines (that is a fresh filing racing this one, not a comeback). A case whose claim leg is already filed takes no enhancement: more money is the claim's business.
3. **A new case.** The enrolment is found by the same handles an eligibility enquiry uses ([C2. Coverage Eligibility Check](C2-coverage-eligibility-check.md)): in force first, else the most recent cover the person had, so a lapsed policy is filed and refused with the reason rather than dead-lettered as "no such person". No enrolment at all is a permanent refusal: "No enrolment matches the patient on this pre-authorisation" (`rejected`; the same envelope redelivered would find the same nothing).

**What a comeback does.** The lines not already on the bill (matched on code, description and claimed amount, because the reference repeats the original lines beside the new ones) are the enhancement; they join the case pending, in a new round (`enhancement_no`), through the same store transition the desk's own enhancement uses, and lines already decided keep their decisions. When the case is `queried`, the submission is first taken as the answer to the query (workflow 121 or 131 [PAYER](../references/PAYERS.md#markers)): the queried lines go back to pending with the hospital's note (the `CQD` supporting information, else "Resubmitted by <sender> (<claim ref>)."), its documents are filed, the open query thread on the case is cleared. No new lines and no open query, with a prior named: `rejected`, "An enhancement has to ask for something"; without a prior named it is the same bundle again, `ignored`. A case that is closed answers "The pre-authorisation <ref> is <stage> and takes no enhancement" or "That case is closed and takes no resubmission" or "... takes no enhancement" (`rejected`). Then the pre-auth thread is reopened on this correlation id (`ReopenPreauthThread`: the new correlation id replaces the old, the answer transaction is cleared so a fresh verdict may go, a case at stage `claim` with no claim leg filed goes back to `preauth`), and the comeback is acknowledged like a first filing.

**What a new case takes from the bundle.** The patient on the case is this payer's member, not the name the hospital typed: the enrolment is the record of who they are. What the hospital states about the admission is taken as sent: hospital (name, HFR id), admission date (the `ADDD` or `EDT` supporting information, else `Coverage.period.start`, else today), expected discharge, urgency from `Claim.priority` (`stat` or `asap` Emergency, `urgent` Urgent, else Elective), diagnoses (the first primary, the rest secondary), the care team by HPR id, procedures named by the package each item bills, line items (quantity, unit price, `net`, a ward or ICU tier riding as a modifier beside the line, never as a line of its own), and the attachments. The age is the member's on the admission date. A document under a code this payer's taxonomy does not carry is filed as `ODN` with its original code on the timeline ("Attachments Filed as Other"): evidence a hospital sent is evidence an adjudicator has to see. Inline attachment bytes are kept ([D24. case_document_file](../database/D24-case-document-file.md)). Answered forms ride in the bundle ([F7. QuestionnaireResponse](../fhir/F7-questionnaireresponse.md)) and are read from the archived message when the desk shows them ([A15. Case Exchange Log](../apis/A15-case-exchange.md)).

**Routing slip.** The case records the correlation id, the sender, the participant code it was addressed to and the hospital's own claim number (`nhcx_claim_ref`, which is not this payer's `claim_no`). The verdict, the query and the payment notices all address the sender.

#### C4Q. REQUEST
`fhir` is an [F1. Bundle](../fhir/F1-bundle.md) Bundle carrying [F8. Claim](../fhir/F8-claim.md) Claim (`use: preauthorization`) with [F15. Patient](../fhir/F15-patient.md) Patient, the provider and payer [F17. Organization](../fhir/F17-organization.md) Organizations, [F18. Coverage](../fhir/F18-coverage.md) Coverage, [F16. Practitioner](../fhir/F16-practitioner.md) Practitioner per care-team member, [F19. Other resources](../fhir/F19-other-resources.md) Procedure per procedure line, and [F7. QuestionnaireResponse](../fhir/F7-questionnaireresponse.md) QuestionnaireResponse per answered form. Headers read: `x-hcx-sender_code`, `x-hcx-recipient_code`, `x-hcx-correlation_id`, `x-hcx-workflow_id` (12 first request, 121 resubmission, 13 enhancement, 19 and 131 query answers under the `pmjay` dialect [PAYER](../references/PAYERS.md#markers); nothing routes on it).

#### C4P. PSEUDOCODE

```
C4(in, submission):                                       # submission = F8 parse
    existing = D19 where nhcx_correlation_id == in.corr
    if existing: return "ignored"                          # a redelivery; outcome names the case

    if comeback(in, submission): return that outcome

    subscription = find_enrolment(submission.handles())    # C1 shared rule
    if none: raise Rejected("No enrolment matches the patient on this pre-authorisation")
    member = D5[subscription.member_id]
    documents, dropped = resolve_documents(submission.documents)   # C1 shared rule
    input = case_from_submission(submission, subscription, member, in) + {documents}
    try: case = D19.create(input)                          # with D20 to D25 children, totals, first D26 event
                                                           # "Pre-Authorization Claim Created"
    catch conflict:                                        # two deliveries racing on the unique correlation id
        existing = D19 where nhcx_correlation_id == in.corr
        if existing: return "ignored"
        raise
    if dropped: D26 event {title: "Attachments Filed as Other", type: warning,
                           description: "<n> attachment(s) arrived under codes this payer does not know (<codes>); they are filed as other documents rather than dropped"}
    exchange_message(case, "in", "preauth", in.corr, in.ledger_id, in.sender,
                     "Pre-auth <claim_ref> for <total>: <n> line(s)", payload(in.envelope))
    D31 audit {action: "preauth.received", entity: "nhcx_txn", id: in.ledger_id,
               detail: "<sender> submitted <claim_ref>, correlation <corr>, filed as <case.id>"}
    A3.acknowledge(case, "preauth")                        # queued, workflow 20, response.partial; best-effort
    return "settled"                                       # outcome {status: filed, case_id, claim_no, stage}

case_from_submission(s, subscription, member, in):
    admitted = s.admitted_on or today
    return {subscription_id, member_id: subscription.member_id,
            patient_name: member.name or s.patient_name, patient_gender: member.gender or s.gender,
            patient_age: age of member.dob on admitted,
            hospital: s.hospital, admitted_on: admitted, expected_discharge: s.expected_discharge,
            urgency: s.urgency or "Elective",
            diagnoses: s.diagnoses, procedures: s.procedures, doctors: s.doctors, line_items: s.line_items,
            exchange: {correlation_id: in.corr, sender_code: in.sender,
                       recipient_code: in.recipient, claim_ref: s.claim_ref}}

comeback(in, s):
    case, found = case_come_back_to(in, s)
    if not found: return none
    if case.exchange.claim_correlation_id: return none     # the claim is filed; more money is the claim's business
    if case.stage not in {preauth, claim}:
        raise Rejected("The pre-authorisation <s.preauth_ref or s.claim_ref> is <case.stage> and takes no enhancement")
    added = lines_not_on_the_bill(case, s.line_items)      # by code, description and claimed amount
    queried = case.adjudication_status == "queried"
    if added empty and not queried:
        if s.preauth_ref: raise Rejected("An enhancement has to ask for something")
        return "ignored"                                   # the same number, the same lines, nothing asked
    documents, _ = resolve_documents(s.documents)
    if queried:
        note = s.query_note or "Resubmitted by <sender> (<s.claim_ref>)."
        D19.respond_to_query(case, {remarks: note, documents})   # queried D25 lines back to pending,
                                                           # documents filed, adjudication pending, D26 "Query Answered"
            on closed: raise Rejected("That case is closed and takes no resubmission")
        documents = none
        D19.nhcx_query_correlation_id = null
    round = case.enhancement_count
    if added not empty:
        round += 1
        case = D19.raise_enhancement(case, {reason: "Enhancement <round> from <sender> (<s.claim_ref>).",
                                            line_items: added, documents})   # D25 rows pending in round,
                                                           # adjudication pending, D26 event
            on closed: raise Rejected("That case is closed and takes no enhancement")
    D19.reopen_preauth_thread(case, in.corr, s.claim_ref)  # nhcx_correlation_id = corr, nhcx_answer_txn_id = null,
                                                           # stage claim -> preauth when no claim leg is filed
    exchange_message(case, "in", "preauth", in.corr, in.ledger_id, in.sender,
        added ? "Enhancement <round> on <ref>: <n> line(s), <amount> more"
              : "Resubmission on <s.claim_ref> answering the query", payload(in.envelope))
    D31 audit {action: added ? "preauth.enhanced" : "preauth.resubmitted", entity: "nhcx_txn", id: in.ledger_id,
               detail: "<sender> came back on <s.claim_ref> (round <round>), correlation <corr>, case <case.id>"}
    A3.acknowledge(case, "preauth")
    return "settled"                                       # outcome {status: enhancement | resubmission, case_id, enhancement: round}

case_come_back_to(in, s):
    if s.preauth_ref: return case_for_claim_ref(s.preauth_ref, in.sender)   # the only lookup when a prior is named
    if s.claim_ref == "": return none
    case = case_for_claim_ref(s.claim_ref, in.sender)
    if none: return none
    if case.exchange.recipient_code and it != in.recipient (numeric part compared): return none
    if case.stage not in {preauth, claim}: return none      # a closed number is being started again
    if case.adjudication_status == "cancelled": return none
    if case.adjudication_status == "pending" and lines_not_on_the_bill(case, s.line_items) not empty:
        return none                                        # new lines on an undecided case are a fresh filing
    return case
```

#### C4S. RESPONSE
`settled` when a case was opened or a comeback filed (and acknowledged, best-effort); `ignored` for a redelivery or the same bundle again; `rejected` when no enrolment matches, the case is closed, or an enhancement asks for nothing; `error` on an unexpected failure.

State changes, per outcome:

| Filing | Writes |
|---|---|
| new case | [D19. case](../database/D19-case.md) row (stage `preauth`, adjudication `pending`, the routing slip), [D20. case_diagnosis](../database/D20-case-diagnosis.md) diagnoses, [D21. case_procedure](../database/D21-case-procedure.md) procedures, [D22. case_doctor](../database/D22-case-doctor.md) doctors, [D23. case_document](../database/D23-case-document.md) documents with [D24. case_document_file](../database/D24-case-document-file.md) bytes, [D25. case_line_item](../database/D25-case-line-item.md) lines in round 0, totals; [D26. case_timeline](../database/D26-case-timeline.md) "Pre-Authorization Claim Created" (and "Attachments Filed as Other"); [D27. case_exchange_message](../database/D27-case-exchange-message.md) the inbound message; [D31. audit_log](../database/D31-audit-log.md) `preauth.received`; the [D28. nhcx_delivery](../database/D28-nhcx-delivery.md) receipt (C1); [D32. id_sequence](../database/D32-id-sequence.md) case and claim serials |
| enhancement | [D25. case_line_item](../database/D25-case-line-item.md) added lines pending in round n, [D19. case](../database/D19-case.md) `enhancement_count` n, adjudication `pending`, `nhcx_correlation_id` replaced, `nhcx_answer_txn_id` cleared; [D26. case_timeline](../database/D26-case-timeline.md) "Enhancement Requested"; [D27. case_exchange_message](../database/D27-case-exchange-message.md); [D31. audit_log](../database/D31-audit-log.md) `preauth.enhanced` |
| resubmission after a query | queried [D25. case_line_item](../database/D25-case-line-item.md) lines back to `pending`, documents filed, [D19. case](../database/D19-case.md) adjudication `pending`, `nhcx_query_correlation_id` cleared, thread reopened; [D26. case_timeline](../database/D26-case-timeline.md) "Query Answered"; [D27. case_exchange_message](../database/D27-case-exchange-message.md); [D31. audit_log](../database/D31-audit-log.md) `preauth.resubmitted` |
| acknowledgement | [D27. case_exchange_message](../database/D27-case-exchange-message.md) the outbound `claimresponse` "acknowledged, with an adjudicator" (A3); nothing on the case marks it answered |

#### C4U. USED BY
- Screens: [S2. Cases](../screens/S2-cases.md), [S3. Case Desk](../screens/S3-case-desk.md), [S4. Members](../screens/S4-members.md)
- APIs: [A3. Pre-auth Answer](../apis/A3-preauth-answer.md), [A5. Query Request](../apis/A5-query-request.md), [A10. Predetermination Quote](../apis/A10-predetermination-quote.md), [A13. Adjudicate](../apis/A13-adjudicate.md), [A18. Provider Driver](../apis/A18-provider-driver.md), [A20. ABHA Create and Verify (ABDM M1)](../apis/A20-abha-m1.md)
- Callbacks: [C1. Callback Door](C1-callback-door.md), [C5. Claim Submit](C5-claim-submit.md), [C6. Predetermination](C6-predetermination.md), [C9. Communication](C9-communication.md)
- FHIR: [F1. Bundle](../fhir/F1-bundle.md), [F7. QuestionnaireResponse](../fhir/F7-questionnaireresponse.md), [F8. Claim](../fhir/F8-claim.md)
- Database: [D3. document_type](../database/D3-document-type.md), [D5. member](../database/D5-member.md), [D7. subscription_family_member](../database/D7-subscription-family-member.md), [D19. case](../database/D19-case.md), [D20. case_diagnosis](../database/D20-case-diagnosis.md), [D21. case_procedure](../database/D21-case-procedure.md), [D22. case_doctor](../database/D22-case-doctor.md), [D23. case_document](../database/D23-case-document.md), [D24. case_document_file](../database/D24-case-document-file.md), [D25. case_line_item](../database/D25-case-line-item.md), [D26. case_timeline](../database/D26-case-timeline.md), [D27. case_exchange_message](../database/D27-case-exchange-message.md), [D31. audit_log](../database/D31-audit-log.md)
- Tests: [T6. Pre-auth Received and Approved](../tests/T6-preauth-approved.md), [T7. Pre-auth Rejected](../tests/T7-preauth-rejected.md), [T9. Enhancement Received and Approved](../tests/T9-enhancement-approved.md), [T18. Redelivery and Duplicates](../tests/T18-redelivery-ignored.md)
