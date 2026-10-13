# T10. Pre-auth Cancelled

#### T10D. DESCRIPTION

A cancel Task arrives on [C7. Task Submit](../callbacks/C7-task-submit.md) naming the claim number; the case is withdrawn (stage `cancelled`, not `rejected`: nobody decided against it), and [A9. Task Answer](../apis/A9-task-answer.md) answers twice: a ClaimResponse closing the pre-auth thread and the completed Task on the cancellation's own thread, both under PC02. A second cancellation is refused on the wire.

#### T10S. SETUP

One member under the [T1. Test Configuration](T1-test-configuration.md) prefix enrolled on the default product. A pre-authorisation filed and acknowledged (as [T6. Pre-auth Received and Approved](T6-preauth-approved.md) up to the acknowledgement), not yet decided.

#### T10G. GUI

1. Hospital side, through the provider driver ([T2. Test Runners](T2-test-runners.md)): send a pre-authorisation.
2. [S2. Cases](../screens/S2-cases.md): the case is pending at stage `preauth`.
3. Hospital side: cancel the pre-authorisation with the reason "Patient went elsewhere.".
4. [S2. Cases](../screens/S2-cases.md): the case shows stage `cancelled`; open it.
5. [S3. Case Desk](../screens/S3-case-desk.md): the timeline records the withdrawal by the hospital; the exchange log shows the Task in, the ClaimResponse out and the Task answer out; no decision can be taken.
6. Hospital side: cancel again; the pre-authorisation tab shows the refusal.

#### T10L. CLI

1. Seed the member and enrolment; through [A18. Provider Driver](../apis/A18-provider-driver.md), send the pre-authorisation and wait for the case through [A15. Case Exchange Log](../apis/A15-case-exchange.md).
2. Through [A18. Provider Driver](../apis/A18-provider-driver.md), send the cancel Task with the reason.
3. Read the case and its exchange log through [A15. Case Exchange Log](../apis/A15-case-exchange.md).
4. Through [A18. Provider Driver](../apis/A18-provider-driver.md), send the cancel Task again; read the exchange log.

#### T10X. EXPECT

- The delivery is answered `cancelled`, stage `cancelled`; [D19. case](../database/D19-case.md) adjudication is `cancelled`.
- Two messages go out: on `v1/preauth/on_submit` a ClaimResponse on the pre-auth's correlation id with `outcome` `error` and status `cancelled`, workflow PC02; on `v1/task/on_submit` the completed Task on the cancel's own correlation id, workflow PC02, `response.complete`, carrying the ClaimResponse beside Patient, both Organizations and Coverage ([F10. Task (claim actions and answers)](../fhir/F10-task-claim-actions.md)) [PAYER](../references/PAYERS.md#markers).
- The second cancel is answered `refused` and the Task goes back `rejected` on its own thread.
- The exchange log holds at least four messages: the Task in, the two answers out, and the refused repeat.
- The hospital's side shows the pre-authorisation cancelled and carries the episode on under a fresh number.
