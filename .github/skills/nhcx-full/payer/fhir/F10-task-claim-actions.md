# F10. Task (claim actions and answers)

#### F10R. RESOURCE
`Task`, in both directions.

- **Received** on `v1/task/submit` (cancel, reprocess, release, status), on `v1/status` or headers-only (status), and on `v1/paymentnotice/on_request` (the payment acknowledgement). No profile is checked. Read by [C7. Task Submit](../callbacks/C7-task-submit.md), [C8. Status Enquiry](../callbacks/C8-status-enquiry.md) and [C11. Payment Acknowledgement](../callbacks/C11-payment-acknowledgement.md). A Task asking for a plan is not this resource: it is [F4. Task (InsurancePlan request)](F4-task-insuranceplan.md).
- **Sent** on `v1/task/on_submit` (the answer to a cancel, a reprocess or a release, and to a status Task sent on the task route) and on `v1/on_status` (the answer to a status ask on the status route), by [A9. Task Answer](../apis/A9-task-answer.md) and [A8. Status Answer](../apis/A8-status-answer.md). The shape is the scheme's own answer to a Task [PAYER](../references/PAYERS.md#markers): a Task coded `approve` when the payer did what was asked and `reject` when it could not, its output an `include` pointing at a ClaimResponse ([F9. ClaimResponse](F9-claimresponse.md)) that says where the case now stands, with the Patient, both Organizations and the Coverage beside it.

#### F10D. DESCRIPTION
**Received.** The first `Task` in the bundle that is not a plan request. What it asks is its `code` on `http://terminology.hl7.org/CodeSystem/financialtaskcode` (the first coding of any system when none names that one):

| `code` | Means | Handled by | Answered |
|---|---|---|---|
| `cancel` | withdraw the pre-authorisation | [C7. Task Submit](../callbacks/C7-task-submit.md) | yes, [A9. Task Answer](../apis/A9-task-answer.md), workflow PC02 |
| `reprocess` | look at a decided claim again | [C7. Task Submit](../callbacks/C7-task-submit.md) | acknowledged at once, then decided on this thread ([A9. Task Answer](../apis/A9-task-answer.md)) |
| `release` | pay the balance of a partly paid claim; the amount asked for rides as the `amount` input | [C7. Task Submit](../callbacks/C7-task-submit.md) | as reprocess |
| `status` (no `paymentack` output) | where does this thread stand | [C8. Status Enquiry](../callbacks/C8-status-enquiry.md) | yes, [A8. Status Answer](../apis/A8-status-answer.md) |
| any code with output `status` = `paymentack` | the hospital saw this payer's payment notice | [C11. Payment Acknowledgement](../callbacks/C11-payment-acknowledgement.md) | no |

A status enquiry may arrive with no bundle at all: the HCX shape carries only `x-hcx-status_filters` in the protected header, and the envelope alone is then read as a status Task ([C1. Callback Door](../callbacks/C1-callback-door.md)). The filter names the thread being asked about: its `x-hcx-correlation_id` (or `correlation_id`), `x-hcx-workflow_id` (or `workflow_id`) and `claim_number` (or `claimNumber`, `x-hcx-claim_number`); each fills its slot only when a Task input did not.

The claim the Task is about is its identifier typed `CLN`, else the first input or output typed `claimNumber`, `intimationNumber`, `initimationNumber` (the misspelling some builders send) or `CLN`. A cancel's `reasonCode` (display, else code) and `description` become the reason on the timeline.

**Sent.** The answer is rendered whichever way the case went. `status` is `completed` when the payer did what was asked (a cancel accomplished, a reprocess decided), `accepted` when it took the request in for a person to decide (the reprocess acknowledgement), `rejected` when it could not (a closed case, no such claim). The code is `approve` "Activate/approve the focal resource" unless the status is `rejected`, then `reject` "Reject the focal resource", on `http://hl7.org/fhir/CodeSystem/task-code`. `description` is a line for a person: the outcome of the reprocess, why a cancel was refused, "No submission on that thread is on record with this payer." on an unknown status ask.

