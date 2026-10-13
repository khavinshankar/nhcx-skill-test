# T17. Status Enquiry Answered

#### T17D. DESCRIPTION

A status enquiry arrives on [C8. Status Enquiry](../callbacks/C8-status-enquiry.md) in either shape: a status Task on `v1/task/submit` (what the sandbox accepts) or the bare `x-hcx-status_filters` header on `v1/status` [SANDBOX](../references/PAYERS.md#markers). [A8. Status Answer](../apis/A8-status-answer.md) answers at once with where the thread stands, as the `x-hcx-status_response` header beside a Task bundle, on the route the ask came in on; an unknown thread is answered `not-found`.

#### T17S. SETUP

One member under the [T1. Test Configuration](T1-test-configuration.md) prefix enrolled on the default product. A pre-authorisation filed and acknowledged, then approved during the test.

#### T17G. GUI

1. Hospital side, through the provider driver ([T2. Test Runners](T2-test-runners.md)): send a pre-authorisation.
2. Hospital side: ask where it stands; the enquiry rows show the answer, pending.
3. [S3. Case Desk](../screens/S3-case-desk.md): approve the case.
4. Hospital side: ask again; the enquiry rows show approved.
5. [S3. Case Desk](../screens/S3-case-desk.md): the exchange log shows both enquiries in and their answers out.

#### T17L. CLI

1. Seed the member and enrolment; through [A18. Provider Driver](../apis/A18-provider-driver.md), send the pre-authorisation and wait for the case through [A15. Case Exchange Log](../apis/A15-case-exchange.md).
2. Through [A18. Provider Driver](../apis/A18-provider-driver.md), send a status Task by claim number; read the answer through [A12. Transaction FHIR](../apis/A12-txn-fhir.md).
3. Approve the case through [A13. Adjudicate](../apis/A13-adjudicate.md); through [A18. Provider Driver](../apis/A18-provider-driver.md), send a status enquiry by correlation id; read the answer.
4. Through [A18. Provider Driver](../apis/A18-provider-driver.md), ask about a correlation id nothing here has.

#### T17X. EXPECT

- The first enquiry is answered `preauth-pending`: the `x-hcx-status_response` header carries `entity_status` `preauth-pending` and `entity_type` `preauth`, the Task in the bundle is `completed`, the answer goes on `v1/task/on_submit` for a Task ask and on `v1/on_status` for a header ask, on the ask's own correlation id, `response.complete` ([F10. Task (claim actions and answers)](../fhir/F10-task-claim-actions.md)).
- After the approval the answer is `claim-approved` with `answered` true, because the verdict went out.
- The unknown thread is answered `not-found` with the Task `rejected`, never left silent.
- The hospital's side shows the answers in its enquiry rows, newest first.