When a case matched, `output[0]` is an `include` (`http://terminology.hl7.org/CodeSystem/financialtaskinputtype`) pointing at a ClaimResponse in the same bundle: `use` by the leg the case is on (`claim` at stage claim, payment or settled, else `preauthorization`), `outcome` and the claim-level `status` adjudication from the case (a withdrawn case reads `complete` and `cancelled`, as the scheme's cancellation does), the `benefit` and `submitted` totals, and the description as `disposition`. The Patient carries the member identifier alone ([F15. Patient](F15-patient.md)), the Organizations both parties ([F17. Organization](F17-organization.md)), the Coverage the enrolment ([F18. Coverage](F18-coverage.md)). When nothing matched, the Task names the two parties and carries no ClaimResponse, Patient or Coverage; an issue in the render result says so.

A status answer also carries the protocol header `x-hcx-status_response` beside the bundle, which is what the hospital reads first ([A8. Status Answer](../apis/A8-status-answer.md)): `entity_type` (`preauth` or `claim`), `entity_status` (the case's stage and decision as one code, for example `preauth-pending`, `claim-queried`, `payment-partial`, `settled`, `cancelled`, `not-found`), `claim_no`, `stage`, `outcome`, `total_claimed`, `total_approved`, `total_paid`, `answered`.

Every resource sent is tagged `SUBSETTED` on `http://terminology.hl7.org/CodeSystem/v3-ObservationValue`; every entry's `id` is its `fullUrl` under `<base>/v1/task/on_submit`, the bundle a `collection` identified by the hospital's claim number ([F1. Bundle](F1-bundle.md)).

#### F10F. FIELDS

Received:

| Element read | Stored in | Notes |
|---|---|---|
| `Task.code.coding[]` code (financialtaskcode preferred) | decides the handler | `cancel`, `reprocess`, `release`, `status` |
| `Task.status` | the audit line | `requested` in practice |
| `Task.description` | the reason on [D26. case_timeline](../database/D26-case-timeline.md); the summary on [D27. case_exchange_message](../database/D27-case-exchange-message.md) | else `reasonCode`, else "Requested by <sender> over NHCX" |
| `Task.reasonCode.coding[0]` display, else code | the cancel reason on [D26. case_timeline](../database/D26-case-timeline.md) | |
| `Task.identifier[]` typed `CLN`, else `input[]` or `output[]` typed `claimNumber`, `intimationNumber`, `initimationNumber`, `CLN` (`valueString`) | the claim number the case is found by ([D19. case](../database/D19-case.md) `nhcx_claim_ref`, `nhcx_claim_submission_ref`, `claim_no`) | first found wins |
| `input[]` or `output[]` typed `correlationId`, `correlation_id`, `x-hcx-correlation_id` (`valueString`) | the thread a status ask names | else from `x-hcx-status_filters` |
| `output[]` typed `status`, `valueCodeableConcept` code on `https://nrces.in/ndhm/fhir/r4/CodeSystem/ndhm-task-output-value` | `paymentack` marks the payment acknowledgement ([D30. payment](../database/D30-payment.md) `nhcx_acknowledged_at`) | |
| `input[]` typed `amount`, `valueMoney.value` | the balance a release asks for, appended to the reopen reason | |
| envelope `x-hcx-status_filters` (object, or a string holding JSON) | the correlation, workflow and claim number of a status ask | read only when the Task left them empty |
| the whole bundle (or the filters when there is none) | [D27. case_exchange_message](../database/D27-case-exchange-message.md) `payload`, kind `task` or `status`, direction `in` | |

Sent:

| Element written | From | Notes |
|---|---|---|
| `Task.status` | `completed`, `accepted` or `rejected` | as above |
| `Task.intent` | `order` | |
| `Task.code.coding[0]` | `approve` or `reject` on `http://hl7.org/fhir/CodeSystem/task-code` | by status |
| `Task.description` | the outcome line | |
| `Task.authoredOn` | now, `+05:30` | |
| `Task.requester`, `Task.owner` | the payer Organization, the provider Organization ([F17. Organization](F17-organization.md)) | by fullUrl |
| `Task.output[0]` | `include` on `http://terminology.hl7.org/CodeSystem/financialtaskinputtype`, `valueReference` the ClaimResponse's fullUrl | only when a case matched |
| `ClaimResponse` (F9 shape) `use`, `outcome`, `adjudication[status]`, `disposition`, `total[benefit]`, `total[submitted]`, `identifier[CLN]` | the case's stage and decision, [D19. case](../database/D19-case.md) `total_approved`, `total_claimed`, the claim number | `identifier.system` is `<base>/v1/claim` or `.../preauthorization` |
| `Patient`, `Organization` (payer, provider), `Coverage` | [D19. case](../database/D19-case.md), [D1. payer](../database/D1-payer.md), [D6. subscription](../database/D6-subscription.md), [D12. policy](../database/D12-policy.md) | the four entries beside the answer, in the scheme's order [PAYER](../references/PAYERS.md#markers) |
| header `x-hcx-status_response` (status answers only) | the case's state as listed above | `entity_status` `not-found` when nothing matched |
| `Bundle.identifier.value` | the hospital's claim number, else the case number | |

#### F10U. USED BY
- APIs: [A6. Payment Notice](../apis/A6-payment-notice.md), [A7. Payment Enquiry Answer](../apis/A7-payment-enquiry-answer.md), [A8. Status Answer](../apis/A8-status-answer.md), [A9. Task Answer](../apis/A9-task-answer.md), [A12. Transaction FHIR](../apis/A12-txn-fhir.md)
- Callbacks: [C1. Callback Door](../callbacks/C1-callback-door.md), [C7. Task Submit](../callbacks/C7-task-submit.md), [C8. Status Enquiry](../callbacks/C8-status-enquiry.md), [C11. Payment Acknowledgement](../callbacks/C11-payment-acknowledgement.md)
- FHIR: [F1. Bundle](F1-bundle.md), [F4. Task (InsurancePlan request)](F4-task-insuranceplan.md), [F9. ClaimResponse](F9-claimresponse.md), [F13. PaymentNotice](F13-paymentnotice.md), [F15. Patient](F15-patient.md), [F16. Practitioner](F16-practitioner.md), [F17. Organization](F17-organization.md), [F18. Coverage](F18-coverage.md)
- Tests: [T10. Pre-auth Cancelled](../tests/T10-preauth-cancelled.md), [T14. Reprocess and Balance Release](../tests/T14-reprocess-and-release.md), [T17. Status Enquiry Answered](../tests/T17-status-answered.md)
